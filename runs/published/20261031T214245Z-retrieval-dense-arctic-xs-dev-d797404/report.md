# Run 20261031T214245Z-retrieval-dense-arctic-xs-dev-d797404

Generated from manifest.json and cases.jsonl by raglab; never edited by hand.

| | |
|---|---|
| Suite | retrieval, split dev, 1 trial(s), gate manual |
| Provenance | local |
| Created | 2026-10-31T21:42:45Z |
| Git | d79740467c63dd84d3e502c0853ef5811523dae7 (clean) |
| Config | retrieval-dense-arctic-xs (`config/retrieval-dense-arctic-xs.toml`, sha256 3eea86a33264) |
| Embedder | snowflake/snowflake-arctic-embed-xs at revision d8c86521100d (fastembed, dimension 384) |
| Retriever | dense, k = 5 |
| Chunker | 1200 characters, overlap 1 |
| Corpus | 18 documents, 228 chunks, sha256 8918d4f79673 |
| Dataset | `datasets/golden.v2.jsonl`, sha256 3d924ad0bd1d, 22 questions in this run |
| Bootstrap | 2000 resamples, seed 20261006, 95% percentile interval |

## Metrics

Labels are sections; a section is found when any of its chunks is in the top 5. A group of sections that state the same rule (any_of) is one thing to find: found, and ranked, by the first chunk of any member.

| Metric | Value | 95% interval | n |
|---|---|---|---|
| hit@5 | 0.682 | 0.499 to 0.864 | 22 |
| mrr@5 | 0.464 | 0.297 to 0.636 | 22 |
| recall@5 | 0.538 | 0.356 to 0.720 | 22 |

## Causes (no judge)

One cause per failed case-trial, the first rule that applies: ingestion (a labelled chunk the run did not search, or a feature split at the chunk settings), retrieval (a labelled section not retrieved), abstention (an abstain case answered or stating a value, or an answerable case abstaining with its labels retrieved), generation (the rest). A case takes the earliest cause in that order among its failed trials. The rule reads the record's fields and the corpus, never the model's reasons: an ambiguous passage and a habit both read as abstention, a chunk's text and the model both read as generation (a triage, not a diagnosis).

| Cause | Case-trials | Cases |
|---|---|---|
| ingestion | 0 | 0 |
| retrieval | 13 | 13 |
| abstention | 0 | 0 |
| generation | 0 | 0 |
| passed | 9 | 9 |
| no_cause | 0 | 0 |

## Questions

Top 5 chunk ids, best first; a labelled section's chunks are marked `*`.

| Case | Split | Tenant | Kind | Hit | RR | Recall | Retrieved |
|---|---|---|---|---|---|---|---|
| R-Q01 | dev | tenant-a | plain-rule | 1 | 0.333 | 1.000 | A-PWD-V1@1.0/4.1/1, A-PWD-V2@2.0/4.1/1, A-PWD-V2@2.0/4.2/1*, A-IR@1.0/A.1/1, A-IR@1.0/5.4/1 |
| R-Q02 | dev | tenant-a | plain-rule | 1 | 0.500 | 1.000 | A-IR@1.0/5.1/1, A-LIFE@1.1/6.1/1*, A-LIFE@1.1/4.1/1, A-LIFE@1.1/5.1/1, A-IR@1.0/5.6/1 |
| R-Q04 | dev | tenant-a | table-only | 0 | 0.000 | 0.000 | A-IR@1.0/5.4/1, X-NCSC@1.0/1/1, A-PWD-V1@1.0/4.5/1, A-FAQ@1.0/Q2/1, A-IR@1.0/5.1/1 |
| R-Q05 | dev | tenant-a | table-only | 0 | 0.000 | 0.000 | A-IR@1.0/5.4/1, X-NCSC@1.0/1/1, A-PWD-V1@1.0/4.5/1, A-IR@1.0/5.2/1, A-FAQ@1.0/Q8/1 |
| R-Q07 | dev | tenant-a | cross-reference | 1 | 1.000 | 0.500 | A-PRIV@1.0/8.1/1*, A-LIFE@1.1/8/1, A-REV@1.0/3.1/1, A-IR@1.0/5.6/1, A-REV@1.0/3.3/1 |
| R-Q08 | dev | tenant-a | cross-reference | 1 | 1.000 | 1.000 | A-PRIV@1.0/7.2/1*, A-IR@1.0/5.6/1, A-PWD-V2@2.0/4.4/1*, A-GLOSS@1.0/13/1, A-REV@1.0/3.3/1 |
| R-Q10 | dev | tenant-a | glossary-dependent | 0 | 0.000 | 0.000 | A-IR@1.0/5.6/1, A-IR@1.0/5.4/1, A-GLOSS@1.0/2/1, A-IR@1.0/5.1/1, A-MFA@1.0/6.2/1 |
| R-Q11 | dev | tenant-a | glossary-dependent | 1 | 0.500 | 0.500 | A-LIFE@1.1/5/1, A-LIFE@1.1/3.1/1*, A-REV@1.0/4.2/1, A-LIFE@1.1/3.2/1, A-LIFE@1.1/4.2/1 |
| R-Q13 | dev | tenant-a | multi-hop | 1 | 0.500 | 0.500 | A-IR@1.0/5.3/1, A-LIFE@1.1/5.2/1*, A-LIFE@1.1/3.3/1, A-REV@1.0/7/1, A-IR@1.0/4.1/1 |
| R-Q14 | dev | tenant-a | multi-hop | 0 | 0.000 | 0.000 | A-EXC@1.0/2/1, A-IR@1.0/5.4/1, A-IR@1.0/5.3/1, A-CLASS@1.1/5/1, A-IR@1.0/A/1 |
| R-Q16 | dev | tenant-a | scanned-page | 0 | 0.000 | 0.000 | A-DEVICE@1.2/7.1/1, A-LIFE@1.1/5/1, A-DEVICE-B@1.0/3/1, A-CLASS@1.1/6/1, A-EXC@1.0/2/1 |
| R-Q18 | dev | tenant-a | version-conflict | 0 | 0.000 | 0.000 | A-IR@1.0/5.4/1, A-PWD-V1@1.0/4.5/1, A-IR@1.0/5.6/1, A-IR@1.0/5.3/1, A-MFA@1.0/6.2/1 |
| R-Q19 | dev | tenant-a | version-conflict | 1 | 1.000 | 1.000 | A-PWD-V2@2.0/4.1/1*, A-IR@1.0/5.4/1, A-PWD-V1@1.0/4.1/1*, A-PWD-V2@2.0/4.2/1, A-CLASS@1.1/3.3/1 |
| R-Q21 | dev | tenant-a | external-conflict | 1 | 0.200 | 0.500 | A-IR@1.0/5.4/1, X-NIST@SP_800-63B-4/intro/1, A-PWD-V1@1.0/4.1/1, A-PWD-V1@1.0/4.5/1, A-FAQ@1.0/Q2/1* |
| R-Q22 | dev | tenant-a | external-conflict | 1 | 0.333 | 0.500 | A-PWD-V2@2.0/6/1, A-PRIV@1.0/6.1/1, A-PWD-V2@2.0/5/1*, X-NIST@SP_800-63B-4/intro/1, X-NCSC@1.0/1/1 |
| R-Q24 | dev | tenant-a | exception-status | 1 | 1.000 | 1.000 | A-EXC@1.0/5.2/1*, A-REMOTE@1.1/4.5/1*, A-EXC@1.0/5.1/1*, A-REMOTE@1.1/4.1/1, A-CLASS@1.1/3.5/1 |
| R-Q25 | dev | tenant-a | exception-status | 1 | 0.333 | 0.333 | A-IR@1.0/5.4/1, A-LIFE@1.1/8/1, A-EXC@1.0/5.1/1*, A-GLOSS@1.0/16/1, A-CLASS@1.1/5/1 |
| R-Q27 | dev | tenant-b | tenant-b | 1 | 1.000 | 1.000 | B-PWD@1.0/3.1/1*, X-NIST@SP_800-63B-4/3.1.1.2/1, B-PWD@1.0/6/1, X-NCSC@1.0/2/1, X-NIST@SP_800-63B-4/intro/1 |
| R-Q28 | dev | tenant-b | tenant-b | 1 | 0.500 | 1.000 | B-MFA@1.0/2/1, B-MFA@1.0/3.2/1*, B-MFA@1.0/7.1/1, B-PWD@1.0/6/1, B-PWD@1.0/3.1/1 |
| R-Q29 | dev | tenant-b | tenant-b | 1 | 1.000 | 1.000 | B-MFA@1.0/5.1/1*, B-PWD@1.0/4.1/1, B-PWD@1.0/6/1, B-MFA@1.0/7.1/1, X-NCSC@1.0/1/1 |
| R-Q31 | dev | tenant-a | paraphrase | 1 | 1.000 | 1.000 | A-REMOTE@1.1/4.5/1*, A-DEVICE-B@1.0/3/1, A-DEVICE-B@1.0/1/1, A-EXC@1.0/5.1/1, A-EXC@1.0/5.2/1 |
| R-Q33 | dev | tenant-a | misspelling | 0 | 0.000 | 0.000 | A-CLASS@1.1/5/1, A-DEVICE@1.2/3/1, A-PWD-V1@1.0/4.1/1, A-PWD-V2@2.0/6/1, A-PWD-V2@2.0/4.1/1 |
