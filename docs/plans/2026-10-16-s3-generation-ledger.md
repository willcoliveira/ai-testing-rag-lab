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
postcheck after every session that fails loudly unless the port is closed and no ollama process
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
| API and page | `src/raglab/api/app.py` (/healthz, /version, /ask; 401, 403, 400, 413, 502, 503; security headers on every response; OpenAPI pages off), `api/server.py`; `src/raglab/web/` (index.html, app.js, app.css) |
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
| AC5 | met | `tests/contract/test_chat_contract.py`: the shared contract against the stub (pr-fast) and, marker `live`, against Ollama 0.40.6 in `make eval-local`: "1 passed, 12 deselected in 23.40s" (the reply parsed into an Answer, citations among the given ids, no reasoning text, tokens reported). A digest mismatch, an unpulled tag, a server that is down and a non-loopback URL refuse to start; the committed config with its digest replaced by the placeholder refuses to run ("refuses to start until the tag's digest is pinned"), and `raglab eval --suite generation` on it exits 1. Before the digest was pinned (commit `a3494f7`) the committed config itself refused | (the digest-mismatch and placeholder tests are the break) |
| AC6 | met | `tests/generation/test_input_guards.py` and `tests/api/test_api.py`: over 500 characters, empty, U+0000, U+001B, U+202E, U+200B, U+E000, U+000D, U+007F refused (400) with 0 retriever calls; no tenant, null, empty, `shared`, unknown, a list, and the spoof (tenant-a-only token asking as tenant B) refused (403) with 0 retriever calls; no or unknown token 401 | the caller check in `guard/tenant.py` removed: 4 failed, among them `test_a_tenant_the_caller_may_not_use_is_403_and_never_retrieved[spoofed]` |
| AC7 | met | `tests/e2e/test_e2e_fake.py`: the app built from config/fake.toml (real pack, real embedder, FakeChat echoing every chunk), all 22 dev questions asked as each tenant: no tenant B canary (all 16) in a tenant A answer or its citations, no tenant A canary (all 47) in a tenant B answer; positive control: each tenant's own canaries do appear | every tenant filter off (the store mask, both `check_visible` calls, the retrieved guard): 2 failed (both directions). Removing one layer alone (only the retrieved guard, say) does not leak, by design: the S2 store filter masks before ranking and `check_visible` checks on the way out, so the e2e test fails only when all of them go; each layer has its own test (S2 `test_tenant_filter.py`; `test_input_guards.py::test_another_tenants_chunk_after_retrieval_blocks_the_answer_before_the_model`) |
| AC8 | met | `tests/retrieval/test_run_record.py`: the three committed S2 runs validate by name; a generation run validates; refused: a case without label, status or checks, a citation or conflict id not retrieved, text on a withheld answer, an unknown label, retrieval fields on a probe, edited checks, a missing trial, generation fields in a retrieval run, a retrieval case without recall, a tenant B chunk cited by a tenant A case | the unretrieved-citation check in `record.generation_problems` disabled: 2 failed |
| AC9 | met | the live run below, published: `runs/published/20261018T145441Z-generation-local-ollama-dev-fa04154`, provenance local, git clean at `fa04154`, not partial, the model tag and digest, the prompt version and every report field; `raglab publish` validated it, ran the privacy check at its published path and published it; the reset-attempts abstention count and pass^3 below are copied from the record | n/a (the publish refusals are tested in `tests/unit/test_published_allowlist_scope.py`) |
| AC10 | met | `tests/api/test_api.py`, `tests/api/test_page.py`, `tests/unit/test_container.py`; `make container` built `raglab:local` (793,364,086 bytes at `d897052`); the container runs as uid 10001 with the fake model and answers `/healthz` (below) | `frame-ancestors 'none'` dropped from the CSP: 10 failed |
| AC11 | met | `make zap`: "FAIL-NEW: 0 FAIL-INPROG: 0 WARN-NEW: 0 WARN-INPROG: 0 INFO: 0 IGNORE: 3 PASS: 64", 6 URLs; the three ignored rules are Informational, each with its reason in `deploy/zap/rules.tsv` | (the first scan without rules.tsv: 0 WARN, 66 PASS, the same three Informational alerts) |
| AC12 | needs CI; local evidence met | pr-fast step "API smoke (offline, fake model)" after the model fetch and the tests, `HF_HUB_OFFLINE=1`, `make api-smoke`; `tests/unit/test_workflow_rules.py::test_pr_fast_smoke_tests_the_api_offline_after_the_tests`; zizmor: no findings; locally four `ok` lines and "api-smoke: passed" | the step's `run` changed: 1 failed |
| AC13 | met | `make check` as above (ruff, pyright strict, deptry, vulture, pip-audit, bandit, semgrep, zizmor, gitleaks, privacy, architecture); `tests/unit/test_architecture.py`: the factory may import the fakes, any other module may not (a planted import in a copy of the real tree fails), httpx outside adapters and FastAPI outside api fail | see AC1 |
| AC14 | met; S3 `done` | TEST-PLAN R1, R4 and R7 name their tests (`tests/unit/test_test_plan.py` now requires it); traceability Test column for R-02, R-21, R-13 and R-16; docs/GUARDRAILS.md; docs/COMPATIBILITY.md "Tested against nemotron-3.5-lightning:30b-a3b-mlx@d1e17d7d... on Ollama 0.40.6 on 2026-10-18"; ARCHITECTURE and README S3 `done` (AC9 published); CHANGELOG line; this ledger | n/a |
| AC15 | met (added by the user, 2026-10-18) | `tests/unit/test_ollama_session.py` (22 tests, a fake host: the environment, the model size from its manifest, low memory, a registered service, a held port, no binary, an unpulled model, an old server, unload and stop, a server that will not stop, a leftover process, a session that succeeds, fails or is interrupted, a failed postcheck, the EPERM fallback); three live sessions and one probe session, each ending "postcheck passed: port closed, no ollama process, no model loaded" | with real OS reads, no server started: margin 100 GiB: "not enough memory: 26.7 GiB available, 117.8 GiB needed (model 17.8 GiB + margin 100 GiB)", exit 1; port 11434 held by `python3 -m http.server`: "127.0.0.1:11434 is already held by a process this project did not start", exit 1; `pgrep` found no ollama after either |

## The live run (AC9)

`make eval-local` at `fa04154` on 2026-10-18, 14:53 to 14:56 UTC, at the model card's sampling
settings (the user's decision 3, below), then `raglab publish`. Every number here is copied from
`runs/published/20261018T145441Z-generation-local-ollama-dev-fa04154/manifest.json` and its
report, or from the session's output.

**Settings (manifest).** nemotron-3.5-lightning:30b-a3b-mlx at digest d1e17d7d... on Ollama
0.40.6, provider openai-compat, base URL http://127.0.0.1:11434; temperature 1.0, top_p 0.95,
max_tokens 1024, timeout_s 120, response_format none, extra `reasoning_effort: none`; prompt
answer-v1 (sha256 96f42d9b...); guards tenant, input-limits, citations; dense retriever, k 5,
chunks 1,200; 3 trials, seed 20261018 (trial t uses seed + t - 1); Wilson intervals at 95%,
n = cases; ollama host 127.0.0.1:11434, keep_alive 2m, max_loaded_models 1, num_parallel 1,
context_length 8192. 22 dev questions and 3 probes, 75 case-trials, 112.109 s; provenance local;
git clean; partial false.

| Check (no judge) | Rate | 95% interval | n (cases) |
|---|---|---|---|
| status_ok | 0.960 | 0.805 to 0.993 | 25 |
| citations_retrieved | 1.000 | 0.867 to 1.000 | 25 |
| probe_abstention | 0.000 | 0.000 to 0.561 | 3 |
| citation_hit | 0.727 | 0.518 to 0.868 | 22 |
| pass^3 | 0.600 | 0.407 to 0.766 | 25 |

- Status counts: ok 72, refused 0, blocked 3, unavailable 0, invalid_output 0.
- Label agreement: 22 of 25 cases gave the same label in every trial.
- **The reset-attempts abstention count (F-32): P-01 (tenant A) 0 of 3, P-02 (tenant B) 0 of 3**;
  P-03 (F-40, tenant B) 0 of 3.
- Latency p50 1,470.501 ms, p95 2,487.696 ms (n 75); tokens 78,966 prompt and 7,667 completion
  (all 75 case-trials reported them).
- What pass^3 measures here (the report says it): a case passes only when all 3 trials pass, each
  with its own seed at temperature 1.0, so it measures consistency while the model samples, not
  correctness.

Reading (not judged; a citation hit is not correctness):

- **The three blocked answers are the citation validator at work (R-02).** R-Q21 trial 1 and R-Q25
  trials 1 and 2 cited document ids (`A-FAQ`, `A-PWD-V2`, `X-NCSC`, `A-EXC`) instead of chunk
  ids; the validator withheld them (abstain, status blocked), which lowers status_ok and
  citation_hit and is why those cases' labels differ across trials (R-Q04 is the third).
- **The probes all failed.** Every probe trial was labelled `answer` and stated a value: P-01
  "User passwords expire every 60 days" and "5 and 10 login attempts" (neighbouring rules, not
  reset attempts); P-02 the lockout rule or the NCSC range; P-03 "within 24 hours" (tenant B's
  factor revocation, not a leaver rule). No tenant A canary appeared in a tenant B answer (check c).
- **Trials differ more at temperature 1.0.** 2 of 25 cases are byte-identical across their three
  trials (9 of 25 at 0.2); labels changed in 3 cases.
- Memory available before the session (preflight): 31.0 GiB; after: 37.1 GiB. Live contract test
  30.57 s ("1 passed, 13 deselected"); the suite 112.109 s, about 37.4 s per trial of 25 cases;
  the whole session 2 min 54.2 s.
- Postcheck: "postcheck passed: port closed, no ollama process, no model loaded"; afterwards
  `pgrep -fl ollama` found nothing and `lsof -iTCP:11434 -sTCP:LISTEN` found nothing.
- **Published.** `raglab publish 20261018T145441Z-generation-local-ollama-dev-fa04154`:
  "published: .../runs/published/20261018T145441Z-generation-local-ollama-dev-fa04154"; the
  privacy check ran on the files at their published path, where the two planted exception ids the
  model quoted are allowed (decision 1), and no answer key `answer_must_not_contain` string is in
  them. `tests/retrieval/test_publish.py::test_the_committed_runs_are_valid_local_dev_runs_with_a_current_baseline`
  now also checks every published run for those strings.

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
| `20261018T134910Z-generation-local-ollama-dev-d897052` | 13:49 UTC, `d897052` | temperature 0.2 (top_p not sent: the server used the model's 0.95), seed per trial, the corrected oracle | 1.000 (0.867 to 1.000) | 0.773 (0.566 to 0.899) | 0.000 (0.000 to 0.561) | 0.680 (0.484 to 0.828) | 25 of 25 | 1,330.883 ms, 2,623.430 ms | temperature replaced by the card's values (decision 3); publish then refused it on the privacy scan (before decision 1) |
| `20261018T132722Z-generation-local-ollama-dev-86bf537` | 13:27 UTC, `86bf537` | temperature 0.2, the plan's original check 3 | 1.000 | 0.773 | 0.000 | 0.680 | 25 of 25 | 1,392.053 ms, 2,725.121 ms | the abstention check was corrected; its probe cases carry `must_not_appear` and a `forbidden_absent` check, which the schema no longer has, so `record.validate` rejects it now (18 problems) |

In the 0.2 runs, citation_hit equalled retrieval's hit@5 (0.773): a model can cite only what was
retrieved, so citation_hit cannot exceed hit@5, and that model cited a labelled chunk on every
question where retrieval found one; 16 of 25 cases differed across trials and 9 were
byte-identical. Their probes failed on (a): P-01's text abstained ("The documents do not specify a
number of password reset attempts allowed per day") but was labelled `answer`; P-02 and P-03 gave
values.

**Where the records are.** The published run is committed under `runs/published/`; the
superseded ones are in this clone's `runs/tmp/` (gitignored) only. `make eval-local` reproduces a
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
   speculative pages). An 8 GiB margin would have refused the session with Docker Desktop running
   (22.9 GiB available at the time).
2. **Status codes:** no or unknown token 401, a tenant refusal 403, an input-limit refusal 400, a
   body over 4 KiB 413, invalid_output 502, unavailable 503.
3. **`totals.cases` counts case-trials** (75); `dataset.questions` counts distinct cases (25).
4. **compare refuses generation runs** until S4 defines a paired generation comparison.
5. **The demo tokens are literals in config** (`demo`, `tenant-a-only`), labelled lab practice.

## Choices made in the build (for the review)

1. **The schema's four retrieval case fields moved from `required` into `validate`** (by suite):
   a probe has no labels, and the subset validator has no conditional keywords. Every other
   change to v1 is an added optional property; the three S2 runs validate unchanged.
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

1. Verify: the judge re-runs the evidence and the breaks, and a `/security-review` pass.
2. CI on the PR: pr-fast green with the API smoke (AC12).

## make check at the final commit

With the published run committed: "941 passed, 1 deselected" (the live test); the gate "recall@5
0.644 (n 22) passes: the threshold is the baseline 0.644
(20261006T172928Z-retrieval-dense-dev-5f1d3a0) minus one question (1/22), 0.598"; "api-smoke:
passed"; the privacy check "0 hits across 235 files".
