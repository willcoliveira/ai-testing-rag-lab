# Suite audit, v0.2 (S8, how-to 09 part B)

The suite audit at the end of v0.2, as the main plan's "Security and audits" part 3 lists it:
"coverage cells against cases, skips, phrase-locked criteria, calibration record, test-split
contamination, intervals and pairing, thresholds with reasons". One section per item, each a check
**run**, with its command and its output quoted, never read off a document; the not-covered list;
and the lab-versus-production line. `scripts/audit_suite.py` recounts every number of the Counts
table (the last section) from the repository's files, `make audit-suite` compares them with this
report, and `tests/unit/test_audit_suite.py` runs it, so the report cannot drift from the tree.

Written on 2026-10-31 at S8's STOP 1, on `feat/s8-gates-causes-audit` against `main` at `ef46a61`,
offline, from the commands below (their outputs are kept under `runs/tmp/s8-evidence/audit/` on the
developer's machine and quoted here). **Section 4 waits for S6's calibration record**, and section
1's coverage of S7b's findings waits for S7b; both are re-run after those merges and this report is
updated then, with the date of each re-run. The system audit (part A, with its adversarial re-test)
is S11's.

## 1. Coverage cells against cases

**The check.** The traceability table of `docs/TEST-PLAN.md` (section 8) against golden set v2
(`datasets/golden.v2.jsonl`) and the answer key: every Golden case cell names exactly the behaviour
cases whose features carry its requirement (`tests/unit/test_test_plan.py`), the file passes its
version's ten rules (`raglab check-dataset`), and v2's own tests hold (`tests/retrieval/test_golden_v2.py`,
`tests/unit/test_check_dataset.py`).

```
$ uv run pytest -q -p no:warnings tests/unit/test_test_plan.py tests/retrieval/test_golden_v2.py tests/unit/test_check_dataset.py
...............................................................          [100%]
63 passed in 9.73s

$ uv run raglab check-dataset
check-dataset: datasets/golden.v1.jsonl passes as v1.1 (34 retrieval questions, 40 behaviour cases, sha256 5f8cdaf18783)
check-dataset: datasets/golden.v2.jsonl passes as v2 (34 retrieval questions, 120 behaviour cases, sha256 3d924ad0bd1d)
```

**What it found.** 23 requirements, every one traced (the Counts table); four requirements with
no planted feature (R-02, R-20, R-21, R-22), each with its reason in the gaps list. The Gate column
is filled for every row (no `tbd`): `pr-fast` where a pull-request check holds the row,
`eval-on-change (local)` where its cases run in the consistency gate or its criteria are judged,
`not covered` for R-22. **Five Test cells are still `tbd`** at `ef46a61`: R-07 (the rule plus its
exception: an S1b boundary test would fill it, with its judged `correct` beside), R-08 (follow
cross-references: a test that the answer to G-72 or G-73 follows the reference it cites), R-09 (the
pack's definitions: a test that G-38, G-74 and G-75 use the glossary's wording), R-12 (all formats
count: the S1b parsing and OCR tests exist in `tests/ingestion/` and would fill it once named), R-23
(procedures whole and in order: a test on G-20, G-76 and G-112 that every step is present in
order). Each is a gap in the Test column, not in the cases: every one of them has its golden cases
in the consistency gate. **The five uncalibrated judged criteria** (S6's D1, verbatim: "grounded
and abstains, 15 each (Recommended)"): `correct`, `cites_support`, `relevant`, `refuses_and_helps`
and `context_sufficient` stay reported, uncalibrated and never gated until labels of their own
calibrate them; at `ef46a61` no calibration bar is on `main`, so the recount says 7 of 7
uncalibrated, and it says 5 of 7 once S6's `bar.toml` merges. **S7b's confirmed findings as cases**
(AG16): not yet; the pack's Versions table gains a row when they land, and this section is re-run.

## 2. Skips

**The check.** Every skip the suite carries, with its reason and owner, read from where it is
written and run where a command exists.

```
$ make audit
Found 7 known vulnerabilities, ignored 50 in 1 package
Name  Version ID                Fix Versions
----- ------- ----------------- ------------
pypdf 6.19.0  <seven advisory ids, four fixed in 6.21.3 and three in 6.21.4; pip-audit names each by its CVE id, which the privacy check's ticket-shaped pattern refuses to commit, so the ids are in runs/tmp/s8-evidence/audit/make-audit.txt and the pull request #35>
make: *** [audit] Error 1

$ uv run pytest -q -p no:warnings tests/unit/test_audit_exceptions.py tests/unit/test_gates_doc.py tests/unit/test_flake_register.py
.............                                                            [100%]
13 passed in 0.20s
```

- **`make audit`'s skips**: 52 advisory ids in the Makefile's `AUDIT_SKIP` (the recount follows
  the continuation lines), Pillow 12.3.0's and pypdf 6.19.0's, each kind named in the Makefile's
  comment, under one review date, **2026-11-21**, which `tests/unit/test_audit_exceptions.py` fails
  after; owner: the maintainer (the decision of 2026-10-21, verbatim in the Makefile). The audit is
  **red on `main` since 2026-10-30**: seven new pypdf advisories (above) that the dependency pull
  request #35 takes; they are not skipped here.
- **The markers kept out of `make check`**: `live`, `judged`, `guardrails`, `perf` and `flaky`
  (`PYTEST_OFFLINE`); `live` and `judged` need a model server (one session by hand,
  `docs/LOCAL-MODEL.md`), `guardrails` waits for S7b's cached validators, `perf` runs in pr-fast's
  own `perf` job, `flaky` is the quarantine (empty); owner: quality.
- **ZAP's ignored rules**: three, each Informational and each with its reason in
  `deploy/zap/rules.tsv` (10109, 10049, 10031); owner: the maintainer (S3's scan of 2026-10-18).
- **The test split's held-out runs**: two published runs hold the test cases
  (`20261020T130138Z-retrieval-dense-test-2c6aa85`, `20261020T130229Z-generation-local-ollama-release-test-2c6aa85`),
  both v1.1's under gate `release` (v0.1.0); `raglab eval` and `raglab publish` refuse the split
  under any other gate (`tests/unit/test_held_out_split.py`); owner: the maintainer, at a release.

## 3. Phrase-locked criteria

**The check.** The guard suites' assertions are behaviour, never refusal wording (how-to 07): every
`expected` of the security pack is a decision (`pass` or `block`), re-checked on every case; the
record's checks match plain substrings, so fullwidth and homoglyph forms escape them (S7a-J6, in
THREAT-MODEL's not-covered list); CRITERIA.md's pass and fail rules are the judge prompt's words
(`tests/unit/test_criteria.py::test_the_pass_and_fail_rules_are_judge_v2s_words`).

```
$ uv run pytest -q -p no:warnings tests/security/test_security_pack.py tests/unit/test_criteria.py tests/security/test_guard_cases.py
....                                                                     [100%]
148 passed in 2.25s
```

**What it found.** The pack's 127 cases (57 must-block, 57 must-not-block and 13 attack cases, the
S7 ledger's count, held by `test_security_pack.py`) carry a decision each and no refusal text; no
criterion is phrase-locked. The one wording the system is told to say ("the company's documents do
not say", the abstain phrasing) is taken out before the prompt-leak guard counts runs (the S7
ledger), so it never counts as a leak. Limit: the substring checks (S7a-J6) stay as they are, with
no Unicode normalisation before matching.

## 4. Calibration record

**The check.** The calibration record (S6's `datasets/calibration/<name>/record.json`) linked, its
verdict per criterion, the triggers, and whether every judged manifest names it.

```
$ uv run raglab gate --judged 20261023T090413Z-judge-local-dev-c14acb0 --against 20261021T081852Z-judge-local-dev-5aa0ec5
judged gate (eval-on-change): refused: no calibration record under datasets/calibration/ describes the judge of 20261023T090413Z-judge-local-dev-c14acb0 (model ministral-3:14b-instruct-2512-q4_K_M, prompt judge-v2): nothing judged gates until S6's record trusts a criterion
```

**What it found.** **Waits for S6.** At `ef46a61` no calibration record exists on `main` (the
recount: 0 records), so the judged gate refuses, which is the honest state: nothing judged gates. No
published judged manifest names a record (the field `judge.calibration_record` is S8's; S6's v2
baseline predates it and is matched by identity). After S6 merges this section quotes the record's
verdict per criterion (trusted, reported only or not trusted), the triggers, and `raglab gate
--judged` run against it on the v2 judged record and a copy.

## 5. Test-split contamination

**The check.** `tests/unit/test_split_contamination.py` (in `make test`, pr-fast's test step)
lists every test-split id of `golden.v2.jsonl` and finds none in `src/`, `config/`,
`datasets/security/`, the prompts (`src/raglab/generate/prompts`), `docs/THRESHOLDS.md` or a
published dev record; the test-split runs that exist are v1.1's under `release`.

```
$ uv run pytest -p no:warnings tests/unit/test_split_contamination.py -v
tests/unit/test_split_contamination.py::test_no_test_split_id_is_in_the_code_the_configs_the_pack_the_prompts_or_the_thresholds PASSED [ 25%]
tests/unit/test_split_contamination.py::test_no_published_dev_record_holds_a_test_split_case PASSED [ 50%]
tests/unit/test_split_contamination.py::test_the_test_split_runs_that_exist_are_v1_1s_under_release PASSED [ 75%]
tests/unit/test_split_contamination.py::test_a_planted_id_in_a_comment_of_the_injection_guard_is_named PASSED [100%]
============================== 4 passed in 0.12s ===============================
```

**What it found.** 53 test-split ids (12 retrieval questions, 41 behaviour cases); no hit in the
scanned places; 31 published dev runs hold no test case; no test-split run on v2 has been made
(v0.2.0's release makes the first). The ledgers may name test ids in their allowed lines (the split
script's moves, S4b's ledger); the check does not scan `docs/plans/`, by design.

## 6. Intervals and pairing

**The check.** Every published metric carries its interval; every comparison is paired
(`compare` refuses unpaired runs, `tests/retrieval/test_compare.py`); the judged comparison pairs
under one judge (`tests/judge/test_judged_compare.py`).

```
$ uv run pytest -p no:warnings tests/retrieval/test_compare.py tests/judge/test_judged_compare.py -v
tests/retrieval/test_compare.py::test_paired_differences_and_flipped_questions_by_hand PASSED [  7%]
tests/retrieval/test_compare.py::test_the_cli_writes_compare_json_and_md PASSED [ 14%]
tests/retrieval/test_compare.py::test_runs_that_are_not_paired_are_refused PASSED [ 21%]
tests/retrieval/test_compare.py::test_different_case_ids_are_refused PASSED [ 28%]
tests/retrieval/test_compare.py::test_paired_generation_differences_and_flipped_cases_by_hand PASSED [ 35%]
tests/retrieval/test_compare.py::test_unpaired_generation_runs_are_refused PASSED [ 42%]
tests/judge/test_judged_compare.py::test_a_judged_record_against_a_copy_of_itself_is_zero_everywhere PASSED [ 50%]
tests/judge/test_judged_compare.py::test_the_two_published_judged_records_compare_under_one_judge PASSED [ 57%]
tests/judge/test_judged_compare.py::test_a_judged_run_under_another_judge_or_dataset_is_not_paired PASSED [ 64%]
tests/judge/test_judged_compare.py::test_twenty_trusted_verdicts_flipped_fail_the_gate_and_a_reported_only_criterion_does_not PASSED [ 71%]
tests/judge/test_judged_compare.py::test_an_unnamed_criterion_is_refused_from_gating_and_a_bad_record_is_refused PASSED [ 78%]
tests/judge/test_judged_compare.py::test_the_record_is_found_by_the_pin_or_by_identity_and_a_changed_pin_is_refused PASSED [ 85%]
tests/judge/test_judged_compare.py::test_a_new_judged_run_names_the_record_that_describes_its_judge PASSED [ 92%]
tests/judge/test_judged_compare.py::test_the_cli_refuses_without_a_record_and_gates_with_a_given_one PASSED [100%]
============================== 14 passed in 7.12s ==============================
```

**What it found.** 33 published runs carry 56 distinct metric keys, every one with `ci_low` and
`ci_high` (Wilson at n = cases for the rates, a percentile bootstrap for the retrieval metrics);
every comparison pairs by case id and refuses another split, dataset, k, trials or judge. The real
judged comparison answer-v1 against answer-v2 under one judge (`raglab compare 5aa0ec5 c14acb0`,
quoted in the S8 ledger) has every interval crossing zero but `abstains` (+0.250, [+0.000, +0.583]
over 6 cases). **Every number in the docs links its record**: held for THRESHOLDS.md by its rows
(each names its run id) and for the README's status lines by S6's JC10 test once it merges; this
part is re-run then. No `runs/compare/` file is committed at STOP 1 (the embedder swap's two
compares come with the download go).

## 7. Thresholds with reasons

**The check.** GA2's test: every metric key of every published manifest, every rate and latency of
the guard-suites records, and the perf smoke's names have a THRESHOLDS.md row with a non-empty Gate
and Reason, and every Gate cell names a gate of `docs/GATES.md`, a hard stop, a rule enforced in
code, or `reported`.

```
$ uv run pytest -p no:warnings tests/unit/test_thresholds_cover_the_metrics.py -v
tests/unit/test_thresholds_cover_the_metrics.py::test_every_metric_has_a_row_with_a_gate_and_a_reason PASSED [ 25%]
tests/unit/test_thresholds_cover_the_metrics.py::test_every_gate_cell_is_a_gate_a_hard_stop_enforced_in_code_or_reported PASSED [ 50%]
tests/unit/test_thresholds_cover_the_metrics.py::test_a_reason_emptied_a_key_renamed_and_a_row_deleted_are_each_named PASSED [ 75%]
tests/unit/test_thresholds_cover_the_metrics.py::test_base_names PASSED  [100%]
============================== 4 passed in 0.03s ===============================
```

**What it found.** Before S8, 16 metrics had no row under this rule (the consistency row named no
gate word, `decision_label` and its per-label keys, `over_abstention`, `behaviour_pass^3` by its
key, the attack suite's `safe` and `safe^3`, the guard suites' `must_block`, `must_not_block` and
`latency_ms`, the perf smoke's `checks`, `http_req_failed`, `p(90)` and `p(95)`); each has its row
now, and the judged gate, the drift alert, the causes and `other_tenant_claim` have theirs.

## Not covered

What the suite does not cover at v0.2, each with its reason, and what production would do:

- **R-22, flag unresolved conflicts** (D4 A, the maintainer's answer of 2026-10-31: "Not covered,
  recorded"): no planted feature, because every planted conflict has a precedence rule (R-04, R-05,
  R-06) and the answer key stays unambiguous; planting it needs two registered documents that
  disagree with no precedence rule, and a register change makes every v2 baseline stale (three
  retrieval baselines, the consistency baseline and its four repeats: five sessions, about 50
  minutes by S4's rule) and S6's calibration stale by its own trigger ("a new golden set version":
  a judge session of about 2 h 21 min and 30 fresh labels), plus new golden cases to sign off. S12
  is the next natural corpus change. Production would plant it and re-baseline.
- **The five uncalibrated judged criteria** (`correct`, `cites_support`, `relevant`,
  `refuses_and_helps`, `context_sufficient`): reported, never gated, until labels of their own
  calibrate them (S6's D1). Production would calibrate each on its own sample.
- **The gates marked `local`** (eval-on-change, nightly, release, manual in `docs/GATES.md`): run by
  hand on the maintainer's Mac until ADR-002's keys exist; `weekly` and `prod-sample` are documented
  only. Production runs them in CI inside Environments with required reviewers.
- **The five `tbd` Test cells** (R-07, R-08, R-09, R-12, R-23, section 1): their cases run, their
  named tests do not exist yet.
- **S7's not-covered items, carried over** (`docs/THREAT-MODEL.md`, "Not covered"): non-English
  attacks, paraphrase and encodings (the substring checks of the record too, S7a-J6); Llama Prompt
  Guard 2 (no sign-up); garak and Petri; attacks that need a new document; promptfoo's remote-only
  plugins; how-to 07's `verbatim` and `state_invariant` kinds; a socket outside Python's module;
  and, from S8, a fabrication about another tenant stated in words (the `other_tenant_claim`
  check reads numbers and dates only, never gated).
- **The judged cause per failure**: the cause rule reads the record's fields and the corpus; a
  judged cause (a judge call on each failed trial) is not offered, since `context_sufficient` is
  uncalibrated and it would cost a judge session per run. Production would sample failures for a
  human or judged cause.
- **The upgrade record's first entry and the embedder swap's runs**: written after the dependency
  pull request #35 merges and after the download go (GA10, GA11); this report is updated then.

Lab practice: this audit is one report at the end of v0.2 with every section a command run and a
recount script, re-run by the criteria judge; production would run the same checks on a schedule
against its real document store and traffic, and S11's system audit repeats it with an adversarial
re-test before the demo goes public.

## Counts

Every value below is recounted by `scripts/audit_suite.py` from the files (`make audit-suite`);
a value that drifts fails `tests/unit/test_audit_suite.py` naming its section.

| Section | Count | Value |
|---|---|---|
| 1. coverage | requirements | 23 |
| 1. coverage | gap rows | 4 |
| 1. coverage | Test cells tbd | 5 |
| 1. coverage | Test cells tbd, ids | R-07, R-08, R-09, R-12, R-23 |
| 1. coverage | Gate cells tbd | 0 |
| 1. coverage | Gate cells not covered | R-22 |
| 1. coverage | behaviour cases (dev/test) | 79/41 |
| 1. coverage | retrieval questions (dev/test) | 22/12 |
| 1. coverage | judged criteria | 7 |
| 1. coverage | criteria a calibration bar names | 0 |
| 1. coverage | criteria a calibration bar names, ids | none |
| 1. coverage | uncalibrated criteria | 7 |
| 2. skips | audit skips (AUDIT_SKIP) | 52 |
| 2. skips | audit skips review date | 2026-11-21 |
| 2. skips | markers out of make check | live, judged, guardrails, perf, flaky |
| 2. skips | registered markers | 12 |
| 2. skips | ZAP rules ignored | 3 |
| 2. skips | published held-out runs (split test or all) | 2 |
| 2. skips | published held-out runs under release | 2 |
| 4. calibration | calibration records | 0 |
| 4. calibration | calibration records, ids | none |
| 5. contamination | test-split ids of golden.v2.jsonl | 53 |
| 5. contamination | published dev runs | 31 |
| 6. intervals | published runs | 33 |
| 6. intervals | published metric keys | 56 |
| 6. intervals | published metric keys with an interval | 56 |
| 6. intervals | comparison files (runs/compare) | 0 |
| 6. intervals | derived causes files (runs/causes) | 11 |
| flakes | register rows | 0 |
| not covered | entries in the not-covered list | 7 |
