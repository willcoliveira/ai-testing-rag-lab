# Run 20261020T130229Z-generation-local-ollama-release-test-2c6aa85

Generated from manifest.json and cases.jsonl by raglab; never edited by hand.

| | |
|---|---|
| Suite | generation, split test, 3 trial(s), seed 20261018, gate release |
| Provenance | local |
| Created | 2026-10-20T13:02:29Z |
| Git | 2c6aa8590d23e79f21e8c0e1a999402ddf46ca3e (clean) |
| Config | generation-local-ollama-release (`config/local-ollama-release.toml`, sha256 a8f3e489f38d) |
| Generator | nemotron-3.5-lightning:30b-a3b-mlx (openai-compat, digest d1e17d7dabac, server 0.40.6) |
| Settings | temperature 1.0, top_p 0.95, max_tokens 1024, timeout_s 120.0, response_format none, reasoning_effort none |
| Prompt | answer-v1 (sha256 96f42d9bc9c7) |
| Guards | tenant, input-limits, citations |
| Embedder | BAAI/bge-small-en-v1.5 at revision aa8f8b060edb |
| Retriever | dense, k = 5 |
| Chunker | 1200 characters, overlap 1 |
| Corpus | 18 documents, 228 chunks, sha256 8918d4f79673 |
| Dataset | `datasets/golden.v1.jsonl`, sha256 5f8cdaf18783 |
| Cases | 25 (75 case-trials) |

## Checks (no judge)

Rates over every trial, with a 95% Wilson interval at n = the number of cases. A citation hit means the answer cites a labelled chunk; it is not correctness (S5 judges that). Only behaviour pass^3 on the dev split is gated, by the consistency gate (Q-05; docs/THRESHOLDS.md), and locally until keys exist; the rest is reported.

pass^3: a case passes only when all 3 trials pass every check that applies; trial t uses seed 20261018 + t - 1 at temperature 1.0, so it measures whether the model passes consistently while it samples at that temperature, not whether it is correct.

| Check | Rate | 95% interval | n (cases) |
|---|---|---|---|
| status_ok | 1.000 | 0.867 to 1.000 | 25 |
| model_citations_retrieved | 1.000 | 0.867 to 1.000 | 25 |
| citation_hit | 0.917 | 0.646 to 0.985 | 12 |
| pass^3 | 0.600 | 0.407 to 0.766 | 25 |
| decision_label | 0.615 | 0.355 to 0.823 | 13 |
| decision_label[answer] | 1.000 | 0.676 to 1.000 | 8 |
| decision_label[abstain] | 0.000 | 0.000 to 0.561 | 3 |
| decision_label[flag-conflict] | 0.000 | 0.000 to 0.793 | 1 |
| decision_label[refuse-and-help] | 0.000 | 0.000 to 0.793 | 1 |
| abstention | 0.000 | 0.000 to 0.561 | 3 |
| over_abstention | 0.000 | 0.000 to 0.278 | 10 |
| behaviour_pass^3 | 0.308 | 0.127 to 0.576 | 13 |

## Run

- Status counts: ok 75, refused 0, blocked 0, unavailable 0, invalid_output 0
- Label agreement: 24 of 25 cases gave the same label in every trial
- Latency: p50 1458.322 ms, p95 2812.554 ms (n 75)
- Tokens: 77607 prompt and 8236 completion, from the 75 case-trials whose server reported them

## Behaviour cases (decision label and abstention, no judge)

The decision label is the structured `label` field, never the text. A flag-conflict case whose conflict side was not retrieved expects answer with no conflict field; the miss counts against retrieval (0 such case-trial(s)).

Expected (rows) against given (columns), in case-trials:

| Expected | answer | abstain | flag-conflict | refuse-and-help | withheld |
|---|---|---|---|---|---|
| answer | 24 | 0 | 0 | 0 | 0 |
| abstain | 9 | 0 | 0 | 0 | 0 |
| flag-conflict | 3 | 0 | 0 | 0 | 0 |
| refuse-and-help | 3 | 0 | 0 | 0 | 0 |

Abstain cases, the oracle's two checks combined (case-trials): label abstain or not, and a value stated or not. "Not abstain, no value" is the S3 pattern.

| Label | No value stated | Value stated |
|---|---|---|
| abstain | 0 | 0 |
| not abstain | 2 | 7 |

- Label agreement: 13 of 13 behaviour cases gave the same label in all 3 trials, right or wrong (behaviour pass^3 counts the cases whose every trial passed every check that applies).
- Label failures (case-trials): 6 with every labelled section retrieved, 0 with a labelled section missed, 9 on abstain cases (no labels).

| Case | Mix | Expected | Given, by trial | Passed |
|---|---|---|---|---|
| G-02 | single-chunk | answer | answer, answer, answer | 0 of 3 |
| G-04 | single-chunk | answer | answer, answer, answer | 0 of 3 |
| G-07 | single-chunk | answer | answer, answer, answer | 3 of 3 |
| G-13 | single-chunk | refuse-and-help | answer, answer, answer | 0 of 3 |
| G-15 | single-chunk | answer | answer, answer, answer | 3 of 3 |
| G-18 | multi-chunk | answer | answer, answer, answer | 3 of 3 |
| G-20 | multi-chunk | answer | answer, answer, answer | 0 of 3 |
| G-24 | unanswerable | abstain | answer, answer, answer | 0 of 3 |
| G-27 | unanswerable | abstain | answer, answer, answer | 0 of 3 |
| G-30 | version-conflict | flag-conflict | answer, answer, answer | 0 of 3 |
| G-32 | version-conflict | answer | answer, answer, answer | 0 of 3 |
| G-35 | paraphrase | answer | answer, answer, answer | 3 of 3 |
| G-37 | misspelling | abstain | answer, answer, answer | 0 of 3 |

## Case-trials

| Case | Trial | Tenant | Kind | Status | Label | Cited | Passed |
|---|---|---|---|---|---|---|---|
| R-Q03 | 1 | tenant-a | retrieval | ok | answer | A-MFA@1.0/7.1/1 | yes |
| R-Q03 | 2 | tenant-a | retrieval | ok | answer | A-MFA@1.0/7.1/1 | yes |
| R-Q03 | 3 | tenant-a | retrieval | ok | answer | A-MFA@1.0/7.1/1 | yes |
| R-Q06 | 1 | tenant-a | retrieval | ok | answer | A-PWD-V1@1.0/4.4/1 | no |
| R-Q06 | 2 | tenant-a | retrieval | ok | answer | A-PWD-V1@1.0/4.4/1 | no |
| R-Q06 | 3 | tenant-a | retrieval | ok | answer | A-PWD-V1@1.0/4.4/1 | no |
| R-Q09 | 1 | tenant-a | retrieval | ok | answer | A-REMOTE@1.1/4.4/1, A-LIFE@1.1/5.4/1, A-LIFE@1.1/5.1/1 | yes |
| R-Q09 | 2 | tenant-a | retrieval | ok | answer | A-REMOTE@1.1/4.4/1, A-LIFE@1.1/5.1/1 | yes |
| R-Q09 | 3 | tenant-a | retrieval | ok | answer | A-REMOTE@1.1/4.4/1, A-LIFE@1.1/5.4/1 | yes |
| R-Q12 | 1 | tenant-a | retrieval | ok | answer | A-GLOSS@1.0/10/1, A-PRIV@1.0/1/1 | yes |
| R-Q12 | 2 | tenant-a | retrieval | ok | answer | A-GLOSS@1.0/10/1, A-PRIV@1.0/4.1/1, A-PRIV@1.0/1/1 | yes |
| R-Q12 | 3 | tenant-a | retrieval | ok | answer | A-GLOSS@1.0/10/1, A-PRIV@1.0/4.1/1 | yes |
| R-Q15 | 1 | tenant-a | retrieval | ok | answer | A-MFA@1.0/6.1/1 | yes |
| R-Q15 | 2 | tenant-a | retrieval | ok | answer | A-MFA@1.0/6.1/1 | yes |
| R-Q15 | 3 | tenant-a | retrieval | ok | answer | A-MFA@1.0/6.1/1 | yes |
| R-Q17 | 1 | tenant-a | retrieval | ok | answer | A-DEVICE-B@1.0/1/1 | yes |
| R-Q17 | 2 | tenant-a | retrieval | ok | answer | A-DEVICE-B@1.0/1/1 | yes |
| R-Q17 | 3 | tenant-a | retrieval | ok | answer | A-DEVICE-B@1.0/1/1 | yes |
| R-Q20 | 1 | tenant-a | retrieval | ok | answer | A-FAQ@1.0/Q2/1, A-PWD-V1@1.0/4.4/1 | yes |
| R-Q20 | 2 | tenant-a | retrieval | ok | answer | A-PWD-V1@1.0/4.4/1, A-FAQ@1.0/Q2/1, X-NCSC@1.0/1/1 | yes |
| R-Q20 | 3 | tenant-a | retrieval | ok | answer | A-PWD-V1@1.0/4.4/1 | yes |
| R-Q23 | 1 | tenant-a | retrieval | ok | answer | X-NCSC@1.0/3/1, A-FAQ@1.0/Q2/1, A-PWD-V2@2.0/4.4/1 | yes |
| R-Q23 | 2 | tenant-a | retrieval | ok | flag-conflict | X-NCSC@1.0/3/1, A-FAQ@1.0/Q2/1, A-PWD-V2@2.0/4.4/1 | yes |
| R-Q23 | 3 | tenant-a | retrieval | ok | answer | X-NCSC@1.0/3/1, A-PWD-V2@2.0/4.4/1, A-FAQ@1.0/Q2/1 | yes |
| R-Q26 | 1 | tenant-a | retrieval | ok | answer | A-EXC@1.0/5.1/1 | yes |
| R-Q26 | 2 | tenant-a | retrieval | ok | answer | A-EXC@1.0/5.1/1 | yes |
| R-Q26 | 3 | tenant-a | retrieval | ok | answer | A-EXC@1.0/5.1/1 | yes |
| R-Q30 | 1 | tenant-b | retrieval | ok | answer | B-PWD@1.0/4.1/1 | yes |
| R-Q30 | 2 | tenant-b | retrieval | ok | answer | B-PWD@1.0/4.1/1 | yes |
| R-Q30 | 3 | tenant-b | retrieval | ok | answer | B-PWD@1.0/4.1/1 | yes |
| R-Q32 | 1 | tenant-a | retrieval | ok | answer | A-DEVICE@1.2/3.4/1 | yes |
| R-Q32 | 2 | tenant-a | retrieval | ok | answer | A-DEVICE@1.2/3.4/1 | yes |
| R-Q32 | 3 | tenant-a | retrieval | ok | answer | A-DEVICE@1.2/3.4/1 | yes |
| R-Q34 | 1 | tenant-a | retrieval | ok | answer | A-REV@1.0/3.1/1 | yes |
| R-Q34 | 2 | tenant-a | retrieval | ok | answer | A-REV@1.0/3.1/1 | yes |
| R-Q34 | 3 | tenant-a | retrieval | ok | answer | A-REV@1.0/3.1/1 | yes |
| G-02 | 1 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q2/1, A-PWD-V1@1.0/4.3/1 | no |
| G-02 | 2 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q2/1, A-PWD-V1@1.0/4.3/1 | no |
| G-02 | 3 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q2/1 | no |
| G-04 | 1 | tenant-a | behaviour | ok | answer | A-LIFE@1.1/6.1/1 | no |
| G-04 | 2 | tenant-a | behaviour | ok | answer | A-LIFE@1.1/6.1/1 | no |
| G-04 | 3 | tenant-a | behaviour | ok | answer | A-LIFE@1.1/6.1/1 | no |
| G-07 | 1 | tenant-a | behaviour | ok | answer | A-REV@1.0/5.1/1 | yes |
| G-07 | 2 | tenant-a | behaviour | ok | answer | A-REV@1.0/5.1/1 | yes |
| G-07 | 3 | tenant-a | behaviour | ok | answer | A-REV@1.0/5.1/1 | yes |
| G-13 | 1 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q10/1 | no |
| G-13 | 2 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q10/1 | no |
| G-13 | 3 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q10/1 | no |
| G-15 | 1 | tenant-b | behaviour | ok | answer | B-MFA@1.0/5.1/1 | yes |
| G-15 | 2 | tenant-b | behaviour | ok | answer | B-MFA@1.0/5.1/1 | yes |
| G-15 | 3 | tenant-b | behaviour | ok | answer | B-MFA@1.0/5.1/1 | yes |
| G-18 | 1 | tenant-a | behaviour | ok | answer | A-EXC@1.0/5.2/1, A-EXC@1.0/5.1/1, A-REMOTE@1.1/4.5/1 | yes |
| G-18 | 2 | tenant-a | behaviour | ok | answer | A-EXC@1.0/5.2/1, A-EXC@1.0/5.1/1, A-REMOTE@1.1/4.5/1 | yes |
| G-18 | 3 | tenant-a | behaviour | ok | answer | A-REMOTE@1.1/4.5/1, A-EXC@1.0/5.2/1, A-EXC@1.0/5.1/1 | yes |
| G-20 | 1 | tenant-a | behaviour | ok | answer | A-IR@1.0/A.3/1 | no |
| G-20 | 2 | tenant-a | behaviour | ok | answer | A-IR@1.0/A.3/1 | no |
| G-20 | 3 | tenant-a | behaviour | ok | answer | A-IR@1.0/A.3/1 | no |
| G-24 | 1 | tenant-b | behaviour | ok | answer | B-MFA@1.0/7.1/1, B-MFA@1.0/5.1/1 | no |
| G-24 | 2 | tenant-b | behaviour | ok | answer | B-MFA@1.0/7.1/1 | no |
| G-24 | 3 | tenant-b | behaviour | ok | answer | B-MFA@1.0/7.1/1, B-MFA@1.0/5.1/1 | no |
| G-27 | 1 | tenant-a | behaviour | ok | answer | A-DEVICE@1.2/5/1, A-DEVICE@1.2/2/1 | no |
| G-27 | 2 | tenant-a | behaviour | ok | answer | A-DEVICE@1.2/5/1, A-DEVICE@1.2/2/1, A-DEVICE@1.2/3/1, A-MFA@1.0/3.3/1 | no |
| G-27 | 3 | tenant-a | behaviour | ok | answer | A-DEVICE@1.2/5/1, A-DEVICE@1.2/4/1, A-MFA@1.0/3.3/1, A-DEVICE@1.2/3/1, A-DEVICE@1.2/2/1 | no |
| G-30 | 1 | tenant-a | behaviour | ok | answer | A-PWD-V2@2.0/4.4/1, A-PWD-V1@1.0/4.3/1, A-FAQ@1.0/Q2/1 | no |
| G-30 | 2 | tenant-a | behaviour | ok | answer | A-PWD-V2@2.0/4.4/1, A-PWD-V1@1.0/4.3/1, A-FAQ@1.0/Q2/1 | no |
| G-30 | 3 | tenant-a | behaviour | ok | answer | A-PWD-V2@2.0/4.4/1, A-PWD-V1@1.0/4.3/1, A-FAQ@1.0/Q2/1 | no |
| G-32 | 1 | tenant-a | behaviour | ok | answer | A-PWD-V1@1.0/4.4/1 | no |
| G-32 | 2 | tenant-a | behaviour | ok | answer | A-PWD-V1@1.0/4.4/1 | no |
| G-32 | 3 | tenant-a | behaviour | ok | answer | A-PWD-V1@1.0/4.4/1 | no |
| G-35 | 1 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q8/1, A-PWD-V2@2.0/4.5/1 | yes |
| G-35 | 2 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q8/1, A-PWD-V2@2.0/4.5/1 | yes |
| G-35 | 3 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q8/1, A-PWD-V2@2.0/4.5/1 | yes |
| G-37 | 1 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q2/1, A-IR@1.0/5.4/1, X-NCSC@1.0/3/1 | no |
| G-37 | 2 | tenant-a | behaviour | ok | answer | X-NCSC@1.0/3/1, A-IR@1.0/5.4/1, X-NCSC@1.0/1/1, A-PRIV@1.0/6.3/1, A-FAQ@1.0/Q2/1 | no |
| G-37 | 3 | tenant-a | behaviour | ok | answer | A-FAQ@1.0/Q2/1 | no |
