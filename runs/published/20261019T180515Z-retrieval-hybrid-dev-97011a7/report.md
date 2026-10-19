# Run 20261019T180515Z-retrieval-hybrid-dev-97011a7

Generated from manifest.json and cases.jsonl by raglab; never edited by hand.

| | |
|---|---|
| Suite | retrieval, split dev, 1 trial(s), gate manual |
| Provenance | local |
| Created | 2026-10-19T18:05:15Z |
| Git | 97011a7070be8aafa29c49da9e42957cd78c6973 (clean) |
| Config | retrieval-hybrid (`config/retrieval-hybrid.toml`, sha256 f4699f2b9e9a) |
| Embedder | BAAI/bge-small-en-v1.5 at revision aa8f8b060edb (fastembed, dimension 384) |
| Retriever | hybrid, k = 5 (dense and BM25, 50 candidates each, reciprocal rank fusion with k = 60) |
| Chunker | 1200 characters, overlap 1 |
| Corpus | 18 documents, 228 chunks, sha256 8918d4f79673 |
| Dataset | `datasets/golden.v1.jsonl`, sha256 5f8cdaf18783, 22 questions in this run |
| Bootstrap | 2000 resamples, seed 20261006, 95% percentile interval |

## Metrics

Labels are sections; a section is found when any of its chunks is in the top 5. A group of sections that state the same rule (any_of) is one thing to find: found, and ranked, by the first chunk of any member.

| Metric | Value | 95% interval | n |
|---|---|---|---|
| hit@5 | 0.864 | 0.727 to 1.000 | 22 |
| mrr@5 | 0.590 | 0.421 to 0.753 | 22 |
| recall@5 | 0.720 | 0.568 to 0.856 | 22 |

## Questions

Top 5 chunk ids, best first; a labelled section's chunks are marked `*`.

| Case | Split | Tenant | Kind | Hit | RR | Recall | Retrieved |
|---|---|---|---|---|---|---|---|
| R-Q01 | dev | tenant-a | plain-rule | 1 | 1.000 | 1.000 | A-PWD-V2@2.0/4.2/1*, A-MFA@1.0/1/1, A-FAQ@1.0/Q1/1, A-PWD-V1@1.0/4.1/1, A-PWD-V2@2.0/4.1/1 |
| R-Q02 | dev | tenant-a | plain-rule | 0 | 0.000 | 0.000 | A-FAQ@1.0/Q5/1, A-FAQ@1.0/Q4/1, A-LIFE@1.1/4.1/1, A-FAQ@1.0/Q10/1, A-IR@1.0/A.3/1 |
| R-Q04 | dev | tenant-a | table-only | 0 | 0.000 | 0.000 | A-FAQ@1.0/Q2/1, X-NCSC@1.0/3/1, A-FAQ@1.0/Q8/1, A-LIFE@1.1/6.1/1, A-FAQ@1.0/Q1/1 |
| R-Q05 | dev | tenant-a | table-only | 0 | 0.000 | 0.000 | X-NCSC@1.0/1/1, A-FAQ@1.0/Q1/1, A-FAQ@1.0/Q8/1, A-PWD-V2@2.0/4.2/1, X-NIST@SP_800-63B-4/3.2.2/1 |
| R-Q07 | dev | tenant-a | cross-reference | 1 | 0.500 | 1.000 | A-REV@1.0/3.1/1, A-REV@1.0/3.2/1*, A-REV@1.0/3.3/1, A-PRIV@1.0/8.1/1*, A-LIFE@1.1/8/1 |
| R-Q08 | dev | tenant-a | cross-reference | 1 | 1.000 | 1.000 | A-PWD-V2@2.0/4.4/1*, A-PWD-V1@1.0/4.3/1, A-FAQ@1.0/Q2/1, A-PRIV@1.0/7.2/1*, A-PWD-V2@2.0/2/1 |
| R-Q10 | dev | tenant-a | glossary-dependent | 1 | 0.333 | 1.000 | A-PWD-V2@2.0/2/1, A-DEVICE-B@1.0/2/1, A-GLOSS@1.0/10/1*, A-IR@1.0/A.3/1, A-EXC@1.0/2.2/1 |
| R-Q11 | dev | tenant-a | glossary-dependent | 1 | 1.000 | 0.500 | A-LIFE@1.1/3.1/1*, A-LIFE@1.1/3.2/1, A-LIFE@1.1/4.2/1, A-LIFE@1.1/5/1, A-LIFE@1.1/4/1 |
| R-Q13 | dev | tenant-a | multi-hop | 1 | 1.000 | 0.500 | A-LIFE@1.1/5.2/1*, A-LIFE@1.1/3.3/1, A-LIFE@1.1/5.1/1, A-LIFE@1.1/5.4/1, A-GLOSS@1.0/4/1 |
| R-Q14 | dev | tenant-a | multi-hop | 1 | 0.333 | 0.667 | A-FAQ@1.0/Q5/1, A-MFA@1.0/1/1, A-FAQ@1.0/Q3/1*, A-FAQ@1.0/Q4/1, A-LIFE@1.1/3.2/1 |
| R-Q16 | dev | tenant-a | scanned-page | 1 | 0.500 | 1.000 | A-DEVICE@1.2/7/1, A-DEVICE-B@1.0/1/1*, A-DEVICE@1.2/7.1/1, A-DEVICE-B@1.0/intro/1, A-REMOTE@1.1/3/1 |
| R-Q18 | dev | tenant-a | version-conflict | 1 | 0.333 | 0.500 | X-NCSC@1.0/3/1, A-PWD-V2@2.0/4.5/1, A-FAQ@1.0/Q2/1*, A-MFA@1.0/1/1, A-FAQ@1.0/Q8/1 |
| R-Q19 | dev | tenant-a | version-conflict | 1 | 0.333 | 0.500 | X-NIST@SP_800-63B-4/3.1.1.2/1, A-FAQ@1.0/Q2/1, A-PWD-V2@2.0/4.1/1*, A-FAQ@1.0/Q8/1, X-NCSC@1.0/3/1 |
| R-Q21 | dev | tenant-a | external-conflict | 1 | 0.200 | 0.500 | X-NCSC@1.0/3/1, X-NIST@SP_800-63B-4/intro/1, A-PWD-V1@1.0/4.3/1, A-PWD-V2@2.0/6/1, A-PWD-V2@2.0/4.4/1* |
| R-Q22 | dev | tenant-a | external-conflict | 1 | 1.000 | 1.000 | X-NIST@SP_800-63B-4/3.2.2/1*, X-NCSC@1.0/1/1, A-PWD-V2@2.0/5/1*, A-REV@1.0/1/1, A-PWD-V2@2.0/6/1 |
| R-Q24 | dev | tenant-a | exception-status | 1 | 1.000 | 1.000 | A-EXC@1.0/5.2/1*, A-EXC@1.0/5.1/1*, A-REMOTE@1.1/4.5/1*, A-REMOTE@1.1/4.4/1, A-REMOTE@1.1/4.3/1 |
| R-Q25 | dev | tenant-a | exception-status | 1 | 1.000 | 0.667 | A-EXC@1.0/5.1/1*, A-FAQ@1.0/Q7/1*, A-CLASS@1.1/A.3/1, A-CLASS@1.1/A.1/1, A-DEVICE@1.2/3.2/1 |
| R-Q27 | dev | tenant-b | tenant-b | 1 | 1.000 | 1.000 | B-PWD@1.0/3.1/1*, X-NIST@SP_800-63B-4/3.1.1.2/1, X-NCSC@1.0/3/1, B-PWD@1.0/3.2/1, B-PWD@1.0/5/1 |
| R-Q28 | dev | tenant-b | tenant-b | 1 | 1.000 | 1.000 | B-MFA@1.0/3.2/1*, B-MFA@1.0/7.1/1, B-MFA@1.0/2/1, B-PWD@1.0/1/1, B-MFA@1.0/3.1/1 |
| R-Q29 | dev | tenant-b | tenant-b | 1 | 1.000 | 1.000 | B-MFA@1.0/5.1/1*, B-MFA@1.0/3.1/1, B-PWD@1.0/6/1, X-NIST@SP_800-63B-4/3.2.2/1, X-NCSC@1.0/3/1 |
| R-Q31 | dev | tenant-a | paraphrase | 1 | 0.200 | 1.000 | A-DEVICE-B@1.0/1/1, A-FAQ@1.0/Q6/1, A-REMOTE@1.1/4.4/1, A-EXC@1.0/5.1/1, A-REMOTE@1.1/4.5/1* |
| R-Q33 | dev | tenant-a | misspelling | 1 | 0.250 | 1.000 | A-MFA@1.0/3.1/1, A-MFA@1.0/1/1, A-PWD-V1@1.0/4.2/1, A-FAQ@1.0/Q1/1*, A-PWD-V1@1.0/3/1 |
