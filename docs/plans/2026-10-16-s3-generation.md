---
stage: S3
name: generation
nodes: [S3]
date: 2026-10-16
status: approved 2026-10-18
---

# S3: Generation, a local live run, the API, a web page and a local container

Part of the main plan (phase P1, release v0.1). Branch: `feat/s3-generation`. Build project
stage 3 / how-to 17 step 6. The first stage where a model writes an answer. Quality is still not
judged (S5); this stage checks what code can check without a judge.

The message that opened S3 planning (2026-10-16): "continue on the plan for this repo".

## Goal

- Turn a question and its retrieved chunks into a structured answer: text, cited chunk ids, the
  decision label (`answer`, `abstain`, `flag-conflict`, `refuse-and-help`; TEST-PLAN section 3),
  a conflict field and a status.
- Run it on a local model through Ollama, publish one live run with its provenance, and report
  what can be counted without a judge: citation integrity, abstention on the omission questions,
  and pass^k over three trials.
- Serve it: an API (`/healthz`, `/version`, `/ask`) that fails closed on tenant, one static page,
  and a container that runs with the fake model and passes a ZAP baseline scan on the Mac.
- Start the guardrail layers: input limits, the tenant check on the request, and the citation
  validator.

## Out of scope (cut or deferred, so the judge holds the stage to this list)

| Item | Where it goes |
|---|---|
| Judged quality (faithfulness, relevancy, correctness of the value) | S5 |
| Behaviour cases in the golden set, the decision-label gate, pass^k as a gate | S4 (cases, consistency gate) |
| Hosted providers (Anthropic, OpenAI, Groq, Bedrock) | S5, after ADR-002 |
| Deploying the container anywhere | S3h |
| Rate limit, budget, kill switch and other demo controls | S10 (the input limits arrive here) |
| Prompt-injection, PII and grounding guards; the attack suite | S7 |
| axe and Playwright checks of the page | Track B (S3 checks labels and keyboard order in a unit test) |
| Tracing | S9 |
| ZAP in CI | S3h, against the host (S3 runs it on the Mac) |

## Prerequisites on your Mac (your action, like the S3h sign-ups)

1. **Ollama.** It is not installed. Install a current version (`brew install ollama`, or the
   app) and pull the generator chosen under "The generator". I don't install software on your machine without your go.
2. **Docker.** Docker Desktop is installed but its daemon is not running. Start it for the
   container and ZAP criteria (AC10, AC11).

## What gets built

```
src/raglab/core/ports.py       + ChatModel protocol; Guardrail protocol (input, retrieved, output)
src/raglab/core/types.py       + Answer (text, cited_ids, label, conflict, status), Status enum
src/raglab/generate/prompts/answer_v1.py   VERSION, the system prompt, the chunk framing (chunks are
                               data, delimited, with their ids); no developer comments in the text
src/raglab/generate/pipeline.py   question + tenant -> guards -> retrieve -> prompt -> model ->
                               parse -> citation validator -> Answer
src/raglab/guard/              NoopGuardrail, InputLimits (length 500, charset), TenantGuard,
                               CitationValidator; docs/GUARDRAILS.md (which layer owns which R-xx)
src/raglab/adapters/openai_compat.py   chat completions over httpx with a JSON schema response
                               format; reads the model digest at start (Ollama /api/tags)
src/raglab/adapters/fake.py    + FakeChat (deterministic, scriptable)
src/raglab/evals/generation.py the generation suite: N trials, deterministic checks, pass^k
src/raglab/api/                FastAPI: /healthz, /version (git sha, prompt version, model + digest),
                               /ask; security headers; the static page
src/raglab/web/index.html      one page: tenant, question, answer, label, citations
cli: raglab ask | serve | eval --suite generation
config/fake.toml  config/local-ollama.toml
schemas/run-record.v1.json     + suite "generation" and the answer fields (see choices)
datasets/probes.s3.jsonl       the abstention probes: F-32 (omission) for each tenant, F-40 for tenant B
deploy/Dockerfile              python 3.13 slim by digest, uv, non-root, the embedder baked in
deploy/zap/                    baseline config with each ignored rule and its reason
runs/published/<run_id>/       the live local run (committed)
```

## The live run

- **Questions:** the 22 dev retrieval questions (labels exist, so a citation can be checked
  against them) plus abstention probes from the answer key: F-32 (reset attempts, an omission) for
  each tenant and F-40 (a tenant B abstention), questions written from their reference answers. The test split is not run.
- **Trials:** N = 3 (the main plan's local default), temperature and seed recorded.
- **Checks per trial, no judge:**
  1. status is `ok`;
  2. every cited id was retrieved for that answer (R-02);
  3. an abstention probe has label `abstain`, and none of its `must_not_appear` strings appears;
  4. a retrieval question is not `abstain` and cites at least one labelled chunk (a citation hit).
- **Reported:** each check's rate with a case-level Wilson interval and n; pass^3 (a case passes
  only if all three trials pass); the abstention count on the reset-attempts probe (out of its
  trials); label agreement across the three trials per case; p50 and p95 latency; tokens.
  Nothing is gated: the main plan sets targets from the first real run, so these numbers become
  S4's and S5's starting point. A citation hit is not correctness; the report says so.
- Every number in the ledger and the PR body is read from the published run record.

## Choices I made (you can change them)

| Item | Choice | Why |
|---|---|---|
| HTTP client | `httpx`, not the `openai` SDK, inside `adapters/` only | Ollama, LM Studio, vLLM and Groq all speak the same chat completions API; one small dependency, and FastAPI's test client uses it anyway |
| Structured output | JSON schema response format; output that does not parse, or names an unknown label, is status `invalid_output` (counted, never repaired into an answer) | the fallback contract: no guessed answer |
| Citation validator | a cited id not in the retrieved set blocks the answer: label becomes `abstain`, status `blocked`, the event is recorded | the main plan's "block and abstain" |
| Model pinning | Ollama tags are not dated, so the config pins the tag **and** its digest; a run whose model digest differs refuses to start, and the manifest records both | the "dated snapshots, never aliases" rule, in its local form |
| Run record | extend v1 additively: `suite` gains `generation`; generation cases carry answer, label, conflict, cited ids, status, guard events, tokens; `validate` requires them for that suite. The three S2 runs still validate unchanged (a test) | no reader of v1 breaks, and the playground reads one format |
| Tenant on the request | lab version: the API maps a caller token to the tenants it may use (config); a request naming another tenant is refused with 403 before retrieval. The page's demo token may use both tenants. Production would take the tenant from the identity provider's claims; the docs say so | R-21 needs a "caller not entitled" case to test |
| Container | the fake model plus the real ONNX embedder, baked in at build time with its sha256 checked | S3h then measures memory with the embedder it will really carry |
| Port | `127.0.0.1:8000` by default; the container binds `0.0.0.0` inside only | nothing listens on the LAN by accident |

## Acceptance criteria

Evidence marked **live** runs on your Mac with Ollama, is excluded from `make check` by the
`live` marker, and is recorded in the ledger. **[CI]** criteria are proven on the PR.

| # | Criterion | Evidence |
|---|---|---|
| AC1 | `ChatModel` and `Guardrail` ports in `core` (stdlib only); `Answer` carries text, cited ids, label, conflict, status; FakeChat lives in `adapters/fake.py` | `make architecture`; `test_answer_types.py` |
| AC2 | The prompt is versioned code: the assembled prompt for a fixed question and fixed chunks equals its reviewed snapshot; chunk text is framed as data with its id; changing the prompt without bumping VERSION fails | `test_prompt_snapshot.py` (TEST-PLAN R4); **break:** edit one word, test fails |
| AC3 | Cited ids are a subset of retrieved ids on every answer: an answer citing an id that was not retrieved is blocked and recorded as `abstain`/`blocked` | `test_citation_validator.py` (TEST-PLAN R7, R-02); **break:** disable the validator, a scripted FakeChat citation of an unretrieved id gets through and the test fails |
| AC4 | The fallback contract: a provider timeout, connection error, HTTP 5xx or unparseable output gives `unavailable` or `invalid_output`, never answer text; the run record counts them | `test_fallback_contract.py` (contract, a local stub server, no network) |
| AC5 | `openai_compat` passes the shared contract tests against a stub server in pr-fast, and against Ollama when it is running (live); a digest mismatch refuses to start | `test_chat_contract.py`; live: the same file with `-m live` |
| AC6 | Input guards: a question over 500 characters, with control characters, or empty is refused before retrieval; a request without a tenant, with an unknown tenant, with "shared", or with a tenant the caller token may not use is refused (403) and the retriever is never called | `test_input_guards.py`, `test_api.py` (TEST-PLAN R1, R-21); **break:** remove the token check, the spoof test fails |
| AC7 | No other tenant's content in an answer: with FakeChat echoing every chunk it is given, no tenant B canary appears in any tenant A answer over all dev questions, and the reverse | `test_e2e_fake.py` (R-13, R-16, S3 part) |
| AC8 | The run record takes generation runs: `eval --suite generation` writes a record that validates; the three S2 runs still validate; a generation case missing its label or citing an unretrieved id is refused | `test_run_record.py` additions |
| AC9 | **Live:** one local run on Ollama (22 dev questions plus the abstention probes, N=3) is published with provenance `local`, the model tag and digest, the prompt version, and the report fields listed under "The live run"; the reset-attempts abstention count and pass^3 in the ledger are copied from the record | `runs/published/<run_id>/`; `raglab publish` validates it; ledger |
| AC10 | The API and page: `/healthz`, `/version` (git sha, prompt version, model and digest), `/ask`; security headers (CSP without inline script, nosniff, frame-ancestors none, referrer policy); the page's inputs have labels and a keyboard order; the container builds from a digest-pinned base, runs as non-root with the fake model, and answers `/healthz` | `test_api.py`, `test_page.py`; `make container` and a curl in the ledger (Docker) |
| AC11 | ZAP baseline against the running fake container on the Mac: no FAIL; each WARN fixed or listed in `deploy/zap/` with its reason | the ZAP report summary in the ledger (Docker) |
| AC12 | [CI] pr-fast starts `raglab serve` with `config/fake.toml` and smoke-tests `/healthz`, `/version`, an `/ask` answer and a no-tenant refusal, offline, without new network access | PR checks; `test_workflow_rules.py` addition |
| AC13 | Architecture and hygiene: httpx and FastAPI imports stay where the rules put them; deptry, vulture, pyright strict, bandit, semgrep clean; `make check` passes | `make check` |
| AC14 | Docs: TEST-PLAN rows R1, R4 and R7 name their tests; the traceability Test column filled for R-02, R-21 and the S3 part of R-13 and R-16; `docs/GUARDRAILS.md` started; COMPATIBILITY.md says "tested against <model>@<digest> on Ollama <version> on <date>"; ARCHITECTURE and README mark S3 done; CHANGELOG line; ledger | `test_test_plan.py`; review |

## How it will run

1. **Build:** the developer (Opus 5.5) builds AC1 to AC8 and AC12 to AC14 offline, then AC10
   and AC11 once Docker is running, then the live run (AC9) once Ollama is installed.
2. **Judge:** Fable 5.1 in a separate clone re-runs the evidence and tries to break AC2, AC3,
   AC6 and AC7, then restores them. S3 is security-relevant, so the judge step adds a
   `/security-review` pass over the API and container.
3. **Fix rounds:** at most two. Product choices come back to you.
4. Sequential subagents unless your go message asks for a Workflow.

**Hosted spend:** none. Everything runs on the fake model or Ollama.

## Decisions

Asked on 2026-10-16; the answers, verbatim:

| Decision | Answer | What it means |
|---|---|---|
| One PR or two | "One PR" | all fourteen criteria land in `feat/s3-generation`, with one judge pass |
| FakeChat at runtime | "Allow via factory only (Recommended)" | rule 4 of `scripts/check_architecture.py` becomes: the fake adapters are built only by `raglab.adapters.factory`, when the config says `provider = "fake"`, and by the unit tests; the run's provenance is `fake`, and publish refuses every fake run. The rule change and a test that fails on any other import are part of AC13 |
| The generator | "is there any smaller and lightweight from the new models of nvidea that we can use, i reckon perhaps there are some better ooptions available for now" | see "The generator" below |
| The plan | "Changes first" | the changes are this section and the generator; the plan comes back for approval |

## The generator

NVIDIA models on Ollama that run on an Apple Silicon Mac (checked 2026-10-16 on ollama.com and the
Hugging Face model card; sizes are Ollama's download sizes):

| Model | Size | Notes |
|---|---|---|
| **Nemotron 3.5 Lightning** `nemotron-3.5-lightning:30b-a3b-mlx` (recommended) | 23 GB, MLX build for Apple Silicon | released 2026-08-11; 30B parameters, 3B active per token (hybrid Mamba-2, MoE and attention), so it runs at about the speed of a 3B model; trained on structured output; thinking is on by default and switched off for generation; OpenMDW 1.1 licence, commercial use allowed |
| Nemotron 3 Nano 4B `nemotron-3-nano:4b` | 2.8 GB | the truly light option, from about March 2026; expect weaker JSON and citation discipline |
| Nemotron 3.5 Bolt | 25 GB | not usable here: Ollama's page says Apple Silicon is not supported |

"Lightweight" means two things here. Lightning is light in compute (3B active) but takes 23 GB of
memory; Nano 4B is light in both, at a cost in quality. On a 48 GB Mac, Lightning fits with room
for the embedder and Docker. With a Nemotron generator, the S5 judge comes from another family
(Qwen, Llama or Gemma), which keeps the main plan's "different family" rule.

How it is pinned: the config names the tag and its digest, and the adapter turns thinking off
and records that in the manifest. The adapter's contract test (AC5) confirms on your Mac that,
with thinking off, the model returns output that fits the answer schema, before the live run.

Second round (2026-10-16), verbatim: generator: "Nemotron 3.5 Lightning (Recommended)"; plan:
"Changes first". So the generator is `nemotron-3.5-lightning:30b-a3b-mlx`, its digest pinned
when it is pulled, and the plan waits for the changes.

## Approval

The plan came back unchanged on 2026-10-18 and was approved. The answer, verbatim: "Approve and
start". The developer builds the offline criteria first, then AC10 and AC11 (Docker is running),
and AC9 once Ollama is installed and the generator is pulled.
