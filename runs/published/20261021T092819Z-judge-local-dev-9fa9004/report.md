# Run 20261021T092819Z-judge-local-dev-9fa9004

Generated from manifest.json and cases.jsonl by raglab; never edited by hand.

| | |
|---|---|
| Suite | judged, split dev, 3 trial(s) of the source, judge seed 20261020, gate manual |
| Provenance | local |
| Created | 2026-10-21T09:28:19Z |
| Git | 9fa90046864ccd602d976380de7e3349cc2580a4 (clean) |
| Config | judge-local (`config/judge-local.toml`, sha256 e827550511a7) |
| Source | 20261021T092047Z-generation-local-ollama-position-dev-f309594 (generation, manifest sha256 0c7b50258c97) |
| Judge | ministral-3:14b-instruct-2512-q4_K_M (openai-compat, digest 4760c35aeb9d, server 0.40.6) |
| Settings | temperature 0.0, max_tokens 512, timeout_s 180.0, response_format json_schema |
| Judge prompt | judge-v2 (sha256 e90d9d8d8bcb) |
| Criteria | `docs/CRITERIA.md`, sha256 8c8f973a3306 |
| Canaries | `datasets/canaries.judge.jsonl`, sha256 4ca54c3ced55 |
| Corpus | 18 documents, 228 chunks, sha256 8918d4f79673 |
| Dataset | `datasets/golden.v1.jsonl`, sha256 5f8cdaf18783 |
| Cases | 30 (90 case-trials) |

## Judged criteria (reported, not gated)

Rates over judged verdicts, with a 95% Wilson interval at n = the number of cases; pass^3 counts the cases whose 3 trials all pass (a withheld trial does not). unable_to_verify is never a pass. Nothing judged is gated before S6 calibrates the judge (docs/CRITERIA.md).

| Metric | Rate | 95% interval | n (cases) |
|---|---|---|---|
| correct | 0.708 | 0.529 to 0.839 | 30 |
| correct[position] | 0.708 | 0.529 to 0.839 | 30 |
| correct_pass^3 | 0.433 | 0.274 to 0.608 | 30 |

| Criterion | Cases | Judged | pass | fail | unable_to_verify | invalid_output | unavailable | Quote found | Quote missing | Passages not shown |
|---|---|---|---|---|---|---|---|---|---|---|
| correct | 30 | 89 | 63 | 26 | 0 | 0 | 0 | 84 | 5 | 0 |

## Checks on the judge (reported)

Repeatability: trial 1 of every behaviour case judged a second time in the same session. Order: grounded asked again on trial 1 of every case with the passages in reverse order.

| Check | Pairs | Agree |
|---|---|---|
| order: grounded reversed | 0 | 0 |

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
| generator | 90 | 489933 | 9610 | 0 |
| judge | 89 | 43091 | 7981 | 0 |
| judge_checks | 0 | 0 | 0 | 0 |
| canaries | 19 | 14224 | 1688 | 0 |

- Judge calls' latency: p50 3465.030 ms, p95 6335.938 ms (n 108); the run took 407.474 s

## Cases

Passes out of judged trials, per criterion.

| Case | Group | Status by trial | grounded | cites_support | correct | relevant | abstains | refuses_and_helps | context_sufficient |
|---|---|---|---|---|---|---|---|---|---|
| G-01:first | position | ok, ok, ok | - | - | 1 of 3 | - | - | - | - |
| G-01:middle | position | ok, ok, ok | - | - | 2 of 3 | - | - | - | - |
| G-01:last | position | ok, ok, ok | - | - | 3 of 3 | - | - | - | - |
| G-03:first | position | ok, ok, ok | - | - | 3 of 3 | - | - | - | - |
| G-03:middle | position | ok, ok, ok | - | - | 1 of 3 | - | - | - | - |
| G-03:last | position | ok, ok, ok | - | - | 3 of 3 | - | - | - | - |
| G-05:first | position | ok, ok, ok | - | - | 1 of 3 | - | - | - | - |
| G-05:middle | position | ok, ok, ok | - | - | 1 of 3 | - | - | - | - |
| G-05:last | position | ok, ok, ok | - | - | 3 of 3 | - | - | - | - |
| G-06:first | position | ok, ok, ok | - | - | 2 of 3 | - | - | - | - |
| G-06:middle | position | ok, ok, ok | - | - | 2 of 3 | - | - | - | - |
| G-06:last | position | ok, ok, ok | - | - | 2 of 3 | - | - | - | - |
| G-08:first | position | ok, ok, ok | - | - | 3 of 3 | - | - | - | - |
| G-08:middle | position | ok, ok, ok | - | - | 3 of 3 | - | - | - | - |
| G-08:last | position | ok, ok, ok | - | - | 2 of 3 | - | - | - | - |
| G-09:first | position | blocked, ok, ok | - | - | 0 of 2 | - | - | - | - |
| G-09:middle | position | ok, ok, ok | - | - | 2 of 3 | - | - | - | - |
| G-09:last | position | ok, ok, ok | - | - | 2 of 3 | - | - | - | - |
| G-10:first | position | ok, ok, ok | - | - | 3 of 3 | - | - | - | - |
| G-10:middle | position | ok, ok, ok | - | - | 3 of 3 | - | - | - | - |
| G-10:last | position | ok, ok, ok | - | - | 3 of 3 | - | - | - | - |
| G-11:first | position | ok, ok, ok | - | - | 2 of 3 | - | - | - | - |
| G-11:middle | position | ok, ok, ok | - | - | 3 of 3 | - | - | - | - |
| G-11:last | position | ok, ok, ok | - | - | 3 of 3 | - | - | - | - |
| G-12:first | position | ok, ok, ok | - | - | 2 of 3 | - | - | - | - |
| G-12:middle | position | ok, ok, ok | - | - | 0 of 3 | - | - | - | - |
| G-12:last | position | ok, ok, ok | - | - | 0 of 3 | - | - | - | - |
| G-14:first | position | ok, ok, ok | - | - | 3 of 3 | - | - | - | - |
| G-14:middle | position | ok, ok, ok | - | - | 3 of 3 | - | - | - | - |
| G-14:last | position | ok, ok, ok | - | - | 2 of 3 | - | - | - | - |
