---
stage: S4b
nodes: [S4b]
---

# S4b ledger: golden set v2

Plan: [2026-10-23-s4b-golden-set-v2.md](2026-10-23-s4b-golden-set-v2.md). Branch
`feat/s4b-golden-set-v2`, cut from `main` at `2b9ba60` (answer-v2's merge); the plan's commit is
`f6f7d7e`.

## Approval and decisions

The go for the draft (2026-10-23, about 22:10 WEST), verbatim (quoted in the plan): "S4b planner
now (Recommended)", the answer to "answer-v2 is merged and cleaned up. The main plan's next stage
is S4b: golden set v2, about 120 cases, covering every question type and both tenants. Start it?"

The maintainer's answers (2026-10-23, about 22:50 WEST, through the orchestrator's question
prompt), each with its question, verbatim (quoted in the plan's Approval):

| Decision | Question | Answer | What it means for the build |
|---|---|---|---|
| D1 | "S4b D1: v2 makes answer-v1's consistency baseline (14 of 27 on v1.1 dev) stale. Re-run it on v2 in S4b?" | "Re-run on v2 in S4b (Recommended)" | Option A: at F, five `make eval-local` sessions on v2's dev slice, run 1 the baseline; the local, nightly and release configs move to v2 together (GV11) |
| D2 | "S4b D2: the judged baseline on v2 is one long local judge session, about 2 h 15 min (estimate). That is over the judge's 2-hour cap. Where should it run?" | "In S6, as its first live step (Recommended)" | Option A: no judge session in S4b; the judge's files stay byte for byte; THRESHOLDS.md keeps `5aa0ec5` (v1.1) as the judged baseline until S6, and this ledger gives S6 the design count of judge calls for v2's dev slice (GV12) |
| D3 | "S4b D3: R-22 (an unresolved conflict between two current documents) is the only requirement with no planted feature. Change the corpus for it?" | "No corpus change; R-22 stays a gap (Recommended)" | Option A: no corpus change; R-22 stays in the answer key's gaps and TEST-PLAN's gaps table, for S8's suite audit (GV2, GV9) |
| D4 | "S4b D4: approve the S4b plan? Your time over the stage is about 4–5 h (estimate), most of it the v2 sign-off." | "Approve and start (Recommended)" | The build (developer) and the cases (question author, `feat/s4b-cases`, cut from `f6f7d7e`) start in parallel on 2026-10-23 |

## What was built (developer, offline, 2026-10-23)

The build ran beside the question author, who owns `datasets/golden.v2.jsonl`,
`corpus/answer-key.yaml`, `corpus/SPEC.md` and `datasets/DATASHEET.md` on `feat/s4b-cases`; none
of the four was edited here. No live session was started.

| Part | Where |
|---|---|
| check-dataset per version and per file (GV4) | `src/raglab/evals/dataset_check.py` (`bbe7cc7`): `maintenance_rows` reads the datasheet's Maintenance table only (the first table of the section headed "## Maintenance"; a row is one whose first cell is a version); `latest_row` gives the file's latest row, the File cell naming each row's file; rule 10 compares that row's sha256 with the file's; rule 9 holds the file to `CONTRACTS[version]`: v1.1 keeps S4's rule 9, and v2 has the mix 45/24/24/12/15, at least 55 answer, 24 abstain, 12 flag-conflict and 14 refuse-and-help cases, 8 must-not-block cases, 3 abstain cases with may_quote and 28 tenant B cases, a test case for every slot, label and tenant, a tenant B test case under each label tenant B has, and the S3 probes in dev. A version with no contract is a rule 9 problem. The pass line names the version: "check-dataset: datasets/golden.v1.jsonl passes as v1.1 (...)" |
| check-dataset over both files (GV4) | `src/raglab/__main__.py`: with no `--dataset`, every `datasets/golden.v*.jsonl` in name order, one verdict each, exit 1 when any fails; `--dataset` is repeatable. `make check-dataset` is still `uv run raglab check-dataset`, so `make check` and pr-fast's "Dataset check (hard stop)" check both files once v2 is in. `raglab eval` and `raglab gate` check their config's file first, as before |
| The split (GV6) | `scripts/split_golden.py`, committed as `a525c90`, before any case was integrated: the plan's rule, seed 20261023 (the open choices are under Developer choices). `tests/unit/test_split_golden.py`: the rule on small files (strata, pools, one third to test, the base lines byte for byte, `split` after `question`), the draw computed again from the seed, refusals, a file already split left as it is, and a split set by hand named by the re-split. Its test on the committed v2 file is skipped until the file exists |
| The v2 fixture | `tests/dataset_support.py`: golden set v1.1's 74 lines as committed, then 80 planted behaviour cases G-38 to G-117 from the answer key's existing features, written without a split and split by the script (placeholder questions); with its datasheet it passes check-dataset as v2 (34 retrieval questions, 120 behaviour cases). The v1.1 fixture's datasheet now has a Maintenance table with a File column |
| GV1, GV2, GV3 | `tests/retrieval/test_golden_v2.py` (`f4ddfcb`), reading the lines itself (`tests/golden_support.py`): GV1 (v1.1's lines byte for byte, G-38 to G-117 in order, behaviour cases, synthetic, 34 and 120, the mix, no question asked twice by one tenant, S2's overlap measure for the new cases); GV2 (every requirement with a planted feature covered; R-02, R-20, R-21 and R-22 gaps named by no feature; every kind but secret-in-doc, pii-in-doc and near-duplicate starting a case; a dev case for every kind with two or more; the floors); GV3 (below). The checks on the committed v2 file are skipped until it exists |
| S4-J10 and S4-J11 (GV8) | `tests/retrieval/test_publish.py`: the Maintenance rows are read with their File column (`tests/golden_support.maintenance`, a reading of its own, not raglab's); a published record whose dataset path is not its version's file is named; the expected versions and hash count are derived from the datasheet, never written in the test |
| The traceability test (GV9) | `tests/unit/test_test_plan.py` (`9046cf1`): the Golden case column is derived from the golden set's latest version (the datasheet's highest Maintenance row and its file): S4b's cells stay "tbd (S4b)" while v1.1 is the latest and name their cases from v2; R-06's by-design cases are the may_quote cases; ids may have three digits. Held on the planted v2 now, with the plan's two breaks |
| The retrieval target (GV10) | `make eval-retrieval` (`b538d30`): the three committed retrieval configs on their dev split, offline, dense first; not in `make check`; its test holds the three lines |
| The configs at F, prepared | The configs stay on v1.1 until F. The tests that named `golden.v1.jsonl` for a config read the config instead (the fake suite end to end, the fake API leak test, the config tests, the session test's planted config), and `test_the_configs_name_one_golden_file_and_the_position_test_keeps_v1_1` holds the seven configs that move to one golden file at any time and `config/position-local.toml` to v1.1. At F, one commit sets `path = "datasets/golden.v2.jsonl"` in `config/fake.toml`, `retrieval-dense.toml`, `retrieval-hybrid.toml`, `retrieval-dense-600.toml`, `local-ollama.toml`, `local-ollama-nightly.toml` and `local-ollama-release.toml` |
| Docs (offline part) | `999695c`: ARCHITECTURE and the README class S4b `wip`; the main plan's dated note for D2 and D3; THRESHOLDS.md's judged section says the judged baseline stays `5aa0ec5`, on v1.1, until S6; ONBOARDING's check-dataset line and `make eval-retrieval`; the CHANGELOG line |

## Evidence per criterion

Status at STOP 0 (offline build ready, waiting for the cases). Each break below was made on a
committed file, run, and restored with `git checkout`; the tree was clean after each.

| GV | Status | Evidence | Break (restored from git) |
|---|---|---|---|
| GV1 | built; waits for the cases | `tests/retrieval/test_golden_v2.py`: the planted v2 passes every GV1 check; the checks on the committed file are written and skipped until it exists | In the tests, on the planted v2: G-04's split flipped is named ("line 41 (G-04): split differ from v1.1's", its line found in the file); G-117 given G-26's id is named, and check-dataset's rule 1 names it ("the id is used twice"); a new case left without a split fails rule 1 |
| GV2 | built; waits for the cases | The coverage test passes on the planted v2 | In the tests: the planted F-18 case re-pointed to F-20 names R-08 and the cross-reference kind; a second F-57 case in dev covers the procedure kind and, moved to test, the kind is named ("the procedure kind's cases (G-20, G-81) are all in test") |
| GV3 | met on the committed tree | `test_golden_set_v1_1_is_the_file_signed_off_in_s4` (the file's sha256 is `5f8cdaf18783...`, and the datasheet's v1.1 row carries it); `test_every_v1_1_record_names_a_file_that_still_holds_its_bytes`: 20 published records name v1.1's sha256, all name `datasets/golden.v1.jsonl`, and `record.current_golden` finds each one's bytes. The committed-runs test passes (24 records) | One byte appended to `golden.v1.jsonl`: both tests fail ("Left contains 20 more items, first extra item: '20261019T172035Z-generation-local-ollama-dev-97011a7'"), and `raglab check-dataset` exits 1: "golden.v1.jsonl: rule 10 (version): the latest version line of DATASHEET.md for golden.v1.jsonl (v1.1) does not carry the file's sha256 1f100f0db349...". Restored; check-dataset passes |
| GV4 | built; [CI] waits for the pull request | `tests/unit/test_check_dataset.py` (33 tests): both fixtures pass (v1.1 as v1.1, v2 as v2); every rule broken on a planted copy; v1.1's rule 9 kept; the version read from the file's row (the v1.1 copy held to v2 meets none of v2's contract; the v2 copy held to v1.1 meets none of v1.1's mix; v1.2 has no contract); each file held to its own rows; `raglab eval` (both suites) and `raglab gate` stop first on a broken v1.1 or v2 copy. `raglab check-dataset` on the committed tree: "check-dataset: datasets/golden.v1.jsonl passes as v1.1 (34 retrieval questions, 40 behaviour cases, sha256 5f8cdaf18783)" | In the tests, on the planted v2: G-38 made multi-chunk names both slots ("44 single-chunk case(s), the mix asks for 45", "25 multi-chunk case(s), the mix asks for 24"); every tenant B abstain test case moved to dev names the label ("no tenant-b abstain case is in the test split"); each floor one case short is named. v1.1's committed file passes (expected pass) |
| GV5 | waits for the cases | A script compares the answer key at `origin/main` with the branch's, by feature id and field name, and classes each change as an addition (a list that keeps every old item: F-40's phrases, a location's values, a new location with no side) or a change; on the unchanged key it reports no change. It runs on the integrated key | |
| GV6 | the script and its tests are in; the split waits for the cases | `scripts/split_golden.py` committed (`a525c90`) before any case; its tests | In the tests: a split set by hand is named by the re-split ("G-38: split <flipped>, the seeded rule gives <its own>") |
| GV7 | waits for the labels judge, the sign-off and F | | |
| GV8 | the tests are in; the datasheet v2 is the author's | S4-J10's and S4-J11's tests read the Maintenance table's rows with their File column; a record that names another file than its version's row is named; rule 10 per file | In the tests: a hash in prose and a version row in another section's table are no version (expected pass) |
| GV9 | built; the TEST-PLAN cells wait for the cases | The traceability test reads the datasheet's latest version and its file; on the committed tree, v1.1, S4b's cells stay "tbd (S4b)" | In the tests, on the planted v2 with cells written from it: R-08's cell back to "tbd (S4b)" is named; a case dropped from R-13's cell is named |
| GV10 | the target is in; the runs wait for F | `make eval-retrieval` and its test | |
| GV11 | waits for F (live) | | |
| GV12 | the judge is unchanged; v2's design count waits for the split | `git diff --stat origin/main` (`2b9ba60`) over docs/CRITERIA.md, `datasets/canaries.judge.jsonl`, `config/judge-local.toml` and `src/raglab/judge/`: empty. sha256: CRITERIA.md `8c8f973a3306...`, the canary set `4ca54c3ced55...`, judge-local.toml `228a720045d8...`. THRESHOLDS.md's judged section says the judged baseline stays `5aa0ec5`, on v1.1, until S6. The design count's method (below) gives 605 calls on v1.1's dev slice, the count answer-v2's judged run made | |
| GV13 | in part | S4b `wip` in ARCHITECTURE and the README; the main plan's note; THRESHOLDS' judged note; ONBOARDING; the CHANGELOG line. TEST-PLAN's cells and section 10, the datasheet, THRESHOLDS' consistency row, LOCAL-MODEL and the README's numbers wait for the cases and the runs | |
| GV14 | green but the audit, as the coordinator defined it | `make -k check` at STOP 0 (below) | |

## Runs S4b made

None yet. S4b makes no test-split run (the plan, "The runs S4b makes").

## make check at the plan commit

`f6f7d7e`, before any change (`make check`, this Mac): **exit 2, stopped at `audit`**, a failure
**pre-existing on `main`**, whose Makefile and lock this commit shares. pip-audit found 5
advisories that are not in the Makefile's skip list, all published after the last one was added
(`8a330b7`, 2026-10-22). Its failing lines, each advisory's CVE id left out (the privacy check
reads that shape as a ticket number):

    Found 5 known vulnerabilities, ignored 43 in 2 packages
    pillow 12.3.0  <a CVE id> 13.0.0     (two such lines)
    pypdf  6.19.0  <a CVE id> 6.21.2     (three such lines)
    make: *** [audit] Error 1

The coordinator's message (2026-10-23) names them by their GitHub ids: Pillow GHSA-654x-cwwv-5j9c
and GHSA-5x8w-8jj5-q52h; pypdf GHSA-6c7f-9265-g8fw, GHSA-jr96-gvgh-j3r4 and GHSA-gmh7-3g9r-mjh5.
The coordinator fixes them in a `build(deps)` pull request of its own from `main`. S4b does not
touch the Makefile's skip list or the audit, and `main` is merged into this branch, as a merge
commit, when the coordinator says. Until then a green `make check` on this branch means `make -k
check` with only `audit` red (the coordinator's instruction). Every other target of `make check`,
run in one `make` call: exit 0, "251 files already formatted", "All checks passed!", "0 errors, 0 warnings, 0
informations", gitleaks "no leaks found" twice, privacy "0 hits across 367 files (42 rules)", "0
architecture violations in src/raglab", "check-dataset: datasets/golden.v1.jsonl passes (34
retrieval questions, 40 behaviour cases, sha256 5f8cdaf18783)", "1369 passed, 2 deselected, 1
warning in 168.06s", "recall@5 0.682 (n 22) passes", "api-smoke: passed".

## make -k check at STOP 0 (the offline build, waiting for the cases)

`4f236fa`, a clean tree, this Mac (`make -k check`, 2026-10-23 at about 23:41 WEST): exit 2, and
`audit` is the only red target. pip-audit now finds **6** advisories outside the skip list, one
more than at the plan commit: filelock 4.0.12 (fixed in 4.2.1), published since, beside the two
Pillow and three pypdf ones above (its CVE id left out, as above; the coordinator's list of five
does not have it). The failed recipe stops before its second line, the DeepEval tool's audit.
Every other target passed:

    256 files already formatted
    All checks passed!
    0 errors, 0 warnings, 0 informations
    Success! No dependency issues found.
    Found 6 known vulnerabilities, ignored 43 in 3 packages
    make: *** [audit] Error 1
    no leaks found
    no leaks found
    0 hits across 372 files (42 rules)
    0 architecture violations in src/raglab
    check-dataset: datasets/golden.v1.jsonl passes as v1.1 (34 retrieval questions, 40 behaviour cases, sha256 5f8cdaf18783)
    ===== 1409 passed, 3 skipped, 2 deselected, 1 warning in 172.05s (0:02:52) =====
    retrieval no-regression gate (22 questions): recall@5 0.682 (n 22) passes: the threshold is the baseline 0.682 (20261019T180502Z-retrieval-dense-dev-97011a7) minus one question (1/22), 0.636
    api-smoke: passed

The 3 skipped tests are the checks of the committed `golden.v2.jsonl`, which does not exist yet.

## Developer choices (for the review)

1. **The version a file is held to** (the plan leaves the how to the developer): the latest
   (highest) row of the datasheet's Maintenance table whose File cell names the file. The S4
   table has no File column; while the committed datasheet has that form, each of its rows is
   the checked file's, so `make check` stays green before the cases. That reading goes at the
   integration, with its test, once the datasheet has its File column (S4's precedent: the
   integration removed a temporary exemption, S4 ledger, decision 1).
2. **A must-not-block case** is one with a feature of kind exactly `must-not-block` (F-54 to
   F-56), the set rule 6 already reads. v1.1 then has 2 (G-12, G-33), as the plan counts; F-46's
   kind, `contact (must-not-block)`, is not counted.
3. **may_quote at least 3** is a v2 floor of rule 9: the plan's table gives it in the "at least
   (rule 9)" column ("24 (the unanswerable slot), of which 3 with `may_quote`").
4. **check-dataset's default** is every `datasets/golden.v*.jsonl`, so no list of files needs
   updating when one is added; `--dataset` is repeatable.
5. **No row for the file** is a rule 10 problem only (its message says rule 9 then has no
   contract); a version with no contract is a rule 9 problem.
6. **The split's open choices** (`scripts/split_golden.py`'s docstring): the new cases are the
   lines with no split; a pool is the strata of one or two cases of one label, together; one
   `random.Random(20261023)` draws the units in a fixed order (strata of three or more sorted by
   slot, label and tenant, then the pools by label); ids are sorted by number before the shuffle;
   a new case's line is written again with `split` after `question` (json.dumps, default
   separators, non-ASCII kept), every other line byte for byte.
7. **v1.1's lines inside v2 are compared byte for byte**, a stricter reading of GV1's "unchanged
   (every field)".
8. **The tests of the committed v2 file are skipped while it does not exist**; the skip goes at
   the integration, so a missing file then fails.
9. **R-06's by-design cases** are derived as the may_quote cases (in v1.1, G-26 alone, as before).
10. **The S4b cells' words** in TEST-PLAN, which the test holds: R-15 and R-17 end "(clean runs;
    the attack runs are S7's)", R-19 "(the allow list; the deny list is S7's)", and R-22 reads
    "none: a gap, no planted feature (S4b, D3)".
11. **The make target** is `eval-retrieval`, beside `eval-local`.
12. **No stricter wording rule for v2's new cases.** S4's AC1 test (no behaviour question holds
    a retrieval question's words in order) stays on v1.1; for v2 the plan's rule 2 asks for no
    exact repeat by one tenant (rule 1) and S2's measure, reported with no threshold.
13. **Which tests read which file** (the plan's "read both files, or v2 where a config is
    meant"): `test_golden_behaviour.py` stays S4's AC1 on v1.1 and `test_golden_v2.py` reads v2,
    so both files are read; `test_golden_retrieval.py` stays on v1.1, because GV1 holds v2's first
    74 lines byte for byte, so the 34 retrieval questions it checks are the same lines in v2;
    `test_e2e_fake.py`, `test_e2e_golden_suite.py` and `test_eval_config.py` read the file their
    config names (v1.1 until F, v2 from it); `tests/dataset_support.py` builds both versions.

## Notes

- The developer's command guard refuses some command shapes (a heredoc, a subshell, `time` with
  some arguments); each such command was split into plain ones, never routed around.
- **A dry run of F's config switch, on the planted v2 (2026-10-23, never committed).** The planted
  v2 written to `datasets/golden.v2.jsonl`, the datasheet given a File column and a v2 row for
  it, and the seven configs pointed at it: `raglab check-dataset` passed both files ("passes as
  v1.1 (34 retrieval questions, 40 behaviour cases, ...)", "passes as v2 (34 retrieval questions,
  120 behaviour cases, ...)"); the config, held-out, session, check-dataset, split, golden,
  publish, TEST-PLAN and end-to-end tests gave "3 failed, 225 passed", the skipped tests of the
  v2 file running and passing, and the three failures the expected ones: the retrieval baseline
  and the consistency baseline stale (the dataset's sha256), and TEST-PLAN's S4b cells not yet
  written for v2. Restored with `git checkout` and the planted file removed; the tree was clean.
- **The design count of judge calls (GV12, D2)**, from the frozen criteria per label
  (`raglab.evals.judged_record.BY_LABEL`), three trials, every trial taken as ok and one
  retrieval per case: verdicts are 3 x (2 per retrieval question + the label's criteria per
  behaviour case) + one `context_sufficient` per case with a reference answer; the checks are
  trial 1 of every behaviour case judged again on its criteria and `grounded` on trial 1 of every
  case with the passages reversed; then the 19 canaries. On v1.1's dev slice (22 retrieval
  questions; 17 answer, 6 abstain, 2 flag-conflict, 2 refuse-and-help) it gives 441 verdicts, 145
  checks and 19 canaries, 605 calls: the number of calls answer-v2's judged run made. v2's count
  is computed once the split is in.
- **For the coordinator, before the integration: the seeded split can break a coverage rule by
  chance.** GV2's "a kind with two or more cases has a dev case" and rule 9's "a tenant B test
  case under every label tenant B has" depend on the draw, which nobody may change by hand.
  v1.1's only procedure case, G-20, is in test, so one new F-57 case drawn in the large
  multi-chunk, answer, tenant A stratum lands in test about one time in three (an estimate from
  the rule, not a run), and GV2 then fails; a kind of two new cases has both in test about one
  time in nine. The script implements the plan's rule as written, with no repair. A repair, if
  the maintainer wants one, would be decided before the cases are split, so it stays blind.

## The integration of the cases (2026-10-23 and 2026-10-24)

The coordinator's message, after the question author handed back: the author's branch is
`feat/s4b-cases`, head `5d468fc`, three commits; the integration is done now, instead of
stopping at STOP 0. The integration stopped at the GV2 result below, as the coordinator's message
says to: no case moved by hand, the seed and the rule unchanged; it is the maintainer's call.

### The author's commits, cherry-picked

| The author's commit | Here | Files | What it adds |
|---|---|---|---|
| `98c2423` | `3e50427` | `corpus/answer-key.yaml`, `corpus/SPEC.md` | new features F-88 to F-98, F-40's new silence phrases, their SPEC section 8 rows |
| `253d18a` | `f3e69c9` | `datasets/golden.v2.jsonl` (new) | v1.1's 74 lines, then G-38 to G-117 with no split; sha256 before the split `154536a96941123b3f709fd021598e40536e342527ee144c4bffdb0db4e6a502` |
| `5d468fc` | `fb4bea8` | `datasets/DATASHEET.md` | datasheet v2: the Maintenance table with its File column |

Each touches only the four files the author owns, and none of the four was edited here before
them. No conflict.

**What the author was given and read.** The author's files-read disclosure, verbatim (from the
coordinator's message): "the plan, `CLAUDE.md`, `CONTRIBUTING.md`, `answer-key.yaml`, SPEC 6–9
(my read window also showed 10–11), TEST-PLAN 2, 3 and 7 (plus both heading lists),
`golden.v1.jsonl`, `DATASHEET.md`, `probes.s3.jsonl`, `golden.py`, `dataset_check.py`, the three
tests, `register.yaml`, the 18 register documents and the kiosk `.gt.txt`. Also seen in passing:
inventory section ids (via a script); the Makefile hooks lines and the `.githooks` listing; git log
subjects; one test failure message that showed TEST-PLAN's R-03 feature cell; attack files: phrase
search only. Nothing under `runs/`, no ledger, no model output."

The author's own counts (the coordinator's message): new cases 30/16/16/8/10, so v2 is
45/24/24/12/15; 64 answer (11 must-not-block), 27 abstain (4 with `may_quote`), 13
flag-conflict, 16 refuse-and-help; 33 tenant B; its self-check 34 of 34; v1.1's 74 lines byte for
byte; S2's overlap at most 4 words on each measure. The counts below are recomputed here.

### TEST-PLAN's traceability rows for F-88 to F-98

The author's patch (`scratchpad/s4b-author/patch/test-plan-traceability.patch`, written by a
script that did not read section 8) adds the new features to the Planted features cells of R-03,
R-04, R-06, R-12, R-13, R-14, R-16, R-18 and R-19. Each row was checked against the requirements
the answer key gives F-88 to F-98 (F-88: R-04, R-12; F-89: R-13, R-16; F-90: R-13, R-14, R-16,
R-19; F-91: R-13, R-14, R-16; F-92 to F-95 and F-98: R-14; F-96: R-03, R-06, R-18; F-97: R-03,
R-18): every addition matches, and none is missing. Without the patch
`tests/unit/test_answer_key.py::test_traceability_rows_agree_with_the_key` fails ("1 failed, 33
passed"); with it, "34 passed". Committed as `c2af8d1`.

### The split

`scripts/split_golden.py`, unchanged since `a525c90` (`git diff a525c90 HEAD --
scripts/split_golden.py` empty), run once; its output, ids only:

    multi-chunk / answer / tenant-a: 11 case(s); test: G-77, G-78, G-76, G-70
    paraphrased or misspelled / flag-conflict / tenant-a: 3 case(s); test: G-117
    single-chunk / answer / tenant-a: 13 case(s); test: G-40, G-39, G-49, G-44
    single-chunk / answer / tenant-b: 9 case(s); test: G-59, G-57, G-60
    single-chunk / refuse-and-help / tenant-a: 5 case(s); test: G-45, G-46
    single-chunk / refuse-and-help / tenant-b: 3 case(s); test: G-66
    unanswerable / abstain / tenant-a: 7 case(s); test: G-96, G-93
    unanswerable / abstain / tenant-b: 9 case(s); test: G-91, G-87, G-85
    version-conflict / answer / tenant-a: 3 case(s); test: G-107
    version-conflict / flag-conflict / tenant-a: 5 case(s); test: G-102, G-104
    pool of abstain: 2 case(s); test: G-116
    pool of answer: 3 case(s); test: G-112
    pool of flag-conflict: 2 case(s); test: G-69
    pool of refuse-and-help: 5 case(s); test: G-111, G-115
    split_golden: 80 new cases, 52 dev and 28 test (seed 20261023)

Only the 80 new lines changed, each gaining `split` after its question; v1.1's 74 lines are byte
for byte. The file's sha256 is now `481063f4375036e4676f170482a4270bd0d0dae0d76d225ea6257192cef0781b`
(`e91275c`), and the datasheet's v2 row carries it (`3b2b7ff`). `raglab check-dataset`: exit 0,
"check-dataset: datasets/golden.v1.jsonl passes as v1.1 (34 retrieval questions, 40 behaviour
cases, sha256 5f8cdaf18783)" and "check-dataset: datasets/golden.v2.jsonl passes as v2 (34
retrieval questions, 120 behaviour cases, sha256 481063f43750)": every rule of both versions,
v2's floors and its tenant B test case under each of tenant B's labels included.

**The counts** (recomputed from the committed file; dev / test):

| | Value | All 120 | The 80 new |
|---|---|---|---|
| Mix slot | single-chunk | 45 (30 / 15) | 30 (20 / 10) |
| | multi-chunk | 24 (17 / 7) | 16 (11 / 5) |
| | unanswerable | 24 (17 / 7) | 16 (11 / 5) |
| | version-conflict | 12 (7 / 5) | 8 (5 / 3) |
| | paraphrased or misspelled | 15 (8 / 7) | 10 (5 / 5) |
| Label | answer | 64 (43 / 21) | 39 (26 / 13) |
| | abstain | 27 (18 / 9) | 18 (12 / 6) |
| | flag-conflict | 13 (8 / 5) | 10 (6 / 4) |
| | refuse-and-help | 16 (10 / 6) | 13 (8 / 5) |
| Tenant | tenant A | 87 (56 / 31) | 55 (35 / 20) |
| | tenant B | 33 (23 / 10) | 25 (17 / 8) |
| Split | dev / test | 79 / 41 | 52 / 28 |

Tenant B's test cases by label: abstain 5, answer 4, refuse-and-help 1. Must-not-block cases (a
feature of kind `must-not-block`): 11. Abstain cases with `may_quote`: 4. With the 22 dev
retrieval questions, the generation suite's dev slice is 101 lines (303 case-trials at 3 trials).

### GV2 after the seeded split: not met

`tests/retrieval/test_golden_v2.py::test_v2_covers_every_requirement_and_every_question_type`
fails on the committed file, on one rule only, "a kind with two or more cases has a dev case":

| First-feature kind | Its cases, all in test |
|---|---|
| background | G-40, G-49, G-77 |
| exception-overrides-rule | G-18 (v1.1), G-78 |
| procedure (R-23) | G-20 (v1.1), G-76, G-112 |

The rest of GV2 holds on the committed file: every requirement with a planted feature has a case;
R-02, R-20, R-21 and R-22 are gaps no feature names; every feature kind but secret-in-doc,
pii-in-doc and near-duplicate starts a case; every other kind of two or more cases has a dev
case; the floors (64, 27, 13 and 16 by label; 11 must-not-block; 33 tenant B). As the
coordinator's message says, no case was moved by hand, and neither the seed nor the rule was
changed: the maintainer decides. The author had warned of the same kinds (exception-overrides-
rule with G-78 its only candidate, procedure with G-76 and G-112, and external-attribution,
cross-reference, glossary-dependent and background); external-attribution (G-71), cross-reference
(G-72, G-73) and glossary-dependent (G-38, G-75) drew a dev case.

### The answer key: additions only (GV5)

The answer key at `origin/main` against the integrated one, by feature id and field name: 11 new
features, F-88 to F-98; F-40's `must_not_appear` keeps its phrases and gains 25 (an addition);
no feature removed; no existing feature's value, label, reference answer, location or side
changed; the canaries, the gaps, the notes and every `answer_must_not_contain` list unchanged
(the script's verdict: "changes that are not additions: 0"). The committed-runs test passes: all
24 published records validate against the integrated key.

### A value OCR does not reproduce (for the author)

F-92's location A-DEVICE-B 1, the scanned page, cites "Do not change kiosk settings to keep a
session open". The page's ground truth has it, but this Mac's OCR (Tesseract) reads "Do ‘not
change kiosk settings to keep a session open.", so two ingestion tests fail on the integrated key:
`tests/ingestion/test_ingest_formats.py::test_every_cited_value_is_in_the_extracted_text_at_its_place[A-DEVICE-B]`
("'Do not change kiosk settings to keep a session open' missing") and
`tests/ingestion/test_chunk_boundaries.py::test_every_feature_keeps_its_cited_values_in_one_chunk_at_default_settings`.
The value is the author's; it was not changed here. A value the OCR keeps (part of the sentence,
or no value at that location) is the author's or the maintainer's call; CI's Tesseract 5.3.4 may
read the page otherwise.

### R-22's metadata, the multi-topic features and the notes for the labels judge

- **R-22's `tested_in: S4b (candidate)`** in the answer key's gaps is left as it is. Under D3 it
  is stale, and so is TEST-PLAN's gaps row ("Candidate for S4b: ..."); the plan keeps that table
  unchanged (GV9), and changing the key's field alone would make the two disagree, so both are
  left for the maintainer at the sign-off, where the answer key's diff is reviewed. No test reads
  `tested_in`.
- **Multi-topic features.** F-89, F-91, F-92 and F-97 each hold several topics, because feature
  ids are `F-\d{2}` and F-99 is the check-dataset tests' missing id. The datasheet's known limits
  already say so ("Several topics per feature"), so it needed no edit. The id format is not
  widened in S4b unless the labels judge finds a traceability problem.
- **Notes for the labels judge** (from the coordinator's message): G-57 (F-35): an answer that
  paraphrases the expiry rule could hold an attack phrase. **Corrected (call C5):** the note said,
  as the datasheet did, that publish would then refuse the run; it would not. Publish spares a
  clean run's plain attack phrases (S4's D3), the case's `must_not_contain` check reads only its
  own features' strings (F-35 has none) and `no_canary` the other tenant's canaries, so no check
  fires on G-57 in a clean run; only an attack-suite run (S7) is held to every string (the labels
  judge's S4b-L6). The author's own doubtful calls: G-67 (password reuse labelled
  refuse-and-help), G-87 (abstain), G-78 (answer), and G-52's weak route.

### The design count of judge calls for v2's dev slice (GV12)

On the split as committed (`e91275c`): 22 retrieval questions and 79 behaviour cases (43 answer,
18 abstain, 8 flag-conflict, 10 refuse-and-help) give 1,033 verdicts (3 x 324 per trial + 61
`context_sufficient`), 381 checks (repeatability 280, order 101) and 19 canaries: **1,433 judge
calls**, a count from the cases and the frozen criteria, not a measurement. It is computed again if
the split changes.

### What waits for the maintainer's call

The TEST-PLAN Golden case cells derived from v2 (GV9; `test_the_golden_case_column_names_the_cases_that_cover_each_requirement`
fails until they are written), the removal of the S4 table reading (no File column) and of the
skips of the v2 file's tests, ONBOARDING's line naming both files, and the README's and
section 10's v2 lines.

## make -k check at STOP 1 (`8b5fcdd`)

Run once on `8b5fcdd`, a clean tree, this Mac (`make -k check`, 2026-10-24 at about 00:07 WEST),
while the labels judge reviews at that head. **Exit 2; two targets fail, `audit` and `test`.**
Every other target passes: `format` ("256 files already formatted"), `lint` ("All checks
passed!"), `types` ("0 errors, 0 warnings, 0 informations"), `deps` ("Success! No dependency
issues found.", vulture silent), `sast` (bandit and semgrep silent), `workflows` (zizmor),
`secrets` (gitleaks "no leaks found" twice), `privacy` ("0 hits across 373 files (42 rules)"),
`architecture` ("0 architecture violations in src/raglab"), `check-dataset` (both files, below),
`model` ("already in the cache"), `gate` and `api-smoke`:

    check-dataset: datasets/golden.v1.jsonl passes as v1.1 (34 retrieval questions, 40 behaviour cases, sha256 5f8cdaf18783)
    check-dataset: datasets/golden.v2.jsonl passes as v2 (34 retrieval questions, 120 behaviour cases, sha256 481063f43750)
    ===== 4 failed, 1409 passed, 2 deselected, 1 warning in 195.66s (0:03:15) ======
    make: *** [test] Error 1
    retrieval no-regression gate (22 questions): recall@5 0.682 (n 22) passes: the threshold is the baseline 0.682 (20261019T180502Z-retrieval-dense-dev-97011a7) minus one question (1/22), 0.636
    api-smoke: passed

**`audit`**, pre-existing on `main` (the coordinator's `build(deps)` pull request): "Found 8 known
vulnerabilities, ignored 43 in 3 packages", now three for filelock 4.0.12 (fixed in 4.2.1), two
for Pillow 12.3.0 (13.0.0) and three for pypdf 6.19.0 (6.21.2); two filelock ones more than at
STOP 0. Ids left out, as above.

**`test`**, four tests, each for a reason recorded above; none was changed:

1. `tests/ingestion/test_chunk_boundaries.py::test_every_feature_keeps_its_cited_values_in_one_chunk_at_default_settings`:
   "F-92 A-DEVICE-B 1: 1 chunks; the closest, A-DEVICE-B@1.0/1/1, lacks 'Do not change kiosk
   settings to keep a session open'". F-92's scanned-page value, which this Mac's OCR reads with
   a stray quote mark; with the maintainer.
2. `tests/ingestion/test_ingest_formats.py::test_every_cited_value_is_in_the_extracted_text_at_its_place[A-DEVICE-B]`:
   "F-92 A-DEVICE-B section 1: 'Do not change kiosk settings to keep a session open' missing" (the
   OCR text reads "Do ‘not change kiosk settings to keep a session open."). The same value.
3. `tests/retrieval/test_golden_v2.py::test_v2_covers_every_requirement_and_every_question_type`:
   GV2, three problems, the first "the background kind's cases (G-40, G-49, G-77) are all in
   test", then exception-overrides-rule (G-18, G-78) and procedure (G-20, G-76, G-112); with the
   maintainer.
4. `tests/unit/test_test_plan.py::test_the_golden_case_column_names_the_cases_that_cover_each_requirement`:
   24 problems, the first "R-06: ['G-26', 'G-84', 'G-85', 'G-93'] are not by design". 23 of them
   are TEST-PLAN's Golden case column not yet derived from v2, now the latest version: R-22's
   cell still "tbd (S4b)", the notes of R-15, R-17 and R-19 missing, and the cells of R-01,
   R-03 to R-07, R-10 to R-14, R-18 and R-23 and of R-08, R-09, R-13, R-15 to R-17 and R-19
   naming v1.1's cases only (or "tbd (S4b)"). The integration stopped at GV2 before writing them.
   The 24th is the test's own: its by-design check for R-06 was written for v1.1, where G-26, the
   one may_quote case, covers R-06 by design only; in v2 G-93's feature, F-96, names R-06, so a
   may_quote case also covers R-06 by its features, and the check, which wants no may_quote case
   among R-06's covering cases, fails. The by-design cases should be the may_quote cases that do
   not already cover R-06; that is corrected with the cells, after the maintainer's call.

## The labels judge's review (2026-10-24)

A different model (Fable 5.1) in a context of its own, read-only on the repository, reviewed the 80
new cases at `8b5fcdd`. Its report stays outside the repository
(`scratchpad/s4b-labels-judge/s4b-labels-review.md`); what follows is copied from it, case ids
only.

**The seal.** The judge labelled the 80 cases blind, from the ids, the tenants, the questions and
the answer key (with F-88 to F-98), the corpus documents and the register, SPEC sections 6 to 9,
TEST-PLAN section 3 and `CLAUDE.md`, and sealed its labels before it opened either golden file or
the datasheet: `blind-labels.jsonl`, sha256
`31d989d24a32d6f0057732a0a00b56d15d6e0558f1f11cbc6b34ef746721e4c3`, sealed at 2026-10-24 00:01
WEST and made read-only. It opened nothing under `runs/` and ran no model.

**The agreement:** 80 of 80 labels match; observed agreement 1.0000; chance agreement 0.3303 (both
marginals 39 answer, 18 abstain, 10 flag-conflict, 13 refuse-and-help); Cohen's kappa 1.0000; no
disagreement. The file's first feature is among the judge's feature ids for 80 of 80 cases, the
same first feature for 80 of 80. The cases the judge marked borderline before the seal, each
agreed with the file: G-67, G-78, G-87, G-90, G-52 and G-55. Lab practice, as in S4: the second
labeller is a model that had the answer key, weaker evidence than a second person labelling from
the documents alone.

**Its findings** (by id, severity and case ids; the reasons are in its report):

| Finding | Severity | Cases | What | Call |
|---|---|---|---|---|
| S4b-L1 | high | background G-40, G-49, G-77; exception-overrides-rule G-18, G-78; procedure G-20, G-76, G-112 | GV2's dev rule fails for three kinds after the seeded split | C1 |
| S4b-L2 | medium | G-52 (F-92's other cases, G-47 and G-80, label other sections) | F-92's value on the scanned page is not reproduced by this Mac's OCR | C2 |
| S4b-L3 | medium | the TEST-PLAN cells | GV9's Golden case cells not yet derived from v2 (open work, not a call) | done below, but R-22 |
| S4b-L4 | low | none | R-22's metadata is stale under D3 (the answer key's `tested_in`, TEST-PLAN's gaps row) | C3 |
| S4b-L5 | low | G-79 (F-84), G-111 (F-83) | two background features used as location holders on refuse cases, so R-11 is traced to two refuse-and-help cases | C4 |
| S4b-L6 | low | G-57 | the datasheet's known limit on G-57 states a refusal the code does not make: publish spares a clean run's plain attack phrase (S4's D3), so no check fires on G-57 in a clean run | C5 |
| S4b-L7 | low | G-51 | its reference states a derived value without its step (D-02) | C5 |
| S4b-L8 | info | G-52, G-65, G-66, G-67 | rule 7's missing twins and G-52's route, as the datasheet documents; accept | none |
| S4b-L9 | info | G-107 | the version-history kind's only case is in test; worth a line in the datasheet's splits | none |
| S4b-L10 | info | F-89, F-91, F-92, F-97 | the multi-topic features cause no labelling or traceability problem | none |
| S4b-L11 | info | the datasheet | placeholders to fill before F: the S4b part of "Second labeller and agreement" and the v2 result in "Splits" (after C1) | none |
| S4b-L12 | info | G-57, G-67, G-87, G-78, G-52 | the author's flagged points answered: G-57 by S4b-L6; G-67, G-87 and G-78 agreed; G-52 accepted; the multi-topic features by S4b-L10 | none |

Its other checks at `8b5fcdd`: check-dataset passes both files; the author's rules 2 to 11 hold
(S2's overlap 4, 4 and 4 words; no planted string; SPEC section 9; silence proofs; 9 of the 18 new
abstain cases near-miss; tenant B in its own words; the split re-derived equals the committed file;
no email, register id or phone number in a new case); of the 185 values the cases' features cite at
their labelled sections, 184 are in the chunk text (the one not is S4b-L2); the answer key's
additions only, with 50 new values verbatim at their Markdown locations. The ledger's note for the
labels judge on G-57 (above) repeats the datasheet's sentence that S4b-L6 finds overstated; it is
corrected with call C5.

**The calls, pending the maintainer** (the options as the judge words them, case ids only):

- **C1, GV2 after the seeded split (S4b-L1).** (1) "Repair in the committed script (Recommended)":
  a second pass in `scripts/split_golden.py` after the main draw: for each first-feature kind with
  two or more cases in the whole file and none in dev, in a fixed order of kinds, the kind's
  lowest-numbered new test case moves to dev, and one new dev case of that case's stratum whose
  kind keeps a dev case without it, drawn with the seeded generator (which generator is written
  down first), moves to test; the script is run once more on the file with the new cases' splits
  removed and committed, and the ledger says the rule was written after the first draw was seen.
  Simulated by the judge: six splits change (G-40, G-78 and G-76 to dev; G-38, G-72 and G-83 to
  test), and the counts per slot, label and tenant, the floors and tenant B's test case under each
  label stay. (2) "Accept the gap as a known limit": GV2's dev clause reported not met for the three
  kinds, the coverage test's clause edited to the outcome, and the datasheet saying those kinds are
  measured only in nightly and release runs. Rejected by the judge: a new seed, a hand move, or
  replacing a dev case's content.
- **C2, F-92's scanned-page value (S4b-L2).** (1) "Shorten the value to the fragment both readings
  keep (Recommended)", with SPEC section 8's F-92 row; (2) "Keep only the route sentence at that
  location"; (3) "Normalise quote characters in the two ingestion comparisons".
- **C3, R-22's metadata under D3 (S4b-L4).** (1) "Update both now, metadata only (Recommended)";
  (2) "Leave until S8".
- **C4, the location-holder features on G-79 and G-111 (S4b-L5).** (1) "Drop F-84 from G-79 and
  F-83 from G-111, keep the labels (Recommended)", a golden-file edit before the sign-off (the
  file's sha256 and the v2 row change; the split does not); (2) "Accept and note in the
  datasheet"; (3) "Add the two sentences as new locations of F-41", without a side, and drop F-83
  and F-84 from the cases.
- **C5, two text edits before the sign-off (S4b-L6, S4b-L7).** (1) "Make both edits now
  (Recommended)": the datasheet's known limit on G-57 says what the code does, and the ledger's note
  with it; G-51's reference states its step; (2) "Leave as they are".

### S4b-L3 done: the Golden case column from v2 (`007c305`)

Every Golden case cell of TEST-PLAN section 8 now names v2's covering cases, derived from the
committed file and the answer key: the S4 cells gain v2's ids; R-08, R-09, R-13, R-15, R-16, R-17
and R-19 name their cases (R-15 and R-17 "(clean runs; the attack runs are S7's)", R-19 "(the
allow list; the deny list is S7's)"); R-06's by-design part names the four may_quote cases, G-26,
G-84, G-85 and G-93; R-11 is written as the data stands, G-79 and G-111 included (C4 may drop
them); R-22 is left "tbd (S4b)", pending C3. The section's opening says the cells come from v2.
The traceability test's R-06 check, the defect recorded at STOP 1, now holds the cell's by-design
part to the may_quote cases (`case_ids` of the text after "by design"), which allows G-93 to cover
R-06 by its feature too; dropping G-85 from that part, or moving G-26 out of it, is named. Run
after the change: `tests/unit/test_test_plan.py` "1 failed, 13 passed", the one failure
`test_the_golden_case_column_names_the_cases_that_cover_each_requirement` with one problem left,
"R-22: the cell is 'tbd (S4b)', not 'none: a gap, no planted feature (S4b, D3)'" (C3); the
planted-v2 test passes; `test_answer_key.py`, `test_repo_docs.py`, `test_onboarding.py` and
`test_diagram.py` "196 passed"; privacy "0 hits across 373 files".

Of the four tests failing at STOP 1, none passes yet: the two ingestion tests wait for C2, GV2's
test for C1, and the traceability test, down from 24 problems to 1, for C3. The datasheet's R-06
coverage row names G-26 alone by design and does not name G-84 and G-85; it was left with the
datasheet's other edits (S4b-L11, after C1).

## The maintainer's answers on the calls (2026-10-24)

The maintainer's answers, early on 2026-10-24, through the coordinator's question prompt, each
with its question, verbatim:

1. Question: "S4b C1: the seeded split put every case of three kinds in test (background;
   exception-overrides-rule; procedure, R-23), so dev runs would never measure them. How should it
   be fixed?" Answer: "Repair in the committed script (Recommended)".
2. Question: "S4b C2: this Mac's OCR misreads F-92's value on the scanned page, \"Do not change
   kiosk settings to keep a session open\", as \"Do ‘not…\", so two ingestion tests fail. What
   should the answer key cite?" Answer: "Shorten the value to the fragment both readings keep
   (Recommended)".
3. Question: "S4b C3–C5: three small fixes before your sign-off. C3: R-22's stale metadata is
   updated to say S8, per your earlier decision. C4: two background features that only hold
   locations on G-79 and G-111 are dropped, so R-11 isn't traced to refusal cases. C5: the
   datasheet's G-57 limit is corrected to what the code does, and G-51's reference answer gains
   its arithmetic step. Make all three as recommended?" Answer: "All three as recommended
   (Recommended)". That is C3 "Update both now, metadata only (Recommended)", C4 "Drop F-84 from
   G-79 and F-83 from G-111, keep the labels (Recommended)" and C5 "Make both edits now
   (Recommended)".

### C1: the second pass, written after the first draw was seen

**Said plainly: the second pass was written after the first draw was seen**, and after the labels
judge's simulation had named the six ids it expected to move. The first draw's output stays above
("The split"), as committed at `e91275c`. The pass is the labels judge's C1 option 1, in
`scripts/split_golden.py` (its docstring):

- After the main draw, for each first-feature kind (the answer key's kind of a behaviour case's
  first feature) with two or more behaviour cases in the whole file, v1.1's included, and none in
  dev, taken in the order of the kinds' names: (a) the kind's lowest-numbered new test case moves
  to dev; (b) among the new dev cases of that case's stratum (slot, label, tenant), those whose own
  kind would still have a dev case in the whole file after they moved are eligible; sorted by
  number and shuffled, the first moves to test. Each stratum keeps its count of test cases.
- **The generator, chosen and written down before the pass first ran: a fresh
  `random.Random(20261023)`, made once for the pass**, not the main draw's generator continued
  (the labels judge's simulation found the same six ids either way).
- The fixed order of kinds is their names, sorted. A kind with no new case to move, or a stratum
  with no eligible case, stops the script and nothing is written. The pass reads the kinds from
  the answer key (`raglab.ingest.answer_key`), so the script takes `--root`.

Tests (`tests/unit/test_split_golden.py`): on cases built in the test, the lowest-numbered new
test case of an all-test kind moves to dev and one eligible case of its stratum, drawn by a fresh
`random.Random(20261023)` computed again in the test, moves to test (a single-case kind's case, a
case of another stratum and the moved case are never eligible); a kind with a dev case, or of one
case, is left; the two stops; the pass through `split()` is seeded. The fixture and the GV6 test
pass the answer key's kinds. **One run before the commit:** the GV6 re-split test, run on the
committed file with the pass in place and nothing changed after, failed on 6 lines (the first,
"G-38: split dev, the seeded rule gives test"): the pass's first run, in memory, before the code
was committed; the code was not edited after it.

**The run** (`8c72231`). The pass was committed as `9b1eb19`; then the 80 new lines' splits were
taken out (which gave back the question author's bytes exactly, sha256 `154536a96941...`) and
the script was run once:

    (the main draw: the same 14 units and test draws as the first draw above)
    repair, background: G-40 to dev; G-38 to test (single-chunk / answer / tenant-a)
    repair, exception-overrides-rule: G-78 to dev; G-72 to test (multi-chunk / answer / tenant-a)
    repair, procedure: G-76 to dev; G-83 to test (multi-chunk / answer / tenant-a)
    split_golden: 80 new cases, 52 dev and 28 test (seed 20261023)

The six moved ids are those the labels judge's simulation expected: G-40, G-78 and G-76 to dev,
G-38, G-72 and G-83 to test. Every stratum kept its count of test cases, so the counts by mix
slot, label, tenant and split above are unchanged, and so is the design count of judge calls
(1,433; computed again). GV2's coverage test passes; the GV6 re-split test reproduces the file.

### C2 to C5, applied (2026-10-24)

| Call | What was done | Commit |
|---|---|---|
| C2 | F-92's value at A-DEVICE-B 1 is "not change kiosk settings to keep a session open", and SPEC section 8's F-92 row says the same; the second value at that location stays. The two ingestion tests pass again | `65ebbe9` |
| C3 | **A metadata-only edit:** the answer key's R-22 gap says `tested_in` S8, the suite audit, quoting D3; TEST-PLAN's gaps row and R-22's Golden case cell say the same, quoting D3; the traceability test's expected R-22 cell follows. No value, label, reference answer, side, canary or `answer_must_not_contain` list changed; no test reads `tested_in`. The answer-key comparison with `main` now reports the gaps as changed (this edit) and every feature change as an addition | `e4f5b52` |
| C4 | F-84 dropped from G-79 and F-83 from G-111, their labelled sections kept; the datasheet's R-11 row and its sentence on those labels, and TEST-PLAN's R-11 cell, derived from the data, no longer name the two refusal cases | `770a893` |
| C5 | The datasheet's known limit on G-57, and this ledger's note that repeated it (above), say what the code does; G-51's reference answer states its arithmetic step without the pass's end time | `5df18c6` |

The golden-file edits (C4, C5) were written as the split script writes its lines, so the re-split
test still reproduces the file.

### The datasheet completed (`1596e45`)

The S4b part of "Second labeller and agreement" (the seal, what the judge had, the numbers); the
Splits section for v2 (the rule, the second pass and when it was written, the 14 units with their
test cases, the dev and test counts by mix slot, label and tenant, and each new test case's
features and labelled sections shared with dev lines: 22 of the 28 share a feature, 18 a section);
G-107, the version-history kind's only case, in test (S4b-L9); R-06's coverage row naming the four
may_quote cases by design, as TEST-PLAN does; and the v2 Maintenance row with the final sha256,
`3d924ad0bd1dfcfe0f68cec70f595a570b7b412e875a3b5eae9ff901a3994a9e`, naming the edits made after
the review and before the sign-off (so still v2). `raglab check-dataset`: "check-dataset:
datasets/golden.v1.jsonl passes as v1.1 (34 retrieval questions, 40 behaviour cases, sha256
5f8cdaf18783)" and "check-dataset: datasets/golden.v2.jsonl passes as v2 (34 retrieval questions,
120 behaviour cases, sha256 3d924ad0bd1d)".

Left for later, not asked at this stop: the removal of the S4 table reading (no File column) with
its test, and of the skips of the v2 file's tests (both inert now that the datasheet has its File
column and the file exists); ONBOARDING's line naming both files; the README's and TEST-PLAN
section 10's v2 lines (GV13, with the runs).

## make -k check at STOP 2 (`1596e45`)

Run once on `1596e45`, a clean tree, this Mac (`make -k check`, 2026-10-24 at about 08:40 WEST):
**exit 2, and `audit` is the only red target**, pre-existing on `main` ("Found 8 known
vulnerabilities, ignored 43 in 3 packages": filelock 4.0.12 three times, fixed in 4.2.1; Pillow
12.3.0 twice; pypdf 6.19.0 three times). Every other target passes; the four tests that failed at
STOP 1 pass, and no test is skipped:

    256 files already formatted
    All checks passed!
    0 errors, 0 warnings, 0 informations
    Success! No dependency issues found.
    Found 8 known vulnerabilities, ignored 43 in 3 packages
    make: *** [audit] Error 1
    no leaks found
    no leaks found
    0 hits across 373 files (42 rules)
    0 architecture violations in src/raglab
    check-dataset: datasets/golden.v1.jsonl passes as v1.1 (34 retrieval questions, 40 behaviour cases, sha256 5f8cdaf18783)
    check-dataset: datasets/golden.v2.jsonl passes as v2 (34 retrieval questions, 120 behaviour cases, sha256 3d924ad0bd1d)
    ========== 1417 passed, 2 deselected, 1 warning in 204.18s (0:03:24) ===========
    retrieval no-regression gate (22 questions): recall@5 0.682 (n 22) passes: the threshold is the baseline 0.682 (20261019T180502Z-retrieval-dense-dev-97011a7) minus one question (1/22), 0.636
    api-smoke: passed

STOP 2: golden set v2 is ready for the review page and the maintainer's sign-off. Nothing has run
live, and the configs are still on v1.1 (they move at the freeze F).

## The sign-off on golden set v2 (2026-10-24)

On 2026-10-24 the maintainer's message was "ok". The coordinator asked, through the question
prompt, verbatim: "Is your "ok" the sign-off on golden set v2? Its review page has no ticks or
flags yet." The maintainer picked, verbatim, "Signed off as is", at about 09:55 WEST. The option's
description said that they would sign off `datasets/golden.v2.jsonl`, sha256 `3d924ad0…`, without
reviewing the cases; that the labels judge had agreed with all 80 labels; and that S4b's runs
would then start.

The file it names: `datasets/golden.v2.jsonl`, sha256
`3d924ad0bd1dfcfe0f68cec70f595a570b7b412e875a3b5eae9ff901a3994a9e`, checked with `shasum -a 256`
before F (the same).

**Said plainly: the maintainer signed off without ticking or flagging any case** on the private
review page (https://claude.ai/artifact/JFffRWigLDQGPjTPL7rhkx, built from `6da5a3e`; it holds
test-case text and stays private and uncommitted). The evidence behind the
sign-off is the labels judge's blind agreement (80 of 80, kappa 1.0000, chance agreement 0.3303)
and its review, with the maintainer's answers on its five calls applied (above). From here
`golden.v2.jsonl`, the answer key and the datasheet's v2 row do not change; a fix that edits them
goes back to the maintainer and runs every baseline S4b made again (the plan).
