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
| Golden set v1 | `datasets/golden.v1.jsonl` and `datasets/DATASHEET.md` (question author): 34 retrieval questions, 22 dev and 12 test, stratified by kind; 30 asked as tenant A, 4 as tenant B; labels at section level, resolved to chunk ids at run time |
| Integration | `raglab eval --split` (dev, test or all) (`evals/config.with_split`: the split is in the resolved config, so its sha256 and the run id say which questions ran); `runs/published/` with the dense dev baseline and the hybrid and dense-600 dev runs; `make gate` in `make check` and the pr-fast step "Retrieval no-regression gate (offline)" after the tests |
| Dependencies | runtime `fastembed==0.8.1`, `rank-bm25==0.2.2`, `numpy==2.5.3` (lock: onnxruntime 1.30.0, huggingface-hub 1.33.0, tokenizers 0.23.2); `typings/rank_bm25` stub for pyright strict; `.gitleaks.toml` allows the 64-hex model pins in the adapter only |

## Evidence per criterion (developer, 2026-10-06, macOS arm64)

`make check` exits 0 with the gate as its last target: 607 tests passed, and the gate printed
the line quoted under AC8. Each break was made on a committed file and restored with `git checkout`.

| AC | Status | Evidence | Break (restored from git) |
|---|---|---|---|
| AC1 | met | `tests/unit/test_metrics.py`: per-case hit, RR and recall on seven hand-computed rankings (a section split into two chunks counts once), means, type 7 quantiles (also against `statistics.quantiles(method="inclusive")`), paired difference 0.125 by hand, bootstrap of a constant, of [0, 1] (both ends), seeded and reproducible, near the normal approximation | RR as 1/(rank + 1): 5 failures across metrics, run record and compare tests; interval tail as 1 - level: 1 failure |
| AC2 | met by the tests; the independent label review is the verify step | `tests/retrieval/test_golden_retrieval.py` on the committed file: 34 questions (22 dev, 12 test), both tenants; every line has an `R-Qnn` id, one of the datasheet's 12 kinds and feature ids that exist in `corpus/answer-key.yaml`; every kind has questions in both splits, one in test; the planted kinds (table-only, cross-reference, glossary, multi-hop with two or more labels, the scanned page, version and external conflicts, tenant B); tenant B questions label only tenant B documents and tenant A questions only tenant A or the shared `X-*` excerpts (from `corpus/register.yaml`); every label resolves to chunks the asker may see at 1,200 and at 600; with A-GLOSS 10 removed from the real inventory the run stops with "R-Q10: A-GLOSS section 10 has no chunk" and the same for R-Q12, and nothing else. Loader and resolver also on small inputs. `datasets/DATASHEET.md`. The rule for a section with several chunks (found when any of its chunks is in the top k) is now stated in the datasheet and in `raglab.evals.golden` | label of R-Q02 changed to A-LIFE 6.2 in the committed file: `raglab gate` stops with "labels that do not resolve: R-Q02: A-LIFE section 6.2 has no chunk" |
| AC3 | met | `tests/retrieval/test_tenant_filter.py`: no tenant, empty, `shared`, unknown refused by every retriever; on fixtures and on the whole pack (every chunk's text asked as the other tenant, k 20) no cross-tenant chunk, for dense, BM25 and hybrid | store filter removed: 7 failures (dense and hybrid; `check_visible` raised TenantError); filter and both output checks removed: "dense: A-PWD-V1@1.0/1/1 asked as tenant-b returned ['A-PWD-V1@1.0/1/1', ...]"; BM25 filter removed: TenantError "chunk B-1@1.0/1/1 of tenant-b was retrieved for tenant-a" |
| AC4 | met | `tests/retrieval/test_run_record.py` (fake embedder); the six real runs below each validated on writing (`raglab eval` exits non-zero on an invalid record), were made from clean commit `5f1d3a0` (`git_dirty: false`), provenance `local`, model BAAI/bge-small-en-v1.5 at `aa8f8b0`; the three published ones validate again in `tests/retrieval/test_publish.py::test_the_committed_runs_are_valid_local_dev_runs_with_a_current_baseline` and passed the privacy check on publish | report check disabled in the validator: 1 failure; dirty-run refusal disabled: 1 failure (publish) |
| AC5 | met | `tests/retrieval/test_compare.py`; the three configurations compared on dev and on the full set, results below | (covered by the RR break above) |
| AC6 | not met as written; reworded by the user's decision (below): F-17 holds at 600 and F-16's table reads with its caption | `tests/ingestion/test_chunk_boundaries.py`: at 600 the caption and Table 1 share a chunk with every row; F-17 holds; F-16 splits only on the note after the table; positive control at 250; three unit tests. `make inventory-snapshot`: no diff (228 chunks, 0 changed); `chunk_experiment.py --chunk-size 600`: 249 chunks (was 250), 1 feature split (was 2) | (the 600 test is the S1b break turned into a check) |
| AC7 | met | `make check`: deptry, vulture, pyright clean; architecture 0 violations; tests offline (`tests/unit/test_no_network.py` guard on, the model loaded from the cache) | `from raglab.adapters.fake import HashingEmbedder` and `import fastembed` in `retrieve/dense.py`: "raglab.adapters.fake is for the unit tests; no module imports it", "vendor SDK fastembed is imported outside raglab.adapters" |
| AC8 | needs CI; local and CI-image evidence met | pr-fast: model cache and `make model` before the tests (`test_pr_fast_restores_and_fetches_the_model_by_revision_before_the_tests`); the gate step "Retrieval no-regression gate (offline)" runs `make gate` with `HF_HUB_OFFLINE=1` after the model, Tesseract and the tests (`test_pr_fast_runs_the_retrieval_gate_offline_after_the_tests`, which also checks that `make check` runs `gate`); zizmor: no findings. Locally `make gate`: "recall@5 0.644 (n 22) passes: the threshold is the baseline 0.644 (20261006T172928Z-retrieval-dense-dev-5f1d3a0) minus one question (1/22), 0.598". CI-image run below. To confirm on the PR: pr-fast green and its gate log line | (1) gate step removed from pr-fast.yml: "'Retrieval no-regression gate (offline)' is not in list", 1 failed; (2) margin made two questions in `gate.py`: `test_the_gate_passes_within_one_question_and_fails_below` fails ("assert not True"); (3) a real regression, dense returning ranks 2 to 6 (`store.search(..., k + 1)[1:]` in `retrieve/dense.py`): `make gate` fails, "recall@5 0.318 (n 22) fails: the threshold is ... 0.598"; (4) one question's wording changed in the committed golden file (labels still resolve): "the baseline ... has another dataset.sha256 (ffb8c5a5... vs e9c3e832...): publish a new baseline in a reviewed pull request", exit 1 |
| AC9 | met (unit and smoke; browser in Track B) | `tests/unit/test_playground.py`: model.js renders a published index in Node; app.js runs against two published runs with a stand-in DOM and fetch (`tests/playground_dom.mjs`); paths outside `runs/published/` refused; CSP and no HTML writes. `runs/published/index.json` now holds three real runs, rebuilt identically by `publish.build_index` (test above). No real browser render this round | `fetchText` path prefixed with `../`: the app.js test fails |
| AC10 | met | S2 `done` in docs/ARCHITECTURE.md and README (`tests/unit/test_diagram.py`); the CHANGELOG S2 line extended (golden set, published runs, gate); this ledger; docs/TEST-PLAN.md rows R2 and R3 name the new tests | |

A note on breaks: after a break that keeps a file's size and is restored within the same second,
Python may run the stale bytecode (the `.pyc` checks mtime in seconds and size). That happened once
here (the margin break left `gate.py`'s compiled two-question margin in place, visible as a
threshold of 0.553); the cached file was removed and the runs were repeated. Every number above is
from a run after that.

## Results (2026-10-06, commit 5f1d3a0, clean tree, macOS arm64, Tesseract 5.5.3)

bge-small-en-v1.5 (ONNX, revision `aa8f8b0`), k = 5, bootstrap 2,000 resamples, seed 20261006,
95% percentile intervals. Labels are sections; a section is found when any of its chunks is in
the top 5.

**Dev split (22 questions), the published runs**

| Config | Run | hit@5 | MRR@5 | recall@5 |
|---|---|---|---|---|
| dense, 1,200 (default, **baseline**) | `20261006T172928Z-retrieval-dense-dev-5f1d3a0` | 0.773 (0.591 to 0.909) | 0.564 (0.390 to 0.739) | 0.644 (0.470 to 0.811) |
| hybrid (dense + BM25, RRF), 1,200 | `20261006T172957Z-retrieval-hybrid-dev-5f1d3a0` | 0.727 (0.545 to 0.909) | 0.548 (0.368 to 0.730) | 0.606 (0.424 to 0.773) |
| dense, 600 | `20261006T173026Z-retrieval-dense-600-dev-5f1d3a0` | 0.773 (0.591 to 0.909) | 0.590 (0.406 to 0.767) | 0.621 (0.447 to 0.788) |

**Full set (34 questions: dev and test), not published**

| Config | hit@5 | MRR@5 | recall@5 |
|---|---|---|---|
| dense, 1,200 | 0.824 (0.706 to 0.941) | 0.654 (0.520 to 0.789) | 0.696 (0.559 to 0.824) |
| hybrid, 1,200 | 0.735 (0.588 to 0.882) | 0.520 (0.380 to 0.665) | 0.627 (0.480 to 0.775) |
| dense, 600 | 0.824 (0.706 to 0.941) | 0.671 (0.533 to 0.808) | 0.681 (0.549 to 0.809) |

**Paired differences (`raglab compare`, B minus A, 95% paired bootstrap interval)**

| Split | A → B | hit@5 | MRR@5 | recall@5 | Flipped (hit) |
|---|---|---|---|---|---|
| dev | dense → hybrid | -0.045 (-0.182 to +0.091) | -0.016 (-0.222 to +0.172) | -0.038 (-0.174 to +0.098) | found by hybrid only: R-Q10; by dense only: R-Q02, R-Q14 |
| dev | dense → dense-600 | +0.000 (+0.000 to +0.000) | +0.026 (-0.019 to +0.102) | -0.023 (-0.068 to +0.000) | none; recall lower on R-Q22, MRR higher on R-Q25, lower on R-Q01 and R-Q22 |
| all | dense → hybrid | -0.088 (-0.235 to +0.059) | -0.134 (-0.302 to +0.027) | -0.069 (-0.216 to +0.083) | 2 found by hybrid only, 5 by dense only (the dev ones above plus 1 and 3 test questions) |
| all | dense → dense-600 | +0.000 (+0.000 to +0.000) | +0.017 (-0.012 to +0.066) | -0.015 (-0.044 to +0.000) | none; the test questions are unchanged |

Reading:
- Every interval of a difference contains 0: at n 22 (or 34) none of the three configurations is
  shown better or worse. Hybrid is lower on every point estimate, and the flips go both ways.
  The default stays dense at 1,200, as the plan set it; nothing was chosen from these numbers,
  and the full set (which holds the test split) was run only to report it.
- Chunk size 600 changes no hit. It loses one section on R-Q22: X-NIST 3.2.2, which at 600 is
  two chunks, neither in the top 5 (at 1,200 its one chunk was at rank 4); it also moves a few
  first ranks.
- Dense misses five dev questions: both table-only ones (R-Q04, R-Q05: Table 1 of the PDF),
  R-Q10 (glossary), R-Q18 (version conflict) and R-Q33 (misspelling). Hybrid finds R-Q10.
- The FAQ decision (1 below) moves these numbers: in the baseline's top 5 lists, the FAQ copy of
  R-Q18's answer (FAQ Q2) is at rank 2, so with "any one of the group" labels R-Q18 would be a
  hit, and R-Q19, R-Q21 and R-Q25 would have a higher first rank. That is read from the lists, not
  from a run.
- **The FAQ decision also reverses the dense-to-hybrid comparison** (the labels judge's S2-L1,
  recomputed from the published dev cases with the FAQ copy counting for its primary section):
  hit@5 becomes dense 0.818, hybrid 0.864, dense-600 0.818, and recall@5 0.682, 0.720 and 0.659.
  Hybrid gains R-Q14, R-Q18 and R-Q33 (FAQ Q3, Q2 and Q1 in its top 5); dense gains only R-Q18.
  The paired difference dense to hybrid becomes +0.045 (-0.091 to +0.182) on hit@5 and +0.038
  (-0.114 to +0.197) on recall@5. Every interval still contains 0. So "hybrid is lower" above holds
  only under primary-only labels; it is not a finding about hybrid.

**Mac and the CI image (the gate margin).** The dense dev run repeated at commit `dbd7c63` (same
dataset, config and code path) in `ubuntu:24.04` linux/amd64 under Docker on the Mac, with
`tesseract-ocr=5.3.4-1build5` and `tesseract-ocr-eng=1:4.1.0-2` as pr-fast pins and Python 3.13
from uv: the same top 5 chunk ids, in the same order, for all 22 questions, so the same metrics
(recall@5 0.644). The largest score difference was 0.0010, on the scanned page's chunk
(A-DEVICE-B 1, whose OCR text differs, so the corpus sha256 differs); every other chunk was within
0.0002. The closest labelled chunk to the rank-5 boundary in the baseline is 0.0021 away (R-Q22,
from a k = 20 listing), about twice the largest difference. So the margin stays at one question
(docs/THRESHOLDS.md): a zero margin could fail on arithmetic alone, and one flipped section moves
recall@5 by 0.023 at most for a two-label question. This was an emulated amd64, not the GitHub
runner; the PR's gate log is the runner's own number.

## Still to do in this stage

1. Verify: done (see "Judges and fixes" below).
2. CI on the PR: pr-fast green, with the model step and the gate's log line.

## Decisions needed

**From the question author (the reviewer or you confirm):**

1. **FAQ near-duplicates (F-53).** Only the primary section is labelled, so a retriever that
   returns only the FAQ copy scores a miss on R-Q14, R-Q18, R-Q19, R-Q21, R-Q23, R-Q25 and R-Q33.
   Adding the FAQ sections to `relevant` would make recall demand both copies. The fix is a schema
   choice: label groups where any one member counts. Open; the effect on the baseline is above.
2. **A section with several chunks** (X-NIST 3.1.1.2 has /1 and /2; R-Q21's expiry sentence is in
   /1). Decided in the build and now stated in the datasheet and `raglab.evals.golden`: the
   section is found when any of its chunks is in the top k. Generous for R-Q21 if only /2 comes
   back; S5's judged metrics check the answer itself. Confirm or change.
3. **Pointer sections are labelled** for cross-references (R-Q07 A-PRIV 8.1, R-Q08 A-PWD-V2 4.4,
   R-Q09 A-LIFE 5.4): a retriever that jumps straight to the target gets the hit but lower recall.
4. **R-Q19 and R-Q20 label version 1.0 too** (history questions), on purpose unlike the answer
   key's `expected_retrieval` for F-05 and F-07 (version 2.0 only).

**From the build:**

5. **F-16 at chunk size 600.** The caption now travels with its table, and F-17 holds at 600. F-16
   also cites the note under the table: caption, table and note are 794 characters, which no
   chunk of 600 can hold. (a) accept that F-16 splits at 600 (the default 1,200 keeps everything
   together), or (b) also bind a table's following note to the table. The developer recommends
   (a): (b) is a rule fitted to one paragraph.
6. **The gate margin is one question**, set from the CI-image measurement above, where the task
   text says recall@5 "must not fall below the published baseline". A zero margin is a one-line
   change in `raglab.evals.gate` and its test, at the risk of a failure from arithmetic alone
   (R-Q22 sits 0.0021 from the boundary).

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
8. **The gate margin is one question** (docs/THRESHOLDS.md), set from the CI-image run above:
   no difference in any top 5, scores within 0.0010, the closest labelled chunk 0.0021 from the
   boundary.
9. **Runs are published for the dev split only.** The full-set runs stay in `runs/tmp` (their
   per-question results include the test split, which is never used to choose anything);
   `tests/retrieval/test_publish.py` checks that every published case is a dev case.
10. **`raglab eval --split`** runs a committed config on another split instead of adding three
   more config files; the split is in the resolved config, so the run says which questions ran.

## Judges and fixes

Fix round 1, 2026-10-06. Four of the judges' findings were confirmed, all low: D2 and D3 (code)
and S2-L2 and S2-L4 (labels). Every new test was run against
the unfixed commit `e4ea4e8` in a scratch copy of the tree (`git archive`, with only the four test
files replaced): 11 failures, every one an assertion on the missing behaviour. The guard
`test_every_label_is_a_location_of_one_of_its_features` passes there too, as it should: it pins
the label policy the datasheet now states, not a defect. After the fixes, `make check` exits 0
with 619 tests (607 before), and the gate printed the same line as under AC8: "recall@5 0.644
(n 22) passes: the threshold is the baseline 0.644 (20261006T172928Z-retrieval-dense-dev-5f1d3a0)
minus one question (1/22), 0.598".

| Defect | Severity | Fix | Test (fails on e4ea4e8) | Commit |
|---|---|---|---|---|
| D2: a retrieval question with no `relevant` field was reported by file line only ("golden.v1.jsonl:24: ..."), while a label that does not resolve names its question | low | `golden.parse_line` reads the id first, and every later `DatasetError` names the line and the question ("golden.v1.jsonl:24 (R-Q24): a retrieval question needs at least one relevant section") | `test_golden_retrieval.py::test_an_error_after_the_id_names_the_question` (four errors: no relevant, tenant, question, a label field), `::test_a_committed_question_without_relevant_is_named_by_its_id` (the judge's repro on a copy of the committed file) | bd0a6f0 |
| D3: `record.validate` did not check whose chunks a case shows, so a hand edit putting B-PWD 1.0 3.1 into tenant A's R-Q01, with flags, scores, results, report and hashes made to agree, validated, and publish and the gate trusted it | low | `validate` reads `corpus/register.yaml` (`raglab.ingest.register`) and refuses every retrieved or labelled chunk id whose document is not in the register or belongs to a tenant the case's tenant may not see; an unreadable register is a problem, so the check fails closed. The test support's `lab_root` now writes a register of the small runs' documents | `test_run_record.py::test_a_record_that_shows_another_tenants_chunk_is_refused`, `::test_a_tenant_b_label_on_a_tenant_a_case_is_refused`, `::test_shared_chunks_pass_and_an_unregistered_document_is_refused`, `::test_a_root_without_a_register_fails_closed`; `test_publish.py::test_a_published_run_edited_to_show_another_tenants_chunk_is_refused` (the judge's repro on a copy of the dense baseline: validate and publish both refuse it). The committed-runs test gets the check through `validate`: the three published runs pass it | 8d312b9 |
| S2-L2: R-Q14 labels A-MFA 3.2 (the factors that are not approved), though the question asks which methods are allowed and by when | low | no label change. The datasheet now states the policy both label findings turn on: labels follow the feature's reference answer, so R-Q14 keeps 3.2 (F-23's reference answer says SMS and voice-call codes are not allowed), with its cost | `test_golden_retrieval.py::test_the_datasheet_states_the_label_scope_the_review_raised` (also asserts the labels as they stand); guard `::test_every_label_is_a_location_of_one_of_its_features` | be05c6e |
| S2-L4: Device Policy 6.2 restates the expiry rule for the USB block and is as relevant to R-Q25 as the labelled A-EXC 4.2, but is not labelled | low | no label change, under the same policy: F-17 does not list 6.2 and its reference answer is complete without it, and labelling it next to A-EXC 4.2 would make recall demand two statements of one rule, as with the FAQ near-duplicates (decision 1). The exception-question rule now names the A-EXC sections, and the known-limits FAQ note includes 6.2 | the same two tests; adding 6.2 to R-Q25 fails the guard until the answer key lists it | be05c6e |

**No label or metric changed,** so no run was repeated: the published runs, the baseline and the
results tables above stand as they are (old and new are the same numbers). For the decision
below, the effect of the other choice, recomputed from the published dev cases (not from a run):

| Config | recall@5 now | R-Q14 without A-MFA 3.2 | R-Q25 with A-DEVICE 6.2 |
|---|---|---|---|
| dense, 1,200 (baseline) | 0.644 | 0.652 (R-Q14 0.333 to 0.500) | 0.640 (R-Q25 0.333 to 0.250) |
| hybrid, 1,200 | 0.606 | 0.606 (R-Q14 finds nothing) | 0.602 |
| dense, 600 | 0.621 | 0.629 | 0.617 |

hit@5 and MRR@5 do not move in either case. A label change also changes the dataset's sha256, so
the baseline would have to be re-run and republished in the same pull request (the gate calls it
stale otherwise).

Notes for the review:

- `scripts/check_architecture.py` already listed fastembed, onnxruntime and huggingface_hub as
  vendor SDKs from the build; nothing to extend.
- The plan says multi-hop questions have "two labelled chunks"; the datasheet says one section
  per hop, "two or three", and R-Q14 has three. The approved plan is left as approved.
- `raglab.evals.record` now imports `raglab.ingest.register` (YAML stays inside `raglab.ingest`;
  architecture check: 0 violations). A run whose documents are not in the register, such as a
  later attack run over files outside it, will need those documents' tenants from somewhere the
  validator trusts; S7 decides where.
- `docs/TEST-PLAN.md`: R2 names the label-policy guard, R3 the two record-tenant tests.

Pending decisions (titles; the first six are under "Decisions needed" above):

1. FAQ near-duplicates (F-53)
2. A section with several chunks
3. Pointer sections are labelled
4. R-Q19 and R-Q20 label version 1.0 too
5. F-16 at chunk size 600
6. The gate margin is one question
7. Label scope of R-Q14 and R-Q25 (S2-L2, S2-L4): keep the labels as the feature's reference
   answer gives them (done this round), or drop A-MFA 3.2 from R-Q14 and add A-DEVICE 6.2 to
   R-Q25 (with an F-17 location in the answer key), re-running and republishing the baseline

## The user's decisions (2026-10-06)

Asked as four questions; the answers, verbatim:

| Decision | Answer | What it means |
|---|---|---|
| 1. FAQ near-duplicates (F-53) | "Defer to S4 (Recommended)" | primary-only labels stay; the caveat is in the datasheet and in the Reading above; S4 designs label groups where any one member counts, when it rebuilds the golden set and republishes the baseline |
| 5. F-16 at chunk size 600 | "Accept and reword AC6 (Recommended)" | AC6 is not met as written; it now reads "the caption stays with its table; F-17 holds at 600 and F-16's table reads with its caption; the snapshot is updated with a reviewed diff". F-16 splits at 600 only on the note after the table; the default 1,200 keeps it whole |
| 6. Gate margin | "One question (Recommended)" | recall@5 may fall by at most one question (1/22) below the baseline, as docs/THRESHOLDS.md gives the reason; the GitHub runner's gate line on the PR is the first check of it |
| 2, 3, 4 and 7. Label rules | "Accept all four (Recommended)" | a section with several chunks is found when any chunk is; pointer sections are labelled; R-Q19 and R-Q20 label v1 too; labels follow the feature's reference answer (R-Q14 keeps A-MFA 3.2, A-DEVICE 6.2 stays unlabelled). Nothing re-run |

No decision is pending. The stage's remaining evidence is CI on the PR (AC8).
