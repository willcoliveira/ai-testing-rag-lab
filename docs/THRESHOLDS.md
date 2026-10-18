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

The test split is never used to set a threshold or to choose a configuration; it runs in
nightly, release and the capstone only.

Lab practice: a production system would set the margin from repeated runs of the gate on the CI
runner itself (its spread over, say, 20 runs), not from a one-question rule.
