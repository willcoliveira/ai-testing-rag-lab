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
  paraphrases the expiry rule could hold an attack phrase, and publish would refuse the run (the
  datasheet's known limits say so too). The author's own doubtful calls: G-67 (password reuse
  labelled refuse-and-help), G-87 (abstain), G-78 (answer), and G-52's weak route.

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
