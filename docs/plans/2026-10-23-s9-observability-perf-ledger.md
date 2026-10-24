---
stage: S9
nodes: [S9]
---

# S9 ledger: tracing with redaction, a perf mode that prod refuses, and a k6 smoke in CI

Plan: [2026-10-23-s9-observability-perf.md](2026-10-23-s9-observability-perf.md). Branch
`feat/s9-observability-perf`, cut from `main` at `2b9ba60` (answer-v2's merge); the plan's commit
is `1f8e111`.

## Approval and decisions

The message that opened S9 planning (2026-10-23, about 22:45 WEST), verbatim, as the plan quotes
it: asked "Which planners should I launch now, next to S4b's? Each writes its plan only, in its
own worktree, and stops for your approval.", the maintainer answered "S6 planner (Recommended), S7
planner (Recommended), S9 planner".

The maintainer's answer (2026-10-23, about 23:30 WEST, through the orchestrator's question
prompt), with its question, verbatim. The question: "S9, observability and performance. Approve
with all five recommended answers? D1: merge when ready and ship in v0.2, bringing this v0.3
stage forward. D2: the OpenTelemetry collector runs in CI only, with no account. D3: k6 runs in
its own parallel pr-fast job, with the median gated at 2× the slowest of ten runs (you then add
`perf` to the required checks). D4: message content in traces is opt-in, for local debugging only.
D5: approve and start. Your time is about 1.5–2 h, with no Ollama sessions." The answer: "All five
as recommended (Recommended)".

It selects each decision's recommended option, named by its label in the plan:

| Decision | Option selected | What was done |
|---|---|---|
| D1 When S9 merges, and which release ships it | "Merge when ready, ship in v0.2" | The main plan's dated note (2026-10-23) quotes the question and the answer; the phase map, in its three copies (the main plan, `docs/ARCHITECTURE.md`, `README.md`), has `S8 --> S3h` where it had `S8 --> S9`; S9 is `wip` in the two status copies |
| D2 The collector and Langfuse | "Collector in CI only, no account" | The collector runs only inside `make perf-smoke` (pr-fast's perf job, and locally while building); the Langfuse pipeline is built and validated and stays off. OB8 is not applicable, by D2. The main plan's open variable "Langfuse cloud as an optional sink" is answered for S9 |
| D3 The k6 smoke in pr-fast | "Own parallel job; median gated at 2× the slowest of ten runs" | A `perf` job beside `check`; the maintainer adds `perf` to the required checks once it has run |
| D4 Message content in traces | "Opt-in for local debugging only" | Off by default; one setting turns it on, honoured only where `RAGLAB_ENV` is `ci` or `local` |
| D5 This plan | "Approve and start (Recommended)" | The plan's status is `approved`; the build started at 23:36 WEST on `feat/s9-observability-perf` at `1f8e111` |

## The state of `main` before the build

`make audit` is red on `main` from advisories published on 2026-10-23, before any change of S9's.
On the clean tree at `1f8e111`, `make -i audit` (both audit lines run) gave, for the main
environment, "Found 6 known vulnerabilities, ignored 43 in 3 packages": filelock 4.0.12 (one
advisory, fixed in 4.2.1), pillow 12.3.0 (two, fixed in 13.0.0) and pypdf 6.19.0 (three, fixed in
6.21.2); and for the DeepEval tool's exported lock, "Found 5 known vulnerabilities, ignored 43 in 2
packages": the same pillow and pypdf lines. (Their ids are in pip-audit's output; the privacy
check's ticket-id pattern refuses them in a committed file.) The orchestrator fixes them in a separate pull request; this branch
never touches `AUDIT_SKIP`. Here "green" means `make -k check` with only `audit` red, from exactly
these lines.

On 2026-10-24 at 03:46 WEST, `make -i audit` on this branch (after the re-lock) gave "Found 8 known
vulnerabilities, ignored 43 in 3 packages": the same lines plus two more filelock 4.0.12 advisories
(three in all, each fixed in 4.2.1), published since, as the orchestrator reported for `main`; and
for the tool's lock the same five. No line names a package S9 added.

## What was built (developer, 2026-10-23 and 2026-10-24, offline)

| Part | Where |
|---|---|
| The pins and both locks (OB1) | `pyproject.toml` (`opentelemetry-api`, `-sdk`, `-exporter-otlp-proto-http` at 1.45.1; `[tool.uv] constraint-dependencies` holds `googleapis-common-protos` at 1.75.5), `uv.lock`; `tools/deepeval-check/pyproject.toml` (the same constraint) and its `uv.lock` |
| The port and the fence (OB2) | `src/raglab/core/ports.py`: `Span`, `Tracer`, `NoopSpan`, `NoopTracer` (standard library only); `scripts/check_architecture.py` rule 7 (`opentelemetry` only in `raglab.obs`) |
| Tracing (OB3) | `src/raglab/obs/names.py` (the spec's names at `9ffc7e0`, raglab's keys, the per-scope allowlist), `src/raglab/obs/otel.py` (the tracer over the SDK, `AllowlistExporter`, the loopback endpoint check, `provider_with`, `for_endpoint`), `src/raglab/obs/traced.py` (`TracedEmbedder`, `chat_attributes`); `src/raglab/generate/pipeline.py` (the pipeline, retrieval and chat spans); `src/raglab/generate/assemble.py` (a tracer, given only by serve, wraps the embedder and reaches the pipeline) |
| Redaction and the guard rule (OB4, OB5) | the allowlist above; `src/raglab/core/reasons.py` (a guard decision's fixed key, used by the API's `_reason` and by the trace) |
| FastAPI's telemetry and the environment (OB3, OB6) | `src/raglab/api/app.py` (`telemetry()`: tracing only with a provider, operation spans, logs, metrics and auto-configuration off, only `POST /ask` traced; the lifespan's shutdown flushes; `create_app` checks the environment); `src/raglab/api/environment.py` (`RAGLAB_ENV`, `PERF_TEST_MODE`, `RAGLAB_TRACE_CONTENT`); `src/raglab/api/server.py` (the checks before anything is built, then the provider) |
| The perf stub (OB6) | `config/perf.toml`; the `perf-stub` provider in `src/raglab/evals/config.py` (read only with `perf_stub=True`, which only serve passes), `src/raglab/adapters/factory.py` and `fake.py` (FakeChat's echo under that provider name) |
| The collector (OB7) | `deploy/otel/collector.yaml`, `langfuse.yaml`, `langfuse-stand-in.yaml` |
| The k6 smoke (OB9) | `perf/smoke.js`; `scripts/perf_smoke.py`; `make perf-smoke`; pr-fast's `perf` job |
| Tests | `tests/obs/test_spans.py` (22), `tests/obs/test_redaction.py` (18), `tests/obs/test_guard_traces.py` (8), `tests/obs_support.py`; `tests/api/test_perf_mode.py` (59); `tests/unit/test_collector_config.py` (7), `tests/unit/test_perf_smoke.py` (13); additions to `tests/unit/test_architecture.py` (rule 7, 22) and `tests/unit/test_workflow_rules.py` (the perf job) |
| Docs (OB11, the parts that need no CI run) | `docs/OBSERVABILITY.md` (new), THRESHOLDS (the Performance section, T not set), TEST-PLAN (Q-01's pointer, section 10's lines), GUARDRAILS (the Logs row), COMPATIBILITY (the S9 section), ONBOARDING, the main plan's note and the phase map in three copies, CHANGELOG |

The names follow the plan's suggestions, with these additions: `src/raglab/core/reasons.py` (the
fixed-key rule in one place for the API and the trace), `src/raglab/api/environment.py`,
`src/raglab/obs/traced.py`, `tests/obs_support.py`, `tests/unit/test_perf_smoke.py`, and
`deploy/otel/langfuse-stand-in.yaml`.

## The dependencies (OB1)

PyPI's JSON, read 2026-10-23 at about 23:40 WEST; the main lock was taken at about 23:58 WEST the
same day (committed at 03:17 on 2026-10-24, `1df477c`, after a pause).

| Package | Version | Uploaded (UTC) | Main lock | Tool lock |
|---|---|---|---|---|
| `opentelemetry-api` | 1.45.1 | 2026-10-06 17:32 | already there (FastAPI); now pinned directly | already there |
| `opentelemetry-sdk` | 1.45.1 | 2026-10-06 17:32 | new | already there |
| `opentelemetry-semantic-conventions` | 0.66b1 | 2026-10-06 17:32 | new (the SDK pins it) | already there |
| `opentelemetry-exporter-otlp-proto-http` | 1.45.1 | 2026-10-06 17:32 | new | new |
| `opentelemetry-exporter-otlp-proto-common` | 1.45.1 | 2026-10-06 17:32 | new | new |
| `opentelemetry-proto` | 1.45.1 | 2026-10-06 17:32 | new | new |
| `opentelemetry-exporter-http-transport` | 0.66b1 | 2026-10-06 17:32 | new | new |
| `opentelemetry-exporter-otlp-common` | 0.66b1 | 2026-10-06 17:32 | new | new |
| `googleapis-common-protos` | 1.75.5 | 2026-09-29 19:25 | new | new |

Each is at least 17 days older than the lock. `googleapis-common-protos` 1.76.0 was uploaded on
2026-10-22 at 23:43 UTC, inside the 7-day cooldown, so a `[tool.uv] constraint-dependencies` line
holds 1.75.5 in both projects, with a comment to drop it after 2026-10-29: a path dependency's
`[tool.uv]` settings do not reach the tool's lock, which would otherwise have resolved 1.76.0. Eight
packages are new to the main lock and six to the tool's; the diffs add lines only, so no other
version moved. `uv lock --check` and `uv lock --project tools/deepeval-check --check` pass;
`make deps` passes (deptry maps the `opentelemetry` namespace without configuration).

**The spec against the package, checked at the start** (a scratch script that imports the 0.66b1
package's incubating `gen_ai` constants and compares their values, no source read): of the 22
`gen_ai` keys S9 uses or forbids, 20 are in the package with the same value; two are not,
`gen_ai.request.reasoning.level` and `gen_ai.retrieval.top_k`, both in the spec at `9ffc7e0`
(`client-inference.md` and `gen-ai-spans.md`). `error.type`, `server.address` and `server.port` are
in its stable attributes. So raglab's constants are its own, read from the spec, and the package is
not imported.

## The binaries (OB7, OB9)

Release metadata from GitHub's API (`gh api`), read 2026-10-23 at about 23:45 WEST; every archive
below was downloaded into a new, empty folder and its sha256 computed with `shasum -a 256`.

| Binary | Release (published, UTC) | Archive | Bytes | sha256 (the pin) |
|---|---|---|---|---|
| k6 | v2.3.0 (2026-09-21 15:17) | `k6-v2.3.0-linux-amd64.tar.gz` | 30847764 | `39c3117b6af817592dcd0ce4242105c0a7af10948c2a425306f0be8f7a8a8ab1`, as `k6-v2.3.0-checksums.txt` lists it |
| k6 | v2.3.0 | `k6-v2.3.0-macos-arm64.zip` | 30130878 | `b2417a3038edc5fe81dc178a889237724b595c5c9cfed875822008e46e862c7d`, as listed |
| the collector, core `otelcol` | v0.162.0 (2026-09-29 12:34) | `otelcol_0.162.0_linux_amd64.tar.gz` | 37254744 | `f99929987a915d3c6b2c9b15bc4938c5cea903a37a3f49e478024a0fa0772339`, as its `.sha256` file says |
| the collector, core `otelcol` | v0.162.0 | `otelcol_0.162.0_darwin_arm64.tar.gz` | 35177135 | `53de34c02913f54aa240861e0febf67a6839bc8ecf1bfab83a8ae7d355d30674`, as its `.sha256` file says |

The archives' members: `k6-v2.3.0-linux-amd64/k6`, `k6-v2.3.0-macos-arm64/k6`, and `otelcol` (with
a README) in both collector archives. `k6 version` printed "k6 v2.3.0 (commit/e088784614, go1.26.8,
darwin/arm64)"; `otelcol --version` "otelcol version 0.162.0".

**The collector's release: v0.162.0, a choice to review.** The plan's rule is "the newest release at
least seven days old on the day of pinning", and its choice 13 names v0.162.0 for 2026-10-23, with
its sums. The publish times: v0.163.0 at 2026-10-16 17:40 UTC, v0.163.1 at 19:39 UTC the same day,
v0.163.2 at 2026-10-21 16:22 UTC. At the pinning (2026-10-23, about 22:45 UTC) v0.163.1 was seven
days and about three hours old, so a reading of the rule by the hour would give v0.163.1; by the
calendar day the two v0.163 releases sat on the boundary, and a patch release followed within five
days. I pinned v0.162.0, as choice 13 says. The maintainer or the judge may prefer v0.163.1; the
change is the two pins and their sums in `scripts/perf_smoke.py`.

**The distribution: core `otelcol`**, the smallest official one with a macOS arm64 and a linux
amd64 archive whose own `components` output lists an OTLP receiver, a processor that deletes
attribute keys and a file exporter. The outputs, on macOS arm64:

| Distribution | Archive, macOS arm64 (linux amd64) | Receivers | Processors | Exporters |
|---|---|---|---|---|
| `otelcol-otlp` | 11382048 (11995238) | otlp | none | otlp_grpc, otlp_http |
| `otelcol-prometheus` | 34037123 (36026338) | blackbox_exporter, otlp, postgres_exporter, prometheus, prometheus_remote_write, stackdriver_exporter, yace_exporter | memory_limiter | debug, otlp_grpc, otlp_http, prometheus, prometheus_remote_write |
| `otelcol` (core) | 35177135 (37254744) | host_metrics, jaeger, kafka, nop, otlp, prometheus, zipkin | attributes, batch, filter, memory_limiter, probabilistic_sampler, resource, span | debug, file, kafka, nop, otlp_grpc, otlp_http, prometheus, prometheus_remote_write, zipkin |

Core's connectors: forward; its extensions: health_check, pprof, zpages. `otelcol-k8s` and
`otelcol-ebpf-profiler` publish no macOS arm64 archive, and `otelcol-contrib` (96729035 bytes on
macOS arm64) is not needed. The component names are this release's (`otlp_http`, not `otlphttp`).

## FastAPI's request span at 0.144.0

Read by test, not from the source: with a provider passed in FastAPI's `telemetry` dict and no
allowlist, a `POST /ask` through the TestClient recorded `server.address` and `server.port` (from
the Host header), `url.path`, `url.query` (`q=query-marker` when given), `url.scheme`,
`http.request.method`, `network.protocol.version`, `http.route`, `http.response.status_code`, and
on an escaped exception `error.type` with the exception's class name (`RuntimeError`); no user
agent, no client address, no event (logs are off). Judged harmless and kept: `http.request.method`,
`http.route`, `http.response.status_code`. Everything else is dropped by the allowlist, which is per
instrumentation scope, so the chat span's own `server.address` (the configured loopback model
server) is kept while FastAPI's, the Host header, is not. Under uvicorn (`make perf-smoke`), the
collector's file held exactly those three keys on every request span.

## Evidence per criterion (developer, 2026-10-24, macOS arm64)

Each break was made on a committed file with `PYTHONDONTWRITEBYTECODE=1`, run, and restored with
`git checkout -- <file>`; the same check was green again after the restore, and `git status --short`
was empty.

| OB | Status (before the draft pull request) | Evidence | Break (restored from git) |
|---|---|---|---|
| OB1 | met locally; CI runs `make audit` on the pull request | the table above; `uv lock --check` and its tool twin pass; `make -i audit`: no line names an S9 package (the pre-existing lines above); `make deps` passes | (1) the tool's lock restored to `main`'s (`git show main:tools/deepeval-check/uv.lock`): the audit's export line (`uv export --project tools/deepeval-check --locked ...`) "error: The lockfile at `uv.lock` needs to be updated, but `--locked` was provided.", exit 1; `make audit` itself stops earlier today, on the pre-existing lines; (2) `pyproject.toml` changed without `uv.lock` (the constraint line removed): `uv sync --locked` "error: The lockfile at `uv.lock` needs to be updated, but `--locked` was provided.", exit 1 (a first try, `opentelemetry-sdk==1.45.0`, was refused as unsatisfiable against the exporter's `>=1.45.1`); both restored, `uv sync --locked` exit 0 and `uv lock --check` "Resolved 86 packages" |
| OB2 | met | `make architecture`: 0 violations; `tests/unit/test_architecture.py` (rule 7: 20 cases of four imports in five layers, obs passes, a planted import in a copy of the real tree); `test_an_eval_run_builds_no_provider_and_makes_no_span` (a generation run with the fake model constructs no `TracerProvider`; the pipeline holds the `NoopTracer`); `test_serve_builds_a_provider_only_with_an_endpoint` | `from opentelemetry import trace` appended to `src/raglab/generate/pipeline.py` and `import opentelemetry.sdk.trace` to `src/raglab/core/ports.py`: `make architecture` "3 architecture violations": `src/raglab/core/ports.py:203: OpenTelemetry (opentelemetry.sdk.trace) is imported only in raglab.obs; elsewhere use the Tracer port of raglab.core`, `src/raglab/generate/pipeline.py:213: OpenTelemetry (opentelemetry) is imported only in raglab.obs; ...`, and rule 1's line for core; restored "0 architecture violations" |
| OB3 | met offline; COMPATIBILITY names the spec's commit and the date | `tests/obs/test_spans.py`, 22 tests through the API: one trace, the request span its root, each parent; each span's name, kind and exact attributes (FakeChat; the local adapter against its stub server with usage reported, unreported, and only the prompt count); `error.type` `unavailable`, `timeout` (FakeChat and an httpx read timeout through the adapter) and `invalid_output`, with an error status and no description; an error type outside the list refused; the endpoint loopback-only | (1) `USAGE_INPUT_TOKENS` renamed to `gen_ai.usage.prompt_tokens` in `names.py`: "1 failed, 21 passed" (the local adapter's exact attributes); (2) an unreported count recorded as 0 (`if True:` and `count or 0` in the pipeline): "3 failed, 19 passed"; restored "22 passed" |
| OB4 | met offline | `tests/obs/test_redaction.py`, 18 tests: markers in the question, a chunk, the answer, an invalid reply, an unavailable error, an escaped exception and a test-only token, tenant B's 16 canaries and the system text's first sentence: none in any exported name, attribute, event, status, link, resource or scope, in five cases; only allowlisted keys per scope; no event, link or status description; the resource is the service's name and version even with `OTEL_RESOURCE_ATTRIBUTES` and `OTEL_SERVICE_NAME` set; what raglab's code recorded before the filter holds no marker, no event and no unreviewed key; with the opt-in (`RAGLAB_ENV=local`) the question and the ok answer are on the pipeline span only and a failed request keeps none | (1) the default flipped (`return Switches(perf_mode, True)` in `environment.py`): "6 failed, 12 passed", the first failure "Left contains 2 more items, first extra item: 'raglab.ask, attribute raglab.content.question: zebra-question-7731'"; (2) the parser's exception recorded on the chat span (`get_current_span().record_exception(error)` in the pipeline): "1 failed, 17 passed": the source check finds the event, while the exported spans pass, since the allowlist drops every event; (3) the bearer token set on FastAPI's request span from the route: under `http.route` and `http.request.method` FastAPI overwrote the value when the span ended ("18 passed" both times), and under an unreviewed key (`enduser.id`) the source span held "Bearer demo" and the exported spans did not ("18 passed"); the token never reaches raglab's own code; (4) an unreviewed key with the question on the pipeline span: "6 failed, 12 passed", all in the source checks, while the exported test passed ("5 passed": the allowlist dropped it); restored "18 passed" |
| OB5 | met offline | `tests/obs/test_guard_traces.py`, 8 tests with the opt-in on: a question over 500 characters, one with a control character, an unknown tenant and no tenant leave no text (the marker or the event's own words) in any span, exported or recorded; an answer the citation guard withheld leaves none; a tenant-B chunk returned for tenant A records no id, no chunk text and no tenant-B canary (its id `B-PWD@1.0/3/1` starts with the canary `B-PWD`), only a count on the retrieval span, and the model is never called; each decision is name, stage and fixed key; every default guard's key is in `REASONS` | (1) the event's text as `raglab.guard.reason`: "6 failed, 2 passed"; (2) the retrieved ids set on the retrieval span before the guards: "1 failed, 7 passed" (the tenant-B case); restored "8 passed" |
| OB6 | met offline | `tests/api/test_perf_mode.py`, 59 tests: a 24-row table of environment, mode, opt-in and provider in `environment.switches` and in `create_app`; the process environment read by default; the perf config served with `/version` naming `perf-stub` and provenance `fake` (the real assembly over the small pack); neither switch set changes nothing; only serve reads a perf-stub config (`raglab eval`, `raglab ask` and `raglab ollama status` refuse it); the perf config has the local config's retrieval and tokens; six refusals as a subprocess of `raglab serve` that holds no port (the test holds it), each "serve failed: ..." on one line, exit 1, nothing on stdout. `make api-smoke` passes as before (the make check below) | (1) the `RAGLAB_ENV` check removed (`if False:`): "20 failed, 39 passed", among them the prod and unset rows in process and as a subprocess; (2) the check moved from `build_app` and `create_app` into the app's startup: "23 failed, 36 passed", the five subprocess rows among them (exit 3 and uvicorn's "Application startup failed"; the real-model row first reached for Ollama's `/api/tags` on loopback, refused); (3) the mode accepted under any config (`if False:` for the provider check): "6 failed, 53 passed", the local-ollama row in process and as a subprocess among them; restored "59 passed" |
| OB7 | met locally; [CI] the perf job's log | `tests/unit/test_collector_config.py`, 7 tests (the receiver on `127.0.0.1` only and OTLP over HTTP only; the local pipeline to a file; no metrics endpoint; the delete list equals raglab's content keys and the spec's Opt-In keys, first in the Langfuse pipeline; endpoint and auth from the environment, no key in any file; the stand-in replaces only the exporter; the smoke's collector environment); `tests/unit/test_perf_smoke.py` (the pins; a changed pin and a bad download refused, nothing kept; a pid file refuses the start and no earlier run's numbers are read); `make perf-smoke`: `validate` passed on the three configurations, the fixture span's content keys reached the local file and none passed the Langfuse pipeline; the postcheck passed. Without the Langfuse keys `validate` refuses `langfuse.yaml` ("exporters::otlp_http/langfuse: at least one endpoint must be specified") | (1) the receiver bound to `0.0.0.0`: "1 failed, 6 passed"; (2) `raglab.content.answer` removed from the delete list: the config test "1 failed, 6 passed", and `make perf-smoke` "perf-smoke: failed: 5 the Langfuse pipeline let content keys through: ['raglab.content.answer']"; (3) one character of k6's macOS pin changed (`b2417a30...` to `c2417a30...`): "perf-smoke: failed: k6 2.3.0: .../k6-v2.3.0-macos-arm64.zip has sha256 b2417a30..., not the pinned c2417a30...; it is not used (delete it to fetch the archive again)", nothing started, the postcheck passed; (4) the collector's stop skipped: "perf-smoke: failed: 6 the collector's port 4391 still answers; 6 the collector (pid 18026) is still running; 6 runs/tmp/perf/otelcol.pid was not removed"; the next `make perf-smoke` refused at the start ("runs/tmp/perf/otelcol.pid exists: a collector from an earlier run may still be running (pid 18026)"), and the developer stopped pid 18026 with SIGTERM and removed the pid file. That run also printed the earlier run's numbers: a bug, fixed in `752ed70` with a test |
| OB8 | not applicable, by D2 ("Collector in CI only, no account") | the Langfuse pipeline is built and validated (OB7) and never sends | |
| OB9 | met, locally and in CI (the perf job passed ten times on the pull request, below) | `perf/smoke.js` (one user, 10 warm-up and 100 gated requests, checks rate 1, no failed request, the median under T = 40 ms, p90 and p95 reported); `make perf-smoke` runs the steps in order and exits non-zero on any failure (the runs below); `tests/unit/test_workflow_rules.py` (the perf job: its own timeout, no needs, the same pinned actions, model and Tesseract steps as `check`, `make perf-smoke` offline last; zizmor: "No findings to report") | (1) a 500 planted in the `/ask` route for the question with `perf-marker-03`: k6 "✗ 'rate==1' rate=80.00%", "✗ 'rate==0' rate=20.00%" (88 of 110 checks), "3 k6 exited with 99", and the trace check "22 traces lack a span"; restored. (2) With T set (`657797d`), a delay of 2 × T, `sleep(0.080)` before the pipeline in `ask_locked`: k6 "✗ 'med<40' med=111.27ms" (checks and failures still held), "perf-smoke: failed: 3 k6 exited with 99 (99: a threshold was crossed)"; restored, and the next run passed with "✓ 'med<40' med=5.4ms" |
| OB10 | met | the ten runs and the arithmetic below (OB10's section); THRESHOLDS.md's row (`median < 40 ms`, the ten attempts with their medians and p95s, the rule, the reason, the provenance: the fake model, GitHub's runner; "not Q-01"); `perf/smoke.js` `MEDIAN_THRESHOLD_MS = 40`; `test_the_scripts_threshold_equals_the_thresholds_cell` passes | the criteria judge's: the script's T edited alone, and T recomputed from the ten logs |
| OB11 | met | the docs above, and since T: OBSERVABILITY's gate, TEST-PLAN's perf line, COMPATIBILITY's CI line, ONBOARDING's median break (its "Not testable yet" row removed), CHANGELOG; ARCHITECTURE and README show S9 `done` (`0ecea82`); `tests/unit/test_test_plan.py`, `test_diagram.py`, `test_onboarding.py`, `test_readme.py`, `test_repo_docs.py` pass | |
| OB12 | local: green but for the pre-existing audit lines (the make check sections below); [CI] the `check` job stops at `make audit` on the same pre-existing lines, so its later steps wait for the audit pull request | the pull request's first run (below) | |

## Local runs of `make perf-smoke` (the Mac, not GitHub's runner)

Each preceded by `make ollama-status` ("pid": null, "port_open": false, "loaded": null). The
medians are the Mac's, for the record only: T comes from the ten runs on GitHub's runner.

| When (WEST) | Tree | Result | Time | /ask median, p95 (Mac) |
|---|---|---|---|---|
| 2026-10-24 03:26 | before `8bfc90c`, uncommitted | passed | 19.68 s real | 5.38 ms, 5.92 ms |
| between the two | the breaks of OB7 and OB9 above | failed as expected | | |
| after the commit of `752ed70` (03:43) | `752ed70` | passed | 17.75 s real | 5.29 ms, 5.79 ms |
| 2026-10-24, after `657797d` (T set) | OB9's median break | failed as expected (above) | | 111.27 ms, 118.95 ms |
| right after it | `657797d` | passed, "✓ 'med<40' med=5.4ms" | 17.66 s real | 5.41 ms, 6.08 ms |

The first run fetched k6 and the collector into `~/.cache/raglab/tools` (30130878 and 35177135
bytes); every later run checked both sums from the cache.

## Developer choices (for the review)

Five of them were put to the maintainer through the orchestrator at stop 1 and confirmed on
2026-10-24, as decided ("Your five items to confirm are fine as you decided", the orchestrator's
message): 1 and 3 together (the provider handed to FastAPI, only `POST /ask` traced), 4 (content
only for an ok answer), 9 (the constraint, dropped after 2026-10-29), 10 (the collector v0.162.0)
and 11 (the ports). Each carries its reason below.

1. **An explicit provider, never the global one** (confirmed). FastAPI takes the provider in its
   `telemetry` dict ("You can also pass a provider directly"), so `raglab serve` hands it the same
   provider the pipeline's tracer uses, and the tests give each app its own: the request span is
   still the root and the pipeline span its child (`test_one_ask_is_one_trace...`). No code sets the
   global provider. The reason: nothing is shared between tests or leaks into a process that never
   asked for tracing, and an eval run cannot pick up a provider by accident. This replaces the
   plan's OB4 wording "the global provider installed once per test session ... cleared per test",
   and removes its risk "one global provider per process".
2. **The allowlist is per instrumentation scope.** raglab's spans keep raglab's reviewed keys,
   FastAPI's the three HTTP keys, any other scope none; so the chat span's `server.address` (the
   configured model server) stays while FastAPI's (the Host header) goes.
3. **FastAPI traces `POST /ask` only** (its `exclude` setting; confirmed): health checks, the page
   and unknown paths make no span. The reason: the plan's span table names one request span, the
   API smoke's and the perf smoke's health polling would otherwise fill the traces, and an unknown
   path never becomes a span name.
4. **Content only for an ok answer** (confirmed). D4's option says "never ... anything of a refused
   or withheld request"; I read a request whose model failed (unavailable, invalid output) as
   withheld too, so the opt-in records the question and the answer of an ok answer only. The
   reason: the stricter reading keeps the rule one sentence long and leaves no failure path that
   records the question.
5. **The tenant only once every input guard has passed**, slightly stricter than "once the tenant
   guard has passed", which would depend on the guards' order.
6. **Retrieval's data source is `policy-pack`**, the one index; the retrieval span is `retrieval
   policy-pack`, kind client, as the spec says.
7. **The chat span also sets `gen_ai.prompt.name`** (the current prompt's version, `answer-v1`),
   conditionally required by the spec "when a named prompt template is used", and `gen_ai.output.type`
   `json` only when the model's config sends a JSON schema.
8. **The guard rule's keys live in `raglab.core.reasons`**, used by the API's `_reason` and by the
   trace, so the two cannot drift; S7 adds its guards' keys there and in `REASONS`.
9. **`googleapis-common-protos` held by a `constraint-dependencies` line in both projects**
   (confirmed; above). The reason: 1.76.0 is inside the 7-day cooldown, and the constraint keeps a
   re-lock (a merge of `main`, another stage's dependency) from picking it up before 2026-10-29.
   **A follow-up:** after 2026-10-29, drop the line from `pyproject.toml` and
   `tools/deepeval-check/pyproject.toml` and re-lock both projects, in a pull request of its own or
   with the next dependency change.
10. **The collector v0.162.0** (confirmed, per the plan's choice 13; above). The reason: the plan
    names it, with its sums, and v0.163.0 and v0.163.1 sat on the cooldown's boundary when it was
    pinned, followed within five days by a patch release.
11. **Ports 8791 (server) and 4391 (collector)** (confirmed), not the defaults (8000 for `raglab
    serve`, 4318 for OTLP/HTTP), because other builds and the maintainer share this Mac and the API
    smoke uses 8765; `PERF_PORT` and `PERF_OTLP_PORT` change them.
12. **The Langfuse check runs in every `make perf-smoke`** with a file standing in for Langfuse: the
    exporter to Langfuse is defined, used by no pipeline, and pointed at a loopback placeholder.
13. **k6's own summary export**, not `handleSummary` (no jslib fetch at run time), with
    `--no-usage-report` and `--include-system-env-vars=false`; `ask_duration`, a trend of the gated
    requests only, carries the median.
14. **No `/security-review` by the developer**: the plan gives it to the criteria judge (choice 14).

## Notes

- The build paused from about 00:50 to 03:15 WEST on 2026-10-24 (a usage limit); the work in the
  worktree was kept as it was.
- The command guard refused several compound shell lines (a heredoc that also ran a script, a
  binary named through a shell variable, `git -C`); each was split into plain steps or written as a
  file. None was routed around.
- During OB6's breaks the subprocess tests ran `raglab serve` with the check removed, so it
  assembled the real corpus with the cached embedder (`HF_HUB_OFFLINE=1`), and one reached for
  Ollama's port on loopback, which refused: Ollama was down throughout (`make ollama-status`).

## make -k check at stop 1

On `2225bdf` (this ledger but this section), `/usr/bin/time -p make -k check`: 210.68 s real
(198.79 s user), the tests 170.63 s, against "about 3.5 to 4 minutes" before S9. Every target
passed but `audit`, which failed on the pre-existing lines only (above; none names a package S9
added):

    267 files already formatted                                   format
    All checks passed!                                            lint
    0 errors, 0 warnings, 0 informations                          types
    Success! No dependency issues found.                          deps (deptry; vulture silent)
    Found 8 known vulnerabilities, ignored 43 in 3 packages       audit: filelock 4.0.12 (3),
                                                                  pillow 12.3.0 (2), pypdf 6.19.0 (3)
    (bandit and semgrep silent)                                   sast
    No findings to report. Good job!                              workflows
    no leaks found, no leaks found                                secrets
    0 hits across 388 files (42 rules)                            privacy
    0 architecture violations in src/raglab                       architecture
    check-dataset: datasets/golden.v1.jsonl passes (34 retrieval questions, 40 behaviour cases, sha256 5f8cdaf18783)
    ========== 1531 passed, 2 deselected, 1 warning in 170.63s (0:02:50) ===========
    retrieval no-regression gate (22 questions): recall@5 0.682 (n 22) passes: the threshold is the baseline 0.682 (20261019T180502Z-retrieval-dense-dev-97011a7) minus one question (1/22), 0.636
    api-smoke: passed

`make audit` stops at its first line's failure, so the tool's audit line ran separately with
`make -i audit` (above: the five pillow and pypdf lines). `make perf-smoke` is not in `make check`;
its last local run passed (above).

## What the draft pull request's first run must show

- **`check`**: every step green but `make audit` (the pre-existing lines, until the orchestrator's
  audit pull request merges), the tests and the API smoke passing; its time against the 607 to
  697 s of 2026-10-23.
- **`perf`**, its first run on linux amd64: the two fetches printing `ok   k6 2.3.0:
  k6-v2.3.0-linux-amd64.tar.gz, sha256 39c3117b... (the pin)` and `ok   otelcol 0.162.0:
  otelcol_0.162.0_linux_amd64.tar.gz, sha256 f99929987a91... (the pin)` (the linux pins and member
  names were checked by download on the Mac, never yet run by the script), `validate` on the three
  configurations, the steps 1 to 6 `ok`, the line `perf-smoke: /ask median ... ms, p90 ..., p95
  ... ms, ...; the median's threshold T: not set`, the step summary's table, and `perf-smoke:
  passed`; its time against the plan's estimate of 3 to 6 minutes.
- **`conventions`**: the title, the branch and this CHANGELOG line.

Then OB10, by the rule: ten report-only runs of the perf job at one commit, all kept; each run's
median and p95 copied from its `perf-smoke: /ask median ...` line with its run id; T = 2 × the
largest median, rounded up to the next 10 ms, written in `perf/smoke.js` (`MEDIAN_THRESHOLD_MS`)
and THRESHOLDS.md's cell (`median < T ms`, with the ten run ids, medians and p95s), which the test
holds equal; then S9 `done` in the phase map, ONBOARDING's last row moved, and the median break
(a delay of 2 × T in the `/ask` route) run locally.

## The pull request's first run, and OB10 (2026-10-24)

The orchestrator pushed the branch at `12f8e70` and opened draft pull request #27. pr-fast run
40074154534 (event `pull_request`, head `12f8e70`), its first attempt, read through GitHub's jobs
API and each job's own log:

- **`conventions`**: success, 7 s.
- **`check`**: failure at its step 16, "Vulnerable dependencies", after 58 s; steps 1 to 15 passed
  (the dataset check, the model, Format, Lint, Types, Dependencies and dead code among them) and 17
  to 25 were skipped. Its audit printed "Found 8 known vulnerabilities, ignored 43 in 3 packages",
  the eight pre-existing lines (filelock 4.0.12 three times, pillow 12.3.0 twice, pypdf 6.19.0
  three times), none of an S9 package. The skipped steps (SAST to the API smoke) ran locally
  (`make -k check`, below) and run in CI once the orchestrator's audit pull request has merged and
  this branch has merged `main`.
- **`perf`**: success, 72 s. Its log: "ok   k6 2.3.0: k6-v2.3.0-linux-amd64.tar.gz, sha256
  39c3117b6af817592dcd0ce4242105c0a7af10948c2a425306f0be8f7a8a8ab1 (the pin)", "ok   otelcol
  0.162.0: otelcol_0.162.0_linux_amd64.tar.gz, sha256
  f99929987a915d3c6b2c9b15bc4938c5cea903a37a3f49e478024a0fa0772339 (the pin)", `validate` on the
  three configurations, steps 1 to 6 `ok` (110 traces of /ask with their five spans), "perf-smoke:
  passed". The linux pins and archive members, checked by download on the Mac, ran for the first
  time here.

**The ten report-only runs (OB10).** The orchestrator re-ran the perf job of that run at the same
commit, attempts 1 to 10, and kept every one; all ten succeeded. I read each attempt's job through
GitHub's API (head `12f8e70`, its attempt number, conclusion success, name `perf`) and its own log
through the job-logs API: each log has one "perf-smoke: passed" line and the median line below,
the same values as the orchestrator's list. (`gh run view --job <id> --log` printed the tenth
attempt's log for every job id, so it was not used.) The jobs' 12-digit ids are not written here:
the privacy check's pattern refuses them, and the run id with the attempt names each job.

| Run 40074154534, attempt | /ask median | p95 | p90 | min | max | perf job |
|---|---|---|---|---|---|---|
| 1 | 15.13 ms | 17.52 ms | 17.35 ms | 13.00 ms | 38.34 ms | 72 s |
| 2 | 14.27 ms | 16.75 ms | 16.45 ms | 12.22 ms | 30.88 ms | 85 s |
| 3 | 14.50 ms | 16.71 ms | 16.46 ms | 12.25 ms | 33.52 ms | 84 s |
| 4 | 14.34 ms | 16.70 ms | 16.47 ms | 12.41 ms | 34.72 ms | 70 s |
| 5 | 8.01 ms | 9.39 ms | 8.91 ms | 6.83 ms | 18.27 ms | 55 s |
| 6 | 15.38 ms | 17.69 ms | 17.46 ms | 12.71 ms | 34.23 ms | 75 s |
| 7 | 14.73 ms | 17.12 ms | 16.97 ms | 12.60 ms | 29.27 ms | 78 s |
| 8 | 13.85 ms | 16.50 ms | 15.95 ms | 11.52 ms | 37.33 ms | 83 s |
| 9 | 14.42 ms | 16.87 ms | 16.47 ms | 12.29 ms | 40.18 ms | 77 s |
| 10 | 12.24 ms | 13.73 ms | 13.68 ms | 9.93 ms | 14.18 ms | 74 s |

**T, by the rule written before the runs:** the largest of the ten medians is attempt 6's, 15.38
ms; 2 × 15.38 ms = 30.76 ms; rounded up to the next 10 ms, **T = 40 ms**. The medians span 8.01 to
15.38 ms (a factor of 1.92 between the fastest runner and the slowest). T is in `perf/smoke.js`
(`MEDIAN_THRESHOLD_MS = 40`) and THRESHOLDS.md's cell (`median < 40 ms`, with the ten attempts,
their medians and p95s, the rule, the reason and the provenance), committed in `657797d`; the test
holds them equal. The perf job took 55 to 85 s per attempt, under the plan's estimate of 3 to 6
minutes, and the `check` job's 900 s budget is untouched by it. OB9's median break then ran
locally (above): "✗ 'med<40' med=111.27ms", k6's exit 99. S9 is `done` in the phase map
(`0ecea82`).

The maintainer adds `perf` to `main`'s required checks (D3), through the orchestrator.
