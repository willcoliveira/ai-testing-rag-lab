# Thresholds

Every gated metric has a threshold and a reason here. Reported-only metrics are listed with why
they are not gated. Later stages add rows (S5 judged metrics, S6 judge agreement, S8 the full
gate map).

## Retrieval (S2)

| Metric | Gate | Threshold | Reason |
|---|---|---|---|
| recall@5, default configuration (`config/retrieval-dense.toml`), dev split | pr-fast, blocking (`raglab gate`) | at least the published baseline's value minus one question (1 / n of the dev split) | The baseline is the committed run marked `baseline` in `runs/published/index.json`. The local embedder is real, so the gate measures real retrieval, but the baseline is made on a maintainer's Mac and CI runs on Linux. Two inputs differ there: the OCR text of the scanned page (Tesseract 5.5.3 locally, 5.3.4 in CI, with different character errors; S1b ledger), which changes that page's chunks and their vectors, and ONNX arithmetic in the last bits, which can swap near-tied chunks at rank 5. One dev question labels the scanned page. The margin of one question is provisional: before the gate is wired into pr-fast, the default configuration is run on the dev split in the CI image (`ubuntu:24.04` with the pinned Tesseract, as S1b measured the OCR) and the margin is set from the observed difference, recorded in the S2 ledger. A baseline made with another dataset or config (sha256 in the manifest) is stale and fails the gate until a new baseline is published in a reviewed pull request. |
| hit@5, MRR@5 | reported | none | Reported with their 95% bootstrap intervals in every run record. recall@5 is the gated one because it counts every labelled section of a multi-hop question, where hit@5 is satisfied by one. |
| Paired differences between configurations | reported (`raglab compare`) | none | With about 20 dev questions the intervals are wide; a comparison informs a choice, recorded in the stage ledger, and does not block a pull request. eval-on-change (main plan) gates on the paired interval once judged metrics exist. |

The test split is never used to set a threshold or to choose a configuration; it runs in
nightly, release and the capstone only.

Lab practice: a production system would set the margin from repeated runs of the gate on the CI
runner itself (its spread over, say, 20 runs), not from a one-question rule.
