# Run 20261020T130138Z-retrieval-dense-test-2c6aa85

Generated from manifest.json and cases.jsonl by raglab; never edited by hand.

| | |
|---|---|
| Suite | retrieval, split test, 1 trial(s), gate release |
| Provenance | local |
| Created | 2026-10-20T13:01:38Z |
| Git | 2c6aa8590d23e79f21e8c0e1a999402ddf46ca3e (clean) |
| Config | retrieval-dense (`config/retrieval-dense.toml`, sha256 f472ba4dc5fb) |
| Embedder | BAAI/bge-small-en-v1.5 at revision aa8f8b060edb (fastembed, dimension 384) |
| Retriever | dense, k = 5 |
| Chunker | 1200 characters, overlap 1 |
| Corpus | 18 documents, 228 chunks, sha256 8918d4f79673 |
| Dataset | `datasets/golden.v1.jsonl`, sha256 5f8cdaf18783, 12 questions in this run |
| Bootstrap | 2000 resamples, seed 20261006, 95% percentile interval |

## Metrics

Labels are sections; a section is found when any of its chunks is in the top 5. A group of sections that state the same rule (any_of) is one thing to find: found, and ranked, by the first chunk of any member.

| Metric | Value | 95% interval | n |
|---|---|---|---|
| hit@5 | 0.917 | 0.750 to 1.000 | 12 |
| mrr@5 | 0.819 | 0.611 to 1.000 | 12 |
| recall@5 | 0.792 | 0.625 to 0.958 | 12 |

## Questions

Top 5 chunk ids, best first; a labelled section's chunks are marked `*`.

| Case | Split | Tenant | Kind | Hit | RR | Recall | Retrieved |
|---|---|---|---|---|---|---|---|
| R-Q03 | test | tenant-a | plain-rule | 1 | 1.000 | 1.000 | A-MFA@1.0/7.1/1*, A-DEVICE-B@1.0/1/1, A-FAQ@1.0/Q2/1, A-MFA@1.0/6.1/1, A-PWD-V1@1.0/4.3/1 |
| R-Q06 | test | tenant-a | table-only | 0 | 0.000 | 0.000 | A-PWD-V1@1.0/4.4/1, X-NCSC@1.0/1/1, A-PRIV@1.0/6.3/1, A-FAQ@1.0/Q8/1, X-NCSC@1.0/3/1 |
| R-Q09 | test | tenant-a | cross-reference | 1 | 1.000 | 1.000 | A-REMOTE@1.1/4.4/1*, A-LIFE@1.1/5.4/1*, A-EXC@1.0/5.2/1, A-LIFE@1.1/5.1/1, A-FAQ@1.0/Q10/1 |
| R-Q12 | test | tenant-a | glossary-dependent | 1 | 0.500 | 0.500 | A-PRIV@1.0/4.1/1, A-GLOSS@1.0/10/1*, A-IR@1.0/5.6/1, A-PRIV@1.0/1/1, A-LIFE@1.1/5.4/1 |
| R-Q15 | test | tenant-a | multi-hop | 1 | 1.000 | 0.500 | A-MFA@1.0/6.1/1*, A-IR@1.0/5.3/1, A-LIFE@1.1/3.1/1, A-LIFE@1.1/5.2/1, A-LIFE@1.1/4/1 |
| R-Q17 | test | tenant-a | scanned-page | 1 | 0.333 | 1.000 | A-DEVICE-B@1.0/2/1, A-DEVICE@1.2/7/1, A-DEVICE-B@1.0/1/1*, A-DEVICE@1.2/7.1/1, A-FAQ@1.0/Q10/1 |
| R-Q20 | test | tenant-a | version-conflict | 1 | 1.000 | 0.500 | A-PWD-V1@1.0/4.4/1*, X-NCSC@1.0/1/1, X-NCSC@1.0/3/1, A-FAQ@1.0/Q2/1, A-PRIV@1.0/6.3/1 |
| R-Q23 | test | tenant-a | external-conflict | 1 | 1.000 | 1.000 | X-NCSC@1.0/3/1*, X-NCSC@1.0/intro/1, A-FAQ@1.0/Q2/1*, A-PWD-V2@2.0/4.4/1*, A-PWD-V2@2.0/4.6/1 |
| R-Q26 | test | tenant-a | exception-status | 1 | 1.000 | 1.000 | A-EXC@1.0/5.1/1*, A-FAQ@1.0/Q11/1, A-EXC@1.0/3.3/1, A-IR@1.0/A.2/1, A-EXC@1.0/3.1/1 |
| R-Q30 | test | tenant-b | tenant-b | 1 | 1.000 | 1.000 | B-PWD@1.0/4.1/1*, X-NCSC@1.0/1/1, X-NCSC@1.0/3/1, B-PWD@1.0/3.1/1, X-NIST@SP_800-63B-4/3.2.2/1 |
| R-Q32 | test | tenant-a | paraphrase | 1 | 1.000 | 1.000 | A-DEVICE@1.2/3.4/1*, A-FAQ@1.0/Q8/1, A-MFA@1.0/5.1/1, A-LIFE@1.1/5.1/1, A-IR@1.0/3.3/1 |
| R-Q34 | test | tenant-a | misspelling | 1 | 1.000 | 1.000 | A-REV@1.0/3.1/1*, A-LIFE@1.1/8/1, A-REV@1.0/4.1/1, A-PRIV@1.0/8.1/1, A-REV@1.0/2/1 |
