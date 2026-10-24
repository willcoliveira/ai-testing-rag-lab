---
stage: S4b
name: golden-set-v2
nodes: [S4b]
date: 2026-10-23
branch: feat/s4b-golden-set-v2
status: approved
---

# S4b: Golden set v2, about 120 behaviour cases over both tenants

Part of the main plan (phase P2, release v0.2). Branch: `feat/s4b-golden-set-v2`, cut from `main`
at `2b9ba60`, answer-v2's merge. Build project stage 4 and how-to 17 step 4, as S4 was [H1, H2];
the method follows how-to 02, "Build a golden set" [H3]: size by failure mode (step 4), split and
freeze (step 5), the datasheet (step 6) and the version (step 7).

The main plan's row for S4b: "about 120 cases covering every question type and both tenants, with
every R-xx traced to at least one case; dev and test split kept; datasheet v2; `check-dataset`
passes; re-run of retrieval on v2 published". Its section "Golden set: 40 → 120" adds that the test
split "is never used to tune anything". S5 ran before S4b (the main plan's decision of 2026-10-20,
"S5 now, S4b after (Recommended)"), so v2's cases are written for the judge that now exists.

**The go for this plan (2026-10-23, about 22:10 WEST), verbatim.** Asked "answer-v2 is merged and
cleaned up. The main plan's next stage is S4b: golden set v2, about 120 cases, covering every
question type and both tenants. Start it?", you answered: "S4b planner now (Recommended)". The
approval of this plan is its last decision, D4, quoted under Approval when you give it.

## Where S4b starts

Counted at `2b9ba60` by a read-only script over `datasets/golden.v1.jsonl` and
`corpus/answer-key.yaml` that prints metadata only, never a question; run ids and values are
copied from the published manifests.

**Golden set v1.1**: `datasets/golden.v1.jsonl`, 74 lines, sha256
`5f8cdaf1878336710335adca98d5691b2ba6e0432698510642c9c7b3dc62e59a` (checked with `shasum -a 256`;
the datasheet's latest Maintenance row).

| Part | dev | test | tenant A | tenant B | Total |
|---|---|---|---|---|---|
| Retrieval questions (12 kinds) | 22 | 12 | 30 | 4 | 34 |
| Behaviour cases | 27 | 13 | 32 | 8 | 40 |

| Behaviour cases, expected label | dev | test | tenant A | tenant B | Total |
|---|---|---|---|---|---|
| answer | 17 | 8 | 23 | 2 | 25 |
| abstain | 6 | 3 | 3 | 6 | 9 |
| flag-conflict | 2 | 1 | 3 | 0 | 3 |
| refuse-and-help | 2 | 1 | 3 | 0 | 3 |

- The mix is the build project's 15/8/8/4/5 (single-chunk, multi-chunk, unanswerable,
  version-conflict, paraphrased or misspelled): 10/6/6/2/3 in dev, 5/2/2/2/2 in test. Two answer
  cases are must-not-block (G-12, G-33); one abstain case has `may_quote` (G-26). Every case is
  `origin: synthetic`.
- **Tenant B** has 8 behaviour cases, 6 of them abstain and 2 answer (one per split); none is
  flag-conflict or refuse-and-help. Tenant B has 4 retrieval questions (3 dev, 1 test).
- **The answer key** has 86 features (by clean-run label: 78 answer, 3 abstain, 2 flag-conflict, 3
  refuse-and-help). 33 are the first feature of a behaviour case. 31 are in no line at all: F-01,
  F-14, F-31, F-35, F-38, F-44, F-45, F-47 to F-49, F-55, F-58, F-63, F-64, F-66 to F-72, F-74,
  F-76 and F-78 to F-85. 19 are only in retrieval questions: F-06, F-09, F-11, F-13, F-18 to F-21,
  F-25 to F-27, F-34, F-36, F-37, F-60, F-61, F-65, F-73 and F-75.
- **Feature kinds that start no behaviour case:** cross-reference, glossary-dependent (and F-11's
  table-only, glossary-dependent), external-attribution, version-history, the three attack kinds,
  secret-in-doc, pii-in-doc, near-duplicate (F-53, which counts through label groups) and
  background (F-60 to F-85; F-62 and F-77 carry group members).

**Requirements**, by the lines whose features name them (a behaviour case counts every feature it
lists, as TEST-PLAN's traceability test does), dev/test:

| R-id | Behaviour cases | Retrieval questions | TEST-PLAN Golden case cell |
|---|---|---|---|
| R-01 | 10/5 | 7/1 | cases |
| R-03 | 6/3 | 0/0 | cases |
| R-04 | 2/2 | 3/1 | cases |
| R-05 | 2/1 | 2/1 | cases |
| R-06 | 1/0, and G-26 by design | 2/1 | cases |
| R-07 | 1/0 | 0/0 | cases |
| R-08 | 0/0 | 2/0 | tbd (S4b) |
| R-09 | 0/0 | 2/1 | tbd (S4b) |
| R-10 | 2/0 | 2/1 | cases |
| R-11 | 6/3 | 6/6 | cases |
| R-12 | 5/2 | 4/5 | cases |
| R-13 and R-16 | 5/2 | 3/1 | tbd (S4b) |
| R-14 | 4/1 | 0/0 | cases |
| R-15 | 0/0 | 0/0 | tbd (S4b) |
| R-17 | 0/0 | 0/0 | tbd (S4b) |
| R-18 | 3/2 | 2/1 | cases |
| R-19 | 1/0 (G-09, the allow list) | 0/0 | tbd (S4b) |
| R-22 | 0/0 | 0/0 | tbd (S4b); no planted feature |
| R-23 | 0/1 | 0/0 | cases |

R-02 applies to every case (`model_citations_retrieved`). R-20 and R-21 have no planted feature by
design (TEST-PLAN, "Gaps"): S3's API tests and S7's attack suite test them, not a golden case.

**What the runs measured where the set is thin** (counts copied from the S4 and answer-v2 ledgers
and the records; no test case's line was opened for this plan):

- **Abstention.** Under answer-v1 the 6 dev abstain cases' 18 trials carried the `abstain` label 1,
  2, 1, 1 and 2 times in S4's five runs. One case moves a dev rate by 3.7 points (1 of 27) and the
  abstain rate by 16.7 (1 of 6).
- **Refuse-and-help.** 2 dev cases, both labelled `answer` in every trial of every S4 run; one of
  them never retrieves its route sections, so no prompt can pass it (answer-v2 plan, "What the
  records add").
- **Flag-conflict.** 2 dev cases, and the conflict rule counts one: G-29's superseded side is never
  retrieved, so it expects `answer`. Every S4 run's flag-conflict decision rate was 0.000.
- **Superseded passages.** Over answer-v2's five runs, 21 trials cited only superseded passages
  (its observation (d): two retrieval questions and one answer case).
- **Over-refusal.** Under answer-v2 an answer case was labelled `refuse-and-help` in 9 trials of the
  four repeats (its observation (a)); the dev set has 2 must-not-block cases to measure it.
- **Tenant B.** 8 cases, 2 of them answers.

**Measured times**, the basis of every estimate below: a dev generator session under answer-v1 took
4 min 33 s to 4 min 56 s for 147 case-trials (S4 ledger: the suite 229.1 to 240.8 s, the live
contract test 20.7 to 45.9 s); under answer-v2, 3 min 50 s to 4 min 25 s (answer-v2 ledger). A
judge session on 147 case-trials took 56 min 52 s (S5's judge-v2 run, `duration_s` 3,380.41) and
54 min 52 s (answer-v2's, `duration_s` 3,257.091 for 605 judge calls). A retrieval run took 10 to
14 s (S4 ledger).

## Goal

- Grow the behaviour cases from 40 to 120, so that every question type the main plan and the answer
  key name has cases and both tenants have cases under every label the pack allows them. One case
  then moves the abstain, flag-conflict and refuse-and-help rates on dev by about 6 to 11 points,
  not 17 to 50 (at two thirds of the target counts below).
- Trace every requirement that has a planted feature to at least one case.
- Keep golden set v1.1 and its 20 published records valid and fully checked.
- Write v2 from the requirements and the answer key, review it independently, split it by a seeded
  rule before any run, and freeze it after your sign-off.
- Hold each version to its own contract in `check-dataset`.
- Republish the retrieval baseline on v2 and, under D1, the consistency baseline.

## Out of scope

| Item | Where it goes |
|---|---|
| Any change to the measure: the behaviour checks, the abstention oracle (its section-list false positive included), the gate's code, `raglab compare`, the run record and its schema | S8, with an oracle version so the published records keep validating |
| The judge: judge-v2, docs/CRITERIA.md, the canary set, `config/judge-local.toml` | frozen since S5; the judged baseline on v2 is D2 |
| A prompt change | a pull request after S4b, on v2's dev split |
| Cases on the planted secret and personal details (F-44, F-45: R-19's deny list) | S7, with the output guard: publish refuses any run that holds either, so one leak would block a baseline (S4's reason, unchanged) |
| Attack runs: whether the cases on F-47 to F-49 resist their attack files | S7; S4b writes their clean-run cases |
| A planted unresolved conflict (R-22) | D3 |
| More retrieval questions | not in S4b (Choices, row 5) |
| Any test-split run, and any test case's run results | the next nightly or release (v0.2) |
| The position test on v2 | not re-run; S5's record stays the position test's, on v1.1 |
| The cost assumptions and ADR-002 at v2's sizes | S8, which sizes the CI gates' slices |
| A tenant B flag-conflict case | none possible: the pack plants no tenant B conflict (SPEC section 9); a known limit |

## Golden set v2

### The file: `datasets/golden.v2.jsonl`, with v1.1 frozen beside it

- **v2 is a new file.** `datasets/golden.v1.jsonl` stays byte for byte (v1.1), and v2 is
  `datasets/golden.v2.jsonl`: v1.1's 74 lines unchanged, then the new behaviour cases.
- **Why a new file, not a new version of the same file.** The validator derives a record's labels,
  behaviour fields and reference answers again only while the file its manifest names still holds
  the bytes it was made from (`raglab.evals.record.current_golden`, read by `label_chunk_problems`
  and `behaviour_field_problems`; the judged record's `reference_problems` makes the same check).
  Rewriting `golden.v1.jsonl` would turn the 20 v1.1 records into history, whose labels and
  behaviour fields are taken as recorded: the gap S4-J2 closed for a current record. With v1.1
  kept, all 20 stay fully checked and can be re-run from the tree. The name also says what the
  file holds, as the main plan calls S4's set "v1" and S4b's "v2".
- **The cost of a new file:** every config that should run v2 names the new path, so its sha256
  changes with the dataset's (both are stale fields of the gates anyway), and the tests that read a
  golden file read both.
- **One datasheet**, `datasets/DATASHEET.md`, becomes datasheet v2. Its Maintenance table gains a
  File column: v1 and v1.1 (`golden.v1.jsonl`) and v2 (`golden.v2.jsonl`), the sha256 staying the
  last column so S4-J10's parse (a row ending in a backticked sha256) still reads it.

### Size and mix

"About 120 cases" counts behaviour cases: the main plan's "Golden set: 40 → 120" starts from S4's
40 behaviour cases (15/8/8/4/5), and its cost note scales a full run by 3×. The 34 retrieval
questions stay as they are (Choices, row 5), so v2 has 154 lines.

| Mix slot | v1.1 | v2 | New |
|---|---|---|---|
| single-chunk | 15 | 45 | 30 |
| multi-chunk | 8 | 24 | 16 |
| unanswerable | 8 | 24 | 16 |
| version-conflict | 4 | 12 | 8 |
| paraphrased or misspelled | 5 | 15 | 10 |
| **Total** | **40** | **120** | **80** |

| Expected label | v1.1 | v2, about | v2, at least (rule 9) |
|---|---|---|---|
| answer | 25 | 62 | 55, of which 8 must-not-block |
| abstain | 9 | 27 | 24 (the unanswerable slot), of which 3 with `may_quote` |
| flag-conflict | 3 | 13 | 12 |
| refuse-and-help | 3 | 18 | 14 |

- **Tenant B: at least 28 cases** (from 8), under answer, abstain and refuse-and-help.
- **Split:** the 40 keep theirs (27 dev, 13 test); the 80 new cases split about two thirds dev by
  the seeded rule below (about 53 and 27), so v2 has about 80 dev and 40 test behaviour cases. The
  generation suite's dev slice grows from 49 cases (147 case-trials) to about 102 (about 306).

Why this mix:

- **Size by failure mode.** How-to 02 step 4: "Start with about 30 cases per failure mode you care
  about, and grow the modes that stay noisy". 120 cases cannot give 30 to every mode, so v2 keeps
  the build project's shape, tripled (the mix S4 measured stays comparable), and inside it grows
  the labels the runs showed to be thin or noisy: abstain to about 27 (about 18 in dev, so one case
  moves the abstain rate by about 5.6 points instead of 16.7), flag-conflict from 3 to about 13,
  refuse-and-help from 3 to about 18, and their other side, must-not-block, from 2 to at least 8.
- **Both tenants.** Tenant B grows from 8 to at least 28, with answers on all seven of its answer
  features (F-34 to F-39, F-52) and refusals, not only abstentions.
- **Every question type.** Every feature kind of the answer key starts at least one case, except
  secret-in-doc and pii-in-doc (S7) and near-duplicate (F-53 counts through label groups, as in
  v1.1); a kind with two or more cases has one in dev.

### Where the new cases come from (a draft, by feature id)

A draft for the question author, by feature id only; the author may swap a feature within its row
while the coverage rules hold, and you sign off the final set. "New" marks an answer-key addition.

| Gap | Features | Label | Tenant |
|---|---|---|---|
| R-08 cross-references | F-18, F-19 | answer | A |
| R-09 the pack's definitions | F-11, F-20, F-21 | answer | A |
| R-06 attribution | F-13, F-14 | answer | A |
| R-04 history and the current value | F-04 (more wordings), F-05 to F-07 and F-58; new: a history feature for the version 1.0 values of F-05, F-06 and F-07 (sides old and new) | flag-conflict; answer | A |
| R-06 company against external | F-08 (more wordings) | flag-conflict | A |
| R-13, R-16 tenant B values | F-34 to F-39, F-52; new: the factors, the administrators' key and the composition rule of the Mirrowfen standards, and Mirrowfen IT Support's contact (must-not-block) | answer | B |
| R-03, R-13 tenant B silence | F-40 on new topics (its phrases extended), F-32 | abstain | B |
| R-03, R-18 omissions | F-32, F-87; new: tenant A omission features, each with a silence proof | abstain | A |
| D-03 attributed quotes | G-26's shape on new topics where the asker's pack is silent and a shared excerpt states a value | abstain (`may_quote`) | A, B |
| R-14 refusals | F-41 to F-43 in new wordings; new: bypass topics from R-14's list (sharing a factor, working around device management, the USB block, a tenant B request to skip MFA, its route the Mirrowfen standard's recovery section) | refuse-and-help | A, B |
| R-14 must-not-block | F-54, F-55, F-56; new: the exceptions process asked plainly, break-glass use; F-52 for tenant B | answer | A, B |
| R-10 multi-hop | F-22, F-23 (F-65 beside F-22, as R-Q15 has it) | answer | A |
| R-05, R-07 exceptions and in-text exceptions | F-15, F-16, F-17, F-51 (F-50, F-84 as background) | answer | A |
| R-23 procedures | F-57 again, in dev: R-23's only case (G-20) is in test | answer | A |
| R-12 formats, R-11 numbers | F-09 to F-12 (the PDF table), F-33 (the scanned page), F-24 (HTML), F-31, F-60 to F-85 | answer | A |
| R-15, R-17 clean-run controls | F-47, F-48, F-49 first, labelled with the governing rule's sections through a second feature | answer (F-49's attack-run label stays in the key) | A |
| R-19 the allow list | F-46 and the tenant B contact | answer | A, B |

The additions come to about 15 to 20 new features (an estimate from the rows above).

### Rules for the question author

S4's rules hold (1 to 6, 9 and 11), and v2 adds three (7, 8 and 10):

1. **Write from the requirements and the answer key, never from a model's output.** The author's
   inputs are the answer key, corpus/SPEC.md sections 6 to 9, TEST-PLAN sections 2, 3 and 7 and the
   register documents. The author opens nothing under `runs/` and no ledger's trial quotes, and the
   ledger lists what the author was given.
2. **No repeats.** No question repeats a line's question for the same tenant (rule 1). S2's measure
   is reported, with no threshold: the longest run of words a new question shares with a document,
   with a retrieval question and with another case. In v1.1 a behaviour case shared at most 4 words
   with a document and 4 with a retrieval question.
3. **No planted strings.** No question holds an `answer_must_not_contain` string or a canary of the
   other tenant, in any letter case (rule 8).
4. **SPEC section 9 binds the cases.** No case turns on an exception's dates (its Status decides,
   D-01); no case says a standard account can be locked within 15 minutes of the first failure; the
   kiosk sign-out and the screen lock are an accepted difference; NIST's and the NCSC's ranges are
   attribution, not conflict.
5. **Silence is proven.** An abstain case names a feature whose silence covers the asker's tenant
   (rule 4); a `may_quote` section is a shared reference section (D-03).
6. **The label fits the question** (TEST-PLAN section 3). A flag-conflict case asks about the
   difference: what an older version said, whether the rule changed, whether external guidance
   agrees. A current-value case labels the current version only.
7. **Refusals have twins.** A refuse-and-help case asks for a step R-14 names as a bypass and labels
   the route a passage states. Each bypass topic gets a must-not-block twin where the pack has a
   sanctioned route: the route asked plainly, labelled `answer`.
8. **Near-miss omissions.** At least a third of the new abstain cases ask about a topic next to a
   planted value (another event, kind of account or system): the shape R-18's acceptance names
   ("omission questions produce no number"). The review page shows that neighbouring value.
9. **Tenant B in its own words.** Tenant B cases use Mirrowfen's words, and a tenant A counterpart
   exists in the pack, so a leak would show.
10. **No split while writing.** The author writes every case without a split; the seeded rule
    assigns it afterwards.
11. **No email address, phone number or exception-register id** in the file: the privacy check
    refuses them outside `corpus/`, as in v1.1 (contacts by role and section).

F-57's limit stays: its procedure is seven sections, more than k = 5, and S4b tunes nothing for it.

### Answer-key additions

S4's D2 answer, "Additions only (Recommended)", applies again:

- **Added:** new features from F-88 onward, each with its SPEC section 8 row, its locations with
  verbatim values, its clean-run label and its requirements; new omission features with
  `must_not_appear` phrases; F-40's phrase list extended for the new tenant B topics, as S4 did; new
  locations on existing features only without a side.
- **Unchanged:** every existing feature's values, label, reference answer and sides; the `canaries`;
  every `answer_must_not_contain` list. The validator reads the answer key live for every published
  record, so a changed side or canary could make a v1.1 record invalid; the committed-runs test is
  the guard.
- **Signed off** with the golden set.

### The split: seeded, stratified, decided before any run

- v1.1's 74 lines keep their splits.
- The 80 new cases are split by a committed script (for example `scripts/split_golden.py`) with
  seed 20261023, written here before any case exists. Within each stratum (mix slot, expected
  label, tenant), sorted by id and shuffled with the seed, one third (rounded) goes to test; a
  stratum of one or two cases is pooled with its label's other strata, so that every mix slot,
  every label and each tenant has test cases. The developer runs it once on the author's cases, and
  a test runs it again and compares.
- It runs before the labels judge and before any run.
- **dev** is for development, the baselines, the gates' margins and any later prompt work. **test**
  runs only in nightly, release and the capstone. A test case ever used to tune anything moves to
  dev, a new case replaces it, and the version goes up.
- **Held out by question, not by feature or section**, as in v1.1: a test case can share its feature
  or section with dev lines, and the datasheet lists that overlap.
- **Test cases stay unused for tuning.** S4b makes no test-split run. This plan, the ledger and the
  pull request give test cases by id and count only, never their text. The labels judge and you
  read them to label and review them, which is not tuning. No published test-split result is read
  for S4b.

### The labels judge

As in S4: a different model (Fable 5.1) in a context of its own.

1. It labels the decision of each of the 80 new cases blind, from the id, the tenant, the question
   and the answer key, and seals its labels (sha256 and time) before it opens the golden file or the
   datasheet.
2. It then reviews each new case against the chunk text and the answer key: the label, the
   sections and groups, the reference answer, the stratum, the R-ids and the rules above.
3. The agreement (matches of 80, Cohen's kappa, chance agreement), each disagreement and each
   finding go to the ledger, and its calls come to you before the sign-off.

Lab practice: the second labeller is a model that has the answer key, which is weaker evidence than
a second person labelling from the documents (S4-L1); no agreement threshold is set.

### Your review page, the sign-off and the freeze

- **The review page.** The orchestrator publishes a private page, as for S4's sign-off. It shows the
  labels judge's disagreements and findings first, then the 80 new cases grouped by mix slot and
  feature, each with its tenant, split, label, reference answer, sections, groups and neighbouring
  value (rule 8). It also shows the answer-key additions with each value at its location, the
  datasheet's diff and the coverage tables. It holds test-case text, so it stays private and is
  never committed.
- **The sign-off** is quoted verbatim in the ledger with the file's sha256. From then on
  `golden.v2.jsonl`, the answer key and the datasheet's v2 row do not change. A fix that edits them
  comes back to you and runs every baseline S4b made again.
- **The freeze commit F** records the sign-off and switches the configs to v2 (below). Every S4b run
  is made at F on a clean tree. Between F and the commit that publishes the runs, `make check` fails
  only on the stale baselines (the retrieval gate and the committed-runs tests), as in S4; every
  other target passes, run one by one.

### Lab practice

- **Synthetic, one author.** Production samples real traffic first and fills the gaps with
  synthetic cases (how-to 02, steps 1 and 2); this pack has no traffic.
- **Below 30 per failure mode.** 120 cases still give most kinds fewer than how-to 02's "about 30
  cases per failure mode"; every run reports n and an interval.
- **A model as the second labeller**, with the answer key (above).

## check-dataset for two versions

- **Both files are checked.** `make check-dataset` (in `make check` and pr-fast's "Dataset check
  (hard stop)" step) checks `golden.v1.jsonl` and `golden.v2.jsonl`, each against its version's
  rules; `raglab eval` and `raglab gate` check the file their config names first.
- **Rules 1 to 8** are unchanged.
- **Rule 9, per version.** v1.1 keeps 15/8/8/4/5, a test case for every mix kind and label, and the
  S3 probes in dev. v2 has:
  - the mix 45/24/24/12/15;
  - the label floors above, must-not-block at least 8, and tenant B at least 28;
  - a test case for every mix slot, every label and each tenant, and a tenant B test case under
    every label tenant B has;
  - the S3 probes in dev.
- **Rule 10, per file.** The latest Maintenance row for the checked file's name carries its
  sha256.
- **The version a file is held to** comes from its Maintenance row. The developer chooses how, and
  says so in the ledger.

## What is pinned to v1.1, and what happens to it under v2

Found by grep at `2b9ba60`. **24 records are published: 20 name v1.1's sha256** (each in its
manifest) **and 4 name v1's**.

| Item | How it is tied to v1.1 | Under v2 |
|---|---|---|
| S2's three retrieval runs and S3's generation run (v1, `ffb8c5a54b22`) | history since S4 | unchanged; they validate as history |
| The retrieval runs at `97011a7`: dense (the gate's baseline, recall@5 0.682, n 22), hybrid (0.720), dense-600 (0.659) | the committed-runs test needs the baseline's dataset and config sha256 to be today's | re-run on v2 in S4b (GV10); v2's dense run becomes the baseline; these three stay published as v1.1 history, still checked in full |
| The consistency baseline `20261019T172035Z-generation-local-ollama-dev-97011a7` and its four repeats (behaviour pass^3 0.519, 14 of 27); THRESHOLDS.md's row, margin 1 case | the gate's stale fields; answer-v2's AV9 test, `test_the_committed_consistency_baseline_is_current` | D1 |
| The v0.1.0 test slice at `2c6aa85`: retrieval (recall@5 0.792, n 12) and generation (behaviour pass^3 0.308, 4 of 13) | the release's measurement | kept as v1.1 history; S4b makes no test-split run; v0.2's release runs v2's test split first |
| The judged records `25ccc0d` (judge-v1) and `5aa0ec5` (judge-v2, the judged baseline), both on the consistency baseline, and `c14acb0` (answer-v2's) | their sources are v1.1 runs; their reference answers are derived again while v1.1 is current | kept and still checked; the judged baseline on v2 is D2 |
| The position run `f309594` and its judged record `9fa9004` | `config/position-local.toml` names v1.1 and ten case ids, which `test_position_contexts.py` derives from `golden.v1.jsonl` | kept; the position config stays on v1.1 (no re-run) |
| answer-v2's five runs at `64bfd78` | measured, not adopted | unchanged |
| S4-J10's and S4-J11's tests (`tests/retrieval/test_publish.py`) | every published run names a version of the Maintenance table; the table lists `v1` and `v1.1`, and the datasheet holds 3 distinct 64-hex strings | the v2 row is added; the expected versions and hash count are derived again from the committed datasheet, never bumped by hand |
| `tests/unit/test_check_dataset.py` | the latest version is v1.1; "34 retrieval questions, 40 behaviour cases" | per version: v1.1's expectations stay, v2's are added |
| `test_golden_behaviour.py`, `test_golden_retrieval.py`, `test_e2e_fake.py`, `test_eval_config.py`, `tests/dataset_support.py` | read `golden.v1.jsonl` | read both files, or v2 where a config is meant |
| `tests/unit/test_test_plan.py` | derives the Golden case column from `golden.v1.jsonl`; `S4B_CELLS` must say "tbd (S4b)" | derives from v2; S4b's cells are filled (GV9) |
| `tests/generation/test_answer_v2_words.py` | answer-v2's text against the 74 v1.1 questions | stays on v1.1: it guards answer-v2's frozen text; a future prompt's leak test reads v2 |
| `tests/unit/test_held_out_split.py` | the nightly and release configs must name the local config's dataset | the three generation configs move together (D1) |
| `tests/e2e/test_e2e_golden_suite.py` | runs `config/fake.toml`'s dev split | v2 |
| docs/CRITERIA.md and `datasets/canaries.judge.jsonl` | frozen; their sha256 in every judged manifest; CRITERIA.md names v1.1's design count, G-09 and P-01's passages in prose; each canary carries its own question and chunk ids | unchanged; no run reads a case id from them; P-01 keeps its id and question in v2 |
| `config/judge-local.toml` and `tests/judge/test_answer_v2_one_judge.py` | the file's sha256 is in `5aa0ec5`'s manifest | unchanged under D2's recommended option |
| `config/cost-assumptions.toml` and ADR-002 | v1.1's sizes (49, 74 and 25 cases), quoted by `make cost` | unchanged (Out of scope) |
| The Pages playground | renders every published run, with each run's dataset path and question count | no change: v2's runs appear beside v1.1's under their own path |
| README, ONBOARDING, LOCAL-MODEL, TEST-PLAN section 10 | S4's numbers and lines | updated from S4b's runs; v1.1's kept where named as history |

**How both stay valid.** The committed-runs test validates every published record: the v1.1 ones
against `golden.v1.jsonl`, still their bytes, so derived again in full, and the v2 ones against
`golden.v2.jsonl`. S4-J10's test finds each record's sha256 in the Maintenance table (v1, v1.1 or
v2). The retrieval gate and AV9's test read only the current baselines, which S4b makes on v2.

## The runs S4b makes, and which runs each check reads

answer-v2's lesson: a plan names, for each check, the runs it reads.

| Run | Made by | Split, gate | Published | Read by |
|---|---|---|---|---|
| Three retrieval runs at F (dense, hybrid, dense-600) | developer, a `make` target (no model) | dev, manual | all three; dense as the baseline | GV10: `make gate` reads the dense run; `raglab compare` reads dense against hybrid and dense against dense-600; the unchanged-questions reading reads these three and v1.1's three |
| Five generation runs at F (D1, option A) | developer, `make eval-local` | dev, manual | all five; run 1 as the baseline | GV11: the baseline is run 1, whatever its value. The margin reads runs 2 to 5 against run 1. `raglab gate --run` reads each of runs 2 to 5. Publish reads all five, and so does the same-seed reading. The shared-cases reading reads run 1 and A only |
| The developer's live break | `make gate-local` with S2's plant | dev, manual | no (`runs/tmp`, a dirty tree) | GV11: the gate's one line |
| The criteria judge's live break | the same | dev, manual | no | its verdict on GV11 |
| One judge session (D2, option B only) | `make judge-local RUN=<run 1>` | dev | yes | GV12: the judged record of run 1 |

No other run. No test or all split. The retrieval and generation runs are all made at F before any
is published, and one commit publishes them. A refused publish (a planted string, a partial run)
leaves its run in `runs/tmp`, the ledger says why and the stage pauses for you. Nobody edits a
record or runs again in the hope of a run that passes (S4's rule).

## What gets built

```
datasets/golden.v2.jsonl         v1.1's 74 lines unchanged, then about 80 behaviour cases (G-38 on)
datasets/golden.v1.jsonl         unchanged (v1.1, frozen)
datasets/DATASHEET.md            datasheet v2; the Maintenance table with a File column
corpus/answer-key.yaml,          additions only: features F-88 on, F-40's phrases, their SPEC rows
  corpus/SPEC.md
src/raglab/evals/dataset_check.py   rules 9 and 10 per version and per file
src/raglab/__main__.py           check-dataset over both files by default
scripts/split_golden.py          the seeded, stratified split of the new cases
config/*.toml                    at F, the dataset path to v2: fake, retrieval-dense, -hybrid,
                                 -dense-600 and, under D1 A, local-ollama, -nightly, -release;
                                 position-local stays on v1.1
Makefile                         check-dataset over both files; one target for the three retrieval
                                 runs on dev
tests/                           v2's file test, the coverage test, the v1.1-current test and the
                                 split test; the dataset tests over both files; S4-J10, S4-J11 and
                                 the traceability test read v2
runs/published/                  three retrieval runs; five generation runs (D1 A); one judged
                                 record (D2 B only)
docs/                            TEST-PLAN, THRESHOLDS, ONBOARDING, LOCAL-MODEL, ARCHITECTURE, README,
                                 the main plan's notes; CHANGELOG
docs/plans/2026-10-23-s4b-golden-set-v2-ledger.md   the ledger
```

The file and target names are suggestions; the developer may choose others and says so in the
ledger.

## Choices I made (you can change them)

| # | Item | Choice | Why |
|---|---|---|---|
| 1 | The file | `golden.v2.jsonl`, with `golden.v1.jsonl` frozen | v1.1's 20 records stay fully checked (`current_golden`) and can be re-run from the tree |
| 2 | What "about 120" counts | behaviour cases, 40 → 120 | the main plan's "40 → 120" starts from S4's 40 behaviour cases, and its cost note scales a run by 3× |
| 3 | The mix | the build project's, tripled (45/24/24/12/15), with label and tenant floors | keeps S4's shape; how-to 02 step 4 grows the noisy modes |
| 4 | v1.1's 40 cases | kept unchanged in v2, ids and splits included | no relabel; the 27 shared dev cases give a reading across versions |
| 5 | Retrieval questions | the 34 stay as they are | the retrieval gate's one-question margin was measured on these 22 dev questions (S2's CI against Mac comparison); the behaviour cases exercise retrieval in the generation suite; review time |
| 6 | The split | about two thirds dev; seed 20261023; strata of mix slot, label and tenant; the author writes blind to it | S4's rule; nobody chooses which case is held out |
| 7 | The answer key | additions only | S4's D2 answer; the published records are validated against the key live |
| 8 | F-44, F-45 | left out again, to S7 | one leak would block a baseline; S7 brings the output guard |
| 9 | F-47 to F-49 | clean-run cases (answer), F-49's attack-run label kept in the key | traces R-15 and R-17 to cases now; the attack behaviour is S7's |
| 10 | Cost | `config/cost-assumptions.toml` and ADR-002 unchanged | S8 sizes the CI slices; ADR-002's choice (local only) does not depend on the sizes |
| 11 | The position test | its config stays on v1.1 | S5's record is the position test's; a re-run is not S4b's |
| 12 | answer-v2's leak test | stays on v1.1's 74 questions | it guards a frozen, unadopted text; a new prompt's leak test reads v2 |
| 13 | The retrieval runs | one `make` target for the three runs | in S4 the developer's command guard refused `raglab eval` lines, and the orchestrator ran them with your answer; the guard also refuses heredocs and some compound lines (answer-v2's ledger; this planner's session) |
| 14 | The review page | private, never committed | it holds test-case text |

## Acceptance criteria

Evidence marked **live** runs on your Mac through the `make` targets only (or `raglab ollama
session`), one model per session, on AC power, with nothing else running, never beside `make
check`; it stays out of `make check` and is recorded in the ledger. **[CI]** marks what only the
pull request's checks prove. Each break is made on a committed file, at the head the criteria
judge gives its verdict on, and restored from git; "expected pass" marks a break that must not
trip its check.

| # | Criterion | Evidence | Break |
|---|---|---|---|
| GV1 | **Golden set v2.** `datasets/golden.v2.jsonl` holds v1.1's 74 lines unchanged (every field) and 80 new behaviour cases from G-38, ids never reused: 120 behaviour cases in the mix 45/24/24/12/15, and the 34 retrieval questions; every new case `origin: synthetic`; no question repeated for the same tenant; S2's word-overlap measure reported | a test of v2 (for example `tests/retrieval/test_golden_v2.py`) reading both files itself; the ledger | one v1.1 line edited inside v2 (its split flipped): the test fails naming the case; a new case given an existing id: rule 1 names it |
| GV2 | **Coverage.** Every requirement with a planted feature has a behaviour case by its features, R-08, R-09, R-13, R-15, R-16, R-17 and R-19 newly; R-02 every case; R-20 and R-21 none, by design; R-22 as D3 decides. Every feature kind starts a case but secret-in-doc, pii-in-doc and near-duplicate; a kind with two or more cases has a dev case, R-23 included. The label floors, must-not-block at least 8, tenant B at least 28 | a coverage test that derives all of it from the file and the answer key; the datasheet's tables | the cases carrying F-18 and F-19 re-pointed to another feature: the test fails naming R-08; R-23's dev case moved to test: it fails naming the procedure kind |
| GV3 | **v1.1 frozen, its records still checked in full.** `golden.v1.jsonl` byte for byte (`5f8cdaf18783…`); each of the 20 v1.1 records names a file that holds its bytes, so its labels, behaviour fields and reference answers are still derived again; all 24 published records validate; no published file changes but `index.json`, by publish | a test over the 20 v1.1 manifests (`record.current_golden`); the committed-runs test; `git diff --diff-filter=MD origin/main -- runs/published` | one byte appended to `golden.v1.jsonl`: the new test fails (20 records would fall back to history) and rule 10 names v1.1 |
| GV4 | **check-dataset, per version.** Rules 1 to 8 unchanged; rules 9 and 10 per version and per file, as above; both files pass; `make check-dataset` checks both; `raglab eval` and `raglab gate` check their config's file first; **[CI]** pr-fast's dataset step checks both | `tests/unit/test_check_dataset.py` (every v2 rule on a planted copy; v1.1's rules unchanged); the pull request's step log | in v2, one single-chunk case made multi-chunk: rule 9 names both slots; every tenant B test case of one label moved to dev: rule 9 names the label; v1.1's rules kept: its committed file still passes (expected pass); each restored, exit 0 |
| GV5 | **Answer-key additions only.** New features from F-88 with their SPEC rows; F-40's phrases extended; each new value verbatim at its location; each silence proof absent from its scope; no existing value, label, reference answer or side changed; `canaries` and every `answer_must_not_contain` list unchanged; every published record validates | `tests/unit/test_answer_key.py`; `git diff origin/main -- corpus/answer-key.yaml` in the ledger; the committed-runs test; your sign-off | F-04's version 2.0 location given side old: the committed-runs test fails on the v1.1 records, whose G-29 and G-30 labels are derived again; a new silence phrase that appears in its scope: the answer-key test fails |
| GV6 | **The split, seeded, and the test split held out.** v1.1's splits kept; the new cases' splits from the committed script and seed, assigned before the labels judge and before any run; about two thirds dev. Every run S4b makes is dev, the ledger listing each with its split and gate. No test case's text in this plan, the ledger or the pull request | a test that runs the script again and compares; the manifests; the criteria judge's scan of the ledger and the pull request for every test question (expected: none) | one new case's split flipped by hand: the script test fails naming it; `raglab eval` on v2's dev config with split test under gate manual is refused (expected refusal) |
| GV7 | **The labels judge, the sign-off and the freeze.** Blind labels sealed (sha256, time) before the judge opened the file; on the 80 new cases, the matches, Cohen's kappa, chance agreement and each disagreement; its findings and your calls; your sign-off, verbatim, with the file's sha256; F recorded; every S4b run made at F on a clean tree with that sha256 | the ledger; the datasheet's agreement section; every S4b manifest (`git_sha` F, `git_dirty` false, the signed dataset sha256) | one label changed in a copy of the sealed labels: its sha256 no longer matches the seal in the ledger, and the agreement recomputed from it differs (the criteria judge's check) |
| GV8 | **Datasheet v2.** How-to 02's sections for v2: the mix by slot, label, tenant and split, the question types, the R-id coverage, the collection (one author, the inputs, the overlap measure), the agreement, the splits (seed, strata, the dev overlap of test cases' features and sections), CC BY 4.0, the Maintenance table with its File column (v1, v1.1, v2), and the known limits | S4-J10's and S4-J11's tests reading the new table; rule 10; review | the v2 row removed: S4-J10's test names every v2 run; a sha256 written in prose outside the table: still no version (expected pass) |
| GV9 | **TEST-PLAN traceability from v2.** The Golden case column derived from `golden.v2.jsonl`: S4b's cells name their cases (R-15 and R-17: clean runs, their attack runs S7's; R-19: the allow list, its deny list S7's); S4's cells derived again; R-22 as D3 decides; R-20, R-21 and the gaps table unchanged; section 10's golden-set line gives v2's counts | `tests/unit/test_test_plan.py` reading v2 and the answer key | R-08's cell back to "tbd (S4b)": the test fails; a case dropped from R-13's cell: it fails naming it |
| GV10 | **Retrieval re-run on v2** (no model). The three configurations on v2's dev split at F, through the `make` target; dense published as the baseline, hybrid and dense-600 beside it; both `raglab compare` readings in the ledger. The 22 dev questions are v1.1's, so each question's top 5 and each metric are set beside v1.1's runs, and any difference is explained: reported, not a stop. `make gate` passes; v1.1's runs stay; **[CI]** the pull request's gate line | `runs/published/`; `index.json`; the committed-runs test; the ledger | v1.1's dense run left as the baseline: `make gate` fails as stale; S2's plant (dense returning ranks 2 to 6): `make gate` fails |
| GV11 | **The consistency baseline on v2** (live; D1, option A). At F, five `make eval-local` sessions (answer-v1, dev ×3, the config's settings), all published, run 1 as the baseline, runs 2 to 5 as repeats. The margin is S4's rule. THRESHOLDS.md's consistency row is replaced in place (run ids, margin, reason), with v1.1's runs named as history. AV9's test passes on the new baseline. Reported: the same-seed reading, the 27 shared dev cases' pass^3 in run 1 beside A's, and the Mac times. Under option B: not applicable | `runs/published/`; THRESHOLDS.md; the gate's lines; the ledger | `raglab gate --run` on each repeat passes (expected pass); live: S2's plant with one `make gate-local` session fails against the new baseline; the old row left above the new one: the row test fails; the local config pointed back at v1.1 with v2's baseline in the index: AV9's test fails naming the dataset and config sha256 |
| GV12 | **The judge frozen; the judged baseline per D2.** No change to judge-v2, docs/CRITERIA.md, the canary set, `config/judge-local.toml` or `src/raglab/judge/`; the four judged records validate; the one-judge test passes. Option A: THRESHOLDS.md says the judged baseline stays `5aa0ec5`, on v1.1, until S6 judges v2's baseline; the ledger gives the design count of judge calls for v2's dev slice (a count from the frozen cases and CRITERIA.md's criteria per label, not a measurement). Option B: one judge session on run 1, its cap set before the run, its record published | `git diff origin/main` over those paths (empty under A); `shasum -a 256`; the ledger | CRITERIA.md given one more line: the one-judge test fails, and publish calls the judged records stale |
| GV13 | **Docs and the standing criterion.** TEST-PLAN (GV9); the datasheet (GV8); THRESHOLDS: the consistency row (D1) and the judged section (D2), the retrieval row's text unchanged; ONBOARDING: the check-dataset line for both files, the retrieval target and the expected outputs from S4b's runs; LOCAL-MODEL: v2's session times; README: golden set v2 and the new baselines; ARCHITECTURE and README: S4b `done` after the runs (`wip` until then); the main plan: a dated note for D2 if work moves to S6 and for D3 if R-22 waits; a CHANGELOG line; the ledger | `test_test_plan.py`, `test_diagram.py`, `test_readme.py`, `test_onboarding.py`, `test_repo_docs.py`, `test_changelog_check.py`; review | ARCHITECTURE's S4b class changed without the README's: `test_readme_status_matches_architecture` fails |
| GV14 | **`make check`, and [CI] pr-fast green.** No new runtime dependency; the retrieval gate passes; every published record validates; the dataset step checks both files | the `make check` tail in the ledger (`/usr/bin/time -p`); the pull request's checks | a planted lint error: `make check` stops at `lint` |

## Time

Every figure in this section is an estimate, with its basis.

### Your review tasks and time

1. **This plan**, with D1 to D4: about 30 to 40 minutes. Basis: S4's and answer-v2's plans
   estimated 30 minutes, S5's 40; none was measured.
2. **The labels judge's calls**, before the sign-off: about 15 minutes. Basis: S4's six calls were
   answered in one message.
3. **The sign-off of v2**, on the review page: about 2.5 to 3.5 hours. That is 80 new cases at about
   1.5 to 2 minutes each (2 to 2.7 hours), plus 30 to 45 minutes for the 15 to 20 answer-key
   additions and the datasheet. Basis: S4's plan rate, "about 2 minutes" a case, itself an estimate;
   the S4 ledger records the sign-off, not how long it took. **This is above the main plan's "about
   2–3 h" for S4b.** The page puts the judge's findings first and groups the cases by feature, and
   the review can take two sittings.
4. **Questions the ledger raises:** about 15 minutes.
5. **The pull request:** about 45 minutes (S4's and answer-v2's estimate).

In all, about 4 to 5 hours over the stage.

### Mac time (live sessions)

A generator session on v2's dev slice takes about 9 minutes. Basis: S4's answer-v1 sessions spent
1.56 to 1.64 s per case-trial in the suite, 20.7 to 45.9 s in the contract test and about 20 s
starting and stopping; applied to about 306 case-trials.

| Work | Sessions | Each | Total |
|---|---|---|---|
| The three retrieval runs (embedder only, no Ollama) | none | 10 to 14 s a run | under 1 minute |
| The five consistency runs (D1 A) | 5 generator | about 9 min | about 45 min |
| The developer's live break (D1 A) | 1 generator | about 9 min | about 9 min |
| The criteria judge's live break (D1 A) | 1 generator | about 9 min | about 9 min |
| **In all, D1 A and D2 A** | **7** | | **about 1 h 5 min** |
| The judged baseline (D2 B only) | 1 judge | about 2 h 10 min to 2 h 20 min | adds about 2 h 15 min |
| D1 B | none | | none |

The judge figure: a design count of about 1,450 calls for v2's dev slice (about 1,050 verdicts,
about 390 checks and the 19 canaries), from the target mix and CRITERIA.md's criteria per label.
At answer-v2's measured 5.38 s a call (3,257.091 s for 605 calls), that is about 7,800 s, above the
judged run's cap of 7,200 s in `config/judge-local.toml`.

Every session runs through the `make` targets or `raglab ollama session` only, one model per
session, on AC power: the power guard refuses on battery and stops a session that loses power,
publishing nothing. Nothing else runs beside a session, `make check` least of all: the memory
margin is thin. The session logs print no clock (answer-v2's AV2-J5), so the Mac-time tables rest
on the developer's shell readings, kept in the progress file.

### Agents' time

No ledger times a subagent on its own. These rest on the timestamps the ledgers do record:

- **S4, 2026-10-19:** the labels judge sealed its labels at 09:45:55; the sign-off was asked at
  about 17:50; the five sessions ran from 18:19 to 18:44 and the retrieval runs at 19:05.
- **answer-v2:** the offline build started at 09:46 on 2026-10-22, and its first live session at
  10:13. On 2026-10-23 the decision came at 11:29, and its criteria judge's live session ran at
  12:06.

| Role | Work | Estimate |
|---|---|---|
| Question author (Opus 5.5) | 80 cases, 15 to 20 answer-key additions, the datasheet draft | 3 to 4 h |
| Developer, offline (Opus 5.5) | check-dataset per version, the split script, the new tests, the tests over both files, the `make` target, the configs at F, the docs | 3 to 4 h |
| Labels judge (Fable 5.1) | 80 blind labels, then the review | 1.5 to 2.5 h |
| Developer, runs | the runs, publish, THRESHOLDS, the ledger, Mac time included | 1.5 to 2 h |
| Criteria judge (Fable 5.1) | the evidence again, the breaks, one live session | 2 to 3 h |
| Fix rounds | at most two | 1 to 2 h each |

The elapsed time is set by the waits for your review, above all the sign-off.

## How it will run

1. **Approval:** D1 to D4, quoted under Approval. From its first commit the developer keeps the
   ledger, `docs/plans/2026-10-23-s4b-golden-set-v2-ledger.md`: each criterion's evidence, every
   run, every finding and every answer of yours, verbatim.
2. **Build, offline** (developer, Opus 5.5), and **the cases, in parallel** (a question author, a
   separate subagent, as in S2 and S4). The developer builds the code, tests and docs of GV1 to GV6,
   GV8, GV9 and GV12 to GV14, with `make check` green; no live session. The author writes the
   cases, the answer-key additions and the datasheet draft by the rules above.
3. **The split:** the developer runs the seeded script once on the author's cases and commits the
   result.
4. **The labels judge** (Fable 5.1, a context of its own): the blind labels, sealed, then the
   review. Its findings go to the ledger, and its calls to you.
5. **Your sign-off** on the review page, quoted verbatim. Then the freeze commit F: the sign-off
   recorded and the configs switched to v2 (the position config stays on v1.1).
6. **The runs at F** (developer, `make` targets only, AC power, nothing else running). Every run,
   retrieval and generation, is made at F on a clean tree before any is published; one commit then
   publishes them all, as in S4, since a run made after a publish commit would not be at F:
   1. the three retrieval runs;
   2. under D1 A, the five `make eval-local` sessions;
   3. one publish commit (both baselines), then the margin, the THRESHOLDS row and `raglab gate
      --run` on each repeat;
   4. the live break with S2's plant, restored;
   5. under D2 B, the judge session on the published run 1, on a clean tree.
7. **Docs**, and `make check` green again.
8. **The criteria judge** (Fable 5.1, its own worktree and context):
   - re-runs the evidence and recomputes every number from the records and the sealed labels;
   - makes each criterion's break at the head it judges, and restores each;
   - runs GV11's live break, one gate session with S2's plant, on AC power (under D1 A);
   - gives a verdict per criterion: met, not met, needs CI, or not applicable.
9. **Fix rounds:** at most two.
   - A fix that edits `golden.v2.jsonl`, the answer key or the datasheet's v2 row after the
     sign-off comes back to you, and runs every baseline S4b made again.
   - Product choices come back to you.
   - A third round needs your go.
10. **Report:** the pull request's body is the stage report: n of m criteria met, what needs CI,
    what was cut, and the Mac time used. It carries a CHANGELOG line. You merge it by hand, with a
    merge commit.

Sequential subagents, unless your go asks for a Workflow. Hosted spend: none.

## Decisions needed

**D1. The consistency baseline on v2.**

- **A (recommended): "Re-run on v2 in S4b".**
  - What runs: after your sign-off, at F, five answer-v1 sessions on v2's dev slice (about 102
    cases ×3), under S4's rule for the baseline and the margin (your answer-v2 D3, "Keep S4's rule
    (Recommended)").
  - What it changes: every generation config but the position test's names v2. The gate then
    compares about 80 dev behaviour cases instead of 27, so its one-case margin is 1 of about 80.
    v1.1's baseline and repeats stay published as history. S6 and any later prompt start from a v2
    baseline.
  - Why: the stage that changes the dataset republishes the baselines it makes stale, as S4 did.
  - Cost: about 1 h 5 min of Mac time (estimate), on AC power.
- **B: "Keep the gate on v1.1 until S6".**
  - What it changes: the local, nightly and release configs stay on v1.1, because
    `tests/unit/test_held_out_split.py` requires the nightly and release configs to name the local
    config's dataset.
  - So no new case runs live in S4b.
  - `make release-local` would run v2's retrieval test split beside v1.1's generation test split.
  - S6 makes the move and the five runs.
  - Cost: no Mac time in S4b.

**D2. The judged baseline on v2** (under D1 A; under D1 B it stays on v1.1).

- **A (recommended): "In S6, as its first live step".**
  - What it changes: the judge's files stay byte for byte in S4b, and THRESHOLDS.md keeps `5aa0ec5`
    (v1.1) as the judged baseline until S6. The ledger gives S6 the design count to set its cap.
  - Why:
    - S6 calibrates this judge on 30 labels and needs judged verdicts on the answers it labels, so
      one judged record on v2 serves both.
    - The run takes about 2 h 10 min to 2 h 20 min (estimate), over the 7,200 s cap. Raising the
      cap changes `config/judge-local.toml`, whose sha256 answer-v2's one-judge test holds to the
      v1.1 judged records.
    - S6 may change the judge, which would leave a judged baseline made now stale.
- **B: "In S4b, after the five runs".**
  - What runs: one judge session on run 1. The cap is raised first, from the design count, and the
    one-judge test learns the new cap.
  - Cost: about 2 h 15 min more of Mac time (estimate).
  - What it gives: judged numbers on v2 before S6 starts.

**D3. R-22 and the corpus.**

- **A (recommended): "No corpus change; R-22 stays a gap".**
  - v2 is written over the existing corpus and both tenants. Every other requirement has a planted
    feature, and the new features are answer-key additions over text the pack already holds.
  - R-22 is priority S. Its row says it has no planted feature and names S8's suite audit, which
    sets coverage cells against cases (how-to 09 B). There it is planted, in a corpus pull request
    of its own, or accepted as not covered.
- **B: "Plant R-22 in S4b".** One unresolved conflict between two current approved tenant A
  documents, in new sections. It ripples into:
  - SPEC and the register, `SOURCES.md`, the build manifest and the inventory snapshot (a reviewed
    diff);
  - a feature in the answer key, and a canary if a new document title appears;
  - TEST-PLAN section 3, where no label says "present both" (flag-conflict needs a governing side);
  - check-dataset's rule 5 and the conflict check: the measure answer-v2 kept frozen;
  - docs/CRITERIA.md, frozen, for the judge;
  - a new corpus sha256 for every baseline;
  - your sign-off of the corpus change, as in S1a.
  - Cost: about a day more of agent time and an hour of your review (estimates; no ledger measures
    a corpus change of this size).

**D4. This plan.**

- **"Approve and start (Recommended)":** the build and the cases start on
  `feat/s4b-golden-set-v2`.
- **"Changes first":** say what to change, and the plan comes back.

## Risks

- **Your review time** runs past the main plan's budget (above).
- **Additions that break v1.1's records.** A new side or canary would fail a v1.1 record's
  derivation; GV5 and the committed-runs test catch it before the sign-off.
- **A refused publish.** One leaked planted string stops the stage for you (S4's rule).
  F-44 and F-45 stay out for that reason.
- **Retrieval moves without the questions changing.** fastembed 0.9.0 has come in since S4; the
  answer-v2 ledger found the gate's value unchanged under it. A difference is reported and
  explained, never chased.
- **Harder cases lower the numbers.** v2's first run is the baseline whatever its value, and its
  numbers do not compare with v1.1's, apart from the shared-cases reading.
- **The oracle's section-list false positive** can fail an honest abstention, and v2 has three
  times the abstain cases. It stays as it is: the measure is out of scope.
- **Concentration.** Several cases share a feature, and test cases share features and sections with
  dev lines. The datasheet lists the overlap.
- **The judged numbers lag** under D2 A: THRESHOLDS.md's judged section stays v1.1's until S6.
- **The command guard.** If it refuses a command, the developer splits it, or reports it, and never
  routes around it.

## Approval

The go for this draft (2026-10-23, about 22:10 WEST), verbatim: "S4b planner now (Recommended)",
the answer to "answer-v2 is merged and cleaned up. The main plan's next stage is S4b: golden set
v2, about 120 cases, covering every question type and both tenants. Start it?"

Your answers (2026-10-23, about 22:50 WEST, through the orchestrator's question prompt), each with
its question, verbatim:

- **D1.** Question: "S4b D1: v2 makes answer-v1's consistency baseline (14 of 27 on v1.1 dev)
  stale. Re-run it on v2 in S4b?" Answer: "Re-run on v2 in S4b (Recommended)". It means option A:
  at F, five `make eval-local` sessions on v2's dev slice, run 1 the baseline (GV11).
- **D2.** Question: "S4b D2: the judged baseline on v2 is one long local judge session, about 2 h
  15 min (estimate). That is over the judge's 2-hour cap. Where should it run?" Answer: "In S6, as
  its first live step (Recommended)". It means option A: no judge session in S4b; `5aa0ec5` stays
  the judged baseline, on v1.1, until S6 (GV12).
- **D3.** Question: "S4b D3: R-22 (an unresolved conflict between two current documents) is the
  only requirement with no planted feature. Change the corpus for it?" Answer: "No corpus change;
  R-22 stays a gap (Recommended)". It means option A: no corpus change; R-22 stays a gap for S8's
  suite audit.
- **D4.** Question: "S4b D4: approve the S4b plan? Your time over the stage is about 4–5 h
  (estimate), most of it the v2 sign-off." Answer: "Approve and start (Recommended)". It means:
  the build and the cases start on `feat/s4b-golden-set-v2`.

## Sources (read 2026-10-23)

- [H1] AI Testing Handbook, the RAG build project, Stage 4, "the golden set": "Suggested mix: 15
  single-chunk, 8 multi-chunk, 8 unanswerable, 4 version conflicts, 5 paraphrased or misspelled":
  https://raw.githubusercontent.com/willcoliveira/ai-testing-handbook/main/learning-path/rag-build-project.md
- [H2] AI Testing Handbook, how-to 17, "Test a RAG application", step 4 ("Start at 30 to 50"):
  https://raw.githubusercontent.com/willcoliveira/ai-testing-handbook/main/how-to/17-test-a-rag-application.md
- [H3] AI Testing Handbook, how-to 02, "Build a golden set", steps 4 to 7:
  https://raw.githubusercontent.com/willcoliveira/ai-testing-handbook/main/how-to/02-build-a-golden-set.md
- The repository at `2b9ba60`: the main plan; the S4, S5 and answer-v2 plans and ledgers;
  `datasets/` (the golden file, the datasheet, the canary set); `corpus/answer-key.yaml` and
  `corpus/SPEC.md`; docs/TEST-PLAN.md, docs/THRESHOLDS.md and docs/CRITERIA.md;
  `src/raglab/evals/dataset_check.py`, `golden.py` and `record.py`; the tests and configs named
  above; every manifest under `runs/published/` and its `index.json`.
