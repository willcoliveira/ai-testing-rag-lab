---
stage: S6
nodes: [S6]
---

# S6 ledger: judge calibration on 30 blind labels

Plan: [2026-10-23-s6-judge-calibration.md](2026-10-23-s6-judge-calibration.md). Branch
`feat/s6-judge-calibration`, cut from `main` at `2b9ba60` (answer-v2's merge); the plan's commit
is `88202a5`.

This ledger covers **phase 1, the offline build** (the plan's "How it will run", step 2): everything
the plan allows before S4b merges. The judged baseline on golden set v2 (JC3), the cap (JC2's
config change), the sample (JC4's committed file), the labels (JC5 to JC8) and the numbers (JC10 to
JC12's) wait for S4b's merge, the dry run and the judge session, each named below.

## Approval and decisions

The go for the plan's draft (2026-10-23, about 22:45 WEST) is quoted in the plan's Approval.

**The approval (2026-10-23, about 23:30 WEST).** The question, verbatim: "S6, judge calibration.
Approve with all five recommended answers? D1: calibrate grounded and abstains, 15 labels each. D2:
kappa 0.80 or more trusts a criterion, under 0.60 stops it. D3: you label alone, plus a blind
re-label of 12 at least a day later. D4: a miss is recorded and fixed in a follow-up PR. D5: approve
and start. Your time is about 3 h 20 min to 5 h 20 min, and the Mac needs one judge session of
about 2 h 15 min after S4b merges."

The answer, verbatim: "All five as recommended (Recommended)". It selects each decision's
recommended option:

| Decision | The option it selects | What is done |
|---|---|---|
| D1 Which criteria the 30 labels calibrate | "grounded and abstains, 15 each (Recommended)" | `bar.toml` allocates 7 judge passes and 8 judge fails to each of `grounded` and `abstains`; the other five criteria stay reported, uncalibrated and never gated |
| D2 The bar | "kappa 0.80 trusts, under 0.60 stops (Recommended)" | `bar.toml` and THRESHOLDS.md: per criterion, kappa 0.80 or more trusted, 0.60 to under 0.80 reported only, under 0.60 not trusted |
| D3 The second labeller | "One labeller, plus a blind re-label of 12 (Recommended)" | `raglab label --relabel`: 6 per criterion, seeded, in a new order, at least 24 hours after the seal; the record carries the single-labeller caveat |
| D4 If a criterion misses the bar | "Record it; fix in a follow-up (Recommended)" | a miss is recorded with its classified causes and the follow-up in the record's "next" line; nothing is signed off or judged again in S6 |
| D5 This plan | "Approve and start (Recommended)" | the offline build started on `feat/s6-judge-calibration` at `88202a5`; the first live step waits for S4b's merge |

## Blindness, from the moment the v2 record exists

Once the judged baseline on v2 exists, this ledger, the pull request's drafts and every message to
the maintainer give its aggregate numbers only: no item-level verdict (a case, trial and criterion
with its verdict, quote or reason) is quoted until the labels are sealed (the plan, "Blindness
starts here").

## The state of `main` at the start

`make audit` is red on `main`, before any S6 change: advisories published on 2026-10-23 hit
Pillow, pypdf and filelock. The orchestrator fixes it in a pull request of its own; S6 never
touches the Makefile's `AUDIT_SKIP`. Until that merges, "green" here means `make -k check` with
only `audit` red. From `make audit` on this branch at `88202a5` (2026-10-23, 23:48 WEST): the first
audit line (the main environment) stopped with "Found 6 known vulnerabilities, ignored 43 in 3
packages" and "make: *** [audit] Error 1", and its table named six advisories:

| Package | Version | Advisories | Fix version |
|---|---|---|---|
| filelock | 4.0.12 | 1 | 4.2.1 |
| pillow | 12.3.0 | 2 | 13.0.0 |
| pypdf | 6.19.0 | 3 | 6.21.2 |

The advisory ids are left out here: the repository's privacy check reads a CVE id (the letters,
the year and a number, joined by hyphens) as a ticket id, and the pre-commit hook refused the commit
that quoted them (six hits of the generic ticket rule); the S5 ledger counted its advisories in
words too.

## What was built (developer, offline, 2026-10-23 and 2026-10-24)

| Part | Where | Commit |
|---|---|---|
| The bar and the labelling guide (JC1), in a commit of their own, before any sampler code | `datasets/calibration/judge-v2-c1/bar.toml`; `datasets/calibration/README.md`; docs/THRESHOLDS.md, "The judge's calibration bar (S6)"; `tests/judge/test_calibration_bar.py` | `d7c9b76` |
| The one-judge test, the cap excepted (JC2's test; the cap itself waits for the dry run) | `tests/judge/test_answer_v2_one_judge.py`: today's config with only `judging.run_timeout_s` set back to the record's 7200.0 hashes to each record's canonical sha256; the file sha256 compared only for a record made under today's cap; `RECORDS` names each record and its cap, so the v2 baseline joins with today's | `e9173b0` |
| The judged run's inputs, shared | `raglab.evals.judged.inputs`: the judged run's preamble (the source checked, the corpus and dataset sha256, the passages and references rebuilt) moved into a function that the judged run and the label CLI both call; the judged run is otherwise unchanged (tests/judge: 93 passed after the move, as before) | `41885f4` |
| The draw, rule s6-1 (JC4) | `raglab.evals.calibration`: `frame`, `draw`, `draw_sample`, `read_sample`, `redraw_problems`, `earlier`, `excluded_by`; `raglab calibrate sample --judged <run>` and `raglab calibrate check` | `41885f4` |
| The blind label CLI (JC5; D3's re-label, JC7) | `raglab.evals.label`; `raglab label --folder <f>` with `--redo`, `--seal`, `--relabel`; `make label`, `make relabel` (`REDO=<n>`, `SEAL=1`) | `41885f4` |
| The agreement, the refusals and the record (JC6 to JC8) | `raglab.evals.calibration`: `kappa`, `rates`, `strata_weights`, `resamples`, `agreement`, `read_inputs`, `disagreement_rows`, `disagreement_details`, `build_record`, `render_record`, `write_record`, `record_problems`; `raglab calibrate disagreements` and `raglab calibrate record`; `make calibrate` | `41885f4`, `dace8c4` |
| Labels never judge examples, never reused (JC9) | `calibration.leak_problems`, `labelled_texts`, `prompt_text`, `LEAK_RUN = 8`; the path and exclusion tests | `4a4e3ee` |
| Docs that need no number (JC10, JC12) | THRESHOLDS.md, "The calibration's verdicts (S6)": each calibrated criterion "waiting for the labels", the triggers, AV2-J3's limit, held to the record by `tests/judge/test_calibration_thresholds.py`; TEST-PLAN R5's gate cell and its test; ONBOARDING's `make label` and `make calibrate` rows; ARCHITECTURE and README: S6 `wip`; a CHANGELOG line | `4f07000` |
| Tests | `tests/calibration_support.py` (a published judged record of the behaviour run, made by a scripted local judge through the stub server, whose reasons and quotes are marked so a test can tell if one reaches the label CLI's screen; a recording judge); `tests/judge/test_calibration_sample.py`, `test_label_cli.py`, `test_calibration_agreement.py`, `test_calibration_leak.py`, `test_calibration_thresholds.py`, `test_calibration_bar.py` | `41885f4` to `4f07000` |

The file and target names follow the plan's suggestions, with these additions: `labels.seal.json`
and `relabels.seal.json` (the seals), the `check` and `disagreements` actions of `raglab
calibrate`, and `tests/calibration_support.py`. The commits after `41885f4` that change only tests
(`0439e9c`, `9704d3e`, `2c9ffe8`, `f08152e`) are tests that a break found too weak, strengthened
(below).

## Evidence per criterion (developer, offline, macOS arm64)

Each break was made on a committed file with `PYTHONDONTWRITEBYTECODE=1`, run, and restored with
`git checkout -- <file>`; the test was green again after the restore and `git status --short` was
empty. The code breaks are text patches kept in a scratch script outside the repository. The
plan's breaks on the committed sample, labels and record need those files, which exist only after
S4b's merge and the labels; until then the same breaks are made on a fixture's files inside the
tests named below.

| JC | Status at stop 1 | Evidence | Break (restored from git) |
|---|---|---|---|
| JC1 | built; the commit order is the criteria judge's check once the sample and labels are committed | `bar.toml` and the guide in `d7c9b76`, before any sampler code (`41885f4`) and before any sample. `test_calibration_bar.py` (2 tests): THRESHOLDS.md's rows equal bar.toml's, in its order, and say what the bar reads; bar.toml is D1's and D2's answers. `test_calibrate_refuses_a_bar_that_changed_since_the_sample` (the plan's calibrate break, on a fixture: "the bar (...bar.toml) changed since the sample pinned it") | (1) THRESHOLDS.md's grounded line alone, `kappa >= 0.80` to `0.70`: "1 failed, 1 passed", restored "2 passed". (2) bar.toml's grounded `trusted = 0.80` to `0.70`: "2 failed", restored "2 passed" |
| JC2 | the test built; the cap waits for the dry run after S4b's merge | `git diff --stat 2b9ba60 -- config/judge-local.toml src/raglab/judge docs/CRITERIA.md datasets/canaries.judge.jsonl pyproject.toml uv.lock`: empty (and against `origin/main`, also `2b9ba60` here). `shasum -a 256`: `config/judge-local.toml` `228a720045d85bfc0fc5fa78d4da3e5f6105f5d9a47d6840bbb7b11ccc855a5f` (the records' `file_sha256`), docs/CRITERIA.md `8c8f973a3306392fa1e2049ca41bcdb23d7a96d17f804af8ac84a0ca3edd9e0e`, the canary set `4ca54c3ced557118f26306543164dc01c7509d1866e9e77f6cd4f2d3284b328f`. `test_answer_v2_one_judge.py` (3 tests). The canonical sha256 of today's config with the cap restored: 7200.0 gives `e827550511a7`, the records' value; 7200 (an int) gives `87b748704fad`; 12600.0 gives `6d0e2f3c4a84` | (1) `temperature = 0.1`: "2 failed, 1 passed" (both records), restored. (2) `seed = 20261021`: "2 failed, 1 passed", restored. (3) the cap alone, `run_timeout_s = 12600`: "3 passed" (expected pass), restored. (4) the restored cap written as an int, `7200`: both records fail ("today's judge config differs from the record's in more than its cap"), restored "3 passed" |
| JC3 | waiting for S4b's merge (live) | - | - |
| JC4 | built; the committed sample waits for the judged baseline on v2 | `test_calibration_sample.py` (13 tests and 1 skipped: the committed-sample re-draw has no sample yet). Rule s6-1 on the v1.1 record `5aa0ec5`, a fixture never sampled for labels: 15 items per criterion; frame grounded 125 judge passes and 19 fails, abstains 6 and 11; drawn 7 and 8 for grounded, 5 and 10 for abstains, with the shortfall said (`abstains`, judge pass, 5 of 7, 2 more from the other stratum: 6 verdicts of 3 cases, one answer already taken by grounded); every answer once; the same draw twice. On `c14acb0` (a scratch run, not a test): frame abstains 11 and 7, drawn 9 and 6, the judge-fail stratum short by 2. The sample file's pins and item fields; the order (grouped by criterion, each criterion's seeded shuffle); the re-draw; drawn once; only a published judged record | (1) the stratum shuffle removed from `draw`: at first "12 passed, 1 skipped", no test failed, so `test_each_stratum_is_taken_in_its_own_seeded_shuffle` was added (`0439e9c`): then "1 failed, 12 passed, 1 skipped", restored. (2) `read_sample` accepting extra item fields: "1 failed" (`test_a_sample_with_a_verdict_field_is_refused`), restored. (3) the one-per-case rule removed: at first the one-per-case test passed by the order's luck, so it was rebuilt on an order that puts four of one case's trials first (`9704d3e`): then "3 failed, 10 passed, 1 skipped"; the field test's verdict check then read the pins' aggregate shortfall too, so it was narrowed to the item lines (`2c9ffe8`). The plan's three breaks on the sample file (one item swapped by hand, a `verdict` field added, one criterion's items in verdict order) are the fixture tests `test_one_item_swapped_by_hand_fails_the_redraw_naming_it` ("item 1 is ..."), `test_a_sample_with_a_verdict_field_is_refused` and `test_items_written_in_verdict_order_fail_the_order_and_redraw_tests`; on the committed sample after it exists |
| JC5 | built; the labels wait for the sample | `test_label_cli.py` (11 tests): each item is a JudgeItem the judged run built (a recording judge); the screen shows the criterion's rules and every input the judge saw, and none of the judge's marked reasons or quotes, said or printed; the screen is the same with the judged record's `cases.jsonl` removed; a label in the judge's schema; a quote not in the answer is asked again and refused in a file; passage ids outside those shown are asked again and refused; resume, redo, seal, and every change refused after the seal; the re-label opens 24 hours after the seal and shows neither the first labels nor the judge's; the CLI refuses a folder without a sample | (1) the CLI made to print the judge's reason (reading the judged record's lines): at first only the removal test failed, because the blindness test read what the session said and not what was printed; it now reads both (`f08152e`): "2 failed, 9 passed", restored. (2) passage ids outside those shown accepted by the CLI and the schema check: "1 failed, 10 passed", restored. (3) the seal's sha256 check removed: "1 failed, 10 passed", restored; the plan's "one label edited after the seal" is the data break inside `test_it_resumes_redoes_and_seals_and_refuses_any_change_after_the_seal` (label and calibrate refuse: "changed after its seal") |
| JC6 | built; the numbers wait for the labels | `test_calibration_agreement.py` (26 tests and 1 skipped: no committed record yet): kappa on the plan's whole table by hand, as exact fractions (1; 32/37 = 0.865 and 98/113 = 0.867 trusted; 8/11 = 0.727 and 14/19 = 0.737 reported only; 64/109 = 0.587 and 22/37 = 0.595 not trusted, 68/113 = 0.602 and 14/23 = 0.609 reported only; 4/9 = 0.444 and 14/29 = 0.483 not trusted), each with its status by the committed bar; TPR and TNR weighted and unweighted by hand (the plan's illustration: weights 40 and 5, weighted TNR 1/2, unweighted 8/9); the bootstrap keeps each stratum's count in every resample, seeded; an undefined resample counted; on a fixture record, grounded's table 2, 1, 0, 3 by hand (kappa 2/3, reported only; TNR weighted 9/13, unweighted 3/4; weight 8/3); the refusals (a judged verdict flipped with its reply and resealed: `record.validate` passes, calibrate refuses on the manifest's sha256; labels off their seal; a label's answer sha256 off the shown answer); `raglab calibrate` on a fixture: sample prints aggregate counts only | (1) TPR and TNR swapped in `rates`: "3 failed, 22 passed, 1 skipped", restored. (2) the weights left out (`strata_weights` gives 1): "2 failed", restored. (3) the judged manifest's pin ignored: "1 failed" (the flipped-and-resealed verdict is no longer refused), restored |
| JC7 | built; the re-label waits for the labels and a day | the re-label CLI and its seal; `calibrate` refuses a re-label inside its 24 hours; the record's labellers line carries the single-labeller caveat (`calibration.CAVEAT`) and the re-label's raw and kappa with the hours between the seals (27.0 in the fixture) | (1) the caveat taken out of the record's labellers line: "1 failed", restored. (2) the re-label made to show the first labels' reasons: "1 failed, 10 passed", restored |
| JC8 | built; the disagreements wait for the labels | `disagreements.jsonl` read and checked (every disagreement classed, one of the four classes, the maintainer's answer); a human error reported as a correction beside the sealed label; record.json and record.md in how-to 05's template (judge, sample, labellers, agreement, threshold, disagreements, verdict, next); the regenerate test | (1) a corrected label fed to the bar: "1 failed" (`test_the_bar_reads_the_sealed_labels_and_a_correction_is_reported_beside`), restored. (2) the regenerate check skipping record.md: "1 failed", restored. The plan's data breaks (record.md edited by hand; a disagreement without a class) are inside the tests |
| JC9 | built; the leak test on the committed labels waits for them | `test_calibration_leak.py` (6 tests and 1 skipped): the longest shared run by hand; every prompt version read whole; a labelled sentence pasted into judge-v2's text found, naming the item; nothing under `src/raglab/judge/` (nor `config/judge-local.toml`) names the calibration folder, a label file or the calibration modules; a later calibration excludes every item of an earlier one and pins its sample's sha256. Measured (2026-10-24, scratch script over every published generation run's answers, 1,710): the longest run any answer shares with judge-v1 or judge-v2 is 6 words (89 answers), with a tokenizer that keeps "company's" one word (7 with one that splits it); `LEAK_RUN` is 8 | (1) the leak limit made four times looser: "1 failed", restored. (2) a judge module naming the folder (`EXAMPLES = "datasets/calibration/judge-v2-c1/labels.jsonl"` in `llm.py`): "1 failed", restored. (3) a later sample allowed to reuse an earlier one's items (`earlier` returning no keys): "1 failed", restored |
| JC10 | built; the numbers wait for the record | THRESHOLDS.md, "The calibration's verdicts (S6)": both criteria "waiting for the labels", the triggers, AV2-J3's limit; `test_calibration_thresholds.py` holds the rows to record.json once it exists, and to "waiting" until then | grounded marked `trusted` while no record exists: "1 failed", restored |
| JC11 | not applicable until the verdicts | - | - |
| JC12 | partly built: what needs no number | TEST-PLAN R5's gate cell ("per criterion by the S6 calibration ...: only a criterion trusted there may gate, from S8") and `test_r5_names_its_tests_and_its_gate_local_until_keys_by_the_s6_calibration`; ONBOARDING's rows; ARCHITECTURE and README S6 `wip`; CHANGELOG. Waiting: section 10's judges line (kappa on n labels), the Test column's words, LOCAL-MODEL (the cap and the session's time), S6 `done` | (1) R5's gate cell put back to "reported, not gated, until S6 calibrates the judge": "1 failed, 12 passed", restored. (2) ARCHITECTURE's S6 class changed to `done` without the README's: `test_readme_status_matches_architecture` failed, restored |
| JC13 | `make -k check`: below | no new dependency (`pyproject.toml` and `uv.lock` unchanged since `2b9ba60`) | waits for the criteria judge |

## Developer choices (for the review)

1. **An undefined kappa reads "reported only"** (`undefined` in bar.toml, written before any
   label): it happens only when the labels and the verdicts all fall in one and the same class, so
   agreement beyond chance cannot be measured; never trusted, never gated. The plan's bar did not
   say; it is my choice, a question for the maintainer, and it can change only before the sample is
   drawn (the sample pins bar.toml's sha256; after it, a change is a new calibration folder).
   Answered on 2026-10-24: "Reported only (Recommended)" (below, "The maintainer's answers").
1a. **A shortfall is said in the sample's pins** (the plan: "any shortfall said"), so for a short
   criterion the labeller can read its strata's counts before labelling (for example "judge pass, 5
   of 7, 2 more from the other stratum"): aggregate counts, never which items. The v1.1 records'
   draws above were short on `abstains` both times, so the v2 draw may be too; this is the plan's
   design, said here so that it is not read later as a blindness slip. Answered on 2026-10-24:
   "Keep it in the sample (Recommended)" (below).
1b. **`src/raglab/evals/judged.py` changed** (choice 9 below), outside `src/raglab/judge/`: the
   criteria judge sees it in `git diff origin/main`; the judged run's tests were green after it.
1c. **Test time:** `tests/judge` took about 14 s before S6 and about 60 s with its tests;
   `make check` took 259.66 s real, where the S5 and answer-v2 ledgers measured 201.89 to 213.25 s.
2. **Rule s6-1's details, fixed in code and in calibration.py's docstring before any record:**
   each stratum's shuffle has a stream of its own, `random.Random("<seed>:<criterion>:<verdict>")`
   (a string seed is hashed the same way on every run), so one stratum's size never moves another's
   draw; the criteria are drawn in the bar's order, each its judge passes first; "one per case
   first" runs in rounds, one more item per case each round; a short stratum's rest is taken from
   the other stratum by the same rule; the labelling order has its own stream,
   `random.Random("<seed>:order:<criterion>")`.
3. **An item excluded from a later sample is a case, trial and criterion**, not a case: a fresh
   sample of the same answers may take another criterion or another trial of a case. Excluding
   whole cases would leave about three abstain cases for a second `abstains` sample.
4. **The sample pins the judge's seed** (the judged manifest's), so the label CLI rebuilds the very
   JudgeItem the judged run sent; bar.toml also holds the bootstrap's and the re-label's settings.
5. **The label CLI shows the judge prompt's user message verbatim** (the criterion's rules, then
   the frames), then the shown passages by number; a passage may be named by its number or its id.
6. **The re-label's 12:** per criterion `random.Random("<seed>:relabel:<criterion>").sample(...)`,
   in the order `random.Random("<seed>:relabel-order")`; the CLI and `calibrate` refuse one inside
   24 hours of the labels' seal.
7. **The record's commits** (bar, sample, labels) are read with `git log` when `make calibrate`
   writes the record, and kept by the regenerate test (a shallow CI checkout has no history); the
   criteria judge checks them with `git log`.
8. **The weights use the frame after exclusions** (the population the sample was drawn from).
9. **`judged.inputs` was extracted from `judged.run`** so the label CLI and the judged run build
   their items with the same code; `src/raglab/judge/` is untouched.
10. **The `__main__.py` docstring's list of commands is unchanged** (a line S7 and S9 may also
    change); `label` and `calibrate` are inserted mid-file, after `canaries` and `cost`.
11. **`make hooks` was not run:** the hooks were active (`core.hooksPath` is set in the shared git
    config), and the target would rewrite that shared setting to a relative path for every
    worktree.

## Waiting, in order, after S4b merges

1. `main` merged into this branch with a merge commit; `make check` green (but for `audit`, until
   the orchestrator's pull request).
2. The dry run on S4b's run 1 with a scripted fake judge, no model: the exact call count (the
   orchestrator relayed S4b's developer's count of 1,433 on the current split, to be taken again
   from the merged data).
3. The cap by the rule (the count × 5.710 s × 1.5, up to the next half hour), with the count, the
   two means and the rule in `config/judge-local.toml`'s comment. `git grep` for the old cap at
   stop 1 names what changes with it: `config/judge-local.toml:50`, `tests/unit/test_eval_config.py`
   line 265 (it replaces the literal `run_timeout_s = 7200`), the example in
   `src/raglab/evals/config.py` line 77 and the judge session's line in docs/LOCAL-MODEL.md. The
   one-judge test already allows the cap.
4. Stop for the maintainer's go on the judge session (about 2 h 15 min, AC power, one model,
   nothing beside it).

## make -k check at stop 1 (2026-10-24, 03:41 to 03:45 WEST, at `4f07000`)

`/usr/bin/time -p make -k check`: real 259.66 s (user 241.90 s, sys 17.00 s), exit 2, from `audit`
alone. Each target, from its output:

| Target | Result |
|---|---|
| format | "262 files already formatted" |
| lint | "All checks passed!" |
| types | "0 errors, 0 warnings, 0 informations" |
| deps | deptry "Success! No dependency issues found."; vulture silent |
| audit | red, pre-existing on `main`: "Found 8 known vulnerabilities, ignored 43 in 3 packages": filelock 4.0.12 three (fixed in 4.2.1), pillow 12.3.0 two (13.0.0), pypdf 6.19.0 three (6.21.2). Two more filelock advisories than at 23:48 (above), as the orchestrator relayed at the resume. The DeepEval tool's audit line did not run: make stops a recipe at its first failing line |
| sast | bandit and semgrep silent (pass) |
| workflows | zizmor "No findings to report. Good job!" |
| secrets | gitleaks dir and git (340 commits): "no leaks found" |
| privacy | "0 hits across 379 files (42 rules)" |
| architecture | "0 architecture violations in src/raglab" |
| check-dataset | "check-dataset: datasets/golden.v1.jsonl passes (34 retrieval questions, 40 behaviour cases, sha256 5f8cdaf18783)" |
| model | "already in the cache" |
| test | "1435 passed, 3 skipped, 2 deselected, 1 warning in 215.65s (0:03:35)". The 3 skipped are the repository-level tests over committed calibration folders (the re-draw, the regenerate and the leak test), which have no sample, record or labels yet ("got empty parameter set"); the warning is starlette's test client deprecation through fastapi, as on `main` |
| gate | "recall@5 0.682 (n 22) passes" |
| api-smoke | "api-smoke: passed" |

After the run: `f71f12c` changes one docstring of `calibration.py` (each agreement scope's bootstrap
stream, said precisely; `ruff format --check` and `ruff check` clean), and this ledger.

## The maintainer's answers to the two questions (2026-10-24, about 12:50 WEST)

Relayed by the orchestrator, each question and answer verbatim:

1. **The undefined kappa.** Question: "S6: when a criterion's kappa can't be computed (for
   example, the judge gave the same verdict on every sampled item), how should the calibration
   record read it?" Answer: "Reported only (Recommended)". The option's description: "Neither
   trusted nor stopped. S8 can't gate on that criterion, and the record says why. This is the
   developer's choice."
2. **The shortfall in the sample.** Question: "S6: if a criterion has too few judge fails to fill
   its sample, the sample records the shortfall, so you'd see that criterion's pass and fail counts
   before labelling. You'd never see which items. Normally you already know the design split, 7
   passes and 8 fails. Keep it that way?" Answer: "Keep it in the sample (Recommended)". The
   option's description: "As the plan says: counts only, fixed before you label. It tells you no
   more than the 7/8 split you already know."

**What says so, checked against each answer** (edits only: S4b's live sessions hold the Mac, so no
test and no `make check` ran for this; the commit hooks did):

- **Answer 1.** `bar.toml` already reads `undefined = "reported only"`, its comment "never trusted,
  never gated" (unchanged, so the bar's commit stays `d7c9b76`); `Bar.status` returns it for an
  undefined kappa (`test_kappa_is_undefined_when_both_raters_use_one_class_and_the_bar_says_so`,
  run at stop 1). "The record says why" was not yet true: record.md showed "undefined" and the
  status but no reason, so `render_record` now writes one sentence per criterion whose kappa
  cannot be computed ("...: neither trusted nor stopped, and S8 does not gate on <criterion>"),
  with a new test, `test_the_record_says_why_a_kappa_cannot_be_computed`: written, ruff-clean and
  byte-compiled, and run once the Mac was free (below). The guide and THRESHOLDS.md quote the
  answer.
- **One word of the question differs from the code, for the review:** its example, "the judge gave
  the same verdict on every sampled item", leaves kappa computable when the labels differ among
  themselves: Cohen's formula then gives exactly 0 (the judge agrees no better than chance), which
  the bar reads as not trusted, not reported only. Kappa cannot be computed only when the labels
  are all of that one class too. With the sample stratified by the judge's verdict, the judge is
  constant on a criterion only when its stratum of one side gives no item (the judged record has
  no such verdict, or each one's answer is already in the sample or excluded). The code
  follows the answer as asked (a kappa that cannot be computed) and leaves kappa 0 to the bar's
  line; changing that would be a new decision.
- **Answer 2.** `draw_sample` writes the shortfall into the pins, counts only, before any label
  (`test_the_draw_on_a_v11_record_is_stratified_seeded_and_one_answer_once` and the field test, run
  at stop 1); the guide now says the pins hold any shortfall, in counts only, never which items,
  and quotes the answer.

**The maintainer on the kappa 0 note:** the orchestrator relayed it to the maintainer, who made no
change (relayed 2026-10-24, 13:10 WEST), so the build stands: a kappa that cannot be computed reads
reported only, and a kappa of 0 is read by the bar's line (not trusted).

**Run once the Mac was free** (the orchestrator, 13:10 WEST: "S4b's live sessions are over and
Ollama is down"), at `b315aeb`, 2026-10-24, 13:17 to 13:19 WEST, the files `b315aeb` touched and
the tests that read them:

- `uv run pyright src/raglab/evals/calibration.py tests/judge/test_calibration_agreement.py`: "0
  errors, 0 warnings, 0 informations".
- `tests/judge/test_calibration_agreement.py`: "27 passed, 1 skipped in 25.65s" (the skip: no
  committed record yet), the new test among the 27.
- `tests/judge/test_calibration_bar.py`, `test_calibration_thresholds.py` (THRESHOLDS.md),
  `test_calibration_sample.py`, `test_label_cli.py`, `test_calibration_leak.py` (calibration.py's
  other readers), `tests/generation/test_consistency_gate.py` and `tests/unit/test_test_plan.py`
  (THRESHOLDS.md's other readers): "67 passed, 2 skipped in 25.72s" (the skips: no committed
  sample or labels yet).
- The new test's break: the sentence's condition made never true (`... is None and False` in
  `render_record`): "1 failed" (`test_the_record_says_why_a_kappa_cannot_be_computed`), restored
  from git: "1 passed".

The guide (`datasets/calibration/README.md`) is read by no test. The full `make -k check` waits for
the next stop, after the merge of `main`.

## The merge of `main` (2026-10-24, 21:39 WEST)

S4b merged as pull request #30 (`b7eb791` on `origin/main`). The orchestrator's go for the steps
after it, verbatim in its first lines: "S4b is merged: #30, merge commit b7eb791 on origin/main.
This is your go for S6's post-S4b steps, up to the stop before the live session." Its step 1 said
to stop, unresolved, if any file but CHANGELOG.md conflicted. The first `git merge --no-ff
origin/main` conflicted in CHANGELOG.md, the Makefile (`.PHONY`), README.md and
docs/ARCHITECTURE.md (the status lines), so the developer ran `git merge --abort` and handed back
with a proposed resolution. The orchestrator's answer, verbatim: "Go: redo the merge of origin/main
(b7eb791) and resolve it as you proposed. 1. **CHANGELOG.md:** S6's line first, then S4b's, then
the audit fix's, every line kept. 2. **Makefile `.PHONY`:** main's line, with `label relabel
calibrate` added at the end. 3. **README.md and docs/ARCHITECTURE.md:** identical in both: - `class
S0,S1a,S1b,S2,S3,S4,S5,S4b done` - `class S6 wip` - `class S3h,S7,S8,S9,S10,S11,S12,B todo`".

`git fetch origin`, then `git merge --no-ff --no-edit origin/main`: the same four files conflicted,
and nothing else (docs/ONBOARDING.md, docs/TEST-PLAN.md, docs/THRESHOLDS.md,
`src/raglab/__main__.py` and `tests/unit/test_test_plan.py` merged without a conflict). Each was
resolved as the go says, by a scratch script that refused any file with other than one conflict
block, and the merge was committed with git's default message: `26b5a5a` ("Merge remote-tracking
branch 'origin/main' into feat/s6-judge-calibration"), parents `8ff9ff8` (S6) and `b7eb791`
(main); 64 files changed against S6's parent, 24 against main's. The resolved hunks, `git show --cc
26b5a5a -- CHANGELOG.md Makefile README.md docs/ARCHITECTURE.md` (the CHANGELOG's two main lines in
full; the `.PHONY` lines are one line each in the file):

```
diff --cc CHANGELOG.md
@@@ -5,15 -5,26 +5,35 @@@ One line per change, newest first, grou
  ## Unreleased

 +- S6, judge calibration (plan `docs/plans/2026-10-23-s6-judge-calibration.md`, ledger beside it):
 +  [S6's line, nine lines in all, as before]
+ - S4b, golden set v2 (plan `docs/plans/2026-10-23-s4b-golden-set-v2.md`, ledger beside it):
+   [S4b's line, thirteen lines in all, as on main]
+ - The advisories published on 2026-10-23, so the audit passes on `main` again: filelock 4.0.12 →
+   [the audit fix's line, seven lines in all, as on main]
  - answer-v2, the prompt fix for abstention (plan `docs/plans/2026-10-21-answer-v2.md`, ledger
diff --cc Makefile
- .PHONY: check ... test gate api-smoke hooks ... container container-run zap label relabel calibrate
 -.PHONY: check ... test gate eval-retrieval api-smoke hooks ... container container-run zap
++.PHONY: check ... test gate eval-retrieval api-smoke hooks ... container container-run zap label relabel calibrate
diff --cc README.md
-   class S0,S1a,S1b,S2,S3,S4,S5 done
+   class S0,S1a,S1b,S2,S3,S4,S5,S4b done
 -  class S3h,S6,S7,S8,S9,S10,S11,S12,B todo
 +  class S6 wip
-   class S3h,S4b,S7,S8,S9,S10,S11,S12,B todo
++  class S3h,S7,S8,S9,S10,S11,S12,B todo
diff --cc docs/ARCHITECTURE.md
-   class S0,S1a,S1b,S2,S3,S4,S5 done
+   class S0,S1a,S1b,S2,S3,S4,S5,S4b done
 -  class S3h,S6,S7,S8,S9,S10,S11,S12,B todo
 +  class S6 wip
-   class S3h,S4b,S7,S8,S9,S10,S11,S12,B todo
++  class S3h,S7,S8,S9,S10,S11,S12,B todo
```

The elided parts are unchanged lines of either parent (the `.PHONY` lines' middles are the same
targets on both sides; the CHANGELOG lines are each side's own text, kept whole). The Makefile hunk
also carries main's five new `AUDIT_SKIP` ids, taken from main as they are. The two tests the go
names, before the commit: `test_readme_status_matches_architecture` and
`test_each_node_has_exactly_one_known_status`: "2 passed".

## The dry run on S4b's run 1 (2026-10-24, 21:41 WEST, at `26b5a5a`)

`judged.run` with `config/judge-local.toml` on `20261024T090351Z-generation-local-ollama-dev-ade9397`
(S4b's run 1, the consistency baseline on golden set v2's dev slice, answer-v1, ×3), with a scripted
fake judge (FakeChat: no model, no Ollama, no network) that answers each canary on its side and
passes every other call, written to the scratchpad, never into the repository. A scratch script, as
S5's dry run. The record validated (`record.validate`: no problem; provenance fake, so it can never
be published); `judged.run` took 0.653 s and the script 0.665 s in all, ingest included. The counts,
as the record holds them (aggregate only; the fake's verdicts are not the judge's, and no judged
record on v2 exists yet):

| Kind | Calls |
|---|---|
| canaries | 19 |
| verdicts | 1,015: `grounded` 298, `cites_support` 149, `correct` 179, `relevant` 244, `abstains` 54, `refuses_and_helps` 30, `context_sufficient` 61 |
| repeatability (trial 1 of every behaviour case judged again) | 268: `grounded` 76, `cites_support` 48, `correct` 58, `relevant` 58, `abstains` 18, `refuses_and_helps` 10 |
| order (`grounded` with the passages reversed) | 98 |
| **in all** | **1,400** |

The source: 303 case-trials of 101 cases (79 behaviour cases, 43 `answer`, 18 `abstain`, 8
`flag-conflict`, 10 `refuse-and-help`; 22 retrieval questions); statuses ok 298 and blocked 5 (a
withheld trial's answer is judged on no criterion; `context_sufficient` reads its retrieval). The plan's design count was about 1,469 and S4b's developer's
about 1,433 on the earlier split (relayed by the orchestrator, to be taken from the merged data):
the merged data gives 1,400. `abstains`' frame will hold at most 54 verdicts, as the plan
projected.

## The cap (2026-10-24, `ec9870c`)

The plan's rule: the count × 5.710 s (the slower measured mean) × 1.5, up to the next half hour.
The two means, from the records: 3,380.41 s / 592 = 5.7102 s (S5's judged baseline, `5aa0ec5`) and
3,257.091 s / 605 = 5.3836 s (answer-v2's judged record, `c14acb0`). 1,400 × 5.710 × 1.5 = 11,991
s, so **`run_timeout_s = 12600`** (3 h 30 min), 1.58 times 1,400 calls at the slower mean.
Committed before the session, with the count, the two means and the rule in the comment (the
config's other lines unchanged):

- `git diff origin/main -- config/judge-local.toml`: the `[judging]` cap's comment block and its
  value, 7200 to 12600, and nothing else. `git diff --stat origin/main -- src/raglab/judge
  docs/CRITERIA.md datasets/canaries.judge.jsonl pyproject.toml uv.lock`: empty.
- `shasum -a 256`: `config/judge-local.toml` now
  `dac42367c992897e3e0f7a840618fe50377c4d5eb9238ef20d287f7eeeca26ff` (the file sha256 the v2 record
  will carry); its canonical sha256 `6d0e2f3c4a84029d82674e230f76acf2efcf89a353ca2002d42fb815e6d305ec`;
  docs/CRITERIA.md `8c8f973a3306392fa1e2049ca41bcdb23d7a96d17f804af8ac84a0ca3edd9e0e` and the canary
  set `4ca54c3ced557118f26306543164dc01c7509d1866e9e77f6cd4f2d3284b328f`, unchanged.
- With it: `tests/judge/test_judged_cap.py` (2 tests: the calls counted again from the source record
  with the judged record's own rules, 19, 1,015, 268 and 98, which needs no OCR text and runs in CI;
  the rule on that count and the two means read from the records, equal to the config's cap, whose
  comment states the count, the means, the factor and the result); the cap literal of
  `tests/unit/test_eval_config.py`'s refusal test; the example in `src/raglab/evals/config.py`; the
  judge session's row of docs/LOCAL-MODEL.md. `tests/judge/test_answer_v2_one_judge.py` needed no
  change: it holds `5aa0ec5` and `c14acb0` at 7200.0.
- JC2's breaks at `ec9870c`, each restored from git: `temperature = 0.1`: "2 failed, 1 passed"
  (both records); `seed = 20261021`: "2 failed, 1 passed"; the cap alone, `14400`: the one-judge
  test "3 passed" (expected pass), and `test_judged_cap.py` "1 failed, 1 passed" (the rule's own
  check). After the restores: "5 passed".

## The session's estimate

Judging 1,400 calls, at S5's per-call medians (the judged records' `latency_ms.p50`): 5.523 s
(`5aa0ec5`) gives 7,731.9 s, 2 h 8 min 52 s; 5.866 s (`25ccc0d`, judge-v1) gives 8,212.3 s, 2 h 16
min 52 s. At the measured means (each run's duration over its calls, the plan's basis): 5.384 s
gives 7,537.1 s, 2 h 5 min 37 s; 5.710 s gives 7,994.2 s, 2 h 13 min 14 s. Per-call times skew
right (p95 9.5 to 13.0 s in those records), so a median understates the sum, and the means are the
better estimate. With the judge's live contract test (33.11 s, answer-v2 ledger) and the server's
start and stop: **about 2 h 6 min to 2 h 15 min**, under the cap's 3 h 30 min. An estimate, not a
measurement: the session measures its own.

## The stop before the live session (JC3)

What the session needs, for the maintainer's go:

- **The command:** `make judge-local RUN=20261024T090351Z-generation-local-ollama-dev-ade9397`, in
  this worktree, at the head of this stop, with a clean tree (a run made from a dirty tree is never
  published). The target runs the judge's live contract test, then `raglab judge`: the canaries
  first (one off its side stops the session before any judged call, and no record is written),
  every answer on its criteria, then the checks on the judge, under the cap of 12,600 s.
- **The judge:** `ministral-3:14b-instruct-2512-q4_K_M` at digest
  `4760c35aeb9d9e9c6174c2492562c0b999e80a222804fd96b1915ab72bbcdcf7` (the preflight reads it from the
  local manifest before the server starts and refuses another), judge-v2 `e90d9d8d8bcb…`,
  docs/CRITERIA.md `8c8f973a3306…`, the canary set `4ca54c3ced55…`, temperature 0, seed 20261020.
- **Power:** AC only. The preflight refuses on battery; the watcher stops a session that loses
  power, and nothing is published.
- **Memory:** the model's 8.5 GiB plus the 4 GiB margin, about 12.5 GiB available before the server
  starts (in the S5 ledger, the judge sessions' preflights read 26.3 and 23.1 GiB available).
- **Nothing beside it:** one model; no `make check`, no other stage's session or test run, no
  other Ollama use, for its whole length (about 2 h 6 min to 2 h 15 min, above). A sleep pauses the
  run (the cap counts awake time only).
- **After it:** the record validated and published from a clean tree (`raglab publish`), then the
  sample drawn (`raglab calibrate sample --judged <the record> --folder
  datasets/calibration/judge-v2-c1`) and committed, then the labels. From the record's existence,
  this ledger and every message give its aggregate numbers only, until the labels are sealed.

## make -k check at stop 2 (2026-10-24, 21:46 to 21:51 WEST, at `ec9870c`): one test fails

`/usr/bin/time -p make -k check API_SMOKE_PORT=8767` (the S9 developer's check used port 8766 at
the same time): real 298.87 s (user 288.31 s, sys 17.50 s), **exit 2, from `test` alone**:

| Target | Result |
|---|---|
| format | "277 files already formatted" |
| lint | "All checks passed!" |
| types | "0 errors, 0 warnings, 0 informations" |
| deps | "Success! No dependency issues found."; vulture silent |
| audit | green since the merge of `main`: both lines "No known vulnerabilities found, 48 ignored" |
| sast | bandit and semgrep silent (pass) |
| workflows | "No findings to report. Good job!" |
| secrets | "no leaks found", twice (405 commits) |
| privacy | "0 hits across 411 files (42 rules)" |
| architecture | "0 architecture violations in src/raglab" |
| check-dataset | "datasets/golden.v1.jsonl passes as v1.1 (34 retrieval questions, 40 behaviour cases, sha256 5f8cdaf18783)" and "datasets/golden.v2.jsonl passes as v2 (34 retrieval questions, 120 behaviour cases, sha256 3d924ad0bd1d)" |
| model | already in the cache |
| test | **"1 failed, 1487 passed, 3 skipped, 2 deselected, 1 warning in 253.26s (0:04:13)"** |
| gate | "recall@5 0.682 (n 22) passes: the threshold is the baseline 0.682 (20261024T090200Z-retrieval-dense-dev-ade9397) minus one question (1/22), 0.636" |
| api-smoke | "api-smoke: passed" |

**The failure:** `tests/judge/test_calibration_leak.py::test_nothing_under_the_judge_package_names_the_calibration`
(JC9's path test): `assert not names.search(config)` found "calibration" in `config/judge-local.toml`.
The cap's new comment (`ec9870c`) names S6's plan file, `docs/plans/2026-10-23-s6-judge-calibration.md`,
and the path test's pattern (`calibration|labels?\.jsonl|relabels|raglab\.evals\.label`) reads any
"calibration" in the judge's config as naming the calibration. My own change, not a conflict: the
config names no calibration folder or label file. The 3 skips are the repository-level tests over
committed calibration files, none of which exist yet; the warning is starlette's, as on `main`.

By the orchestrator's go ("If anything beyond these files conflicts, or the check fails, stop and
hand back"), the developer stopped here, unfixed, and handed back two ways to fix it: reword the
comment so it does not name the plan's file (`config/judge-local.toml` only; the path test stays
as strict), or narrow the pattern to the calibration folder and the label files
(`datasets/calibration`, `labels.jsonl`, `relabels`, `raglab.evals.label` and
`raglab.evals.calibration`). Either is followed by the full `make -k check` again.

## The cap's comment reworded, and the count reconciled (2026-10-24)

The orchestrator's go, verbatim: "Go for (a): reword the cap comment in config/judge-local.toml so
it no longer names the plan file. Keep the rule and the numbers, and keep the test strict." Done in
`e87225e`: one comment line, "(S6, docs/plans/2026-10-23-s6-judge-calibration.md, "The cap")"
to "(S6's plan, its section "The cap")"; the rule, the numbers, the value and the path test
unchanged. `config/judge-local.toml` is now sha256
`4d7b79f03a1f10609cfb90215fd20427f4362ce07e7ebc33620a19e0222821fc` (the file sha256 the v2 record
will carry, in place of `dac42367c992…` above); its canonical sha256 is unchanged,
`6d0e2f3c4a84029d82674e230f76acf2efcf89a353ca2002d42fb815e6d305ec`. The tests it touches
(`test_calibration_leak.py`, `test_judged_cap.py`, `test_answer_v2_one_judge.py`,
`tests/unit/test_eval_config.py`): "57 passed, 1 skipped".

**The count: the dry run's 1,400 against S4b's design count of 1,433** (S4b ledger, "The design
count of judge calls for v2's dev slice (GV12)": "1,033 verdicts (3 x 324 per trial + 61
`context_sufficient`), 381 checks (repeatability 280, order 101) and 19 canaries", about 7,715 s at
5.38 s a call):

| Kind | S4b's design count | The dry run | Difference |
|---|---|---|---|
| verdicts on each trial's answer | 972 (3 × 324) | 954 | −18 |
| `context_sufficient` | 61 | 61 | 0 |
| repeatability | 280 | 268 | −12 |
| order | 101 | 98 | −3 |
| canaries | 19 | 19 | 0 |
| **in all** | **1,433** | **1,400** | **−33** |

Why, from S4b's run 1 (a generation record: its statuses, no judge verdict): the design count is "a
count from the cases and the frozen criteria, not a measurement", so it takes every trial as giving
an answer. Run 1 withheld five trials, each `blocked` by the citation validator at the output stage
("the answer cites ids that were not retrieved"): R-Q25 trial 3 (a retrieval question: `grounded`
and `relevant`), G-22 trials 1 and 3 (`flag-conflict`, four criteria each), G-58 trial 1 and G-105
trial 1 (`answer`, four each). A withheld trial has no text, so no criterion of its answer is
judged: 2 + 4 + 4 + 4 + 4 = 18 verdicts. Three of the five are trial 1 (G-22, G-58, G-105), so
their repeatability calls (4 each, 12) and their order checks (one each, 3) are not made either.
`context_sufficient` stays at 61: it reads the retrieval, which a withheld trial still has. Counted
from the record with the judged record's own rules (a scratch script), the run as it is gives
1,400, the dry run's count, and the same run with every trial set to ok gives 1,433, S4b's.

**What it changes:** not the cap. The rule on 1,433 calls would give 1,433 × 5.710 s × 1.5 =
12,273.6 s, up to the same 12,600 s. The estimate is 33 calls shorter, 178 to 188 s (about 3
minutes) at 5.384 to 5.710 s a call: S4b's 7,715 s (2 h 8 min 35 s) at 5.38 s becomes 7,537 s (2
h 5 min 37 s) at 1,400 calls; the session estimate above (about 2 h 6 min to 2 h 15 min) already
counts 1,400.

**The session's command, as the orchestrator gives it for the go:** `caffeinate -i make judge-local
RUN=20261024T090351Z-generation-local-ollama-dev-ade9397`. In its words: "This Mac's system sleep
is set to 1 minute, and `make judge-local` holds no wake assertion of its own. `caffeinate -i`
keeps the Mac awake only while the command runs and changes no setting." The ledger records the
wrapper again when the session runs.

## make -k check at stop 2, again (2026-10-24, 21:54 to 21:59 WEST, at `e87225e`): green

`/usr/bin/time -p make -k check API_SMOKE_PORT=8767`: real 288.54 s (user 280.86 s, sys 14.76 s),
**exit 0**. format "277 files already formatted"; lint "All checks passed!"; types "0 errors, 0
warnings, 0 informations"; deps "Success! No dependency issues found."; audit, both lines "No known
vulnerabilities found, 48 ignored"; sast silent; workflows "No findings to report. Good job!";
secrets "no leaks found" twice (409 commits); privacy "0 hits across 411 files (42 rules)";
architecture "0 architecture violations in src/raglab"; check-dataset "datasets/golden.v1.jsonl
passes as v1.1 (34 retrieval questions, 40 behaviour cases, sha256 5f8cdaf18783)" and
"datasets/golden.v2.jsonl passes as v2 (34 retrieval questions, 120 behaviour cases, sha256
3d924ad0bd1d)"; model in the cache; test **"1488 passed, 3 skipped, 2 deselected, 1 warning in
246.88s (0:04:06)"** (the 3 skips: no committed calibration files yet; the warning starlette's, as
on `main`); gate "recall@5 0.682 (n 22) passes: the threshold is the baseline 0.682
(20261024T090200Z-retrieval-dense-dev-ade9397) minus one question (1/22), 0.636"; api-smoke
"api-smoke: passed".

The stop before the live session holds: the judge session waits for the maintainer's go.

## JC3: the judge session on golden set v2 (2026-10-24, 22:01, to 2026-10-25, 00:22 WEST)

**The go.** The maintainer chose the time; the question, verbatim: "S6's judge session takes about
2 h 15 min. The judge model (~8.5 GiB) stays loaded and the GPU stays busy. The Mac must stay
plugged in with the lid open, and nothing else heavy can run alongside it. When should it run?";
the answer, verbatim: "Tonight, after checks (Recommended)". The orchestrator's checks at 22:00: AC
power, Ollama down (no process, nothing on 11434), no make or pytest running, about 27 GiB free,
the tree clean at `c8da78b`. The developer's, at 22:01:39: the tree clean at `c8da78b`; `pmset -g
batt` "Now drawing from 'AC Power'"; no ollama, pytest or make process; `make ollama-status`: no
pid, port closed, no process, nothing loaded, 26.9 GiB available, "power": "AC Power".

**The command, verbatim, with the wrapper:** `caffeinate -i make judge-local
RUN=20261024T090351Z-generation-local-ollama-dev-ade9397`, run in the background from the clean
tree at `c8da78b`, its output to `runs/tmp/s6-evidence/judge-session.log` (gitignored) with the
shell's clock before and after. `caffeinate -i` kept the Mac from idle sleep while the command ran
(this Mac's system sleep is set to 1 minute, and `make judge-local` holds no wake assertion of its
own) and changed no setting. Nothing else ran beside it: the developer read only the log's key
lines, three times, and counted the server's requests once.

| | |
|---|---|
| Launch | 2026-10-24T22:01:56 WEST (the shell's `date`) |
| Preflight | "model: ministral-3:14b-instruct-2512-q4_K_M at the pinned digest 4760c35aeb9d"; "memory: 27.0 GiB available; the model needs 8.5 GiB plus a margin of 4 GiB"; "power: the Mac draws from 'AC Power'"; "ollama 0.40.6 up on http://127.0.0.1:11434 (pid 1086, ...)" |
| The judge's live contract test | "1 passed, 4 deselected in 32.99s" |
| The canaries | "canaries: judging 19 items first", then "canaries: all 19 on their side" |
| The judged run | "judged 303 case-trials", then the checks on the judge; "run record: .../runs/tmp/20261024T210231Z-judge-local-dev-c8da78b" |
| The stop | "unloaded ministral-3:14b-instruct-2512-q4_K_M"; "stopped the server (pid 1086)"; **"postcheck passed: port closed, no ollama process, no model loaded"**; exit 0 |
| End | 2026-10-25T00:22:49 WEST: **2 h 20 min 53 s** (8,453 s) from launch to the postcheck |
| After | `make ollama-status`: no pid, port closed, no process, nothing loaded, 27.1 GiB available, AC Power |

**The record, `20261024T210231Z-judge-local-dev-c8da78b`** (created 2026-10-24T21:02:31Z,
provenance local, not partial, git `c8da78b` clean). Its manifest names: config `judge-local`, file
sha256 `4d7b79f03a1f…` and canonical sha256 `6d0e2f3c4a84…` (today's, the cap of 12,600 s); the
judge `ministral-3:14b-instruct-2512-q4_K_M` at digest `4760c35aeb9d…`, server 0.40.6; judge-v2
`e90d9d8d8bcb…`; docs/CRITERIA.md `8c8f973a3306…`; the canary set `4ca54c3ced55…`; the source,
S4b's run 1, manifest sha256 `d7dd1ea383a4…`. `record.validate`: no problem. Its manifest's sha256:
`417f2d5ca0ba571c1c603a222bc02dcad29dcca650ebf2e0c1b57ac5225eddbd` (pinned by the sample, below).

**Calls and time** (from the manifest): 1,400 judge calls, the dry run's count: 1,015 verdicts
(the role `judge`), 366 checks on the judge (`judge_checks`: 268 repeats and 98 reversals) and 19
canaries; the generator's 303 from the source. Tokens as the server reported them: judge 756,289
prompt and 125,146 completion; checks 303,782 and 48,028; canaries 14,224 and 1,688; unreported 0
in every role. The run itself took **8,417.243 s: 6.012 s a call** (its duration over its 1,400
calls); a judge call's p50 5,755.260 ms and p95 10,721.633 ms (n 1,400). Against the estimate
(about 2 h 6 min to 2 h 15 min, from the measured means 5.384 and 5.710 s): the session took 2 h
20 min 53 s, the run's mean per call 5.3% above the slower measured mean; inside the plan's own
range (2 h 13 min to 2 h 21 min at its design count). The run used 67% of its cap (8,417 of
12,600 s).

**Aggregate results only** (the blindness rule: no case, trial or item until the labels are
sealed). Per criterion, from the manifest's results: rate over judged verdicts with its 95% Wilson
interval at n = cases, pass^3, and the counts; `invalid_output` and `unavailable` were 0 for every
criterion.

| Criterion | Judged | pass | fail | unable_to_verify | Rate [95%] (n cases) | pass^3 | Quote missing |
|---|---|---|---|---|---|---|---|
| `grounded` | 298 | 252 | 46 | 0 | 0.846 [0.763, 0.903] (101) | 70 of 101 | 6 |
| `cites_support` | 149 | 128 | 21 | 0 | 0.859 [0.738, 0.929] (51) | 35 of 51 | 10 |
| `correct` | 179 | 80 | 99 | 0 | 0.447 [0.329, 0.571] (61) | 16 of 61 | 14 |
| `relevant` | 244 | 212 | 32 | 0 | 0.869 [0.780, 0.925] (83) | 58 of 83 | 7 |
| `abstains` | 54 | 31 | 23 | 0 | 0.574 [0.353, 0.769] (18) | 6 of 18 | 0 |
| `refuses_and_helps` | 30 | 29 | 1 | 0 | 0.967 [0.677, 0.998] (10) | 9 of 10 | 3 |
| `context_sufficient` | 61 | 34 | 26 | 1 | 0.557 [0.433, 0.675] (61) | - | - |

Passages named but not shown: 2 `grounded` verdicts and 1 `relevant`. **The checks on the judge:**
repeatability 268 of 268 pairs agree (`grounded` 76, `cites_support` 48, `correct` 58, `relevant`
58, `abstains` 18, `refuses_and_helps` 10); order (`grounded` with the passages reversed) 89 of 98
agree. All reported, nothing gated: the calibration's verdicts decide what may gate.

**Published:** `uv run raglab publish 20261024T210231Z-judge-local-dev-c8da78b` ("published: ...")
from the clean tree: validation, the stale check (CRITERIA.md and the canary set current), the
planted strings and the privacy check passed; committed in `e1426f3` (the record and
`runs/published/index.json`). **The one-judge test** holds it with today's cap, its file sha256
included (`0d7d9f8`): "4 passed"; JC2's temperature break (`temperature = 0.1`) now fails all
three records ("3 failed, 1 passed"), restored. THRESHOLDS.md's judged section names it as the
judged baseline, with `5aa0ec5`, `c14acb0` and `25ccc0d` as v1.1 history, and docs/LOCAL-MODEL.md
the session's time (`c4e7558`).

## JC4: the sample (2026-10-25, 00:24 WEST, `44b4adc`)

`uv run raglab calibrate sample --judged 20261024T210231Z-judge-local-dev-c8da78b --folder
datasets/calibration/judge-v2-c1`, verbatim: "grounded: 15 items, 7 of the frame's 252 judge passes
and 8 of its 46 judge fails"; "abstains: 15 items, 7 of the frame's 31 judge passes and 8 of its
23 judge fails"; "sample: 30 items written to .../sample.jsonl". No shortfall. Its pins: rule
`s6-1`, seed 20261023, the bar's sha256 `8b7faa3ec1fc…` (bar.toml, last changed in `d7c9b76`), the
judged record and its manifest sha256 `417f2d5ca0ba…`, the source run, judge-v2, the judge's seed
20261020, `excludes` [] and `shortfall` [], drawn at 2026-10-24T23:24:21Z. The file: 31 lines (the
pins and 30 items), sha256 `c562d13ad2e55e0a9b9d820e28ff2a1c00b7e61166f55582f9fcd71222c91a07`.
`raglab calibrate check`: "judge-v2-c1 draws and regenerates as committed". The repository's tests
over the committed sample (the re-draw, the order, the exclusion): "47 passed, 2 skipped" (no
record, no labels yet).

**The chain so far, by `git log` (committer times):** the bar `d7c9b76` (2026-10-23T23:52:27+01:00)
→ the judged record published `e1426f3` (2026-10-25T00:23:37+01:00) → the sample `44b4adc`
(2026-10-25T00:24:35+01:00); the labels follow.

**What `make label` shows** (a smoke check, 00:25, with `q` at once; read through a filter of its
headers only): "===== Item 1 of 30: grounded =====", the criterion's rules ("Criterion: grounded",
"Pass when ...", "Fail when ..."), the question, passages and answer frames, "Passages shown, by
number:", then the verdict prompt. `q` stopped it, and no labels file was written.

## The labelling, handed to the maintainer

From here the stage waits for the maintainer's labels (the plan's step 6). The steps, as the guide
gives them (`datasets/calibration/README.md`):

1. In a terminal, in this worktree:
   `cd /Users/admpro/Documents/other/ai-testing-rag-lab/.claude/worktrees/agent-ab79f506441b53cf5`
   (branch `feat/s6-judge-calibration`). No model, no Ollama and no network are needed.
2. `make label`. Each of the 30 items shows the criterion's rules (15 `grounded`, then 15
   `abstains`), then the question, the passages and the answer exactly as the judge saw them.
   Answer: `p` or `f`; the quote, words of the answer copied exactly; the passages your verdict
   rests on (their numbers, or empty for none); one sentence of reason; `y` or `n` for ambiguous (y
   when the frozen rule reads two ways, with both readings in the reason). `q` stops; `make label`
   resumes at the first unlabelled item; `make label REDO=<n>` labels item n again, before the seal.
3. Before the seal, do not open the judged record's `cases.jsonl` or `report.md`
   (`runs/published/20261024T210231Z-judge-local-dev-c8da78b/`), its playground page, or this
   folder's record files.
4. When all 30 are labelled: `make label SEAL=1` ("sealed labels.jsonl: 30 labels, sha256 ...").
   Nothing changes after it.
5. Then a statement, in your own words, that you did not open those files before the seal; the
   developer quotes it verbatim here and commits `labels.jsonl` and `labels.seal.json` as written,
   in one commit.
6. The re-label: `make relabel`, no earlier than 24 hours after the seal's time (it refuses before,
   naming when it opens), 12 items, then `make relabel SEAL=1`.

Time (the plan's estimates): the 30 labels about 1 h 15 min to 2 h 15 min, in one or two sittings;
the re-label about 30 to 55 minutes; the disagreements, after the seal, about 15 to 30 minutes.

## make -k check at the labelling stop (2026-10-25, 00:27 to 00:32 WEST, at `c4e7558`): green

`/usr/bin/time -p make -k check API_SMOKE_PORT=8767`: real 303.53 s, **exit 0**. format "278 files
already formatted"; lint "All checks passed!"; types "0 errors, 0 warnings, 0 informations"; deps
"Success! No dependency issues found."; audit, both lines "No known vulnerabilities found, 48
ignored"; sast silent; workflows "No findings to report. Good job!"; secrets "no leaks found" twice
(415 commits); privacy "0 hits across 415 files (42 rules)"; architecture "0 architecture
violations in src/raglab"; check-dataset v1.1 and v2 both pass; model in the cache; test **"1490
passed, 2 skipped, 2 deselected, 1 warning in 251.90s (0:04:11)"** (the 2 skips: no record and no
labels yet; the committed sample's re-draw now runs and passes); gate "recall@5 0.682 (n 22)
passes"; api-smoke "api-smoke: passed".
