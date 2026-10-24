# Run 20261024T210231Z-judge-local-dev-c8da78b

Generated from manifest.json and cases.jsonl by raglab; never edited by hand.

| | |
|---|---|
| Suite | judged, split dev, 3 trial(s) of the source, judge seed 20261020, gate manual |
| Provenance | local |
| Created | 2026-10-24T21:02:31Z |
| Git | c8da78bb0733a7d0a758cbd090164106e08e2e3e (clean) |
| Config | judge-local (`config/judge-local.toml`, sha256 6d0e2f3c4a84) |
| Source | 20261024T090351Z-generation-local-ollama-dev-ade9397 (generation, manifest sha256 d7dd1ea383a4) |
| Judge | ministral-3:14b-instruct-2512-q4_K_M (openai-compat, digest 4760c35aeb9d, server 0.40.6) |
| Settings | temperature 0.0, max_tokens 512, timeout_s 180.0, response_format json_schema |
| Judge prompt | judge-v2 (sha256 e90d9d8d8bcb) |
| Criteria | `docs/CRITERIA.md`, sha256 8c8f973a3306 |
| Canaries | `datasets/canaries.judge.jsonl`, sha256 4ca54c3ced55 |
| Corpus | 18 documents, 228 chunks, sha256 8918d4f79673 |
| Dataset | `datasets/golden.v2.jsonl`, sha256 3d924ad0bd1d |
| Cases | 101 (303 case-trials) |

## Judged criteria (reported, not gated)

Rates over judged verdicts, with a 95% Wilson interval at n = the number of cases; pass^3 counts the cases whose 3 trials all pass (a withheld trial does not). unable_to_verify is never a pass. Nothing judged is gated before S6 calibrates the judge (docs/CRITERIA.md).

| Metric | Rate | 95% interval | n (cases) |
|---|---|---|---|
| grounded | 0.846 | 0.763 to 0.903 | 101 |
| grounded[answer] | 0.843 | 0.706 to 0.922 | 43 |
| grounded[flag-conflict] | 0.682 | 0.351 to 0.895 | 8 |
| grounded[refuse-and-help] | 0.967 | 0.677 to 0.998 | 10 |
| grounded[abstain] | 0.759 | 0.529 to 0.899 | 18 |
| grounded[retrieval] | 0.923 | 0.740 to 0.981 | 22 |
| grounded_pass^3 | 0.693 | 0.597 to 0.775 | 101 |
| cites_support | 0.859 | 0.738 to 0.929 | 51 |
| cites_support[answer] | 0.874 | 0.743 to 0.943 | 43 |
| cites_support[flag-conflict] | 0.773 | 0.430 to 0.939 | 8 |
| cites_support_pass^3 | 0.686 | 0.550 to 0.797 | 51 |
| correct | 0.447 | 0.329 to 0.571 | 61 |
| correct[answer] | 0.425 | 0.290 to 0.573 | 43 |
| correct[flag-conflict] | 0.500 | 0.215 to 0.785 | 8 |
| correct[refuse-and-help] | 0.500 | 0.237 to 0.763 | 10 |
| correct_pass^3 | 0.262 | 0.168 to 0.384 | 61 |
| relevant | 0.869 | 0.780 to 0.925 | 83 |
| relevant[answer] | 0.866 | 0.734 to 0.938 | 43 |
| relevant[flag-conflict] | 0.955 | 0.618 to 0.996 | 8 |
| relevant[refuse-and-help] | 0.933 | 0.635 to 0.991 | 10 |
| relevant[retrieval] | 0.815 | 0.612 to 0.925 | 22 |
| relevant_pass^3 | 0.699 | 0.593 to 0.787 | 83 |
| abstains | 0.574 | 0.353 to 0.769 | 18 |
| abstains[abstain] | 0.574 | 0.353 to 0.769 | 18 |
| abstains_pass^3 | 0.333 | 0.163 to 0.563 | 18 |
| refuses_and_helps | 0.967 | 0.677 to 0.998 | 10 |
| refuses_and_helps[refuse-and-help] | 0.967 | 0.677 to 0.998 | 10 |
| refuses_and_helps_pass^3 | 0.900 | 0.596 to 0.982 | 10 |
| context_sufficient | 0.557 | 0.433 to 0.675 | 61 |
| context_sufficient[answer] | 0.628 | 0.479 to 0.756 | 43 |
| context_sufficient[flag-conflict] | 0.125 | 0.022 to 0.471 | 8 |
| context_sufficient[refuse-and-help] | 0.600 | 0.313 to 0.832 | 10 |

| Criterion | Cases | Judged | pass | fail | unable_to_verify | invalid_output | unavailable | Quote found | Quote missing | Passages not shown |
|---|---|---|---|---|---|---|---|---|---|---|
| grounded | 101 | 298 | 252 | 46 | 0 | 0 | 0 | 292 | 6 | 2 |
| cites_support | 51 | 149 | 128 | 21 | 0 | 0 | 0 | 139 | 10 | 0 |
| correct | 61 | 179 | 80 | 99 | 0 | 0 | 0 | 165 | 14 | 0 |
| relevant | 83 | 244 | 212 | 32 | 0 | 0 | 0 | 237 | 7 | 1 |
| abstains | 18 | 54 | 31 | 23 | 0 | 0 | 0 | 54 | 0 | 0 |
| refuses_and_helps | 10 | 30 | 29 | 1 | 0 | 0 | 0 | 27 | 3 | 0 |
| context_sufficient | 61 | 61 | 34 | 26 | 1 | 0 | 0 | 0 | 0 | 0 |

## Checks on the judge (reported)

Repeatability: trial 1 of every behaviour case judged a second time in the same session. Order: grounded asked again on trial 1 of every case with the passages in reverse order.

| Check | Pairs | Agree |
|---|---|---|
| repeat: grounded | 76 | 76 |
| repeat: cites_support | 48 | 48 |
| repeat: correct | 58 | 58 |
| repeat: relevant | 58 | 58 |
| repeat: abstains | 18 | 18 |
| repeat: refuses_and_helps | 10 | 10 |
| order: grounded reversed | 98 | 89 |

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
| generator | 303 | 315432 | 34915 | 0 |
| judge | 1015 | 756289 | 125146 | 0 |
| judge_checks | 366 | 303782 | 48028 | 0 |
| canaries | 19 | 14224 | 1688 | 0 |

- Judge calls' latency: p50 5755.260 ms, p95 10721.633 ms (n 1400); the run took 8417.243 s

## Cases

Passes out of judged trials, per criterion.

| Case | Group | Status by trial | grounded | cites_support | correct | relevant | abstains | refuses_and_helps | context_sufficient |
|---|---|---|---|---|---|---|---|---|---|
| R-Q01 | retrieval | ok, ok, ok | 3 of 3 | - | - | 0 of 3 | - | - | - |
| R-Q02 | retrieval | ok, ok, ok | 3 of 3 | - | - | 2 of 3 | - | - | - |
| R-Q04 | retrieval | ok, ok, ok | 1 of 3 | - | - | 3 of 3 | - | - | - |
| R-Q05 | retrieval | ok, ok, ok | 3 of 3 | - | - | 3 of 3 | - | - | - |
| R-Q07 | retrieval | ok, ok, ok | 3 of 3 | - | - | 2 of 3 | - | - | - |
| R-Q08 | retrieval | ok, ok, ok | 3 of 3 | - | - | 3 of 3 | - | - | - |
| R-Q10 | retrieval | ok, ok, ok | 2 of 3 | - | - | 3 of 3 | - | - | - |
| R-Q11 | retrieval | ok, ok, ok | 3 of 3 | - | - | 3 of 3 | - | - | - |
| R-Q13 | retrieval | ok, ok, ok | 3 of 3 | - | - | 3 of 3 | - | - | - |
| R-Q14 | retrieval | ok, ok, ok | 3 of 3 | - | - | 3 of 3 | - | - | - |
| R-Q16 | retrieval | ok, ok, ok | 3 of 3 | - | - | 1 of 3 | - | - | - |
| R-Q18 | retrieval | ok, ok, ok | 2 of 3 | - | - | 3 of 3 | - | - | - |
| R-Q19 | retrieval | ok, ok, ok | 3 of 3 | - | - | 3 of 3 | - | - | - |
| R-Q21 | retrieval | ok, ok, ok | 2 of 3 | - | - | 3 of 3 | - | - | - |
| R-Q22 | retrieval | ok, ok, ok | 3 of 3 | - | - | 3 of 3 | - | - | - |
| R-Q24 | retrieval | ok, ok, ok | 3 of 3 | - | - | 1 of 3 | - | - | - |
| R-Q25 | retrieval | ok, ok, blocked | 2 of 2 | - | - | 2 of 2 | - | - | - |
| R-Q27 | retrieval | ok, ok, ok | 3 of 3 | - | - | 2 of 3 | - | - | - |
| R-Q28 | retrieval | ok, ok, ok | 3 of 3 | - | - | 2 of 3 | - | - | - |
| R-Q29 | retrieval | ok, ok, ok | 3 of 3 | - | - | 2 of 3 | - | - | - |
| R-Q31 | retrieval | ok, ok, ok | 3 of 3 | - | - | 3 of 3 | - | - | - |
| R-Q33 | retrieval | ok, ok, ok | 3 of 3 | - | - | 3 of 3 | - | - | - |
| P-01 | abstain | ok, ok, ok | 2 of 3 | - | - | - | 0 of 3 | - | - |
| P-02 | abstain | ok, ok, ok | 3 of 3 | - | - | - | 1 of 3 | - | - |
| P-03 | abstain | ok, ok, ok | 2 of 3 | - | - | - | 0 of 3 | - | - |
| G-01 | answer | ok, ok, ok | 2 of 3 | 0 of 3 | 2 of 3 | 2 of 3 | - | - | 1 of 1 |
| G-03 | answer | ok, ok, ok | 3 of 3 | 3 of 3 | 3 of 3 | 3 of 3 | - | - | 1 of 1 |
| G-05 | answer | ok, ok, ok | 3 of 3 | 3 of 3 | 0 of 3 | 3 of 3 | - | - | 1 of 1 |
| G-06 | answer | ok, ok, ok | 3 of 3 | 3 of 3 | 1 of 3 | 3 of 3 | - | - | 1 of 1 |
| G-08 | answer | ok, ok, ok | 3 of 3 | 3 of 3 | 3 of 3 | 3 of 3 | - | - | 1 of 1 |
| G-09 | answer | ok, ok, ok | 2 of 3 | 3 of 3 | 0 of 3 | 3 of 3 | - | - | 1 of 1 |
| G-10 | answer | ok, ok, ok | 3 of 3 | 3 of 3 | 3 of 3 | 3 of 3 | - | - | 1 of 1 |
| G-11 | answer | ok, ok, ok | 3 of 3 | 3 of 3 | 3 of 3 | 3 of 3 | - | - | 1 of 1 |
| G-12 | answer | ok, ok, ok | 1 of 3 | 2 of 3 | 0 of 3 | 3 of 3 | - | - | 1 of 1 |
| G-14 | answer | ok, ok, ok | 3 of 3 | 3 of 3 | 3 of 3 | 3 of 3 | - | - | 1 of 1 |
| G-16 | answer | ok, ok, ok | 3 of 3 | 2 of 3 | 3 of 3 | 3 of 3 | - | - | 1 of 1 |
| G-17 | answer | ok, ok, ok | 0 of 3 | 3 of 3 | 0 of 3 | 3 of 3 | - | - | 0 of 1 |
| G-19 | answer | ok, ok, ok | 3 of 3 | 2 of 3 | 0 of 3 | 3 of 3 | - | - | 0 of 1 |
| G-21 | answer | ok, ok, ok | 3 of 3 | 3 of 3 | 1 of 3 | 3 of 3 | - | - | 1 of 1 |
| G-22 | flag-conflict | blocked, ok, blocked | 1 of 1 | 1 of 1 | 0 of 1 | 1 of 1 | - | - | 0 of 1 |
| G-23 | refuse-and-help | ok, ok, ok | 3 of 3 | - | 0 of 3 | 3 of 3 | - | 3 of 3 | 0 of 1 |
| G-25 | abstain | ok, ok, ok | 3 of 3 | - | - | - | 2 of 3 | - | - |
| G-26 | abstain | ok, ok, ok | 1 of 3 | - | - | - | 3 of 3 | - | - |
| G-28 | abstain | ok, ok, ok | 3 of 3 | - | - | - | 0 of 3 | - | - |
| G-29 | flag-conflict | ok, ok, ok | 1 of 3 | 1 of 3 | 0 of 3 | 3 of 3 | - | - | 0 of 1 |
| G-31 | answer | ok, ok, ok | 3 of 3 | 3 of 3 | 0 of 3 | 0 of 3 | - | - | 0 of 1 |
| G-33 | answer | ok, ok, ok | 2 of 3 | 2 of 3 | 1 of 3 | 2 of 3 | - | - | 1 of 1 |
| G-34 | refuse-and-help | ok, ok, ok | 3 of 3 | - | 0 of 3 | 3 of 3 | - | 3 of 3 | 0 of 1 |
| G-36 | answer | ok, ok, ok | 3 of 3 | 3 of 3 | 3 of 3 | 2 of 3 | - | - | 0 of 1 |
| G-40 | answer | ok, ok, ok | 3 of 3 | 3 of 3 | 1 of 3 | 2 of 3 | - | - | 1 of 1 |
| G-41 | answer | ok, ok, ok | 3 of 3 | 3 of 3 | 1 of 3 | 3 of 3 | - | - | 0 of 1 |
| G-42 | answer | ok, ok, ok | 3 of 3 | 3 of 3 | 0 of 3 | 3 of 3 | - | - | 1 of 1 |
| G-43 | answer | ok, ok, ok | 3 of 3 | 3 of 3 | 2 of 3 | 2 of 3 | - | - | 1 of 1 |
| G-47 | refuse-and-help | ok, ok, ok | 2 of 3 | - | 1 of 3 | 2 of 3 | - | 2 of 3 | 1 of 1 |
| G-48 | refuse-and-help | ok, ok, ok | 3 of 3 | - | 3 of 3 | 3 of 3 | - | 3 of 3 | 1 of 1 |
| G-50 | answer | ok, ok, ok | 3 of 3 | 3 of 3 | 1 of 3 | 3 of 3 | - | - | 1 of 1 |
| G-51 | answer | ok, ok, ok | 3 of 3 | 3 of 3 | 2 of 3 | 3 of 3 | - | - | 1 of 1 |
| G-52 | refuse-and-help | ok, ok, ok | 3 of 3 | - | 3 of 3 | 3 of 3 | - | 3 of 3 | 1 of 1 |
| G-53 | answer | ok, ok, ok | 3 of 3 | 2 of 3 | 3 of 3 | 3 of 3 | - | - | 1 of 1 |
| G-54 | answer | ok, ok, ok | 2 of 3 | 3 of 3 | 0 of 3 | 3 of 3 | - | - | 0 of 1 |
| G-55 | answer | ok, ok, ok | 3 of 3 | 3 of 3 | 2 of 3 | 3 of 3 | - | - | 1 of 1 |
| G-56 | answer | ok, ok, ok | 0 of 3 | 1 of 3 | 0 of 3 | 3 of 3 | - | - | 0 of 1 |
| G-58 | answer | blocked, ok, ok | 0 of 2 | 1 of 2 | 0 of 2 | 2 of 2 | - | - | 0 of 1 |
| G-61 | answer | ok, ok, ok | 3 of 3 | 3 of 3 | 3 of 3 | 3 of 3 | - | - | 1 of 1 |
| G-62 | answer | ok, ok, ok | 3 of 3 | 2 of 3 | 1 of 3 | 1 of 3 | - | - | 1 of 1 |
| G-63 | answer | ok, ok, ok | 3 of 3 | 3 of 3 | 2 of 3 | 3 of 3 | - | - | 1 of 1 |
| G-64 | answer | ok, ok, ok | 3 of 3 | 3 of 3 | 1 of 3 | 3 of 3 | - | - | 1 of 1 |
| G-65 | refuse-and-help | ok, ok, ok | 3 of 3 | - | 3 of 3 | 3 of 3 | - | 3 of 3 | 1 of 1 |
| G-67 | refuse-and-help | ok, ok, ok | 3 of 3 | - | 3 of 3 | 3 of 3 | - | 3 of 3 | 1 of 1 |
| G-68 | flag-conflict | ok, ok, ok | 3 of 3 | 2 of 3 | 2 of 3 | 3 of 3 | - | - | 0 of 1 |
| G-71 | answer | ok, ok, ok | 1 of 3 | 3 of 3 | 0 of 3 | 3 of 3 | - | - | 0 of 1 |
| G-73 | answer | ok, ok, ok | 3 of 3 | 3 of 3 | 3 of 3 | 3 of 3 | - | - | 1 of 1 |
| G-74 | answer | ok, ok, ok | 0 of 3 | 1 of 3 | 0 of 3 | 3 of 3 | - | - | 0 of 1 |
| G-75 | answer | ok, ok, ok | 3 of 3 | 3 of 3 | 0 of 3 | 1 of 3 | - | - | 0 of 1 |
| G-76 | answer | ok, ok, ok | 2 of 3 | 1 of 3 | 0 of 3 | 3 of 3 | - | - | 0 of 1 |
| G-78 | answer | ok, ok, ok | 3 of 3 | 3 of 3 | 0 of 3 | 3 of 3 | - | - | 0 of 1 |
| G-79 | refuse-and-help | ok, ok, ok | 3 of 3 | - | 1 of 3 | 3 of 3 | - | 3 of 3 | 0 of 1 |
| G-80 | refuse-and-help | ok, ok, ok | 3 of 3 | - | 1 of 3 | 3 of 3 | - | 3 of 3 | 0 of 1 |
| G-81 | refuse-and-help | ok, ok, ok | 3 of 3 | - | 0 of 3 | 2 of 3 | - | 3 of 3 | 1 of 1 |
| G-82 | answer | ok, ok, ok | 3 of 3 | 3 of 3 | 2 of 3 | 3 of 3 | - | - | 0 of 1 |
| G-84 | abstain | ok, ok, ok | 3 of 3 | - | - | - | 3 of 3 | - | - |
| G-86 | abstain | ok, ok, ok | 3 of 3 | - | - | - | 3 of 3 | - | - |
| G-88 | abstain | ok, ok, ok | 3 of 3 | - | - | - | 3 of 3 | - | - |
| G-89 | abstain | ok, ok, ok | 1 of 3 | - | - | - | 2 of 3 | - | - |
| G-90 | abstain | ok, ok, ok | 3 of 3 | - | - | - | 2 of 3 | - | - |
| G-92 | abstain | ok, ok, ok | 3 of 3 | - | - | - | 3 of 3 | - | - |
| G-94 | abstain | ok, ok, ok | 1 of 3 | - | - | - | 1 of 3 | - | - |
| G-95 | abstain | ok, ok, ok | 3 of 3 | - | - | - | 0 of 3 | - | - |
| G-97 | abstain | ok, ok, ok | 2 of 3 | - | - | - | 1 of 3 | - | - |
| G-98 | abstain | ok, ok, ok | 3 of 3 | - | - | - | 2 of 3 | - | - |
| G-99 | abstain | ok, ok, ok | 2 of 3 | - | - | - | 2 of 3 | - | - |
| G-100 | flag-conflict | ok, ok, ok | 3 of 3 | 3 of 3 | 3 of 3 | 3 of 3 | - | - | 1 of 1 |
| G-101 | flag-conflict | ok, ok, ok | 3 of 3 | 3 of 3 | 1 of 3 | 3 of 3 | - | - | 0 of 1 |
| G-103 | flag-conflict | ok, ok, ok | 1 of 3 | 3 of 3 | 0 of 3 | 2 of 3 | - | - | 0 of 1 |
| G-105 | answer | blocked, ok, ok | 2 of 2 | 2 of 2 | 2 of 2 | 2 of 2 | - | - | 0 of 1 |
| G-106 | answer | ok, ok, ok | 3 of 3 | 3 of 3 | 2 of 3 | 0 of 3 | - | - | 1 of 1 |
| G-108 | answer | ok, ok, ok | 3 of 3 | 3 of 3 | 0 of 3 | 3 of 3 | - | - | 1 of 1 |
| G-109 | flag-conflict | ok, ok, ok | 2 of 3 | 3 of 3 | 3 of 3 | 3 of 3 | - | - | 0 of 1 |
| G-110 | flag-conflict | ok, ok, ok | 1 of 3 | 1 of 3 | 2 of 3 | 3 of 3 | - | - | 0 of 1 |
| G-113 | answer | ok, ok, ok | 3 of 3 | 3 of 3 | 0 of 3 | 1 of 3 | - | - | 0 of 1 |
| G-114 | abstain | ok, ok, ok | 0 of 3 | - | - | - | 3 of 3 | - | - |
