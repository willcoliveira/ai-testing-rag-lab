---
stage: S2
nodes: [S2]
---

# S2 ledger: retrieval, run record v1, playground

Plan: [2026-10-06-s2-retrieval.md](2026-10-06-s2-retrieval.md).

## Approval

The user's answers, verbatim (2026-10-06, quoted in the plan): playground: "Local until go-public
(Recommended)"; plan: "Approve and start".

## What was built (developer, 2026-10-06)

| Part | Where |
|---|---|
| Ports | `src/raglab/core/ports.py`: Embedder, VectorStore, Retriever; `core/types.py`: `ScoredChunk`, `REQUEST_TENANTS`, `visible_tenants` (fails closed: no tenant, an empty one, `shared` or an unknown one is refused), `check_visible` (the second line, on the way out) |
| Fake embedder | `src/raglab/adapters/fake.py`: HashingEmbedder (blake2b hashing trick, unit tests only; architecture rule 4: no module of raglab imports it) |
| Local embedder | `src/raglab/adapters/fastembed_embed.py`: BAAI/bge-small-en-v1.5 as ONNX through fastembed, from Qdrant/bge-small-en-v1.5-onnx-Q at revision `aa8f8b060edb00e03bfdd08813a2949946c8ba55`, five files each pinned by sha256; `raglab fetch-model` / `make model` downloads over https into `~/.cache/raglab/models` (or `RAGLAB_MODEL_DIR`); loading never downloads (`specific_model_path`) and refuses a missing or altered file; onnxruntime on one thread |
| Factory | `src/raglab/adapters/factory.py`: the only constructor of the real embedder; refuses another provider, model or revision |
| Store | `src/raglab/index/memory.py`: numpy cosine, tenant mask before ranking, ties by chunk id |
| Retrievers | `src/raglab/retrieve/`: dense; BM25 (rank-bm25 Okapi, one index per request tenant, so another tenant's chunks are neither ranked nor in the term statistics); hybrid (reciprocal rank fusion, 50 candidates each, rrf_k 60) |
| Metrics | `src/raglab/evals/metrics.py`: hit@k, reciprocal rank (MRR@k), recall@k with sections as the unit of relevance; paired differences; percentile bootstrap (2,000 resamples, `random.Random(seed)`, type 7 quantiles) |
| Golden loader | `src/raglab/evals/golden.py`: reads `datasets/golden.v1.jsonl` (`relevant: [{doc_id, section_id}]`), resolves each label to its section's chunks at the run's settings; a label with no chunk or one the asker's tenant cannot see stops the run |
| Configs | `src/raglab/evals/config.py` (strict TOML); `config/retrieval-dense.toml`, `retrieval-hybrid.toml`, `retrieval-dense-600.toml` |
| Run record v1 | `schemas/run-record.v1.json`; `src/raglab/evals/schema.py` (a JSON Schema subset that refuses unsupported keywords); `src/raglab/evals/record.py` (writer, generated report.md, validator: schema, run id, file hashes, per-case scores against ranks and labels, results recomputed, report re-rendered) |
| Suite | `src/raglab/evals/retrieval.py`: ingest at the config's settings, index, ask as each question's tenant, score, manifest (git sha and dirty flag, config, chunker, embedder and retriever hashes, dataset and corpus sha256, tools, seed, provenance) |
| CLI | `raglab eval --suite retrieval --config ...`, `raglab compare A B`, `raglab publish RUN [--baseline]`, `raglab gate --config ...`, `raglab fetch-model` |
| Publish | `src/raglab/evals/publish.py`: refuses an invalid, dirty, fake or partial run and any privacy hit (`node scripts/check-forbidden.mjs --dir`), copies to `runs/published/<run_id>/`, rebuilds `index.json` with baselines |
| Gate | `src/raglab/evals/gate.py`: recall@5 at least the baseline minus one question; a baseline with another dataset or config hash fails as stale (docs/THRESHOLDS.md) |
| Chunker | `src/raglab/chunk/sections.py`: a caption paragraph ("Table N: ...") right before a table is one unit with it, kept whole up to twice the budget; a longer table splits between rows with the caption leading |
| Playground | `playground/` (index.html with a strict CSP, model.js pure, app.js renders with textContent only, app.css); `make playground` serves `playground/` beside `runs/published/` on 127.0.0.1 (`scripts/serve_playground.py`); Pages added to docs/GO-PUBLIC.md as step 9 |
| CI | pr-fast: `actions/cache@55cc8345863c7cc4c66a329aec7e433d2d1c52a9 # v6.1.0` restores `~/.cache/raglab/models` keyed by `EMBED_MODEL_REVISION`, then `make model` (download on a miss, hashes always checked), tests with `HF_HUB_OFFLINE=1` |
| Architecture | `scripts/check_architecture.py`: fastembed, onnxruntime and huggingface_hub are vendor SDKs; rule 4 (fake adapters imported by no module) |
| Dependencies | runtime `fastembed==0.8.1`, `rank-bm25==0.2.2`, `numpy==2.5.3` (lock: onnxruntime 1.30.0, huggingface-hub 1.33.0, tokenizers 0.23.2); `typings/rank_bm25` stub for pyright strict; `.gitleaks.toml` allows the 64-hex model pins in the adapter only |

## Evidence per criterion (developer run, 2026-10-06, macOS arm64)

`make check` exits 0 with the question author's draft `datasets/golden.v1.jsonl` in the work tree
(599 tests passed). The real-dataset tests in `tests/retrieval/test_golden_retrieval.py` need that
file, which the question author commits.

| AC | Status | Evidence | Break (restored from git) |
|---|---|---|---|
| AC1 | met | `tests/unit/test_metrics.py`: per-case hit, RR and recall on seven hand-computed rankings (a section split into two chunks counts once), means, type 7 quantiles (also against `statistics.quantiles(method="inclusive")`), paired difference 0.125 by hand, bootstrap of a constant, of [0, 1] (both ends), seeded and reproducible, near the normal approximation | RR as 1/(rank + 1): 5 failures across metrics, run record and compare tests; interval tail as 1 - level: 1 failure |
| AC2 | pending (question author, reviewer) | `tests/retrieval/test_golden_retrieval.py`: loader and resolver on small inputs; on the draft file: 34 retrieval questions (22 dev, 12 test), both tenants, the planted kinds, every label resolves at 1,200 and at 600 | (the file is the author's) |
| AC3 | met | `tests/retrieval/test_tenant_filter.py`: no tenant, empty, `shared`, unknown refused by every retriever; on fixtures and on the whole pack (every chunk's text asked as the other tenant, k 20) no cross-tenant chunk, for dense, BM25 and hybrid | store filter removed: 7 failures (dense and hybrid; `check_visible` raised TenantError); filter and both output checks removed: "dense: A-PWD-V1@1.0/1/1 asked as tenant-b returned ['A-PWD-V1@1.0/1/1', ...]"; BM25 filter removed: TenantError "chunk B-1@1.0/1/1 of tenant-b was retrieved for tenant-a" |
| AC4 | met (fake embedder); the real run follows the questions | `tests/retrieval/test_run_record.py`: a run writes manifest, cases and report that validate; git sha, dirty flag, config file and resolved hashes, chunker, embedder and retriever hashes, model and revision, seed, provenance; eight broken manifests rejected by the schema; edited cases and report caught; same inputs give the same results. A real `raglab eval` with bge-small on the draft file validated (`record.validate` returned no problem) and passed the privacy check (0 hits); its numbers are from a dirty tree and are not recorded | report check disabled in the validator: 1 failure; dirty-run refusal disabled: 1 failure (publish) |
| AC5 | mechanism met; result pending | `tests/retrieval/test_compare.py`: paired differences, intervals and flipped ids against hand values; unpaired runs refused (k, dataset, case ids, an invalid record). The three-configuration result goes here after the committed questions and a clean run | (covered by the RR break above) |
| AC6 | partly met (decision below) | `tests/ingestion/test_chunk_boundaries.py`: at 600 the caption and Table 1 share a chunk with every row; F-17 holds; F-16 splits only on the note after the table; positive control at 250; three unit tests (over the budget, over twice the budget, a caption only right before a table). `make inventory-snapshot`: no diff (228 chunks, 0 changed); `chunk_experiment.py --chunk-size 600`: 249 chunks (was 250), 1 feature split (was 2) | (the 600 test is the S1b break turned into a check) |
| AC7 | met | `make check`: deptry, vulture, pyright clean; architecture 0 violations; tests offline (`tests/unit/test_no_network.py` guard on, the model loaded from the cache) | `from raglab.adapters.fake import HashingEmbedder` and `import fastembed` in `retrieve/dense.py`: "raglab.adapters.fake is for the unit tests; no module imports it", "vendor SDK fastembed is imported outside raglab.adapters" |
| AC8 | needs CI | `tests/unit/test_workflow_rules.py::test_pr_fast_restores_and_fetches_the_model_by_revision_before_the_tests`; zizmor: no findings. The gate step is not wired yet (see below) | `make model` step replaced: "assert 'echo skipped' == 'make model'" |
| AC9 | met (unit and smoke; browser in Track B) | `tests/unit/test_playground.py`: model.js renders a published index (run list, intervals, per-question hits and labelled ids) in Node; app.js itself runs against two published runs with a stand-in DOM and fetch (`tests/playground_dom.mjs`): run list newest first, metrics and question tables, a click on the other run, no error in the status line, only `runs/published/` fetched; paths outside it refused; CSP and no HTML writes; scripts parse; the local site holds only the playground and the published runs. Served from a scratch site, the page, scripts and index answered 200. No real browser render this round (the browser extension was not connected) | `fetchText` path prefixed with `../`: the app.js test fails (status line shows the fetch error) |
| AC10 | pending | CHANGELOG line, this ledger, docs/TEST-PLAN.md rows L10, L11, R2, R3; the diagram moves to done when the stage closes | |

## Still to do in this stage

1. The question author commits `datasets/golden.v1.jsonl` and `datasets/DATASHEET.md`; the
   reviewer checks the labels.
2. From a clean commit: `raglab eval` with the three configs, `raglab compare` dense with hybrid
   and dense with dense-600 (result into AC5 above), `raglab publish <dense run> --baseline`
   (with the others published or not), commit `runs/published/`.
3. Measure the Mac-to-CI difference (dense, dev, in `ubuntu:24.04` with the pinned Tesseract)
   and set the gate margin from it. Then wire the gate: a pr-fast step `uv run raglab gate --config config/retrieval-dense.toml` after
   the tests (and a `make gate` target in `check`), with its workflow test; break it once.
4. Diagram and README: S2 done.

## Decision needed

**F-16 at chunk size 600.** The caption now travels with its table, and F-17 holds at 600. F-16
also cites the note under the table ("The Status column shows Approved while an exception is in
force"): caption, table and note are 794 characters, which no chunk of 600 can hold. Options:

- (a) accept that F-16 splits at 600 (what the experiment measures; the default 1,200 keeps
  everything together); or
- (b) also bind a table's following note (a paragraph that names one of its columns) to the
  table, so a chunk may grow to about 800 at size 600.

The developer built (a)'s state and recommends it: (b) is a rule fitted to one paragraph.

## Choices made in the build (for the review)

1. **Sections are the unit of relevance.** A label is a section; it is found when any of its
   chunks is in the top k, so dense-600 has the same number of things to find as dense-1200.
2. **MRR is MRR@5**: a first relevant chunk below rank 5 scores 0.
3. **The bootstrap uses `random.Random(seed)`**, not numpy, so intervals do not move with a numpy
   upgrade; the validator recomputes them from the cases.
4. **Scores and latency in cases.jsonl are rounded** (6 and 3 places); the results are computed
   from the rounded per-case values, so a validator reproduces them exactly.
5. **No chunk text in a run record**: ids, scores and labels only; questions are included (our
   own text, checked by the privacy scan on publish).
6. **git_dirty counts untracked files**, so a run with an uncommitted dataset cannot be published.
7. **Model files outside the checkout** (`~/.cache/raglab/models`), so the secret and privacy
   scans never read 67 MB of ONNX, and CI caches the same path.
8. **The gate margin is one question, provisionally** (docs/THRESHOLDS.md): the scanned page's
   OCR differs between the Mac (Tesseract 5.5.3) and CI (5.3.4), and one dev question labels that
   page, besides ONNX last-bit differences. Before the gate is wired, the dense dev run is repeated
   in the `ubuntu:24.04` image with the pinned Tesseract and the margin is set from what it shows.
