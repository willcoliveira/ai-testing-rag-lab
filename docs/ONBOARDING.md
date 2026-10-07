# Onboarding

This guide covers what you can run today, what you can break on purpose to learn what each test
guards, and where each concept already lives. It is current as of S2 (2026-10-06). Every stage
that adds a command or a concept updates it, and `tests/unit/test_onboarding.py` checks that
every path, `make` target and `raglab` command named here exists.

The lab is a policy Q&A assistant over a fictional company's identity and security policy pack.
Up to S2 it ingests the pack, retrieves from it with a real local embedding model, and scores
retrieval against labelled questions. No model writes an answer yet; that starts in S3.

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
| `make check` | Every offline gate: format, lint, types, dependency and security scans, privacy, architecture, tests, the retrieval gate | All tests pass, then `recall@5 0.644 (n 22) passes ... 0.598` |
| `uv run raglab ingest` | The pack parsed and chunked into `runs/tmp/inventory.json` | 228 chunks from 21 documents |
| `uv run raglab ingest --chunk-size 600 --compare corpus/inventory.snapshot.json` | A chunking change as a reviewable diff | 249 chunks, with the changed ids listed |
| `uv run python scripts/chunk_experiment.py --chunk-size 600` | Which planted features a smaller chunk breaks | 0 split at 1,200 and 1 split at 600 (F-16) |
| `uv run raglab eval --suite retrieval --config config/retrieval-dense.toml` | One retrieval run, written as a run record | A folder in `runs/tmp/` with `manifest.json`, `cases.jsonl` and `report.md`; recall@5 0.644 |
| The same with `config/retrieval-hybrid.toml`, then `uv run raglab compare <dense run> <hybrid run>` | A paired comparison with bootstrap intervals and the questions that flipped | Every interval contains 0; only hybrid finds R-Q10; only dense finds R-Q02 and R-Q14 |
| `make gate` | The no-regression gate that pr-fast runs | The pass line above |
| `make playground` | The published runs in a browser | http://127.0.0.1:8000/ listing three runs with per-question hits |
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
| Make dense retrieval drop its best hit (return ranks 2 to 6) in `src/raglab/retrieve/dense.py` | `make gate` | `recall@5 0.318 (n 22) fails: the threshold is ... 0.598` |
| Reword one question in `datasets/golden.v1.jsonl`, keeping its labels | `make gate` | The baseline has another `dataset.sha256`: publish a new baseline in a reviewed pull request |
| Point R-Q02's label at a section that does not exist (A-LIFE 6.2) | `make gate` | `R-Q02: A-LIFE section 6.2 has no chunk` |
| Shrink the chunk budget until rules lose their exceptions | `uv run python scripts/chunk_experiment.py --chunk-size 250` | 7 features split, each with the closest chunk and the sentence it lacks; F-15 shows the MFA rule cut from its break-glass exception |
| Import `fastembed` in `src/raglab/retrieve/dense.py` | `make architecture` | Vendor SDK fastembed is imported outside `raglab.adapters` |
| Disable the tenant check (`tenant_problems`) in `src/raglab/evals/record.py` | `uv run pytest tests/retrieval/test_publish.py` (it forges a copy of the baseline with a tenant B chunk in a tenant A case) | The forgery test fails: the forged record now validates and would publish |
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
| Engineering | Hardened CI: pinned actions; secret, dependency, SAST and workflow scans | `.github/workflows/pr-fast.yml` | `tests/unit/test_workflow_rules.py` |
| Engineering | The privacy check, Conventional Commits and git hooks | `scripts/check-forbidden.mjs`, `.githooks/` | `tests/unit/test_privacy_check.py`, `tests/unit/test_conventions.py` |

Also worth a look: the progress diagram is itself tested (`tests/unit/test_diagram.py`), and the
playground reads only published runs (`tests/unit/test_playground.py`).

## Not testable yet

Anything that needs an answer from a model starts in S3.

| Capability | Arrives in |
|---|---|
| Answers with citations, abstention ("the documents do not say") and conflict flags | S3 |
| A live local model run on Ollama, repeated, with pass^k | S3 |
| The API (`/healthz`, `/version`), web UI, container and a ZAP baseline scan | S3 |
| The first guardrails: input limits and a citation validator | S3 |
| A deployed demo: the fake model first, then a real model with rate and budget limits | S3h, then S10 |
| Behaviour cases (abstain, flag a conflict, refuse but help) and the dataset consistency gate | S4 (40 cases), S4b (about 120) |
| Judged metrics (faithfulness, relevancy), measured tokens, the provider and cost decision | S5 |
| A judge calibrated against human labels (kappa) | S6 |
| Prompt injection, poisoned documents, red team, Guardrails AI (the attack documents are in the corpus but kept out of the default ingest) | S7 |
| Every failure tagged with its cause, a suite audit and GATES.md | S8 |
| Tracing with redaction and a perf gate | S9 |
| Browser and accessibility tests of the UI and the playground | Track B |
| The teaching playground on Pages | S11, at go-public |
