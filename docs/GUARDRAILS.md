# Guardrails

Which guard layer owns which requirement (docs/TEST-PLAN.md, sections 3 and 4), where it lives,
and the test that shows it. Started in S3 with the first three layers; S7a adds the rule layer
(the injection detector, the register filter, the instruction scan, the link, secrets and
personal-details and prompt-leak guards) and the attack suite, S7b the Guardrails AI comparison,
S10 the demo controls.

A guard implements the `Guardrail` port (`src/raglab/core/ports.py`), with a check at each stage
of a request. A check that returns an event stops the request: at input it is **refused** before
retrieval (the retriever is never called); after retrieval or on the output the answer is
**withheld** (status `blocked`, label `abstain`, no text). One step does not stop it (S7): a
**drop step** after retrieval leaves chunks out of the prompt, with an event per document, and the
request goes on from the chunks it keeps; the model, the output guards and the answer's citations
see only those. The pipeline (`src/raglab/generate/pipeline.py`) runs the guards in this order
(`raglab.guard.default_guards`): tenant, input limits, injection detector; after retrieval the
tenant check, then the register filter's drop step; on the output citations, links, secrets and
personal details, prompt leak. The instruction scan runs before any of them, where the index is
built.

An event names the rule and the layer, never the text a guard removed or withheld (how-to 07 step
8): a document or chunk id, a rule group, a count. The API answers a refused request with its
guard's fixed reason and a withheld answer with "blocked", and logs each decision as the guard's
name, its stage and its key in `REASONS` (`src/raglab/api/app.py`, `GUARD_REASONS`), never a
guard's own text.

## The layers (S3)

| Layer | Stage | Owns | What it does | Code | Tests |
|---|---|---|---|---|---|
| Tenant guard | input | R-21 | Refuses a request with no tenant, an empty one, `shared`, an unknown one, or one the caller's token may not use; the API answers 403 | `src/raglab/guard/tenant.py` | `tests/generation/test_input_guards.py`, `tests/api/test_api.py` |
| Tenant guard | after retrieval | R-13, R-16 (S3 part) | Blocks the answer before the model sees a chunk of another tenant (the store and the retrievers already filter before ranking: this is the line after them) | `src/raglab/guard/tenant.py` | `tests/generation/test_input_guards.py::test_another_tenants_chunk_after_retrieval_blocks_the_answer_before_the_model`, `tests/e2e/test_e2e_fake.py` |
| Input limits | input | the S3 plan's input limits (no R-id; the demo controls of S10 build on them) | Refuses an empty question, one over 500 characters, and control or invisible characters (Unicode Cc except line breaks and tabs, Cf, Cs, Co, Cn); the API answers 400, and caps the body at 4 KiB (413) | `src/raglab/guard/limits.py` | `tests/generation/test_input_guards.py`, `tests/api/test_api.py` |
| Citation validator | output | R-02 | Blocks an answer that cites, or flags as a conflict, an id that was not retrieved for it; the event names the ids | `src/raglab/guard/citations.py` | `tests/generation/test_citation_validator.py` |
| Fallback contract | model | Q-03 (honest failure) | A timeout, connection error or HTTP error gives `unavailable` (API 503); a reply outside the answer schema gives `invalid_output` (API 502). Neither carries answer text, and the run record counts both; any `unavailable` trial marks the run partial, never published (judge S3-J10) | `src/raglab/generate/pipeline.py`, `src/raglab/generate/prompts/answer_v1.py` | `tests/generation/test_fallback_contract.py` |

The run record checks the same rules again: `raglab.evals.record.validate` refuses a generation
case that cites an id it did not retrieve, a withheld answer with text, and any chunk, cited or
retrieved, of a tenant the case's tenant may not see.

## The layers (S7a)

| Layer | Stage | Owns | What it does | Code | Tests |
|---|---|---|---|---|---|
| Instruction scan | ingest (arrow L9), where the index is built | R-17 | Flags a chunk that matches two of three rule groups (addressed to the assistant; change its rules; send something out) and quarantines it, kept out of the index; the event names the chunk id and the groups. Inert on the clean pack, so the inventory, its snapshot and a clean run's corpus sha256 do not change | `src/raglab/ingest/scan.py`, `src/raglab/generate/assemble.py` | `tests/security/test_instruction_scan.py`, `tests/security/test_guard_cases.py` |
| Input injection detector | input | R-17 (direct), R-20 | Refuses before retrieval (the API answers 400) a question that holds an instruction to the assistant, text dressed as a system or developer message, or a request for the prompt or the configuration | `src/raglab/guard/injection.py` | `tests/security/test_guard_cases.py`, `tests/security/test_guard_reasons.py` |
| Register filter | after retrieval (a drop step) | R-15 | Leaves out every chunk whose status the register did not give (approved, superseded, reference): a page outside the register, even one that claims a register id, never reaches the prompt; the answer goes on from the rest; the event names the document id and the rule. Front matter is never read | `src/raglab/guard/register_filter.py` | `tests/security/test_attack_suite.py`, `tests/security/test_guard_cases.py` |
| Citation validator, extended | output | R-02, R-15 | Also blocks an answer that cites, or flags as a conflict, a chunk outside the register, even one that was in the prompt | `src/raglab/guard/citations.py` | `tests/security/test_guard_cases.py`, `tests/security/test_attack_suite.py` |
| Link guard | output | R-17 | Withholds an answer holding a link that appears in no register document (a register chunk the scan's rules do not flag, so a link planted inside a registered document is never allowed: there the guard is a second layer through the scan's rules), with or without its scheme; a register link cut at a slash passes, one with a query added does not | `src/raglab/guard/links.py`, `src/raglab/ingest/trusted.py` | `tests/security/test_guard_cases.py`, `tests/security/test_attack_suite.py` |
| Secrets and personal-details guard | output (arrow R8) | R-19 | Withholds an answer holding a credential-shaped token or an email address or phone number outside the team contacts of `corpus/SPEC.md` section 6; the team contacts (F-46, Mirrowfen IT Support) pass | `src/raglab/guard/disclosure.py`, `src/raglab/ingest/trusted.py` | `tests/security/test_guard_cases.py`, `tests/security/test_attack_suite.py` |
| Prompt-leak guard | output | R-20 | Withholds an answer sharing a run of 8 or more words with the system prompt (N set from the prompt text alone, S7 ledger), the phrase the prompt tells the model to say not counted | `src/raglab/guard/prompt_leak.py` | `tests/security/test_guard_cases.py`, `tests/security/test_attack_suite.py` |

Every layer has must-block and must-not-block cases in the security pack (`datasets/security/`),
decided binary per build (`tests/security/test_guard_cases.py`), and its miss rate, false-block
rate and added latency are measured by `make guard-suites` (docs/THRESHOLDS.md, Guards). The
deterministic attack suite (`tests/security/test_attack_suite.py`) shows each attack of
docs/THREAT-MODEL.md landing without its defences and stopped by each defence alone; `make
attack-local` asks the same attack cases of the local model, with the defences off and on (S7,
`src/raglab/evals/attack.py`, a session only with the maintainer's go). The guard set
(each layer's name and rules sha256) is part of what makes a consistency baseline current: a new
set needs a zero-event replay over the baseline's records (`make replay`, `runs/replays/`).

## Lab practice

- **The tenant comes from a demo token map.** `config/*.toml` `[api] tokens` maps a public demo
  token to the tenants it may use; the page uses `demo`, which may use both. Production takes the
  tenant from the identity provider's claims and never from the request body.
- **One request at a time.** The API serialises requests with a lock. Rate limits, a budget and a
  kill switch come with the public demo (S10).
- **Prompt text is data-framed, not sanitised.** Chunk text sits in `<chunk>` frames that it cannot
  close; an instruction inside a document is still text the model reads. S7 adds the instruction
  scan on ingest and the attack suite (R-17).
- **The register is a YAML file.** Production would read the document system's approval state,
  set at ingestion by the system that holds it, never by the document.
- **The detectors are rules**, written from the requirements and checked on the golden set's dev
  questions and the near misses of the pack. Paraphrase, encodings and other languages pass them;
  production would add a classifier or a managed guardrail behind the same port (S7b compares
  Guardrails AI's validators).
- **Withhold, not mask.** An output guard withholds the whole answer; masking personal details is
  one of S7b's comparisons.
- **The `FAKE-` token shape** is the lab's planted-token convention; production would run a
  secrets detector and a PII service.

## Later layers

| Layer | Stage | Owns |
|---|---|---|
| Guardrails AI validators (Detect Jailbreak, Restrict To Topic, Detect PII, Secrets Present, Toxic Language, Provenance Embeddings), compared with the rule layer | S7b | R-17, R-19, R-18 |
| Grounding (every value in a cited passage) | judged in S5; the Provenance comparison in S7b | R-18 |
| Rate limit, budget, kill switch | S10 | Q-02, Q-03 |
