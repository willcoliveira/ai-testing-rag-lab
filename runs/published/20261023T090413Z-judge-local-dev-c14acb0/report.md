# Run 20261023T090413Z-judge-local-dev-c14acb0

Generated from manifest.json and cases.jsonl by raglab; never edited by hand.

| | |
|---|---|
| Suite | judged, split dev, 3 trial(s) of the source, judge seed 20261020, gate manual |
| Provenance | local |
| Created | 2026-10-23T09:04:13Z |
| Git | c14acb06f500f859131c922cb21ebc0f00352c95 (clean) |
| Config | judge-local (`config/judge-local.toml`, sha256 e827550511a7) |
| Source | 20261023T084147Z-generation-local-ollama-dev-64bfd78 (generation, manifest sha256 2fec397fc6c3) |
| Judge | ministral-3:14b-instruct-2512-q4_K_M (openai-compat, digest 4760c35aeb9d, server 0.40.6) |
| Settings | temperature 0.0, max_tokens 512, timeout_s 180.0, response_format json_schema |
| Judge prompt | judge-v2 (sha256 e90d9d8d8bcb) |
| Criteria | `docs/CRITERIA.md`, sha256 8c8f973a3306 |
| Canaries | `datasets/canaries.judge.jsonl`, sha256 4ca54c3ced55 |
| Corpus | 18 documents, 228 chunks, sha256 8918d4f79673 |
| Dataset | `datasets/golden.v1.jsonl`, sha256 5f8cdaf18783 |
| Cases | 49 (147 case-trials) |

## Judged criteria (reported, not gated)

Rates over judged verdicts, with a 95% Wilson interval at n = the number of cases; pass^3 counts the cases whose 3 trials all pass (a withheld trial does not). unable_to_verify is never a pass. Nothing judged is gated before S6 calibrates the judge (docs/CRITERIA.md).

| Metric | Rate | 95% interval | n (cases) |
|---|---|---|---|
| grounded | 0.850 | 0.725 to 0.924 | 49 |
| grounded[answer] | 0.902 | 0.680 to 0.975 | 17 |
| grounded[flag-conflict] | 0.500 | 0.095 to 0.905 | 2 |
| grounded[refuse-and-help] | 1.000 | 0.342 to 1.000 | 2 |
| grounded[abstain] | 0.833 | 0.436 to 0.970 | 6 |
| grounded[retrieval] | 0.833 | 0.632 to 0.936 | 22 |
| grounded_pass^3 | 0.776 | 0.641 to 0.870 | 49 |
| cites_support | 0.842 | 0.624 to 0.945 | 19 |
| cites_support[answer] | 0.902 | 0.680 to 0.975 | 17 |
| cites_support[flag-conflict] | 0.333 | 0.045 to 0.841 | 2 |
| cites_support_pass^3 | 0.684 | 0.460 to 0.846 | 19 |
| correct | 0.397 | 0.220 to 0.606 | 21 |
| correct[answer] | 0.471 | 0.262 to 0.690 | 17 |
| correct[flag-conflict] | 0.000 | 0.000 to 0.658 | 2 |
| correct[refuse-and-help] | 0.167 | 0.013 to 0.759 | 2 |
| correct_pass^3 | 0.238 | 0.106 to 0.451 | 21 |
| relevant | 0.868 | 0.737 to 0.939 | 43 |
| relevant[answer] | 0.882 | 0.657 to 0.967 | 17 |
| relevant[flag-conflict] | 1.000 | 0.342 to 1.000 | 2 |
| relevant[refuse-and-help] | 0.833 | 0.241 to 0.987 | 2 |
| relevant[retrieval] | 0.848 | 0.649 to 0.944 | 22 |
| relevant_pass^3 | 0.791 | 0.648 to 0.886 | 43 |
| abstains | 0.611 | 0.260 to 0.875 | 6 |
| abstains[abstain] | 0.611 | 0.260 to 0.875 | 6 |
| abstains_pass^3 | 0.500 | 0.188 to 0.812 | 6 |
| refuses_and_helps | 1.000 | 0.342 to 1.000 | 2 |
| refuses_and_helps[refuse-and-help] | 1.000 | 0.342 to 1.000 | 2 |
| refuses_and_helps_pass^3 | 1.000 | 0.342 to 1.000 | 2 |
| context_sufficient | 0.619 | 0.409 to 0.792 | 21 |
| context_sufficient[answer] | 0.765 | 0.527 to 0.904 | 17 |
| context_sufficient[flag-conflict] | 0.000 | 0.000 to 0.658 | 2 |
| context_sufficient[refuse-and-help] | 0.000 | 0.000 to 0.658 | 2 |

| Criterion | Cases | Judged | pass | fail | unable_to_verify | invalid_output | unavailable | Quote found | Quote missing | Passages not shown |
|---|---|---|---|---|---|---|---|---|---|---|
| grounded | 49 | 147 | 125 | 22 | 0 | 0 | 0 | 146 | 1 | 0 |
| cites_support | 19 | 57 | 48 | 9 | 0 | 0 | 0 | 57 | 0 | 0 |
| correct | 21 | 63 | 25 | 38 | 0 | 0 | 0 | 60 | 3 | 0 |
| relevant | 43 | 129 | 112 | 17 | 0 | 0 | 0 | 129 | 0 | 0 |
| abstains | 6 | 18 | 11 | 7 | 0 | 0 | 0 | 18 | 0 | 0 |
| refuses_and_helps | 2 | 6 | 6 | 0 | 0 | 0 | 0 | 6 | 0 | 0 |
| context_sufficient | 21 | 21 | 13 | 8 | 0 | 0 | 0 | 0 | 0 | 0 |

## Checks on the judge (reported)

Repeatability: trial 1 of every behaviour case judged a second time in the same session. Order: grounded asked again on trial 1 of every case with the passages in reverse order.

| Check | Pairs | Agree |
|---|---|---|
| repeat: grounded | 27 | 27 |
| repeat: cites_support | 19 | 19 |
| repeat: correct | 21 | 21 |
| repeat: relevant | 21 | 21 |
| repeat: abstains | 6 | 6 |
| repeat: refuses_and_helps | 2 | 2 |
| order: grounded reversed | 49 | 47 |

## Canaries (a hard stop on the judge)

| Item | Criterion | Side | Verdict | Status | On side |
|---|---|---|---|---|---|
| C-01 | grounded | fail | fail | ok | yes |
| C-02 | abstains | fail | fail | ok | yes |
| C-03 | grounded | pass | pass | ok | yes |
| C-04 | abstains | pass | pass | ok | yes |
| C-05 | grounded | pass | pass | ok | yes |
| C-06 | grounded | fail | fail | ok | yes |
| C-07 | cites_support | pass | pass | ok | yes |
| C-08 | cites_support | fail | fail | ok | yes |
| C-09 | correct | pass | pass | ok | yes |
| C-10 | correct | fail | fail | ok | yes |
| C-11 | relevant | pass | pass | ok | yes |
| C-12 | relevant | fail | fail | ok | yes |
| C-13 | abstains | fail | fail | ok | yes |
| C-14 | refuses_and_helps | pass | pass | ok | yes |
| C-15 | refuses_and_helps | fail | fail | ok | yes |
| C-16 | context_sufficient | pass | pass | ok | yes |
| C-17 | context_sufficient | fail | fail | ok | yes |
| C-18 | grounded | fail | fail | ok | yes |
| C-19 | grounded | fail | fail | ok | yes |

## Tokens and time

Every call's tokens as its server reported them; a call that reported none is unreported, never estimated. The generator's are the source run's.

| Role | Calls | Prompt | Completion | Unreported |
|---|---|---|---|---|
| generator | 147 | 316086 | 13041 | 0 |
| judge | 441 | 315609 | 47538 | 0 |
| judge_checks | 145 | 119817 | 16225 | 0 |
| canaries | 19 | 14224 | 1688 | 0 |

- Judge calls' latency: p50 5277.612 ms, p95 9488.513 ms (n 605); the run took 3257.091 s

## Cases

Passes out of judged trials, per criterion.

| Case | Group | Status by trial | grounded | cites_support | correct | relevant | abstains | refuses_and_helps | context_sufficient |
|---|---|---|---|---|---|---|---|---|---|
| R-Q01 | retrieval | ok, ok, ok | 3 of 3 | - | - | 0 of 3 | - | - | - |
| R-Q02 | retrieval | ok, ok, ok | 3 of 3 | - | - | 3 of 3 | - | - | - |
| R-Q04 | retrieval | ok, ok, ok | 0 of 3 | - | - | 3 of 3 | - | - | - |
| R-Q05 | retrieval | ok, ok, ok | 3 of 3 | - | - | 3 of 3 | - | - | - |
| R-Q07 | retrieval | ok, ok, ok | 3 of 3 | - | - | 3 of 3 | - | - | - |
| R-Q08 | retrieval | ok, ok, ok | 3 of 3 | - | - | 3 of 3 | - | - | - |
| R-Q10 | retrieval | ok, ok, ok | 0 of 3 | - | - | 3 of 3 | - | - | - |
| R-Q11 | retrieval | ok, ok, ok | 3 of 3 | - | - | 3 of 3 | - | - | - |
| R-Q13 | retrieval | ok, ok, ok | 3 of 3 | - | - | 3 of 3 | - | - | - |
| R-Q14 | retrieval | ok, ok, ok | 3 of 3 | - | - | 3 of 3 | - | - | - |
| R-Q16 | retrieval | ok, ok, ok | 3 of 3 | - | - | 1 of 3 | - | - | - |
| R-Q18 | retrieval | ok, ok, ok | 1 of 3 | - | - | 3 of 3 | - | - | - |
| R-Q19 | retrieval | ok, ok, ok | 3 of 3 | - | - | 3 of 3 | - | - | - |
| R-Q21 | retrieval | ok, ok, ok | 2 of 3 | - | - | 2 of 3 | - | - | - |
| R-Q22 | retrieval | ok, ok, ok | 3 of 3 | - | - | 3 of 3 | - | - | - |
| R-Q24 | retrieval | ok, ok, ok | 3 of 3 | - | - | 3 of 3 | - | - | - |
| R-Q25 | retrieval | ok, ok, ok | 2 of 3 | - | - | 3 of 3 | - | - | - |
| R-Q27 | retrieval | ok, ok, ok | 3 of 3 | - | - | 2 of 3 | - | - | - |
| R-Q28 | retrieval | ok, ok, ok | 3 of 3 | - | - | 2 of 3 | - | - | - |
| R-Q29 | retrieval | ok, ok, ok | 3 of 3 | - | - | 1 of 3 | - | - | - |
| R-Q31 | retrieval | ok, ok, ok | 3 of 3 | - | - | 3 of 3 | - | - | - |
| R-Q33 | retrieval | ok, ok, ok | 2 of 3 | - | - | 3 of 3 | - | - | - |
| P-01 | abstain | ok, ok, ok | 3 of 3 | - | - | - | 3 of 3 | - | - |
| P-02 | abstain | ok, ok, ok | 3 of 3 | - | - | - | 3 of 3 | - | - |
| P-03 | abstain | ok, ok, ok | 3 of 3 | - | - | - | 0 of 3 | - | - |
| G-01 | answer | ok, ok, ok | 3 of 3 | 3 of 3 | 0 of 3 | 0 of 3 | - | - | 1 of 1 |
| G-03 | answer | ok, ok, ok | 3 of 3 | 3 of 3 | 1 of 3 | 3 of 3 | - | - | 1 of 1 |
| G-05 | answer | ok, ok, ok | 3 of 3 | 3 of 3 | 2 of 3 | 3 of 3 | - | - | 1 of 1 |
| G-06 | answer | ok, ok, ok | 3 of 3 | 3 of 3 | 2 of 3 | 3 of 3 | - | - | 1 of 1 |
| G-08 | answer | ok, ok, ok | 3 of 3 | 3 of 3 | 3 of 3 | 3 of 3 | - | - | 1 of 1 |
| G-09 | answer | ok, ok, ok | 3 of 3 | 3 of 3 | 1 of 3 | 3 of 3 | - | - | 1 of 1 |
| G-10 | answer | ok, ok, ok | 3 of 3 | 3 of 3 | 3 of 3 | 3 of 3 | - | - | 1 of 1 |
| G-11 | answer | ok, ok, ok | 3 of 3 | 3 of 3 | 2 of 3 | 3 of 3 | - | - | 1 of 1 |
| G-12 | answer | ok, ok, ok | 0 of 3 | 2 of 3 | 1 of 3 | 3 of 3 | - | - | 1 of 1 |
| G-14 | answer | ok, ok, ok | 3 of 3 | 3 of 3 | 3 of 3 | 3 of 3 | - | - | 1 of 1 |
| G-16 | answer | ok, ok, ok | 3 of 3 | 1 of 3 | 3 of 3 | 3 of 3 | - | - | 1 of 1 |
| G-17 | answer | ok, ok, ok | 1 of 3 | 2 of 3 | 0 of 3 | 3 of 3 | - | - | 0 of 1 |
| G-19 | answer | ok, ok, ok | 3 of 3 | 2 of 3 | 0 of 3 | 3 of 3 | - | - | 0 of 1 |
| G-21 | answer | ok, ok, ok | 3 of 3 | 3 of 3 | 0 of 3 | 3 of 3 | - | - | 1 of 1 |
| G-22 | flag-conflict | ok, ok, ok | 3 of 3 | 2 of 3 | 0 of 3 | 3 of 3 | - | - | 0 of 1 |
| G-23 | refuse-and-help | ok, ok, ok | 3 of 3 | - | 0 of 3 | 2 of 3 | - | 3 of 3 | 0 of 1 |
| G-25 | abstain | ok, ok, ok | 2 of 3 | - | - | - | 2 of 3 | - | - |
| G-26 | abstain | ok, ok, ok | 1 of 3 | - | - | - | 3 of 3 | - | - |
| G-28 | abstain | ok, ok, ok | 3 of 3 | - | - | - | 0 of 3 | - | - |
| G-29 | flag-conflict | ok, ok, ok | 0 of 3 | 0 of 3 | 0 of 3 | 3 of 3 | - | - | 0 of 1 |
| G-31 | answer | ok, ok, ok | 3 of 3 | 3 of 3 | 0 of 3 | 0 of 3 | - | - | 0 of 1 |
| G-33 | answer | ok, ok, ok | 3 of 3 | 3 of 3 | 0 of 3 | 3 of 3 | - | - | 1 of 1 |
| G-34 | refuse-and-help | ok, ok, ok | 3 of 3 | - | 1 of 3 | 3 of 3 | - | 3 of 3 | 0 of 1 |
| G-36 | answer | ok, ok, ok | 3 of 3 | 3 of 3 | 3 of 3 | 3 of 3 | - | - | 0 of 1 |
