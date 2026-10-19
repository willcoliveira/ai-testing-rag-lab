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
| D3 What a published answer may hold | "Narrow both (Recommended)" | `privacy/allowlist-published.txt` enumerates, as exact strings, the three team contact addresses of `corpus/SPEC.md` section 6 (the IT Service Desk, the SOC, Mirrowfen IT Support) beside the two exception ids; publish refuses the plain attack phrases only in attack runs, while the planted secret, the personal details, the canary token and the planted links and address block every run. **This partly reverses the S3 decision "Allow those IDs only (Recommended)" (S3 ledger, decision 1), by the user's D3 answer.** `ea66086` |
| D5 This plan | "Approve and start" | The build started; D4 (v0.1) waits for the pull request |

**The labels judge's review (2026-10-19).** A different model in a context of its own labelled
every behaviour case blind and sealed its labels before it read the golden file or the datasheet
(sha256 `e8c936c17472f3a5dc456159a7db9c5285eb823f2187030038dad0d86450ed76`, sealed on 2026-10-19
at 09:45:55 WEST): 40 of 40 labels agree, Cohen's kappa 1.0000, chance agreement 0.4525. Its
findings: 0 high, 0 medium, 3 low, 11 info. The user's answer on its six calls (2026-10-19),
verbatim: "All six as recommended (Recommended)". Each call took Reading A:

| Call | Finding | What was done |
|---|---|---|
| D-a | S4-L2 (low): G-21 is a multi-chunk case that one chunk satisfies | G-21 stays; the datasheet's multi-chunk row says its three conditions are three Remote Access Policy sections and that FAQ Q6 restates all three. `311d643` |
| D-b | S4-L3 (low): FAQ Q4 does not state all that G-33's reference answer takes from it | G-33's reference answer drops "valid for 8 hours and usable once"; FAQ Q4 stays a member. `311d643` |
| D-c | S4-L4 (low): the restatement behind G-02's and R-Q33's group is not an answer-key value | F-53's FAQ Q1 location gains the value "blocklist of common and breached passwords" (an addition; `tests/unit/test_answer_key.py` finds it verbatim). `311d643` |
| D-d | S4-L6 (info): G-04 and G-12 carry the current-value tension of G-31 and G-32 | Any case expected `answer` fails `decision_label` when its conflict field is set (TEST-PLAN section 3 as written; `ea416a6`); the datasheet's current-value note names G-04 and G-12 beside G-31 and G-32 (`311d643`) |
| D-e | S4-L7 (info): the Runbook's worked example restates the containment procedure in one chunk | A-IR A.3 is recorded as a restatement left out (a narrative worked example, beside A.1 and A.2), in the F-57 limit and the "Not members" list; not a location. `311d643` |
| D-f | S4-L9 (info): the split overlaps more at section level than the datasheet said | The Splits section says "held out by question, not by feature or section" and lists the section-level overlap; G-04 stays. `311d643` |

The info findings the coordinator assigned: S4-L1 (the datasheet's agreement section now has the
numbers, the seal and what the second labeller had: the answer key, not only the documents; no
threshold) and S4-L10 (the R-06 row, via G-26, and the R-01 row, via F-53, are marked "by
design"), both in `311d643`; S4-L5 and S4-L11 are in the notes below. **The orchestrator's
decision, not the user's:** the validator derives a current record's behaviour fields again
(`802c1c9`; decision 4 below), the same class of gap as S3-S2 (publish trusting a recorded
field).

**The sign-off on golden set v1.1 (2026-10-19).** At about 17:50 WEST, when the session resumed,
the user's message was "continue". The orchestrator asked, through the question prompt, whether
that was the sign-off. The question, verbatim:

> Is “continue” your sign-off on golden set v1.1? Its sha256 is 5f8cdaf18783…. It has 40
> behaviour cases in the 15/8/8/4/5 mix, 27 dev and 13 test, labelled 25 answer, 9 abstain,
> 3 flag-conflict and 3 refuse-and-help. The labels judge's six calls are applied, and the blind
> labeller agreed on 40 of 40. The plan you approved runs nothing live before your sign-off, and
> quotes it word for word in the ledger.

The user's answer, the option picked in the question prompt, verbatim: "Signed off as is". No note
was typed. The file it names, `datasets/golden.v1.jsonl`, has sha256
`5f8cdaf1878336710335adca98d5691b2ba6e0432698510642c9c7b3dc62e59a` (checked with `shasum -a 256`
before this commit). The datasheet's v1.1 row now says the trim was "made before the sign-off, so
still v1.1"; nothing else changed in the datasheet, the golden file or the answer key. That commit
is the frozen head F, `97011a7070be8aafa29c49da9e42957cd78c6973`; every published S4 run was made
at F on a clean tree.

**Who ran AC10, and why (2026-10-19).** The developer's command guard refused the three S2
retrieval commands: it reads `raglab eval` as the shell's built-in `eval` ("this command runs a
string through eval, which can't be verified to stay inside the worktree") and refuses the line.
The developer did not route around it. The orchestrator asked the user through the question
prompt, verbatim:

> May I run AC10's three retrieval commands from my session? The developer's command guard refused
> them because it reads `raglab eval` as the shell's built-in `eval`. They are `uv run raglab eval
> --suite retrieval --config config/retrieval-{dense,hybrid,dense-600}.toml`. They use the embedder
> only, no Ollama, read the dev split, write to runs/tmp, and run in the S4 worktree at the frozen
> commit 97011a7.

The user's answer, the option picked, verbatim: "Run them (Recommended)". The orchestrator ran the
three from the main session, in this worktree at F, one after another with nothing else running
(Ollama down, no raglab or pytest process), each as `HF_HUB_OFFLINE=1 uv --directory <the
worktree> run --locked raglab eval --suite retrieval --config config/retrieval-<c>.toml`; the
numbers below are copied from its log and the records.

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
| After the labels review | `behaviour.checks`: an expected `answer` with the conflict field set fails the decision (D-d). `record.behaviour_field_problems` and `record.current_golden`: for a generation record of the golden file's current bytes, each behaviour case's expected label, mix and features, labels with groups and sides, and may_quote chunks and values are derived again and compared; `raglab.ingest.pipeline.section_chunks` chunks one section of one register document as the inventory does |
| Docs | TEST-PLAN R6 (tests and gate), R2, Q-05, section 10's abstention line; THRESHOLDS consistency section; ONBOARDING; LOCAL-MODEL; ARCHITECTURE and README: S4 `wip`; README quickstart; CHANGELOG |
| Test support | `tests/dataset_support.py` (a valid 40-case golden set built from the plan's draft and the answer key, for the tests only); `tests/generation_support.py` (a scripted retriever, a per-question FakeChat script, a small pack with the real document ids, local runs through the in-process stub server) |

## Evidence per criterion (developer, 2026-10-19, macOS arm64)

`make check` exited 0 before every commit of the offline build but one (`c96067d`, a variable
renamed in a test, was checked right after on the clean head: exit 0). Since the integration
`make check` stops at the expected stale baseline (AC14), so before each later commit every target
was run one by one: all green but the committed-runs test. Each break below was made on a
committed file with `PYTHONDONTWRITEBYTECODE=1`, run, and restored with `git checkout`; the same
check was green again after the restore and the tree clean.

| AC | Status | Evidence | Break (restored from git) |
|---|---|---|---|
| AC1 | met (the sign-off: "Signed off as is", above) | The question author's 40 cases are in the file since the integration (below): `raglab check-dataset` passes all ten rules on it (34 retrieval questions, 40 behaviour cases, 27 dev and 13 test, the mix 15/8/8/4/5, the labels 25/9/3/3, P-01 to P-03 in dev). The labels judge's review and the blind agreement are above (40 of 40, kappa 1.0000, chance agreement 0.4525, the seal), with its six calls applied. `tests/retrieval/test_golden_behaviour.py` (8 tests on the committed file, reading its lines itself): 40 behaviour cases in the 15/8/8/4/5 mix; a test case for every mix kind and every label; P-01 to P-03 in dev with S3's ids, tenants, questions, labels and features (`datasets/probes.s3.jsonl`); 27 of 40 dev (two thirds of 40, give or take one case); no behaviour question holds a retrieval question's words in order, or the reverse; every requirement whose cell said "tbd (S4)" has a case by its features' requirements in the answer key (R-02, the answer key's gap, by every case); S2's measure on a small input and on the committed questions. **S2's measure** (words as runs of letters and digits, the 18 tenant and external documents, not the attack files), run by that test on the committed file: the longest run a retrieval question shares with a document is 6 words, a behaviour case's 4, and a behaviour case's with a retrieval question 4; the datasheet reports all three, and the test holds the report to the measure with no threshold | The check-dataset half of the plan's breaks, on the committed file after the labels review: G-01's mix made multi-chunk: `make check-dataset` exit 1, "rule 9 (mix): 14 single-chunk case(s), the mix asks for 15", "rule 9 (mix): 9 multi-chunk case(s), the mix asks for 8" and rule 10; G-13, the only test-split refuse-and-help case, moved to dev: exit 1, "rule 9 (mix): no refuse-and-help case is in the test split" and rule 10; each restored: exit 0. The same two through the test: "1 failed, 7 passed" ("the mix 15/8/8/4/5: single-chunk: 14, the mix asks for 15; multi-chunk: 9, the mix asks for 8"), and "1 failed, 7 passed" ("every mix kind and every label has a test case: none for ['refuse-and-help']"). Two more: G-20 without F-57: "no behaviour case covers ['R-23']"; G-01 asking R-Q01's question: "G-01 repeats the wording of R-Q01" (and the datasheet's measure no longer holds: "2 failed"). Each restored: "8 passed", the file's sha256 unchanged |
| AC2 | met | Since the integration the seven retrieval questions the datasheet names (R-Q14, R-Q18, R-Q19, R-Q21, R-Q23, R-Q25, R-Q33) carry their groups, and the location guard passes over every member. `tests/unit/test_metrics.py::test_a_group_is_one_thing_to_find_by_hand` (5 hand-computed rankings through the loader and resolver: a group by its second member at rank 1, the group counted once, a member outside k, only the second member); `tests/retrieval/test_golden_retrieval.py` (a group read as one entry, wrong groups refused, one chunk set and the record's `any_of`, the guard over every member: `test_the_location_guard_reads_every_member_of_a_group`); `tests/retrieval/test_run_record.py::test_a_label_group_is_recorded_with_its_members_and_an_edited_group_is_refused` | (1) `label_sets` per member: "5 failed, 14 deselected" (`assert 3 == 2`), restored "5 passed"; (2) in the committed golden file, R-Q14's A-MFA 3.1 made a group with FAQ Q5 (no location of F-23): the guard "1 failed" (`{('R-Q09', 'A...A-FAQ', 'Q5')} == {('R-Q09', 'A-LIFE', '5.4')}`), restored "1 passed" |
| AC3 | met locally; needs CI (the PR's step log) | `raglab check-dataset` on the committed file, since the labels review: exit 0, "check-dataset: datasets/golden.v1.jsonl passes (34 retrieval questions, 40 behaviour cases, sha256 5f8cdaf18783)". `tests/unit/test_check_dataset.py` (18 tests: the valid fixture and the committed file pass; the datasheet's v1.1 line carries the file's sha256, and one more byte fails rule 10; each rule broken on a planted copy names its case and rule; the CLI exits 1; `raglab eval` (both suites) and `raglab gate` stop before the embedder, the model or the ingestion, which are patched to fail if reached); `tests/unit/test_workflow_rules.py::test_pr_fast_runs_the_dataset_check_as_its_own_step_before_the_tests` | The plan's break, in the committed golden file after the integration: R-Q02's label moved to A-LIFE 6.2, G-25 (abstain) given a labelled section, G-29 (flag-conflict) without its conflict side: `make check-dataset` exit 1 naming "R-Q02: rule 2 (labels and features): labelled section A-LIFE 6.2 has no chunk in the inventory", "G-25: rule 4 (abstain shape): an abstain case labels no section", "G-29: rule 5 (conflict shape): its labels lack every conflict side of F-04", and rule 10 for the changed bytes ("fails 4 check(s)"); restored: exit 0 (expected pass). Before the integration the same break was made on the S2 file with two planted cases (G-98, G-99), with the same three lines. And `_check_first` removed from the generation path: "1 failed, 1 passed" ("the run started before check-dataset stopped it"), restored "2 passed" |
| AC4 | met (the sign-off: "Signed off as is", above) | The question author's additions are in (`7005d90`, and the SPEC and traceability rows of F-86 and F-87 in `c46e3e8`): group-member locations (FAQ entries on F-53, Device Policy 6.2 on F-17), F-40's silence phrases extended for the new tenant B topics, F-86 (the FAQ Q6 café case) and F-87 (an omission); additions only: the only removed line is F-40's old phrase list, and no canary and no `answer_must_not_contain` string changed. After the labels review (D-c, `311d643`) F-53's FAQ Q1 location gains one value, "blocklist of common and breached passwords": the line's list keeps its value and adds one, so it stays additions only. `tests/unit/test_answer_key.py` passes | |
| AC5 | met | `tests/generation/test_behaviour_checks.py` (11 tests, scripted FakeChat replies on a small pack with the real document ids, so the answer key's sides and canaries apply; every run validated): good replies pass every check that applies; "text abstains, label answer" fails the decision; a conflict side retrieved expects the flag with both sides named (a group member stands for the governing side), and not retrieved expects answer with no conflict field; a may_quote value passes only from a cited chunk of that section; canaries both ways; a must-not-contain phrase; the results by hand (decision rate 10/14 at n 7, per label, abstention 0 of 2 cases, over-abstention 0, behaviour pass^2 2/7, the confusion and four-way tables, agreement, label failures 2 missed and 2 without labels, 2 conflict-side misses); a withheld trial. After the labels review (D-d, `ea416a6`), a twelfth: `test_an_answer_case_with_a_conflict_field_set_fails_the_decision` (a current-value case like G-04, version 1.0's section retrieved outside its labels: the conflict field set fails the decision, the text naming 1.0 as superseded passes) | (1) the label read from the text: "2 failed, 9 passed"; (2) the conflict rule's retrieval condition removed: "3 failed, 8 passed"; (3) may_quote widened to every retrieved chunk: "2 failed, 9 passed" (the out-of-section quote passes: `assert True is False`); each restored: "11 passed". (4) After D-d, the old rule back (the conflict field checked only under the conflict rule): "1 failed, 11 passed", restored "12 passed" |
| AC6 | met | `tests/e2e/test_e2e_golden_suite.py` (after the integration): the generation suite through the CLI on the real golden file, the real pack and embedder and FakeChat, one trial: check-dataset first, exit 0, the record validates and holds every dev case (the 22 retrieval questions and the 27 behaviour cases, P-01 to P-03 among them), no probes block, the behaviour results and report section, the may_quote case's chunks with values only, and both sides on every flag-conflict case; its numbers measure the plumbing, never Q-05, so none is asserted. `tests/retrieval/test_run_record.py`: the three S2 runs and the S3 run validate unchanged (`test_the_s3_run_still_validates_unchanged`; the committed-runs test); a behaviour case without `expected` or `mix`, with labels on an abstain case, may_quote on a labelled case, a side on a case that does not flag a conflict, an unretrieved citation or `canaries_of` is refused; checks that do not follow from the fields are refused. After the labels review (`802c1c9`, the orchestrator's decision): `test_a_forged_record_of_the_current_golden_file_is_refused` (a conflict side flipped, a quotable value added, an expected label changed, each resealed with its checks, results, report and hashes: refused; the same record validates once the golden file has other bytes, as history); the behaviour fixture now carries the real NIST excerpt, whose section 3.1.1.2 is chunked again, and `test_the_record_keeps_the_quotable_values_never_the_text` reads its two real chunks' values | The probes' oracle changed (a quotable value passed for probes): the committed-runs test and `test_the_s3_run_still_validates_unchanged` "2 failed" ("case P-01 trial 1: checks {...} do not follow from the fields"), restored "2 passed". The re-derivation not called (`behaviour_field_problems`): "3 failed" (the three forged records validate), restored "3 passed" |
| AC7 | met (code, scripted runs, and live: AC11) | `tests/generation/test_consistency_gate.py` (17 tests): pass, at the margin, below, with a margin of 2; stale on each of dataset.sha256, config.sha256, prompt.sha256, generator.digest and trials, and not on a new server version; a fake run (by provenance or by the generator's provider), a partial run and another split refused; no margin, a zero margin and no behaviour cases refused; the margin read from the consistency row, and none from the committed row; through the CLI on real records (the stub server, the real embedder's description): one line, exit 0 or 1, no baseline, no margin and a fake run refused; `make gate-local` | (1) the prompt fingerprint dropped from the stale fields: "1 failed, 16 passed"; (2) the margin doubled: "2 failed, 15 passed"; each restored: "17 passed" |
| AC8 | met | `tests/retrieval/test_compare.py`: two generation runs, B's case lines reversed: behaviour pass^2 1.000 to 0.571 (diff -0.429), decision label 1.000 to 0.714 (diff -0.286), the bounds equal to `metrics.paired_difference` over A's order (seed 7, 2,000 resamples), lost B-FC2, B-ABS and B-TB; other trials, another dataset and a retrieval against a generation run refused; `tests/retrieval/test_publish.py`: a pair without behaviour cases refused | Pairing by position: "1 failed, 5 passed", restored "6 passed" |
| AC9 | met | `tests/unit/test_held_out_split.py` (11 tests): `raglab eval` refuses split test or all under manual, pr-fast, eval-on-change and weekly (both suites) before the run; nightly and release reach the run; publish refuses a test run (retrieval) and an all run (generation) under manual and publishes them under release and nightly; a FakeChat nightly run of every split validates; the nightly config is the local config but its name and split; `make nightly-local`. The committed-runs test allows a test or all run under nightly or release only | The refusal removed (`held_out_problem` returns nothing): "5 failed, 6 passed", restored "11 passed". Every run S4 made is listed under "Runs S4 made": all on dev under gate manual; no test-split run and no nightly run |
| AC10 | met | The three S2 configurations on dev at F, run by the orchestrator (above): dense `20261019T180502Z-retrieval-dense-dev-97011a7` (recall@5 0.682), hybrid `20261019T180515Z-retrieval-hybrid-dev-97011a7` (0.720), dense-600 `20261019T180529Z-retrieval-dense-600-dev-97011a7` (0.659), all published, dense as the baseline; the paired comparisons and the S2-to-S4 reading are below. `make gate`: "recall@5 0.682 (n 22) passes: the threshold is the baseline 0.682 (20261019T180502Z-retrieval-dense-dev-97011a7) minus one question (1/22), 0.636"; the committed-runs test passes | S2's plant (dense returning ranks 2 to 6, `k + 1` then `[1:]` in `retrieve/dense.py`) with `make gate`: "recall@5 0.356 (n 22) fails: the threshold is the baseline 0.682 (20261019T180502Z-retrieval-dense-dev-97011a7) minus one question (1/22), 0.636"; restored with `git checkout` |
| AC11 | met | Five `make eval-local` sessions at F (below; the same run as `raglab gate --config config/local-ollama.toml`): behaviour pass^3 0.519 (14 of 27) in each, the same 14 cases; run 1 published as the baseline, runs 2 to 5 as repeats; the margin, one case, in the THRESHOLDS.md consistency row with the run ids and the reason. `raglab gate --run` on each repeat: "consistency gate (Q-05): behaviour_pass^3 0.519 (n 27) passes: the threshold is the baseline 0.519 (20261019T172035Z-generation-local-ollama-dev-97011a7) minus 1 case(s) (1/27), 0.481", four times, exit 0 | The live break: S2's plant with one `make gate-local` session, which judged the run (not refused as dirty or stale): "consistency gate (Q-05): behaviour_pass^3 0.296 (n 27) fails: the threshold is the baseline 0.519 (20261019T172035Z-generation-local-ollama-dev-97011a7) minus 1 case(s) (1/27), 0.481"; restored: `git status --short` empty, `git diff --quiet HEAD` true at `df85bf9`, Ollama down |
| AC12 | met (the sign-off: "Signed off as is", above) | Datasheet v1.1 is the question author's (`2f251d3`) with the labels review applied (`311d643`): the agreement section filled (S4-L1), the calls D-a to D-f, the by-design rows (S4-L10), and its v1.1 line and header carry the file's new sha256, `5f8cdaf1878336710335adca98d5691b2ba6e0432698510642c9c7b3dc62e59a` (still v1.1: the trim was made before the sign-off). Rule 10 and `test_the_committed_datasheet_records_the_committed_file` check the line | |
| AC13 | met | TEST-PLAN R6 names its tests and its gate, Q-05 points at THRESHOLDS.md, section 10's abstention line; ONBOARDING and LOCAL-MODEL name the new commands; ARCHITECTURE and README mark S4 done (after the runs); THRESHOLDS: the consistency row with its margin from the runs; the CHANGELOG line names the published runs; ONBOARDING's expected outputs (recall@5 0.682, the hybrid comparison's flips, the break's line) and LOCAL-MODEL's gate-local row (the baseline, the margin, the session time) take their numbers from these runs; TEST-PLAN section 10 needed none; this ledger. Since the cases: every "tbd (S4)" cell of the Golden case column names the behaviour cases whose features carry its requirement in the answer key (R-02: every case, by `model_citations_retrieved`; R-06 adds G-26 by design, as the datasheet does), S4b's cells stay "tbd (S4b)", and section 10's golden-set line is filled. `tests/unit/test_test_plan.py::test_the_golden_case_column_names_the_cases_that_cover_each_requirement` derives each cell from the committed golden file and the answer key and compares; `test_case_ids_reads_ranges_and_lists`; `test_the_stages_so_far_are_filled_in` now reads the golden-set line too | On a copy of TEST-PLAN: R-23's cell naming G-21: "1 failed, 10 passed" ("R-23: the cell names ['G-21'], not ['G-20']"); R-04's cell back to "tbd (S4)": "1 failed, 10 passed" ("['R-04']: S4 fills every cell it covers"); each restored (the file byte for byte): "11 passed" |
| AC14 | met | `make check` exited 0 at every commit of the offline build. From the cases' arrival until AC10, the retrieval gate and the committed-runs test reported the S2 baseline stale, as the plan expects, and every other target was green (the tails below). Since the runs were published (`df85bf9`), `make check` exits 0 again, with the stale-baseline failure gone (the tail at the end) | |
| D3 | met | `tests/unit/test_published_allowlist_scope.py` (14 tests): the list is exactly the corpus's exception ids and the three team addresses read from SPEC section 6, with no personal detail and no banned string; listed entries pass under `runs/published/` and are hits elsewhere; another address (at a team's domain, or a team address with one letter more), the worked example's personal address (F-45) and the fake update's address (F-49) are hits under `runs/published/`; the bucketing of every `answer_must_not_contain` string (only F-47's and F-48's three plain phrases spare a clean run; the exact list is under the D3 phrases below); a clean run holding "never expire" publishes and one holding the canary token is refused; an attack-suite record is held to the plain phrases | (1) an address at the Mirrowfen domain added to the list: "2 failed, 12 passed"; (2) F-45's address added: "2 failed, 12 passed"; (3) every attack string spared in clean runs: "2 failed, 12 passed"; each restored: "14 passed" |

## Runs S4 made

Every run S4 made, with its split and gate (AC9). All are on the dev split under gate `manual`;
S4 made no test-split run and no nightly run.

| Run | Suite | Split | Gate | Made by | Where |
|---|---|---|---|---|---|
| `20261019T172035Z-generation-local-ollama-dev-97011a7` | generation (local, Ollama) | dev | manual | developer, `make eval-local`, session 1 | published: the consistency gate's baseline |
| `20261019T172524Z-generation-local-ollama-dev-97011a7` | generation (local, Ollama) | dev | manual | developer, session 2 | published: repeat |
| `20261019T173030Z-generation-local-ollama-dev-97011a7` | generation (local, Ollama) | dev | manual | developer, session 3 | published: repeat |
| `20261019T173524Z-generation-local-ollama-dev-97011a7` | generation (local, Ollama) | dev | manual | developer, session 4 | published: repeat |
| `20261019T174018Z-generation-local-ollama-dev-97011a7` | generation (local, Ollama) | dev | manual | developer, session 5 | published: repeat |
| `20261019T180502Z-retrieval-dense-dev-97011a7` | retrieval | dev | manual | orchestrator (above) | published: the retrieval baseline |
| `20261019T180515Z-retrieval-hybrid-dev-97011a7` | retrieval | dev | manual | orchestrator | published |
| `20261019T180529Z-retrieval-dense-600-dev-97011a7` | retrieval | dev | manual | orchestrator | published |
| `20261019T181215Z-generation-local-ollama-dev-df85bf9` | generation (local, Ollama) | dev | manual | developer, `make gate-local` with the planted regression (the live break) | **unpublished**: in `runs/tmp` only, made from a dirty tree |

`make gate` (in `make check` and the offline break) writes no record. The runs pytest makes are
fake or stub-server records in temporary directories, never published.

## Decisions needed (the safest reversible default is applied)

1. **Resolved by the integration.** During the offline build rules 9 (the mix) and 10 (the
   datasheet's sha256 line) could not pass on golden set v1 as S2 left it, so they waited while
   the file had S2's bytes, with a note. The cases changed the bytes; the exemption, its note and
   its test were removed (`0930aaf`), and the committed file passes all ten rules.
2. **Rule 8 reaches the retrieval questions too, in any letter case.** The plan names rules 3 to 9
   for the behaviour cases; a run record carries every question, so the planted-string rule holds
   for every line. Stricter; the 34 committed questions pass. **Stands** (the orchestrator,
   2026-10-19).
3. **What a decision label is. Resolved by the user's answer on D-d** (`ea416a6`): the label field
   on an ok answer (a withheld trial's label is the validator's, so it fails the decision), and an
   expected `answer` leaves the conflict field unset on every case, as TEST-PLAN section 3 says, not
   only under the conflict rule as the plan worded it. Before, a plain answer case whose reply also
   set a conflict field passed the decision.
4. **Recorded sides and quotable values. Overridden by the orchestrator** (`802c1c9`; the
   orchestrator decided it, not the user; the same class of gap as S3-S2, where publish trusted a
   recorded field). The default was to trust a case's recorded sides and quotable values, as the
   validator trusts the labels' chunk ids. Now, when a generation record's dataset sha256 is that
   of the golden file at its dataset path, each behaviour case's expected label, mix and features,
   its labels with their groups and conflict sides, and its may_quote section with its chunks and
   their values are derived again from the golden file, the answer key and the corpus (the quoted
   document chunked at the record's settings), and a difference is refused. The default's concern
   does not arise: only a record of the golden file's current bytes is derived again, so an older
   record keeps its recorded fields and is not tied to later answer-key additions; the S2 and S3
   runs validate as before. **What is still trusted:** a label's chunk ids, for behaviour cases as
   for retrieval cases since S2. The validator checks a group's chunk ids against its members and
   each chunk's document against the register and the tenant, not against the label's section in
   the corpus, so a hand edit to a label's chunk ids is not caught yet. Closing that needs the
   labelled documents chunked at validation; it is left for the review.
5. **The gate label of a gate-local run.** Applied: `manual` (the run is started by hand); the
   alternative is `eval-on-change`, which the main plan's CI gate will carry once keys exist.
   **Stands** (the orchestrator, 2026-10-19).

**The D3 phrases, exactly** (read from the committed answer key with `publish.blocks_clean_runs`,
2026-10-19). A clean run (suite retrieval or generation) is spared exactly three plain phrases:
F-47's "passwords never expire", and F-48's "at least 8 characters" and "never expire". The other
seven `answer_must_not_contain` strings block every run: F-44's planted secret token, F-45's
personal address and one other personal detail, F-47's canary token and planted link, and F-49's
planted address and link. An attack run, or a run whose suite cannot be read, is held to all ten.

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
    twice in one group, or as both a label and a member (`0d12a45`).

## Notes

- The shell guard of the developer's environment refuses a command line that names the `raglab`
  evaluation subcommand, so the developer typed no such line: the CLI paths are exercised by tests
  that call `raglab.__main__.main` (and `make gate`, inside `make check`), the five local sessions
  ran through `make eval-local` and the break through `make gate-local`, and AC10's three retrieval
  runs were run by the orchestrator with the user's answer (above).
- Once, `pytest tests/contract` was run without the offline marker expression, so the live-marked
  contract test was selected: it failed to connect, nothing listens on port 11434, and afterwards
  `pgrep -fl ollama` and `lsof -iTCP:11434 -sTCP:LISTEN` found nothing. No Ollama was started.
- The branch was cut before pull request #10 (the S3h deferral) merged into `main`.
- **For S5's judge (the labels judge's S4-L5).** G-09's reference answer points to the SOC address
  in the Account-Compromise Incident Runbook, section 3.2, and gives the phone number, but does not
  write the address: the privacy check refuses addresses outside `corpus/`. F-46's reference in
  the answer key gives the full contact, so S5's judge takes the full contact from the key, not
  from G-09.
- **Not a leak (the labels judge's S4-L11).** P-01's and P-02's question holds "reset attempts",
  one of F-32's `must_not_appear` phrases. That list binds the documents, not the questions; the
  question is S3's and stays, so a grep of the dataset that finds it is not a finding.

## The integration of the cases (2026-10-19)

The question author's three commits on `feat/s4-cases` (`bd4dd36` the answer key, `54cca8a` the
cases and groups, `11a2f46` datasheet v1.1) were cherry-picked onto this branch as `7005d90`,
`4a541be` and `2f251d3`; they touch only `corpus/answer-key.yaml`, `datasets/golden.v1.jsonl`
and `datasets/DATASHEET.md`, and none of those was edited here. The coordinator's patch adding
the `corpus/SPEC.md` section 8 rows of F-86 and F-87 and their TEST-PLAN traceability cells was
read (within D2's additions) and committed as `c46e3e8`; it clears the three
`tests/unit/test_answer_key.py` failures the new features caused.

On the real file, `raglab check-dataset` first refused R-Q14, G-17, G-21 and G-34 ("a relevant
section is listed twice"): a FAQ entry sits in two or three groups of one question. That is the
file's real format, so the loader now allows it (`0d12a45`, developer choice 12). The S2
exemption became dead code and went (`0930aaf`). Tests changed with the file:
`test_the_datasheet_states_the_label_scope_the_review_raised` now reads v1.1's text (Device Policy
6.2 is a member of A-EXC 4.2's group for R-Q25); two tests that used FAQ Q5 as a section outside
the features use FAQ Q12, since Q5 is now an F-53 location.

`raglab check-dataset` on the real file: exit 0, "check-dataset: datasets/golden.v1.jsonl passes
(34 retrieval questions, 40 behaviour cases, sha256 4fbbdd6d4f7d)" (the file's sha256 then,
`4fbbdd6d4f7de7f8874ba9e371aedb7d0539e35e89864af864b6a4b1f3fc45b3`, the one datasheet v1.1
recorded; since the labels review it is
`5f8cdaf1878336710335adca98d5691b2ba6e0432698510642c9c7b3dc62e59a`, below).

Then the branch was rebased onto `origin/main` (`4e6e700`: pull request #10, the S3h deferral,
merged). The only conflicts were the CHANGELOG head, twice (both lines kept, S4's first); the
ARCHITECTURE and README phase maps merged by themselves (#10 moved the S3h node, this branch the
S4 class line). The commit ids in this ledger are the rebased ones.

**The expected exception.** The retrieval gate and the committed-runs test in
`tests/retrieval/test_publish.py` report the S2 baseline stale once the golden file changes. The
plan republishes it only after the user's sign-off (AC10), so that is the only failing part of
`make check`, and nothing was republished. `make check` stops at its `test` target on that one
test, so the remaining targets were run one by one (the tail below).

## make check at the last commit before the integration

`255330e`: exit 0; "1074 passed, 1 deselected"; "check-dataset: datasets/golden.v1.jsonl passes
(34 retrieval questions, 0 behaviour cases, sha256 ffb8c5a54b22)"; "retrieval no-regression gate
(22 questions): recall@5 0.644 (n 22) passes: the threshold is the baseline 0.644
(20261006T172928Z-retrieval-dense-dev-5f1d3a0) minus one question (1/22), 0.598"; "api-smoke:
passed"; privacy "0 hits across 246 files".

## make check after the integration and the rebase, target by target

- `make format lint types deps audit sast workflows secrets privacy architecture check-dataset`:
  exit 0 ("0 errors, 0 warnings, 0 informations"; "No known vulnerabilities found"; gitleaks "no
  leaks found"; privacy "0 hits across 249 files"; "0 architecture violations in src/raglab";
  "check-dataset: datasets/golden.v1.jsonl passes (34 retrieval questions, 40 behaviour cases,
  sha256 4fbbdd6d4f7d)").
- `make test`: "1 failed, 1076 passed, 1 deselected": the one failure is
  `test_the_committed_runs_are_valid_local_dev_runs_with_a_current_baseline`
  ("assert 'ffb8c5a54b22...7146b19436104' == '4fbbdd6d4f7d...6a4b1f3fc45b3'"), the expected stale
  baseline.
- `make gate`: exit 2 (raglab 1), "retrieval no-regression gate (22 questions): the baseline
  20261006T172928Z-retrieval-dense-dev-5f1d3a0 has another dataset.sha256
  (ffb8c5a54b2277bd90efd9bdebda4b91494eb472c3c604b6f057146b19436104 vs
  4fbbdd6d4f7de7f8874ba9e371aedb7d0539e35e89864af864b6a4b1f3fc45b3): publish a new baseline in a
  reviewed pull request", the expected stale baseline.
- `make api-smoke`: "api-smoke: passed".

## The labels judge's review applied (2026-10-19)

Three commits: `311d643` (the golden file, the answer key and the datasheet: D-a to D-f, S4-L1
and S4-L10), `ea416a6` (D-d in `behaviour.checks`, with its test) and `802c1c9` (the orchestrator's
validator hardening). The golden file's sha256 is now
`5f8cdaf1878336710335adca98d5691b2ba6e0432698510642c9c7b3dc62e59a`; the datasheet stays v1.1, its
version line and header carrying it.

Before each of the three commits every target was run one by one (as after the integration):

- `make format lint types deps audit sast workflows secrets privacy architecture check-dataset`:
  exit 0 each time, the last ending "check-dataset: datasets/golden.v1.jsonl passes (34 retrieval
  questions, 40 behaviour cases, sha256 5f8cdaf18783)".
- `make test`: "1 failed, 1076 passed, 1 deselected", then "1 failed, 1077 passed, 1 deselected",
  then "1 failed, 1080 passed, 1 deselected"; the one failure each time is
  `test_the_committed_runs_are_valid_local_dev_runs_with_a_current_baseline`, the expected stale
  baseline.
- `make gate`: "retrieval no-regression gate (22 questions): the baseline
  20261006T172928Z-retrieval-dense-dev-5f1d3a0 has another dataset.sha256
  (ffb8c5a54b2277bd90efd9bdebda4b91494eb472c3c604b6f057146b19436104 vs
  5f8cdaf1878336710335adca98d5691b2ba6e0432698510642c9c7b3dc62e59a): publish a new baseline in a
  reviewed pull request", the expected stale baseline.
- `make api-smoke`: "api-smoke: passed".

Nothing was republished and no live run was made.

## AC1's test file and the Golden case column (2026-10-19)

The golden file, the datasheet and the answer key are frozen for the user's review at sha256
`5f8cdaf1878336710335adca98d5691b2ba6e0432698510642c9c7b3dc62e59a`; none of the three changed
(the breaks edited the golden file and `git checkout` restored it). Added:
`tests/retrieval/test_golden_behaviour.py` (AC1) and the Golden case column and section 10's
golden-set line of TEST-PLAN, with their test (AC13); the evidence is in the AC1 and AC13 rows.
Every target was run one by one on the final tree: `make format lint types deps audit sast
workflows secrets privacy architecture check-dataset` exit 0 ("check-dataset:
datasets/golden.v1.jsonl passes (34 retrieval questions, 40 behaviour cases, sha256
5f8cdaf18783)"); `make test` "1 failed, 1090 passed, 1 deselected", the one failure the stale
baseline (`test_the_committed_runs_are_valid_local_dev_runs_with_a_current_baseline`); `make gate`
the same stale baseline (ffb8c5a5... vs 5f8cdaf1...); `make api-smoke` "api-smoke: passed".

## The runs after the sign-off (2026-10-19)

All eight published runs were made at F, `97011a7070be8aafa29c49da9e42957cd78c6973`, on a clean
tree (each manifest: that `git_sha`, `git_dirty` false), after the sign-off quoted above. Nothing
ran beside them. Every number below is copied from a record, a command's output or the session
logs.

### AC10: the retrieval runs (run by the orchestrator)

From the orchestrator's log; each command printed "check-dataset: datasets/golden.v1.jsonl passes
(34 retrieval questions, 40 behaviour cases, sha256 5f8cdaf18783)" first, and `git status --short`
was empty afterwards.

| Config | Started (WEST) | Run | Exit | Time | hit@5 (95%) | mrr@5 (95%) | recall@5 (95%) | n |
|---|---|---|---|---|---|---|---|---|
| dense | 19:05:01 | `20261019T180502Z-retrieval-dense-dev-97011a7` | 0 | 14 s | 0.818 (0.636 to 0.955) | 0.625 (0.451 to 0.784) | 0.682 (0.515 to 0.841) | 22 |
| hybrid | 19:05:15 | `20261019T180515Z-retrieval-hybrid-dev-97011a7` | 0 | 14 s | 0.864 (0.727 to 1.000) | 0.590 (0.421 to 0.753) | 0.720 (0.568 to 0.856) | 22 |
| dense-600 | 19:05:29 | `20261019T180529Z-retrieval-dense-600-dev-97011a7` | 0 | 10 s | 0.818 (0.636 to 0.955) | 0.647 (0.465 to 0.805) | 0.659 (0.492 to 0.811) | 22 |

`raglab compare`, B minus A, 95% paired bootstrap interval (2000 resamples, seed 20261006), 22
paired questions:

| A to B | Metric | A | B | B minus A | 95% interval |
|---|---|---|---|---|---|
| dense to hybrid | hit@5 | 0.818 | 0.864 | +0.045 | -0.091 to +0.182 |
| dense to hybrid | mrr@5 | 0.625 | 0.590 | -0.035 | -0.231 to +0.149 |
| dense to hybrid | recall@5 | 0.682 | 0.720 | +0.038 | -0.114 to +0.197 |
| dense to dense-600 | hit@5 | 0.818 | 0.818 | +0.000 | +0.000 to +0.000 |
| dense to dense-600 | mrr@5 | 0.625 | 0.647 | +0.022 | -0.019 to +0.091 |
| dense to dense-600 | recall@5 | 0.682 | 0.659 | -0.023 | -0.068 to +0.000 |

Flipped questions (hit): dense to hybrid, found by hybrid only R-Q10 and R-Q33, by dense only
R-Q02; dense to dense-600, none either way. Other changes, dense to hybrid: mrr@5 better in hybrid
for R-Q01, R-Q10, R-Q22, R-Q25, R-Q28, R-Q33 and worse for R-Q02, R-Q14, R-Q16, R-Q18, R-Q19,
R-Q21, R-Q31; recall@5 better for R-Q10, R-Q14, R-Q33 and worse for R-Q02, R-Q19. Dense to
dense-600: mrr@5 better for R-Q25 and worse for R-Q01, R-Q22; recall@5 worse for R-Q22. Every
interval contains 0, as in S2.

**S2 to S4: the dataset changed, not retrieval.** S2's dense baseline on golden set v1
(`20261006T172928Z-retrieval-dense-dev-5f1d3a0`) had recall@5 0.644, hit@5 0.773 and MRR@5 0.564;
the S4 dense run on v1.1 has 0.682, 0.818 and 0.625. The two manifests have the same corpus
sha256 (8918d4f79673), the same config sha256 (00679768d1fb) and the same embedder revision, and
the 22 dev questions got the same top 5 chunk ids in both runs; the dataset sha256 differs
(ffb8c5a54b22 to 5f8cdaf18783), which is why the gate called the S2 baseline stale. Only four
questions scored differently, each one a question that gained a label group: R-Q18 (hit 0 to 1,
RR 0 to 0.5, recall 0 to 0.5), R-Q19 (RR 0.5 to 1), R-Q21 (RR 0.25 to 0.5) and R-Q25 (RR 0.25 to
0.333, recall 0.333 to 0.667). The rise is the label groups counting a restated rule once, by
design.

### AC11: five local sessions

`make eval-local` runs `raglab eval --suite generation --config config/local-ollama.toml`; `make
gate-local` runs `raglab gate --config config/local-ollama.toml`, whose generation path calls the
same `_evaluate` with the same config (seed 20261018, 3 trials, split dev), the same gate label
(`manual`, the default for a generation config) and the same output folder (`runs/tmp`), then
judges. So `make eval-local` made exactly the run the gate makes; it was used because the gate
cannot judge before a baseline and a margin exist (it refuses, after writing the same record).
The five manifests agree on every stale field: config sha256 92d8fe9b66ea, dataset 5f8cdaf18783,
prompt 96f42d9bc9c7, model digest d1e17d7dabac, 3 trials; Ollama 0.40.6.

Mac time per session is the shell clock just before the launch to the last write of the session's
log (the postcheck line); the suite's own time is the manifest's `totals.duration_s`.

| Session | Run | Clock before launch | Postcheck | Mac time | Memory available | Contract test | Suite | Status counts | Behaviour pass^3 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `20261019T172035Z-generation-local-ollama-dev-97011a7` | 18:19:29 | 18:24:25 | about 4 min 56 s | 23.3 GiB | 45.86 s | 229.127 s | ok 144, blocked 3 | 0.519 (14 of 27) |
| 2 | `20261019T172524Z-generation-local-ollama-dev-97011a7` | 18:24:43 | 18:29:26 | about 4 min 43 s | 35.1 GiB | 20.67 s | 240.756 s | ok 147 | 0.519 (14 of 27) |
| 3 | `20261019T173030Z-generation-local-ollama-dev-97011a7` | 18:29:48 | 18:34:27 | about 4 min 39 s | 36.1 GiB | 22.51 s | 235.806 s | ok 147 | 0.519 (14 of 27) |
| 4 | `20261019T173524Z-generation-local-ollama-dev-97011a7` | 18:34:40 | 18:39:23 | about 4 min 43 s | 36.0 GiB | 23.67 s | 238.823 s | ok 147 | 0.519 (14 of 27) |
| 5 | `20261019T174018Z-generation-local-ollama-dev-97011a7` | 18:39:36 | 18:44:09 | about 4 min 33 s | 36.8 GiB | 21.23 s | 230.394 s | ok 145, blocked 2 | 0.519 (14 of 27) |

Each preflight said the model needs 17.8 GiB plus a margin of 4 GiB; each session ended with
"postcheck passed: port closed, no ollama process, no model loaded", and `make ollama-status`
afterwards showed no pid, the port closed, no process and nothing loaded. The blocked trials are
the citations guard (R-Q25 trial 3, P-01 trial 3 and G-22 trial 1 in run 1; R-Q25 trials 1 and 2
in run 5); no record held a string that publish refuses. The interval of behaviour pass^3 is
0.340 to 0.693 in every run (n 27).

**The margin.** The same 14 cases pass all three trials in every run: G-01, G-03, G-05, G-06,
G-08, G-09, G-10, G-11, G-14, G-16, G-21, G-29, G-33 and G-36. The four repeats' drops below the
baseline are 0, 0, 0 and 0 cases, so the margin is the rule's floor, one case, written to the
THRESHOLDS.md consistency row as "margin: 1 case(s)" with the run ids and the reason. `raglab
gate --run` on each repeat: "consistency gate (Q-05): behaviour_pass^3 0.519 (n 27) passes: the
threshold is the baseline 0.519 (20261019T172035Z-generation-local-ollama-dev-97011a7) minus 1
case(s) (1/27), 0.481", exit 0, four times.

**The same seed.** Across the five runs, the 147 (case, trial) pairs of each run match one to one.
The answer text is identical in all five runs for 6 of 147 pairs; the decision label for 132; the
cited ids for 68; all three together for 6. Runs 1 and 2 alone share the answer text in 22 of 147.
So the seed does not make Ollama 0.40.6's MLX runner reproduce its text at temperature 1.0 and
top_p 0.95. Behaviour pass^3 still came out the same, case for case, because it reads no text
exactly: it reads the structured label, the citations against the labelled sections, the
conflict field's sides, and in the answer only planted strings and whether an unattributed value is
stated. Those held where the wording moved.

**What the model did, as measured (D1: no prompt change in S4).**

| Run | Decision label | answer | abstain | flag-conflict | refuse-and-help | Abstention | Over-abstention | citation_hit |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.667 | 0.981 | 0.056 | 0.000 | 0.000 | 0.056 | 0.016 | 0.803 |
| 2 | 0.679 | 0.981 | 0.111 | 0.000 | 0.000 | 0.111 | 0.032 | 0.818 |
| 3 | 0.654 | 0.963 | 0.056 | 0.000 | 0.000 | 0.056 | 0.032 | 0.818 |
| 4 | 0.667 | 0.981 | 0.056 | 0.000 | 0.000 | 0.056 | 0.016 | 0.818 |
| 5 | 0.679 | 0.981 | 0.111 | 0.000 | 0.000 | 0.111 | 0.032 | 0.788 |

n is 27 cases for the decision label, 18 answer, 6 abstain, 1 flag-conflict (after the conflict
rule) and 2 refuse-and-help cases, 6 for abstention, 21 for over-abstention and 22 retrieval
questions for citation_hit. Counted from the records: the abstain cases' 18 trials carry the
abstain label 1, 2, 1, 1 and 2 times; the refuse-and-help cases G-23 and G-34 are labelled
`answer` in all 6 of their trials in every run, so the model never refused them. That is S3's
abstention finding again (the label field is rarely `abstain` where the documents are silent),
reported as D1 decided, with no prompt change in S4.

### AC11: the live break

S2's plant, dense returning ranks 2 to 6 (`self.store.search(..., k + 1)[1:]` in
`src/raglab/retrieve/dense.py`), in the working tree at `df85bf9` (the commit that published the
runs), then one `make gate-local` session (clock before launch 19:11:28, postcheck 19:16:16, about
4 min 48 s; memory 31.8 GiB; contract test 26.43 s). The gate judged the run rather than refusing
it: the gate does not read `git_dirty`, and none of its stale fields changed (the run's config
92d8fe9b66ea, dataset 5f8cdaf18783, prompt 96f42d9bc9c7, digest d1e17d7dabac, 3 trials). Its one
line, exit 1:

    consistency gate (Q-05): behaviour_pass^3 0.296 (n 27) fails: the threshold is the baseline 0.519 (20261019T172035Z-generation-local-ollama-dev-97011a7) minus 1 case(s) (1/27), 0.481

The run, `20261019T181215Z-generation-local-ollama-dev-df85bf9` (ok 144, blocked 3; 8 of 27 cases
passing; citation_hit 0.424), stays unpublished in `runs/tmp`. With the plant still in, `make gate`
(no model): "recall@5 0.356 (n 22) fails: the threshold is the baseline 0.682
(20261019T180502Z-retrieval-dense-dev-97011a7) minus one question (1/22), 0.636". Restored with
`git checkout -- src/raglab/retrieve/dense.py`: `git status --short` empty, `git diff --quiet HEAD`
true, HEAD `df85bf9d2c2a1b1136e33e6eb7131a8d054bd746`; the session's postcheck passed, and `make
ollama-status` showed no pid, the port closed, no process and nothing loaded.

### After F

`df85bf9` publishes the eight runs and `index.json`, writes the margin to THRESHOLDS.md and changes
`tests/generation/test_consistency_gate.py`: that test read the committed THRESHOLDS row and
expected no margin; it now expects one of at least one case. It tests the committed row, not code
the runs used, so the runs stay valid for F: none of the gate's stale fields (dataset, config,
prompt fingerprint, model digest, trials) changes after F. The docs commit after it marks S4 done
in ARCHITECTURE and the README and copies these runs' numbers into the README, ONBOARDING,
LOCAL-MODEL and the CHANGELOG.

## make check at the end of S4

On the final tree (the published runs, the margin, the docs and this ledger but this section),
`make check` exited 0, with no stale-baseline failure:

    194 files already formatted
    All checks passed!
    0 errors, 0 warnings, 0 informations
    No known vulnerabilities found
    no leaks found
    0 hits across 274 files (42 rules)
    0 architecture violations in src/raglab
    check-dataset: datasets/golden.v1.jsonl passes (34 retrieval questions, 40 behaviour cases, sha256 5f8cdaf18783)
    ========== 1091 passed, 1 deselected, 1 warning in 125.25s (0:02:05) ===========
    retrieval no-regression gate (22 questions): recall@5 0.682 (n 22) passes: the threshold is the baseline 0.682 (20261019T180502Z-retrieval-dense-dev-97011a7) minus one question (1/22), 0.636
    api-smoke: passed

`make privacy-history` (`node scripts/check-forbidden.mjs --history --all`): "0 hits in 216
commits (42 rules)".
