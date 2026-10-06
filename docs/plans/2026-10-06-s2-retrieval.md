---
stage: S2
name: retrieval
nodes: [S2]
date: 2026-10-06
status: approved 2026-10-06
---

# S2: Retrieval without a judge, run record v1, minimal playground

Part of the main plan (phase P1, release v0.1). Branch: `feat/s2-retrieval`. Build project
stage 2 / how-to 17 step 3. Retrieval is scored against labelled chunks, so no model judges
anything.

## Goal

- Retrieve the right chunks for a question and measure how well: hit rate, MRR and recall@k
  against labelled chunk ids.
- Compare configurations fairly: a paired difference with a bootstrap interval, plus the
  questions whose outcome flipped.
- Write every evaluation as a **run record**, the format later gates and the playground read.
- Render the published runs in a first static playground.

## Out of scope

Generation and answers (S3), the golden set's behaviour cases (S4), judged metrics (S5) and
hosted embedders.

## What gets built

```
src/raglab/core/ports.py       + Embedder, VectorStore, Retriever protocols
src/raglab/adapters/fake.py    HashingEmbedder (deterministic; unit tests only)
src/raglab/adapters/fastembed_embed.py   local ONNX embedder (BAAI/bge-small-en-v1.5)
src/raglab/index/memory.py     in-memory cosine store (numpy), tenant filter that fails closed
src/raglab/retrieve/           dense, BM25 (rank-bm25), hybrid by reciprocal rank fusion
src/raglab/evals/metrics.py    hit@k, MRR, recall@k; paired diff; bootstrap interval (seeded)
src/raglab/evals/record.py     run record v1 writer and validator
schemas/run-record.v1.json     the schema (manifest + cases.jsonl + report.md)
datasets/golden.v1.jsonl       retrieval questions (kind: retrieval), labelled chunk ids, split dev/test
datasets/DATASHEET.md          how the questions were made and labelled, the mix, version, licence
cli: raglab eval --suite retrieval --config ...   raglab compare A B   raglab publish RUN
runs/published/<run_id>/       the baseline run (committed)
playground/                    static page: lists published runs, shows metrics and per-question results
```

**Carried over from S1b:** a table caption travels with its table in the chunker, so F-16 and F-17
hold at half size.

## Questions and labels

- **About 30 retrieval questions**, more than the build project's 20, because the pack is bigger.
  Each is written from the answer key and the requirements, covering every planted retrieval
  kind: plain, table-only, cross-reference, glossary, multi-hop (two labelled chunks), the scanned
  page, version and external conflicts, and tenant B.
- **Labels:** each question's relevant chunk ids, resolved through the stable section ids, so a
  re-chunk updates them mechanically and a test fails if a label goes missing.
- **Split:** dev and test, with the test split used only in nightly, release and the capstone.
- **Checking:** an independent reviewer checks every label against the chunk text. You confirm
  only the decisions the reviewer raises.

## Configurations compared (on the same questions)

1. dense (bge-small), k = 5;
2. hybrid: dense plus BM25, fused by reciprocal rank;
3. dense with chunk size 600, the S1b experiment, to show a chunking change measured end to end.

The report gives each metric with its value, a bootstrap 95% interval and n. Each pairwise
comparison gives the paired difference with its interval, and lists the flipped questions by id.

## Gate

pr-fast gets a no-regression gate: on the dev split, recall@5 of the default configuration must
not fall below the committed baseline run, with the threshold and its reason in
`docs/THRESHOLDS.md`. The embedder is real, so the numbers are real local numbers: provenance
`local`, model and version in the manifest.

## Choices I made (you can change them)

| Item | Choice | Why |
|---|---|---|
| Embedder | `fastembed` with `BAAI/bge-small-en-v1.5`: ONNX, about 67 MB, no PyTorch, Apache-2.0. Pinned model revision, inside `adapters/` | small enough for a laptop and CI, real semantic retrieval; the main plan's "small local ONNX embedder" |
| Model in CI | downloaded once in a setup step with the network on, cached by GitHub Actions by revision, then tests run offline (the no-network guard stays on for tests) | tests stay hermetic, and the download is cached |
| Vector store | in-memory, numpy cosine; Qdrant stays a later option behind the same port | 228 chunks need no database |
| BM25 | `rank-bm25` (pure Python, Apache-2.0) | the hybrid comparison from the main plan |
| Bootstrap | 2,000 resamples, fixed seed, recorded in the manifest | reproducible intervals |

## Decision needed: where the playground lives while the repo is private

GitHub Pages for a private repository needs a paid plan.
- **Option A (recommended):** build it as static files in `playground/`, open locally with
  `make playground`, and switch Pages on at go-public (added to GO-PUBLIC.md).
- **Option B:** make the repository public now and deploy Pages from S2.

## Acceptance criteria

| # | Criterion | Evidence |
|---|---|---|
| AC1 | Metrics are correct: hit@k, MRR, recall@k, paired diff and bootstrap match hand-computed values on small fixtures | `test_metrics.py` (unit) |
| AC2 | About 30 labelled questions (dev/test), every planted retrieval kind covered, labels resolve to existing chunks, a datasheet | `test_golden_retrieval.py`; reviewer evidence |
| AC3 | The tenant filter fails closed: a query without a tenant is refused, and no tenant B chunk is ever returned for tenant A | `test_tenant_filter.py`; **break:** remove the filter and the test fails |
| AC4 | `raglab eval --suite retrieval` writes a run record that validates against `schemas/run-record.v1.json` (manifest with git sha, config hashes, model and revision, seed, provenance; cases.jsonl; generated report.md) | `test_run_record.py` |
| AC5 | `raglab compare` gives paired differences with bootstrap intervals and flipped questions for the three configurations; the result is recorded in the ledger | ledger; `test_compare.py` |
| AC6 | The table caption stays with its table; F-16 and F-17 hold at chunk size 600; the inventory snapshot is updated with a reviewed diff. *Reworded by the user's decision (2026-10-06, "Accept and reword AC6 (Recommended)"): F-17 holds at 600 and F-16's table reads with its caption; F-16's note may split at 600* | `test_chunk_boundaries.py`; snapshot diff in the PR |
| AC7 | Embedder and SDK in `adapters/` only; HashingEmbedder used only by unit tests; deptry, vulture and pyright clean; tests offline | `make check`; architecture rules |
| AC8 | [CI] the model is fetched in setup and cached, tests run offline, and the recall@5 no-regression gate runs and passes | PR checks |
| AC9 | The minimal playground renders `runs/published/index.json` (run list, metrics with intervals, per-question hits) with no network and no model | Playwright later (Track B); for now a unit test of the generated index and a smoke check |
| AC10 | Diagram and README mark S2 done, plus a CHANGELOG line and a ledger | tests and CI |

## How it will run (orchestrated workflow)

1. **Build:** the developer builds the retrieval stack, metrics, run record, CLI, caption fix and
   playground.
2. **Questions:** a question author writes and labels the questions in parallel with the build,
   then the developer resolves the labels.
3. **Verify:** two Fable judges in clones. One checks the criteria and breaks; the other checks
   the labels and statistics (every label against its chunk text, the metric arithmetic, bootstrap
   determinism, and that no test-split question was used to tune anything).
4. **Confirm and fix:** each defect is reproduced, then one fix round. Product choices come to you.

## Approval

Your answers, verbatim (2026-10-06): playground: "Local until go-public (Recommended)"; plan: "Approve and start". So the playground is built as static files opened with `make playground`, and Pages is added to GO-PUBLIC.md.
