# Thresholds

Every gated metric has a threshold and a reason here. Reported-only metrics are listed with why
they are not gated. Later stages add rows (S5 judged metrics, S6 judge agreement, S8 the full
gate map).

## Retrieval (S2)

| Metric | Gate | Threshold | Reason |
|---|---|---|---|
| recall@5, default configuration (`config/retrieval-dense.toml`), dev split | pr-fast, blocking (`raglab gate`) | at least the published baseline's value minus one question (1 / n of the dev split) | The baseline is the committed run marked `baseline` in `runs/published/index.json`. The local embedder is real, so the gate measures real retrieval, but the baseline is made on a maintainer's Mac and CI runs on Linux. Two inputs differ there: the OCR text of the scanned page (Tesseract 5.5.3 locally, 5.3.4 in CI, with different character errors; S1b ledger), which changes that page's chunks and their vectors, and ONNX arithmetic in the last bits, which can swap near-tied chunks at rank 5. One dev question labels the scanned page. **Measured** (S2 ledger, 2026-10-06): the default configuration on the dev split in `ubuntu:24.04` linux/amd64 (Docker on the maintainer's Mac, so emulated, not the GitHub runner itself) with the pinned Tesseract 5.3.4 gave the same top 5 chunks for all 22 dev questions and the same metrics as the Mac (recall@5 0.644 both); the largest score difference was 0.0010, on the scanned page's chunk (its OCR text differs), and at most 0.0002 on every other chunk (ONNX arithmetic). The closest labelled chunk to the rank-5 boundary is 0.0021 away (R-Q22: its table chunk at rank 5, 0.0021 above rank 6), about twice the largest difference seen. So a zero margin could fail a PR on arithmetic alone, while one question (1/22, 0.045) absorbs any single crossing; one flipped section of a two-label question moves recall@5 by 0.023. The margin is therefore one question, set from that measurement; a regression larger than one question fails. The first number from the runner itself is the PR's gate log; if it ever differs from the baseline, record it here and in the stage ledger. A baseline made with another dataset or config (sha256 in the manifest) is stale and fails the gate until a new baseline is published in a reviewed pull request. |
| hit@5, MRR@5 | reported | none | Reported with their 95% bootstrap intervals in every run record. recall@5 is the gated one because it counts every labelled section of a multi-hop question, where hit@5 is satisfied by one. |
| Paired differences between configurations | reported (`raglab compare`) | none | With about 20 dev questions the intervals are wide; a comparison informs a choice, recorded in the stage ledger, and does not block a pull request. eval-on-change (main plan) gates on the paired interval once judged metrics exist. |

## Generation (S3)

Nothing is gated in S3: the main plan sets targets from the first real run, so the numbers of the
first local run (S3 ledger) are S4's and S5's starting point.

| Metric | Gate | Threshold | Reason |
|---|---|---|---|
| status_ok, model_citations_retrieved, probe_abstention, citation_hit, pass^3 (Wilson intervals at n = cases) | reported | none | One local run on 25 cases; S4 adds the behaviour cases and the consistency gate, S5 the judged metrics. A citation hit is not correctness, and citation_hit cannot exceed retrieval's hit@5 |
| Citation integrity (R-02) | enforced in code, not by a threshold | every cited id was retrieved | The citation validator blocks any other answer, and the run record refuses a case that cites an unretrieved id |
| Latency p50, p95 and tokens | reported | none | Q-01 and Q-02 get their baselines in S5 |

## Consistency (S4, Q-05)

| Metric | Gate | Threshold | Reason |
|---|---|---|---|
| behaviour pass^3, `config/local-ollama.toml`, dev split (Q-05) | the consistency gate, `make gate-local` (`raglab gate`): by hand and **local** until keys exist; a pull request that changes the prompt, the generation code, the chunker, the embedder or the model quotes its line | margin: 1 case(s): at least the baseline's behaviour pass^3 minus one case (1/79 on golden set v2's 79 dev behaviour cases) | **Measured** (S4b ledger, 2026-10-24, after golden set v2's sign-off, at the frozen commit ade9397): the baseline `20261024T090351Z-generation-local-ollama-dev-ade9397` has behaviour pass^3 0.418 (33 of 79); the repeats `20261024T091315Z-generation-local-ollama-dev-ade9397` 0.430 (34 of 79), and `20261024T092237Z-generation-local-ollama-dev-ade9397`, `20261024T093208Z-generation-local-ollama-dev-ade9397` and `20261024T114208Z-generation-local-ollama-dev-ade9397` 0.418 (33 of 79) each. The largest drop below the baseline is 0 cases, so the margin is the rule's floor, one case: a run with 32 of 79 passes and one with 31 fails (the gate compares case counts). The counts held, but not the cases: each repeat's passing set differs from run 1's by one to three cases (31 cases pass in all five runs), and the same seed gave the same answer text in only 13 of 303 (case, trial) pairs, so a one-case margin on 79 cases is thin evidence of the spread. **History:** S4's baseline on golden set v1.1, `20261019T172035Z-generation-local-ollama-dev-97011a7` (0.519, 14 of 27, margin one case), and its four repeats stay published; their numbers do not compare with v2's (S4 ledger: the same 14 cases passed in all five runs, and the same answer text came back in only 6 of 147 pairs). The rule (S4 plan, "How the threshold is set"): after the golden set's sign-off, with the code frozen, five gate-local runs at the config's settings, seed included; the first complete run is published as the baseline, whatever its value (never the best of five), the other four as repeats; the margin is the largest drop of behaviour pass^3 below the baseline among the four repeats, in cases, and at least one case. The gate reads it from this cell as `margin: M case(s)` and refuses to judge until the cell holds one; the run ids and the reason come with the number. A baseline made with another dataset, config, prompt fingerprint, model digest or number of trials is stale and fails the gate until a new one is published in a reviewed pull request; a new Ollama version is not stale, it is a change the gate exists to see. A fake run is refused: the fake model's trials are identical, so its pass^3 measures the plumbing. |
| label agreement (the cases whose trials all gave the same label, right or wrong) | reported | none | A model that always abstains agrees perfectly, so agreement is not gated on its own; agreement minus behaviour pass^3 counts the cases that agree and still fail, and the rest waver |
| decision-label rate (overall and per expected label), the confusion table, abstention on the abstain cases and over-abstention on the others, the label failures split by whether the labelled sections were retrieved | reported | none | Read without a judge (TEST-PLAN R6); targets come from the first real runs (main plan), and S5's judge reads the text |

Lab practice: a production system runs this gate in CI against a managed model endpoint, on a
schedule and on every change to the prompt, the generation code or the model (the main plan's
nightly and eval-on-change), and sets the margin from many more repeats on that runner. Here it
runs on the Mac by hand until keys exist, and its margin comes from four repeats. The S4b runs
were made on golden set v2 at the frozen commit ade9397, four in a row and the fifth about two
hours later, after the developer agent stopped on a usage limit, with the same commit, model and
config (S4b ledger).

## Judged (S5)

Nothing judged is gated in S5. The criteria are docs/CRITERIA.md's, signed off on 2026-10-20 and
again on 2026-10-21 (`correct` reworded: judge-v2); the numbers are the judged baseline's,
`runs/published/20261021T081852Z-judge-local-dev-5aa0ec5/` (its `report.md`): the consistency
baseline's answers judged by the local judge under judge-v2. The first judged record,
`runs/published/20261020T195341Z-judge-local-dev-25ccc0d/` (judge-v1), stays published as the
evidence for the second sign-off; its numbers are not the baseline's.

**Golden set v2 (S4b).** The judged baseline stays `5aa0ec5`, on golden set v1.1's dev split,
until S6 judges v2's consistency baseline as its first live step: the user's answer to S4b's D2,
verbatim, "In S6, as its first live step (Recommended)". S4b changes none of the judge's files.
The judged numbers above are v1.1's and do not compare with a run on v2.

| Metric | Gate | Threshold | Reason |
|---|---|---|---|
| `grounded`, `cites_support`, `correct`, `relevant`, `abstains`, `refuses_and_helps`, `context_sufficient`: the pass rate over judged verdicts (Wilson interval at n = cases), pass^3, the unable_to_verify rate, the split by expected label | reported | none | The judge is uncalibrated until S6: how-to 17 step 10 asks to "calibrate the judge on 30 or more human labels before the threshold gates anything". unable_to_verify is never a pass, and a high rate of it reads as a badly written criterion |
| The canary set (`datasets/canaries.judge.jsonl`) | a hard stop on the judge, in every judge session, before any judged call | every item on its side | A judge that passes a planted invention, or obeys an instruction planted in its input, should grade nothing; the stop is on the judge, not on the system |
| The judge's repeatability (trial 1 judged twice) and order agreement (`grounded` with the passages reversed) | reported | none | Measured, not assumed: S4 found that a fixed seed does not reproduce the generator's text on the MLX runner; S6 reads them beside the human labels |
| The position test: each position's rate and the paired differences middle minus first and middle minus last | reported | none | A test of the generator's long contexts on ten cases, whose intervals are wide; scored by code first, the judge's `correct` beside it |
| DeepEval 4.3.1's metric canary, hallucination direction and faithfulness cross-check | reported (docs/COMPATIBILITY.md and the S5 ledger: docs/CRITERIA.md is frozen since its sign-off) | none | DeepEval's scores are never the judged numbers (D4: "Own judge; DeepEval fenced (Recommended)"); a hallucination threshold would be written only after its direction is measured, and DeepEval itself points RAG to faithfulness |

## Cost and latency (S5, Q-01, Q-02)

All reported. The formula is code (`raglab cost`, `src/raglab/evals/cost.py`, tested on
hand-computed values): a call costs (prompt tokens × input price + completion tokens × output
price) / 1,000,000; a case-trial is its generator call and its judge calls; a run is the sum of
its case-trials, and of one canary set when the run is judged; a month is the sum over the run
types of `config/cost-assumptions.toml` of runs per month × cost per run. The judge's
repeatability and order checks ("Checks per run" in `raglab cost`'s output) are priced apart and
not counted in the month total: they are S5's measurements of the judge, not part of a routine
run. The prices are `config/prices.toml`'s, each with its source and read date.

From `make cost JUDGED=20261021T081852Z-judge-local-dev-5aa0ec5` (the published judged baseline,
147 case-trials; price_table_date 2026-10-21), copied from its output, which ADR-002 quotes in
full:

| Tokens per case-trial | Prompt | Completion |
|---|---|---|
| generator (one call) | 1042.2 | 109.8 |
| judge (its criteria's calls) | 2150.7 | 347.6 |
| judge_checks (repeatability and order) | 789.0 | 113.5 |

The canaries (19 calls, 14224 prompt and 1688 completion tokens) run once per run. The monthly
estimate per option, at the assumed runs a month:

| Option | Per month |
|---|---|
| local only | $0.0000 |
| local generator, Claude Haiku 5.5 judge | $1.21 |
| local generator, gpt-5-mini judge | $3.83 |
| local generator, Claude Sonnet 5.5 judge | $24.21 |
| Claude Haiku 5.5 generator, gpt-5-mini judge | $4.60 |
| gpt-5-mini generator, Claude Haiku 5.5 judge | $3.53 |

**Q-01, the local latency baseline (reported):** the pipeline's answer time per case-trial (the
input guards, retrieval, the generator call and the output checks, in-process, without the API
layer) on S4's consistency baseline, on golden set v1.1, `20261019T172035Z-generation-local-ollama-dev-97011a7`: p50
1510.180 ms, p95 2743.227 ms (n 147). The local judge's time per call on the judged baseline: p50
5522.768 ms, p95 10373.613 ms (n 592), on AC power (the session's power line; the S4 baseline's
power source was not recorded). Both are the maintainer's Mac; a hosted provider's are measured
after the sign-up.

## Performance (S9)

The k6 smoke (`make perf-smoke`, pr-fast's `perf` job; docs/OBSERVABILITY.md): one virtual user
sends 10 warm-up and then 100 gated `/ask` requests to `raglab serve --config config/perf.toml`, the
perf stub (the fake echo model, provenance fake), over HTTP on loopback, on GitHub's
`ubuntu-24.04` runner. It is the HTTP path on the stub on GitHub's runner: **not Q-01**, which is
in-process, the real model, on the maintainer's Mac.

| Metric | Gate | Threshold | Reason |
|---|---|---|---|
| k6 smoke: /ask median (`ask_duration`, the 100 gated requests) | pr-fast `perf` job, blocking | median < 40 ms: T, set on 2026-10-24 by the rule below from the ten runs below (the largest median 15.38 ms; 2 × 15.38 = 30.76 ms, rounded up to the next 10 ms) | GitHub's hosted runners are shared machines whose speed varies (one pr-fast test step took 346 s on one run and 451 s on another on 2026-10-23), so a smoke must not go red on a slow machine; the regressions a smoke exists for cost far more than double (a model or an index loaded per request, a blocking call, a loop that grows with the corpus). **The rule, written before any run** (the S9 plan): the job lands with the median threshold off; ten report-only runs of the job at one commit, all kept, none dropped and none run again for a better number, each run's median and p95 copied from its log with its run id; T = 2 × the largest of the ten medians, rounded up to the next 10 ms; T changes only in a reviewed pull request with ten new runs under the same rule (a change of k6, of the runner image, of the stub, or a guard that adds latency to `/ask`). `tests/unit/test_perf_smoke.py` holds perf/smoke.js's value equal to this cell |
| k6 smoke: every reply 200 with status ok; failed requests | pr-fast `perf` job, blocking | checks rate 1; http_req_failed rate 0 | A smoke that sends 110 requests to a stub has no reason to see one fail; any failure is a bug, not noise |
| k6 smoke: /ask p90, p95, minimum, maximum | reported (the job's log and step summary) | none | The tail on a shared runner is noisier than the median |

**The ten report-only runs** (provenance: the fake model, the perf stub; GitHub's `ubuntu-24.04`
runner): the perf job of pr-fast run 40074154534 at commit `12f8e70`, attempts 1 to 10 on
2026-10-24, every one kept and every one passed (checks rate 1, no failed request). Each value is
copied from its job's `perf-smoke: /ask median ...` line:

| Run 40074154534, attempt | Median | p95 |
|---|---|---|
| 1 | 15.13 ms | 17.52 ms |
| 2 | 14.27 ms | 16.75 ms |
| 3 | 14.50 ms | 16.71 ms |
| 4 | 14.34 ms | 16.70 ms |
| 5 | 8.01 ms | 9.39 ms |
| 6 | 15.38 ms | 17.69 ms |
| 7 | 14.73 ms | 17.12 ms |
| 8 | 13.85 ms | 16.50 ms |
| 9 | 14.42 ms | 16.87 ms |
| 10 | 12.24 ms | 13.73 ms |

The largest median is attempt 6's, 15.38 ms; T = 2 × 15.38 ms = 30.76 ms, rounded up to the next
10 ms: **40 ms**. The medians span 8.01 to 15.38 ms, a factor of 1.9 between the fastest and the
slowest runner, which is why the margin is 2× the slowest and not a tighter rule.

Lab practice: a smoke, not a load test. One user on a shared CI runner and a stub for the model
catch a regression that doubles the API's time, not one of 10%. Production load-tests a staging
copy of the real deployment on capacity of its own, with the model in the path, against agreed
latency objectives, and sets margins from many more runs.

The test split is never used to set a threshold or to choose a configuration; it runs in
nightly, release and the capstone only.

Lab practice: a production system would set the margin from repeated runs of the gate on the CI
runner itself (its spread over, say, 20 runs), not from a one-question rule.

## Guards (S7)

Every guard layer is gated case by case, binary per build: a single miss of a must-block case or a
single false block of a must-not-block case fails `make test` and pr-fast, and the failure names
the case and the layer (`tests/security/test_guard_cases.py`; the attack suite,
`tests/security/test_attack_suite.py`, the same way). The reason: the main plan's targets set
"injection resisted", "zero cross-tenant leaks", "cited ids are always ones that were retrieved"
and "every must-block and must-not-block case passes" at 100% from the start, so no rate below
100% is accepted and none is set from a run. The rates and latencies below are reported, not
gated: the 95% Wilson interval says how far "0 of n" is from proof (0 of 5 still allows a miss rate
up to 0.434), and the latency is what each layer adds to a request.

From `runs/guard-suites/20261025T181249Z-5c4d409.json` (`make guard-suites` on the maintainer's
Mac, provenance local, the dev split of golden set v2, from a clean tree at `5c4d409`; the latency
is the layer's own check, in-process, over all of its cases):

| Layer | Must-block: misses / n (95% Wilson) | Must-not-block: false blocks / n (95% Wilson) | Added latency p50 / p95 (ms) | Cases |
|---|---|---|---|---|
| Tenant guard | 0 / 5 (0.000 to 0.434) | 0 / 106 (0.000 to 0.035) | 0.000333 / 0.002126 | the pack; golden set v2's 101 dev questions |
| Input limits | 0 / 6 (0.000 to 0.390) | 0 / 106 (0.000 to 0.035) | 0.004521 / 0.006445 | the pack; the 101 dev questions |
| Input injection detector | 0 / 10 (0.000 to 0.278) | 0 / 111 (0.000 to 0.033) | 0.021250 / 0.030209 | the pack; the 101 dev questions |
| Instruction scan | 0 / 7 (0.000 to 0.354) | 0 / 235 (0.000 to 0.016) | 0.047250 / 0.145277 | the pack; F-47's chunk; the 228 clean chunks |
| Register filter | 0 / 29 (0.000 to 0.117) | 0 / 233 (0.000 to 0.016) | 0.000416 / 0.000912 | the pack; the 24 attack-page chunks; the 228 clean chunks |
| Citation validator | 0 / 5 (0.000 to 0.434) | 0 / 1499 (0.000 to 0.003) | 0.000792 / 0.001125 | the pack; 1,494 recorded answers |
| Link guard | 0 / 6 (0.000 to 0.390) | 0 / 1500 (0.000 to 0.003) | 0.004520 / 0.011104 | the pack; 1,494 recorded answers |
| Secrets and personal-details guard | 0 / 8 (0.000 to 0.324) | 0 / 1502 (0.000 to 0.003) | 0.018438 / 0.046958 | the pack; 1,494 recorded answers |
| Prompt-leak guard | 0 / 6 (0.000 to 0.390) | 0 / 1500 (0.000 to 0.003) | 0.020479 / 0.056687 | the pack; 1,494 recorded answers |

The recorded answers are the 1,494 answered case-trials (status ok) of golden set v2's
consistency baseline `20261024T090351Z-generation-local-ollama-dev-ade9397` and its four repeats
(S4b). The first run, on golden set v1.1's baseline and repeats before S4b merged, stays in
`runs/guard-suites/20261024T030214Z-ebcdb7d.json`: no miss and no false block there either. The
test split's questions are checked only at nightly and release (`raglab guard-suites --split test
--gate nightly`).

Lab practice: a production system would also measure each layer on live traffic samples, where
the false-block rate on real questions is the number that matters, and would set its classifier
thresholds from those; here every case is handwritten or derived from the signed-off golden set
and corpus, and the rules have no threshold to tune.
