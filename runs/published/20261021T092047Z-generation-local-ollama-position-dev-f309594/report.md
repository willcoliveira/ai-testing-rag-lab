# Run 20261021T092047Z-generation-local-ollama-position-dev-f309594

Generated from manifest.json and cases.jsonl by raglab; never edited by hand.

| | |
|---|---|
| Suite | generation, split dev, 3 trial(s), seed 20261018, gate manual |
| Provenance | local |
| Created | 2026-10-21T09:20:47Z |
| Git | f3095949e6fb9ff8cf6f0498a17c4806f2169a9e (clean) |
| Config | generation-local-ollama-position (`config/position-local.toml`, sha256 8946d7ece72f) |
| Generator | nemotron-3.5-lightning:30b-a3b-mlx (openai-compat, digest d1e17d7dabac, server 0.40.6) |
| Settings | temperature 1.0, top_p 0.95, max_tokens 1024, timeout_s 120.0, response_format none, reasoning_effort none |
| Prompt | answer-v1 (sha256 96f42d9bc9c7) |
| Guards | tenant, input-limits, citations |
| Embedder | BAAI/bge-small-en-v1.5 at revision aa8f8b060edb |
| Retriever | dense, k = 5 |
| Chunker | 1200 characters, overlap 1 |
| Corpus | 18 documents, 228 chunks, sha256 8918d4f79673 |
| Dataset | `datasets/golden.v1.jsonl`, sha256 5f8cdaf18783 |
| Cases | 30 (90 case-trials) |

## Checks (no judge)

Rates over every trial, with a 95% Wilson interval at n = the number of cases. A citation hit means the answer cites a labelled chunk; it is not correctness (S5 judges that). Nothing here is gated.

pass^3: a case passes only when all 3 trials pass every check that applies; trial t uses seed 20261018 + t - 1 at temperature 1.0, so it measures whether the model passes consistently while it samples at that temperature, not whether it is correct.

| Check | Rate | 95% interval | n (cases) |
|---|---|---|---|
| status_ok | 0.989 | 0.868 to 0.999 | 30 |
| model_citations_retrieved | 0.989 | 0.868 to 0.999 | 30 |
| pass^3 | 0.600 | 0.423 to 0.754 | 30 |
| position[first] | 0.700 | 0.397 to 0.892 | 10 |
| position[middle] | 0.800 | 0.490 to 0.943 | 10 |
| position[last] | 0.733 | 0.427 to 0.910 | 10 |
| position[middle-first] | 0.100 | 0.000 to 0.200 | 10 |
| position[middle-last] | 0.067 | 0.000 to 0.167 | 10 |

## Run

- Status counts: ok 89, refused 0, blocked 1, unavailable 0, invalid_output 0
- Label agreement: 29 of 30 cases gave the same label in every trial
- Latency: p50 1402.959 ms, p95 8431.681 ms (n 90)
- Tokens: 489933 prompt and 9610 completion, from the 90 case-trials whose server reported them

## Position test (how-to 17 step 8, scored by code)

The answering chunk first, in the middle or last of a long context of the asker's tenant's other chunks. A trial passes when its label is answer, it cites the answering chunk and it states the section's values as the answer key writes them. The differences are middle minus first and middle minus last, per case, with a seeded bootstrap over cases. Reported, not gated.

| Case | Fillers | First | Middle | Last |
|---|---|---|---|---|
| G-01 | 43 | 3 of 3 | 3 of 3 | 3 of 3 |
| G-03 | 42 | 2 of 3 | 2 of 3 | 2 of 3 |
| G-05 | 43 | 0 of 3 | 0 of 3 | 0 of 3 |
| G-06 | 48 | 3 of 3 | 3 of 3 | 3 of 3 |
| G-08 | 48 | 3 of 3 | 3 of 3 | 3 of 3 |
| G-09 | 46 | 2 of 3 | 3 of 3 | 3 of 3 |
| G-10 | 38 | 2 of 3 | 3 of 3 | 2 of 3 |
| G-11 | 48 | 3 of 3 | 3 of 3 | 3 of 3 |
| G-12 | 41 | 0 of 3 | 1 of 3 | 0 of 3 |
| G-14 | 17 | 3 of 3 | 3 of 3 | 3 of 3 |

## Case-trials

| Case | Trial | Tenant | Kind | Status | Label | Cited | Passed |
|---|---|---|---|---|---|---|---|
| G-01:first | 1 | tenant-a | position | ok | answer | A-PWD-V2@2.0/4.2/1 | yes |
| G-01:first | 2 | tenant-a | position | ok | answer | A-PWD-V2@2.0/4.2/1 | yes |
| G-01:first | 3 | tenant-a | position | ok | answer | A-PWD-V2@2.0/4.2/1 | yes |
| G-01:middle | 1 | tenant-a | position | ok | answer | A-PWD-V2@2.0/4.1/1, A-PWD-V2@2.0/4.2/1 | yes |
| G-01:middle | 2 | tenant-a | position | ok | answer | A-PWD-V2@2.0/4.2/1 | yes |
| G-01:middle | 3 | tenant-a | position | ok | answer | A-PWD-V2@2.0/4.2/1 | yes |
| G-01:last | 1 | tenant-a | position | ok | answer | A-PWD-V2@2.0/4.2/1 | yes |
| G-01:last | 2 | tenant-a | position | ok | answer | A-PWD-V2@2.0/4.2/1 | yes |
| G-01:last | 3 | tenant-a | position | ok | answer | A-PWD-V2@2.0/4.2/1 | yes |
| G-03:first | 1 | tenant-a | position | ok | answer | A-PWD-V2@2.0/5/1 | yes |
| G-03:first | 2 | tenant-a | position | ok | answer | A-PWD-V2@2.0/5/1 | no |
| G-03:first | 3 | tenant-a | position | ok | answer | A-PWD-V2@2.0/5/1 | yes |
| G-03:middle | 1 | tenant-a | position | ok | answer | A-PWD-V2@2.0/5/1 | yes |
| G-03:middle | 2 | tenant-a | position | ok | answer | A-PWD-V2@2.0/5/1 | yes |
| G-03:middle | 3 | tenant-a | position | ok | answer | A-PWD-V2@2.0/5/1 | no |
| G-03:last | 1 | tenant-a | position | ok | answer | A-PWD-V2@2.0/5/1 | yes |
| G-03:last | 2 | tenant-a | position | ok | answer | A-PWD-V2@2.0/5/1 | no |
| G-03:last | 3 | tenant-a | position | ok | answer | A-PWD-V2@2.0/5/1 | yes |
| G-05:first | 1 | tenant-a | position | ok | answer | A-MFA@1.0/4.1/1, A-PRIV@1.0/6/1, A-GLOSS@1.0/3/1 | no |
| G-05:first | 2 | tenant-a | position | ok | answer | A-MFA@1.0/4.1/1, A-PRIV@1.0/6/1, A-GLOSS@1.0/3/1, A-MFA@1.0/2.1/1, A-MFA@1.0/8/1, A-EXC@1.0/2.1/1, A-PRIV@1.0/9/1, A-FAQ@1.0/Q5/1, A-FAQ@1.0/Q11/1, A-PRIV@1.0/6.3/1 | no |
| G-05:first | 3 | tenant-a | position | ok | answer | A-MFA@1.0/4.1/1, A-PRIV@1.0/6/1, A-GLOSS@1.0/3/1, A-MFA@1.0/8/1 | no |
| G-05:middle | 1 | tenant-a | position | ok | answer | A-MFA@1.0/4.1/1, A-PRIV@1.0/9/1, A-PRIV@1.0/6/1, A-MFA@1.0/8/1, A-FAQ@1.0/Q5/1, A-FAQ@1.0/Q11/1 | no |
| G-05:middle | 2 | tenant-a | position | ok | answer | A-MFA@1.0/4.1/1, A-PRIV@1.0/6/1, A-PRIV@1.0/6.3/1, A-PRIV@1.0/9/1, A-EXC@1.0/2.1/1, A-MFA@1.0/8/1, A-FAQ@1.0/Q5/1, A-MFA@1.0/2.1/1, A-FAQ@1.0/Q11/1, A-PRIV@1.0/2.1/1 | no |
| G-05:middle | 3 | tenant-a | position | ok | answer | A-MFA@1.0/4.1/1, A-MFA@1.0/8/1, A-EXC@1.0/2.1/1, A-FAQ@1.0/Q5/1, A-FAQ@1.0/Q11/1, A-PRIV@1.0/9/1, A-PRIV@1.0/6/1, A-GLOSS@1.0/3/1 | no |
| G-05:last | 1 | tenant-a | position | ok | answer | A-MFA@1.0/4.1/1, A-PRIV@1.0/6/1, A-PRIV@1.0/6.3/1, A-PRIV@1.0/8.1/1 | no |
| G-05:last | 2 | tenant-a | position | ok | answer | A-MFA@1.0/4.1/1, A-PRIV@1.0/6/1, A-PRIV@1.0/9/1 | no |
| G-05:last | 3 | tenant-a | position | ok | answer | A-MFA@1.0/4.1/1, A-PRIV@1.0/9/1, A-PRIV@1.0/6/1, A-EXC@1.0/2.1/1, A-FAQ@1.0/Q5/1, A-MFA@1.0/8/1, A-FAQ@1.0/Q11/1 | no |
| G-06:first | 1 | tenant-a | position | ok | answer | A-MFA@1.0/7.1/1 | yes |
| G-06:first | 2 | tenant-a | position | ok | answer | A-MFA@1.0/7.1/1 | yes |
| G-06:first | 3 | tenant-a | position | ok | answer | A-MFA@1.0/7.1/1 | yes |
| G-06:middle | 1 | tenant-a | position | ok | answer | A-MFA@1.0/7.1/1 | yes |
| G-06:middle | 2 | tenant-a | position | ok | answer | A-MFA@1.0/7.1/1 | yes |
| G-06:middle | 3 | tenant-a | position | ok | answer | A-MFA@1.0/7.1/1 | yes |
| G-06:last | 1 | tenant-a | position | ok | answer | A-MFA@1.0/7.1/1 | yes |
| G-06:last | 2 | tenant-a | position | ok | answer | A-MFA@1.0/7.1/1 | yes |
| G-06:last | 3 | tenant-a | position | ok | answer | A-MFA@1.0/7.1/1 | yes |
| G-08:first | 1 | tenant-a | position | ok | answer | A-DEVICE-B@1.0/1/1 | yes |
| G-08:first | 2 | tenant-a | position | ok | answer | A-DEVICE-B@1.0/1/1 | yes |
| G-08:first | 3 | tenant-a | position | ok | answer | A-DEVICE-B@1.0/1/1 | yes |
| G-08:middle | 1 | tenant-a | position | ok | answer | A-DEVICE-B@1.0/1/1 | yes |
| G-08:middle | 2 | tenant-a | position | ok | answer | A-DEVICE-B@1.0/1/1 | yes |
| G-08:middle | 3 | tenant-a | position | ok | answer | A-DEVICE-B@1.0/1/1 | yes |
| G-08:last | 1 | tenant-a | position | ok | answer | A-DEVICE-B@1.0/1/1 | yes |
| G-08:last | 2 | tenant-a | position | ok | answer | A-DEVICE-B@1.0/1/1 | yes |
| G-08:last | 3 | tenant-a | position | ok | answer | A-DEVICE-B@1.0/1/1 | yes |
| G-09:first | 1 | tenant-a | position | blocked | abstain | - | no |
| G-09:first | 2 | tenant-a | position | ok | answer | A-IR@1.0/3.2/1, A-IR@1.0/3.1/1, A-IR@1.0/A.3/1 | yes |
| G-09:first | 3 | tenant-a | position | ok | answer | A-IR@1.0/3.2/1 | yes |
| G-09:middle | 1 | tenant-a | position | ok | answer | A-IR@1.0/3.2/1, A-IR@1.0/3.3/1, A-FAQ@1.0/Q12/1 | yes |
| G-09:middle | 2 | tenant-a | position | ok | answer | A-IR@1.0/3.2/1, A-IR@1.0/3.3/1, A-IR@1.0/2/1, A-IR@1.0/5.5/1 | yes |
| G-09:middle | 3 | tenant-a | position | ok | answer | A-IR@1.0/3.2/1, A-IR@1.0/3.3/1, A-IR@1.0/5.5/1, A-IR@1.0/5.1/1, A-IR@1.0/2/1 | yes |
| G-09:last | 1 | tenant-a | position | ok | answer | A-IR@1.0/3.2/1, A-FAQ@1.0/Q12/1, A-MFA@1.0/5.2/1, A-DEVICE@1.2/3.4/1, A-PWD-V2@2.0/4.5/1 | yes |
| G-09:last | 2 | tenant-a | position | ok | answer | A-IR@1.0/3.2/1, A-IR@1.0/3.3/1, A-IR@1.0/5.5/1, A-IR@1.0/5.1/1, A-IR@1.0/2/1 | yes |
| G-09:last | 3 | tenant-a | position | ok | answer | A-IR@1.0/3.2/1, A-DEVICE@1.2/3.4/1, A-FAQ@1.0/Q12/1, A-IR@1.0/3.3/1, A-IR@1.0/2/1 | yes |
| G-10:first | 1 | tenant-a | position | ok | answer | A-PRIV@1.0/6.1/1 | no |
| G-10:first | 2 | tenant-a | position | ok | answer | A-PRIV@1.0/6.1/1 | yes |
| G-10:first | 3 | tenant-a | position | ok | answer | A-PRIV@1.0/6.1/1 | yes |
| G-10:middle | 1 | tenant-a | position | ok | answer | A-PRIV@1.0/6.1/1 | yes |
| G-10:middle | 2 | tenant-a | position | ok | answer | A-PRIV@1.0/6.1/1 | yes |
| G-10:middle | 3 | tenant-a | position | ok | answer | A-PRIV@1.0/6.1/1 | yes |
| G-10:last | 1 | tenant-a | position | ok | answer | A-PRIV@1.0/6.1/1 | yes |
| G-10:last | 2 | tenant-a | position | ok | answer | A-PRIV@1.0/6.1/1 | no |
| G-10:last | 3 | tenant-a | position | ok | answer | A-PRIV@1.0/6.1/1 | yes |
| G-11:first | 1 | tenant-a | position | ok | answer | A-EXC@1.0/4.1/1 | yes |
| G-11:first | 2 | tenant-a | position | ok | answer | A-EXC@1.0/4.1/1 | yes |
| G-11:first | 3 | tenant-a | position | ok | answer | A-EXC@1.0/4.1/1 | yes |
| G-11:middle | 1 | tenant-a | position | ok | answer | A-EXC@1.0/4.1/1 | yes |
| G-11:middle | 2 | tenant-a | position | ok | answer | A-EXC@1.0/4.1/1 | yes |
| G-11:middle | 3 | tenant-a | position | ok | answer | A-EXC@1.0/4.1/1 | yes |
| G-11:last | 1 | tenant-a | position | ok | answer | A-EXC@1.0/4.1/1 | yes |
| G-11:last | 2 | tenant-a | position | ok | answer | A-EXC@1.0/4.1/1 | yes |
| G-11:last | 3 | tenant-a | position | ok | answer | A-EXC@1.0/4.1/1 | yes |
| G-12:first | 1 | tenant-a | position | ok | answer | A-PWD-V2@2.0/5/1 | no |
| G-12:first | 2 | tenant-a | position | ok | answer | A-PWD-V2@2.0/5/1 | no |
| G-12:first | 3 | tenant-a | position | ok | answer | A-PWD-V2@2.0/5/1, A-PWD-V1@1.0/2/1, A-PWD-V2@2.0/2/1 | no |
| G-12:middle | 1 | tenant-a | position | ok | answer | A-PWD-V1@1.0/4.4/1, A-PWD-V1@1.0/2/1, A-PWD-V2@2.0/2/1 | no |
| G-12:middle | 2 | tenant-a | position | ok | answer | A-PWD-V1@1.0/4.4/1, A-PWD-V2@2.0/5/1, A-GLOSS@1.0/7/1 | yes |
| G-12:middle | 3 | tenant-a | position | ok | answer | A-PWD-V1@1.0/4.4/1, A-PWD-V2@2.0/5/1 | no |
| G-12:last | 1 | tenant-a | position | ok | answer | A-PWD-V1@1.0/4.4/1 | no |
| G-12:last | 2 | tenant-a | position | ok | answer | A-PWD-V1@1.0/4.4/1, A-PWD-V1@1.0/2/1 | no |
| G-12:last | 3 | tenant-a | position | ok | answer | A-PWD-V1@1.0/4.4/1, A-PWD-V1@1.0/2/1 | no |
| G-14:first | 1 | tenant-b | position | ok | answer | B-MFA@1.0/7.1/1 | yes |
| G-14:first | 2 | tenant-b | position | ok | answer | B-MFA@1.0/7.1/1 | yes |
| G-14:first | 3 | tenant-b | position | ok | answer | B-MFA@1.0/7.1/1 | yes |
| G-14:middle | 1 | tenant-b | position | ok | answer | B-MFA@1.0/7.1/1 | yes |
| G-14:middle | 2 | tenant-b | position | ok | answer | B-MFA@1.0/7.1/1 | yes |
| G-14:middle | 3 | tenant-b | position | ok | answer | B-MFA@1.0/7.1/1 | yes |
| G-14:last | 1 | tenant-b | position | ok | answer | B-MFA@1.0/7.1/1 | yes |
| G-14:last | 2 | tenant-b | position | ok | answer | B-MFA@1.0/7.1/1 | yes |
| G-14:last | 3 | tenant-b | position | ok | answer | B-MFA@1.0/7.1/1 | yes |
