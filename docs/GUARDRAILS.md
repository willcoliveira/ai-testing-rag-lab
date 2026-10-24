# Guardrails

Which guard layer owns which requirement (docs/TEST-PLAN.md, sections 3 and 4), where it lives,
and the test that shows it. Started in S3 with the first three layers; S7 adds the injection, PII
and grounding guards and the attack suite, S10 the demo controls.

A guard implements the `Guardrail` port (`src/raglab/core/ports.py`), with a check at each stage
of a request. A check that returns an event stops the request: at input it is **refused** before
retrieval (the retriever is never called); after retrieval or on the output the answer is
**withheld** (status `blocked`, label `abstain`, no text). The pipeline
(`src/raglab/generate/pipeline.py`) runs the guards in this order: tenant, input limits,
citations.

## The layers (S3)

| Layer | Stage | Owns | What it does | Code | Tests |
|---|---|---|---|---|---|
| Tenant guard | input | R-21 | Refuses a request with no tenant, an empty one, `shared`, an unknown one, or one the caller's token may not use; the API answers 403 | `src/raglab/guard/tenant.py` | `tests/generation/test_input_guards.py`, `tests/api/test_api.py` |
| Tenant guard | after retrieval | R-13, R-16 (S3 part) | Blocks the answer before the model sees a chunk of another tenant (the store and the retrievers already filter before ranking: this is the line after them) | `src/raglab/guard/tenant.py` | `tests/generation/test_input_guards.py::test_another_tenants_chunk_after_retrieval_blocks_the_answer_before_the_model`, `tests/e2e/test_e2e_fake.py` |
| Input limits | input | the S3 plan's input limits (no R-id; the demo controls of S10 build on them) | Refuses an empty question, one over 500 characters, and control or invisible characters (Unicode Cc except line breaks and tabs, Cf, Cs, Co, Cn); the API answers 400, and caps the body at 4 KiB (413) | `src/raglab/guard/limits.py` | `tests/generation/test_input_guards.py`, `tests/api/test_api.py` |
| Citation validator | output | R-02 | Blocks an answer that cites, or flags as a conflict, an id that was not retrieved for it; the event names the ids | `src/raglab/guard/citations.py` | `tests/generation/test_citation_validator.py` |
| Fallback contract | model | Q-03 (honest failure) | A timeout, connection error or HTTP error gives `unavailable` (API 503); a reply outside the answer schema gives `invalid_output` (API 502). Neither carries answer text, and the run record counts both; any `unavailable` trial marks the run partial, never published (judge S3-J10) | `src/raglab/generate/pipeline.py`, `src/raglab/generate/prompts/answer_v1.py` | `tests/generation/test_fallback_contract.py` |
| Logs: traces never keep what a guard removed (S9; the main plan's guardrails line, how-to 07 step 8) | the trace | no R-id | A guard's decision is recorded as its name, its stage and the API's fixed reason key (`src/raglab/core/reasons.py`, the API's `REASONS`), never the event's text; a refused or withheld request leaves no text in any span; the tenant and the retrieved and cited ids appear only once the guards that check them have passed; content only with the opt-in, only for an ok answer (docs/OBSERVABILITY.md). A new guard (S7) adds its key to `REASONS` | `src/raglab/generate/pipeline.py`, `src/raglab/obs/` | `tests/obs/test_guard_traces.py`, `tests/obs/test_redaction.py` |

The run record checks the same rules again: `raglab.evals.record.validate` refuses a generation
case that cites an id it did not retrieve, a withheld answer with text, and any chunk, cited or
retrieved, of a tenant the case's tenant may not see.

## Lab practice

- **The tenant comes from a demo token map.** `config/*.toml` `[api] tokens` maps a public demo
  token to the tenants it may use; the page uses `demo`, which may use both. Production takes the
  tenant from the identity provider's claims and never from the request body.
- **One request at a time.** The API serialises requests with a lock. Rate limits, a budget and a
  kill switch come with the public demo (S10).
- **Prompt text is data-framed, not sanitised.** Chunk text sits in `<chunk>` frames that it cannot
  close; an instruction inside a document is still text the model reads. S7 adds the instruction
  scan on ingest and the attack suite (R-17).

## Later layers

| Layer | Stage | Owns |
|---|---|---|
| Instruction scan on ingest, prompt-injection guard | S7 | R-15, R-17 |
| Secrets and PII on the output | S7 | R-19 |
| Grounding (every value in a cited passage) | S7, judged in S5 | R-18 |
| System prompt leak | S7 | R-20 |
| Rate limit, budget, kill switch | S10 | Q-02, Q-03 |
