---
stage: S4
nodes: [S4]
---

# S4 ledger: the golden set, the dataset hard stop and the consistency gate

Plan: [2026-10-19-s4-golden-set.md](2026-10-19-s4-golden-set.md).

## Approval and decisions

The go for the draft (2026-10-18), verbatim (quoted in the plan): "Draft S4 plan (Recommended)".

The user's answers (2026-10-19), verbatim (quoted in the plan's Approval):

| Decision | Answer | What was done |
|---|---|---|
| D1 The S3 abstention finding | "Measure as is (Recommended)" | No prompt change in S4: answer-v1 stays. The behaviour checks read the label field, and the report counts the S3 pattern on the abstain cases (label not abstain, no value stated) in its four-way table. The baseline will record what the model gives (AC11, after the sign-off) |
| D2 Additions to the answer key | "Additions only (Recommended)" | The question author's answer-key additions are on their branch (`feat/s4-cases`), integrated below; this build added no answer-key line |
| D3 What a published answer may hold | "Narrow both (Recommended)" | `privacy/allowlist-published.txt` enumerates, as exact strings, the three team contact addresses of `corpus/SPEC.md` section 6 (the IT Service Desk, the SOC, Mirrowfen IT Support) beside the two exception ids; publish refuses the plain attack phrases only in attack runs, while the planted secret, the personal details, the canary token and the planted links and address block every run. **This partly reverses the S3 decision "Allow those IDs only (Recommended)" (S3 ledger, decision 1), by the user's D3 answer.** `c018cc6` |
| D5 This plan | "Approve and start" | The build started; D4 (v0.1) waits for the pull request |

## What was built (developer, 2026-10-19)

| Part | Where |
|---|---|
| Label groups (AC2) | `src/raglab/evals/golden.py`: a `relevant` entry may be `{"any_of": [sections]}` (two or more, the first the primary); `Resolved.label_sets` gives one chunk set per entry, so `raglab.evals.metrics` (unchanged: it already scores one set per thing to find) counts a group once for hit, MRR and recall; the record keeps the primary's ids, every member's chunks together and the members under `any_of`, which `record.case_problems` checks; a report adds one sentence when a run has a group. The location guard reads every member |
| check-dataset (AC3) | `src/raglab/evals/dataset_check.py`, `raglab check-dataset`, `make check-dataset` (in `make check`, before the tests), the pr-fast step "Dataset check (hard stop)" right after "Install the project"; `raglab eval` and `raglab gate` run it first (`_check_first` in `raglab.__main__`); `raglab.ingest.answer_key.features` reads the kinds, labels, locations and sides, silence proofs and banned strings (YAML stays in `raglab.ingest`) |
| Behaviour cases (AC5, AC6) | `src/raglab/evals/behaviour.py` (fields, checks, results, report section); `src/raglab/evals/oracle.py` (S3's abstention oracle, moved unchanged, with an optional `quotable` set for D-03); `generation.py` runs the golden set's behaviour cases (probes only when a config names a probes file); `generation_record.py` dispatches to them and adds results and a report section only when a run has behaviour cases; `record.py` validates the kind's fields; `schemas/run-record.v1.json` extended additively |
| Probes folded (AC9 item) | `[generation] probes` is optional; `config/fake.toml` and `config/local-ollama.toml` name no probes file (the plan: "out of the configs"); a probe id that is also a golden id is refused |
| Consistency gate (AC7) | `src/raglab/evals/gate.py` (`consistency`, `consistency_margin`); `raglab gate --config <generation config>` (runs, writes, gates) and `raglab gate --run <run>` (gates a finished run); `make gate-local`; the THRESHOLDS.md consistency row ("set from runs after the sign-off", no number) |
| Paired comparison (AC8) | `src/raglab/evals/compare.py` (`compare_generation`) |
| Test slice (AC9) | `raglab.evals.config.held_out_problem`, called by `raglab eval` (both suites) and `publish`; `config/local-ollama-nightly.toml`; `make nightly-local` |
| D3 | `privacy/allowlist-published.txt`; `publish.banned_strings`, `publish.blocks_clean_runs`; `scripts/check-forbidden.mjs` (comments only) |
| Docs | TEST-PLAN R6 (tests and gate), R2, Q-05, section 10's abstention line; THRESHOLDS consistency section; ONBOARDING; LOCAL-MODEL; ARCHITECTURE and README: S4 `wip`; README quickstart; CHANGELOG |
| Test support | `tests/dataset_support.py` (a valid 40-case golden set built from the plan's draft and the answer key, for the tests only); `tests/generation_support.py` (a scripted retriever, a per-question FakeChat script, a small pack with the real document ids, local runs through the in-process stub server) |

## Evidence per criterion (developer, 2026-10-19, macOS arm64)

`make check` exited 0 before every commit but one (`c5cd17b`, a variable renamed in a test, was
checked right after on the clean head: exit 0). Each break below was made on a committed file with
`PYTHONDONTWRITEBYTECODE=1`, run, and restored with `git checkout`; the same check was green again
after the restore and the tree clean.

| AC | Status | Evidence | Break (restored from git) |
|---|---|---|---|
| AC1 | pending (the labels judge and the user's sign-off) | The question author's 40 cases are in the file since the integration (below): `raglab check-dataset` passes all ten rules on it (34 retrieval questions, 40 behaviour cases, 27 dev and 13 test, the mix 15/8/8/4/5, the labels 25/9/3/3, P-01 to P-03 in dev); the labels judge's review, the blind agreement, AC1's own test file and the user's sign-off come next | |
| AC2 | met | Since the integration the seven retrieval questions the datasheet names (R-Q14, R-Q18, R-Q19, R-Q21, R-Q23, R-Q25, R-Q33) carry their groups, and the location guard passes over every member. `tests/unit/test_metrics.py::test_a_group_is_one_thing_to_find_by_hand` (5 hand-computed rankings through the loader and resolver: a group by its second member at rank 1, the group counted once, a member outside k, only the second member); `tests/retrieval/test_golden_retrieval.py` (a group read as one entry, wrong groups refused, one chunk set and the record's `any_of`, the guard over every member: `test_the_location_guard_reads_every_member_of_a_group`); `tests/retrieval/test_run_record.py::test_a_label_group_is_recorded_with_its_members_and_an_edited_group_is_refused` | (1) `label_sets` per member: "5 failed, 14 deselected" (`assert 3 == 2`), restored "5 passed"; (2) in the committed golden file, R-Q14's A-MFA 3.1 made a group with FAQ Q5 (no location of F-23): the guard "1 failed" (`{('R-Q09', 'A...A-FAQ', 'Q5')} == {('R-Q09', 'A-LIFE', '5.4')}`), restored "1 passed" |
| AC3 | met locally; needs CI (the PR's step log) | `raglab check-dataset` on the committed file, since the integration: exit 0, "check-dataset: datasets/golden.v1.jsonl passes (34 retrieval questions, 40 behaviour cases, sha256 4fbbdd6d4f7d)". `tests/unit/test_check_dataset.py` (18 tests: the valid fixture and the committed file pass; the datasheet's v1.1 line carries the file's sha256, and one more byte fails rule 10; each rule broken on a planted copy names its case and rule; the CLI exits 1; `raglab eval` (both suites) and `raglab gate` stop before the embedder, the model or the ingestion, which are patched to fail if reached); `tests/unit/test_workflow_rules.py::test_pr_fast_runs_the_dataset_check_as_its_own_step_before_the_tests` | The plan's break, in the committed golden file after the integration: R-Q02's label moved to A-LIFE 6.2, G-25 (abstain) given a labelled section, G-29 (flag-conflict) without its conflict side: `make check-dataset` exit 1 naming "R-Q02: rule 2 (labels and features): labelled section A-LIFE 6.2 has no chunk in the inventory", "G-25: rule 4 (abstain shape): an abstain case labels no section", "G-29: rule 5 (conflict shape): its labels lack every conflict side of F-04", and rule 10 for the changed bytes ("fails 4 check(s)"); restored: exit 0 (expected pass). Before the integration the same break was made on the S2 file with two planted cases (G-98, G-99), with the same three lines. And `_check_first` removed from the generation path: "1 failed, 1 passed" ("the run started before check-dataset stopped it"), restored "2 passed" |
| AC4 | pending (the user's sign-off) | The question author's additions are in (`b7d66a4`, and the SPEC and traceability rows of F-86 and F-87 in `0902af8`): group-member locations (FAQ entries on F-53, Device Policy 6.2 on F-17), F-40's silence phrases extended for the new tenant B topics, F-86 (the FAQ Q6 café case) and F-87 (an omission); additions only: the only removed line is F-40's old phrase list, and no canary and no `answer_must_not_contain` string changed. `tests/unit/test_answer_key.py` passes | |
| AC5 | met | `tests/generation/test_behaviour_checks.py` (11 tests, scripted FakeChat replies on a small pack with the real document ids, so the answer key's sides and canaries apply; every run validated): good replies pass every check that applies; "text abstains, label answer" fails the decision; a conflict side retrieved expects the flag with both sides named (a group member stands for the governing side), and not retrieved expects answer with no conflict field; a may_quote value passes only from a cited chunk of that section; canaries both ways; a must-not-contain phrase; the results by hand (decision rate 10/14 at n 7, per label, abstention 0 of 2 cases, over-abstention 0, behaviour pass^2 2/7, the confusion and four-way tables, agreement, label failures 2 missed and 2 without labels, 2 conflict-side misses); a withheld trial | (1) the label read from the text: "2 failed, 9 passed"; (2) the conflict rule's retrieval condition removed: "3 failed, 8 passed"; (3) may_quote widened to every retrieved chunk: "2 failed, 9 passed" (the out-of-section quote passes: `assert True is False`); each restored: "11 passed" |
| AC6 | met | `tests/retrieval/test_run_record.py`: the three S2 runs and the S3 run validate unchanged (`test_the_s3_run_still_validates_unchanged`; the committed-runs test); a behaviour case without `expected` or `mix`, with labels on an abstain case, may_quote on a labelled case, a side on a case that does not flag a conflict, an unretrieved citation or `canaries_of` is refused; checks that do not follow from the fields are refused | The probes' oracle changed (a quotable value passed for probes): the committed-runs test and `test_the_s3_run_still_validates_unchanged` "2 failed" ("case P-01 trial 1: checks {...} do not follow from the fields"), restored "2 passed" |
| AC7 | met (code and scripted runs); live after the sign-off (AC11) | `tests/generation/test_consistency_gate.py` (17 tests): pass, at the margin, below, with a margin of 2; stale on each of dataset.sha256, config.sha256, prompt.sha256, generator.digest and trials, and not on a new server version; a fake run (by provenance or by the generator's provider), a partial run and another split refused; no margin, a zero margin and no behaviour cases refused; the margin read from the consistency row, and none from the committed row; through the CLI on real records (the stub server, the real embedder's description): one line, exit 0 or 1, no baseline, no margin and a fake run refused; `make gate-local` | (1) the prompt fingerprint dropped from the stale fields: "1 failed, 16 passed"; (2) the margin doubled: "2 failed, 15 passed"; each restored: "17 passed" |
| AC8 | met | `tests/retrieval/test_compare.py`: two generation runs, B's case lines reversed: behaviour pass^2 1.000 to 0.571 (diff -0.429), decision label 1.000 to 0.714 (diff -0.286), the bounds equal to `metrics.paired_difference` over A's order (seed 7, 2,000 resamples), lost B-FC2, B-ABS and B-TB; other trials, another dataset and a retrieval against a generation run refused; `tests/retrieval/test_publish.py`: a pair without behaviour cases refused | Pairing by position: "1 failed, 5 passed", restored "6 passed" |
| AC9 | met | `tests/unit/test_held_out_split.py` (11 tests): `raglab eval` refuses split test or all under manual, pr-fast, eval-on-change and weekly (both suites) before the run; nightly and release reach the run; publish refuses a test run (retrieval) and an all run (generation) under manual and publishes them under release and nightly; a FakeChat nightly run of every split validates; the nightly config is the local config but its name and split; `make nightly-local`. The committed-runs test allows a test or all run under nightly or release only | The refusal removed (`held_out_problem` returns nothing): "5 failed, 6 passed", restored "11 passed" |
| AC10 | pending | After the sign-off: the three S2 configurations on dev at the frozen head, dense as the baseline. Until then the S2 baseline is stale (below) | |
| AC11 | pending | Live, after the sign-off and the freeze: five gate-local runs, the first the baseline, the margin from the four repeats | |
| AC12 | pending (the user's sign-off) | Datasheet v1.1 is the question author's (`c09cbec`); its latest version line carries the file's sha256, which rule 10 and `test_the_committed_datasheet_records_the_committed_file` check | |
| AC13 | partial | TEST-PLAN R6 names its tests and its gate, Q-05 points at THRESHOLDS.md, section 10's abstention line; ONBOARDING and LOCAL-MODEL name the new commands; ARCHITECTURE and README: S4 `wip`, not done; THRESHOLDS: the consistency row with no number; a CHANGELOG line; this ledger. The Golden case column and section 10's golden-set line wait for the cases | |
| AC14 | not yet: the expected exception | `make check` exited 0 at every commit of the offline build. Since the cases landed, the retrieval gate and the committed-runs test report the S2 baseline stale, as the plan expects until AC10 (the tail below) | |
| D3 | met | `tests/unit/test_published_allowlist_scope.py` (14 tests): the list is exactly the corpus's exception ids and the three team addresses read from SPEC section 6, with no personal detail and no banned string; listed entries pass under `runs/published/` and are hits elsewhere; another address (at a team's domain, or a team address with one letter more), the worked example's personal address (F-45) and the fake update's address (F-49) are hits under `runs/published/`; the bucketing of every `answer_must_not_contain` string (only F-47's and F-48's three plain phrases spare a clean run); a clean run holding "never expire" publishes and one holding the canary token is refused; an attack-suite record is held to the plain phrases | (1) an address at the Mirrowfen domain added to the list: "2 failed, 12 passed"; (2) F-45's address added: "2 failed, 12 passed"; (3) every attack string spared in clean runs: "2 failed, 12 passed"; each restored: "14 passed" |

## Runs S4 made

None published, and none live. The runs above are fake or stub-server records written by pytest in
temporary directories. No Ollama session ran, and no test-split run was made outside those test
records.

## Decisions needed (the safest reversible default is applied)

1. **Resolved by the integration.** During the offline build rules 9 (the mix) and 10 (the
   datasheet's sha256 line) could not pass on golden set v1 as S2 left it, so they waited while
   the file had S2's bytes, with a note. The cases changed the bytes; the exemption, its note and
   its test were removed (`5668685`), and the committed file passes all ten rules.
2. **Rule 8 reaches the retrieval questions too, in any letter case.** The plan names rules 3 to 9
   for the behaviour cases; a run record carries every question, so the planted-string rule holds
   for every line. Stricter; the 34 committed questions pass.
3. **What a decision label is.** Applied: the label field on an ok answer (a withheld trial's
   label is the validator's, so it fails the decision); the "no conflict field" condition only
   under the conflict rule, as the plan words it, so a plain answer case whose reply also sets a
   conflict field passes the decision. The stricter reading (TEST-PLAN section 3: answer means the
   conflict field is not set) is a one-line change.
4. **Recorded sides and quotable values.** A flag-conflict case's labels carry their side, read
   from the answer key at run time, and an abstain case's may_quote section carries the values its
   chunks state (numbers only): the validator recomputes every check from these fields, as it
   trusts the labels' chunk ids, and does not re-read the answer key's locations (only its canaries
   and banned strings, live). Re-deriving sides at validation would tie old records to later
   answer-key additions.
5. **The gate label of a gate-local run.** Applied: `manual` (the run is started by hand); the
   alternative is `eval-on-change`, which the main plan's CI gate will carry once keys exist.

## Developer choices (for the review)

1. **metrics.py needed no change for groups**: it already scores one chunk set per thing to find;
   the group is formed where labels resolve (`golden.Resolved.label_sets`). Its docstring says so.
2. **Rule 4 reads the first feature's silence proof** (scope corpus or the asker's tenant), as rule
   7 reads the first feature's label; **rule 6's must-not-block features are those of kind
   `must-not-block`** (F-54 to F-56, as the plan names them; F-46's kind is `contact
   (must-not-block)`, which rule 7 already holds to answer when it is first).
3. **A question repeats only for the same tenant** (rule 1): S3's P-01 and P-02 ask the same words
   as two tenants.
4. **The datasheet's version line** is a list item or table row that starts with a version (`v1`,
   `| v1.1 |`); the latest is the highest version, and it must hold the file's sha256.
5. **no_canary and must_not_contain read the conflict note as well as the answer**: both are model
   text a record publishes.
6. **The confusion table's rows are the effective expected label** (after the conflict rule), and
   a trial whose status is not ok is its own column, `withheld`.
7. **The consistency margin's cell format is `margin: M case(s)`** on the row whose first cell
   starts with "behaviour pass^"; the gate refuses to judge without one, or with less than one
   case.
8. **The generation comparison** pairs behaviour cases only, by id, with A's seed and interval
   level and 2,000 resamples (the retrieval default), and refuses partial runs.
9. **D3's bucketing**: a string blocks clean runs unless it is a plain phrase (letters and digits
   between single spaces) of an attack feature (kind `attack-...`); a run of any suite but retrieval
   and generation, or whose suite cannot be read, is held to every string.
10. **The nightly gate is passed on the command line** (`make nightly-local` gives `--gate
    nightly`); the config holds split all, and `raglab eval` refuses it under any other gate.
11. **The probes key is optional, and both committed generation configs drop it** (fake.toml too):
    once the probes are golden cases, a config naming the probes file would repeat their ids.
12. **A section may sit in several groups of one question** (found in the real file: a FAQ entry
    that restates two rules is a member of the group of each); it is still refused twice as a label,
    twice in one group, or as both a label and a member (`4cef0e3`).

## Notes

- The shell guard of this environment refuses a command line that names the `raglab` evaluation
  subcommand, so no suite was run from the shell; the CLI paths are exercised by tests that call
  `raglab.__main__.main` (and `make gate`, inside `make check`).
- Once, `pytest tests/contract` was run without the offline marker expression, so the live-marked
  contract test was selected: it failed to connect, nothing listens on port 11434, and afterwards
  `pgrep -fl ollama` and `lsof -iTCP:11434 -sTCP:LISTEN` found nothing. No Ollama was started.
- The branch was cut before pull request #10 (the S3h deferral) merged into `main`.

## The integration of the cases (2026-10-19)

The question author's three commits on `feat/s4-cases` (`bd4dd36` the answer key, `54cca8a` the
cases and groups, `11a2f46` datasheet v1.1) were cherry-picked onto this branch as `b7d66a4`,
`2171cd6` and `c09cbec`; they touch only `corpus/answer-key.yaml`, `datasets/golden.v1.jsonl`
and `datasets/DATASHEET.md`, and none of those was edited here. The coordinator's patch adding
the `corpus/SPEC.md` section 8 rows of F-86 and F-87 and their TEST-PLAN traceability cells was
read (within D2's additions) and committed as `0902af8`; it clears the three
`tests/unit/test_answer_key.py` failures the new features caused.

On the real file, `raglab check-dataset` first refused R-Q14, G-17, G-21 and G-34 ("a relevant
section is listed twice"): a FAQ entry sits in two or three groups of one question. That is the
file's real format, so the loader now allows it (`4cef0e3`, developer choice 12). The S2
exemption became dead code and went (`5668685`). Tests changed with the file:
`test_the_datasheet_states_the_label_scope_the_review_raised` now reads v1.1's text (Device Policy
6.2 is a member of A-EXC 4.2's group for R-Q25); two tests that used FAQ Q5 as a section outside
the features use FAQ Q12, since Q5 is now an F-53 location.

`raglab check-dataset` on the real file: exit 0, "check-dataset: datasets/golden.v1.jsonl passes
(34 retrieval questions, 40 behaviour cases, sha256 4fbbdd6d4f7d)" (the file's sha256
`4fbbdd6d4f7de7f8874ba9e371aedb7d0539e35e89864af864b6a4b1f3fc45b3`, the one datasheet v1.1
records).

**The expected exception.** The retrieval gate and the committed-runs test in
`tests/retrieval/test_publish.py` report the S2 baseline stale once the golden file changes. The
plan republishes it only after the user's sign-off (AC10), so that is the only failing part of
`make check`, and nothing was republished. `make check` stops at its `test` target on that one
test, so the remaining targets were run one by one (the tail below).

## make check at the last commit before the integration

`42e8113`: exit 0; "1074 passed, 1 deselected"; "check-dataset: datasets/golden.v1.jsonl passes
(34 retrieval questions, 0 behaviour cases, sha256 ffb8c5a54b22)"; "retrieval no-regression gate
(22 questions): recall@5 0.644 (n 22) passes: the threshold is the baseline 0.644
(20261006T172928Z-retrieval-dense-dev-5f1d3a0) minus one question (1/22), 0.598"; "api-smoke:
passed"; privacy "0 hits across 246 files".

## make check after the integration, target by target

- `make format lint types deps audit sast workflows secrets privacy architecture check-dataset`:
  exit 0 ("0 errors, 0 warnings, 0 informations"; "No known vulnerabilities found"; gitleaks "no
  leaks found"; privacy "0 hits across 247 files"; "0 architecture violations in src/raglab";
  "check-dataset: datasets/golden.v1.jsonl passes (34 retrieval questions, 40 behaviour cases,
  sha256 4fbbdd6d4f7d)").
- `make test`: "1 failed, 1075 passed, 1 deselected": the one failure is
  `test_the_committed_runs_are_valid_local_dev_runs_with_a_current_baseline`
  ("assert 'ffb8c5a54b22...7146b19436104' == '4fbbdd6d4f7d...6a4b1f3fc45b3'"), the expected stale
  baseline.
- `make gate`: exit 2 (raglab 1), "retrieval no-regression gate (22 questions): the baseline
  20261006T172928Z-retrieval-dense-dev-5f1d3a0 has another dataset.sha256
  (ffb8c5a54b2277bd90efd9bdebda4b91494eb472c3c604b6f057146b19436104 vs
  4fbbdd6d4f7de7f8874ba9e371aedb7d0539e35e89864af864b6a4b1f3fc45b3): publish a new baseline in a
  reviewed pull request", the expected stale baseline.
- `make api-smoke`: "api-smoke: passed".
