---
stage: S9
name: observability-perf
nodes: [S9]
date: 2026-10-23
branch: feat/s9-observability-perf
status: draft, awaiting the maintainer's approval
---

# S9: Tracing with redaction, a perf mode that prod refuses, and a k6 smoke in CI

A stage of the main plan's phase P3 (release v0.3), planned early, beside v0.2's stages (your go,
under Approval). Branch: `feat/s9-observability-perf`, cut from `main` at `2b9ba60`, answer-v2's
merge.

The main plan's row for S9: "gen_ai spans; message content off by default, redaction proven by a
test; optional Langfuse via a collector; API refuses `PERF_TEST_MODE` in prod; [CI] k6 smoke
against the stub, gating the median and reporting p95". Its guardrails table gives S9 one more
line: "Logs | traces never keep what a guard removed (how-to 07 step 8) | — | S9". S10's row later
writes "OTel to Langfuse or Datadog" and "PII redaction at the collector" into
`path-to-prod-aws.md`; S9 builds the lab form those sentences start from.

**A roadmap change, said plainly.** The main plan puts S9 in v0.3, after S8 (the phase map's
`S8 --> S9` edge), and v0.2 (S5, S4b, S6 to S8) is not released yet. Building S9 now brings a v0.3
stage forward. D1 asks when it merges and which release it ships in.

## Where S9 starts

Read from the files at `2b9ba60`, from PyPI's and GitHub's release metadata, and from two pr-fast
runs of 2026-10-23 (Sources). Each number is copied from one of them.

**What S9 really depends on.** On S3, which is merged: the API (`src/raglab/api/`), the pipeline
and its guard events (`src/raglab/generate/pipeline.py`), the fake model (FakeChat, provider
`fake`), the configs, the API smoke and the loopback rule of the local adapter. On S5's token rule
(tokens as the server reports them; an unreported count stays unreported). On answer-v2's outcome:
`raglab.generate.prompts.CURRENT` names the prompt, answer-v1. It does not depend on S4b, S6 or
S8: it reads no dataset field beyond the answer key's tenant canaries (in its tests), no judge and
no gate map. The `S8 --> S9` edge is an order of phases, not a data dependency. S7 is a soft
dependency, both ways (under "Inputs and outputs").

**The API.** `/healthz`, `/version` and `/ask` (a bearer token names the tenants a caller may
use), behind a lock: "One request runs at a time (a lock; lab scale)". A refusal's `reason` comes
from a fixed vocabulary (`REASONS`), never a guard's own text, which goes to the server log only.
FastAPI 0.144.0, Starlette 1.8.0, uvicorn 0.54.0.

**FastAPI already speaks OpenTelemetry.** In `uv.lock`, FastAPI 0.144.0 depends on
`opentelemetry-api` 1.45.1. FastAPI's documentation says: "FastAPI provides OpenTelemetry support
by default for HTTP request traces, metrics, and logs"; its settings `tracing`, `metrics`, `logs`
and `operation_spans` default to `True`; "Configure the library before the app starts, and FastAPI
uses those providers automatically"; "Exception logs include the exception's type, message, and
stack trace. Messages and stack traces can contain sensitive information"; and `auto_configure`
"Add[s] exporters for endpoints set in environment variables", by default only when
`FASTAPI_OTEL_AUTO_CONFIGURE=true` [FA1]. `create_app` passes no `telemetry` setting today. Nothing
configures a provider, so all of it goes to OpenTelemetry's no-op default; the moment S9 sets a
tracer provider, FastAPI's own spans go out with raglab's. The page lists no attributes of its
request spans, so S9 proves their content by test rather than by reading.

**The pipeline.** Input guards, retrieval, retrieved-chunk guards, the prompt, the model, the
parser, output guards. A `GuardEvent` has `guard`, `stage` and `reason`; the reason is free text
(for example the code point of a refused character). An answer withheld by a guard carries no text.

**Nothing traces yet.** There is no `raglab.obs`, no `Tracer` port (the main plan's layout lists
both), no `perf/` folder and no k6. The pytest marker `perf` exists and `make test` leaves it out
(`PYTEST_OFFLINE`). Tests never use the network: an autouse fixture refuses every socket connection
(`tests/unit/test_no_network.py`). `scripts/check_architecture.py` has six rules; none names
OpenTelemetry. The run record's case lines carry no `trace_id` (the main plan's run record v1 lists
one).

**The configs.** `config/fake.toml` (FakeChat, the cached ONNX embedder) is what the container and
the API smoke serve. `config/local-ollama.toml` has the same chunker (1,200 characters), embedder
and `k` (5), and also `[api] tokens`.

**The locks.** The main lock has `opentelemetry-api` 1.45.1, `protobuf` 7.36.2 and `requests`
2.34.2. The DeepEval tool's lock (`tools/deepeval-check/uv.lock`, which records raglab by path)
already resolves `opentelemetry-api` and `opentelemetry-sdk` 1.45.1 and
`opentelemetry-semantic-conventions` 0.66b1, through DeepEval. Neither lock has an OTLP exporter.

**pr-fast today**, from `gh run view --json jobs`:

| Run | Event | `check` job | Tests | API smoke | Tesseract install |
|---|---|---|---|---|---|
| 39974278476 | push to `main`, 2026-10-23 14:58 UTC | 607 s | 451 s | 48 s | 10 s |
| 39949465423 | pull request `feat/answer-v2`, 11:54 UTC | 697 s | 346 s | 40 s | 223 s |

The job's timeout is 15 minutes (900 s). The same test step took 1.3 times as long on one run as on
the other. A local `make check` takes about 3.5 to 4 minutes (measured on 2026-10-23).

## Goal

- **gen_ai spans** for one `/ask`, named and attributed as the GenAI conventions say, at a commit
  of the specification this plan pins, beside FastAPI's own request span.
- **Message content off by default**, with an opt-in that prod refuses (D4), and a test that proves
  no question, answer, chunk text, token or other tenant's canary reaches any exported span,
  FastAPI's included.
- **Nothing a guard removed is kept** in a trace.
- **A collector** that the app exports to on loopback, with a file sink, and an optional route to
  Langfuse that deletes content keys before anything leaves (D2).
- **`PERF_TEST_MODE`**: the switch that serves the perf stub, and that the API refuses outside an
  explicit CI or local environment, prod included.
- **A k6 smoke in pr-fast** against the stub, gating the median of `/ask` and reporting p95, with
  the threshold set from measured runs on GitHub's runner by a rule written here (D3).

## Out of scope

| Item | Where it goes |
|---|---|
| `trace_id` and `redacted` in the run record's case lines | not here: the run record and its schema stay as they are, so every published record validates unchanged; they come with tracing of eval runs, if a later stage wants it |
| Tracing `raglab eval`, `raglab judge` and the CLI | not here: the pipeline's spans exist wherever a tracer is built, and only `raglab serve` builds one |
| OpenTelemetry metrics and logs (FastAPI's included) | not here: FastAPI's `metrics` and `logs` are switched off explicitly |
| Langfuse scores or evals written back; Datadog | S10 or later (the path-to-prod document) |
| Demo controls (rate limit, budget, kill switch), and which of them `PERF_TEST_MODE` lifts for a load test | S10 |
| The guards S7 adds (injection, topic, PII mask, grounding) | S7, under S9's tracing rule (below) |
| Load tests beyond a smoke (stress, soak, more users) | the main plan's `manual` gate ("load") |
| Tracing in the container; a deployed collector; tail sampling | S3h and S10 (the image keeps tracing off) |
| Any hosted model | ADR-002: local only for now |

## The OpenTelemetry pieces

**Packages** (PyPI JSON, read 2026-10-23 [PY1]). Every version below was uploaded at least 17 days
before this plan; the last row's note marks a newer release that is inside the cooldown:

| Package | Version | Uploaded | In the main lock today | Note |
|---|---|---|---|---|
| `opentelemetry-api` | 1.45.1 | 2026-10-06 | yes, through FastAPI | |
| `opentelemetry-sdk` | 1.45.1 | 2026-10-06 | no (the tool's lock has it) | requires `opentelemetry-semantic-conventions==0.66b1` |
| `opentelemetry-semantic-conventions` | 0.66b1 | 2026-10-06 | no (the tool's lock has it) | |
| `opentelemetry-exporter-otlp-proto-http` | 1.45.1 | 2026-10-06 | no | requires the four below, `googleapis-common-protos~=1.52` and `requests~=2.7` |
| `opentelemetry-exporter-otlp-proto-common` | 1.45.1 | 2026-10-06 | no | |
| `opentelemetry-proto` | 1.45.1 | 2026-10-06 | no | `protobuf<8.0,>=5.0` |
| `opentelemetry-exporter-http-transport` | 0.66b1 | 2026-10-06 | no | |
| `opentelemetry-exporter-otlp-common` | 0.66b1 | 2026-10-06 | no | |
| `googleapis-common-protos` | 1.75.5 | 2026-09-29 | no | **1.76.0 was uploaded 2026-10-22, inside the 7-day cooldown**: a lock taken before 2026-10-29 pins 1.75.5 |

- **The pins.** The api, the SDK and the exporter at exactly 1.45.1, the conventions package at
  0.66b1: the DeepEval tool's lock already resolves those through raglab's path dependency, and
  another pin would break `uv lock --project tools/deepeval-check`. Any change to the main
  `pyproject.toml` re-locks both projects. Eight packages are new to the main lock; `protobuf` and
  `requests` are already there.
- **The audit.** `make audit` audits both locks; no new skip is planned. If an advisory appears on a
  new package, the developer stops and asks, as on 2026-10-21.
- **OTLP over HTTP, not gRPC.** Langfuse: "`gRPC` is not supported yet" [LF1]; the HTTP exporter
  also keeps `grpcio` out of the main lock.

**The GenAI conventions** [OT1 to OT4]. They have left the core semantic conventions: the old pages
say "This page has moved and is no longer maintained in this repository", and point to
`open-telemetry/semantic-conventions-genai`. That repository lists no release, and its schema URL
reads "TODO". Its documents say "**Status**: [Development]". This plan read `main` at `9ffc7e0`
(committed 2026-10-21):

- **Inference span:** "Span name SHOULD be `{gen_ai.operation.name} {gen_ai.request.model}`";
  "Span kind SHOULD be `CLIENT`". Required: `gen_ai.operation.name`, `gen_ai.provider.name`.
  Conditionally required: `gen_ai.request.model`, `error.type` ("If the operation ended in an
  error"), `gen_ai.request.seed`, `server.port`. Recommended: `gen_ai.response.model`,
  `gen_ai.response.id`, `gen_ai.response.finish_reasons`, `gen_ai.usage.input_tokens`,
  `gen_ai.usage.output_tokens`, `gen_ai.request.temperature`, `gen_ai.request.top_p`,
  `gen_ai.request.max_tokens`, `server.address`. **Opt-In:** `gen_ai.input.messages`,
  `gen_ai.output.messages`, `gen_ai.system_instructions`.
- **Embeddings span:** operation `embeddings`, named `{gen_ai.operation.name}
  {gen_ai.request.model}`. **Retrieval span:** operation `retrieval`, named
  `{gen_ai.operation.name} {gen_ai.data_source.id}`; `gen_ai.retrieval.query.text` "may contain
  sensitive information".
- **Content:** "OpenTelemetry instrumentations SHOULD NOT capture them by default, but SHOULD
  provide an option for users to opt in"; "Model instructions, user messages, and model outputs
  are considered sensitive and are often large in size"; "Instrumentation SHOULD NOT synthesize
  output content for a failed operation".
- **The provider name** for a local Ollama server: no well-known value fits; "If one of them
  applies, then the respective value MUST be used; otherwise, a custom value MAY be used".

What S9 does with that:

- **Names pinned by commit.** The span names and attribute keys are constants in `raglab.obs`,
  each traced to the spec at `9ffc7e0`; COMPATIBILITY.md records the commit and the date. Whether
  the 0.66b1 package's incubating `gen_ai` constants match the moved spec is checked at the start of
  the build, never assumed (S5's rule for DeepEval); the constants do not depend on it.
- **Status Development** means names can change without a release. A rename is a reviewed change
  with its own pull request; nothing follows `main` of the spec automatically.

**Which spans one `/ask` makes:**

| Span | Kind | Made by | What it carries (no content) |
|---|---|---|---|
| `POST /ask` (FastAPI's request span, the root) | server | FastAPI | what FastAPI records, filtered by the allowlist below; Langfuse "requires that a root span is sent" [LF1] |
| raglab's pipeline span | internal | raglab | prompt version; status; decision label; each guard decision as guard name, stage and the API's fixed reason key; the tenant only once the tenant guard has passed; the retrieved chunk ids and the cited ids only once the retrieved-chunk guards have passed |
| `embeddings <model>` | per the spec | raglab | the embedder's model id and revision |
| `retrieval <data source>` | per the spec | raglab | `k` and the number of chunks returned; no query text, no ids (they come after the guards, on the pipeline span) |
| `chat <model>` | client | raglab | provider, model, digest, the request settings, `gen_ai.usage.*` only when the server reported them (never estimated, never 0 for unreported), `error.type` as a fixed value (`unavailable`, `timeout`, `invalid_output`); never an exception's message or stack |

**Content, when D4 allows it.** Off by default. Under D4's recommended option, one setting turns it
on, and only where `RAGLAB_ENV` is `ci` or `local`. Then the pipeline span gets two raglab
attributes: the question as the pipeline passes it on after the input guards, and the answer text
of an `ok` answer after the output guards. The spec's Opt-In message attributes are never set, on
any span. They would carry the framed prompt, which holds chunk text the run record never holds,
and the model's raw reply, which is exactly what the output guard may withhold.

**The allowlist.** Spans leave the process through one filter (the main plan's "redaction span
processor"): only attribute keys on a reviewed list are exported. The list holds the spec's keys
above, raglab's keys, and those of FastAPI's request-span keys that the developer lists in the
ledger at 0.144.0 and judges harmless (method, route, status code: never a client address, a user
agent, a query or a header). A key nobody reviewed never leaves.

**FastAPI's telemetry, set explicitly** in `raglab.api`: `tracing` on (its request span is the
root), `operation_spans` off, `logs` off (the stack-trace warning above), `metrics` off, and
`auto_configure` off in code, so `FASTAPI_OTEL_AUTO_CONFIGURE=true` in an environment cannot add an
exporter beside raglab's.

**Where traces go.** Tracing stays off unless an OTLP endpoint is configured, and in S9 that
endpoint must be a loopback address, as the local model adapter's URL must be. S10 widens it with
an allowlist. `raglab serve` alone builds a tracer provider, with a batch processor and the
OTLP/HTTP exporter; it flushes and shuts down on a graceful stop (the API smoke's SIGTERM).

## The collector, and optional Langfuse (D2)

**The binary.** The official releases (GitHub release metadata, read 2026-10-23 [C1]) publish a
`.sha256` file, with sigstore signatures, next to every archive:

| Release | Published | Days old on 2026-10-23 |
|---|---|---|
| v0.163.2 | 2026-10-21 | 2 |
| v0.163.0, v0.163.1 | 2026-10-16 | 7 |
| v0.162.0 | 2026-09-29 | 24 |

The 7-day cooldown is stated for Python packages and actions; S9 applies it to binaries by
analogy. The developer pins the newest release at least seven days old on the day of pinning, with
its `.sha256` values. For v0.162.0: core `otelcol` 37,254,744 bytes on linux amd64 (`f99929987a91…`)
and 35,177,135 on macOS arm64 (`53de34c02913…`); `otelcol-contrib` 112,285,869 (`fcc063749f73…`) and
96,729,035 (`d5e11974d2e4…`).

**Which distribution.** The documentation says "The components included in the distributions can
be found in the `manifest.yaml` of each distribution" [C2]. This plan read no repository's files,
so which distribution has what is open. The developer picks the smallest official distribution
whose own `components` output (the binary lists them) includes the OTLP receiver, a processor that
deletes attribute keys and the file exporter. That output and the size go in the ledger. Core
`otelcol` is a third of contrib's size.

**The configuration** (`deploy/otel/`):

- an OTLP/HTTP receiver bound to `127.0.0.1` only;
- a local pipeline: a batch processor, then the file exporter, writing under `runs/tmp/otel/`
  (gitignored);
- a Langfuse pipeline: first a processor that deletes every content key the app can emit, so
  content never leaves the Mac even from a local session where D4's opt-in is on; then
  `otlphttp` to `/api/public/otel` with Basic auth built from keys in the environment ("Langfuse
  uses Basic Auth to authenticate requests" [LF1]). It is configured only when those keys are set,
  and never in CI.

**Where it runs.** Only inside `make perf-smoke` (in pr-fast's perf job, and locally while
building) and, under D2's B or C, a Langfuse session target. Each starts the collector as a child
process and stops it whatever happens, on Ctrl-C, SIGTERM and SIGHUP too. A postcheck follows, as
Ollama's sessions do: the port is closed and no collector process is left. A pid file makes the
next start refuse after a SIGKILL. Nothing is installed system-wide; the archive is cached and its
sha256 checked before each use, as `make model` does for the embedder.

**Langfuse's facts** for D2. Cloud: endpoints `https://cloud.langfuse.com/api/public/otel` (EU) and
`https://us.cloud.langfuse.com/api/public/otel` (US). The Hobby plan: "Hobby (Free)", "50k units /
month included", "30 days" of data, "2 users", "No credit card required", region "US, EU, or
Japan"; the page does not say what happens at the limit [LF3]. Self-hosted: OTLP since v3.22.0. The
Compose deployment wants "at least 4 cores and 16 GiB of memory" and "e.g. 100GiB" of storage for
its VM, and "After about 2-3 minutes, the langfuse-web-1 container should log "Ready"" [LF1, LF2].

## `PERF_TEST_MODE`, and how prod refuses it

**What it does in S9.** It serves the perf stub. A new config, `config/perf.toml`, has the local
config's retrieval settings and the demo tokens, with `[generator] provider = "perf-stub"`: the
fake echo model under the name `perf-stub`, built by the factory, provenance `fake`. It never
builds the local model's adapter, so no Ollama is needed. Two keys must match:

- `raglab serve` serves a `perf-stub` config only when `PERF_TEST_MODE=1`;
- `PERF_TEST_MODE=1` is accepted only with a `perf-stub` config, so the mode cannot be switched on
  under a real model;
- only `raglab serve` accepts the `perf-stub` provider.

`/version` names `perf-stub` and provenance `fake`. From S10 on, `PERF_TEST_MODE` is where the demo
controls' exemptions for a load test live (S10 decides which); the refusal below covers them.

**How prod refuses it.** `RAGLAB_ENV` says where the server runs. `PERF_TEST_MODE=1` is honoured
only when `RAGLAB_ENV` is exactly `ci` or `local`. When it is `prod`, unset or anything else, the
server refuses to start: a non-zero exit and one line naming the reason, before the port is bound.
That fails closed, as the tenant guard and the power guard do: the mode needs a positive statement
that this is not prod. `create_app` checks again, so an app built another way refuses too.
`PERF_TEST_MODE` with any value other than `1` or unset also refuses. D4's content opt-in follows
the same environment rule. With neither switch set, nothing changes: the container and the API
smoke serve as today, and the image needs no edit. S10's deploy sets `RAGLAB_ENV=prod` (an output
to S10).

## The k6 smoke in CI (D3)

**k6.** v2.3.0, GitHub's "Latest", published 2026-09-21. Its release ships
`k6-v2.3.0-checksums.txt`: linux amd64 `39c3117b6af8…` (30,847,764 bytes) and macOS arm64
`b2417a3038ed…` [K1]. It is installed as gitleaks is in pr-fast: the archive, its sha256 checked,
with no third-party action. k6's thresholds allow "`avg`, `min`, `max`, `med` and `p(N)`" on a
trend, and a crossed threshold makes k6 "exit with a non-zero exit code" [K2]. The 2.x line is a
major version since 2026-05-11; the developer checks the summary options at 2.3.0. k6 runs on the
runner; no Grafana Cloud account is used.

**The stub and the load.** `make perf-smoke` (`scripts/perf_smoke.py`) runs these steps:

1. starts the collector;
2. starts `PERF_TEST_MODE=1 RAGLAB_ENV=ci raglab serve --config config/perf.toml` on loopback,
   tracing to the collector;
3. runs `perf/smoke.js`: one virtual user, a warm-up that is not gated, then a fixed number of
   `/ask` requests with the demo token, on fixed questions written in the script (none from the
   golden set's test split);
4. stops the server and the collector;
5. checks the collector's file: every `/ask` the smoke sent has its trace with the spans above, and
   the markers planted in its questions appear nowhere;
6. runs the postcheck.

There is one user because `/ask` runs behind a lock: more users would measure the queue, not the
service.

**The thresholds.** Every reply is 200 with status `ok` (`checks` rate 1); no request fails; the
median of `/ask` is under T. p95, with p90, the minimum and the maximum, goes to the summary and the
job's step summary, reported and never gated: the tail on a shared runner is noisier than the
median.

**How T is set, written before any run.** The frame is how-to 06's: "Write the margin before the
run", and ten runs as "a floor for a smoke set" (as answer-v2's plan quotes it):

1. The perf job lands with the median threshold off; the checks and failures thresholds are on.
2. Ten report-only runs of the job at one commit on GitHub's runner: a temporary ten-way matrix in
   one commit, or ten reruns. All ten are kept: none dropped, none run again for a better number.
   Each run's median and p95 are copied from its log into the ledger, with the run id.
3. T = 2 × the largest of the ten medians, rounded up to the next 10 ms. It is committed in
   THRESHOLDS.md's new row, with the ten run ids, their medians and p95s, the rule and the reason;
   a test keeps the k6 script's value equal to that cell.
4. T changes only in a reviewed pull request, with ten new runs under the same rule. Those
   triggers are a change of k6, of the runner image, of the stub, or a guard that adds latency to
   `/ask` (S7).

**The reason for 2×.** GitHub's hosted runners are shared machines whose speed varies: today the
same test step took 346 s on one run and 451 s on another. A smoke must not go red on a slow
machine. The regressions a smoke exists for cost far more than double: a model or an index loaded
per request, a blocking call, a loop that grows with the corpus. The row says plainly that this is
the HTTP path on the stub on GitHub's runner. It is not Q-01, which is in-process, the real model,
on the Mac.

**The job and pr-fast's time.** Under D3's recommended option, the k6 smoke gets its own `perf` job
in pr-fast. It runs beside `check`, under the workflow rules (SHA-pinned actions, `contents: read`,
`persist-credentials: false`, its own timeout). It repeats what the server needs: `uv sync`, the
cached embedder, and pinned Tesseract, because the server reads the scanned page when it starts.

- **Its length, an estimate:** about 3 to 6 minutes. That is 30 to 60 s of setup, Tesseract at 10
  to 223 s (measured), 40 to 48 s for the server's start, checks and stop (the API smoke's
  measured step), and about a minute of k6 and the trace check.
- **pr-fast's wall time** stays the `check` job's, 607 to 697 s today, while the perf job is
  shorter.
- **The arithmetic behind not making it a step of `check`:** about 1.5 to 2 more minutes (an
  estimate) on 697 s is 787 to 817 s, against the 900 s timeout, on a day when Tesseract takes
  223 s.

You add `perf` to the branch's required checks.

## Inputs and outputs

**Inputs from other stages:**

| From | What S9 uses | State |
|---|---|---|
| S3 | the API, the pipeline and its guard events, FakeChat, the configs, the API smoke's pattern, the loopback rule | merged |
| S5 | the token rule: as the server reports them, unreported stays unreported | merged |
| answer-v2 | `raglab.generate.prompts.CURRENT` (answer-v1) for the prompt version on the pipeline span | merged |
| **S7** (planning now) | **1.** The guard layers S7 adds. S9 records a decision as guard name, stage and the API's fixed reason key, so each new guard needs a key in `REASONS`, never its own text in a span. **2.** How a masking guard (PII) hands the masked text on. S9's capture point is after the last input guard, so D4's opt-in records whatever S7 hands on; S7's tests should include a case with the opt-in on. **3.** Whether S7's guards sit in `/ask`'s path and add latency. If so, S7's pull request sets T again by S9's rule (ten runs); if S7 merges first, S9 measures T on top of S7's guards. | not assumed: each is named for S7's plan |
| S4b, S6, S8 | nothing | — |

**Outputs to later stages:** S7 inherits the tracing rule and the k6 gate. S8's GATES.md gets the
perf gate's row from THRESHOLDS.md. S10 sets `RAGLAB_ENV=prod` in its deploy, decides what
`PERF_TEST_MODE` lifts, widens the loopback-only endpoint with an allowlist, and starts its "OTel to
Langfuse or Datadog" and "PII redaction at the collector" from S9's collector configuration.

## Shared files the build touches

So that merges can be sequenced. New files that no other stage touches are listed under "What gets
built".

| File | What S9 changes | Other stages that touch it |
|---|---|---|
| `CHANGELOG.md` | one line | every stage |
| `docs/TEST-PLAN.md` | Q-01's row points to the k6 row too; section 10 gets observability and perf lines | S4b, S6, S7 |
| `docs/THRESHOLDS.md` | a new "Performance (S9)" section, the k6 row | S6, S7, S8 |
| `docs/ARCHITECTURE.md`, `README.md` | S9 `done`; the phase map's edge, per D1 | every stage |
| `docs/plans/2026-10-05-raglab-plan.md` | a dated decision note (D1, D2), as the 2026-10-18 and 2026-10-20 notes; the open-variables row "Langfuse cloud as an optional sink" answered | any stage with a decision note |
| `docs/GUARDRAILS.md` | the Logs row ("traces never keep what a guard removed"), built | S7 |
| `docs/ONBOARDING.md`, `docs/COMPATIBILITY.md` | the "Not testable yet" row moves; the new commands; the versions tested | S6, S7 |
| `Makefile` | `perf-smoke` (and, per D2, a Langfuse session target) | S6, S7 |
| `pyproject.toml`, `uv.lock`, `tools/deepeval-check/uv.lock` | the OpenTelemetry dependencies; both projects re-locked | S7 if it adds a library; the second to merge re-locks both |
| `.github/workflows/pr-fast.yml` | the `perf` job (per D3) | S7 if it adds suites |
| `src/raglab/api/app.py`, `server.py` | FastAPI's telemetry setting; the environment, mode and opt-in checks before the port binds | S7 if it adds refusals, S10 |
| `src/raglab/generate/pipeline.py` | spans; guard decisions; content only after the guards | **S7** (its guard layers) |
| `src/raglab/core/ports.py` | the `Tracer` port | **S7** if the Guardrail port changes for masking |
| `src/raglab/adapters/factory.py`, `fake.py`, `src/raglab/evals/config.py` | the `perf-stub` provider | — |
| `scripts/check_architecture.py`, `tests/unit/test_architecture.py`, `tests/unit/test_workflow_rules.py` | rule 7; the perf job's rules | S7 |

S7 and S9 overlap most: the pipeline, the ports, the architecture rules, the locks and pr-fast.
Whichever merges second rebases onto the other and re-locks both projects.

## Lab practice

- **A smoke, not a load test.** One user on a shared CI runner, a stub for the model: it catches a
  regression that doubles the API's time, not one of 10%. Production load-tests a staging copy of
  the real deployment on capacity of its own, with the model in the path, against agreed latency
  objectives, and sets margins from many more runs.
- **One service, a collector per run, a file as the sink.** Production runs collectors as agents or
  a gateway, with sampling and PII redaction, and routes to Langfuse or Datadog (S10's document).
- **Content opt-in for debugging** (D4). Production keeps content out of traces, or sends it to a
  restricted store with its own retention.
- **Checksums only.** The collector's sigstore signatures are published and not verified here;
  production verifies signatures.

## What gets built

```
src/raglab/core/ports.py            + Tracer port (standard library only), a no-op default
src/raglab/obs/                     tracer provider and OTLP/HTTP exporter (loopback endpoint), span
                                    helpers, the attribute allowlist, the spec's names pinned to
                                    9ffc7e0, the content opt-in; the only package that imports
                                    opentelemetry
src/raglab/generate/pipeline.py     spans around embedding, retrieval and the model; guard decisions;
                                    retrieved ids and content only after the guards
src/raglab/api/                     FastAPI's telemetry set explicitly; RAGLAB_ENV, PERF_TEST_MODE and
                                    the opt-in checked before the port binds, and again in create_app
src/raglab/adapters/                provider perf-stub (the echo model under that name), built by the
                                    factory only
config/perf.toml                    the local config's retrieval, provider perf-stub, the demo tokens
deploy/otel/                        the collector's configuration: the local pipeline, the Langfuse
                                    pipeline (content keys deleted, keys from the environment)
perf/smoke.js                       the k6 smoke
scripts/perf_smoke.py               fetches and checks k6 and the collector, starts both and the
                                    server, runs k6, checks the trace file, stops all, postcheck
scripts/check_architecture.py       rule 7: opentelemetry imported only in raglab.obs
Makefile                            perf-smoke (+ the Langfuse session target, per D2)
.github/workflows/pr-fast.yml       the perf job (per D3)
pyproject.toml, uv.lock, tools/deepeval-check/uv.lock
tests/obs/                          spans, redaction, guard traces (the in-memory exporter)
tests/api/test_perf_mode.py         the mode, the environment and the refusal, in process and as a
                                    subprocess
tests/unit/                         collector configuration; workflow rules; architecture; the
                                    threshold cell
docs/OBSERVABILITY.md (new)         what is traced and never traced, the opt-in, perf-smoke, the
                                    collector, Langfuse, the lab-practice labels
docs/                               THRESHOLDS, TEST-PLAN, GUARDRAILS, COMPATIBILITY, ONBOARDING,
                                    ARCHITECTURE, README, the main plan's note; CHANGELOG
docs/plans/2026-10-23-s9-observability-perf-ledger.md   the ledger
```

The file and target names are suggestions; the developer may choose others and says so in the
ledger.

## Choices I made (you can change them)

| # | Item | Choice | Why |
|---|---|---|---|
| 1 | Where OpenTelemetry lives | a `Tracer` port in `raglab.core`; `opentelemetry` imported only in `raglab.obs` (architecture rule 7); the pipeline takes a tracer as it takes a chat model | the repo's ports-and-adapters rule; the main plan's layout lists the port |
| 2 | Runtime dependency or extra | runtime dependencies of the main project | `raglab serve` traces, pyright must resolve `raglab.obs` in CI, and an extra would need installing there anyway. The cost: eight new packages in the runtime and the image. The alternative: a `raglab[otel]` extra |
| 3 | Protocol | OTLP over HTTP | Langfuse takes no gRPC; no `grpcio` |
| 4 | The spec's names | constants pinned to the spec's commit, the 0.66b1 package checked, not relied on | the spec is Development, has moved and has no release |
| 5 | Content on gen_ai spans | never; D4's opt-in only on raglab's pipeline span, after the guards | the framed prompt holds chunk text; the raw reply is what a guard may withhold |
| 6 | What a trace keeps of a guard | name, stage, the API's fixed reason key; ids and tenant only after the guards pass | a reason or an id can carry what the guard stopped; a tenant-B document id is a tenant-B canary |
| 7 | Redaction | an allowlist of keys at the exporter, and a delete at the collector's Langfuse pipeline | a key nobody reviewed never leaves; content never leaves the Mac |
| 8 | FastAPI's telemetry | request span kept as the root; operation spans, logs and metrics off; `auto_configure` off in code | Langfuse needs the root span; FastAPI's exception logs may hold sensitive text |
| 9 | `PERF_TEST_MODE`'s shape | a `perf-stub` config plus the switch, two keys that must match; `RAGLAB_ENV` fails closed | the config says what runs, as every config here does. Not chosen: the switch overriding a config's model |
| 10 | The stub | the echo model under the name `perf-stub`; a new class only if the echo does not serve | the main plan's `PerfStubChat`, without a second fake |
| 11 | k6's install | the release archive and its sha256, in one fetch path for CI and local | gitleaks' precedent; no third-party action for zizmor to watch |
| 12 | The smoke's load | one user, a warm-up, a fixed request count, questions written in the script | the lock; the test split is never read |
| 13 | The collector's version | the newest at least seven days old (v0.162.0 on 2026-10-23), the smallest distribution with the needed components | the cooldown, by analogy |
| 14 | Review | a `/security-review` pass in the criteria judge's step | S9 decides what traces may hold, and what the API refuses |

## Acceptance criteria

**[CI]** marks what only the pull request's checks prove. Each break is made on a committed file
and restored from git. No criterion needs an Ollama session; `make perf-smoke` loads no model.

| # | Criterion | Evidence | Break |
|---|---|---|---|
| OB1 | **Dependencies, pinned and audited.** `opentelemetry-sdk` and the OTLP/HTTP exporter at 1.45.1 and the api at 1.45.1, pinned exactly; `googleapis-common-protos` 1.75.5 unless the lock is taken after 2026-10-29; both projects locked; every new package's upload date in the ledger, each at least seven days before the lock; `make audit` passes with no new skip; `make deps` passes | `uv lock --check`; `uv lock --project tools/deepeval-check --check`; `make audit`; `make deps`; the ledger's table | the tool's lock restored to `main`'s: `make audit` fails on its `--locked` export; `pyproject.toml` changed without `uv.lock`: `uv sync --locked` fails |
| OB2 | **The port and the fence.** The `Tracer` port in `raglab.core` (standard library only) with a no-op default; `opentelemetry` imported only in `raglab.obs` (rule 7); only `raglab serve` builds a tracer provider; `raglab eval` makes no span and opens no connection | `make architecture`; `tests/unit/test_architecture.py`; a test that an eval run with the fake model builds no provider | an `opentelemetry` import added in `raglab.generate`, then in `raglab.core`: `make architecture` fails naming each file |
| OB3 | **gen_ai spans, by the pinned spec.** One `/ask` makes one trace: FastAPI's request span as the root, raglab's pipeline span, and the embeddings, retrieval and chat spans, named and attributed as the spec at `9ffc7e0` says (the table above); tokens only as reported; `error.type` a fixed value on `unavailable`, `timeout` and `invalid_output`; COMPATIBILITY.md names the spec commit and the date | `tests/obs/test_spans.py` through the API, with the in-memory exporter, FakeChat, and the local adapter against its stub server (usage reported and not reported) | `gen_ai.usage.input_tokens` renamed to another key (for example `gen_ai.usage.prompt_tokens`): the test fails; an unreported count recorded as 0: the test fails |
| OB4 | **Content off by default; the redaction test.** With default settings, no exported span, event, status, link or resource, FastAPI's included, holds the question, the answer, a chunk's text, the system text, the bearer token or another tenant's canary; only allowlisted keys leave the process; no exception message or stack is recorded. With D4's opt-in in a `ci` or `local` environment, the question and an `ok` answer appear on the pipeline span only | `tests/obs/test_redaction.py` through the API (TestClient): the global provider installed once per test session with an in-memory exporter, cleared per test; distinctive markers planted in the question, a chunk, the answer, an invalid reply, an unavailable error's text and a test-only token; tenant B's canaries from the answer key | the default flipped to capture on: the test fails, naming the span and key; `record_exception` added in the pipeline: the invalid-reply marker fails it; the token set as an attribute: it fails; a key added outside the allowlist: it never reaches the exporter (the allowlist's own test) |
| OB5 | **Nothing a guard removed.** With the opt-in on: a refused question (over 500 characters; a control character; an unknown tenant string) leaves no text in any span; an answer withheld by the citation guard leaves none; a request blocked after retrieval (a tenant-B chunk returned for tenant A) records no retrieved id and no tenant-B canary; each decision is recorded as guard, stage and fixed key, never the event's own text | `tests/obs/test_guard_traces.py`, with the scripted store and FakeChat of the existing guard tests | the event's `reason` recorded as an attribute: the refused-question marker fails the test; retrieved ids recorded on the retrieval span before the guard: the tenant-B canary fails it |
| OB6 | **`PERF_TEST_MODE`, and prod refuses it.** `config/perf.toml` is served only with `PERF_TEST_MODE=1`; the mode only with a `perf-stub` config and only where `RAGLAB_ENV` is exactly `ci` or `local`; under `prod`, unset or any other value, the server exits non-zero with one line before the port binds; `create_app` refuses too; the opt-in follows the same rule; `/version` names `perf-stub`, provenance `fake`; with neither switch set nothing changes (the API smoke passes as today) | `tests/api/test_perf_mode.py`: a table of environment, mode and config in process, and as a subprocess that the port never answers, as `tests/unit/test_api_smoke.py` runs one; `make api-smoke` | the `RAGLAB_ENV` check removed: the `prod` and unset rows fail; the check moved after the port binds: the subprocess test fails; the mode accepted with `config/local-ollama.toml`: its row fails |
| OB7 | **The collector: pinned, configured, contained.** The release by the cooldown rule and the smallest official distribution with the needed components (its `components` output and size in the ledger); each archive's sha256 checked before use; the receiver on `127.0.0.1` only; the local pipeline to a file under `runs/tmp/`; the Langfuse pipeline deletes every content key the app can emit and is configured only when its keys are set; `validate` passes on every configuration; the collector runs only inside `make perf-smoke` or D2's session target, which stop it whatever happens and run the postcheck (port closed, no collector process; a pid file after a SIGKILL) | `tests/unit/test_collector_config.py` (loopback bind; the delete list covers every content key raglab defines; no key in any file); the perf job's log; a fixture span carrying the content keys sent through the Langfuse pipeline with a file standing in for Langfuse: the keys are gone | the receiver bound to `0.0.0.0`: the configuration test fails; a content key removed from the delete list: the fixture check fails; one character of a pinned sha256 changed: the fetch refuses; the collector's stop skipped: the postcheck fails |
| OB8 | **Optional Langfuse, per D2.** Under A: the pipeline is built and validated (OB7) and not run against Langfuse; this criterion is not applicable, by D2. Under B or C: one session target with its postcheck sends a few requests with content off; the ledger records the trace id and what Langfuse shows (span names, attributes, no content); keys only in `.env` | the ledger; `make secrets` | under B or C, the session started with the opt-in on: Langfuse's trace still holds no content (expected pass: the collector's delete) |
| OB9 | **The k6 smoke.** k6 2.3.0 from its archive, sha256 `39c3117b6af8…` (linux amd64) checked; `perf/smoke.js` as above (one user, warm-up, fixed count, checks rate 1, no failed request, median under T, p95 and p90 reported); `make perf-smoke` runs the steps listed under "The stub and the load", in that order, and exits non-zero if any fails; **[CI]** the `perf` job, per D3, under the workflow rules | `tests/unit/test_workflow_rules.py` additions (the job pins k6 and checks its sum, runs `make perf-smoke`, has its timeout); **[CI]** the pull request's perf job log and step summary | a delay of 2 × T planted in the `/ask` route: `make perf-smoke` fails on the median, naming the threshold (the judge runs it locally; no sabotage commit is pushed); a 500 planted for one question: the checks threshold fails |
| OB10 | **The threshold, set from measured runs.** The rule above, applied as written: ten report-only runs at one commit, all kept, each run's median and p95 with its run id in the ledger; T by D3's rule; THRESHOLDS.md's row with the run ids, the numbers, the rule, the reason and the provenance (the fake model, GitHub's runner); p95 reported; the row says it is not Q-01; the k6 script's T equals the row's | **[CI]** the ten runs' logs (`gh run view --log`); THRESHOLDS.md; a test that the script and the row agree | the script's T edited alone: the test fails; the criteria judge recomputes T from the ten logs |
| OB11 | **Docs and the standing criterion.** OBSERVABILITY.md (what is traced and never traced, the opt-in, `make perf-smoke`, the collector, Langfuse per D2, the lab-practice labels); THRESHOLDS (OB10); TEST-PLAN (Q-01's pointer, section 10's lines); GUARDRAILS (the Logs row built); COMPATIBILITY (OpenTelemetry 1.45.1, the spec at `9ffc7e0`, k6 2.3.0, the collector's release, "tested on <date>"); ONBOARDING (the row moves, the commands); ARCHITECTURE and README (S9 `done`, the phase map per D1); the main plan's dated note quoting D1 and D2; a CHANGELOG line; the ledger | `tests/unit/test_test_plan.py`, `test_diagram.py`, `test_onboarding.py`, `test_readme.py`, `test_repo_docs.py`; review | |
| OB12 | **`make check`, and [CI] pr-fast green.** `make check` green (its time in the ledger, against 3.5 to 4 minutes today); the `check` job's time and the perf job's time on the pull request (against 607 to 697 s today); the retrieval gate passes; every published record validates unchanged | the `make check` tail in the ledger; the pull request's checks | |

## Mac time and the live sessions

**No Ollama session, under any option.** Nothing in S9 loads a model. The spans of a real model's
call are tested against the local adapter's stub server, which reports usage the way Ollama does.

| Work | Model | Each | Count | Total |
|---|---|---|---|---|
| `make perf-smoke` while building (developer) | none | about 1 to 2 minutes, an estimate (CI's API smoke step: 40 to 48 s; k6 about a minute) | about 5 | about 10 minutes |
| The criteria judge's k6 breaks | none | the same | 2 to 3 | about 5 minutes |
| D2's B: the Langfuse Cloud session | none | about 10 minutes, an estimate | 1 | about 10 minutes |
| D2's C: the self-hosted Langfuse session | none | "about 2-3 minutes" to ready [LF2], plus requests and the stop; the first image pull not measured | 1 to 2 | about 20 to 30 minutes, plus the pull |

- `make perf-smoke` downloads k6 (about 30 MB) and the collector (35 to 97 MB on macOS arm64, by
  distribution) once into a cache, checks their sha256 on every use, binds loopback ports only,
  and stops everything it started. It is a short, model-free target, not one of the serialised
  live sessions; the orchestrator may schedule it anyway.
- D2's C needs about 16 GiB and must never overlap an Ollama session.

## Your review tasks and time

My estimates:

1. **This plan**, with D1 to D5: about 30 to 40 minutes (answer-v2's plan, with four decisions,
   was estimated at 30).
2. **Adding `perf` to `main`'s required checks** after the job first runs (D3's A): about 5
   minutes.
3. **D2's B only:** the Langfuse sign-up (no card), a project, its keys in `.env`: about 15
   minutes.
4. **The pull request:** about 45 to 60 minutes (answer-v2's was estimated at 45; S9 has more code
   and a new CI job).

In all, about 1.5 to 2 hours; about 15 minutes more under D2's B.

## How it will run

1. **Approval:** D1 to D5, quoted under Approval.
2. **Build, offline** (developer, Opus 5.5): the dependencies and both locks (OB1); the port, the
   fence and `raglab.obs` (OB2); the spans, the allowlist, FastAPI's setting and the guard rule
   (OB3 to OB5); the perf mode (OB6); the collector's configuration and `make perf-smoke` (OB7,
   OB9); `make check` green. Spec pages and release metadata only: never the source of an
   instrumentation, the collector or FastAPI.
3. **Local smoke runs** of `make perf-smoke` while building (no model).
4. **CI** (OB9, OB10). The developer pushes the branch and opens the pull request as a draft, so
   pr-fast runs: the title follows the conventions, and the body says the report comes at the end.
   Then the perf job without the median threshold, the ten runs, T by the rule, the gate commit,
   THRESHOLDS.md's row.
5. **Per D2:** under B or C, the session (OB8).
6. **Docs and the ledger** (OB11, OB12).
7. **Criteria judge** (Fable 5.1, its own worktree):
   - re-runs the evidence and recomputes T from the ten logs;
   - breaks OB1 to OB7, OB9 and OB10 (OB9's locally with `make perf-smoke`) and restores each;
   - reads the pull request's checks for the [CI] parts;
   - adds a `/security-review` pass;
   - gives a verdict per criterion: met, not met, needs CI, or not applicable by D2 (OB8).
8. **Fix rounds:** at most two; a third only with your go.
9. **Report:** the pull request's body is the stage report: n of m criteria met, what needs CI,
   what was cut, the CI time used, and the Mac time used (none expected beyond the smoke runs). A
   CHANGELOG line. The pull request leaves draft; you merge by hand, with a merge commit.

Sequential subagents, unless your go asks for a Workflow. Hosted spend: none (Langfuse's Hobby plan
is free under D2's B).

**Time, labelled estimates:**

| Role | Estimate | Basis |
|---|---|---|
| Planner (this plan) | measured: 22:48 to 23:20, about 32 minutes to this commit | the progress log |
| Decisions round | about 17 minutes | S3's measured round |
| Developer | about 3 to 4 hours | S3's full stage took about 2 hours. S9 adds a dependency change with two re-locks, a new CI job, binaries with checksums, a collector's lifecycle with a postcheck, and the CI waits: each pr-fast run is about 10 to 12 minutes (607 to 697 s measured), and the ten runs about one job's length in parallel |
| Criteria judge | about 1 to 1.5 hours | S3's full judge took about 1 hour, plus a few minutes of local smoke runs |
| Your time | about 1.5 to 2 hours | above |

## Decisions needed

**D1. When S9 merges, and which release ships it.**

- **A (recommended): "Merge when ready, ship in v0.2".** S9 merges once its criteria are met,
  beside v0.2's stages, and v0.2.0's notes list it as brought forward from v0.3. What changes:
  - the main plan gets a dated note quoting your go and this answer, as the 2026-10-18 and
    2026-10-20 notes did;
  - its phase map, in the three copies, shows S9 built beside P2: `S8 --> S9` gives way to
    `S8 --> S3h`, so P3's host spike still waits for S8;
  - v0.2 grows by one stage, and P3 starts with S3h;
  - S7's pull request inherits the tracing rule and the k6 gate.
- **B: "Build now, merge after v0.2's tag".** The pull request waits. It is rebased over S4b, S6,
  S7 and S8 (at least `uv.lock`, the Makefile, pr-fast, TEST-PLAN, THRESHOLDS and the CHANGELOG),
  and T is measured again after S7 if S7's guards sit in `/ask`'s path. S9 stays a v0.3 stage and
  the phase map is unchanged.
- **C: "Approve now, build after v0.2".** No parallel build and nothing to rebase. The versions in
  this plan (OpenTelemetry 1.45.1, k6 2.3.0, the collector) are read again when the build starts.
- Whichever you choose, the pull request records it in the main plan's release slices.

**D2. The collector and Langfuse: what you sign up for.**

- **A (recommended): "Collector in CI only, no account".** The collector runs in pr-fast's perf
  job and in `make perf-smoke`, writing to a file; that proves the path and the redaction under
  load. The Langfuse pipeline is built and validated, and stays off. No account, and nothing new
  runs on your Mac outside those targets. S10 chooses the sink (Langfuse or Datadog) with the host.
  OB8 is not applicable, by D2.
- **B: "Langfuse Cloud, Hobby plan".** Your sign-up: "Hobby (Free)", "50k units / month included",
  "30 days" of data, "2 users", "No credit card required", region US, EU or Japan; the keys in
  `.env` only.
  - It adds a session target (collector up with the Langfuse pipeline, a few requests, collector
    down, postcheck): about 10 minutes, an estimate, and your look at the trace.
  - What leaves your Mac: span names, timings, model ids, token counts, chunk ids and statuses;
    never question, answer or chunk text, which the collector deletes even if captured.
- **C: "Self-hosted Langfuse, in a session".** No account, and nothing leaves your Mac. The costs:
  - the Compose deployment wants "at least 4 cores and 16 GiB of memory", and "after about 2-3
    minutes" it is ready;
  - images of a size not measured, and a Compose file pinned by image digests, to keep in the repo;
  - it must never run beside an Ollama session;
  - about 20 to 30 minutes of Mac time, an estimate, plus the first pull.

**D3. The k6 smoke in pr-fast.**

- **A (recommended): "Own parallel job; median gated at 2× the slowest of ten runs".** A `perf`
  job beside `check`, with its own timeout. k6 2.3.0 from its archive, the sha256 checked, no
  third-party action. One user; the `/ask` median gated, p95 reported; T = 2 × the largest median
  of ten report-only runs, rounded up to the next 10 ms, written before the runs.
  - pr-fast's wall time stays the `check` job's.
  - You add `perf` to the required checks, and the developer opens the pull request as a draft
    early, for the ten runs.
- **B: "A step in the check job".** No new required check, but about 1.5 to 2 more minutes (an
  estimate) on a job that took 607 to 697 s today under a 900 s timeout, with Tesseract once at
  223 s; the timeout would be raised.
- **C: "Report only until S8".** k6 runs and prints the median and p95; nothing gates until S8's
  gate map sets it. The main plan's "gating the median" moves to S8.
- Under A or B, the margin can be 1.5× instead of 2×. That is tighter, and more likely to go red
  on a slow runner.

**D4. Message content in traces: may it be captured at all?**

- **A (recommended): "Opt-in for local debugging only".** Off by default. One setting turns it on,
  honoured only where `RAGLAB_ENV` is `ci` or `local`; prod or unset refuses to start.
  - Even then, only the question after the input guards and the text of an `ok` answer, on
    raglab's pipeline span. Never the framed prompt, a chunk's text, the raw reply, the system
    text, or anything of a refused or withheld request.
  - Deleted at the collector before any Langfuse export.
  - It matches the spec's "SHOULD provide an option for users to opt in" and the main plan's demo
    rule, "redacted traces only".
- **B: "Never capture content".** No opt-in at all: the simplest and strictest, short of the
  spec's opt-in. Debugging an answer then reads the run record or the server log.
- **C: "Opt-in everywhere, redacted at the collector".** Production-shaped (S10's "PII redaction at
  the collector"), but the demo could hold users' questions in traces, against "redacted traces
  only", and the redaction would rest on S7's PII guard, which does not exist yet.

**D5. This plan:** "Approve and start (Recommended)", or changes first.

## Risks

- **The spec moves under us.** The GenAI conventions are Development, left the core repository in
  2026 and have no release. Pinning by commit keeps the build stable; a rename is a reviewed pull
  request.
- **FastAPI's own spans.** The documentation lists no attributes of its request span, and a
  FastAPI bump can change them. The allowlist drops what nobody reviewed, and the redaction test
  runs in pr-fast on every bump.
- **One global provider per process.** FastAPI uses the global provider, which OpenTelemetry sets
  once per process: the tests share one in-memory exporter, cleared per test.
- **Weight and audit surface.** Eight new runtime packages, protobuf-based, in the image too.
  `googleapis-common-protos` is inside the cooldown today.
- **Runner noise.** One pr-fast test step varied 1.3× between two runs today. 2× over the slowest
  of ten may still go red on an unusually slow machine. The ledger records any such run, and the
  flake policy is S8's.
- **S7's latency.** Guards in `/ask`'s path re-set T. The order of S7's and S9's merges decides
  who measures.
- **The perf job's set-up.** Tesseract's install took 10 s on one run and 223 s on another, which
  is why the job has its own timeout.
- **A thin `PERF_TEST_MODE` in S9.** It unlocks the stub and nothing more until S10's controls
  exist; its refusal is what S9 proves.
- **Typing and dependency checks.** pyright's strict mode on `raglab.obs` and deptry's mapping of
  the `opentelemetry` namespace packages may need configuration.
- **D2's B:** metadata leaves the Mac; the Hobby plan's behaviour at its limit is not stated.

## Approval

The message that opened S9 planning, verbatim, about 22:45 WEST on 2026-10-23. You asked, in your
own words: "can we launch more sub agents in parallel to that one to speed up the development phase
for upcoming steps into the plan?" Asked "Which planners should I launch now, next to S4b's? Each
writes its plan only, in its own worktree, and stops for your approval.", you answered: "S6 planner
(Recommended), S7 planner (Recommended), S9 planner". The S9 option told you it "doesn't depend on
S4b and needs no live sessions, but it brings a v0.3 stage forward, ahead of the v0.2 release."

That is the go to plan, not to build. Your answers to D1 to D5 go here, verbatim, with their
questions.

## Sources (read 2026-10-23)

A note on the reading: only specification pages, documentation pages, PyPI's JSON and GitHub
release metadata were read; no source code of another project.

- [OT1] OpenTelemetry, the former GenAI pages ("Moved"): https://opentelemetry.io/docs/specs/semconv/gen-ai/
- [OT2] OpenTelemetry GenAI semantic conventions, repository page (no release; schema URL "TODO"),
  `main` at `9ffc7e00c639` (2026-10-21): https://github.com/open-telemetry/semantic-conventions-genai
- [OT3] GenAI spans (status, embeddings, retrieval, content capture):
  https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-spans.md
- [OT4] Client inference (the inference span and its attributes):
  https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/client-inference.md
- [PY1] PyPI JSON for `opentelemetry-api`, `-sdk`, `-semantic-conventions`,
  `-exporter-otlp-proto-http`, `-exporter-otlp-proto-common`, `-proto`,
  `-exporter-http-transport`, `-exporter-otlp-common`, `googleapis-common-protos`, `protobuf`:
  https://pypi.org/pypi/<name>/json
- [FA1] FastAPI, OpenTelemetry: https://fastapi.tiangolo.com/advanced/opentelemetry/
- [LF1] Langfuse, OpenTelemetry: https://langfuse.com/integrations/native/opentelemetry
- [LF2] Langfuse, Docker Compose: https://langfuse.com/self-hosting/deployment/docker-compose
- [LF3] Langfuse, pricing: https://langfuse.com/pricing
- [K1] k6 v2.3.0 release (assets, `k6-v2.3.0-checksums.txt`): https://github.com/grafana/k6/releases/tag/v2.3.0
- [K2] k6, thresholds: https://grafana.com/docs/k6/latest/using-k6/thresholds/
- [C1] OpenTelemetry Collector releases (v0.162.0 to v0.163.2; assets and `.sha256` files):
  https://github.com/open-telemetry/opentelemetry-collector-releases/releases
- [C2] OpenTelemetry Collector, distributions: https://opentelemetry.io/docs/collector/distributions/
- The repository at `2b9ba60`: the main plan (S9 and S10 rows, phase map, guardrails, gate map,
  accounts, costs, open variables), the S5 and answer-v2 plans, `docs/ARCHITECTURE.md`,
  `docs/GUARDRAILS.md`, `docs/TEST-PLAN.md`, `docs/THRESHOLDS.md`, `docs/LOCAL-MODEL.md`, the
  Makefile, `.github/workflows/pr-fast.yml`, `pyproject.toml`, both locks, `src/raglab/api/`,
  `src/raglab/generate/pipeline.py`, `src/raglab/adapters/`, `src/raglab/runtime/ollama.py`,
  `scripts/api_smoke.py`, `scripts/check_architecture.py`; pr-fast runs 39974278476 and
  39949465423 (`gh run view --json jobs`).
