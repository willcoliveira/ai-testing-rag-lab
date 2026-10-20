# Onboarding

This guide covers what you can run today, what you can break on purpose to learn what each test
guards, and where each concept already lives. It is current as of S4, done (2026-10-19): golden
set v1.1 (40 behaviour cases) is signed off, and the retrieval and local generation baselines are
republished on it (the S4 ledger). Every stage that adds a command or a concept updates it, and
`tests/unit/test_onboarding.py` checks that every path, `make` target and `raglab` command named
here exists, and that the stage this line names is not still in progress once the phase map marks
it done.

The lab is a policy Q&A assistant over a fictional company's identity and security policy pack.
Up to S2 it ingests the pack, retrieves from it with a real local embedding model, and scores
retrieval against labelled questions. From S3 a model writes a structured answer: the fake echo
model offline, a local model through Ollama for live runs.

## Set up

You need [uv](https://docs.astral.sh/uv/), Node 22, [gitleaks](https://github.com/gitleaks/gitleaks)
and Tesseract (`brew install tesseract`, or `apt-get install tesseract-ocr`). No account and no API
key.

```bash
uv sync
make hooks     # required in every clone
make model     # once: the 67 MB embedding model, hash-checked, into ~/.cache/raglab/models
```

The privacy check always loads the committed example list. The maintainer's own list
(`privacy/forbidden-strings.txt`) is local and gitignored. `make check` passes without it, as it does in
CI.

## Run it

| Command | What it shows | What you should see |
|---|---|---|
| `make check` | Every offline gate: format, lint, types, dependency and security scans, privacy, architecture, the dataset check, tests, the retrieval gate | All tests pass, then `recall@5 ... passes`. Since S4 the retrieval baseline is the dense dev run on golden set v1.1 (recall@5 0.682) |
| `make check-dataset` (or `uv run raglab check-dataset`) | The golden file against its ten rules before any run: labels, features, the answer, abstain, conflict and refusal shapes, planted strings, the mix, the datasheet's sha256 line | One `check-dataset: datasets/golden.v1.jsonl passes (...)` line; a broken case is named with its rule, and every `raglab eval` and `raglab gate` stops on it |
| `uv run raglab ingest` | The pack parsed and chunked into `runs/tmp/inventory.json` | 228 chunks from 21 documents |
| `uv run raglab ingest --chunk-size 600 --compare corpus/inventory.snapshot.json` | A chunking change as a reviewable diff | 249 chunks, with the changed ids listed |
| `uv run python scripts/chunk_experiment.py --chunk-size 600` | Which planted features a smaller chunk breaks | 0 split at 1,200 and 1 split at 600 (F-16) |
| `uv run raglab eval --suite retrieval --config config/retrieval-dense.toml` | One retrieval run, written as a run record | A folder in `runs/tmp/` with `manifest.json`, `cases.jsonl` and `report.md`; recall@5 0.682 |
| The same with `config/retrieval-hybrid.toml`, then `uv run raglab compare <dense run> <hybrid run>` | A paired comparison with bootstrap intervals and the questions that flipped | Every interval contains 0; only hybrid finds R-Q10 and R-Q33; only dense finds R-Q02 |
| `make gate` | The no-regression gate that pr-fast runs | The pass line above |
| `make playground` | The published runs in a browser | http://127.0.0.1:8000/ listing the published runs with per-question hits |
| `uv run raglab ask --config config/fake.toml --tenant tenant-a "How long must a password be?"` | One answer from the fake model, as JSON | Status `ok`, label `answer`, the retrieved chunks' text, and their ids in `cited_ids` |
| `uv run raglab ask --config config/fake.toml --tenant shared "x"` | The tenant guard failing closed | Status `refused`, no answer, exit 1 |
| `uv run raglab serve --config config/fake.toml` | The API and the page | http://127.0.0.1:8000/ asks as tenant A or B with the demo token |
| `make api-smoke` | The API smoke test that pr-fast runs | Five `ok` lines (the last: the server stopped gracefully on SIGTERM, exit -15), then `api-smoke: passed` |
| `uv run raglab eval --suite generation --config config/fake.toml` | A generation run record with the fake model: every dev retrieval question and behaviour case, 3 trials each | The checks, and for the behaviour cases the decision-label rate, the confusion and abstention tables and behaviour pass^3; with the echo model these measure the plumbing (it answers whenever a chunk is retrieved), never Q-05 |
| `uv run raglab compare <run A> <run B>` on two generation runs | The paired difference of behaviour pass^3 and of the decision-label rate, by case id, and the flipped cases | Refused unless the dataset, split and trials match |
| `uv run raglab eval --suite retrieval --config config/retrieval-dense.toml --split test` | The test split held out | Refused: test and all run only with `--gate nightly` or `--gate release` |
| `make ollama-status` | Whether a local model server is up, and the memory available | No pid, port closed, no ollama process |
| `make eval-local` | The live run on Ollama (needs Ollama and the pinned model; docs/LOCAL-MODEL.md) | The live contract test, the run record, then `postcheck passed` |
| `make gate-local` | The consistency gate (Q-05) on Ollama: a dev run, then `raglab gate` against the published local baseline | One `consistency gate (Q-05): ...` line; it refuses to judge until docs/THRESHOLDS.md sets the margin from runs |
| `make nightly-local` | The local nightly on Ollama: every split, `--gate nightly` | The live contract test, then a run record of split all |
| `make container`, then `make zap` | The fake-model container and its ZAP baseline scan (Docker) | No FAIL and no WARN; three Informational alerts, each ignored with its reason in `deploy/zap/rules.tsv` |
| `make corpus` | Rebuilds the PDF, HTML and scanned PNG from the Markdown sources | No change in `git status` |

Read next: [README.md](../README.md), [ARCHITECTURE.md](ARCHITECTURE.md) for the progress
diagrams, [TEST-PLAN.md](TEST-PLAN.md) for the requirements and one named check per pipeline
arrow, and the stage ledgers in [plans/](plans/).

## Break it on purpose

The fastest way to learn what a test protects is to break the code and watch the right test name
the cause. A developer or a judge made each break below during a stage, so the expected failure is
real.

Work in a separate clone with `PYTHONDONTWRITEBYTECODE=1` set, so no stale bytecode outlives a
break. Restore each file with `git checkout -- <file>`, and never commit a break.

| Break | Run | Expected failure |
|---|---|---|
| Remove the tenant mask in `src/raglab/index/memory.py` | `uv run pytest tests/retrieval/test_tenant_filter.py` | 7 failures; the second check, on the way out, raises `TenantError` |
| Score reciprocal rank as 1/(rank + 1) in `src/raglab/evals/metrics.py` | `make test` | 5 failures across the metrics, run record and compare tests |
| Make dense retrieval drop its best hit (return ranks 2 to 6) in `src/raglab/retrieve/dense.py` | `make gate` | `recall@5 0.356 (n 22) fails: the threshold is ... 0.636` |
| Reword one question in `datasets/golden.v1.jsonl`, keeping its labels | `make gate` | The baseline has another `dataset.sha256`: publish a new baseline in a reviewed pull request |
| Point R-Q02's label at a section that does not exist (A-LIFE 6.2) | `make gate` | `R-Q02: A-LIFE section 6.2 has no chunk` |
| The same label edit | `make check-dataset` | `R-Q02: rule 2 (labels and features): labelled section A-LIFE 6.2 has no chunk in the inventory`, before any run |
| Read the decision label from the answer text instead of the `label` field in `src/raglab/evals/behaviour.py` | `uv run pytest tests/generation/test_behaviour_checks.py` | The text-abstains, label-answer case passes when it must fail: the test fails |
| Pair the cases of `raglab compare` by position in `src/raglab/evals/compare.py` | `uv run pytest tests/retrieval/test_compare.py` | The hand-computed generation comparison fails (its B run lists the cases in reverse) |
| Shrink the chunk budget until rules lose their exceptions | `uv run python scripts/chunk_experiment.py --chunk-size 250` | 7 features split, each with the closest chunk and the sentence it lacks; F-15 shows the MFA rule cut from its break-glass exception |
| Import `fastembed` in `src/raglab/retrieve/dense.py` | `make architecture` | Vendor SDK fastembed is imported outside `raglab.adapters` |
| Disable the tenant check (`tenant_problems`) in `src/raglab/evals/record.py` | `uv run pytest tests/retrieval/test_publish.py` (it forges a copy of the baseline with a tenant B chunk in a tenant A case) | The forgery test fails: the forged record now validates and would publish |
| Make `check_output` in `src/raglab/guard/citations.py` return `None` | `uv run pytest tests/generation/test_citation_validator.py` | An answer citing a tenant B chunk that was never retrieved gets through, and the test fails |
| Remove the caller check (`caller_tenants`) in `src/raglab/guard/tenant.py` | `uv run pytest tests/api/test_api.py` | The spoof (a tenant-a-only token asking as tenant B) is answered instead of 403 |
| Change one word of `SYSTEM` in `src/raglab/generate/prompts/answer_v1.py` | `uv run pytest tests/generation/test_prompt_snapshot.py` | The snapshot and the fingerprint tests fail: the prompt changed without a new VERSION |
| Commit with a message like `updated stuff` | `git commit` | The commit-msg hook refuses it: not a Conventional Commit |
| Change the chunker's default budget | `uv run pytest tests/ingestion/test_inventory_snapshot.py` | The snapshot test fails and prints the chunk diff; `make inventory-snapshot` regenerates it on purpose |

## Concepts already built

Read them in this order: the data, then ingestion, retrieval, evaluation, and the engineering
around them.

| Area | Concept | Where it lives | The test that shows it |
|---|---|---|---|
| Data | Planted features: facts put in the corpus so the right answer is known | `corpus/answer-key.yaml`, `corpus/SPEC.md` | `tests/unit/test_answer_key.py` |
| Data | Requirements traced to features (R-01 to R-23) | `docs/TEST-PLAN.md` part 1 | `tests/unit/test_test_plan.py` |
| Data | Licensed, attributed sources; visibly fake secrets | `corpus/SOURCES.md`, `corpus/LICENSE.md` | `tests/unit/test_corpus_sources.py`, `tests/unit/test_corpus_allowlist_scope.py` |
| Data | A deterministic build of the PDF, HTML and scanned page | `scripts/build_corpus.py` | `tests/unit/test_corpus_build.py` |
| Ingestion | One parser per format, with the PDF table read as rows | `src/raglab/ingest/` | `tests/ingestion/test_ingest_formats.py` |
| Ingestion | OCR measured by character error rate (0.22% against a 1% bar) | `src/raglab/ingest/ocr.py` | `tests/ingestion/test_ocr.py` |
| Ingestion | Section-aware chunking that keeps a rule with its exception | `src/raglab/chunk/sections.py` | `tests/ingestion/test_chunk_boundaries.py` |
| Ingestion | Chunk metadata (tenant, version, section, page) and deterministic ids | `src/raglab/core/types.py` | `tests/ingestion/test_chunk_metadata.py` |
| Ingestion | A chunking change shown as a reviewable diff | `corpus/inventory.snapshot.json` | `tests/ingestion/test_inventory_snapshot.py` |
| Retrieval | Ports and adapters: vendor SDKs only in `adapters/`, a fake for unit tests | `src/raglab/core/ports.py`, `src/raglab/adapters/`, `scripts/check_architecture.py` | `tests/unit/test_architecture.py` |
| Retrieval | A pinned, hash-checked local model; tests never touch the network | `src/raglab/adapters/fastembed_embed.py` | `tests/retrieval/test_local_embedder.py`, `tests/unit/test_no_network.py` |
| Retrieval | Tenant isolation that refuses rather than guesses | `src/raglab/core/types.py`, `src/raglab/index/memory.py` | `tests/retrieval/test_tenant_filter.py` |
| Retrieval | Dense, BM25 and hybrid by reciprocal rank fusion | `src/raglab/retrieve/` | `tests/retrieval/test_store_and_retrievers.py` |
| Evaluation | hit@k, MRR@k and recall@k against labelled sections | `src/raglab/evals/metrics.py` | `tests/unit/test_metrics.py` |
| Evaluation | Bootstrap intervals and a paired comparison with flipped questions | `src/raglab/evals/metrics.py`, `src/raglab/evals/compare.py` | `tests/retrieval/test_compare.py` |
| Evaluation | A golden set with a dev and test split and a datasheet | `datasets/golden.v1.jsonl`, `datasets/DATASHEET.md` | `tests/retrieval/test_golden_retrieval.py` |
| Evaluation | The run record: manifest, cases and report, with provenance and hashes | `schemas/run-record.v1.json`, `src/raglab/evals/record.py` | `tests/retrieval/test_run_record.py` |
| Evaluation | Publish, a baseline, and a no-regression gate with a written threshold | `src/raglab/evals/publish.py`, `src/raglab/evals/gate.py`, `docs/THRESHOLDS.md` | `tests/retrieval/test_publish.py` |
| Evaluation | Label groups: sections that state the same rule are one thing to find | `src/raglab/evals/golden.py` | `tests/unit/test_metrics.py`, `tests/retrieval/test_golden_retrieval.py` |
| Evaluation | The dataset hard stop: ten rules before every run and in pr-fast | `src/raglab/evals/dataset_check.py` | `tests/unit/test_check_dataset.py` |
| Evaluation | Behaviour cases: the decision label from the field, abstention as its own check, no judge | `src/raglab/evals/behaviour.py`, `src/raglab/evals/oracle.py` | `tests/generation/test_behaviour_checks.py` |
| Evaluation | The consistency gate (Q-05) with a margin set from runs, and a paired comparison of generation runs | `src/raglab/evals/gate.py`, `src/raglab/evals/compare.py` | `tests/generation/test_consistency_gate.py`, `tests/retrieval/test_compare.py` |
| Evaluation | The test split held out of every run but nightly and release | `src/raglab/evals/config.py`, `config/local-ollama-nightly.toml` | `tests/unit/test_held_out_split.py` |
| Engineering | Hardened CI: pinned actions; secret, dependency, SAST and workflow scans | `.github/workflows/pr-fast.yml` | `tests/unit/test_workflow_rules.py` |
| Engineering | The privacy check, Conventional Commits and git hooks | `scripts/check-forbidden.mjs`, `.githooks/` | `tests/unit/test_privacy_check.py`, `tests/unit/test_conventions.py` |

| Generation | A versioned prompt with chunks framed as data, and a strict parser | `src/raglab/generate/prompts/answer_v1.py` | `tests/generation/test_prompt_snapshot.py` |
| Generation | Guard layers: input limits, the tenant guard, the citation validator | `src/raglab/guard/`, `docs/GUARDRAILS.md` | `tests/generation/test_input_guards.py`, `tests/generation/test_citation_validator.py` |
| Generation | The fallback contract: no reply or a bad reply is never an answer | `src/raglab/generate/pipeline.py`, `src/raglab/adapters/openai_compat.py` | `tests/generation/test_fallback_contract.py`, `tests/contract/test_chat_contract.py` |
| Generation | Checks without a judge, Wilson intervals and pass^k | `src/raglab/evals/generation_record.py`, `src/raglab/evals/generation.py` | `tests/retrieval/test_run_record.py` |
| Engineering | An API that fails closed on tenant, with security headers, and a page with labels | `src/raglab/api/`, `src/raglab/web/` | `tests/api/test_api.py`, `tests/api/test_page.py`, `tests/e2e/test_e2e_fake.py` |
| Engineering | A local model for one session only, with usage guards | `src/raglab/runtime/ollama.py`, `docs/LOCAL-MODEL.md` | `tests/unit/test_ollama_session.py` |

Also worth a look: the progress diagram is itself tested (`tests/unit/test_diagram.py`), and the
playground reads only published runs (`tests/unit/test_playground.py`).

## Not testable yet

Judged quality starts in S5; S3 checks only what code can count.

| Capability | Arrives in |
|---|---|
| A deployed demo: the fake model first, then a real model with rate and budget limits | S3h (start of P3), then S10 |
| Behaviour cases (abstain, flag a conflict, refuse but help) and the dataset consistency gate | S4 (40 cases), S4b (about 120) |
| Judged metrics (faithfulness, relevancy), measured tokens, the provider and cost decision | S5 |
| A judge calibrated against human labels (kappa) | S6 |
| Prompt injection, poisoned documents, red team, Guardrails AI (the attack documents are in the corpus but kept out of the default ingest) | S7 |
| Every failure tagged with its cause, a suite audit and GATES.md | S8 |
| Tracing with redaction and a perf gate | S9 |
| Browser and accessibility tests of the UI and the playground | Track B |
| The teaching playground on Pages | S11, at go-public |
