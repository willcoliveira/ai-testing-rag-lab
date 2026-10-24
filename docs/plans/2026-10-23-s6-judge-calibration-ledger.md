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
   say; it is my choice and yours to change before the sample is drawn.
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
   two means and the rule in `config/judge-local.toml`'s comment; `tests/unit/test_eval_config.py`
   line 265 replaces the literal `run_timeout_s = 7200` and changes with it. The one-judge test
   already allows the cap.
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
