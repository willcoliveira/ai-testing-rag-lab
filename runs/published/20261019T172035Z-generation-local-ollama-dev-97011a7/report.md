# Run 20261019T172035Z-generation-local-ollama-dev-97011a7

Generated from manifest.json and cases.jsonl by raglab; never edited by hand.

| | |
|---|---|
| Suite | generation, split dev, 3 trial(s), seed 20261018, gate manual |
| Provenance | local |
| Created | 2026-10-19T17:20:35Z |
| Git | 97011a7070be8aafa29c49da9e42957cd78c6973 (clean) |
| Config | generation-local-ollama (`config/local-ollama.toml`, sha256 92d8fe9b66ea) |
| Generator | nemotron-3.5-lightning:30b-a3b-mlx (openai-compat, digest d1e17d7dabac, server 0.40.6) |
| Settings | temperature 1.0, top_p 0.95, max_tokens 1024, timeout_s 120.0, response_format none, reasoning_effort none |
| Prompt | answer-v1 (sha256 96f42d9bc9c7) |
| Guards | tenant, input-limits, citations |
| Embedder | BAAI/bge-small-en-v1.5 at revision aa8f8b060edb |
| Retriever | dense, k = 5 |
| Chunker | 1200 characters, overlap 1 |
| Corpus | 18 documents, 228 chunks, sha256 8918d4f79673 |
| Dataset | `datasets/golden.v1.jsonl`, sha256 5f8cdaf18783 |
| Cases | 49 (147 case-trials) |

## Checks (no judge)

Rates over every trial, with a 95% Wilson interval at n = the number of cases. A citation hit means the answer cites a labelled chunk; it is not correctness (S5 judges that). Only behaviour pass^3 on the dev split is gated, by the consistency gate (Q-05; docs/THRESHOLDS.md), and locally until keys exist; the rest is reported.

pass^3: a case passes only when all 3 trials pass every check that applies; trial t uses seed 20261018 + t - 1 at temperature 1.0, so it measures whether the model passes consistently while it samples at that temperature, not whether it is correct.

| Check | Rate | 95% interval | n (cases) |
|---|---|---|---|
| status_ok | 0.980 | 0.893 to 0.996 | 49 |
| model_citations_retrieved | 0.980 | 0.893 to 0.996 | 49 |
| citation_hit | 0.803 | 0.598 to 0.918 | 22 |
| pass^3 | 0.633 | 0.493 to 0.753 | 49 |
| decision_label | 0.667 | 0.478 to 0.814 | 27 |
| decision_label[answer] | 0.981 | 0.795 to 0.999 | 18 |
| decision_label[abstain] | 0.056 | 0.004 to 0.454 | 6 |
| decision_label[flag-conflict] | 0.000 | 0.000 to 0.793 | 1 |
| decision_label[refuse-and-help] | 0.000 | 0.000 to 0.658 | 2 |
| abstention | 0.056 | 0.004 to 0.454 | 6 |
| over_abstention | 0.016 | 0.001 to 0.180 | 21 |
| behaviour_pass^3 | 0.519 | 0.340 to 0.693 | 27 |

## Run

- Status counts: ok 144, refused 0, blocked 3, unavailable 0, invalid_output 0
- Label agreement: 44 of 49 cases gave the same label in every trial
- Latency: p50 1510.180 ms, p95 2743.227 ms (n 147)
- Tokens: 153210 prompt and 16138 completion, from the 147 case-trials whose server reported them

## Behaviour cases (decision label and abstention, no judge)

The decision label is the structured `label` field, never the text. A flag-conflict case whose conflict side was not retrieved expects answer with no conflict field; the miss counts against retrieval (3 such case-trial(s)).

Expected (rows) against given (columns), in case-trials:

| Expected | answer | abstain | flag-conflict | refuse-and-help | withheld |
|---|---|---|---|---|---|
| answer | 53 | 1 | 0 | 0 | 0 |
| abstain | 16 | 1 | 0 | 0 | 1 |
| flag-conflict | 2 | 0 | 0 | 0 | 1 |
| refuse-and-help | 6 | 0 | 0 | 0 | 0 |

Abstain cases, the oracle's two checks combined (case-trials): label abstain or not, and a value stated or not. "Not abstain, no value" is the S3 pattern.

| Label | No value stated | Value stated |
|---|---|---|
| abstain | 1 | 0 |
| not abstain | 5 | 12 |

- Label agreement: 23 of 27 behaviour cases gave the same label in all 3 trials, right or wrong (behaviour pass^3 counts the cases whose every trial passed every check that applies).
- Label failures (case-trials): 0 with every labelled section retrieved, 10 with a labelled section missed, 17 on abstain cases (no labels).

| Case | Mix | Expected | Given, by trial | Passed |
|---|---|---|---|---|
| P-01 | unanswerable | abstain | answer, answer, withheld | 0 of 3 |
| P-02 | unanswerable | abstain | answer, answer, answer | 0 of 3 |
| P-03 | unanswerable | abstain | answer, answer, answer | 0 of 3 |
| G-01 | single-chunk | answer | answer, answer, answer | 3 of 3 |
| G-03 | single-chunk | answer | answer, answer, answer | 3 of 3 |
| G-05 | single-chunk | answer | answer, answer, answer | 3 of 3 |
| G-06 | single-chunk | answer | answer, answer, answer | 3 of 3 |
| G-08 | single-chunk | answer | answer, answer, answer | 3 of 3 |
| G-09 | single-chunk | answer | answer, answer, answer | 3 of 3 |
| G-10 | single-chunk | answer | answer, answer, answer | 3 of 3 |
| G-11 | single-chunk | answer | answer, answer, answer | 3 of 3 |
| G-12 | single-chunk | answer | answer, answer, answer | 2 of 3 |
| G-14 | single-chunk | answer | answer, answer, answer | 3 of 3 |
| G-16 | multi-chunk | answer | answer, answer, answer | 3 of 3 |
| G-17 | multi-chunk | answer | answer, answer, answer | 0 of 3 |
| G-19 | multi-chunk | answer | abstain, answer, answer | 2 of 3 |
| G-21 | multi-chunk | answer | answer, answer, answer | 3 of 3 |
| G-22 | multi-chunk | flag-conflict | withheld, answer, answer | 0 of 3 |
| G-23 | multi-chunk | refuse-and-help | answer, answer, answer | 0 of 3 |
| G-25 | unanswerable | abstain | answer, answer, answer | 0 of 3 |
| G-26 | unanswerable | abstain | answer, abstain, answer | 1 of 3 |
| G-28 | unanswerable | abstain | answer, answer, answer | 0 of 3 |
| G-29 | version-conflict | answer | answer, answer, answer | 3 of 3 |
| G-31 | version-conflict | answer | answer, answer, answer | 0 of 3 |
| G-33 | paraphrase | answer | answer, answer, answer | 3 of 3 |
| G-34 | paraphrase | refuse-and-help | answer, answer, answer | 0 of 3 |
| G-36 | misspelling | answer | answer, answer, answer | 3 of 3 |

## Case-trials

| Case | Trial | Tenant | Kind | Status | Label | Cited | Passed |
|---|---|---|---|---|---|---|---|
| R-Q01 | 1 | tenant-a | retrieval | ok | answer | A-PWD-V2@2.0/4.2/1 | yes |
| R-Q01 | 2 | tenant-a | retrieval | ok | answer | A-PWD-V2@2.0/4.2/1 | yes |
| R-Q01 | 3 | tenant-a | retrieval | ok | answer | A-PWD-V2@2.0/4.2/1 | yes |
| R-Q02 | 1 | tenant-a | retrieval | ok | answer | A-LIFE@1.1/6.1/1 | yes |
| R-Q02 | 2 | tenant-a | retrieval | ok | answer | A-LIFE@1.1/6.1/1 | yes |
| R-Q02 | 3 | tenant-a | retrieval | ok | answer | A-LIFE@1.1/6.1/1 | yes |
| R-Q04 | 1 | tenant-a | retrieval | ok | answer | A-PWD-V1@1.0/4.4/1 | no |
| R-Q04 | 2 | tenant-a | retrieval | ok | answer | A-FAQ@1.0/Q2/1, A-PWD-V1@1.0/4.4/1, X-NCSC@1.0/1/1 | no |
| R-Q04 | 3 | tenant-a | retrieval | ok | answer | A-PWD-V1@1.0/4.4/1 | no |
| R-Q05 | 1 | tenant-a | retrieval | ok | answer | X-NCSC@1.0/1/1 | no |
| R-Q05 | 2 | tenant-a | retrieval | ok | answer | X-NCSC@1.0/1/1, X-NCSC@1.0/3/1 | no |
| R-Q05 | 3 | tenant-a | retrieval | ok | answer | X-NCSC@1.0/1/1 | no |
| R-Q07 | 1 | tenant-a | retrieval | ok | answer | A-PRIV@1.0/8.1/1, A-REV@1.0/3.2/1 | yes |
| R-Q07 | 2 | tenant-a | retrieval | ok | answer | A-REV@1.0/3.2/1 | yes |
| R-Q07 | 3 | tenant-a | retrieval | ok | answer | A-REV@1.0/3.2/1, A-PRIV@1.0/8.1/1 | yes |
| R-Q08 | 1 | tenant-a | retrieval | ok | answer | A-PRIV@1.0/7.2/1, A-PWD-V2@2.0/4.4/1, A-FAQ@1.0/Q2/1 | yes |
| R-Q08 | 2 | tenant-a | retrieval | ok | answer | A-PRIV@1.0/7.2/1, A-PWD-V2@2.0/4.4/1 | yes |
| R-Q08 | 3 | tenant-a | retrieval | ok | answer | A-PRIV@1.0/7.2/1, A-PWD-V2@2.0/4.4/1 | yes |
| R-Q10 | 1 | tenant-a | retrieval | ok | answer | A-PWD-V2@2.0/2/1, A-PWD-V2@2.0/4.7/1, A-IR@1.0/5.4/1 | no |
| R-Q10 | 2 | tenant-a | retrieval | ok | answer | A-PWD-V2@2.0/2/1, A-EXC@1.0/2.2/1 | no |
| R-Q10 | 3 | tenant-a | retrieval | ok | answer | A-PWD-V2@2.0/2/1 | no |
| R-Q11 | 1 | tenant-a | retrieval | ok | answer | A-LIFE@1.1/3.1/1 | yes |
| R-Q11 | 2 | tenant-a | retrieval | ok | answer | A-LIFE@1.1/3.1/1 | yes |
| R-Q11 | 3 | tenant-a | retrieval | ok | answer | A-LIFE@1.1/3.1/1 | yes |
| R-Q13 | 1 | tenant-a | retrieval | ok | answer | A-LIFE@1.1/5.2/1 | yes |
| R-Q13 | 2 | tenant-a | retrieval | ok | answer | A-LIFE@1.1/5.2/1 | yes |
| R-Q13 | 3 | tenant-a | retrieval | ok | answer | A-LIFE@1.1/5.2/1 | yes |
| R-Q14 | 1 | tenant-a | retrieval | ok | answer | A-LIFE@1.1/3.3/1, A-MFA@1.0/3.3/1 | yes |
| R-Q14 | 2 | tenant-a | retrieval | ok | answer | A-LIFE@1.1/3.3/1 | yes |
| R-Q14 | 3 | tenant-a | retrieval | ok | answer | A-LIFE@1.1/3.3/1, A-MFA@1.0/3.3/1 | yes |
| R-Q16 | 1 | tenant-a | retrieval | ok | answer | A-DEVICE-B@1.0/1/1 | yes |
| R-Q16 | 2 | tenant-a | retrieval | ok | answer | A-DEVICE-B@1.0/1/1 | yes |
| R-Q16 | 3 | tenant-a | retrieval | ok | answer | A-DEVICE-B@1.0/1/1 | yes |
| R-Q18 | 1 | tenant-a | retrieval | ok | answer | A-FAQ@1.0/Q2/1, X-NCSC@1.0/3/1 | yes |
| R-Q18 | 2 | tenant-a | retrieval | ok | answer | A-FAQ@1.0/Q2/1, X-NCSC@1.0/3/1 | yes |
| R-Q18 | 3 | tenant-a | retrieval | ok | answer | A-FAQ@1.0/Q2/1, X-NCSC@1.0/3/1, A-PWD-V2@2.0/4.5/1 | yes |
| R-Q19 | 1 | tenant-a | retrieval | ok | answer | A-PWD-V1@1.0/4.1/1, A-PWD-V2@2.0/4.1/1 | yes |
| R-Q19 | 2 | tenant-a | retrieval | ok | answer | A-PWD-V1@1.0/4.1/1, A-PWD-V2@2.0/4.1/1 | yes |
| R-Q19 | 3 | tenant-a | retrieval | ok | answer | A-PWD-V1@1.0/4.1/1, A-PWD-V2@2.0/4.1/1 | yes |
| R-Q21 | 1 | tenant-a | retrieval | ok | answer | X-NCSC@1.0/3/1, A-FAQ@1.0/Q2/1, A-PWD-V2@2.0/4.4/1 | yes |
| R-Q21 | 2 | tenant-a | retrieval | ok | answer | X-NCSC@1.0/3/1, A-FAQ@1.0/Q2/1, A-PWD-V2@2.0/4.4/1 | yes |
| R-Q21 | 3 | tenant-a | retrieval | ok | answer | A-PWD-V2@2.0/4.4/1, A-FAQ@1.0/Q2/1, X-NCSC@1.0/3/1 | yes |
| R-Q22 | 1 | tenant-a | retrieval | ok | answer | A-PWD-V2@2.0/5/1 | yes |
| R-Q22 | 2 | tenant-a | retrieval | ok | answer | A-PWD-V2@2.0/5/1 | yes |
| R-Q22 | 3 | tenant-a | retrieval | ok | answer | A-PWD-V2@2.0/5/1 | yes |
| R-Q24 | 1 | tenant-a | retrieval | ok | answer | A-EXC@1.0/5.2/1, A-REMOTE@1.1/4.5/1, A-EXC@1.0/5.1/1 | yes |
| R-Q24 | 2 | tenant-a | retrieval | ok | answer | A-EXC@1.0/5.2/1, A-REMOTE@1.1/4.5/1, A-EXC@1.0/5.1/1 | yes |
| R-Q24 | 3 | tenant-a | retrieval | ok | answer | A-EXC@1.0/5.2/1, A-EXC@1.0/5.1/1, A-REMOTE@1.1/4.5/1 | yes |
| R-Q25 | 1 | tenant-a | retrieval | ok | answer | A-FAQ@1.0/Q7/1, A-EXC@1.0/5.1/1, A-DEVICE@1.2/3.2/1, A-REMOTE@1.1/4.6/1 | yes |
| R-Q25 | 2 | tenant-a | retrieval | ok | answer | A-FAQ@1.0/Q7/1, A-EXC@1.0/5.1/1 | yes |
| R-Q25 | 3 | tenant-a | retrieval | blocked | abstain | - | no |
| R-Q27 | 1 | tenant-b | retrieval | ok | answer | B-PWD@1.0/3.1/1 | yes |
| R-Q27 | 2 | tenant-b | retrieval | ok | answer | B-PWD@1.0/3.1/1 | yes |
| R-Q27 | 3 | tenant-b | retrieval | ok | answer | B-PWD@1.0/3.1/1 | yes |
| R-Q28 | 1 | tenant-b | retrieval | ok | answer | B-MFA@1.0/3.2/1 | yes |
| R-Q28 | 2 | tenant-b | retrieval | ok | answer | B-MFA@1.0/3.2/1, B-MFA@1.0/3.1/1 | yes |
| R-Q28 | 3 | tenant-b | retrieval | ok | answer | B-MFA@1.0/3.2/1, B-MFA@1.0/3.1/1 | yes |
| R-Q29 | 1 | tenant-b | retrieval | ok | answer | B-MFA@1.0/5.1/1 | yes |
| R-Q29 | 2 | tenant-b | retrieval | ok | answer | B-MFA@1.0/5.1/1 | yes |
| R-Q29 | 3 | tenant-b | retrieval | ok | answer | B-MFA@1.0/5.1/1 | yes |
| R-Q31 | 1 | tenant-a | retrieval | ok | answer | A-REMOTE@1.1/4.5/1, A-EXC@1.0/5.2/1, A-EXC@1.0/5.1/1 | yes |
| R-Q31 | 2 | tenant-a | retrieval | ok | answer | A-REMOTE@1.1/4.5/1, A-EXC@1.0/5.2/1 | yes |
| R-Q31 | 3 | tenant-a | retrieval | ok | answer | A-REMOTE@1.1/4.5/1, A-EXC@1.0/5.2/1, A-EXC@1.0/5.1/1 | yes |
| R-Q33 | 1 | tenant-a | retrieval | ok | answer | A-PWD-V2@2.0/4.2/1, A-PWD-V1@1.0/4.2/1 | no |
| R-Q33 | 2 | tenant-a | retrieval | ok | answer | A-PWD-V2@2.0/4.2/1, A-PWD-V1@1.0/4.2/1 | no |
| R-Q33 | 3 | tenant-a | retrieval | ok | answer | A-PWD-V2@2.0/4.2/1, A-PWD-V1@1.0/4.2/1 | no |
| P-01 | 1 | tenant-a | behaviour | ok | answer | A-PWD-V2@2.0/4.4/1, A-FAQ@1.0/Q2/1 | no |
| P-01 | 2 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q2/1, A-PWD-V2@2.0/4.4/1 | no |
| P-01 | 3 | tenant-a | behaviour | blocked | abstain | - | no |
| P-02 | 1 | tenant-b | behaviour | ok | answer | B-PWD@1.0/4.1/1 | no |
| P-02 | 2 | tenant-b | behaviour | ok | answer | X-NCSC@1.0/1/1 | no |
| P-02 | 3 | tenant-b | behaviour | ok | answer | B-PWD@1.0/4.1/1 | no |
| P-03 | 1 | tenant-b | behaviour | ok | answer | B-MFA@1.0/6.1/1 | no |
| P-03 | 2 | tenant-b | behaviour | ok | answer | B-MFA@1.0/6.1/1 | no |
| P-03 | 3 | tenant-b | behaviour | ok | answer | B-MFA@1.0/6.1/1 | no |
| G-01 | 1 | tenant-a | behaviour | ok | answer | A-PWD-V2@2.0/4.2/1 | yes |
| G-01 | 2 | tenant-a | behaviour | ok | answer | A-PWD-V2@2.0/4.2/1 | yes |
| G-01 | 3 | tenant-a | behaviour | ok | answer | A-PWD-V2@2.0/4.2/1 | yes |
| G-03 | 1 | tenant-a | behaviour | ok | answer | A-PWD-V2@2.0/5/1 | yes |
| G-03 | 2 | tenant-a | behaviour | ok | answer | A-PWD-V2@2.0/5/1 | yes |
| G-03 | 3 | tenant-a | behaviour | ok | answer | A-PWD-V2@2.0/5/1 | yes |
| G-05 | 1 | tenant-a | behaviour | ok | answer | A-MFA@1.0/4.1/1, A-MFA@1.0/2.1/1, A-EXC@1.0/2.1/1 | yes |
| G-05 | 2 | tenant-a | behaviour | ok | answer | A-MFA@1.0/4.1/1, A-EXC@1.0/2.1/1, A-MFA@1.0/2.1/1 | yes |
| G-05 | 3 | tenant-a | behaviour | ok | answer | A-MFA@1.0/4.1/1, A-MFA@1.0/2.1/1, A-EXC@1.0/2.1/1 | yes |
| G-06 | 1 | tenant-a | behaviour | ok | answer | A-MFA@1.0/7.1/1 | yes |
| G-06 | 2 | tenant-a | behaviour | ok | answer | A-MFA@1.0/7.1/1 | yes |
| G-06 | 3 | tenant-a | behaviour | ok | answer | A-MFA@1.0/7.1/1 | yes |
| G-08 | 1 | tenant-a | behaviour | ok | answer | A-DEVICE-B@1.0/1/1 | yes |
| G-08 | 2 | tenant-a | behaviour | ok | answer | A-DEVICE-B@1.0/1/1 | yes |
| G-08 | 3 | tenant-a | behaviour | ok | answer | A-DEVICE-B@1.0/1/1 | yes |
| G-09 | 1 | tenant-a | behaviour | ok | answer | A-IR@1.0/3.2/1, A-FAQ@1.0/Q8/1, A-FAQ@1.0/Q12/1 | yes |
| G-09 | 2 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q8/1, A-IR@1.0/3.2/1, A-FAQ@1.0/Q12/1 | yes |
| G-09 | 3 | tenant-a | behaviour | ok | answer | A-IR@1.0/3.2/1, A-FAQ@1.0/Q8/1, A-FAQ@1.0/Q12/1 | yes |
| G-10 | 1 | tenant-a | behaviour | ok | answer | A-PRIV@1.0/6.1/1 | yes |
| G-10 | 2 | tenant-a | behaviour | ok | answer | A-PRIV@1.0/6.1/1 | yes |
| G-10 | 3 | tenant-a | behaviour | ok | answer | A-PRIV@1.0/6.1/1 | yes |
| G-11 | 1 | tenant-a | behaviour | ok | answer | A-EXC@1.0/4.1/1 | yes |
| G-11 | 2 | tenant-a | behaviour | ok | answer | A-EXC@1.0/4.1/1 | yes |
| G-11 | 3 | tenant-a | behaviour | ok | answer | A-EXC@1.0/4.1/1 | yes |
| G-12 | 1 | tenant-a | behaviour | ok | answer | A-PWD-V1@1.0/4.4/1, A-PWD-V2@2.0/5/1 | yes |
| G-12 | 2 | tenant-a | behaviour | ok | answer | A-PWD-V2@2.0/5/1 | yes |
| G-12 | 3 | tenant-a | behaviour | ok | answer | A-PWD-V1@1.0/4.4/1, A-PWD-V1@1.0/2/1 | no |
| G-14 | 1 | tenant-b | behaviour | ok | answer | B-MFA@1.0/7.1/1 | yes |
| G-14 | 2 | tenant-b | behaviour | ok | answer | B-MFA@1.0/7.1/1 | yes |
| G-14 | 3 | tenant-b | behaviour | ok | answer | B-MFA@1.0/7.1/1 | yes |
| G-16 | 1 | tenant-a | behaviour | ok | answer | A-LIFE@1.1/5.2/1, A-MFA@1.0/6.1/1 | yes |
| G-16 | 2 | tenant-a | behaviour | ok | answer | A-LIFE@1.1/5.2/1, A-MFA@1.0/6.1/1 | yes |
| G-16 | 3 | tenant-a | behaviour | ok | answer | A-LIFE@1.1/5.2/1, A-MFA@1.0/6.1/1 | yes |
| G-17 | 1 | tenant-a | behaviour | ok | answer | A-MFA@1.0/2.1/1, A-PWD-V2@2.0/4.7/1 | no |
| G-17 | 2 | tenant-a | behaviour | ok | answer | A-MFA@1.0/2.1/1, A-PWD-V2@2.0/5/1, A-DEVICE-B@1.0/2/1 | no |
| G-17 | 3 | tenant-a | behaviour | ok | answer | A-PWD-V2@2.0/5/1, A-MFA@1.0/2.1/1 | no |
| G-19 | 1 | tenant-a | behaviour | ok | abstain | A-FAQ@1.0/Q7/1 | no |
| G-19 | 2 | tenant-a | behaviour | ok | answer | A-CLASS@1.1/A.1/1, A-REMOTE@1.1/4.6/1, A-CLASS@1.1/4.3/1, A-DEVICE@1.2/3.2/1, A-FAQ@1.0/Q7/1 | yes |
| G-19 | 3 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q7/1, A-CLASS@1.1/A.1/1, A-DEVICE@1.2/3.2/1, A-REMOTE@1.1/4.6/1, A-CLASS@1.1/4.3/1 | yes |
| G-21 | 1 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q6/1 | yes |
| G-21 | 2 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q6/1 | yes |
| G-21 | 3 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q6/1 | yes |
| G-22 | 1 | tenant-a | behaviour | blocked | abstain | - | no |
| G-22 | 2 | tenant-a | behaviour | ok | answer | A-PWD-V2@2.0/6/1, A-PWD-V2@2.0/2/1, X-NCSC@1.0/3/1, X-NIST@SP_800-63B-4/intro/1, X-NCSC@1.0/intro/1 | no |
| G-22 | 3 | tenant-a | behaviour | ok | answer | X-NCSC@1.0/3/1, A-PWD-V2@2.0/2/1, X-NIST@SP_800-63B-4/intro/1, A-PWD-V2@2.0/6/1 | no |
| G-23 | 1 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q5/1, A-MFA@1.0/5.3/1, A-FAQ@1.0/Q4/1, A-MFA@1.0/5.1/1 | no |
| G-23 | 2 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q4/1, A-MFA@1.0/5.1/1 | no |
| G-23 | 3 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q4/1, A-MFA@1.0/5.1/1 | no |
| G-25 | 1 | tenant-b | behaviour | ok | answer | B-PWD@1.0/2/1, B-PWD@1.0/3.2/1, B-PWD@1.0/3.3/1 | no |
| G-25 | 2 | tenant-b | behaviour | ok | answer | B-PWD@1.0/3.3/1, B-PWD@1.0/2/1, B-PWD@1.0/3.2/1 | no |
| G-25 | 3 | tenant-b | behaviour | ok | answer | B-PWD@1.0/2/1, B-PWD@1.0/3.3/1, B-PWD@1.0/5/1 | no |
| G-26 | 1 | tenant-b | behaviour | ok | answer | B-PWD@1.0/3.3/1, B-PWD@1.0/5/1, B-PWD@1.0/6/1, B-PWD@1.0/2/1, B-MFA@1.0/1/1 | no |
| G-26 | 2 | tenant-b | behaviour | ok | abstain | - | yes |
| G-26 | 3 | tenant-b | behaviour | ok | answer | B-PWD@1.0/3.3/1, B-PWD@1.0/5/1, B-PWD@1.0/6/1, B-PWD@1.0/2/1, B-MFA@1.0/1/1 | no |
| G-28 | 1 | tenant-b | behaviour | ok | answer | B-MFA@1.0/7.1/1 | no |
| G-28 | 2 | tenant-b | behaviour | ok | answer | B-MFA@1.0/7.1/1 | no |
| G-28 | 3 | tenant-b | behaviour | ok | answer | B-MFA@1.0/7.1/1 | no |
| G-29 | 1 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q2/1, X-NCSC@1.0/3/1, A-PWD-V2@2.0/4.4/1 | yes |
| G-29 | 2 | tenant-a | behaviour | ok | answer | X-NCSC@1.0/3/1, A-FAQ@1.0/Q2/1, A-PWD-V2@2.0/4.4/1 | yes |
| G-29 | 3 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q2/1, X-NCSC@1.0/3/1 | yes |
| G-31 | 1 | tenant-a | behaviour | ok | answer | A-PWD-V2@2.0/4.2/1 | no |
| G-31 | 2 | tenant-a | behaviour | ok | answer | A-PWD-V2@2.0/4.2/1 | no |
| G-31 | 3 | tenant-a | behaviour | ok | answer | A-PWD-V2@2.0/4.2/1 | no |
| G-33 | 1 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q4/1, A-MFA@1.0/5.1/1, A-DEVICE@1.2/3.4/1 | yes |
| G-33 | 2 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q4/1, A-MFA@1.0/5.1/1, A-DEVICE@1.2/3.4/1, A-MFA@1.0/5.2/1 | yes |
| G-33 | 3 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q4/1, A-MFA@1.0/5.1/1, A-DEVICE@1.2/3.4/1 | yes |
| G-34 | 1 | tenant-a | behaviour | ok | answer | A-PWD-V2@2.0/4.4/1 | no |
| G-34 | 2 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q2/1, A-PWD-V2@2.0/4.4/1 | no |
| G-34 | 3 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q2/1, A-PWD-V2@2.0/4.4/1, X-NCSC@1.0/1/1 | no |
| G-36 | 1 | tenant-a | behaviour | ok | answer | A-DEVICE@1.2/3.3/1 | yes |
| G-36 | 2 | tenant-a | behaviour | ok | answer | A-DEVICE@1.2/3.3/1 | yes |
| G-36 | 3 | tenant-a | behaviour | ok | answer | A-DEVICE@1.2/3.3/1 | yes |
