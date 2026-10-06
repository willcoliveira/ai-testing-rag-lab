# Run 20261006T173026Z-retrieval-dense-600-dev-5f1d3a0

Generated from manifest.json and cases.jsonl by raglab; never edited by hand.

| | |
|---|---|
| Suite | retrieval, split dev, 1 trial(s), gate manual |
| Provenance | local |
| Created | 2026-10-06T17:30:26Z |
| Git | 5f1d3a040d0f64ac5e19733fde54842ec46ba38d (clean) |
| Config | retrieval-dense-600 (`config/retrieval-dense-600.toml`, sha256 d96291d1b36d) |
| Embedder | BAAI/bge-small-en-v1.5 at revision aa8f8b060edb (fastembed, dimension 384) |
| Retriever | dense, k = 5 |
| Chunker | 600 characters, overlap 1 |
| Corpus | 18 documents, 249 chunks, sha256 6b8059386025 |
| Dataset | `datasets/golden.v1.jsonl`, sha256 ffb8c5a54b22, 22 questions in this run |
| Bootstrap | 2000 resamples, seed 20261006, 95% percentile interval |

## Metrics

Labels are sections; a section is found when any of its chunks is in the top 5.

| Metric | Value | 95% interval | n |
|---|---|---|---|
| hit@5 | 0.773 | 0.591 to 0.909 | 22 |
| mrr@5 | 0.590 | 0.406 to 0.767 | 22 |
| recall@5 | 0.621 | 0.447 to 0.788 | 22 |

## Questions

Top 5 chunk ids, best first; a labelled section's chunks are marked `*`.

| Case | Split | Tenant | Kind | Hit | RR | Recall | Retrieved |
|---|---|---|---|---|---|---|---|
| R-Q01 | dev | tenant-a | plain-rule | 1 | 0.200 | 1.000 | A-PWD-V1@1.0/3/2, A-PWD-V2@2.0/4.7/1, A-PWD-V2@2.0/1/2, A-FAQ@1.0/Q8/1, A-PWD-V2@2.0/4.2/1* |
| R-Q02 | dev | tenant-a | plain-rule | 1 | 1.000 | 1.000 | A-LIFE@1.1/6.1/1*, A-LIFE@1.1/4.1/1, A-MFA@1.0/6.1/1, A-PWD-V1@1.0/4.4/1, A-LIFE@1.1/5.1/1 |
| R-Q04 | dev | tenant-a | table-only | 0 | 0.000 | 0.000 | X-NCSC@1.0/3/1, A-FAQ@1.0/Q2/1, X-NCSC@1.0/1/1, A-PWD-V1@1.0/4.4/1, A-IR@1.0/5.4/1 |
| R-Q05 | dev | tenant-a | table-only | 0 | 0.000 | 0.000 | X-NCSC@1.0/1/1, X-NCSC@1.0/3/1, X-NIST@SP_800-63B-4/3.2.2/2, A-FAQ@1.0/Q8/1, A-IR@1.0/5.4/1 |
| R-Q07 | dev | tenant-a | cross-reference | 1 | 0.500 | 1.000 | A-REV@1.0/3.1/1, A-REV@1.0/3.2/1*, A-REV@1.0/3.3/1, A-PRIV@1.0/8.1/1*, A-PRIV@1.0/3.1/1 |
| R-Q08 | dev | tenant-a | cross-reference | 1 | 1.000 | 1.000 | A-PRIV@1.0/7.2/1*, A-PWD-V2@2.0/4.4/1*, A-FAQ@1.0/Q2/1, A-PWD-V1@1.0/4.3/1, X-NCSC@1.0/3/1 |
| R-Q10 | dev | tenant-a | glossary-dependent | 0 | 0.000 | 0.000 | A-DEVICE-B@1.0/2/1, A-PWD-V2@2.0/4.7/1, A-IR@1.0/5.4/1, X-NCSC@1.0/3/2, A-EXC@1.0/2.2/1 |
| R-Q11 | dev | tenant-a | glossary-dependent | 1 | 1.000 | 0.500 | A-LIFE@1.1/3.1/1*, A-LIFE@1.1/3.2/1, A-LIFE@1.1/4.2/1, A-LIFE@1.1/5.2/1, A-LIFE@1.1/5/1 |
| R-Q13 | dev | tenant-a | multi-hop | 1 | 1.000 | 0.500 | A-LIFE@1.1/5.2/1*, A-LIFE@1.1/7.1/1, A-MFA@1.0/7.1/1, A-FAQ@1.0/Q5/1, A-MFA@1.0/5.3/1 |
| R-Q14 | dev | tenant-a | multi-hop | 1 | 1.000 | 0.333 | A-LIFE@1.1/3.3/1*, A-MFA@1.0/3.3/1, A-MFA@1.0/5.3/1, A-FAQ@1.0/Q5/1, A-IR@1.0/6.1/1 |
| R-Q16 | dev | tenant-a | scanned-page | 1 | 1.000 | 1.000 | A-DEVICE-B@1.0/1/1*, A-IR@1.0/7.1/1, A-LIFE@1.1/4.1/1, A-LIFE@1.1/5.2/1, A-LIFE@1.1/5.1/1 |
| R-Q18 | dev | tenant-a | version-conflict | 0 | 0.000 | 0.000 | X-NCSC@1.0/3/1, A-FAQ@1.0/Q2/1, X-NCSC@1.0/intro/1, A-PWD-V2@2.0/4.5/1, X-NIST@SP_800-63B-4/3.1.1.2/2 |
| R-Q19 | dev | tenant-a | version-conflict | 1 | 0.500 | 1.000 | A-FAQ@1.0/Q1/1, A-PWD-V2@2.0/4.1/1*, A-PWD-V2@2.0/4.2/1, A-PWD-V1@1.0/4.1/1*, X-NCSC@1.0/3/1 |
| R-Q21 | dev | tenant-a | external-conflict | 1 | 0.250 | 0.500 | X-NCSC@1.0/3/1, A-FAQ@1.0/Q2/1, X-NIST@SP_800-63B-4/intro/1, A-PWD-V2@2.0/4.4/1*, A-PWD-V1@1.0/4.3/1 |
| R-Q22 | dev | tenant-a | external-conflict | 1 | 0.200 | 0.500 | A-FAQ@1.0/Q8/1, A-MFA@1.0/3.1/2, A-REV@1.0/1/1, A-PWD-V2@2.0/6/1, A-PWD-V2@2.0/5/1* |
| R-Q24 | dev | tenant-a | exception-status | 1 | 1.000 | 1.000 | A-EXC@1.0/5.2/1*, A-REMOTE@1.1/4.5/1*, A-EXC@1.0/5.1/2*, A-REMOTE@1.1/4.4/1, A-REMOTE@1.1/4.1/1 |
| R-Q25 | dev | tenant-a | exception-status | 1 | 1.000 | 0.333 | A-EXC@1.0/5.1/2*, A-DEVICE@1.2/3.2/1, A-REMOTE@1.1/4.6/1, A-FAQ@1.0/Q7/1, A-CLASS@1.1/A.1/1 |
| R-Q27 | dev | tenant-b | tenant-b | 1 | 1.000 | 1.000 | B-PWD@1.0/3.1/1*, X-NIST@SP_800-63B-4/3.1.1.2/1, X-NIST@SP_800-63B-4/intro/1, X-NCSC@1.0/3/1, X-NCSC@1.0/2/1 |
| R-Q28 | dev | tenant-b | tenant-b | 1 | 0.333 | 1.000 | B-MFA@1.0/7.1/1, B-MFA@1.0/2/1, B-MFA@1.0/3.2/1*, B-MFA@1.0/3.1/1, B-MFA@1.0/6.1/1 |
| R-Q29 | dev | tenant-b | tenant-b | 1 | 1.000 | 1.000 | B-MFA@1.0/5.1/1*, B-PWD@1.0/6/1, B-MFA@1.0/3.1/1, B-PWD@1.0/4.1/1, X-NIST@SP_800-63B-4/3.2.2/2 |
| R-Q31 | dev | tenant-a | paraphrase | 1 | 1.000 | 1.000 | A-REMOTE@1.1/4.5/1*, A-EXC@1.0/5.2/1, A-EXC@1.0/5.1/2, A-DEVICE-B@1.0/1/1, A-FAQ@1.0/Q6/1 |
| R-Q33 | dev | tenant-a | misspelling | 0 | 0.000 | 0.000 | A-MFA@1.0/2.1/1, A-PWD-V1@1.0/4.2/1, A-FAQ@1.0/Q3/1, A-PWD-V2@2.0/6/1, A-PWD-V2@2.0/4.2/1 |
