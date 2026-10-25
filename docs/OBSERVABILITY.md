# Observability and performance (S9)

What `raglab serve` traces, what it never traces, the switch that serves the perf stub and how
prod refuses it, the k6 smoke in CI, and the collector. Plan:
[2026-10-23-s9-observability-perf.md](plans/2026-10-23-s9-observability-perf.md); evidence: its
ledger.

## Tracing is off unless a collector is named

Only `raglab serve` builds a tracer provider, and only when `RAGLAB_OTLP_ENDPOINT` names a
collector on the loopback interface by its address (`http://127.0.0.1:<port>`, not the name
`localhost`; S10 widens it with an allowlist). Anything else refuses to start. `raglab eval`, `raglab judge`, `raglab ask` and every other command
use the no-op tracer and build nothing (`tests/obs/test_spans.py`). Spans go over OTLP/HTTP (no
gRPC: Langfuse takes none, and `grpcio` stays out of the lock), batched, and are flushed when the
server stops gracefully. `OTEL_EXPORTER_OTLP_ENDPOINT` never decides where spans go, the resource
is the service's name and version only (never `OTEL_RESOURCE_ATTRIBUTES`), and FastAPI's own
auto-configuration is off in code, so `FASTAPI_OTEL_AUTO_CONFIGURE=true` adds no exporter.

OpenTelemetry is imported only in `raglab.obs` (`scripts/check_architecture.py`, rule 7): the
pipeline writes to the `Tracer` port of `raglab.core`, as it calls the `ChatModel` port.

## What one /ask makes

One trace, named and attributed by the GenAI semantic conventions at commit `9ffc7e00c639` of
`open-telemetry/semantic-conventions-genai` (2026-10-21; status Development, no release). The names
are constants in `src/raglab/obs/names.py`; a rename in the spec is a reviewed pull request.

| Span | Kind | Parent | Attributes |
|---|---|---|---|
| `POST /ask` (FastAPI's request span) | server | none: the root | `http.request.method`, `http.route`, `http.response.status_code` |
| `raglab.ask` (the pipeline) | internal | the request span | `raglab.prompt.version`, `raglab.status`, `raglab.label`; a guard's decision as `raglab.guard.name`, `raglab.guard.stage` and `raglab.guard.reason` (the API's fixed key); `raglab.tenant` once the input guards have passed; `raglab.retrieved.ids` and `raglab.cited.ids` once the retrieved-chunk guards have passed; `error.type` on a failure |
| `retrieval policy-pack` | client | the pipeline span | `gen_ai.operation.name` retrieval, `gen_ai.data_source.id`, `gen_ai.retrieval.top_k`, `raglab.retrieved.count` |
| `embeddings <model>` | client | the retrieval span | `gen_ai.operation.name` embeddings, `gen_ai.provider.name`, `gen_ai.request.model`, `gen_ai.embeddings.dimension.count`, `raglab.embedder.revision` |
| `chat <model>` | client | the pipeline span | `gen_ai.operation.name` chat, `gen_ai.provider.name`, `gen_ai.request.model`, `raglab.model.digest`, `gen_ai.request.seed`, `gen_ai.prompt.name`, the request settings the model has (`gen_ai.request.temperature`, `top_p`, `max_tokens`, `reasoning.level`, `gen_ai.output.type` json when a schema is requested, `server.address` and `server.port`), `gen_ai.usage.input_tokens` and `output_tokens` only as the server reported them, `error.type` on a failure |

**`error.type` takes one of three fixed values**, as the spec asks an instrumentation to document:
`unavailable` (no reply), `timeout` (no reply in time) and `invalid_output` (a reply outside the
answer schema). The chat span stays open through the parse, so an invalid reply is its error.
Never an exception's message or stack: spans start with exception recording off, and the span
status carries a code, never a description.

**Token counts** follow S5's rule: as the server reports them. An unreported count stays unset,
never 0, never estimated.

## What is never traced

- **Content, by default.** No question, answer, chunk text, system text, prompt or raw reply is
  set on any span. The spec's Opt-In attributes (`gen_ai.input.messages`,
  `gen_ai.output.messages`, `gen_ai.system_instructions`, `gen_ai.retrieval.query.text`,
  `gen_ai.retrieval.documents`) are never set at all: the input messages would hold every retrieved
  chunk's text, which no run record holds, and the output messages the model's raw reply, which is
  exactly what the output guard may withhold.
- **What a guard removed** (the main plan's guardrails table, "traces never keep what a guard
  removed"): a refused or withheld request leaves no text; a decision is its guard, its stage and
  the API's fixed reason key (`raglab.core.reasons`), never the event's own text, which can carry
  the refused character or another tenant's chunk id; ids and the tenant appear only once the
  guards that check them have passed (`tests/obs/test_guard_traces.py`).
- **Which decision the guard attributes hold** (S7, merged with S9): `raglab.guard.name`,
  `raglab.guard.stage` and `raglab.guard.reason` hold the decision that stopped the request, or,
  when nothing stopped it, a drop step's decision: the register filter's, as `register`,
  `retrieved` and `dropped`, with `raglab.status` ok, which tells the two apart. The retrieved ids
  are the chunks kept, so a page the register filter left out never appears in a trace. The
  caveat: a request that is dropped from and then withheld shows only the stop in its trace; the
  drop stays in the run record's guard events and in the server log (guard, stage and key).
- **The instruction scan.** Its quarantines happen when the index is built, not in a request, so
  no trace holds them; they are listed in the attack record's manifest (`attack.quarantined`).
- **FastAPI's request details.** Its request span also records the Host header (as
  `server.address` and `server.port`), the path, the query, the scheme and the protocol version,
  and an escaped exception's class. Only the method, the route and the status code leave. Health
  checks and the page make no span at all: FastAPI's telemetry covers `POST /ask` only.
- **The bearer token.** The API turns it into the caller's tenants before the pipeline runs.
- **A caller's trace context.** The `traceparent`, `tracestate` and `baggage` headers are never
  read: while raglab traces, the global text-map propagator reads nothing, so every request starts
  a trace of raglab's own, rooted at its request span; every span is sampled, so a `traceparent`
  with flags 00 cannot silence a request; and a span leaves with its ids and an empty trace state
  (the criteria judge's S9-J2; `tests/obs/test_trace_context.py`). Joining a caller's trace (W3C
  propagation from a trusted gateway) is S10's decision, with the host.

**One filter on the way out.** Every span leaves through `raglab.obs.otel.AllowlistExporter`: only
the reviewed keys of `names.py` for raglab's spans, the three HTTP keys for FastAPI's, none for
any other instrumentation; no events, no links, no status description, and the resource's name
and version. A key nobody reviewed never leaves. `tests/obs/test_redaction.py` plants markers in
the question, a chunk, the answer, an invalid reply, an unavailable error, an escaped exception
and a test-only token, with tenant B's canaries, and checks both what leaves and what raglab's
code recorded before the filter.

## The content opt-in (D4: "Opt-in for local debugging only")

`RAGLAB_TRACE_CONTENT=1` records, on the pipeline span only and only for an ok answer, the question
as the pipeline passed it on after the input guards (`raglab.content.question`) and the answer's
text after the output guards (`raglab.content.answer`). Nothing of a refused, blocked,
unavailable or invalid request. It is honoured only where `RAGLAB_ENV` is exactly `ci` or `local`;
anywhere else the server refuses to start, and any value but `1` refuses too. The collector's
Langfuse pipeline deletes both keys before anything leaves, so content never leaves the machine
even from a session where the opt-in is on.

Lab practice: production keeps content out of traces, or sends it to a restricted store with its
own retention.

## PERF_TEST_MODE, and how prod refuses it

`PERF_TEST_MODE=1` serves the perf stub: `config/perf.toml`, whose generator provider is
`perf-stub` (FakeChat's echo under that name, provenance fake), behind the local config's
retrieval settings and the demo tokens. Two keys must match: the stub is served only with the
mode, and the mode is accepted only with a perf-stub config, so it never runs under a real model.
Only `raglab serve` reads a perf-stub config; every other command refuses it. `/version` names
`perf-stub`, provenance `fake`.

`RAGLAB_ENV` says where the server runs. Each switch is honoured only where it is exactly `ci` or
`local`. Under `prod`, unset or any other value, `raglab serve` exits 1 with one line naming the
reason, before it builds anything or binds the port; `create_app` checks again, so an app built
another way refuses too. That fails closed, as the tenant guard does. With neither switch set,
nothing changes: the container and the API smoke serve as before. S10's deploy sets
`RAGLAB_ENV=prod`, and decides which demo controls the mode lifts for a load test.

## The k6 smoke: `make perf-smoke`

What pr-fast's `perf` job runs, beside `check`, and what you can run locally (it loads no model;
check `make ollama-status` first if a model session might be up). It:

1. fetches k6 2.3.0 and the collector (core `otelcol` v0.162.0) once into
   `~/.cache/raglab/tools` (`RAGLAB_TOOLS_DIR`), checks each archive's sha256 against its pin in
   `scripts/perf_smoke.py` on every use, extracts the binary for this run, and validates the
   collector's three configurations;
2. starts the collector on `127.0.0.1:4391`, with a pid file;
3. starts `raglab serve --config config/perf.toml` on `127.0.0.1:8791` with `PERF_TEST_MODE=1`,
   `RAGLAB_ENV=ci`, tracing to the collector, content off;
4. runs `perf/smoke.js`: one virtual user (`/ask` runs behind a lock, so more users would measure
   the queue), 10 warm-up requests, then 100 gated ones, on questions written in the script (none
   from the golden set), each with a marker; then sends a fixture span carrying every content key;
5. stops the server (SIGTERM: a graceful stop flushes its spans), then the collector;
6. checks the collector's files: every `/ask` has its trace with the five spans, no marker
   appears, no content key passes the Langfuse pipeline, and the fixture's keys reached the local
   file;
7. runs the postcheck: both ports closed, no process left, the pid file removed.

Whatever happens (an error, Ctrl-C, SIGTERM, SIGHUP) the server and the collector are stopped and
the postcheck runs. A pid file left by a run that was killed makes the next start refuse until
you stop that collector and delete the file. The ports are `PERF_PORT` and `PERF_OTLP_PORT`.

**The gate.** Every reply must be 200 with status ok and no request may fail. The median of the
100 gated requests must be under T = 40 ms, set on 2026-10-24 by the rule in
[THRESHOLDS.md](THRESHOLDS.md): ten report-only runs of the job at one commit, T = 2 × the largest
median (15.38 ms), rounded up to the next 10 ms. A slower median fails the job with k6's line
`✗ 'med<40'`. p90, p95, the minimum and the maximum are reported, in the log and the job's step
summary, never gated. It is the HTTP path on the stub on GitHub's runner, not Q-01. T changes only
in a reviewed pull request with ten new runs (a change of k6, of the runner image, of the stub, or
a guard that adds latency to `/ask`).

Lab practice: a smoke, not a load test. It catches a regression that doubles the API's time, not
one of 10%; production load-tests a staging copy of the real deployment, with the model in the
path, against agreed latency objectives.

## The collector and Langfuse (D2: "Collector in CI only, no account")

`deploy/otel/`, for core `otelcol` v0.162.0: the smallest official distribution whose own
`components` list has the OTLP receiver, a processor that deletes attribute keys (`attributes`)
and the file exporter (the ledger has the list).

- `collector.yaml`: the local pipeline. OTLP over HTTP received on `127.0.0.1` only, batched,
  written to a file under `runs/tmp/` (gitignored). The collector serves no metrics endpoint of
  its own.
- `langfuse.yaml`: the route to Langfuse, merged over it. First the `attributes/content` processor
  deletes every content key raglab defines, then `otlp_http` to Langfuse's `/api/public/otel`
  endpoint with Basic auth from the environment (`LANGFUSE_OTEL_ENDPOINT`, `LANGFUSE_BASIC_AUTH`:
  the base64 of the public and secret keys; core `otelcol` has no basicauth extension). Without
  those variables the configuration does not validate, so it cannot start by accident.
- `langfuse-stand-in.yaml`: a file stands in for Langfuse. `make perf-smoke` runs the Langfuse
  pipeline this way; the exporter to Langfuse is defined, used by no pipeline, and pointed at a
  loopback placeholder. Nothing is sent anywhere.

Under D2 nothing sends to Langfuse and no account exists; S10 chooses the sink, Langfuse or
Datadog, with the host. A session that sends would merge `langfuse.yaml` only when its keys are
set, from `.env`, never in CI.

Lab practice: one collector per run and a file as the sink. Production runs collectors as agents
or a gateway, with sampling and PII redaction, and routes to Langfuse or Datadog (S10's
document). The collector's and k6's archives are checked by sha256 only; their sigstore signatures
are published and not verified here, while production verifies signatures.
