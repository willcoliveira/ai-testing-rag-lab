# Run 20261018T145441Z-generation-local-ollama-dev-fa04154

Generated from manifest.json and cases.jsonl by raglab; never edited by hand.

| | |
|---|---|
| Suite | generation, split dev, 3 trial(s), seed 20261018, gate manual |
| Provenance | local |
| Created | 2026-10-18T14:54:41Z |
| Git | fa04154e19a1e46ed1e74365b5befec6ec21fb9c (clean) |
| Config | generation-local-ollama (`config/local-ollama.toml`, sha256 e991f7cfb166) |
| Generator | nemotron-3.5-lightning:30b-a3b-mlx (openai-compat, digest d1e17d7dabac, server 0.40.6) |
| Settings | temperature 1.0, top_p 0.95, max_tokens 1024, timeout_s 120.0, response_format none, reasoning_effort none |
| Prompt | answer-v1 (sha256 96f42d9bc9c7) |
| Guards | tenant, input-limits, citations |
| Embedder | BAAI/bge-small-en-v1.5 at revision aa8f8b060edb |
| Retriever | dense, k = 5 |
| Chunker | 1200 characters, overlap 1 |
| Corpus | 18 documents, 228 chunks, sha256 8918d4f79673 |
| Dataset | `datasets/golden.v1.jsonl`, sha256 ffb8c5a54b22; probes `datasets/probes.s3.jsonl`, sha256 35b284750c3f |
| Cases | 25 (75 case-trials) |

## Checks (no judge)

Rates over every trial, with a 95% Wilson interval at n = the number of cases. A citation hit means the answer cites a labelled chunk; it is not correctness (S5 judges that). Nothing here is gated.

pass^3: a case passes only when all 3 trials pass every check that applies; trial t uses seed 20261018 + t - 1 at temperature 1.0, so it measures whether the model passes consistently while it samples at that temperature, not whether it is correct.

| Check | Rate | 95% interval | n (cases) |
|---|---|---|---|
| status_ok | 0.960 | 0.805 to 0.993 | 25 |
| citations_retrieved | 1.000 | 0.867 to 1.000 | 25 |
| probe_abstention | 0.000 | 0.000 to 0.561 | 3 |
| citation_hit | 0.727 | 0.518 to 0.868 | 22 |
| pass^3 | 0.600 | 0.407 to 0.766 | 25 |

## Run

- Status counts: ok 72, refused 0, blocked 3, unavailable 0, invalid_output 0
- Label agreement: 22 of 25 cases gave the same label in every trial
- Latency: p50 1470.501 ms, p95 2487.696 ms (n 75)
- Tokens: 78966 prompt and 7667 completion, from the 75 case-trials whose server reported them

## Abstention probes

| Probe | Features | Tenant | Abstained |
|---|---|---|---|
| P-01 | F-32 | tenant-a | 0 of 3 |
| P-02 | F-32 | tenant-b | 0 of 3 |
| P-03 | F-40 | tenant-b | 0 of 3 |

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
| R-Q04 | 2 | tenant-a | retrieval | ok | abstain | A-PWD-V1@1.0/4.4/1 | no |
| R-Q04 | 3 | tenant-a | retrieval | ok | answer | A-PWD-V1@1.0/4.4/1 | no |
| R-Q05 | 1 | tenant-a | retrieval | ok | answer | X-NCSC@1.0/1/1 | no |
| R-Q05 | 2 | tenant-a | retrieval | ok | answer | X-NCSC@1.0/1/1 | no |
| R-Q05 | 3 | tenant-a | retrieval | ok | answer | X-NCSC@1.0/1/1 | no |
| R-Q07 | 1 | tenant-a | retrieval | ok | answer | A-PRIV@1.0/8.1/1, A-REV@1.0/3.2/1 | yes |
| R-Q07 | 2 | tenant-a | retrieval | ok | answer | A-PRIV@1.0/8.1/1, A-REV@1.0/3.2/1 | yes |
| R-Q07 | 3 | tenant-a | retrieval | ok | answer | A-PRIV@1.0/8.1/1, A-REV@1.0/3.2/1 | yes |
| R-Q08 | 1 | tenant-a | retrieval | ok | answer | A-PRIV@1.0/7.2/1, A-PWD-V2@2.0/4.4/1 | yes |
| R-Q08 | 2 | tenant-a | retrieval | ok | answer | A-PWD-V2@2.0/4.4/1, A-PRIV@1.0/7.2/1 | yes |
| R-Q08 | 3 | tenant-a | retrieval | ok | answer | A-PRIV@1.0/7.2/1, A-PWD-V2@2.0/4.4/1 | yes |
| R-Q10 | 1 | tenant-a | retrieval | ok | answer | A-PWD-V2@2.0/2/1, A-PWD-V2@2.0/4.7/1 | no |
| R-Q10 | 2 | tenant-a | retrieval | ok | answer | A-DEVICE-B@1.0/2/1, A-PWD-V2@2.0/2/1, A-PWD-V2@2.0/4.7/1 | no |
| R-Q10 | 3 | tenant-a | retrieval | ok | answer | A-PWD-V2@2.0/2/1, A-IR@1.0/5.4/1 | no |
| R-Q11 | 1 | tenant-a | retrieval | ok | answer | A-LIFE@1.1/3.1/1 | yes |
| R-Q11 | 2 | tenant-a | retrieval | ok | answer | A-LIFE@1.1/3.1/1 | yes |
| R-Q11 | 3 | tenant-a | retrieval | ok | answer | A-LIFE@1.1/3.1/1 | yes |
| R-Q13 | 1 | tenant-a | retrieval | ok | answer | A-LIFE@1.1/5.2/1 | yes |
| R-Q13 | 2 | tenant-a | retrieval | ok | answer | A-LIFE@1.1/5.2/1 | yes |
| R-Q13 | 3 | tenant-a | retrieval | ok | answer | A-LIFE@1.1/5.2/1 | yes |
| R-Q14 | 1 | tenant-a | retrieval | ok | answer | A-LIFE@1.1/3.3/1, A-MFA@1.0/3.3/1, A-FAQ@1.0/Q5/1 | yes |
| R-Q14 | 2 | tenant-a | retrieval | ok | answer | A-LIFE@1.1/3.3/1, A-MFA@1.0/3.3/1 | yes |
| R-Q14 | 3 | tenant-a | retrieval | ok | answer | A-LIFE@1.1/3.3/1, A-MFA@1.0/3.3/1, A-MFA@1.0/5.3/1, A-FAQ@1.0/Q5/1 | yes |
| R-Q16 | 1 | tenant-a | retrieval | ok | answer | A-DEVICE-B@1.0/1/1 | yes |
| R-Q16 | 2 | tenant-a | retrieval | ok | answer | A-DEVICE-B@1.0/1/1 | yes |
| R-Q16 | 3 | tenant-a | retrieval | ok | answer | A-DEVICE-B@1.0/1/1 | yes |
| R-Q18 | 1 | tenant-a | retrieval | ok | answer | A-FAQ@1.0/Q2/1, X-NCSC@1.0/3/1 | no |
| R-Q18 | 2 | tenant-a | retrieval | ok | answer | A-FAQ@1.0/Q2/1, A-PWD-V2@2.0/4.5/1, X-NCSC@1.0/3/1 | no |
| R-Q18 | 3 | tenant-a | retrieval | ok | answer | A-FAQ@1.0/Q2/1, X-NCSC@1.0/3/1 | no |
| R-Q19 | 1 | tenant-a | retrieval | ok | answer | A-PWD-V1@1.0/4.1/1, A-PWD-V2@2.0/4.1/1 | yes |
| R-Q19 | 2 | tenant-a | retrieval | ok | answer | A-PWD-V1@1.0/4.1/1, A-PWD-V2@2.0/4.1/1 | yes |
| R-Q19 | 3 | tenant-a | retrieval | ok | answer | A-PWD-V1@1.0/4.1/1, A-PWD-V2@2.0/4.1/1 | yes |
| R-Q21 | 1 | tenant-a | retrieval | blocked | abstain | - | no |
| R-Q21 | 2 | tenant-a | retrieval | ok | answer | A-FAQ@1.0/Q2/1, A-PWD-V2@2.0/4.4/1, X-NIST@SP_800-63B-4/intro/1, X-NCSC@1.0/3/1 | yes |
| R-Q21 | 3 | tenant-a | retrieval | ok | answer | A-PWD-V2@2.0/4.4/1, X-NIST@SP_800-63B-4/intro/1 | yes |
| R-Q22 | 1 | tenant-a | retrieval | ok | answer | A-PWD-V2@2.0/5/1 | yes |
| R-Q22 | 2 | tenant-a | retrieval | ok | answer | A-PWD-V2@2.0/5/1 | yes |
| R-Q22 | 3 | tenant-a | retrieval | ok | answer | A-PWD-V2@2.0/5/1 | yes |
| R-Q24 | 1 | tenant-a | retrieval | ok | answer | A-EXC@1.0/5.2/1, A-REMOTE@1.1/4.5/1 | yes |
| R-Q24 | 2 | tenant-a | retrieval | ok | answer | A-EXC@1.0/5.2/1, A-EXC@1.0/5.1/1, A-REMOTE@1.1/4.5/1 | yes |
| R-Q24 | 3 | tenant-a | retrieval | ok | answer | A-EXC@1.0/5.2/1, A-REMOTE@1.1/4.5/1, A-EXC@1.0/5.1/1 | yes |
| R-Q25 | 1 | tenant-a | retrieval | blocked | abstain | - | no |
| R-Q25 | 2 | tenant-a | retrieval | blocked | abstain | - | no |
| R-Q25 | 3 | tenant-a | retrieval | ok | answer | A-EXC@1.0/5.1/1, A-FAQ@1.0/Q7/1, A-DEVICE@1.2/3.2/1 | yes |
| R-Q27 | 1 | tenant-b | retrieval | ok | answer | B-PWD@1.0/3.1/1 | yes |
| R-Q27 | 2 | tenant-b | retrieval | ok | answer | B-PWD@1.0/3.1/1 | yes |
| R-Q27 | 3 | tenant-b | retrieval | ok | answer | B-PWD@1.0/3.1/1 | yes |
| R-Q28 | 1 | tenant-b | retrieval | ok | answer | B-MFA@1.0/3.2/1, B-MFA@1.0/3.1/1 | yes |
| R-Q28 | 2 | tenant-b | retrieval | ok | answer | B-MFA@1.0/3.2/1, B-MFA@1.0/3.1/1 | yes |
| R-Q28 | 3 | tenant-b | retrieval | ok | answer | B-MFA@1.0/3.2/1, B-MFA@1.0/3.1/1 | yes |
| R-Q29 | 1 | tenant-b | retrieval | ok | answer | B-MFA@1.0/5.1/1 | yes |
| R-Q29 | 2 | tenant-b | retrieval | ok | answer | B-MFA@1.0/5.1/1 | yes |
| R-Q29 | 3 | tenant-b | retrieval | ok | answer | B-MFA@1.0/5.1/1 | yes |
| R-Q31 | 1 | tenant-a | retrieval | ok | answer | A-REMOTE@1.1/4.5/1, A-EXC@1.0/5.2/1, A-EXC@1.0/5.1/1 | yes |
| R-Q31 | 2 | tenant-a | retrieval | ok | answer | A-REMOTE@1.1/4.5/1, A-EXC@1.0/5.2/1, A-EXC@1.0/5.1/1 | yes |
| R-Q31 | 3 | tenant-a | retrieval | ok | answer | A-REMOTE@1.1/4.5/1, A-EXC@1.0/5.2/1, A-EXC@1.0/5.1/1 | yes |
| R-Q33 | 1 | tenant-a | retrieval | ok | answer | A-PWD-V2@2.0/4.2/1, A-PWD-V1@1.0/4.2/1 | no |
| R-Q33 | 2 | tenant-a | retrieval | ok | answer | A-PWD-V2@2.0/4.2/1 | no |
| R-Q33 | 3 | tenant-a | retrieval | ok | answer | A-PWD-V2@2.0/4.2/1, A-PWD-V2@2.0/6/1 | no |
| P-01 | 1 | tenant-a | probe | ok | answer | A-FAQ@1.0/Q2/1, A-PWD-V2@2.0/4.4/1, X-NCSC@1.0/3/1 | no |
| P-01 | 2 | tenant-a | probe | ok | answer | A-FAQ@1.0/Q2/1, A-PWD-V2@2.0/4.4/1 | no |
| P-01 | 3 | tenant-a | probe | ok | answer | X-NCSC@1.0/1/1 | no |
| P-02 | 1 | tenant-b | probe | ok | answer | B-PWD@1.0/4.1/1 | no |
| P-02 | 2 | tenant-b | probe | ok | answer | X-NCSC@1.0/1/1 | no |
| P-02 | 3 | tenant-b | probe | ok | answer | B-PWD@1.0/4.1/1 | no |
| P-03 | 1 | tenant-b | probe | ok | answer | B-MFA@1.0/6.1/1 | no |
| P-03 | 2 | tenant-b | probe | ok | answer | B-MFA@1.0/6.1/1 | no |
| P-03 | 3 | tenant-b | probe | ok | answer | B-MFA@1.0/6.1/1 | no |
