---
stage: S3
nodes: [S3]
---

# S3 ledger: generation, the local live run, the API, the page and the container

Plan: [2026-10-16-s3-generation.md](2026-10-16-s3-generation.md).

## Approval and added scope

The user's answer, verbatim (quoted in the plan): "Approve and start".

**AC15, added by the user's message on 2026-10-18** (relayed by the orchestrator; the approved plan
stays as it is). The source of this scope, verbatim: "you can downlaod and install them as long as
you add safe evals against the usage and ensure it will be down once the project is not online so
the rest of the mac is fine to use and do the other work".

AC15 as built: the local model server runs for one session only, never as a resident service
(`make ollama-up`, `ollama-down`, `ollama-status`, `eval-local`); loopback only, one model, one
request, a context length from config, a short keep-alive and an explicit unload; a preflight
that refuses low memory, a registered launchd or brew service, or a port held by another process;
a per-request timeout, a max-tokens cap and a wall-clock cap that marks a run partial; and a
postcheck after every session (ended normally, by an error, Ctrl-C, SIGTERM or SIGHUP; a
SIGKILL cannot be caught) that fails loudly unless the port is closed and no ollama process
(so no model) is left. Lab practice: production runs the model on a managed endpoint, not on a
laptop (docs/LOCAL-MODEL.md).

Ollama 0.40.6 was installed (Homebrew formula, CLI only) and the generator pulled by the
orchestrator, not by the developer; its digest `d1e17d7dabacb401dec6440b4ec987ea053b9568b01f89fb3d54f8b2e71397be`
and size (19072744624 bytes) were read from the server's /api/tags at pull time.

## What was built (developer, 2026-10-18)

| Part | Where |
|---|---|
| Ports and types | `src/raglab/core/ports.py`: ChatModel, Guardrail (check_input, check_retrieved, check_output); `core/types.py`: Answer (text, cited_ids, label, conflict, status), Status (ok, refused, blocked, unavailable, invalid_output), Conflict, GuardEvent, ChatRequest, ChatReply, ChatUnavailable, ChatTimeout. Standard library only |
| Prompt | `src/raglab/generate/prompts/answer_v1.py`: VERSION `answer-v1`, the system prompt, the question and chunk frames (a chunk's text cannot close its frame), the answer schema, a fingerprint, and a strict parser that never repairs |
| Pipeline | `src/raglab/generate/pipeline.py` (input guards, retrieve, retrieved guards, prompt, model, parse, output guards); `generate/assemble.py` builds it from a generation config |
| Guards | `src/raglab/guard/`: NoopGuardrail, InputLimits (500 characters, control and invisible characters), TenantGuard (no tenant, `shared`, unknown, caller not entitled; a chunk of another tenant after retrieval), CitationValidator; docs/GUARDRAILS.md |
| Adapters | `adapters/fake.py`: FakeChat (echo or script); `adapters/openai_compat.py` (httpx; loopback only; tag and digest checked at start against /api/tags; server version from /api/version; `response_format` and `reasoning_effort` sent only when the config says so); `adapters/factory.py`: `chat()` builds FakeChat only on provider fake |
| Architecture | `scripts/check_architecture.py`: rule 4 now "the fake adapters are imported only by raglab.adapters.factory"; rule 5: httpx (and aiohttp, urllib3) only in adapters, FastAPI, Starlette and uvicorn only in `raglab.api` |
| Suite and record | `evals/generation.py` (N trials, per-trial seed, wall-clock cap, partial), `evals/generation_record.py` (checks, the abstention oracle, results, report), `evals/metrics.wilson_interval`; `schemas/run-record.v1.json` extended additively; `evals/record.validate` by suite; `compare` refuses generation runs; `publish` indexes the generator; `ingest/answer_key.py` reads the canaries |
| Configs and data | `config/fake.toml`, `config/local-ollama.toml`; `datasets/probes.s3.jsonl` (P-01 F-32 tenant A, P-02 F-32 tenant B, P-03 F-40 tenant B) |
| API and page | `src/raglab/api/app.py` (/healthz, /version, /ask; 401, 403, 400, 413, 502, 503; security headers on every response, a 500 included since fix round 1; OpenAPI pages off), `api/server.py`; `src/raglab/web/` (index.html, app.js, app.css) |
| CLI | `raglab ask`, `raglab serve`, `raglab eval --suite generation`, `raglab ollama up|down|status|session` |
| Local model | `src/raglab/runtime/ollama.py` (Host, Session: preflight, up, down, postcheck, run); docs/LOCAL-MODEL.md |
| CI | `scripts/api_smoke.py`, `make api-smoke` (in `make check`), pr-fast step "API smoke (offline, fake model)" |
| Container | `deploy/Dockerfile`, `.dockerignore` (an allow list), `deploy/zap/rules.tsv`, `deploy/zap/scan.sh`; `make container`, `container-run`, `zap` |
| Docs | docs/GUARDRAILS.md, docs/LOCAL-MODEL.md, docs/COMPATIBILITY.md; TEST-PLAN R1, R4, R7 and the traceability Test column; THRESHOLDS generation rows; ARCHITECTURE and README: S3 `done`; ONBOARDING; CONTRIBUTING design rules |
| Dependencies | runtime `fastapi==0.144.0`, `starlette==1.8.0` (imported directly, so declared), `uvicorn==0.54.0`, `httpx==0.28.1` (was transitive); `uv.lock` updated with uv; pip-audit, deptry and vulture clean. Images by digest: `python:3.13-slim@sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f` (Python 3.13.16, Debian 13.7), `ghcr.io/zaproxy/zaproxy:stable@sha256:5ccfff9a411743ab2615136a2edd7416bec9ce41572fa94e935df38c14adb2b6` (ZAP 2.17.0), both multi-arch index digests |

## Evidence per criterion (developer, 2026-10-18, macOS arm64, Apple M4 Pro, 48 GiB)

`make check` exits 0 at the final commit: the count and the tail are in the last section; the gate printed
"recall@5 0.644 (n 22) passes: the threshold is the baseline 0.644
(20261006T172928Z-retrieval-dense-dev-5f1d3a0) minus one question (1/22), 0.598" (unchanged from
S2: the retrieval configs resolve as before); then "api-smoke: passed". Each break below was made
on a committed file with `PYTHONDONTWRITEBYTECODE=1`, run, and restored with `git checkout`, and
the same check was green again after the restore (the git status was clean at the end).

| AC | Status | Evidence | Break (restored from git) |
|---|---|---|---|
| AC1 | met | `make architecture`: "0 architecture violations in src/raglab"; `tests/generation/test_answer_types.py` (8 tests: the ports are Protocols in core, the five Answer fields, a withheld answer carries no text, FakeChat in adapters/fake.py) | a planted `from raglab.adapters.fake import FakeChat` in `generate/pipeline.py`: "src/raglab/generate/pipeline.py:18: raglab.adapters.fake is built only by raglab.adapters.factory (provider fake) and the unit tests; no other module imports it" |
| AC2 | met | `tests/generation/test_prompt_snapshot.py`: the assembled prompt equals `tests/snapshots/answer-v1.txt`; the fingerprint of `answer-v1` is recorded (96f42d9b...); a chunk holding `</chunk>`, `</CHUNK>` and `</question>` stays in one frame; no developer comments in the text | "1. Use only the passages." made "passage": 2 failed (snapshot, and "changed without a new VERSION") |
| AC3 | met | `tests/generation/test_citation_validator.py`: a scripted FakeChat citing B-PWD@1.0/3/1 for a tenant A question is blocked (abstain, status blocked, the event names the id); a conflict id not retrieved is blocked; 120 random citation sets (6 small questions, each tenant, 10 each): every ok answer's citations are retrieved | `check_output` returns None: 4 failed, including the scripted unretrieved citation |
| AC4 | met | `tests/generation/test_fallback_contract.py` (19 tests, the real adapter against an in-process stub of Ollama, httpx.MockTransport, no socket): read and connect timeouts, connection errors, HTTP 500, 503, 404, a non-JSON body, an empty completion, prose, a fenced reply, an unknown label, an empty answer and missing fields each give unavailable or invalid_output with no text; a run record counts them (`status_counts` unavailable 2, invalid_output 3); a timeout or the wall-clock cap marks the run partial | the parser made to strip a code fence: 1 failed (the fenced reply became an answer) |
| AC5 | met | `tests/contract/test_chat_contract.py`: the shared contract against the stub (pr-fast) and, marker `live`, against Ollama 0.40.6 in `make eval-local`: "1 passed, 13 deselected in 29.78s" at `3b66ea3` (an earlier commit's file had 12 deselected; correction 5) (the reply parsed into an Answer, citations among the given ids, no reasoning text, tokens reported). A digest mismatch, an unpulled tag, a server that is down and a non-loopback URL refuse to start; the committed config with its digest replaced by the placeholder refuses to run ("refuses to start until the tag's digest is pinned"), and `raglab eval --suite generation` on it exits 1. Before the digest was pinned (commit `a3494f7`) the committed config itself refused | (the digest-mismatch and placeholder tests are the break) |
| AC6 | met | `tests/generation/test_input_guards.py` and `tests/api/test_api.py`: over 500 characters, empty, U+0000, U+001B, U+202E, U+200B, U+E000, U+000D, U+007F refused (400) with 0 retriever calls; no tenant, null, empty, `shared`, unknown, a list, and the spoof (tenant-a-only token asking as tenant B) refused (403) with 0 retriever calls; no or unknown token 401 | the caller check in `guard/tenant.py` removed: 4 failed, among them `test_a_tenant_the_caller_may_not_use_is_403_and_never_retrieved[spoofed]` |
| AC7 | met | `tests/e2e/test_e2e_fake.py`: the app built from config/fake.toml (real pack, real embedder, FakeChat echoing every chunk), all 22 dev questions asked as each tenant: no tenant B canary (all 16) in a tenant A answer or its citations, no tenant A canary (all 47) in a tenant B answer; positive control: each tenant's own canaries do appear | every tenant filter off (the store mask, both `check_visible` calls, the retrieved guard): 2 failed (both directions). Removing one layer alone (only the retrieved guard, say) does not leak, by design: the S2 store filter masks before ranking and `check_visible` checks on the way out, so the e2e test fails only when all of them go; each layer has its own test (S2 `test_tenant_filter.py`; `test_input_guards.py::test_another_tenants_chunk_after_retrieval_blocks_the_answer_before_the_model`) |
| AC8 | met | `tests/retrieval/test_run_record.py`: the three committed S2 runs validate by name; a generation run validates; refused: a case without label, status or checks, a citation or conflict id not retrieved, text on a withheld answer, an unknown label, retrieval fields on a probe, edited checks, a missing trial, generation fields in a retrieval run, a retrieval case without recall, a tenant B chunk cited by a tenant A case | the unretrieved-citation check in `record.generation_problems` disabled: 2 failed |
| AC9 | met | the live run below, published: `runs/published/20261018T162604Z-generation-local-ollama-dev-3b66ea3`, provenance local, git clean at `3b66ea3`, not partial, the model tag and digest, the prompt version and every report field; `raglab publish` validated it, ran the privacy check at its published path and published it; the reset-attempts abstention count and pass^3 below are copied from the record | n/a (the publish refusals are tested in `tests/unit/test_published_allowlist_scope.py`) |
| AC10 | met | `tests/api/test_api.py`, `tests/api/test_page.py`, `tests/unit/test_container.py`; `make container` built `raglab:local` (793,364,086 bytes at `d897052`); the container runs as uid 10001 with the fake model and answers `/healthz` (below) | `frame-ancestors 'none'` dropped from the CSP: 10 failed |
| AC11 | met | `make zap`: "FAIL-NEW: 0 FAIL-INPROG: 0 WARN-NEW: 0 WARN-INPROG: 0 INFO: 0 IGNORE: 3 PASS: 64", 6 URLs; the three ignored rules are Informational, each with its reason in `deploy/zap/rules.tsv` | without rules.tsv the same three Informational alerts count as WARN: the judge's scan with the pinned image read "WARN-NEW: 3 ... PASS: 64" (correction 3; the developer's first scan's "0 WARN, 66 PASS" was with ZAP's defaults before the pin was used and is withdrawn). Rerun after fix round 1 (no chmod 777): "FAIL-NEW: 0 ... WARN-NEW: 0 ... IGNORE: 3 PASS: 64", 6 URLs |
| AC12 | needs CI; local evidence met | pr-fast step "API smoke (offline, fake model)" after the model fetch and the tests, `HF_HUB_OFFLINE=1`, `make api-smoke`; `tests/unit/test_workflow_rules.py::test_pr_fast_smoke_tests_the_api_offline_after_the_tests`; zizmor: no findings; locally four `ok` lines and "api-smoke: passed" | the step's `run` changed: 1 failed |
| AC13 | met | `make check` as above (ruff, pyright strict, deptry, vulture, pip-audit, bandit, semgrep, zizmor, gitleaks, privacy, architecture); `tests/unit/test_architecture.py`: the factory may import the fakes, any other module may not (a planted import in a copy of the real tree fails), httpx outside adapters and FastAPI outside api fail | see AC1 |
| AC14 | met; S3 `done` | TEST-PLAN R1, R4 and R7 name their tests (`tests/unit/test_test_plan.py` now requires it); traceability Test column for R-02, R-21, R-13 and R-16; docs/GUARDRAILS.md; docs/COMPATIBILITY.md "Tested against nemotron-3.5-lightning:30b-a3b-mlx@d1e17d7d... on Ollama 0.40.6 on 2026-10-18"; ARCHITECTURE and README S3 `done` (AC9 published); CHANGELOG line; this ledger | n/a |
| AC15 | met (added by the user, 2026-10-18) | `tests/unit/test_ollama_session.py` (22 tests, a fake host: the environment, the model size from its manifest, low memory, a registered service, a held port, no binary, an unpulled model, an old server, unload and stop, a server that will not stop, a leftover process, a session that succeeds, fails or is interrupted, a failed postcheck, the EPERM fallback); the four `make eval-local` sessions and the probe session, each ending "postcheck passed: port closed, no ollama process, no model loaded" (each ended normally). SIGTERM and SIGHUP (judge S3-J2): the evidence is the subprocess unit test with the fake host (`test_a_terminated_session_still_stops_the_server_and_runs_the_postcheck`); no live session has been ended by a signal, and the live demonstration is pending the judge. The executable match (S3-J5), the asked port (S3-J3) and the flushed lines (S3-J7): unit tests | with real OS reads, no server started: margin 100 GiB: "not enough memory: 26.7 GiB available, 117.8 GiB needed (model 17.8 GiB + margin 100 GiB)", exit 1; port 11434 held by `python3 -m http.server`: "127.0.0.1:11434 is already held by a process this project did not start", exit 1; `pgrep` found no ollama after either |

## The live run (AC9)

`make eval-local` at `3b66ea3` (after fix round 1) on 2026-10-18, 16:25 to 16:28 UTC, at the
model card's sampling settings (the user's decision 3, below), then `raglab publish`. Every
number here is copied from
`runs/published/20261018T162604Z-generation-local-ollama-dev-3b66ea3/manifest.json` and its
report, or from the session's output.

**Settings (manifest).** nemotron-3.5-lightning:30b-a3b-mlx at digest d1e17d7d... on Ollama
0.40.6, provider openai-compat, base URL http://127.0.0.1:11434; temperature 1.0, top_p 0.95,
max_tokens 1024, timeout_s 120, response_format none, extra `reasoning_effort: none`; prompt
answer-v1 (sha256 96f42d9b...); guards tenant, input-limits, citations; dense retriever, k 5,
chunks 1,200; 3 trials, seed 20261018 (trial t uses seed + t - 1); Wilson intervals at 95%,
n = cases; ollama host 127.0.0.1:11434, keep_alive 2m, max_loaded_models 1, num_parallel 1,
context_length 8192. 22 dev questions and 3 probes, 75 case-trials, 110.896 s; provenance local;
git clean; partial false.

| Check (no judge) | Rate | 95% interval | n (cases) |
|---|---|---|---|
| status_ok | 0.973 | 0.824 to 0.996 | 25 |
| model_citations_retrieved | 0.973 | 0.824 to 0.996 | 25 |
| probe_abstention | 0.000 | 0.000 to 0.561 | 3 |
| citation_hit | 0.742 | 0.534 to 0.879 | 22 |
| pass^3 | 0.640 | 0.445 to 0.798 | 25 |

- Status counts: ok 73, refused 0, blocked 2, unavailable 0, invalid_output 0.
- Label agreement: 24 of 25 cases gave the same label in every trial.
- **The reset-attempts abstention count (F-32): P-01 (tenant A) 0 of 3, P-02 (tenant B) 0 of 3**;
  P-03 (F-40, tenant B) 0 of 3.
- Latency p50 1,378.811 ms, p95 2,434.308 ms (n 75); tokens 78,966 prompt and 7,717 completion
  (all 75 case-trials reported them).
- What pass^3 measures here (the report says it): a case passes only when all 3 trials pass, each
  with its own seed at temperature 1.0, so it measures consistency while the model samples, not
  correctness.

Reading (not judged; a citation hit is not correctness):

- **model_citations_retrieved now moves (judge S3-J1).** R-Q25 trials 1 and 3 cited document ids
  (`A-DEVICE`, `A-EXC`, `A-FAQ`) instead of chunk ids; the validator withheld them (status
  blocked), and the check reads its event, so 0.973 here is the model's reply, and it equals
  status_ok because those two blocked trials are the only trials that are not ok. R-Q25 is also
  the one case whose label changed across trials.
- **The probes all failed.** Every probe trial was labelled `answer`: P-01 "User passwords expire
  every 60 days" twice, and once "The documents do not specify a daily limit for password reset
  attempts" (no value, check b passes, but labelled `answer`, check a fails); P-02 the lockout
  rule or the NCSC range; P-03 "within 24 hours" (tenant B's factor revocation, not a leaver
  rule). No tenant A canary appeared in a tenant B answer (check c).
- **No case is byte-identical across its three trials** at temperature 1.0 (0 of 25).
- Memory available before the session (preflight): 30.8 GiB; after: 36.7 GiB. Live contract test
  29.78 s ("1 passed, 13 deselected"); the suite 110.896 s, about 37.0 s per trial of 25 cases;
  the whole session 2 min 52.1 s.
- Postcheck: "postcheck passed: port closed, no ollama process, no model loaded"; afterwards
  `pgrep -fl ollama` found nothing and `lsof -iTCP:11434 -sTCP:LISTEN` found nothing.
- **Published.** `raglab publish 20261018T162604Z-generation-local-ollama-dev-3b66ea3`:
  "published: .../runs/published/20261018T162604Z-generation-local-ollama-dev-3b66ea3"; the
  privacy check ran on the files at their published path (decision 1), and no answer key
  `answer_must_not_contain` string is in them (also checked for every published run by
  `tests/retrieval/test_publish.py::test_the_committed_runs_are_valid_local_dev_runs_with_a_current_baseline`).

**Plan correction (2026-10-18).** The plan's check 3 read: "an abstention probe has label
`abstain`, and none of its `must_not_appear` strings appears". In corpus/answer-key.yaml,
`must_not_appear` (scope `corpus` for F-32, `tenant-b` for F-40) is a guarantee about the
documents (those phrases are absent from the pack, which is what makes it an omission), not a ban
on words in the answer: an honest abstention ("The documents do not say how many password reset
attempts...") contains "reset attempts" and would fail by construction. The orchestrator replaced
it, and the run above is scored by the named abstention oracle (`abstention_oracle`, exported by
`raglab.evals.generation`): (a) label `abstain`, (b) no policy value in the text, following R-18's
acceptance ("omission questions produce no number"), and (c) for F-40, no tenant A canary from the
answer key in the tenant B answer (R-16). Tests: `tests/generation/test_abstention_oracle.py` (an
honest abstention that names the topic passes; one that states a number fails; reference numbers
such as "section 4.4" are not values; number words are not counted, a stated limit). The approved
plan file is unchanged.

**Superseded runs (not published, kept in this clone's `runs/tmp/` as history).**

| Run | When, commit | Settings | status_ok | citation_hit | probe_abstention | pass^3 | Label agreement | p50, p95 | Why superseded |
|---|---|---|---|---|---|---|---|---|---|
| `20261018T145441Z-generation-local-ollama-dev-fa04154` (was published, removed in `e628690`; it never left this branch) | 14:54 UTC, `fa04154` | temperature 1.0, top_p 0.95 | 0.960 (0.805 to 0.993) | 0.727 (0.518 to 0.868) | 0.000 (0.000 to 0.561) | 0.600 (0.407 to 0.766) | 22 of 25 | 1,470.501 ms, 2,487.696 ms | its `citations_retrieved` row read 1.000 (0.867 to 1.000) while 3 trials were blocked for unretrieved citations: the check could not fail (judge S3-J1); the record carries the old check name, so it no longer validates. Memory 31.0 GiB before, 37.1 GiB after; 112.109 s |
| `20261018T134910Z-generation-local-ollama-dev-d897052` | 13:49 UTC, `d897052` | temperature 0.2 (top_p not sent: the server used the model's 0.95), seed per trial, the corrected oracle | 1.000 (0.867 to 1.000) | 0.773 (0.566 to 0.899) | 0.000 (0.000 to 0.561) | 0.680 (0.484 to 0.828) | 25 of 25 | 1,330.883 ms, 2,623.430 ms | temperature replaced by the card's values (decision 3); publish then refused it on the privacy scan (before decision 1) |
| `20261018T132722Z-generation-local-ollama-dev-86bf537` | 13:27 UTC, `86bf537` | temperature 0.2, the plan's original check 3 | 1.000 | 0.773 | 0.000 | 0.680 | 25 of 25 | 1,392.053 ms, 2,725.121 ms | the abstention check was corrected; its probe cases carry `must_not_appear` and a `forbidden_absent` check, which the schema no longer has, so `record.validate` rejects it now (18 problems) |

In the 0.2 runs, citation_hit equalled retrieval's hit@5 (0.773): a model can cite only what was
retrieved, so citation_hit cannot exceed hit@5, and that model cited a labelled chunk on every
question where retrieval found one; 16 of 25 cases differed across trials and 9 were
byte-identical. Their probes failed on (a): P-01's text abstained ("The documents do not specify a
number of password reset attempts allowed per day") but was labelled `answer`; P-02 and P-03 gave
values.

**Where the records are.** The published run is committed under `runs/published/`; the
superseded ones are in this clone's `runs/tmp/` (gitignored) only (fa04154's also in git history at
`20cd685`). `make eval-local` reproduces a
run in about 3 minutes, with Ollama 0.40.6 and the pinned model.

**Thinking off and the response format, verified on 0.40.6** (a probe session, exploratory, from
a script in the developer's scratch space; each variant one request with the answer prompt, then
the postcheck passed):

| Request fields | HTTP | Reasoning text | Reply fits the schema |
|---|---|---|---|
| `response_format: json_object`, `reasoning_effort: none` | 501 "structured output is unavailable" | n/a | n/a |
| `reasoning_effort: none` | 200 | 0 characters | yes |
| none | 200 | 3,793 characters | no (empty content, 1,024 completion tokens) |
| `think: false` | 200 | 2,732 characters | yes |
| `reasoning: {effort: none}` | 200 | 0 characters | yes |

The first live contract run had already shown `json_schema` failing with HTTP 501; the server log
says "Structured output is unavailable ... xgrammar library not found" for the MLX runner. So the
local config sends `reasoning_effort: none` and no response format (decision 2), and the live
contract test checks both before every run.

## The container (AC10) and ZAP (AC11), 2026-10-18

First build at `86bf537` (793,351,201 bytes; `fetch-model` in the build: "every file matches its
pinned sha256: /opt/raglab/models/..."; Tesseract 5.5.0; memory in use 1.779 GiB after start).
Rebuilt at `d897052` (20.4 s with a warm cache) for the evidence below: `raglab:local`,
793,364,086 bytes, `USER 10001`, `RAGLAB_GIT_SHA=d8970521c16556387d6ae3427e6435db797f5cef`.
`make container-run` publishes 127.0.0.1:8000 only (`lsof`: `127.0.0.1:8000 (LISTEN)`); up after
about 26 s (it ingests and embeds the pack at start).

```
$ curl -i http://127.0.0.1:8000/healthz
HTTP/1.1 200 OK
content-type: application/json
content-security-policy: default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'
x-content-type-options: nosniff
x-frame-options: DENY
referrer-policy: no-referrer
permissions-policy: camera=(), microphone=(), geolocation=(), payment=(), usb=()
cross-origin-opener-policy: same-origin
cross-origin-resource-policy: same-origin
cross-origin-embedder-policy: require-corp
cache-control: no-store

{"status":"ok"}
$ curl http://127.0.0.1:8000/version
{"raglab":"0.0.1","git_sha":"d8970521c16556387d6ae3427e6435db797f5cef","prompt_version":"answer-v1","provider":"fake","model":"fake-echo","digest":"fake","provenance":"fake"}
```

`/ask` as tenant A with the demo token: 200; without a tenant: 403
`{"status":"refused","label":"abstain","answer":"",...}`; `docker exec raglab id`: uid 10001.

`make zap` at `d897052` (ZAP 2.17.0 from its own container against Docker's host name, port
8000; the same result at `86bf537`): 6 URLs;
"FAIL-NEW: 0 FAIL-INPROG: 0 WARN-NEW: 0 WARN-INPROG: 0 INFO: 0 IGNORE: 3 PASS: 64". The three
ignored rules are Informational: 10109 Modern Web Application (the page is script-driven), 10049
Non-Storable Content (`no-store` on purpose), 10031 User Controllable HTML Element Attribute (a
false positive: ZAP's GET of the form finds "tenant-b" in a static `<option>`). Reasons in
`deploy/zap/rules.tsv`. The container is stopped by the script's trap.

## The user's decisions (2026-10-18)

Asked as three questions after the first report; the answers, verbatim:

| Decision | Answer | What was done |
|---|---|---|
| 1. Publishing: the planted exception ids in answers | "Allow those IDs only (Recommended)" | `privacy/allowlist-published.txt` enumerates the two exceptions-register ids the corpus plants (never a pattern), and the privacy check applies it only under `runs/published/`. publish now scans a run at its published path (a refused copy is removed) and refuses any run holding an answer key `answer_must_not_contain` string (the planted secret F-44, the personal details F-45, the attack canary), which no privacy pattern catches. `3207101` |
| 3. Temperature | "Card values, re-run (Recommended)" | temperature 1.0 and top_p 0.95 from the model card, https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4 ("Recommended sampling settings are Temperature 1.0 and Top_P 0.95", the same for reasoning on and off; read 2026-10-18, as relayed by the orchestrator: the developer's own fetch of another URL of the card returned 401), cited in `config/local-ollama.toml`; the adapter sends top_p and the manifest records it; the run above. `fa04154` |
| 2. JSON mode | "Accept, record the limit (Recommended)" | docs/COMPATIBILITY.md records the MLX runner's HTTP 501 on Ollama 0.40.6 with this tag and digest, the date, and how to re-test schema mode on every Ollama upgrade (`RAGLAB_LIVE_CONFIG` points the live contract test at a copy with `response_format = "json_schema"`). `fa04154` |

Evidence for decision 1, `tests/unit/test_published_allowlist_scope.py` (10 tests): the list is
exactly the corpus's exceptions-register ids; a published record holding one passes the real
check; the same ids are hits under `runs/tmp/`, `docs/` and `src/`; another id of the same shape
and a planted contact are hits under `runs/published/`; publish refuses the F-44 secret and both
F-45 details and leaves nothing behind; a run quoting a planted id publishes through the real
check while one quoting another id is refused and removed. **Break:** the list widened with the
prefix of the 2026 id, its first two parts (a pattern in effect: the rule's match is that prefix): 3 failed (the enumeration,
another id under runs/published, the real publish); restored from git: 10 passed.

## Developer choices (standing; the judge may challenge them)

The orchestrator relayed that these stand as chosen.

1. **The memory margin is 4 GiB** (the model's 17.8 GiB plus 4 GiB, against free, inactive and
   speculative pages). It is the minimum that still runs on this Mac with Docker Desktop running:
   the judge's preflight read 21.8 GiB available, exactly the 17.8 + 4 GiB needed (correction 7);
   an 8 GiB margin would refuse. The live sessions read 30.8 to 34.1 GiB available.
2. **Status codes:** no or unknown token 401, a tenant refusal 403, an input-limit refusal 400, a
   body over 4 KiB 413, invalid_output 502, unavailable 503.
3. **`totals.cases` counts case-trials** (75); `dataset.questions` counts distinct cases (25).
4. **compare refuses generation runs** until S4 defines a paired generation comparison.
5. **The demo tokens are literals in config** (`demo`, `tenant-a-only`), labelled lab practice.

## Fix round 1 (the judge's verdict, 2026-10-18)

The judge (a separate clone, its scripts and logs in its own scratch space) found four medium and
five low defects and three info items. For each, the test the judge suggested was written first
and run against the code of `20cd685` (with `PYTHONDONTWRITEBYTECODE=1`): each failed there for
the defect's reason, except S3-J3's, which passes at 20cd685 (that code asks the right port) and
fails only under the judge's sabotage (`port + 1` in the preflight); all pass after the fix (fix
round 2, correction 1). `make check` passed before each commit.

| Defect | Severity | Fix | Test (fails at 20cd685) | Commit |
|---|---|---|---|---|
| S3-S2: publish trusted the provenance string: a fake-model run relabelled `local` and resealed was published | medium | `record.validate` refuses a run whose embedder or generator is a fake (provider fake, or a fake revision or digest) unless its provenance is fake; `publish` refuses any such run. The tests that publish now make honest local runs (the real cached embedder; the OpenAI-compatible adapter against the in-process stub) instead of relabelling fakes | `tests/retrieval/test_publish.py::test_a_fake_model_run_labelled_local_is_refused`, `::test_a_fake_chat_run_labelled_local_is_refused` (at 20cd685: no problem reported, the run published) | e628690 |
| S3-J1: `citations_retrieved` could only be 1.000 (the validator withholds the answer before the check reads it) | medium | the check is now `model_citations_retrieved`: a trial fails it when the citation validator's event fired (the model's reply cited an unretrieved id); the blocked count stays; `validate` refuses a citations event on an answer that is not blocked | `tests/generation/test_citation_validator.py::test_the_record_counts_the_models_unretrieved_citations` (a FakeChat citing B-PWD@1.0/3/1: value below 1.0; at 20cd685 the metric did not exist and the old one read 1.000); `tests/retrieval/test_run_record.py::test_a_broken_generation_case_is_refused[a citations event on an ok answer...]` | e628690 |
| S3-J2: SIGTERM or SIGKILL of the session left `ollama serve` running; the docs said "always" | medium | the session turns SIGTERM and SIGHUP into SystemExit, so its finally block unloads the model, stops the server and runs the postcheck (a server started before the signal is stopped too). SIGKILL cannot be caught: docs/LOCAL-MODEL.md says so, and the pid file makes the next `up` refuse until `make ollama-down`. "always stops it" removed from the docs, the config comment and the Makefile | `tests/unit/test_ollama_session.py::test_a_terminated_session_still_stops_the_server_and_runs_the_postcheck[SIGTERM]`, `[SIGHUP]` (a subprocess session whose runner signals itself; at 20cd685: exit -15 and -1, no output) | c7a354d |
| S3-S1: a 500 carried no security headers (the middleware sits inside Starlette's error middleware) | medium | a catch-all exception handler answers a fixed 500 JSON body with every security header and logs the exception | `tests/api/test_api.py::test_a_server_error_carries_the_security_headers` (a FakeChat that raises; at 20cd685: a plain-text 500 without the headers) | 95b8cac |
| S3-J3: the fake host ignored which port a check asked about | low | `FakeHost` records `(host, port)` | `tests/unit/test_ollama_session.py::test_the_preflight_and_the_postcheck_ask_about_the_configured_port` (it passes at 20cd685, whose code asks the right port; with the judge's sabotage, `port + 1` in the preflight, the old tests passed 22 and this test failed: "1 failed, 22 passed") | c7a354d |
| S3-J4: a repeated citation was kept twice | low | the parser keeps each cited and conflict id once, in first-seen order | `tests/generation/test_prompt_snapshot.py::test_a_repeated_citation_is_kept_once` | 63c4485 |
| S3-J5: the postcheck matched any command line naming "ollama" and relied on BSD pgrep leaving out the caller's ancestors | low | a process counts only when its executable's name is `ollama` | `tests/unit/test_ollama_session.py::test_only_the_ollama_executable_counts_as_an_ollama_process` (a `vim config/local-ollama.toml`, a `tail -f` of the log and the session's own raglab command are not ollama) | c7a354d |
| S3-S3: error `reason` fields echoed adapter and parser text | low | `reason` is one of `raglab.api.app.REASONS`, a fixed vocabulary; the raw text goes to the server log (logger `raglab.api`) and, in a run, to the record's guard events and error field | `tests/api/test_api.py::test_an_error_reason_comes_from_a_fixed_vocabulary[script0-503]`, `[script1-502]` | 95b8cac |
| S3-S4: `deploy/zap/scan.sh` made the report folder world-writable (`chmod 777`) | low | no chmod: the folder keeps the caller's mode (755 here) and Docker Desktop's file sharing lets ZAP's user write into it; a Linux host would chown it to ZAP's uid (noted in the script). Running ZAP as the caller's uid was tried and failed ("Failed to access summary file /tmp/zap_out.json"). `make zap` rerun: "FAIL-NEW: 0 ... WARN-NEW: 0 ... IGNORE: 3 PASS: 64" | `tests/unit/test_container.py::test_the_zap_script_makes_nothing_world_writable` | 3b66ea3 |

At 20cd685 the new tests gave, in one run over the six files: "9 failed, 86 passed" (the S2, J1,
S1, S3, J4, J5 and S4 tests), and separately the two signal tests failed (exit -15, exit -1). After
the fixes `make check` passed with 954 tests at `3b66ea3`.

**Info items, notes only (no code):**

- **S3-J6, for S3h:** the container needs a writable `/tmp` (pytesseract writes its temporary
  image there): with `docker run --read-only` it dies at start, with `--read-only --tmpfs /tmp` it
  answers `/healthz` and `/ask` (the judge's run). A hosted deploy that sets a read-only root
  filesystem must mount a tmpfs at `/tmp`.
- **S3-S5, accepted:** the published-ids allowlist is scoped by path prefix (`runs/published/`),
  not by validated record. Accepted with the judge's reasoning: only `publish` writes there, and
  both ids are tenant A canaries, so R-16 still catches them in a tenant B answer
  (`abstention_oracle`'s no_canary, `tests/e2e/test_e2e_fake.py`); the enumeration test refuses
  a widened list.

**Ledger corrections (the verdict's section 5).** Each corrected line, as it now reads:

1. Security headers: "security headers on every response, a 500 included since fix round 1" (What
   was built, API and page). Before fix round 1 a 500 had none (S3-S1); 200, 400, 401, 403, 404,
   405, 413, 502 and 503 had them.
2. The session's stop: "on success, on failure, on Ctrl-C (SIGINT), on `kill` (SIGTERM) and on a
   closed terminal (SIGHUP). A SIGKILL cannot be caught: the server and a loaded model then stay
   up (the model until the keep-alive ends), the postcheck does not run, and the pid file in
   `runs/tmp/ollama/` makes the next `up` or session refuse until `make ollama-down` stops it"
   (docs/LOCAL-MODEL.md); the AC15 scope above ("a postcheck after every session") holds for
   every ending but SIGKILL.
3. AC11's scan without rules: "without rules.tsv the same three Informational alerts count as
   WARN: the judge's scan with the pinned image read "WARN-NEW: 3 ... PASS: 64"". The earlier
   "0 WARN, 66 PASS" is withdrawn.
4. `citations_retrieved 1.000 (0.867 to 1.000)` could not move (S3-J1); it is replaced by
   `model_citations_retrieved`, which in the published run reads 0.973 (0.824 to 0.996).
5. AC5: "1 passed, 13 deselected in 29.78s" at `3b66ea3`; the earlier "12 deselected" was from
   an earlier commit of the test file.
6. The postcheck's "no ollama process" now matches the ollama executable only (S3-J5), so it no
   longer depends on BSD pgrep's ancestor exclusion; on Linux it would not count the session
   itself.
7. The memory margin: "It is the minimum that still runs on this Mac with Docker Desktop running:
   the judge's preflight read 21.8 GiB available, exactly the 17.8 + 4 GiB needed" (Developer
   choices, 1).

## Fix round 2 (the judge's round 1 re-check, 2026-10-18)

The judge's re-check at `390aa63` confirmed eight round-1 items fixed (S3-J1, J3, J4, J5, S1, S2,
S3, S4), found S3-J2 fixed in code and by its subprocess test with the live demonstration still
owed (its trigger misfired on the buffered log, below), and one new low defect. The tally: 14 met,
1 needs CI (AC12). The test was written first and run at `390aa63`, where it fails for the
defect's reason; `make check` passed before each commit. No live session was run in this round,
and the published run of `3b66ea3` stands: S3-J7 changes no record.

| Defect | Severity | Fix | Test (fails at 390aa63) | Commit |
|---|---|---|---|---|
| S3-J7: the session's own lines were block-buffered off a terminal (`Session.say` defaulted to `print` without flush, and `raglab ollama` printed its postcheck line the same way), so under `make eval-local > log 2>&1` or CI they appeared only at exit, after the child commands' output and out of order, and a kill lost them; the judge's live SIGTERM trigger waited for such a line and fired after the session had ended | low | `say_now` prints flushed and is `Session.say`'s default; the postcheck lines in `raglab ollama` flush; `ollama-up`, `ollama-down`, `ollama-status` and `eval-local` set `PYTHONUNBUFFERED=1`; a note in docs/LOCAL-MODEL.md | `tests/unit/test_ollama_session.py::test_the_sessions_lines_reach_a_pipe_as_they_happen` (a session subprocess with stdout piped, the fake host and the default `say`, `PYTHONUNBUFFERED` removed from its environment; its runner marks a file and sleeps 2 s; at 390aa63: "no 'up' line within 1 s of the runner starting: b''"), `::test_the_makefile_session_targets_run_unbuffered` (at 390aa63 the ollama-up target had no `PYTHONUNBUFFERED=1`) | ab03be9 |

At 390aa63 the two tests gave "2 failed, 26 deselected"; after the fix the session tests gave "28
passed". **Break:** the flush removed from `say_now` in the committed file: "1 failed, 27 passed"
(`test_the_sessions_lines_reach_a_pipe_as_they_happen`, "no 'up' line within 1 s of the runner
starting: b''"); restored from git: "28 passed", the tree clean.

**For the owed live check of S3-J2:** with the lines flushed, a trigger on the session's
"session: uv run raglab eval ..." line now fires while the session runs; the judge's other
suggestion, `pgrep -f "raglab eval --suite generation"`, does not depend on the log at all.

**Ledger corrections (the re-check's section 6.4).** Each corrected line, as it now reads:

1. Fix round 1's first paragraph: "each failed there for the defect's reason, except S3-J3's,
   which passes at 20cd685 (that code asks the right port) and fails only under the judge's
   sabotage (`port + 1` in the preflight); all pass after the fix".
2. AC15's evidence: "SIGTERM and SIGHUP (judge S3-J2): the evidence is the subprocess unit test
   with the fake host (`test_a_terminated_session_still_stops_the_server_and_runs_the_postcheck`);
   no live session has been ended by a signal, and the live demonstration is pending the judge".
3. Choices made in the build, 1: "fix round 1 renamed the check `citations_retrieved` to
   `model_citations_retrieved` inside run-record v1, which is not additive ... That was acceptable
   only because the record lived on this branch; a later rename of a v1 field needs run-record
   v2".
4. S3-J7 is the table above.

## Choices made in the build (for the review)

1. **The schema's four retrieval case fields moved from `required` into `validate`** (by suite):
   a probe has no labels, and the subset validator has no conditional keywords. Every other
   change to v1 is an added optional property, with one exception: fix round 1 renamed the check
   `citations_retrieved` to `model_citations_retrieved` inside run-record v1, which is not
   additive (the plan promised that no reader of v1 breaks): it broke the one generation record
   that existed (fa04154), which was removed from `runs/published/` and is listed as superseded.
   That was acceptable only because the record lived on this branch; a later rename of a v1 field
   needs run-record v2. The three S2 runs validate unchanged.
2. **The stub server is in process** (httpx.MockTransport): the autouse no-network guard refuses
   every socket, including loopback. Tests marked `live` skip the guard on purpose.
3. **The entitlement check lives in one place**, the tenant guard, so removing it fails the spoof
   test; the API only maps the refusal to 403.
4. **Wilson intervals at n = cases**, with the rate over case-trials: the trials of one case are
   not independent.
5. **Canaries stay out of run records**: probes name `canaries_of`, and the validator reads the
   answer key, so a record never carries the planted contacts.
6. **The session's stop falls back to signalling the server** when macOS refuses the group signal
   (EPERM, seen at the end of the first session with the MLX runner; the server stopped anyway).

## Notes

- `.claude/worktrees/` (another agent's locked git worktree, created during this stage) sits inside
  the checkout; deptry and gitleaks scanned it and failed. It is now gitignored and skipped by
  gitleaks (`29689de`); it was not touched.
- `host.docker.internal` is in `privacy/allowlist.txt`, as Docker's public host name.
- `df523f8` (the container) was committed before `29689de` (the worktree ignore), so on this
  machine, with the nested worktree present, `make check` at `df523f8` alone fails in deptry; in a
  clean clone it passes.
- Starlette 1.8 warns that its test client wants `httpx2`; a warning only.
- A stray editor swap file of the plan (`docs/plans/.2026-10-16-s3-generation.md.swp`, untracked)
  was deleted by the developer at the start; if the plan was open in an editor, it will warn.

## Still to do in this stage

1. The live SIGTERM demonstration for S3-J2 (the judge, after fix round 2).
2. CI on the PR: pr-fast green with the API smoke (AC12).

## make check at the final commit

After fix round 2 (the run of `3b66ea3` still the published one): "956 passed, 1 deselected"
(the live test); "0 architecture violations in src/raglab"; the gate "recall@5 0.644 (n 22)
passes: the threshold is the baseline 0.644 (20261006T172928Z-retrieval-dense-dev-5f1d3a0) minus
one question (1/22), 0.598"; "api-smoke: passed"; the privacy check "0 hits across 235 files".
After fix round 1 it was "954 passed, 1 deselected".
