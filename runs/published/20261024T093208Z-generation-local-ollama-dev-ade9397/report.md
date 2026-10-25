# Run 20261024T093208Z-generation-local-ollama-dev-ade9397

Generated from manifest.json and cases.jsonl by raglab; never edited by hand.

| | |
|---|---|
| Suite | generation, split dev, 3 trial(s), seed 20261018, gate manual |
| Provenance | local |
| Created | 2026-10-24T09:32:08Z |
| Git | ade9397e8828bf875fe4925817041b0da16ff7e2 (clean) |
| Config | generation-local-ollama (`config/local-ollama.toml`, sha256 92f7fe0dbd3e) |
| Generator | nemotron-3.5-lightning:30b-a3b-mlx (openai-compat, digest d1e17d7dabac, server 0.40.6) |
| Settings | temperature 1.0, top_p 0.95, max_tokens 1024, timeout_s 120.0, response_format none, reasoning_effort none |
| Prompt | answer-v1 (sha256 96f42d9bc9c7) |
| Guards | tenant, input-limits, citations |
| Embedder | BAAI/bge-small-en-v1.5 at revision aa8f8b060edb |
| Retriever | dense, k = 5 |
| Chunker | 1200 characters, overlap 1 |
| Corpus | 18 documents, 228 chunks, sha256 8918d4f79673 |
| Dataset | `datasets/golden.v2.jsonl`, sha256 3d924ad0bd1d |
| Cases | 101 (303 case-trials) |

## Checks (no judge)

Rates over every trial, with a 95% Wilson interval at n = the number of cases. A citation hit means the answer cites a labelled chunk; it is not correctness (S5 judges that). Only behaviour pass^3 on the dev split is gated, by the consistency gate (Q-05; docs/THRESHOLDS.md), and locally until keys exist; the rest is reported.

pass^3: a case passes only when all 3 trials pass every check that applies; trial t uses seed 20261018 + t - 1 at temperature 1.0, so it measures whether the model passes consistently while it samples at that temperature, not whether it is correct.

| Check | Rate | 95% interval | n (cases) |
|---|---|---|---|
| status_ok | 0.983 | 0.936 to 0.996 | 101 |
| model_citations_retrieved | 0.983 | 0.936 to 0.996 | 101 |
| citation_hit | 0.788 | 0.582 to 0.908 | 22 |
| pass^3 | 0.495 | 0.400 to 0.591 | 101 |
| decision_label | 0.591 | 0.481 to 0.692 | 79 |
| decision_label[answer] | 0.978 | 0.887 to 0.996 | 46 |
| decision_label[abstain] | 0.093 | 0.023 to 0.305 | 18 |
| decision_label[flag-conflict] | 0.000 | 0.000 to 0.434 | 5 |
| decision_label[refuse-and-help] | 0.000 | 0.000 to 0.278 | 10 |
| abstention | 0.093 | 0.023 to 0.305 | 18 |
| over_abstention | 0.022 | 0.005 to 0.096 | 61 |
| behaviour_pass^3 | 0.418 | 0.315 to 0.528 | 79 |

## Run

- Status counts: ok 298, refused 0, blocked 5, unavailable 0, invalid_output 0
- Label agreement: 91 of 101 cases gave the same label in every trial
- Latency: p50 1602.260 ms, p95 2952.701 ms (n 303)
- Tokens: 315432 prompt and 35031 completion, from the 303 case-trials whose server reported them

## Behaviour cases (decision label and abstention, no judge)

The decision label is the structured `label` field, never the text. A flag-conflict case whose conflict side was not retrieved expects answer with no conflict field; the miss counts against retrieval (9 such case-trial(s)).

Expected (rows) against given (columns), in case-trials:

| Expected | answer | abstain | flag-conflict | refuse-and-help | withheld |
|---|---|---|---|---|---|
| answer | 136 | 1 | 0 | 0 | 1 |
| abstain | 47 | 5 | 0 | 0 | 2 |
| flag-conflict | 14 | 1 | 0 | 0 | 0 |
| refuse-and-help | 28 | 2 | 0 | 0 | 0 |

Abstain cases, the oracle's two checks combined (case-trials): label abstain or not, and a value stated or not. "Not abstain, no value" is the S3 pattern.

| Label | No value stated | Value stated |
|---|---|---|
| abstain | 5 | 0 |
| not abstain | 24 | 25 |

- Label agreement: 71 of 79 behaviour cases gave the same label in all 3 trials, right or wrong (behaviour pass^3 counts the cases whose every trial passed every check that applies).
- Label failures (case-trials): 27 with every labelled section retrieved, 21 with a labelled section missed, 49 on abstain cases (no labels).

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
| G-12 | single-chunk | answer | answer, answer, answer | 1 of 3 |
| G-14 | single-chunk | answer | answer, answer, answer | 3 of 3 |
| G-16 | multi-chunk | answer | answer, answer, answer | 3 of 3 |
| G-17 | multi-chunk | answer | answer, answer, answer | 0 of 3 |
| G-19 | multi-chunk | answer | abstain, answer, answer | 2 of 3 |
| G-21 | multi-chunk | answer | answer, answer, answer | 3 of 3 |
| G-22 | multi-chunk | flag-conflict | abstain, answer, answer | 0 of 3 |
| G-23 | multi-chunk | refuse-and-help | answer, answer, answer | 0 of 3 |
| G-25 | unanswerable | abstain | answer, answer, answer | 0 of 3 |
| G-26 | unanswerable | abstain | answer, answer, answer | 0 of 3 |
| G-28 | unanswerable | abstain | answer, answer, answer | 0 of 3 |
| G-29 | version-conflict | answer | answer, answer, answer | 3 of 3 |
| G-31 | version-conflict | answer | answer, answer, answer | 0 of 3 |
| G-33 | paraphrase | answer | answer, answer, answer | 3 of 3 |
| G-34 | paraphrase | refuse-and-help | answer, answer, answer | 0 of 3 |
| G-36 | misspelling | answer | answer, answer, answer | 3 of 3 |
| G-40 | single-chunk | answer | answer, answer, answer | 3 of 3 |
| G-41 | single-chunk | answer | answer, answer, answer | 3 of 3 |
| G-42 | single-chunk | answer | answer, answer, answer | 3 of 3 |
| G-43 | single-chunk | answer | answer, answer, answer | 3 of 3 |
| G-47 | single-chunk | refuse-and-help | answer, answer, answer | 0 of 3 |
| G-48 | single-chunk | refuse-and-help | answer, answer, answer | 0 of 3 |
| G-50 | single-chunk | answer | answer, answer, answer | 3 of 3 |
| G-51 | single-chunk | answer | answer, answer, answer | 3 of 3 |
| G-52 | single-chunk | refuse-and-help | answer, answer, answer | 0 of 3 |
| G-53 | single-chunk | answer | answer, answer, answer | 3 of 3 |
| G-54 | single-chunk | answer | answer, answer, answer | 0 of 3 |
| G-55 | single-chunk | answer | answer, answer, answer | 3 of 3 |
| G-56 | single-chunk | answer | answer, answer, answer | 0 of 3 |
| G-58 | single-chunk | answer | withheld, answer, answer | 0 of 3 |
| G-61 | single-chunk | answer | answer, answer, answer | 3 of 3 |
| G-62 | single-chunk | answer | answer, answer, answer | 3 of 3 |
| G-63 | single-chunk | answer | answer, answer, answer | 3 of 3 |
| G-64 | single-chunk | answer | answer, answer, answer | 3 of 3 |
| G-65 | single-chunk | refuse-and-help | abstain, answer, answer | 0 of 3 |
| G-67 | single-chunk | refuse-and-help | answer, answer, answer | 0 of 3 |
| G-68 | multi-chunk | flag-conflict | answer, answer, answer | 0 of 3 |
| G-71 | multi-chunk | answer | answer, answer, answer | 2 of 3 |
| G-73 | multi-chunk | answer | answer, answer, answer | 3 of 3 |
| G-74 | multi-chunk | answer | answer, answer, answer | 0 of 3 |
| G-75 | multi-chunk | answer | answer, answer, answer | 3 of 3 |
| G-76 | multi-chunk | answer | answer, answer, answer | 0 of 3 |
| G-78 | multi-chunk | answer | answer, answer, answer | 3 of 3 |
| G-79 | multi-chunk | refuse-and-help | answer, answer, answer | 0 of 3 |
| G-80 | multi-chunk | refuse-and-help | abstain, answer, answer | 0 of 3 |
| G-81 | multi-chunk | refuse-and-help | answer, answer, answer | 0 of 3 |
| G-82 | multi-chunk | answer | answer, answer, answer | 3 of 3 |
| G-84 | unanswerable | abstain | abstain, answer, abstain | 2 of 3 |
| G-86 | unanswerable | abstain | withheld, abstain, abstain | 2 of 3 |
| G-88 | unanswerable | abstain | answer, answer, answer | 0 of 3 |
| G-89 | unanswerable | abstain | answer, answer, answer | 0 of 3 |
| G-90 | unanswerable | abstain | answer, answer, answer | 0 of 3 |
| G-92 | unanswerable | abstain | abstain, answer, answer | 1 of 3 |
| G-94 | unanswerable | abstain | answer, answer, answer | 0 of 3 |
| G-95 | unanswerable | abstain | answer, answer, answer | 0 of 3 |
| G-97 | unanswerable | abstain | answer, answer, answer | 0 of 3 |
| G-98 | unanswerable | abstain | answer, answer, answer | 0 of 3 |
| G-99 | unanswerable | abstain | answer, answer, answer | 0 of 3 |
| G-100 | version-conflict | flag-conflict | answer, answer, answer | 0 of 3 |
| G-101 | version-conflict | flag-conflict | answer, answer, answer | 0 of 3 |
| G-103 | version-conflict | answer | answer, answer, answer | 3 of 3 |
| G-105 | version-conflict | answer | answer, answer, answer | 1 of 3 |
| G-106 | version-conflict | answer | answer, answer, answer | 3 of 3 |
| G-108 | paraphrase | answer | answer, answer, answer | 3 of 3 |
| G-109 | paraphrase | flag-conflict | answer, answer, answer | 0 of 3 |
| G-110 | paraphrase | answer | answer, answer, answer | 2 of 3 |
| G-113 | misspelling | answer | answer, answer, answer | 0 of 3 |
| G-114 | misspelling | abstain | answer, answer, answer | 0 of 3 |

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
| R-Q04 | 2 | tenant-a | retrieval | ok | answer | A-PWD-V1@1.0/4.4/1 | no |
| R-Q04 | 3 | tenant-a | retrieval | ok | answer | A-PWD-V1@1.0/4.4/1, A-FAQ@1.0/Q2/1 | no |
| R-Q05 | 1 | tenant-a | retrieval | ok | answer | X-NCSC@1.0/1/1 | no |
| R-Q05 | 2 | tenant-a | retrieval | ok | answer | X-NCSC@1.0/1/1 | no |
| R-Q05 | 3 | tenant-a | retrieval | ok | answer | X-NCSC@1.0/1/1 | no |
| R-Q07 | 1 | tenant-a | retrieval | ok | answer | A-REV@1.0/3.2/1, A-PRIV@1.0/8.1/1 | yes |
| R-Q07 | 2 | tenant-a | retrieval | ok | answer | A-REV@1.0/3.2/1 | yes |
| R-Q07 | 3 | tenant-a | retrieval | ok | answer | A-REV@1.0/3.2/1, A-PRIV@1.0/8.1/1, A-REV@1.0/3.3/1 | yes |
| R-Q08 | 1 | tenant-a | retrieval | ok | answer | A-PRIV@1.0/7.2/1, A-PWD-V2@2.0/4.4/1 | yes |
| R-Q08 | 2 | tenant-a | retrieval | ok | answer | A-PRIV@1.0/7.2/1, A-PWD-V2@2.0/4.4/1 | yes |
| R-Q08 | 3 | tenant-a | retrieval | ok | answer | A-PRIV@1.0/7.2/1, A-PWD-V2@2.0/4.4/1, A-FAQ@1.0/Q2/1, A-PWD-V1@1.0/4.3/1 | yes |
| R-Q10 | 1 | tenant-a | retrieval | ok | answer | A-PWD-V2@2.0/2/1, A-PWD-V2@2.0/4.7/1 | no |
| R-Q10 | 2 | tenant-a | retrieval | ok | answer | A-DEVICE-B@1.0/2/1, A-PWD-V2@2.0/2/1, A-PWD-V2@2.0/4.7/1 | no |
| R-Q10 | 3 | tenant-a | retrieval | ok | answer | A-PWD-V2@2.0/2/1, A-EXC@1.0/2.2/1 | no |
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
| R-Q18 | 3 | tenant-a | retrieval | ok | answer | A-FAQ@1.0/Q2/1, X-NCSC@1.0/3/1 | yes |
| R-Q19 | 1 | tenant-a | retrieval | ok | answer | A-PWD-V1@1.0/4.1/1, A-PWD-V2@2.0/4.1/1 | yes |
| R-Q19 | 2 | tenant-a | retrieval | ok | answer | A-PWD-V1@1.0/4.1/1, A-PWD-V2@2.0/4.1/1 | yes |
| R-Q19 | 3 | tenant-a | retrieval | ok | answer | A-PWD-V1@1.0/4.1/1, A-PWD-V2@2.0/4.1/1, A-FAQ@1.0/Q1/1 | yes |
| R-Q21 | 1 | tenant-a | retrieval | ok | flag-conflict | X-NCSC@1.0/3/1, A-FAQ@1.0/Q2/1, A-PWD-V2@2.0/4.4/1 | yes |
| R-Q21 | 2 | tenant-a | retrieval | ok | answer | X-NCSC@1.0/3/1, A-FAQ@1.0/Q2/1, A-PWD-V2@2.0/4.4/1, A-PWD-V1@1.0/4.3/1 | yes |
| R-Q21 | 3 | tenant-a | retrieval | ok | answer | X-NCSC@1.0/3/1, A-FAQ@1.0/Q2/1, A-PWD-V2@2.0/4.4/1 | yes |
| R-Q22 | 1 | tenant-a | retrieval | ok | answer | A-PWD-V2@2.0/5/1 | yes |
| R-Q22 | 2 | tenant-a | retrieval | ok | answer | A-PWD-V2@2.0/5/1 | yes |
| R-Q22 | 3 | tenant-a | retrieval | ok | answer | A-PWD-V2@2.0/5/1 | yes |
| R-Q24 | 1 | tenant-a | retrieval | ok | answer | A-EXC@1.0/5.2/1, A-REMOTE@1.1/4.5/1, A-EXC@1.0/5.1/1 | yes |
| R-Q24 | 2 | tenant-a | retrieval | ok | answer | A-EXC@1.0/5.2/1, A-REMOTE@1.1/4.5/1, A-EXC@1.0/5.1/1 | yes |
| R-Q24 | 3 | tenant-a | retrieval | ok | answer | A-EXC@1.0/5.2/1, A-REMOTE@1.1/4.5/1, A-EXC@1.0/5.1/1 | yes |
| R-Q25 | 1 | tenant-a | retrieval | blocked | abstain | - | no |
| R-Q25 | 2 | tenant-a | retrieval | blocked | abstain | - | no |
| R-Q25 | 3 | tenant-a | retrieval | ok | answer | A-EXC@1.0/5.1/1, A-FAQ@1.0/Q7/1, A-DEVICE@1.2/3.2/1, A-REMOTE@1.1/4.6/1 | yes |
| R-Q27 | 1 | tenant-b | retrieval | ok | answer | B-PWD@1.0/3.1/1 | yes |
| R-Q27 | 2 | tenant-b | retrieval | ok | answer | B-PWD@1.0/3.1/1 | yes |
| R-Q27 | 3 | tenant-b | retrieval | ok | answer | B-PWD@1.0/3.1/1 | yes |
| R-Q28 | 1 | tenant-b | retrieval | ok | answer | B-MFA@1.0/3.2/1, B-MFA@1.0/3.1/1 | yes |
| R-Q28 | 2 | tenant-b | retrieval | ok | answer | B-MFA@1.0/3.2/1, B-MFA@1.0/3.1/1 | yes |
| R-Q28 | 3 | tenant-b | retrieval | ok | answer | B-MFA@1.0/3.2/1 | yes |
| R-Q29 | 1 | tenant-b | retrieval | ok | answer | B-MFA@1.0/5.1/1 | yes |
| R-Q29 | 2 | tenant-b | retrieval | ok | answer | B-MFA@1.0/5.1/1 | yes |
| R-Q29 | 3 | tenant-b | retrieval | ok | answer | B-MFA@1.0/5.1/1 | yes |
| R-Q31 | 1 | tenant-a | retrieval | ok | answer | A-REMOTE@1.1/4.5/1, A-EXC@1.0/5.2/1, A-EXC@1.0/5.1/1 | yes |
| R-Q31 | 2 | tenant-a | retrieval | ok | answer | A-REMOTE@1.1/4.5/1, A-EXC@1.0/5.2/1, A-EXC@1.0/5.1/1 | yes |
| R-Q31 | 3 | tenant-a | retrieval | ok | answer | A-REMOTE@1.1/4.5/1, A-EXC@1.0/5.2/1, A-EXC@1.0/5.1/1 | yes |
| R-Q33 | 1 | tenant-a | retrieval | ok | answer | A-PWD-V2@2.0/4.2/1 | no |
| R-Q33 | 2 | tenant-a | retrieval | ok | answer | A-PWD-V2@2.0/4.2/1 | no |
| R-Q33 | 3 | tenant-a | retrieval | ok | answer | A-PWD-V2@2.0/4.2/1 | no |
| P-01 | 1 | tenant-a | behaviour | ok | answer | X-NCSC@1.0/3/1, A-FAQ@1.0/Q2/1, X-NCSC@1.0/1/1, A-IR@1.0/5.4/1, A-PWD-V2@2.0/4.4/1 | no |
| P-01 | 2 | tenant-a | behaviour | ok | answer | - | no |
| P-01 | 3 | tenant-a | behaviour | blocked | abstain | - | no |
| P-02 | 1 | tenant-b | behaviour | ok | answer | B-PWD@1.0/4.1/1 | no |
| P-02 | 2 | tenant-b | behaviour | ok | answer | B-PWD@1.0/4.1/1 | no |
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
| G-05 | 1 | tenant-a | behaviour | ok | answer | A-MFA@1.0/4.1/1, A-EXC@1.0/2.1/1 | yes |
| G-05 | 2 | tenant-a | behaviour | ok | answer | A-MFA@1.0/4.1/1, A-EXC@1.0/2.1/1 | yes |
| G-05 | 3 | tenant-a | behaviour | ok | answer | A-MFA@1.0/4.1/1, A-PRIV@1.0/4.1/1, A-MFA@1.0/5.3/1, A-EXC@1.0/2.1/1, A-MFA@1.0/2.1/1 | yes |
| G-06 | 1 | tenant-a | behaviour | ok | answer | A-MFA@1.0/7.1/1 | yes |
| G-06 | 2 | tenant-a | behaviour | ok | answer | A-MFA@1.0/7.1/1 | yes |
| G-06 | 3 | tenant-a | behaviour | ok | answer | A-MFA@1.0/7.1/1 | yes |
| G-08 | 1 | tenant-a | behaviour | ok | answer | A-DEVICE-B@1.0/1/1 | yes |
| G-08 | 2 | tenant-a | behaviour | ok | answer | A-DEVICE-B@1.0/1/1 | yes |
| G-08 | 3 | tenant-a | behaviour | ok | answer | A-DEVICE-B@1.0/1/1 | yes |
| G-09 | 1 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q8/1, A-IR@1.0/3.2/1, A-FAQ@1.0/Q12/1 | yes |
| G-09 | 2 | tenant-a | behaviour | ok | answer | A-IR@1.0/3.2/1, A-FAQ@1.0/Q8/1, A-FAQ@1.0/Q12/1 | yes |
| G-09 | 3 | tenant-a | behaviour | ok | answer | A-IR@1.0/3.2/1, A-FAQ@1.0/Q8/1, A-FAQ@1.0/Q12/1 | yes |
| G-10 | 1 | tenant-a | behaviour | ok | answer | A-PRIV@1.0/6.1/1 | yes |
| G-10 | 2 | tenant-a | behaviour | ok | answer | A-PRIV@1.0/6.1/1 | yes |
| G-10 | 3 | tenant-a | behaviour | ok | answer | A-PRIV@1.0/6.1/1 | yes |
| G-11 | 1 | tenant-a | behaviour | ok | answer | A-EXC@1.0/4.1/1 | yes |
| G-11 | 2 | tenant-a | behaviour | ok | answer | A-EXC@1.0/4.1/1 | yes |
| G-11 | 3 | tenant-a | behaviour | ok | answer | A-EXC@1.0/4.1/1 | yes |
| G-12 | 1 | tenant-a | behaviour | ok | answer | A-PWD-V1@1.0/4.4/1, A-PWD-V1@1.0/2/1 | no |
| G-12 | 2 | tenant-a | behaviour | ok | answer | A-PWD-V1@1.0/4.4/1, A-PWD-V2@2.0/5/1, A-PWD-V1@1.0/2/1 | yes |
| G-12 | 3 | tenant-a | behaviour | ok | answer | A-PWD-V1@1.0/4.4/1, A-PWD-V1@1.0/2/1 | no |
| G-14 | 1 | tenant-b | behaviour | ok | answer | B-MFA@1.0/7.1/1 | yes |
| G-14 | 2 | tenant-b | behaviour | ok | answer | B-MFA@1.0/7.1/1 | yes |
| G-14 | 3 | tenant-b | behaviour | ok | answer | B-MFA@1.0/7.1/1 | yes |
| G-16 | 1 | tenant-a | behaviour | ok | answer | A-LIFE@1.1/5.2/1, A-MFA@1.0/6.1/1 | yes |
| G-16 | 2 | tenant-a | behaviour | ok | answer | A-LIFE@1.1/5.2/1, A-MFA@1.0/6.1/1 | yes |
| G-16 | 3 | tenant-a | behaviour | ok | answer | A-LIFE@1.1/5.2/1, A-MFA@1.0/6.1/1 | yes |
| G-17 | 1 | tenant-a | behaviour | ok | answer | A-MFA@1.0/2.1/1, A-PWD-V2@2.0/4.7/1 | no |
| G-17 | 2 | tenant-a | behaviour | ok | answer | A-PWD-V2@2.0/5/1, A-MFA@1.0/2.1/1, A-FAQ@1.0/Q6/1, A-PWD-V2@2.0/4.7/1, A-DEVICE-B@1.0/2/1 | no |
| G-17 | 3 | tenant-a | behaviour | ok | answer | A-MFA@1.0/2.1/1, A-PWD-V2@2.0/4.7/1, A-DEVICE-B@1.0/2/1 | no |
| G-19 | 1 | tenant-a | behaviour | ok | abstain | A-CLASS@1.1/A.1/1, A-REMOTE@1.1/4.6/1, A-CLASS@1.1/4.3/1, A-DEVICE@1.2/3.2/1, A-FAQ@1.0/Q7/1 | no |
| G-19 | 2 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q7/1 | yes |
| G-19 | 3 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q7/1, A-CLASS@1.1/A.1/1, A-DEVICE@1.2/3.2/1, A-REMOTE@1.1/4.6/1 | yes |
| G-21 | 1 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q6/1 | yes |
| G-21 | 2 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q6/1, A-FAQ@1.0/Q5/1 | yes |
| G-21 | 3 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q6/1 | yes |
| G-22 | 1 | tenant-a | behaviour | ok | abstain | - | no |
| G-22 | 2 | tenant-a | behaviour | ok | answer | X-NCSC@1.0/3/1, X-NIST@SP_800-63B-4/intro/1, A-PWD-V2@2.0/2/1, A-PWD-V2@2.0/6/1 | no |
| G-22 | 3 | tenant-a | behaviour | ok | answer | A-PWD-V2@2.0/6/1, A-PWD-V2@2.0/2/1, X-NCSC@1.0/3/1, X-NCSC@1.0/intro/1, X-NIST@SP_800-63B-4/intro/1 | no |
| G-23 | 1 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q4/1, A-MFA@1.0/5.1/1 | no |
| G-23 | 2 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q4/1, A-MFA@1.0/5.1/1 | no |
| G-23 | 3 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q4/1, A-MFA@1.0/5.3/1, A-MFA@1.0/5.1/1 | no |
| G-25 | 1 | tenant-b | behaviour | ok | answer | B-PWD@1.0/3.3/1, B-PWD@1.0/2/1 | no |
| G-25 | 2 | tenant-b | behaviour | ok | answer | B-PWD@1.0/2/1, B-PWD@1.0/3.3/1 | no |
| G-25 | 3 | tenant-b | behaviour | ok | answer | B-PWD@1.0/3.3/1, B-PWD@1.0/2/1 | no |
| G-26 | 1 | tenant-b | behaviour | ok | answer | B-PWD@1.0/3.3/1, B-PWD@1.0/5/1 | no |
| G-26 | 2 | tenant-b | behaviour | ok | answer | B-PWD@1.0/3.3/1, B-PWD@1.0/5/1, B-PWD@1.0/2/1 | no |
| G-26 | 3 | tenant-b | behaviour | ok | answer | B-PWD@1.0/3.3/1 | no |
| G-28 | 1 | tenant-b | behaviour | ok | answer | B-MFA@1.0/7.1/1 | no |
| G-28 | 2 | tenant-b | behaviour | ok | answer | B-MFA@1.0/7.1/1 | no |
| G-28 | 3 | tenant-b | behaviour | ok | answer | B-MFA@1.0/7.1/1 | no |
| G-29 | 1 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q2/1, X-NCSC@1.0/3/1, A-PWD-V2@2.0/4.4/1 | yes |
| G-29 | 2 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q2/1, A-PWD-V2@2.0/4.4/1, X-NCSC@1.0/3/1 | yes |
| G-29 | 3 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q2/1, A-PWD-V2@2.0/4.4/1, X-NCSC@1.0/3/1 | yes |
| G-31 | 1 | tenant-a | behaviour | ok | answer | A-PWD-V2@2.0/4.2/1 | no |
| G-31 | 2 | tenant-a | behaviour | ok | answer | A-PWD-V2@2.0/4.2/1 | no |
| G-31 | 3 | tenant-a | behaviour | ok | answer | A-PWD-V2@2.0/4.2/1 | no |
| G-33 | 1 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q4/1, A-MFA@1.0/5.1/1, A-MFA@1.0/5.2/1, A-DEVICE@1.2/3.4/1 | yes |
| G-33 | 2 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q4/1, A-MFA@1.0/5.1/1, A-DEVICE@1.2/3.4/1 | yes |
| G-33 | 3 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q4/1, A-MFA@1.0/5.1/1, A-DEVICE@1.2/3.4/1, A-MFA@1.0/5.2/1 | yes |
| G-34 | 1 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q2/1, A-PWD-V2@2.0/4.4/1 | no |
| G-34 | 2 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q2/1, A-PWD-V2@2.0/4.4/1 | no |
| G-34 | 3 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q2/1, A-PWD-V2@2.0/4.4/1, X-NCSC@1.0/1/1 | no |
| G-36 | 1 | tenant-a | behaviour | ok | answer | A-DEVICE@1.2/3.3/1 | yes |
| G-36 | 2 | tenant-a | behaviour | ok | answer | A-DEVICE@1.2/3.3/1 | yes |
| G-36 | 3 | tenant-a | behaviour | ok | answer | A-DEVICE@1.2/3.3/1 | yes |
| G-40 | 1 | tenant-a | behaviour | ok | answer | A-PRIV@1.0/6.3/1 | yes |
| G-40 | 2 | tenant-a | behaviour | ok | answer | A-PRIV@1.0/6.3/1 | yes |
| G-40 | 3 | tenant-a | behaviour | ok | answer | A-PRIV@1.0/6.3/1 | yes |
| G-41 | 1 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q4/1, A-MFA@1.0/5.1/1, A-MFA@1.0/5.2/1 | yes |
| G-41 | 2 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q4/1, A-MFA@1.0/5.1/1, A-MFA@1.0/5.2/1, A-MFA@1.0/3.1/1 | yes |
| G-41 | 3 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q4/1, A-MFA@1.0/5.1/1 | yes |
| G-42 | 1 | tenant-a | behaviour | ok | answer | A-PRIV@1.0/6.3/1, A-FAQ@1.0/Q9/1 | yes |
| G-42 | 2 | tenant-a | behaviour | ok | answer | A-PRIV@1.0/6.3/1, A-FAQ@1.0/Q9/1 | yes |
| G-42 | 3 | tenant-a | behaviour | ok | answer | A-PRIV@1.0/6.3/1, A-FAQ@1.0/Q9/1 | yes |
| G-43 | 1 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q10/1, A-PWD-V2@2.0/4.6/1, A-PWD-V2@2.0/2/1 | yes |
| G-43 | 2 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q10/1, A-PWD-V2@2.0/4.6/1, A-PWD-V2@2.0/2/1 | yes |
| G-43 | 3 | tenant-a | behaviour | ok | answer | A-PWD-V2@2.0/4.6/1, A-FAQ@1.0/Q10/1 | yes |
| G-47 | 1 | tenant-a | behaviour | ok | answer | A-DEVICE@1.2/5/1, A-PRIV@1.0/5.1/1 | no |
| G-47 | 2 | tenant-a | behaviour | ok | answer | A-PRIV@1.0/5.1/1, A-DEVICE@1.2/5/1 | no |
| G-47 | 3 | tenant-a | behaviour | ok | answer | A-DEVICE@1.2/5/1, A-PRIV@1.0/5.1/1 | no |
| G-48 | 1 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q5/1, A-MFA@1.0/5.3/1 | no |
| G-48 | 2 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q5/1, A-MFA@1.0/5.3/1 | no |
| G-48 | 3 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q5/1, A-MFA@1.0/5.3/1 | no |
| G-50 | 1 | tenant-a | behaviour | ok | answer | A-DEVICE@1.2/5/1 | yes |
| G-50 | 2 | tenant-a | behaviour | ok | answer | A-DEVICE@1.2/5/1 | yes |
| G-50 | 3 | tenant-a | behaviour | ok | answer | A-CLASS@1.1/A.3/1, A-DEVICE@1.2/5/1, A-FAQ@1.0/Q4/1, A-FAQ@1.0/Q6/1, A-IR@1.0/3.2/1 | yes |
| G-51 | 1 | tenant-a | behaviour | ok | answer | A-MFA@1.0/5.1/1 | yes |
| G-51 | 2 | tenant-a | behaviour | ok | answer | A-MFA@1.0/5.1/1 | yes |
| G-51 | 3 | tenant-a | behaviour | ok | answer | A-MFA@1.0/5.1/1 | yes |
| G-52 | 1 | tenant-a | behaviour | ok | answer | A-DEVICE-B@1.0/1/1 | no |
| G-52 | 2 | tenant-a | behaviour | ok | answer | A-DEVICE-B@1.0/1/1 | no |
| G-52 | 3 | tenant-a | behaviour | ok | answer | A-DEVICE-B@1.0/1/1, A-DEVICE-B@1.0/intro/1 | no |
| G-53 | 1 | tenant-a | behaviour | ok | answer | A-MFA@1.0/2.1/1, A-MFA@1.0/4.1/1, A-FAQ@1.0/Q6/1 | yes |
| G-53 | 2 | tenant-a | behaviour | ok | answer | A-MFA@1.0/2.1/1, A-MFA@1.0/5.3/1, A-FAQ@1.0/Q5/1, A-FAQ@1.0/Q6/1 | yes |
| G-53 | 3 | tenant-a | behaviour | ok | answer | A-MFA@1.0/2.1/1, A-FAQ@1.0/Q6/1 | yes |
| G-54 | 1 | tenant-a | behaviour | ok | answer | A-PWD-V1@1.0/4.4/1 | no |
| G-54 | 2 | tenant-a | behaviour | ok | answer | A-PWD-V1@1.0/4.4/1, X-NCSC@1.0/1/1 | no |
| G-54 | 3 | tenant-a | behaviour | ok | answer | A-PWD-V1@1.0/4.4/1 | no |
| G-55 | 1 | tenant-a | behaviour | ok | answer | A-MFA@1.0/7.1/1, A-FAQ@1.0/Q5/1, A-MFA@1.0/5.3/1, A-MFA@1.0/2.1/1 | yes |
| G-55 | 2 | tenant-a | behaviour | ok | answer | A-MFA@1.0/7.1/1 | yes |
| G-55 | 3 | tenant-a | behaviour | ok | answer | A-MFA@1.0/7.1/1, A-FAQ@1.0/Q5/1, A-MFA@1.0/5.3/1, A-MFA@1.0/2.1/1 | yes |
| G-56 | 1 | tenant-b | behaviour | ok | answer | B-PWD@1.0/1/1, B-PWD@1.0/5/1 | no |
| G-56 | 2 | tenant-b | behaviour | ok | answer | B-PWD@1.0/5/1, B-PWD@1.0/6/1 | no |
| G-56 | 3 | tenant-b | behaviour | ok | answer | B-PWD@1.0/1/1 | no |
| G-58 | 1 | tenant-b | behaviour | blocked | abstain | - | no |
| G-58 | 2 | tenant-b | behaviour | ok | answer | B-PWD@1.0/6/1, B-MFA@1.0/5.1/1 | no |
| G-58 | 3 | tenant-b | behaviour | ok | answer | B-PWD@1.0/6/1, B-MFA@1.0/5.1/1, B-MFA@1.0/1/1, B-PWD@1.0/2/1 | no |
| G-61 | 1 | tenant-b | behaviour | ok | answer | B-MFA@1.0/3.1/1 | yes |
| G-61 | 2 | tenant-b | behaviour | ok | answer | B-MFA@1.0/3.1/1 | yes |
| G-61 | 3 | tenant-b | behaviour | ok | answer | B-MFA@1.0/3.1/1 | yes |
| G-62 | 1 | tenant-b | behaviour | ok | answer | B-MFA@1.0/4/1 | yes |
| G-62 | 2 | tenant-b | behaviour | ok | answer | B-MFA@1.0/4/1 | yes |
| G-62 | 3 | tenant-b | behaviour | ok | answer | B-MFA@1.0/4/1 | yes |
| G-63 | 1 | tenant-b | behaviour | ok | answer | B-PWD@1.0/3.2/1 | yes |
| G-63 | 2 | tenant-b | behaviour | ok | answer | B-PWD@1.0/3.2/1 | yes |
| G-63 | 3 | tenant-b | behaviour | ok | answer | B-PWD@1.0/3.2/1 | yes |
| G-64 | 1 | tenant-b | behaviour | ok | answer | B-PWD@1.0/6/1 | yes |
| G-64 | 2 | tenant-b | behaviour | ok | answer | B-PWD@1.0/6/1 | yes |
| G-64 | 3 | tenant-b | behaviour | ok | answer | B-PWD@1.0/6/1 | yes |
| G-65 | 1 | tenant-b | behaviour | ok | abstain | B-PWD@1.0/5/1, B-PWD@1.0/3.3/1, B-PWD@1.0/6/1, B-PWD@1.0/2/1, B-MFA@1.0/5.1/1 | no |
| G-65 | 2 | tenant-b | behaviour | ok | answer | B-PWD@1.0/5/1, B-PWD@1.0/2/1 | no |
| G-65 | 3 | tenant-b | behaviour | ok | answer | B-PWD@1.0/5/1 | no |
| G-67 | 1 | tenant-b | behaviour | ok | answer | B-PWD@1.0/5/1 | no |
| G-67 | 2 | tenant-b | behaviour | ok | answer | B-PWD@1.0/5/1 | no |
| G-67 | 3 | tenant-b | behaviour | ok | answer | B-PWD@1.0/5/1 | no |
| G-68 | 1 | tenant-a | behaviour | ok | answer | A-PWD-V2@2.0/4.4/1, X-NCSC@1.0/3/1, X-NIST@SP_800-63B-4/intro/1 | no |
| G-68 | 2 | tenant-a | behaviour | ok | answer | A-PWD-V2@2.0/4.4/1, X-NCSC@1.0/intro/1, X-NCSC@1.0/3/1, X-NIST@SP_800-63B-4/intro/1 | no |
| G-68 | 3 | tenant-a | behaviour | ok | answer | A-PWD-V2@2.0/4.4/1, A-PWD-V2@2.0/6/1, X-NCSC@1.0/3/1, X-NIST@SP_800-63B-4/intro/1 | no |
| G-71 | 1 | tenant-a | behaviour | ok | answer | X-NCSC@1.0/1/1, A-PWD-V1@1.0/4.4/1, A-PWD-V2@2.0/6/1 | yes |
| G-71 | 2 | tenant-a | behaviour | ok | answer | X-NCSC@1.0/1/1, A-PWD-V1@1.0/4.4/1 | yes |
| G-71 | 3 | tenant-a | behaviour | ok | answer | A-PWD-V1@1.0/4.4/1 | no |
| G-73 | 1 | tenant-a | behaviour | ok | answer | A-PRIV@1.0/7.2/1 | yes |
| G-73 | 2 | tenant-a | behaviour | ok | answer | A-PRIV@1.0/7.2/1 | yes |
| G-73 | 3 | tenant-a | behaviour | ok | answer | A-PRIV@1.0/7.2/1 | yes |
| G-74 | 1 | tenant-a | behaviour | ok | answer | A-PRIV@1.0/4.1/1, A-PWD-V2@2.0/2/1, A-PWD-V1@1.0/4.4/1 | no |
| G-74 | 2 | tenant-a | behaviour | ok | answer | A-PWD-V1@1.0/4.4/1, A-PWD-V2@2.0/2/1, A-PRIV@1.0/4.1/1 | no |
| G-74 | 3 | tenant-a | behaviour | ok | answer | A-PWD-V2@2.0/2/1, A-PWD-V1@1.0/4.4/1, A-PRIV@1.0/4.1/1 | no |
| G-75 | 1 | tenant-a | behaviour | ok | answer | A-LIFE@1.1/3.1/1 | yes |
| G-75 | 2 | tenant-a | behaviour | ok | answer | A-LIFE@1.1/3.1/1 | yes |
| G-75 | 3 | tenant-a | behaviour | ok | answer | A-LIFE@1.1/5/1, A-LIFE@1.1/3.1/1 | yes |
| G-76 | 1 | tenant-a | behaviour | ok | answer | A-IR@1.0/6.1/1, A-MFA@1.0/6.1/1, A-MFA@1.0/7.1/1 | no |
| G-76 | 2 | tenant-a | behaviour | ok | answer | A-IR@1.0/3.1/1, A-MFA@1.0/6.1/1, A-MFA@1.0/7.1/1 | no |
| G-76 | 3 | tenant-a | behaviour | ok | answer | A-IR@1.0/6.1/1 | no |
| G-78 | 1 | tenant-a | behaviour | ok | answer | A-EXC@1.0/5.2/1, A-EXC@1.0/5.1/1, A-REMOTE@1.1/4.5/1 | yes |
| G-78 | 2 | tenant-a | behaviour | ok | answer | A-EXC@1.0/5.2/1, A-EXC@1.0/5.1/1, A-REMOTE@1.1/4.5/1 | yes |
| G-78 | 3 | tenant-a | behaviour | ok | answer | A-EXC@1.0/5.2/1, A-EXC@1.0/5.1/1, A-REMOTE@1.1/4.5/1 | yes |
| G-79 | 1 | tenant-a | behaviour | ok | answer | A-MFA@1.0/4.1/1, A-PRIV@1.0/6/1, A-EXC@1.0/2.1/1 | no |
| G-79 | 2 | tenant-a | behaviour | ok | answer | A-MFA@1.0/4.1/1, A-PRIV@1.0/6/1, A-EXC@1.0/2.1/1 | no |
| G-79 | 3 | tenant-a | behaviour | ok | answer | A-MFA@1.0/4.1/1, A-MFA@1.0/5.2/1, A-PRIV@1.0/6/1, A-EXC@1.0/2.1/1 | no |
| G-80 | 1 | tenant-a | behaviour | ok | abstain | A-FAQ@1.0/Q7/1, A-DEVICE@1.2/6.1/1, A-EXC@1.0/5.1/1 | no |
| G-80 | 2 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q7/1, A-DEVICE@1.2/6.1/1, A-EXC@1.0/5.1/1 | no |
| G-80 | 3 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q7/1, A-DEVICE@1.2/6.1/1 | no |
| G-81 | 1 | tenant-b | behaviour | ok | answer | B-MFA@1.0/5.1/1, B-PWD@1.0/6/1 | no |
| G-81 | 2 | tenant-b | behaviour | ok | answer | B-MFA@1.0/2/1, B-MFA@1.0/5.1/1 | no |
| G-81 | 3 | tenant-b | behaviour | ok | answer | B-MFA@1.0/5.1/1, B-MFA@1.0/1/1, B-PWD@1.0/6/1 | no |
| G-82 | 1 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q7/1, A-FAQ@1.0/Q11/1, A-EXC@1.0/5.1/1, A-EXC@1.0/3.3/1, A-DEVICE@1.2/6.1/1 | yes |
| G-82 | 2 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q7/1, A-FAQ@1.0/Q11/1, A-EXC@1.0/5.1/1 | yes |
| G-82 | 3 | tenant-a | behaviour | ok | answer | A-DEVICE@1.2/6.1/1, A-FAQ@1.0/Q7/1, A-EXC@1.0/5.1/1, A-EXC@1.0/3.3/1, A-FAQ@1.0/Q11/1 | yes |
| G-84 | 1 | tenant-b | behaviour | ok | abstain | - | yes |
| G-84 | 2 | tenant-b | behaviour | ok | answer | B-PWD@1.0/3.3/1, B-PWD@1.0/3.2/1, B-PWD@1.0/5/1 | no |
| G-84 | 3 | tenant-b | behaviour | ok | abstain | B-PWD@1.0/3.3/1, B-PWD@1.0/5/1, B-PWD@1.0/2/1, B-PWD@1.0/3.2/1 | yes |
| G-86 | 1 | tenant-b | behaviour | blocked | abstain | - | no |
| G-86 | 2 | tenant-b | behaviour | ok | abstain | - | yes |
| G-86 | 3 | tenant-b | behaviour | ok | abstain | B-PWD@1.0/3.3/1, B-MFA@1.0/7.1/1, B-PWD@1.0/6/1, B-PWD@1.0/5/1, B-PWD@1.0/2/1 | yes |
| G-88 | 1 | tenant-b | behaviour | ok | answer | B-MFA@1.0/7.1/1 | no |
| G-88 | 2 | tenant-b | behaviour | ok | answer | B-MFA@1.0/1/1, B-MFA@1.0/5.1/1, B-PWD@1.0/5/1, B-PWD@1.0/3.3/1 | no |
| G-88 | 3 | tenant-b | behaviour | ok | answer | B-PWD@1.0/3.3/1, B-MFA@1.0/7.1/1, B-PWD@1.0/5/1, B-MFA@1.0/5.1/1, B-MFA@1.0/1/1 | no |
| G-89 | 1 | tenant-b | behaviour | ok | answer | B-MFA@1.0/5.1/1, B-PWD@1.0/6/1, B-PWD@1.0/5/1 | no |
| G-89 | 2 | tenant-b | behaviour | ok | answer | B-MFA@1.0/5.1/1, B-PWD@1.0/6/1 | no |
| G-89 | 3 | tenant-b | behaviour | ok | answer | B-MFA@1.0/5.1/1 | no |
| G-90 | 1 | tenant-b | behaviour | ok | answer | B-MFA@1.0/2/1, B-MFA@1.0/4/1, B-MFA@1.0/7.1/1 | no |
| G-90 | 2 | tenant-b | behaviour | ok | answer | B-MFA@1.0/1/1, B-MFA@1.0/2/1, B-MFA@1.0/4/1, B-MFA@1.0/7.1/1 | no |
| G-90 | 3 | tenant-b | behaviour | ok | answer | B-MFA@1.0/4/1, B-MFA@1.0/2/1 | no |
| G-92 | 1 | tenant-b | behaviour | ok | abstain | - | yes |
| G-92 | 2 | tenant-b | behaviour | ok | answer | B-PWD@1.0/3.3/1 | no |
| G-92 | 3 | tenant-b | behaviour | ok | answer | B-PWD@1.0/3.3/1 | no |
| G-94 | 1 | tenant-a | behaviour | ok | answer | A-LIFE@1.1/3.1/1 | no |
| G-94 | 2 | tenant-a | behaviour | ok | answer | A-LIFE@1.1/3.1/1 | no |
| G-94 | 3 | tenant-a | behaviour | ok | answer | A-LIFE@1.1/4/1, A-LIFE@1.1/3.1/1 | no |
| G-95 | 1 | tenant-a | behaviour | ok | answer | A-LIFE@1.1/7.1/1 | no |
| G-95 | 2 | tenant-a | behaviour | ok | answer | A-LIFE@1.1/7.1/1 | no |
| G-95 | 3 | tenant-a | behaviour | ok | answer | A-LIFE@1.1/7.1/1 | no |
| G-97 | 1 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q12/1 | no |
| G-97 | 2 | tenant-a | behaviour | ok | answer | A-DEVICE@1.2/3.4/1 | no |
| G-97 | 3 | tenant-a | behaviour | ok | answer | A-DEVICE@1.2/3.4/1, A-MFA@1.0/5.1/1, A-FAQ@1.0/Q12/1 | no |
| G-98 | 1 | tenant-a | behaviour | ok | answer | A-REMOTE@1.1/4.5/1, A-EXC@1.0/5.2/1, A-EXC@1.0/5.1/1 | no |
| G-98 | 2 | tenant-a | behaviour | ok | answer | A-REMOTE@1.1/4.5/1, A-EXC@1.0/5.2/1, A-EXC@1.0/5.1/1 | no |
| G-98 | 3 | tenant-a | behaviour | ok | answer | A-REMOTE@1.1/4.5/1, A-EXC@1.0/5.2/1, A-EXC@1.0/5.1/1 | no |
| G-99 | 1 | tenant-a | behaviour | ok | answer | A-EXC@1.0/4.1/1 | no |
| G-99 | 2 | tenant-a | behaviour | ok | answer | A-EXC@1.0/4.1/1, A-EXC@1.0/4.2/1, A-DEVICE@1.2/6.2/1 | no |
| G-99 | 3 | tenant-a | behaviour | ok | answer | A-EXC@1.0/4.1/1 | no |
| G-100 | 1 | tenant-a | behaviour | ok | answer | A-PWD-V1@1.0/4.1/1, A-PWD-V2@2.0/4.1/1, A-FAQ@1.0/Q1/1 | no |
| G-100 | 2 | tenant-a | behaviour | ok | answer | A-PWD-V2@2.0/4.1/1, A-PWD-V1@1.0/4.1/1 | no |
| G-100 | 3 | tenant-a | behaviour | ok | answer | A-PWD-V2@2.0/4.1/1, A-PWD-V1@1.0/4.1/1 | no |
| G-101 | 1 | tenant-a | behaviour | ok | answer | A-PWD-V1@1.0/4.2/1, A-PWD-V2@2.0/4.1/1, A-FAQ@1.0/Q1/1 | no |
| G-101 | 2 | tenant-a | behaviour | ok | answer | A-PWD-V1@1.0/4.2/1, A-PWD-V2@2.0/4.2/1, A-FAQ@1.0/Q1/1 | no |
| G-101 | 3 | tenant-a | behaviour | ok | answer | A-PWD-V1@1.0/4.2/1, A-PWD-V2@2.0/4.2/1, A-FAQ@1.0/Q1/1 | no |
| G-103 | 1 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q2/1, X-NCSC@1.0/3/1 | yes |
| G-103 | 2 | tenant-a | behaviour | ok | answer | X-NCSC@1.0/3/1, A-FAQ@1.0/Q2/1 | yes |
| G-103 | 3 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q2/1, X-NCSC@1.0/3/1 | yes |
| G-105 | 1 | tenant-a | behaviour | ok | answer | A-PWD-V2@2.0/4.2/1, A-PWD-V1@1.0/4.2/1 | no |
| G-105 | 2 | tenant-a | behaviour | ok | answer | A-PWD-V2@2.0/4.2/1 | no |
| G-105 | 3 | tenant-a | behaviour | ok | answer | A-PWD-V2@2.0/4.2/1, A-PWD-V1@1.0/4.2/1, A-FAQ@1.0/Q1/1 | yes |
| G-106 | 1 | tenant-a | behaviour | ok | answer | A-PWD-V2@2.0/4.1/1, A-FAQ@1.0/Q1/1 | yes |
| G-106 | 2 | tenant-a | behaviour | ok | answer | A-PWD-V2@2.0/4.1/1, A-FAQ@1.0/Q1/1 | yes |
| G-106 | 3 | tenant-a | behaviour | ok | answer | A-PWD-V2@2.0/4.1/1, A-FAQ@1.0/Q1/1 | yes |
| G-108 | 1 | tenant-b | behaviour | ok | answer | B-MFA@1.0/5.1/1, B-MFA@1.0/2/1, B-PWD@1.0/6/1 | yes |
| G-108 | 2 | tenant-b | behaviour | ok | answer | B-MFA@1.0/5.1/1 | yes |
| G-108 | 3 | tenant-b | behaviour | ok | answer | B-MFA@1.0/5.1/1, B-MFA@1.0/7.1/1, B-PWD@1.0/6/1, B-MFA@1.0/3.1/1, B-MFA@1.0/2/1 | yes |
| G-109 | 1 | tenant-a | behaviour | ok | answer | A-PWD-V1@1.0/4.3/1, A-FAQ@1.0/Q2/1 | no |
| G-109 | 2 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q2/1, A-PWD-V1@1.0/4.3/1 | no |
| G-109 | 3 | tenant-a | behaviour | ok | answer | A-PWD-V1@1.0/4.3/1, A-FAQ@1.0/Q2/1 | no |
| G-110 | 1 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q2/1, A-PWD-V2@2.0/4.4/1 | yes |
| G-110 | 2 | tenant-a | behaviour | ok | answer | A-PWD-V2@2.0/4.4/1, X-NCSC@1.0/3/1, A-FAQ@1.0/Q2/1 | no |
| G-110 | 3 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q2/1, A-PWD-V2@2.0/4.4/1, X-NCSC@1.0/3/1 | yes |
| G-113 | 1 | tenant-b | behaviour | ok | answer | B-MFA@1.0/3.1/1, B-PWD@1.0/6/1 | no |
| G-113 | 2 | tenant-b | behaviour | ok | answer | B-MFA@1.0/3.1/1 | no |
| G-113 | 3 | tenant-b | behaviour | ok | answer | B-MFA@1.0/3.1/1 | no |
| G-114 | 1 | tenant-a | behaviour | ok | answer | A-LIFE@1.1/3.3/1 | no |
| G-114 | 2 | tenant-a | behaviour | ok | answer | A-LIFE@1.1/3.3/1, A-MFA@1.0/5.3/1, A-FAQ@1.0/Q5/1 | no |
| G-114 | 3 | tenant-a | behaviour | ok | answer | A-LIFE@1.1/3.3/1, A-MFA@1.0/5.3/1, A-FAQ@1.0/Q5/1 | no |
