---
stage: S6
name: judge-calibration
nodes: [S6]
date: 2026-10-23
branch: feat/s6-judge-calibration
status: approved
---

# S6: Judge calibration on 30 blind labels

Part of the main plan (phase P2, release v0.2). Branch: `feat/s6-judge-calibration`, cut from
`main` at `2b9ba60`, answer-v2's merge. Build project stage 6, "calibrate the judge (playbook 05)",
and how-to 17 step 10 [H1, H2]; the method follows how-to 05, "Calibrate the evaluator" [H3].

The main plan's row for S6: "bar written before looking; blind `label` CLI after the rubric
settles; labels never reused as judge examples; kappa, confusion table, TPR and TNR; second
labeller on 10–15 items, or an explicit single-labeller caveat; how-to 05 record template;
threshold and reason in THRESHOLDS.md". Its risks add "30 labels: a precursor, not the calibration
study", and its open variables give S6 "About 1–2 hours of blind labelling, and whether a second
labeller is available".

**The go for this plan (2026-10-23, about 22:45 WEST), verbatim.** You asked, in your own words:
"can we launch more sub agents in parallel to that one to speed up the development phase for
upcoming steps into the plan?" Asked "Which planners should I launch now, next to S4b's? Each
writes its plan only, in its own worktree, and stops for your approval.", you answered: "S6 planner
(Recommended), S7 planner (Recommended), S9 planner". The approval of this plan is its last
decision, D5, quoted under Approval when you give it.

## Where S6 starts

Read at `2b9ba60`. Each number is copied from a file, a published manifest or a ledger, or computed
by a read-only script where it says so (the planner's scripts sit outside the repository).

### The judge, frozen since S5

- **The model:** `ministral-3:14b-instruct-2512-q4_K_M` at digest `4760c35aeb9d…`, local on Ollama
  0.40.6, temperature 0, seed 20261020, at most 512 output tokens, `json_schema`
  (`config/judge-local.toml`).
- **The prompt:** judge-v2, fingerprint `e90d9d8d8bcb…`: one criterion per call, every input framed
  as data, a strict parser.
- **The criteria:** docs/CRITERIA.md, sha256 `8c8f973a3306…`, signed off twice: on 2026-10-20
  ("Sign off with the clause (Recommended)") and on 2026-10-21 ("Reword and re-judge
  (Recommended)"). Every criterion's status line reads "reported (calibrated in S6)". The file is
  frozen: a change needs a new sign-off and makes every judged record made under it stale for
  publishing (`publish.judged_problems`).
- **The canary set:** `datasets/canaries.judge.jsonl`, 19 items, sha256 `4ca54c3ced55…`, a hard
  stop at the start of every judge session.
- **The config:** `config/judge-local.toml`, file sha256 `228a720045d8…`, canonical sha256
  `e827550511a7…`. The judged run's cap is `run_timeout_s = 7200`, set in S5 from 592 calls times
  the slowest canary call (9.196 s), rounded up to two hours. `JudgeConfig.resolved()` hashes the
  whole `[judging]` table, so the cap is part of the canonical sha256 as well as the file's.
- **The one-judge test:** `tests/judge/test_answer_v2_one_judge.py` holds `5aa0ec5` and `c14acb0`
  to today's judge: the prompt, CRITERIA.md, the canary set, the model and digest, and the whole
  config block (`name`, `path`, `file_sha256` and the canonical `sha256`). Any change to the file,
  the cap included, turns it red.
- **Sessions:** one model per session, loopback, and AC power only (S5's AC22: the session refuses
  on battery and stops cleanly if the power goes).

The hashes were checked with `shasum -a 256` and against both judged manifests on 2026-10-23.

### The judged records, all on golden set v1.1's dev slice

| Record | What it judged | Judge calls | Run time | `grounded` pass / fail | `abstains` pass / fail |
|---|---|---|---|---|---|
| `20261020T195341Z-judge-local-dev-25ccc0d` | judge-v1, history | 592 | 3,869.275 s (awake) | 125 / 19 | 6 / 11 |
| `20261021T081852Z-judge-local-dev-5aa0ec5` | judge-v2 on answer-v1's consistency baseline: the judged baseline | 592 | 3,380.41 s | 125 / 19 | 6 / 11 |
| `20261023T090413Z-judge-local-dev-c14acb0` | judge-v2 on answer-v2's first run (measured, not adopted) | 605 | 3,257.091 s | 125 / 22 | 11 / 7 |

Every repeated verdict agreed with the first in both judge-v2 records (92 and 96 pairs); the order
check agreed in 46 of 48 and 47 of 49. In `c14acb0` the 11 `abstains` passes come from 4 cases
(counted from its lines).

### What S5 and answer-v2 left for S6

- **S5's caveats, "for S6"** (S5 ledger): `relevant` fails short right answers (16 of its 23 fails
  are on answers that state the answer key's value, 10 of them two words long); `grounded` fails
  some answers that say the documents do not state the value (4 of its 19 fails; two of them state
  no value at all, which the first sign-off's clause passes). "Both criteria read correctly; the
  judge misapplies them, and S6's human labels calibrate it."
- **The S5 ledger** also records the judge failing an answer on `correct` for an added fact, which
  the rule does not fail; **answer-v2's plan** adds that it passed refusals that name no sanctioned
  route (`refuses_and_helps`).
- **AV2-J3 (info), answer-v2's criteria judge,** verbatim from its ledger: "The judged record's
  check holds a verdict to its reply, not the reply to the judge: a verdict flipped together with
  its reply's verdict, then resealed, validates [...] A published judged record's integrity rests
  on the reviewed commit that publishes it." Decided below, under "AV2-J3 and the chain of
  evidence".
- **Promises in the docs:** THRESHOLDS.md says of the repeatability and order checks, "S6 reads them
  beside the human labels"; TEST-PLAN section 10 holds the placeholder "<from S6: kappa on 30
  labels>"; R5's gate reads "reported, not gated, until S6 calibrates the judge", which
  `tests/unit/test_test_plan.py` asserts.

### S4b's answers, and what S6 inherits from them

You answered S4b's decisions on 2026-10-23, at about 23:00 WEST. The option labels, verbatim:

| S4b decision | Your answer | What it means for S6 |
|---|---|---|
| D1, the consistency baseline on v2 | "Re-run on v2 in S4b (Recommended)" | S4b re-runs answer-v1's five-run consistency baseline on golden set v2's dev slice (about 102 cases ×3) at its freeze commit, and publishes run 1 as the baseline. That run is the source S6 judges. |
| D2, the judged baseline on v2 | "In S6, as its first live step (Recommended)" | S6 makes the judged baseline on v2 from S4b's run 1, as its first live step. Until then THRESHOLDS.md keeps `5aa0ec5` (v1.1). S4b's ledger gives S6 a design count, about 1,450 judge calls, about 7,800 s at answer-v2's 5.38 s a call: over the 7,200 s cap. S6 raises the cap and changes the one-judge test (below). |
| D3, R-22 and the corpus | "No corpus change; R-22 stays a gap (Recommended)" | Nothing for S6: no new criterion, and CRITERIA.md and the canary set stay as they are. |
| D4, the S4b plan | "Approve and start (Recommended)" | S4b is being built now. S6's offline build can start once this plan is approved; its first live step waits for S4b's merge, because the source run, `golden.v2.jsonl` and the corpus sha256 must be in this branch's tree: the developer merges `main` into this branch first. |

If S4b's sign-off or its runs move the counts (cases per label in dev, withheld trials), the design
count moves with them: S6 counts the calls again with a dry run before it sets the cap.

### What the handbook asks

- **Build project, stage 6** [H1]: "Label 30 outputs yourself (supported or not, abstained
  correctly or not) before looking at the judge's scores. Compute agreement and pick the threshold
  from it, not from the library default." "Prove it: kappa, the confusion table, and the threshold
  you chose with the reason."
- **How-to 17, step 10** [H2]: "Calibrate the judge on 30 or more human labels before the threshold
  gates anything."
- **How-to 05** [H3]: draw a blind sample ("Hide the judge's verdicts from the labellers"; "At least
  30 cases per failure mode you care about"); label by hand, two people, "the same schema the judge
  uses"; compute agreement three ways, with "Cohen's kappa for two raters on binary labels" and raw
  agreement beside it; "Set the threshold before you look" (McHugh's reading "treats 0.80 to 0.90
  as strong and below 0.60 as weak"; "A judge that agrees with humans less than the humans agree
  with each other is not ready"); read and classify every disagreement ("criterion badly written",
  "judge prompt unclear", "human error (relabel)", "genuine ambiguity (mark the case)"; "Do not
  tune the judge to the sample; fix the cause"); "Re-run on a fresh sample after changes"; schedule
  recalibration triggers; write the record "beside the judge prompt version", from its template
  (judge, sample, labellers, agreement, threshold, disagreements, verdict, next).

### Measured times, the basis of every estimate below

- **A judge session on 147 case-trials:** 56 min 52 s (S5's judge-v2 run, 09:18:21 to 10:15:13 on
  2026-10-21) and 54 min 52 s (answer-v2's, 2026-10-23). Per judge call, computed from the records:
  3,380.41 s / 592 = 5.710 s and 3,257.091 s / 605 = 5.384 s.
- **A short judge session** (`make judge-canaries`): 2 min 2 s, twice (S5 ledger). The judge's live
  contract test alone: 33.11 s (answer-v2 ledger).
- **A dry run of a judged run** with a scripted fake judge, no model: 0.546 s, ingest included (S5
  ledger).
- **`make check`:** 201.89 to 213.25 s real (S5 and answer-v2 ledgers); pr-fast about 12 minutes
  (the orchestrator's reading, 2026-10-23).
- **Agents** (the orchestrator's timing notes): in S3, a planner's research 16 min, a decisions round
  17 min, a full criteria judge about 1 h and a developer's full stage about 2 h; on 2026-10-23,
  S4b's planner 32 min.

## Goal

- Make the judged baseline on golden set v2 (S4b's D2) with the judge unchanged but for the run's
  cap, and keep the one-judge test meaning "the same judge".
- Calibrate the judge against your blind labels: 30 of that record's verdicts, drawn by a seeded rule
  stratified by criterion and verdict, under a bar written and committed before any label exists.
- Report kappa, the confusion table, TPR and TNR with intervals and every disagreement classified,
  in how-to 05's record, and write the threshold and its reason in THRESHOLDS.md: per calibrated
  criterion, trusted (S8 may gate on it), reported only, or not trusted.
- Keep the labels out of the judge for good.

## Out of scope

| Item | Where it goes |
|---|---|
| Any gate on a judged criterion | S8 wires eval-on-change; S6 says which criteria may gate |
| A change to the judge: judge-v3, CRITERIA.md, the canary set, the model | D4: a follow-up pull request under A, one loop inside S6 under B |
| The criteria D1 leaves out | reported, uncalibrated, and never gated until labels of their own calibrate them |
| The calibration record's id in judged manifests (the main plan's manifest names one) | S8, when a gate reads it: the judged baseline on v2 is made before the record exists |
| A judged record that proves its own replies (AV2-J3) | not possible from inside a record (below) |
| A hosted judge, any sign-up | ADR-002: local only for now |
| Any test-split run | nightly and release |
| Re-judging the v1.1 records, or the position test on v2 | none: they stay published as history |
| Calibration in the Pages playground | S11 |

## The judged baseline on golden set v2: S6's first live step

- **The source:** S4b's run 1, the consistency baseline on v2 (answer-v1, dev, ×3), published by
  S4b. It is judged as S5 judged its source: each behaviour case and retrieval question on its
  criteria (docs/CRITERIA.md's table), `context_sufficient` once per case, the canaries first, and
  the checks on the judge after (trial 1 of every behaviour case judged again; `grounded` on trial 1
  of every case with the passages reversed).
- **The design count** (computed from S4b's plan targets; a count, not a measurement). Two thirds of
  each label's new cases in dev gives about 42 `answer`, 18 `abstain`, 9 `flag-conflict` and 12
  `refuse-and-help` dev cases, plus the 22 dev retrieval questions. That makes 1,059 verdicts
  (`grounded` 309, `cites_support` 153, `correct` 189, `relevant` 255, `abstains` 54,
  `refuses_and_helps` 36, `context_sufficient` 63), 391 checks and 19 canaries: about 1,469 calls,
  fewer the withheld trials. S4b's plan says about 1,450.
- **Its time** (estimate): 1,469 calls at the two measured means, 5.384 and 5.710 s, is 7,909 to
  8,388 s of judging, about twice the longest judged run so far (3,869.275 s). With the contract
  test and the start and stop, the session takes about 2 h 13 min to 2 h 21 min.
- **The cap.** The developer first runs the judged run once offline on S4b's run 1 with a scripted
  fake judge (no model, as S5's dry run did), which gives the exact call count. The cap is that count
  times 5.710 s, the slower measured mean, times 1.5, rounded up to the next half hour: 12,600 s
  (3 h 30 min) at 1,469 calls. It is committed in `config/judge-local.toml`, with the count, the two
  means and the rule in the file's comment, before the session, as S5 set its cap. S5's own rule
  (the calls times the slowest canary call, times 1.3) would give about 18,000 s, five hours that a
  hung run would spend in full; two judged runs now measure the mean per call, where S5 had only the
  canaries. A run that hits the cap is partial and never published.
- **The one-judge test, cap excepted.** It is rewritten to hold the same judge, not the same file:
  today's config with only `judging.run_timeout_s` set back to the records' 7,200 must hash to
  `5aa0ec5`'s and `c14acb0`'s canonical config sha256 (`e827550511a7…`). The `file_sha256`
  equality is dropped, because the cap's comment changes it. Everything else it checks stays: the
  prompt's version and fingerprint, CRITERIA.md, the canary set, the model and digest, and
  `publish.judged_problems` empty. The judged baseline on v2 joins the test with its config matched
  exactly, so all three records compare under one judge. The committed manifests are the oracle: a
  restored value of the wrong type shows as a red test, not a silent pass.
- **Why one config and not a second file.** A second config (a `judge-local-v2.toml` with the larger
  cap) would leave the test alone, but its name enters every run id
  (`<time>-<config name>-<split>-<sha>`) and the Makefile's `JUDGE_CONFIG`, and it would make two
  configs for one judge.
- **The checks on the judge stay** (391 of the 1,469 calls). Dropping them would fit under the old
  cap but needs a code change, and THRESHOLDS.md promises S6 reads the judge's repeatability and
  order agreement beside the labels: they are the judge's own noise.
- **Blindness starts here.** Once the record exists, the ledger, the drafts of the pull request and
  every message to you give its aggregate numbers only. No item-level verdict (a case, trial and
  criterion with its verdict, quote or reason) is quoted until your labels are sealed.
- **THRESHOLDS.md** moves its judged section to this record. `5aa0ec5` and `c14acb0` are named as
  v1.1 history. Everything stays reported until the calibration's verdicts land.

## The calibration

### The bar, written before any label (D2)

Under D2's recommended answer, per calibrated criterion, on your sealed labels:

| Cohen's kappa, the judge against you, on the criterion's 15 items | Status | What it means |
|---|---|---|
| 0.80 or more | trusted | S8 may gate on it |
| 0.60 to under 0.80 | reported only | its numbers stay reported, with the record linked; no gate |
| under 0.60 | not trusted | its pass rates are not read as evidence anywhere (THRESHOLDS.md, the README, pull request bodies) until a fix is calibrated (D4) |

**What the lines mean in items.** Cohen's formula on 15 items, 7 judge passes and 8 judge fails
(arithmetic, not a measurement):

| Disagreements of 15 | Kappa | Status under D2 A |
|---|---|---|
| 0 | 1.000 | trusted |
| 1 | 0.865 to 0.867 | trusted |
| 2 | 0.727 to 0.737 | reported only |
| 3 | 0.587, 0.595, 0.602 or 0.609 | reported only when at least two of the three are the judge failing what you pass (0.602, 0.609); not trusted when at least two are the judge passing what you fail (0.587, 0.595) |
| 4 | 0.444 to 0.483 | not trusted |

- **The interval.** Each kappa gets a 95% interval from a bootstrap within strata (below). On 15
  items it is wide, and the bar reads the point estimate: that is the main plan's "a precursor, not
  the calibration study".
- **What the bar does not read:** the weighted TPR and TNR, the pooled kappa and the second
  labeller's numbers. They are reported beside it.
- **Where it is written:** `bar.toml` in the calibration folder, which `raglab calibrate` reads, and
  THRESHOLDS.md's judged section, held equal by a test. Both are committed before the sample is
  drawn. The sample records the bar's sha256, and `calibrate` refuses a bar that changed since.
- **The sealed labels decide.** A correction you make after seeing the judge's verdicts is reported
  beside your sealed label and never replaces it in the numbers the bar reads.

### The items (D1)

- **The unit** is one judge verdict: an answer (a case and trial) on one criterion, shown with
  exactly what the judge saw.
- **The frame:** the v2 judged record's first-pass verdicts (`verdicts`, never `repeat` or
  `reversed`) on the calibrated criteria, with status `ok` and a verdict of pass or fail.
  `unable_to_verify`, `invalid_output` and `unavailable` are on neither side: counted in the record,
  never sampled.
- **The strata:** criterion × the judge's verdict. Under D1 A: `grounded` 15 (7 judge passes, 8
  judge fails) and `abstains` 15 (7 and 8). The odd item goes to the fails, where S5's caveat on
  `grounded` lies.
- **The draw, rule s6-1, seed 20261023** (this plan's date, written here before the record exists).
  Within a stratum, the verdicts are sorted by case id and trial and shuffled with the seed, then
  taken in that order. An answer (case and trial) already in the sample is skipped, and so is a case
  already taken in that stratum, until every case of the stratum has given one item; second trials
  follow in the same order. A stratum smaller than its allocation gives all it has, and the rest of
  the criterion's items come from its other stratum; the record says so. The labelling order groups
  the items by criterion (one rule in mind at a time) and shuffles them within each criterion, so
  the judge's verdicts are mixed.
- **Expected frame sizes** (from the design count and the v1.1 records' rates; projections, not
  measurements): `grounded` about 309 verdicts, of which 13 to 15% fails (19 of 144 and 22 of 147
  in the v1.1 records), so about 40 to 46; `abstains` about 54 (11 of 17 and 7 of 18 failed on
  v1.1). With `c14acb0`'s 11 passes on 4 cases, the "one per case first" rule may need second
  trials.
- **The sample file** holds the pins (the judged record's id and its manifest's sha256, the source
  run's id, the bar's sha256, the seed and the rule's name) and, per item, its order, case id,
  trial and criterion. No verdict and no stratum. A test draws it again from the published record
  and compares.

### The blind `label` CLI

`raglab label` (behind `make label`), which you run in this branch's worktree on your Mac. It needs
no model, no Ollama and no network, so it is not a live session.

- **It shows, item by item:** the criterion's pass and fail rules in judge-v2's words, which
  `tests/unit/test_criteria.py` holds equal to CRITERIA.md (the settled rubric: two sign-offs, then
  frozen); and the item as the judge saw it, rebuilt with `raglab.evals.judged.judge_item` from the
  source generation record and the corpus: the question, each passage with the id, document,
  version, section and status its frame carries, the reference answer when the criterion sees one
  (neither of D1 A's criteria does), and the answer.
- **It never shows** the judge's verdict, quote, passage ids or reason, the stratum, the generator's
  decision label, or anything else the judge did not see. It never opens the judged record's lines:
  it reads the sample, the source record and the corpus.
- **It records, in the judge's schema:** the verdict (pass or fail), the quote (a verbatim span of
  the answer, checked), the passage ids (among those shown), a one-sentence reason, an `ambiguous`
  flag (with the two readings in the reason), the shown answer's sha256, the time, and the seconds
  spent on the item. Ambiguity is a flag on a binary label, not a third class: kappa is for two
  raters on binary labels [H3].
- **It resumes** where you stopped, lets you redo an item before the seal, and `--seal` writes the
  file's sha256 and time. After the seal it refuses any change, and so does `calibrate`.
- **The guide**, `datasets/calibration/README.md`, committed with the bar: judge only what is shown,
  as the judge does; the frozen rules decide, not the rule you would write today (a rule you would
  change gets the `ambiguous` flag and a reason, never a change mid-labelling: grading changes the
  grader's own criteria as they go [H3]); one or two sittings; do not open the v2 record's
  `cases.jsonl`, its `report.md` or its playground page before the seal.
- **After the seal:** your attestation that you did not open them, quoted verbatim in the ledger.
  The developer commits the labels and the seal as written, in one commit.

### The statistics, defined before any label

- **Per calibrated criterion, and pooled over them:** the confusion table (your label × the judge's
  verdict, in sample counts), raw agreement and Cohen's kappa. The pooled kappa fills TEST-PLAN's
  "kappa <x> on <n> labels".
- **TPR** is the share of the answers you pass that the judge passes; **TNR** the share of the
  answers you fail that the judge fails. The sample is stratified by the judge's verdict, so both are
  estimated for the judged record by weighting each item by its stratum's size over its sample size;
  the unweighted shares are shown beside them. Why the weights matter (an illustration from
  projected sizes, not a measurement): at S5's `grounded` fail rate (19 of 144) on about 309
  verdicts, a sampled judge pass stands for about 38 verdicts and a judge fail for about 5, so one
  judge pass that you fail takes the weighted TNR to about one half: the judge would miss about half
  of the real fails.
- **Intervals:** 95%, percentile, from a bootstrap within strata, 2,000 resamples (`raglab
  compare`'s count) with seed 20261023. A resample whose kappa is undefined is counted and reported.
- **The judge's own noise, beside the labels:** the v2 record's repeatability and order agreement on
  the calibrated criteria.
- **By code only:** `raglab calibrate` computes every number, tested on hand-computed tables, in the
  standard library: no new dependency.

### The second labeller (D3)

You are the only labeller this plan knows of, so the main plan's "second labeller on 10–15 items,
or an explicit single-labeller caveat" is D3. Under D3 A: the caveat, and a blind re-label of 12
items (6 per criterion, drawn from the 30 with the seed and shown in a new order) at least a day
after the seal, through the same CLI, which shows neither your first labels nor the judge's
verdicts. Your agreement with yourself (raw and kappa) is reported beside the judge's against you,
and is labelled as what it is: a floor on your own label noise, not how-to 05's agreement between
two people. Remembering some first labels a day later makes it an optimistic floor.

### Reading the disagreements

After the seal, the developer shows you each disagreement with the judge's reason beside yours, and
drafts a class for it (how-to 05 step 5): criterion badly written, judge prompt unclear, human
error, or genuine ambiguity. You confirm or change each class; your answers are quoted in the
ledger and written to `disagreements.jsonl`, which `calibrate` reads. A "human error" is reported as
a correction beside the sealed label (above). A "genuine ambiguity" is marked in the record only:
golden set v2 is frozen after S4b's sign-off. Nothing about the judge is tuned to these 30 items.

### The record

`raglab calibrate` writes `record.json` and `record.md` in the calibration folder (suggested:
`datasets/calibration/judge-v2-c1/`, beside the bar, the sample, the labels and their seals). The
Markdown follows how-to 05's template, filled from the files, never edited by hand:

```
judge: ministral-3:14b-instruct-2512-q4_K_M @ 4760c35aeb9d, judge-v2 e90d9d8d8bcb, temperature 0
sample: 30 verdicts of <the v2 judged record>, drawn <date>, rule s6-1, seed 20261023;
  grounded 15 (7 judge pass, 8 judge fail), abstains 15 (7, 8)
labellers: the maintainer (blind); <D3's answer: the re-label, a second person, or the caveat>
agreement: per criterion and pooled: raw, kappa [95% interval], TPR and TNR weighted [interval]
  and unweighted; the judge's repeatability and order agreement beside them
threshold: kappa >= 0.80 trusted, 0.60 to 0.80 reported only, < 0.60 not trusted
  (written <commit>, before the sample <commit> and the labels <commit>)
disagreements: <n> read: <k> criterion, <k> prompt, <k> human error, <k> ambiguous
verdict: trusted for <criteria>; reported only for <criteria>; not trusted for <criteria>
next: recalibrate on <the triggers>, or <the follow-up D4 names>
```

**The triggers** (how-to 05 step 7): a change of the judge's model, digest or prompt version; a
change of CRITERIA.md or the canary set; a new golden set version; S8's drift alert on a judged pass
rate; and the gate map's manual "calibration re-run" before each release. Each one makes this
record history for the judge it no longer describes.

### If a criterion misses the bar (D4)

- **What is re-signed off:** CRITERIA.md (a third sign-off) when a disagreement's class is
  "criterion badly written"; the canary set only if a canary's side changes. **What is versioned:**
  the prompt, as judge-v3 with its reviewed snapshot and fingerprint, when the class is "judge prompt
  unclear". **What is judged again:** the judged baseline on v2, as a new record; the first stays
  published as history. **What is labelled again:** a fresh sample of the same allocation that
  excludes the first 30 (how-to 05 step 6: "Calibrating and measuring on the same cases is
  overfitting"); the bar is read on the fresh sample only.
- **What never changes:** the v1.1 judged records (`25ccc0d`, `5aa0ec5`, `c14acb0`) and the position
  test's (`9fa9004`) are not judged again; under a new CRITERIA.md or judge-v3 they become stale for
  publishing, stay published as history, and the one-judge test becomes a history test. A sealed
  label is never edited.
- **Where it happens is D4:** a follow-up pull request (A) or one loop inside S6 with your go (B).
- **If no criterion misses:** nothing is changed, so no fresh-sample re-run is owed now (how-to 05
  step 6 applies after changes); the triggers schedule the next calibration.

### Labels are never judge examples

- **A leak test:** no judge prompt version (judge-v1, judge-v2 or any later one) holds a run of 8 or
  more words from a labelled item's answer, quote or reason. Eight, because the rules' own phrases
  (for example, that the documents do not state it) recur in honest answers; the longest run shared
  today is measured and reported.
- **No path in:** nothing under `src/raglab/judge/` names the calibration folder (a test), and the
  canary set stays frozen.
- **Never reused:** the sampler of any later calibration excludes every item of an earlier record (a
  test), so this sample is never measured twice.

### AV2-J3 and the chain of evidence

- **The decision: S6 addresses AV2-J3 where it touches the calibration, and documents the rest.** A
  calibration is exactly where a flipped verdict would pay: a verdict changed after your labels were
  seen would raise the agreement.
- **The chain:** the bar, committed → the judged record, published → the sample, which pins the
  bar's sha256 and the judged record's manifest sha256 (and through it the sha256 of every file of
  the record) → your labels, sealed with their sha256 and time, each carrying the shown answer's
  sha256 → the record, generated. `calibrate` refuses a bar, a judged record or a labels file that
  changed after it was pinned. The order of the commits is the criteria judge's check with `git
  log` (a pytest cannot rely on the history in a shallow CI checkout).
- **What it does not do:** make a judged record prove its own replies. A reply hash chain inside the
  record is recomputed by a reseal like every other hash, so it adds code and no proof; a real proof
  would need a witness outside the record, such as the server signing each reply, and nothing in the
  repository has one. The record's limits and THRESHOLDS.md's judged section say so: a published
  judged record's integrity rests on the reviewed commit that publishes it.

## Lab practice

- **30 labels, 15 per criterion,** where how-to 05 asks for "at least 30 cases per failure mode you
  care about": a precursor, as the main plan says. Production labels about 30 or more per
  criterion and sets the bar where an interval's lower bound clears it.
- **One labeller** (D3), who also wrote the criteria, signed off the golden set and has read S5's
  caveats about the judge's tendencies: the items' verdicts are unseen, but the tendencies are known.
  Production uses two or more trained labellers, independent of the criteria's author, and an
  adjudicator.
- **Blindness is a procedure:** the published record is one command away, and the attestation is
  the evidence. Production hides the verdicts in a labelling tool with access control.
- **A local judge on a laptop,** in one session of more than two hours. Production calibrates a
  judge on a managed endpoint, and recalibrates on a schedule.

## What gets built

```
src/raglab/evals/calibration.py   the draw (rule s6-1: seeded, stratified, blind); the agreement
                                  (confusion table, raw, Cohen's kappa, TPR and TNR weighted and
                                  unweighted, bootstrap within strata); the bar; the record (json and
                                  md); the refusals (seal, pins, a disagreement without a class)
src/raglab/evals/label.py         the blind label CLI's core: items rebuilt with judged.judge_item
                                  from the source record and the corpus; the label schema; the seal
src/raglab/__main__.py            raglab label; raglab calibrate (sample, record)
config/judge-local.toml           run_timeout_s raised by the rule, with its numbers in the comment
tests/judge/                      the one-judge test (cap excepted; the v2 record added); the
                                  calibration tests (hand-computed tables, the re-draw, the sample's
                                  fields, blindness, the seal, the pins, the record regenerated,
                                  the leak test, the exclusion of earlier items)
tests/unit/test_test_plan.py      R5's gate wording
datasets/calibration/README.md    the method, the labelling guide and the files
datasets/calibration/judge-v2-c1/ bar.toml, sample.jsonl, labels.jsonl and its seal, relabels.jsonl
                                  and its seal (D3 A), disagreements.jsonl, record.json, record.md
runs/published/                   the judged baseline on golden set v2
Makefile                          label, relabel, calibrate
docs/                             THRESHOLDS, TEST-PLAN, LOCAL-MODEL, ONBOARDING, ARCHITECTURE,
                                  README; CHANGELOG
docs/plans/2026-10-23-s6-judge-calibration-ledger.md   the ledger
```

The file and target names are suggestions; the developer may choose others and says so in the
ledger.

## Shared files, for sequencing the merges

S6 merges after S4b: its first live step needs S4b's run 1 in the tree.

| File | S6's change | Also touched by |
|---|---|---|
| CHANGELOG.md | one line | every pull request |
| docs/THRESHOLDS.md | the judged section: the v2 baseline, the bar, the verdicts, the triggers | S4b (the consistency row; the judged section's note that `5aa0ec5` stays); later stages' rows |
| docs/TEST-PLAN.md | section 10's judges line; R5's gate cell; the Test column's words for the calibrated criteria | S4b (the traceability column, section 10's golden-set line); S7 (the security line) |
| docs/CRITERIA.md | none under D4 A; a third sign-off only under D4 B with a miss | frozen since S5 |
| docs/plans/2026-10-05-raglab-plan.md | none expected (S4b writes the note for its D2) | S4b |
| README.md, docs/ARCHITECTURE.md | the S6 node, `wip` then `done` | every stage |
| Makefile | the new targets and the `.PHONY` line | likely S7 and S9 (one shared `.PHONY` line) |
| pyproject.toml, uv.lock | none expected: the statistics use the standard library | dependency pull requests |
| .github/workflows/ | none expected: the new tests run in pr-fast's existing test step | — |
| src/raglab/__main__.py | the `label` and `calibrate` subcommands | possibly S7 and S9 |
| config/judge-local.toml | the cap | none (S4b leaves it unchanged under its D2 A) |
| tests/judge/test_answer_v2_one_judge.py | the same judge, cap excepted; the v2 record added | none expected |
| tests/unit/test_test_plan.py | R5's gate wording | S4b (GV9) |
| runs/published/index.json | the v2 judged record | S4b's runs (published before S6's) |
| docs/LOCAL-MODEL.md | the cap and the v2 judge session's measured time | S4b (v2's generator session times) |
| docs/ONBOARDING.md | `make label` and `make calibrate` | S4b (check-dataset over two files) |

## Choices I made (you can change them)

| # | Item | Choice | Why |
|---|---|---|---|
| 1 | Where the items come from | the judged baseline on v2 (S4b's D2): no verdict of it has been seen | blindness; it is the judge on the data S8 will gate; the v1.1 records' verdicts are quoted in the S5 and answer-v2 ledgers |
| 2 | The cap | raised in the one config, by a rule from the two measured means; the one-judge test holds the judge's identity, the cap excepted | a second config file puts its name into run ids and the Makefile; S5's slowest-canary rule would give about five hours |
| 3 | The checks on the judge | kept in the v2 run | the judge's own noise, read beside the labels, as THRESHOLDS.md promises |
| 4 | The unit of a label | one verdict, shown as the judge saw it, labelled in the judge's schema | how-to 05 step 2: "the same schema the judge uses" |
| 5 | Ambiguity | a flag on a binary label | kappa is for two raters on binary labels |
| 6 | The sample file | the item keys only, grouped by criterion and shuffled within | stratifying by verdict would otherwise leak the verdict |
| 7 | The CLI's inputs | the sample, the source record and the corpus; never the judged record's lines | a test can then prove the CLI cannot show a verdict |
| 8 | What the bar reads | each criterion's kappa on its sealed labels | TPR and TNR weighted on 7 and 8 items swing on one item; they are reported for S8's margins |
| 9 | Corrections after unblinding | reported beside, never in the bar's numbers | a labeller who defers to the judge would raise the agreement |
| 10 | AV2-J3 | the calibration pins its inputs; the judged record's format is unchanged | no reseal-proof hash exists inside a record |
| 11 | Where the record lives | `datasets/calibration/`, beside the judge's other inputs (the canary set) | how-to 05 step 8: "beside the judge prompt version"; it is data and generated text, not code |
| 12 | The seed | 20261023, this plan's date, written before the record exists | the repository's convention (S4b's split uses the same date) |
| 13 | CRITERIA.md | untouched on the pass path; trust lives in THRESHOLDS.md | an edit makes every judged record stale and fails the one-judge test |

## Acceptance criteria

Evidence marked **live** runs on your Mac through the `make` targets only (or `raglab ollama
session`), one model per session, on AC power, with nothing else running and never beside `make
check`; it stays out of `make check` and is recorded in the ledger. **[CI]** marks what only the pull
request's checks prove. Each break is made on a committed file, at the head the criteria judge gives
its verdict on, and restored from git; "expected pass" marks a break that must not trip its check.

| # | Criterion | Evidence | Break |
|---|---|---|---|
| JC1 | **The bar and the guide, before any label.** D2's bar in `bar.toml` (per criterion: the trusted and stop lines, and what the bar reads) and in THRESHOLDS.md's judged section, held equal; the labelling guide; both committed before the sample is drawn; the sample records the bar's sha256, and `raglab calibrate` refuses a bar that changed since | a test that THRESHOLDS.md's bar equals `bar.toml`; `git log --format='%H %cI'` over the bar, the sample and the labels (the criteria judge); the ledger | the trusted line moved in `bar.toml` after the sample (0.80 to 0.70): `calibrate` refuses, naming the bar; THRESHOLDS.md's line alone edited: the equality test fails |
| JC2 | **The cap, and the same judge.** `run_timeout_s` raised by the rule (the dry run's exact count × 5.710 s × 1.5, up to the next half hour), its comment giving the count, the means and the rule, committed before the session; the diff of `config/judge-local.toml` holds the cap and its comment only; judge-v2, CRITERIA.md, the canary set and `src/raglab/judge/` unchanged; the one-judge test holds `5aa0ec5`, `c14acb0` and the v2 judged baseline to one judge, the cap excepted | `git diff origin/main -- config/judge-local.toml src/raglab/judge docs/CRITERIA.md datasets/canaries.judge.jsonl` in the ledger; `shasum -a 256`; `tests/judge/test_answer_v2_one_judge.py` | the temperature set to 0.1: the test fails for all three records; the seed changed: it fails; the cap alone changed: it passes (expected pass) |
| JC3 | **The judged baseline on golden set v2** (live, provenance local). After `main` (with S4b) is merged here: one `make judge-local RUN=<S4b's run 1>` session; the contract test; the canaries all on their side; the record validated and published from a clean tree, its manifest naming judge-v2 `e90d9d8d8bcb…`, CRITERIA.md `8c8f973a3306…`, the canary set `4ca54c3ced55…` and the digest `4760c35aeb9d…`; the dry run's call count beside the record's; per criterion the rate with a Wilson interval, pass^3, the `unable_to_verify` rate and the split by label; the checks on the judge; the run's duration, seconds per call and the session's clock times; THRESHOLDS.md's judged section moved to it, `5aa0ec5` and `c14acb0` as v1.1 history; no item-level verdict quoted before the seal | `runs/published/`; `raglab publish`; the ledger | a copy of the record with one verdict flipped apart from its reply and resealed: `record.validate` refuses it; the same verdict flipped together with its reply validates (AV2-J3's limit, expected pass); JC6's break makes that flip on the published record in place, where `calibrate`'s pin refuses it |
| JC4 | **The sample: seeded, stratified, blind.** D1's allocation drawn by rule s6-1 with seed 20261023 from the v2 record's first-pass `ok` verdicts; the sample file holds the pins (the judged record's id and manifest sha256, the source run's id, the bar's sha256, the seed, the rule) and, per item, only its order, case, trial and criterion, grouped by criterion and shuffled within; any shortfall said; committed before any label | a test that draws again from the published record and compares; a test of the file's fields and order; the commit order | one item swapped by hand: the re-draw test fails naming it; a `verdict` field added: the field test fails; one criterion's items written in verdict order: the order test fails |
| JC5 | **The blind CLI, your labels and the seal.** `raglab label` rebuilds each item with `judged.judge_item` from the source record and the corpus and shows exactly the judge's inputs and the criterion's rules; never the judge's verdict, quote, passage ids or reason, nor the stratum; never opens the judged record's lines; records the judge's schema (pass or fail, a quote found in the answer, passage ids among those shown, a reason, the `ambiguous` flag), the shown answer's sha256, the time and the seconds per item; seals (sha256 and time) and refuses changes after; your 30 labels sealed and committed as written; your attestation quoted | `tests/judge/` CLI tests (each item equals the JudgeItem the judged run built; the output holds none of the judge's fields for the item; with the judged record's `cases.jsonl` removed the output is the same; a quote not in the answer is refused); the labels' commit; the ledger | the CLI made to print the judge's reason: the blindness test fails; passage ids outside those shown accepted: the schema test fails; one label edited after the seal: `label` and `calibrate` refuse it |
| JC6 | **The agreement, after the seal, by code.** `raglab calibrate` refuses unless the labels match their seal, each label's answer sha256 matches the judged line's, and the pins hold (the bar, the judged record's manifest); per calibrated criterion and pooled: the confusion table, raw agreement and Cohen's kappa; TPR and TNR weighted by stratum, unweighted beside; 95% intervals from a bootstrap within strata (2,000 resamples, seed 20261023); the repeatability and order agreement on the same criteria; each criterion's status by the bar; written to `record.json` and `record.md` | hand-computed tests (kappa, TPR, TNR, the weights, the intervals' resampling within strata, the refusals); the record files; the criteria judge recomputes every number | TPR and TNR swapped in the code: the hand-computed test fails; the weights left out: the weighted test fails; one verdict of the published v2 record flipped together with its reply and resealed: `calibrate` refuses, naming the manifest's sha256 |
| JC7 | **The second labeller, or the caveat (D3).** Under A: the seeded 12, labelled at least a day after the seal through the same CLI, which shows neither your first labels nor the judge's verdicts; sealed; your raw agreement and kappa with yourself beside the judge's; the record's labellers line gives one labeller and the caveat. Under B: the second person's 12, sealed; human-to-human, judge-to-each and judge-to-consensus kappa on them. Under C: the caveat | the re-label or second-labeller file and its seal; the record (the gap between the seals); the ledger | the re-label view made to show a first label: the blindness test fails; the caveat sentence taken out of the record's template: the record test fails |
| JC8 | **The disagreements, and the record.** Every disagreement read with the judge's reason and yours side by side, classified (criterion badly written, judge prompt unclear, human error, genuine ambiguity), your confirmation of each class quoted; a correction after unblinding reported beside the sealed label; `record.md` in how-to 05's template (judge, sample, labellers, agreement, threshold, disagreements, verdict, next), generated, never edited by hand | `disagreements.jsonl`; a test that regenerates the record and compares; a test that the bar reads the sealed file; the ledger | `record.md` edited by hand: the regenerate test fails; a disagreement left without a class: `calibrate` refuses; a corrected label fed to the bar: the sealed-file test fails |
| JC9 | **Labels never judge examples, never reused.** No judge prompt version holds a run of 8 or more words from a labelled answer, quote or reason (the longest shared run reported); nothing under `src/raglab/judge/` names the calibration folder; any later calibration's sampler excludes every item of an earlier record | the leak test; the path test; the exclusion test | a labelled reason's sentence pasted into `judge_v2.py`'s rules: the leak test fails naming the item (the snapshot test fails too); a later sample allowed to reuse an item: the exclusion test fails |
| JC10 | **The threshold and its reason in THRESHOLDS.md.** The judged section: the v2 baseline; the bar with its reason and the commit that wrote it before the labels; per calibrated criterion its status, kappa with its interval, TPR and TNR, and the record's path; the uncalibrated criteria reported and never gated until calibrated; the recalibration triggers; AV2-J3's limit in one sentence; no judged pass rate given in the repository's docs without the record linked | a test that THRESHOLDS.md's calibration rows equal `record.json` (the status and kappa per criterion); review | a criterion marked trusted in THRESHOLDS.md while its record says reported only: the test fails |
| JC11 | **If a criterion misses the bar (D4).** Under A: its status, the classified causes and the follow-up in the record's "next" line and the ledger; nothing re-signed off or judged again in S6. Under B, with your go: the change signed off and quoted, the canaries on their side under it, the v2 baseline judged again and published, the first v2 record kept as history, the one-judge test made a history test, a fresh sample that excludes the first 30, labelled and sealed, and the bar read on it only. If no criterion misses: not applicable | the ledger; the record; under B, the second judged record and the second sample | under B, the fresh sample allowed to reuse an item of the first: the exclusion test fails; under A, a not-trusted criterion written as reported only: JC10's test fails |
| JC12 | **Docs and the standing criterion.** TEST-PLAN: section 10's judges line (kappa on n labels, with the record), R5's gate cell and its test, the Test column's words for the calibrated criteria; LOCAL-MODEL: the cap and the v2 judge session's measured time; ONBOARDING: `make label` and `make calibrate` with their expected output; ARCHITECTURE and README: S6 `done` (`wip` until the record); a CHANGELOG line; the ledger | `test_test_plan.py`, `test_diagram.py`, `test_readme.py`, `test_onboarding.py`, `test_repo_docs.py`, `test_changelog_check.py`; review | ARCHITECTURE's S6 class changed without the README's: `test_readme_status_matches_architecture` fails; R5's gate cell put back to "reported, not gated, until S6": its test fails |
| JC13 | **`make check`, and [CI] pr-fast green.** No new dependency (`pyproject.toml` and `uv.lock` unchanged); every published record validates; the retrieval gate and the dataset check pass | the `make check` tail with `/usr/bin/time -p` in the ledger; the pull request's checks | a planted lint error: `make check` stops at `lint` |

## Time

Every figure in this section is an estimate, with its basis, unless it says it was measured.

### Your tasks and time

1. **This plan,** with D1 to D5: about 20 to 40 minutes. Basis: S3's decisions round took 17 minutes
   (measured); S4's and answer-v2's plans were estimated at 30 minutes and S5's at 40.
2. **Labelling the 30 items:** about 1 h 15 min to 2 h 15 min, in one or two sittings. Basis: about
   2.5 to 4.5 minutes an item: S4b's plan rate of about 1.5 to 2 minutes to read and judge a golden
   case (an estimate), plus about 1 to 2.5 minutes for up to five passages of at most 1,200
   characters each, the quote and the reason. Under D1 A every item shows its passages. The main
   plan's figure is "about 1–2 hours" (an estimate). The CLI records the seconds per item, so S6
   replaces this estimate with a measurement.
3. **The re-label of 12 (D3 A),** at least a day later: about 30 to 55 minutes, at the same rate.
4. **The disagreements:** reading each with the judge's reason and confirming its class, about 15 to
   30 minutes. Their number is unknown before the labels; this assumes 2 to 8 in all (a guess).
5. **Questions the ledger raises:** about 15 minutes.
6. **The pull request:** about 45 minutes (S4b's and answer-v2's estimate).

In all, about 3 h 20 min to 5 h 20 min under D3 A. D3 B replaces the re-label with briefing the
second person, about 15 minutes; a D4 B loop adds about 1.5 to 2.5 hours (a sign-off and 30 more
labels).

### Mac time (live sessions)

| Work | Sessions | Each | Total |
|---|---|---|---|
| The dry run (scripted fake judge, no model) | none | under a second (S5's took 0.546 s) | — |
| The judged baseline on v2 (S6's first live step) | 1 judge session, `make judge-local RUN=<S4b's run 1>` | about 2 h 13 min to 2 h 21 min: 1,469 design calls at the measured 5.384 to 5.710 s, plus the contract test (33.11 s) and the start and stop | about 2 h 13 min to 2 h 21 min |
| The sample, your labelling, `calibrate` | none: no model | — | — |
| The criteria judge's live check | 1 judge session, `make judge-canaries` at the head: the judge pinned there passes its contract test and its canaries | about 2 min (S5: 2 min 2 s, twice, measured) | about 2 min |
| **In all, D4 A** | **2** | | **about 2 h 15 min to 2 h 23 min** |
| D4 B, if a criterion misses | +1 judge session, the re-judging | as above | adds about 2 h 13 min to 2 h 21 min |

- Each session runs through the `make` targets only, one model, on AC power: the power guard
  refuses on battery and stops a session that loses power, publishing nothing. Nothing else runs
  beside it, `make check` least of all. You serialize it against S7's and S9's sessions; it cannot
  overlap S4b's, because its source is S4b's published run.
- **Sleep.** `pmset -g`, read for this plan on 2026-10-23, gives idle sleep after 1 minute in the
  profile in use, "sleep prevented by caffeinate, powerd". If the Mac sleeps mid-session, the run
  pauses: its cap counts awake time only (S5 ledger), so a sleep costs time, not the run.
- The session logs print no clock (answer-v2's AV2-J5), so the Mac-time tables rest on the
  developer's shell readings, kept in the progress file.

### Agents' time

| Role | Work | Estimate |
|---|---|---|
| Developer, offline (Opus 5.5) | the bar file and guide, the draw, the label CLI, `calibrate` and the record, the one-judge test, the tests, the docs' drafts | 3 to 4 h (S3's full stage took about 2 h, measured; this build adds a CLI, a statistics module and their tests) |
| Developer, live and after | the merge of `main`, the dry run, the cap, the session (about 2 h 20 min of waiting on the Mac), publishing, the sample; after your labels: `calibrate`, the disagreements' drafts, THRESHOLDS.md and the docs | about 3.5 to 4.5 h elapsed, of which about 1 to 1.5 h of work |
| Criteria judge (Fable 5.1) | the evidence again, every number recomputed from the files, the breaks, one live check | 1 to 2 h (S3's full judge took about 1 h, measured) |
| Fix rounds | at most two | about 1 h each |

The elapsed time is set by S4b's merge, your labelling and the day before the re-label.

## How it will run

1. **Approval:** D1 to D5, quoted under Approval. From its first commit the developer keeps the
   ledger, `docs/plans/2026-10-23-s6-judge-calibration-ledger.md`: each criterion's evidence, every
   run, every finding and every answer of yours, verbatim.
2. **Build, offline** (developer, Opus 5.5), which can start before S4b merges: the bar file and the
   guide first, in a commit of their own; then the draw, the label CLI, `calibrate`, the record, the
   one-judge test's new form (the cap still 7,200), the tests (against fakes, with the v1.1 records
   as fixtures that are never sampled for labels) and the docs' drafts, with `make check` green. No
   live session.
3. **After S4b merges:** `main` merged into this branch, `make check` green, then the dry run on S4b's
   run 1 and the cap's commit.
4. **Live, the first step:** the judge session on S4b's run 1; the record published; THRESHOLDS.md's
   judged section moved to it, with aggregate numbers only.
5. **The sample:** drawn by `raglab calibrate`, committed.
6. **Your labels:** `make label` in this worktree; the seal; your attestation; the developer commits
   both files as written.
7. **The agreement:** `raglab calibrate`; the disagreements shown to you and classified; your
   confirmations quoted; the record generated.
8. **D3 A's re-label,** at least a day after the seal; sealed, committed; the record generated again.
9. **The verdicts by the bar.** Under D4 B and a miss: the loop, with your go.
10. **Docs,** and `make check` green again.
11. **The criteria judge** (Fable 5.1, its own worktree and context): re-runs the evidence and
    recomputes every number from the record's files and the published judged record; checks the
    commit order of the bar, the sample and the labels; makes each criterion's break at the head it
    judges, and restores each; runs one `make judge-canaries` session at the head, on AC power; gives
    a verdict per criterion: met, not met, needs CI, or not applicable.
12. **Fix rounds:** at most two. Product choices come back to you; a fix never edits a sealed label;
    a third round needs your go.
13. **Report:** the pull request's body is the stage report: n of m criteria met, what needs CI, what
    was cut, and the Mac time used. It carries a CHANGELOG line. You merge it by hand, with a merge
    commit.

Sequential subagents, unless your go asks for a Workflow. Hosted spend: none.

**Sign-ups: none.** S6 runs the local judge, by your choice for now: "let's use a local model for
now and then we need to identify all the signups and everything that I need to do" (S5's D6). It
needs no account, key or paid service; a second person under D3 B needs none either.

**What S6 gives later stages:** S7 the calibrated `grounded` verdict that its Provenance comparison
reads ("the calibrated faithfulness judge", main plan); S8 the criteria it may gate, the weighted TPR
and TNR for its margins, and the triggers; S11 the record for the capstone's "the judges and their
agreement".

## Decisions needed

**D1. Which criteria the 30 labels calibrate.**

- **A (recommended): "grounded and abstains, 15 each".**
  - What: 15 items per criterion, 7 judge passes and 8 judge fails, from the v2 record.
  - Why: they are the build project's stage 6, word for word ("supported or not, abstained correctly
    or not"); `grounded` is the faithfulness judge S7 compares its Provenance validator with; they
    carry R-18 ("Never invent a value") and R-03 ("Abstain when silent"); and 15 items allow a
    verdict per criterion, where one disagreement moves kappa by about 0.13.
  - What it changes: only `grounded` and `abstains` can be trusted to gate in S8. `correct`,
    `cites_support`, `relevant`, `refuses_and_helps` and `context_sufficient` stay reported,
    uncalibrated and never gated until labels of their own calibrate them; S8's suite audit lists
    them as a gap. Every item shows five passages: about 1 h 15 min to 2 h 15 min of labelling.
- **B: "Four with requirements: grounded, correct, abstains, refuses_and_helps (8, 8, 8, 6)".**
  - Adds R-01 and R-11 (`correct`) and R-14 (`refuses_and_helps`).
  - But kappa on 8 items moves by 0.25 a disagreement (one disagreement at 4 and 4 gives 0.75, under
    the 0.80 line), so under D2 A any disagreement keeps a criterion from being trusted. And
    `refuses_and_helps` had no judge fail in either v1.1 record (6 of 6 passes each), so its fail
    stratum may be nearly empty and its kappa undefined.
  - What it changes: up to four criteria get a verdict, each on thinner evidence.
- **C: "All seven, about 4 each".**
  - A pooled kappa over every judged criterion; no per-criterion verdict on 4 items.
  - What it changes: the bar can read only the pooled kappa, so S8 gates every judged criterion on
    it, or none.

**D2. The bar, written before any label.**

- **A (recommended): "kappa 0.80 trusts, under 0.60 stops".**
  - What: per criterion, kappa 0.80 or more is trusted (S8 may gate on it), 0.60 to under 0.80 is
    reported only, and under 0.60 is not trusted.
  - Why: how-to 05's template ("kappa >= 0.80 to trust; below 0.60 stop using") and McHugh's
    reading; on 15 items, trusted means at most one disagreement (the table above).
  - What it changes: a criterion with two disagreements of 15 stays reported only.
- **B: "kappa 0.60 trusts".**
  - McHugh's moderate as the trust line: two disagreements of 15 are still trusted, three are at the
    line, and under 0.60 is not trusted.
  - What it changes: more criteria may gate in S8, on a judge that may disagree with you about once
    in seven items.
- **C: "Nothing gates on 30 labels".**
  - The record is reported whatever the kappa. Every judged criterion stays reported until a fuller
    study, about 30 labels per criterion (how-to 05).
  - What it changes: S8 gates on no judged criterion, and THRESHOLDS.md says so and why.

**D3. The second labeller.** You are the only labeller this plan knows of.

- **A (recommended): "One labeller, plus a blind re-label of 12".**
  - What: the single-labeller caveat, and, at least a day after the seal, you label 12 of the 30
    again (6 per criterion, drawn with the seed, in a new order), through the same CLI, which shows
    neither your first labels nor the judge's verdicts.
  - Why: your agreement with yourself is the nearest stand-in for how-to 05's human-to-human
    agreement that one person can give, and it is reported as exactly that.
  - Cost: about 30 to 55 minutes more.
- **B: "A second person labels 12".**
  - What: someone you choose, recorded by role and never by name, labels a seeded 12 blind, with the
    same CLI and guide: human-to-human kappa, judge to each, judge to consensus (how-to 05 step 3)
    on those 12. The bar still reads the judge against you, on 15 per criterion.
  - Cost: about 30 to 45 minutes of their time, a clone with `uv sync` (or your Mac), and about 15
    minutes of yours to brief them.
- **C: "One labeller, caveat only".** No measure of your label noise.
- What each changes: the record's labellers and agreement lines, and your time. Under A or C, how-to
  05's "a judge that agrees with humans less than the humans agree with each other is not ready"
  cannot be checked as written.

**D4. If a criterion misses the bar.**

- **A (recommended): "Record it; fix in a follow-up".**
  - What: the criterion's status (reported only or not trusted), its disagreements classified, and
    the follow-up named in the record's "next" line. Nothing is signed off again or judged again in
    S6.
  - The follow-up pull request: by the classified cause, a reworded rule (CRITERIA.md's third
    sign-off) or judge-v3; the canary set signed off again only if a side changes; the canaries run;
    the v2 baseline judged again (about 2 h 15 min of Mac time); a fresh sample that excludes the
    first 30, labelled by you (about 1.25 to 2.25 hours); the bar read on the fresh sample only.
  - Why: one fix and its fresh calibration is about the size of S6 again. S6 then merges with an
    honest record, and S7 and S8 know which criteria are trusted.
- **B: "One fix inside S6, with my go".**
  - What: the same steps in this pull request, at most once, after your go; the first v2 record stays
    published as history.
  - Cost: about 2 h 15 min more Mac time, and about 1.5 to 2.5 hours more of yours (the sign-off
    and 30 more labels).
- Either way: the v1.1 judged records and the position test's are never judged again, and a sealed
  label is never edited.

**D5. This plan.**

- **"Approve and start (Recommended)":** the offline build starts on `feat/s6-judge-calibration`; the
  first live step waits for S4b's merge.
- **"Changes first":** say what to change, and the plan comes back.

## Risks

- **The judge misses the bar.** S5's caveats point at `grounded`'s reading of answers that state
  nothing; D4 decides what follows.
- **Thin numbers.** One disagreement moves kappa by about 0.13 on 15 items; the intervals are wide;
  30 labels are a precursor.
- **The longest session yet,** more than two hours: a hang spends up to the cap (3 h 30 min at the
  design count); a sleep pauses the run; a cap set too low makes the run partial and unpublishable,
  and the rule's margin of 1.5 over the slower measured mean is there to prevent it.
- **Short strata.** `c14acb0`'s 11 `abstains` passes came from 4 cases; the draw's shortfall rule
  then takes second trials, or items from the other stratum, and the record says so.
- **Blindness leaks.** The published record is one command away; the procedure, the attestation and
  the ledger's aggregate-only rule are the guards.
- **Labeller drift and fatigue.** Two sittings; the CLI records the time per item; D3 A's re-label
  measures the drift.
- **Weighted TPR and TNR swing on one item,** so the bar does not read them; S8 reads them, with their
  intervals, when it sets a margin.
- **S4b slips, or its counts move.** The offline build goes ahead; the live step waits; the dry run
  recounts before the cap is set.
- **Merge conflicts** in the shared files above with S7 and S9: S6 merges after S4b, and the
  orchestrator sequences the rest.
- **Privacy.** Your reasons are free text and are committed: the privacy check, gitleaks and the
  hooks read them like any file.
- **The command guard.** If it refuses a command, the developer splits it, or reports it, and never
  routes around it.

## Approval

The go for this draft (2026-10-23, about 22:45 WEST), verbatim: "S6 planner (Recommended), S7
planner (Recommended), S9 planner", the answer to "Which planners should I launch now, next to
S4b's? Each writes its plan only, in its own worktree, and stops for your approval.", after you
asked: "can we launch more sub agents in parallel to that one to speed up the development phase for
upcoming steps into the plan?"

**The approval (2026-10-23, about 23:30 WEST).** The question, verbatim: "S6, judge calibration.
Approve with all five recommended answers? D1: calibrate grounded and abstains, 15 labels each. D2:
kappa 0.80 or more trusts a criterion, under 0.60 stops it. D3: you label alone, plus a blind
re-label of 12 at least a day later. D4: a miss is recorded and fixed in a follow-up PR. D5: approve
and start. Your time is about 3 h 20 min to 5 h 20 min, and the Mac needs one judge session of
about 2 h 15 min after S4b merges."

Your answer, verbatim: "All five as recommended (Recommended)".

The answer selects each decision's recommended option:

- **D1:** "grounded and abstains, 15 each (Recommended)". 15 items per criterion, 7 judge passes
  and 8 judge fails, from the judged baseline on v2; the other five criteria stay reported,
  uncalibrated and never gated until labels of their own calibrate them.
- **D2:** "kappa 0.80 trusts, under 0.60 stops (Recommended)". Per criterion, kappa 0.80 or more
  is trusted (S8 may gate on it), 0.60 to under 0.80 reported only, under 0.60 not trusted.
- **D3:** "One labeller, plus a blind re-label of 12 (Recommended)". The single-labeller caveat,
  and a blind re-label of 12 of the 30 (6 per criterion, drawn with the seed, in a new order) at
  least a day after the seal, through the same CLI.
- **D4:** "Record it; fix in a follow-up (Recommended)". A criterion that misses the bar is
  recorded with its classified causes and the follow-up named in the record's "next" line; nothing
  is signed off again or judged again in S6.
- **D5:** "Approve and start (Recommended)". The offline build starts on
  `feat/s6-judge-calibration`; the first live step waits for S4b's merge.

## Sources (read 2026-10-23)

- [H1] AI Testing Handbook, the RAG build project, "Stage 6: calibrate the judge (playbook 05)":
  https://raw.githubusercontent.com/willcoliveira/ai-testing-handbook/main/learning-path/rag-build-project.md
- [H2] AI Testing Handbook, how-to 17, "Test a RAG application", step 10:
  https://raw.githubusercontent.com/willcoliveira/ai-testing-handbook/main/how-to/17-test-a-rag-application.md
- [H3] AI Testing Handbook, how-to 05, "Calibrate the evaluator", steps 1 to 8 and the record
  template:
  https://raw.githubusercontent.com/willcoliveira/ai-testing-handbook/main/how-to/05-calibrate-the-evaluator.md
- The repository at `2b9ba60`: the main plan; the S5 and answer-v2 plans and ledgers; S4b's plan at
  `f6f7d7e` on `feat/s4b-golden-set-v2` (read only); docs/CRITERIA.md, docs/THRESHOLDS.md,
  docs/TEST-PLAN.md, docs/LOCAL-MODEL.md; `config/judge-local.toml`; `datasets/canaries.judge.jsonl`;
  `src/raglab/evals/judged.py`, `judged_record.py`, `publish.py` and `config.py`;
  `tests/judge/test_answer_v2_one_judge.py`; the judged records' manifests and lines under
  `runs/published/`.
