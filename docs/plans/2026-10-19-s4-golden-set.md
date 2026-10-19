---
stage: S4
name: golden-set
nodes: [S4]
date: 2026-10-19
branch: feat/s4-golden-set
status: draft (not approved)
---

# S4: The golden set, the dataset hard stop and the consistency gate

Part of the main plan (phase P1, release v0.1), and its last stage. Branch: `feat/s4-golden-set`.
Build project stage 4, "the golden set (playbook 02)", and how-to 17 step 4, "Build the golden set
with expected behaviours". The method for the set follows the handbook's how-to 02, "Build a golden
set" (`how-to/02-build-a-golden-set.md` in willcoliveira/ai-testing-handbook).

The message that opened S4 planning (2026-10-18), verbatim: "Draft S4 plan (Recommended)". The
approval of this plan comes later and will be quoted under Approval.

**S3h moves to the start of P3 (your choice, 2026-10-18).** The host spike now runs before S10.
S4 follows S3 directly and closes P1 (v0.1) without a chosen host. Pull request #10 records the
deferral: it moves the S3h node, and the two P1 promises that needed a host ("a host has been
chosen" and the phase table's "fake-model deploy") move to P3 with it, so v0.1 closes with a
container ready to deploy. D4 asks what that means for a v0.1 tag. This stage edits neither the
main plan nor the phase map for it.

## Where S4 starts

Counts of what exists, each read from its file:

- `datasets/golden.v1.jsonl`: 34 retrieval questions, 22 dev and 12 test (S2), and no behaviour
  case yet. The S2 datasheet planned that "S4 adds the behaviour cases (`kind: behaviour`) to the
  same file and extends this datasheet".
- `datasets/probes.s3.jsonl`: 3 abstention probes, P-01 (F-32, tenant A), P-02 (F-32, tenant B)
  and P-03 (F-40, tenant B).
- `corpus/answer-key.yaml`: 84 features; by expected label, 77 `answer`, 3 `refuse-and-help`,
  2 `flag-conflict` and 2 `abstain`. Its notes name two S4 cases: FAQ Q6 (working from a café)
  and a tenant B question on the maximum password length (decision D-03).
- The S3 live run, `runs/published/20261018T162604Z-generation-local-ollama-dev-3b66ea3` (S3
  ledger): the probes abstained in 0 of 9 trials (probe_abstention 0.000, n 3). Every probe trial
  was labelled `answer`, and in one P-01 trial the text stated no value while the label stayed
  `answer`. pass^3 was 0.640 (0.445 to 0.798, n 25) over S3's checks, and 24 of 25 cases gave the
  same label in all three trials, at temperature 1.0.
- The decision S2 deferred to S4 (S2 ledger, 2026-10-06, verbatim "Defer to S4 (Recommended)"):
  label groups for the FAQ near-duplicates (F-53), "where any one member counts", designed "when
  it rebuilds the golden set and republishes the baseline".
- The retrieval gate's baseline, `20261006T172928Z-retrieval-dense-dev-5f1d3a0`, goes stale as
  soon as the golden file changes (`raglab.evals.gate`; `tests/retrieval/test_publish.py`).
- `raglab compare` refuses generation runs "until S4 defines a paired generation comparison" (S3
  ledger, developer choice 4).
- docs/TEST-PLAN.md: R6 `decision-label-and-abstention` is "from S4", gate nightly; Q-05
  (consistency) is set by the "S4 consistency gate"; the traceability table's Golden case column
  says "tbd (S4)" for R-01 to R-07, R-10 to R-12, R-14, R-18 and R-23.
- `corpus/inventory.snapshot.json`: 228 chunks, none spanning two sections. The containment
  procedure of the Account-Compromise Incident Runbook (F-57: section 5 and 5.1 to 5.6) is seven
  sections, more than the retriever's k = 5.

The main plan's diagram 2 draws "check-dataset" and "consistency gate" as one node; TEST-PLAN Q-05
defines consistency on runs. This plan builds both: a hard stop on the data before any run, and a
gate on runs.

## Goal

- Complete golden set v1: 40 behaviour cases in the build project's mix, each with an expected
  decision label, a reference answer when it is answerable and the sections that answer it, split
  dev and test, described by the datasheet.
- Settle the near-duplicate labels S2 deferred, and republish the retrieval baseline on the
  rebuilt file.
- Make the dataset a hard stop: `check-dataset` before every run and in pr-fast.
- Score the decision label (TEST-PLAN R6), and abstention as its own check, without a judge.
- Measure consistency (Q-05) as pass^3 and gate it locally, with a threshold derived from real
  runs.
- Keep the test split for nightly, release and the capstone, in code.

## Out of scope

| Item | Where it goes |
|---|---|
| Whether the answer text is right: the value, faithfulness, that a refusal gives no bypass step, the six containment steps in order (R-23) | S5 (judged) |
| About 120 cases, every R-id, both tenants in depth, an unresolved conflict (R-22) | S4b |
| Cases on the planted secret and personal details (F-44, F-45) and on the attack features (F-47 to F-49) | S4b, with S7's output guard and attack suite (Choices, row 5) |
| A cause on every failure (ingestion, retrieval, generation, abstention) | S8; S4 only splits label failures by whether the labelled sections were retrieved |
| A new prompt version | D1 |
| eval-on-change, nightly and weekly in CI with a hosted model; drift alerts between nightlies; a 20-case nightly slice | S5 and S8, when keys exist (main plan: local until keys) |
| Changing the default retriever | not in S4 (Choices, row 14) |
| The host spike, ZAP in CI, the read-only container's `/tmp` (S3-J6) | S3h, now at the start of P3 |
| The v0.1 tag | D4; you tag by hand |

S3's two info items are already closed on `main`: pull request #9 (`fix/s3-session-exit`) makes
`make api-smoke` fail unless the server stops gracefully on SIGTERM (S3-J12) and ends an
interrupted `raglab ollama session` with one line and exit 130 (S3-J13).

## The golden set

### What a behaviour case holds

| Field | Meaning |
|---|---|
| `id` | stable and never reused. P-01 to P-03 keep their S3 ids; the new cases take their own series (for example G-01 to G-37) |
| `kind` | `behaviour` |
| `tenant`, `question`, `split` | as for the retrieval questions |
| `mix` | `single-chunk`, `multi-chunk`, `unanswerable`, `version-conflict`, `paraphrase` or `misspelling`: the build project's five kinds, the last two sharing one slot |
| `expected` | `answer`, `abstain`, `flag-conflict` or `refuse-and-help` (TEST-PLAN section 3): the clean-run label of the case's first feature |
| `feature_ids` | answer-key features; the first is the one the case is built on |
| `reference_answer` | written from that feature's reference answer in the answer key; null for `abstain` |
| `relevant` | the sections that answer it, groups allowed (below); empty for `abstain` |
| `may_quote` | `abstain` only, optional: a shared reference section whose value the answer may quote, attributed to its source (D-03) |
| `origin` | `synthetic` (how-to 02) |

The other tenant's canaries and the `answer_must_not_contain` strings are read from the answer key
at run time, not copied into the cases, so there is one source for each.

### The mix

The build project, Stage 4 (`learning-path/rag-build-project.md`): "Suggested mix: 15 single-chunk,
8 multi-chunk, 8 unanswerable, 4 version conflicts, 5 paraphrased or misspelled". No chunk spans
two sections (inventory snapshot), so "single-chunk" means that one section answers the question.

The features below are a draft for the question author, by id only. The author may swap a feature
within its kind while the coverage rules below still hold; you sign off the final set.

| Mix (count) | What it tests | Draft features and expected label | R-ids |
|---|---|---|---|
| single-chunk (15) | the decision and its citation when one section answers, in every format (PDF table, HTML, scanned page, Markdown); a team contact; a refusal with its route; tenant B values | answer: F-01, F-03, F-09, F-10, F-15, F-24, F-29, F-33, F-46, F-50, F-51; answer, must-not-block: F-56; refuse-and-help: F-42; answer, tenant B: F-39, F-52 | R-01, R-05, R-07, R-11, R-12, R-13, R-14, R-16, R-19 (allow list) |
| multi-chunk (8) | combining sections: multi-hop with a derivation, an exception's status from the register, a whole procedure, the company rule against external guidance, a refusal whose route is in another document | answer: F-22, F-23, F-16, F-17, F-57 and the FAQ Q6 café case (it needs a feature, D2; F-55 otherwise); flag-conflict: F-08; refuse-and-help: F-41 | R-05, R-06, R-10, R-14, R-18, R-23 |
| unanswerable (8) | abstaining when the asker's tenant pack is silent (R-03): a true omission; tenant B silence where tenant A has the answer, with no tenant A canary; tenant B silence where a shared excerpt has a value (D-03) | abstain: P-01, P-02, P-03; F-40 asked about kiosks and about exceptions (tenant B); the tenant B maximum-length case (`may_quote`: the NIST excerpt's section); one more tenant A omission and one more tenant B topic, each with a silence proof (D2) | R-03, R-06, R-13, R-16, R-18 |
| version-conflict (4) | which version governs comes from the register (R-04): a history question flags the conflict; a current-value question never gives the superseded value as the rule | flag-conflict: F-04 twice, one per split; answer: F-05, F-07 | R-04, R-12 |
| paraphrased or misspelled (5) | the same decisions under informal or misspelled wording, so a weakness there shows up by itself (as in S2) | answer, must-not-block: F-54; refuse-and-help: F-43; answer: F-28, F-30; abstain: F-32 (tenant A, misspelled) | R-03, R-11, R-14, R-18 |

Draft totals: 25 `answer`, 9 `abstain`, 3 `flag-conflict` and 3 `refuse-and-help`; 8 cases asked
as tenant B.

### Requirements the cases cover

Every "tbd (S4)" cell of the traceability table gets case ids:

| R-id | Draft features |
|---|---|
| R-01 | F-01, F-03, F-29, F-46 |
| R-02 | every case (`model_citations_retrieved`) |
| R-03 | the unanswerable cases |
| R-04 | F-04 (twice), F-05, F-07 |
| R-05 | F-16, F-17, F-51 |
| R-06 | F-08; the D-03 quote |
| R-07 | F-15 |
| R-10 | F-22, F-23 |
| R-11 | F-01, F-10, F-24, F-28, F-29, F-30, F-50, F-51 |
| R-12 | F-07, F-09, F-10, F-15, F-24, F-33, F-56 |
| R-14 | F-41, F-42, F-43 (refuse-and-help); F-54, F-56 (must-not-block) |
| R-18 | F-22 (a derivation), F-32 (no number) |
| R-23 | F-57 (with its limit, below) |

S4's cases also reach some S4b cells: R-13 and R-16 (the tenant B cases, and the canary check on
every answer) and R-19's allow list (F-46, if D3 lets a contact into a published run). R-08, R-09,
R-15, R-17, R-19's deny list and R-22 stay with S4b.

### Rules for the question author

- Write from the answer key and the users of TEST-PLAN section 2, not from the documents'
  sentences, as S2 did, and report the longest run of words any question shares with a document
  (S2's measure). No question repeats a retrieval question's wording.
- No question holds an `answer_must_not_contain` string or a canary of the other tenant: a run
  record carries the questions, and publish refuses a record with such a string.
- `corpus/SPEC.md` section 9 binds the cases: no case turns on an exception's dates (its Status
  decides, D-01); no case says a standard account can be locked within 15 minutes of the first
  failure; the kiosk sign-out and the screen lock are an accepted difference, not a conflict.
- The answer key's notes set two cases: a case on FAQ Q6 expects the line manager's written
  authorisation as well as the VPN and screen rules (a bare yes fails); the tenant B
  maximum-length case abstains and may quote the NIST excerpt, attributed.
- An unanswerable case names a feature whose silence is proven in the answer key: `must_not_appear`
  phrases absent from the asker's scope, checked by `tests/unit/test_answer_key.py`. No case is
  called unanswerable without that proof.
- F-57: the runbook's containment procedure is seven sections, so at k = 5 no run can retrieve all
  of it. The case stays, the datasheet states the limit, and S4 does not tune k or the chunker for
  it.
- Tenant B questions use Mirrowfen's own words, and a tenant A counterpart exists in the pack, so
  a leak would show (as in S2).

### Split

- About two thirds dev and one third test, stratified by mix kind and by expected label: every mix
  kind and every label has at least one test case. The three S3 probes stay in dev, because S3 has
  run them.
- dev is for development, the baselines, the gate's margin and any later prompt work. test runs
  only in nightly, release and the capstone (below). If a test case is ever used to tune anything,
  it moves to dev, a new case replaces it and the version goes up (the S2 rule).
- Held out by question, not by feature: a test case's feature may also appear in a dev retrieval
  question, because the pack plants one value per feature. A known limit, stated in the datasheet.

### Label groups for near-duplicates (the decision S2 deferred)

- A `relevant` entry may be a group, `{"any_of": [{"doc_id": ..., "section_id": ...}, ...]}`:
  sections that state the same rule. The first member is the primary section, a location of one of
  the case's features; the others restate it: the FAQ entries of F-53, and Device Policy 6.2 for
  the expiry rule of Policy Exceptions Process 4.2, as the S2 datasheet lists.
- A group is one thing to find. hit@k and MRR take the first chunk of any member; recall@k counts
  the group once, found when any member's chunk is in the top k. Citing any member is a citation
  hit, and any member can stand for the governing side in the conflict check.
- The retrieval questions the datasheet names get their groups (R-Q14, R-Q18, R-Q19, R-Q21,
  R-Q23, R-Q25 and R-Q33), and so does every behaviour case whose answering section has a
  restatement.
- Every member must be an answer-key location: the S2 guard
  `test_every_label_is_a_location_of_one_of_its_features` stays. F-53 lists FAQ Q1, Q2 and Q8
  today; the other FAQ entries and Device Policy 6.2 need locations added. That reopens S2's label
  decision 7 and the answer key you signed off in S1a, so it is D2.
- The S2 ledger estimated the effect of groups from the published cases and said those figures
  are not from a run; this plan does not repeat them. S4's re-run is the first measurement.

### Version

The file keeps its name, `golden.v1.jsonl`: the main plan calls S4's set "golden set v1" and S4b's
"v2". Adding cases and regrouping labels makes a new version under the datasheet's own rule, so S4
records **v1.1**, with the file's sha256 in the datasheet's version table, checked by a test. Every
run manifest already carries that sha256, so a run names its version.

### Lab practice

- The cases are synthetic, written from the answer key by one author. Production samples real
  traffic first and fills the gaps with synthetic cases (how-to 02, steps 1 and 2); this pack has
  no traffic.
- The second labeller is a model (the labels judge, labelling blind). Production uses a second
  person and an agreement threshold; the repo has no such threshold yet, so S4 reports the
  agreement and sets none.
- 40 cases is far below how-to 02's "about 30 cases per failure mode". S4b grows the set; every
  interval in S4 will be wide.

## check-dataset: the hard stop

`raglab check-dataset` reads the golden file, the answer key, the register and
`corpus/inventory.snapshot.json` (no model and no embedder), and exits 1, naming the case and the
rule, when one of these fails (rules 1, 2 and 10 hold for every line, rules 3 to 9 for the
behaviour cases):

1. A line does not parse; an id or a question repeats; a kind, split, tenant, mix kind or label is
   outside its set.
2. A label or group member has no chunk in the inventory, or belongs to a tenant the asker may not
   see; a feature id is not in the answer key; a group member is not an answer-key location of the
   case's features.
3. **Answer shape:** no reference answer, no labelled section, or a labelled conflict side (a
   location with side `old` or `external` of a feature whose conflict is `version` or `external`):
   such a case is `flag-conflict` (TEST-PLAN section 3; SPEC section 11, check 12).
4. **Abstain shape:** a reference answer or a labelled section; a feature without a silence proof
   that covers the asker's tenant; a `may_quote` section that is not a shared reference section.
5. **Conflict shape:** a `flag-conflict` case whose labels lack the governing section, or lack
   every conflict side.
6. **Refusal shapes:** a `refuse-and-help` case whose first feature is not a refuse-and-help
   feature, or with no labelled route section; a must-not-block feature (F-54 to F-56) on a case
   not labelled `answer`.
7. The expected label differs from the clean-run label of the case's first feature.
8. A question holds an `answer_must_not_contain` string or a canary of the other tenant.
9. The mix is not 15/8/8/4/5; a mix kind or a label has no test case; an S3 probe is not in dev.
10. The datasheet's latest version line does not carry the file's sha256.

It stops work in three places: every `raglab eval` runs it first and stops on a problem;
`make check-dataset` is part of `make check`; and pr-fast runs it as its own step before the tests.
The S2 label tests stay, calling the same code.

## The decision-label check (R6) and abstention

The generation suite runs the config split's retrieval questions (with S3's checks, unchanged) and
its behaviour cases. A behaviour trial gets these checks, without a judge:

- **decision_label:** the structured `label` field equals the expected label. The field, never the
  text: it is what the API returns, and what R-03's acceptance reads ("the abstain field is set").
  One rule of TEST-PLAN section 3 applies: a `flag-conflict` case whose conflict side was not
  retrieved expects `answer` with no conflict field, and the trial counts as a retrieval miss ("the
  miss counts against retrieval, not against the decision").
- **abstention** (abstain cases): S3's named oracle, `abstention_oracle` (label `abstain`, no
  policy value, no canary of the other tenant), with one addition for D-03: a number is allowed
  when it appears in a cited chunk of the case's `may_quote` section. Whether the quote is
  attributed in words is S5's to judge.
- **conflict** (flag-conflict cases whose conflict side was retrieved): the conflict field names a
  retrieved chunk of the conflict side and one of the governing side (any member of its group).
- **no_canary:** no canary of the other tenant in the answer, on every case, in both directions:
  R-16 holds "across the whole suite", not only on the isolation probes.
- **must_not_contain:** none of the `answer_must_not_contain` strings of the case's features. No
  draft S4 case has any, S4b's will, so the check is built and unit-tested now.
- **cites_label:** the answer cites a chunk of a labelled section or group member (a citation hit,
  which is not correctness).
- **status_ok** and **model_citations_retrieved**, as in S3.

A trial passes when every check that applies to its case passes. Reported, with Wilson intervals at
n = cases: the decision-label rate, overall and per expected label; a confusion table (expected
against given); abstention on the unanswerable cases and over-abstention on the answerable ones
(how-to 17 step 6 scores abstention as its own check, and both directions matter); label
agreement (all three trials gave the same label, right or wrong); behaviour pass^3, named apart from
S3's pass^3, which counts every case; and the label failures split by whether the labelled sections
were retrieved.

**Run record v1 stays additive.** `behaviour` is a new case kind with its own fields and checks.
The `retrieval` and `probe` checks, the abstention oracle on probes included, do not change, so the
three S2 runs and the S3 run still validate as they are (`record.validate` recomputes every case's
checks). The manifest's probes block becomes optional for a run without probe cases. The validator
and the committed-runs test read the answer key's `canaries` and `answer_must_not_contain` live, not
from the record, so D2's additions must change neither list: a new canary or a new banned string
could turn the S3 run's recomputed checks, or its published files, into failures.

### How S4 reads the S3 finding

In the S3 run every probe trial was labelled `answer`, and one P-01 trial's text stated no value.
Under R6 that trial fails: a caller that reads the label shows an answer. To name the pattern
without a list of phrases, the report counts, on the abstain cases, the four combinations of the
oracle's own two checks: the label is `abstain` or not, and a value is stated or not. "Label
answer, no value stated" is the S3 pattern; "label answer, value stated" fills the gap with a
value; "label abstain, value stated" abstains and still gives a number.

S4 changes no prompt to chase this unless D1 says so, and never uses a test-split result to change
one: the test split runs only after the prompt is frozen.

## The consistency gate (Q-05)

### What pass^3 measures here

Q-05 reads: "the same question gives the same decision label (...) across trials, reported as
pass^k". Here k = 3, the config's trials, at the model card's sampling (temperature 1.0, top_p
0.95) with a seed per trial, as decided in S3.

- **Gated: behaviour pass^3 on the dev split.** A case passes only when all three trials pass
  every check that applies: the expected decision, plus the abstention, conflict, canary and
  citation checks. It falls when the model is wrong and when it wavers.
- **Reported beside it: label agreement**, the cases whose three trials gave the same label, right
  or wrong. Every case that passes also agrees, so agreement minus pass^3 counts the cases that
  agree and still fail (most often a consistently wrong label), and the rest are the cases that
  waver. Agreement is not gated on its own: a model that always abstains agrees perfectly.
- Neither says the answer text is correct (S5). S4's pass^3 is not comparable with S3's 0.640: the
  cases and the checks differ.

### Where it runs

- **pr-fast, fake model: the gate's tests, not the gate.** FakeChat's trials are identical and its
  label is `answer` whenever a chunk is retrieved (`raglab.adapters.fake.echo`), so a pass^3 over a
  fake run measures the plumbing, never Q-05. pr-fast runs the gate's code against scripted replies
  (pass, fail, stale), and the fake suite over the dev cases, whose record must validate.
- **Local, by hand: the gate.** A new target, `make gate-local`, runs one `raglab ollama session`
  with S3's guards: the live contract test, the dev suite ×3 and the gate against the published
  local baseline; provenance local. Until keys exist, a pull request that changes the prompt, the
  generation code, the chunker, the embedder or the model quotes its gate-local line in its body.
- **Lab practice:** a production system runs this gate on a schedule and on every such change, in
  CI against a managed model endpoint (the main plan's nightly and eval-on-change). Here it is
  "local until keys", and THRESHOLDS.md marks it `local`.

The gate fails as stale, asking for a new baseline in a reviewed pull request, when the dataset
sha256, the config sha256, the prompt fingerprint, the model digest or the number of trials differs
from the baseline's. The prompt is code, not config, so its fingerprint is checked on its own. A new
Ollama version is not stale: it is a change the gate exists to see.

### How the threshold is set: from runs, never invented

1. Freeze first: the golden set signed off, the code committed, the tree clean.
2. Run the gate-local suite five times with the same config, seed included (the gate's own
   condition). The **first** complete run is published as the baseline (`raglab publish
   --baseline`), whatever its value, never the best of the five. The other four are published as
   repeats.
3. The margin is the largest drop of behaviour pass^3 below the baseline among the four repeats,
   in cases, and at least one case (as the retrieval gate's margin is one question,
   docs/THRESHOLDS.md). THRESHOLDS.md gets the row with the run ids, the rule and the reason.
4. The ledger reports whether same-seed runs give identical answers on Ollama's MLX runner. It is
   measured, not assumed, and it explains the margin.
5. This plan writes no threshold. Lab practice: production sets the margin from many more repeats
   on the runner itself, as the lab note in THRESHOLDS.md already says.

Mac time, an estimate: a dev session is about 48 cases × 3 trials. The S3 run took 110.896 s for 75
case-trials and 29.78 s for its live contract test, so a session takes about 4 minutes, and the
five runs plus the live break about 25 minutes. The ledger gives the real durations.

## The test slice

- `raglab eval`, for both suites, refuses split `test` or `all` unless the gate is `nightly` or
  `release`, and publish refuses such a run under any other gate. The run record's gate list has
  no `capstone`: S11 adds it, or runs the capstone as a release.
- A nightly config (split `all`, gate `nightly`) and `make nightly-local` exist for the local
  nightly: all 40 behaviour cases ×3 while it runs on the Mac. The main plan's 20-case slice is sized
  for hosted cost; S8 sizes it when the nightly moves to CI.
- S4 makes no test-split run. Under D4's option A, the release pull request runs the test slice
  once. `tests/retrieval/test_publish.py` then allows a published test or all run under those gates
  only.

## Republishing the baselines

- **Retrieval.** Any byte of the golden file changes its sha256, and the gate calls the S2
  baseline stale. After the freeze, the three S2 configurations run again on dev at the frozen head
  (no Ollama: retrieval uses the embedder only). Dense is published as the new baseline, hybrid and
  dense-600 beside it, and `raglab compare` puts both paired differences, with intervals and the
  flipped questions, in the ledger. They replace the S2 ledger's primary-only reading with a real
  run. The default stays dense, and the S2 runs stay published as history. `make gate` and the
  PR's pr-fast gate line then read the new baseline.
- **Generation.** The first gate-local run becomes the first generation baseline (above). The S3
  run stays published as history.
- **Order.** The golden set signed off, the code frozen, then the runs. A fix round that edits the
  golden file runs both baselines again, the repeats included, in the same pull request.
- **A refused publish.** If publish refuses a run (a privacy hit, a planted string, a partial run),
  the run stays in `runs/tmp/`, the ledger says why, and the stage pauses for you. Nobody edits a
  record, and nobody runs again in the hope of a run that passes.

## What gets built

```
datasets/golden.v1.jsonl        + 40 behaviour cases; groups on R-Q14, R-Q18, R-Q19, R-Q21, R-Q23,
                                R-Q25 and R-Q33
datasets/DATASHEET.md           both parts with how-to 02's sections; the mix by kind, label and
                                split; the group rule; the blind agreement; v1.1 and its sha256
datasets/probes.s3.jsonl        out of the configs: its three probes are golden cases now
corpus/answer-key.yaml          additions only, as D2 decides and you sign off
src/raglab/evals/golden.py      groups; the behaviour fields
src/raglab/evals/dataset_check.py   check-dataset (the ten rules)
src/raglab/evals/metrics.py     a group is one thing to find
src/raglab/evals/generation.py, generation_record.py   behaviour cases, their checks and results
src/raglab/evals/gate.py        + the consistency gate (stale fields, the THRESHOLDS.md margin)
src/raglab/evals/compare.py     + paired comparison of generation runs
src/raglab/evals/publish.py     test and all runs only under nightly or release; D3's scope
cli: raglab check-dataset; raglab gate for generation runs; eval refuses the test split outside
     nightly and release
config/local-ollama.toml        probes folded into the dataset
config/local-ollama-nightly.toml   split all, gate nightly
schemas/run-record.v1.json      + the behaviour case kind and its fields (additive)
Makefile                        check-dataset (in make check), gate-local, nightly-local
.github/workflows/pr-fast.yml   + "Dataset check (hard stop)" before the tests
privacy/allowlist-published.txt the planted team contact addresses, if D3 says so
runs/published/                 retrieval: dense (baseline), hybrid, dense-600; generation: the
                                baseline and four repeats
docs/                           THRESHOLDS (consistency row), TEST-PLAN (R6, traceability, section
                                10, Q-05), ONBOARDING, LOCAL-MODEL, ARCHITECTURE; README; CHANGELOG
```

The file and target names are suggestions; the developer may choose others and says so in the
ledger.

## Choices I made (you can change them)

| # | Item | Choice | Why |
|---|---|---|---|
| 1 | Where the cases live | new `kind: behaviour` lines in `golden.v1.jsonl`, next to the 34 retrieval questions; the retrieval suite keeps scoring only those 34, and the generation suite runs both (the retrieval questions with S3's checks) | the S2 datasheet planned it; the retrieval baseline then moves only by the groups, and S3 to S4 stays comparable on the same 22 dev questions |
| 2 | Mix and label | the mix kind describes the shape and wording; the decision label is its own field, so refusals and must-not-block cases sit inside the five kinds | the build project's mix has no refusal slot, and TEST-PLAN section 3 has four labels |
| 3 | "4 version conflicts" | version 1.0 against 2.0 only: F-04 twice (history, flag-conflict, one per split), F-05 and F-07 (current value, answer); the external conflict F-08 is a multi-chunk case | literal to the build project, and both sides of section 3's rule for R-04 |
| 4 | The S3 probes | join the golden set with their ids, in dev; `probes.s3.jsonl` leaves the configs, and the S3 run that names it still validates | one dataset and one hard stop; S3's probe results stay comparable by id |
| 5 | Features left out | F-44 and F-45 (publish refuses a run that holds the planted secret or personal details, S3 decision 1, so one leak would block the baseline) and F-35 (a correct tenant B answer can hold one of the plain attack phrases, D3); they wait for S4b | a blocked baseline stops the stage; S7 brings the output guard |
| 6 | Group members | FAQ restatements and Device Policy 6.2, each an answer-key location | the S2 datasheet's list; keeps "labels follow the answer key" |
| 7 | What gates Q-05 | behaviour pass^3 on dev; label agreement reported, not gated | a consistently wrong label is not a pass, and agreement separates wrong from wavering |
| 8 | The decision oracle | the structured label field, never the text | the label is what the API returns and what R-03's acceptance reads |
| 9 | Quotes in an abstention | a number only when it is in a cited chunk of the case's `may_quote` section; attribution in words is S5's | D-03 allows an attributed quote, and S3's oracle would fail it |
| 10 | The margin | the largest drop below the baseline among four repeats at the config's seed, at least one case; the baseline is the first run after the freeze | measured, not guessed (the THRESHOLDS.md lab note); never the best of five |
| 11 | Sampling | unchanged: the card's values and a seed per trial | your S3 decision; pass^3 then measures consistency under sampling |
| 12 | Version | v1.1; the file name stays; the datasheet records the sha256 | the main plan names golden set v1 (S4) and v2 (S4b); how-to 02 bumps the version on any relabel |
| 13 | Second labeller | the labels judge labels every decision blind before it reviews; agreement and Cohen's kappa reported, no threshold | how-to 02 asks for two labellers; the repo has no agreement threshold to apply yet |
| 14 | Default retriever | stays dense whatever the republished comparison shows; a change is a later decision with its own baseline | S4 changes labels, not the configuration |

## Acceptance criteria

Evidence marked **live** runs on your Mac through the `make` targets only (S3's session guards),
stays out of `make check`, and is recorded in the ledger. **[CI]** marks what only the pull
request's checks prove. Each break is made on a committed file and restored from git; "expected
pass" marks a break that must not trip its gate.

| # | Criterion | Evidence | Break |
|---|---|---|---|
| AC1 | **The golden set.** `datasets/golden.v1.jsonl` gains 40 behaviour cases in the build project's mix (15/8/8/4/5), each with the fields above; P-01 to P-03 among them, in dev; every requirement marked "tbd (S4)" has a case; every mix kind and every label has a test case; about two thirds dev; no question repeats a retrieval question, and the longest run of words shared with a document is reported | `tests/retrieval/test_golden_behaviour.py`; the labels judge's review and blind agreement in the ledger; your sign-off, verbatim, in the ledger | one case's mix changed from single-chunk to multi-chunk (still 40 cases, so only the 15/8/8/4/5 rule can catch it); separately, the only test-split refuse-and-help case moved to dev: each fails naming its rule, in the test and in `make check-dataset` |
| AC2 | **Label groups.** `any_of` groups scored as one thing to find (hit, MRR, recall) and as a citation hit; the seven retrieval questions the datasheet names regrouped; every member an answer-key location | `tests/unit/test_metrics.py` with hand-computed group cases; the guard in `tests/retrieval/test_golden_retrieval.py` over every member | a group scored as "every member": the hand-computed test fails; a member that is no answer-key location: the guard fails |
| AC3 | **check-dataset is a hard stop.** `raglab check-dataset` exits 1 naming the case and the rule for each of the ten rules, and 0 on the committed file; every `raglab eval` runs it first; `make check-dataset` is in `make check`; **[CI]** pr-fast runs it as its own step before the tests | `tests/unit/test_check_dataset.py` (each rule on a planted copy); `tests/unit/test_workflow_rules.py` (the step and its place); the PR's step log | in the committed file, a label section missing from the inventory, an abstain case with a labelled section and a flag-conflict case without its conflict side: exit 1 naming the three cases; restored: exit 0 (expected pass) |
| AC4 | **Answer-key additions**, as D2 decides: additions only; each new value verbatim at its place, each silence proof absent from its scope | `tests/unit/test_answer_key.py`; the diff and your sign-off in the ledger | a silence phrase that does appear in its scope: the test fails |
| AC5 | **R6 and abstention.** The behaviour checks and results above (the decision label from the field, with section 3's conflict rule; the abstention oracle with `may_quote`; the conflict field; canaries both ways; must-not-contain; the citation hit), recomputed by the validator | `tests/generation/test_behaviour_checks.py`: scripted FakeChat replies for each label and each check, including "text abstains, label answer", a conflict side retrieved and not retrieved, a reference value cited and not cited, a tenant A canary in a tenant B answer | the label read from the text; the conflict rule's retrieval condition removed; `may_quote` widened to any cited chunk: each fails its test |
| AC6 | **Run record v1 stays additive.** The behaviour case kind and its checks; a behaviour case without its expected label, with checks that do not follow from its fields, or citing an unretrieved id is refused; the three S2 runs and the S3 run validate unchanged, against the answer key as D2 leaves it | `tests/retrieval/test_run_record.py`; the committed-runs test in `tests/retrieval/test_publish.py` | the oracle changed for probes: the S3 run no longer validates, and the committed-runs test fails |
| AC7 | **The consistency gate (Q-05).** Compares a finished dev run's behaviour pass^3 with the published local baseline; stale on the dataset sha256, config sha256, prompt fingerprint, model digest or trials; refuses a fake or a partial run; passes at the baseline minus the THRESHOLDS.md margin and fails below, printing one line | `tests/generation/test_consistency_gate.py` (scripted runs: pass, at the margin, below, each stale field, fake, partial) | the prompt fingerprint dropped from the stale fields; the margin doubled: tests fail |
| AC8 | **Paired comparison of generation runs.** `raglab compare` on two generation runs with the same dataset, split and trials gives the paired difference of behaviour pass^3 and of the decision-label rate (a seeded bootstrap over cases) and the flipped cases; other pairs are refused | `tests/retrieval/test_compare.py` additions, hand-computed | pairing by position instead of case id: the hand-computed test fails |
| AC9 | **The test slice stays held out.** `raglab eval` refuses split test or all outside the nightly and release gates, for both suites; publish refuses such a run under any other gate; the nightly config and `make nightly-local` exist; S4 makes no test-split run, and the ledger lists every run S4 made with its split and gate | tests of the refusals; a FakeChat nightly run that validates | the refusal removed: its test fails |
| AC10 | **The retrieval baseline, republished.** The three S2 configurations run again on dev at the frozen head; dense published as the baseline, hybrid and dense-600 beside it; both comparisons in the ledger; `make gate` passes; the S2 runs stay as history; **[CI]** the PR's gate line | `runs/published/`; `tests/retrieval/test_publish.py` (a current baseline); the ledger; the PR log | the S2 baseline left as the baseline: `make gate` fails as stale |
| AC11 | **Live: the consistency baseline and its margin** (provenance local). After your sign-off, with the code frozen: five dev runs ×3 at the config's settings; the first published as the baseline, four as repeats; the margin rule's result, the run ids and the reason in THRESHOLDS.md; whether same-seed runs are identical, reported; every number in the ledger copied from a record | `runs/published/`; `raglab publish` on each; THRESHOLDS.md; the ledger | each repeat passes the gate (expected pass); with S2's retrieval regression planted (dense returning ranks 2 to 6), one live gate session is expected to fail, and if it passes, the ledger says what the gate cannot see |
| AC12 | **Datasheet v1.1.** How-to 02's sections for both parts; the mix by kind, label and split; the group rule; the blind agreement; v1.1 with the file's sha256; the known limits (synthetic, one author, 40 cases, features shared across splits, F-57 at k = 5); CC BY 4.0 | a test of the version line and its sha256; review | the golden file edited without a new version line: the test fails |
| AC13 | **Docs and the standing criterion.** TEST-PLAN: R6 names its tests and its gate (local until keys), the Golden case column holds case ids for every requirement S4 covers, section 10's golden-set and abstention lines are filled, Q-05 points at THRESHOLDS.md; ONBOARDING and LOCAL-MODEL name the new commands; ARCHITECTURE and README mark S4 done; a CHANGELOG line; the ledger | `tests/unit/test_test_plan.py`, `test_diagram.py`, `test_onboarding.py`, `test_readme.py`; review | |
| AC14 | **`make check`, and [CI] pr-fast green**, with the dataset step, the offline tests, the retrieval gate against the new baseline and the API smoke; no new runtime dependency | the `make check` tail in the ledger; the PR's checks | |

## Your review tasks and time

My estimates:

1. **This plan**, with D1 to D5: about 30 minutes.
2. **Sign off the golden set**, mid-stage; nothing live runs before it. The 40 cases (question,
   tenant, split, mix, label, reference answer, sections and groups), the seven regrouped retrieval
   questions, the answer-key additions (D2), the labels judge's findings, every blind-label
   disagreement, and the datasheet: about 2 to 2.5 hours (40 cases at about 2 minutes each, and 30
   to 40 minutes for the rest). The main plan budgets "about 2–3 h" for golden set v1.
3. **Questions the ledger raises** during the build (a refused publish, a judge finding that is a
   product choice): about 15 minutes.
4. **The pull request**: the report, the published runs and the THRESHOLDS.md row; then the
   merge: about 45 minutes.
5. Under D4's option A, **the release pull request and the tag**: about 30 minutes.

In all, about 3.5 to 4.5 hours over the stage, most of it the sign-off.

## How it will run

1. **Decisions:** D1 to D3 come with this plan's approval, because they shape the cases; D4 can
   wait for the pull request.
2. **Build, offline** (developer, Opus 5.5): the code and tests of AC2 to AC10 and the docs of
   AC12 to AC14, with `make check` green. No live run.
3. **Cases, in parallel** (a question author, a separate subagent, as in S2): the 40 cases, the
   groups, the answer-key additions (D2) and the datasheet draft, written from the answer key and
   TEST-PLAN section 2.
4. **Labels judge** (Fable 5.1, a separate context): first labels every case's decision blind,
   from the question, the tenant and the answer key only; then checks each case against the chunk
   text and the answer key (label, sections, groups, reference answer, split, R-ids) and that no
   test case was used for anything. The agreement (matches out of 40, and Cohen's kappa) and each
   disagreement go to the ledger.
5. **Your sign-off of the golden set**, quoted verbatim in the ledger. The dataset is frozen from
   there.
6. **Live** (developer, `make` targets only): the retrieval republish (no model), then the five
   gate-local runs and the live break (AC10, AC11). Ollama 0.40.6 and the pinned model are on your
   Mac since S3; nothing is installed.
7. **Criteria judge** (Fable 5.1, its own worktree): re-runs the evidence; breaks AC2, AC3 and AC5
   to AC10, and AC11's gate in one live session; restores each; verdict per criterion: met, not
   met or needs CI. If D3 is A, it also tries to get an address that is not enumerated through the
   published allowlist.
8. **Fix rounds:** at most two. Product choices come back to you; a fix that edits the golden file
   goes back to you and runs both baselines again. A third round only with your go.
9. **Report:** the PR body is the stage report: n of m criteria met, what needs CI, what was cut,
   and the Mac time used.

Sequential subagents unless your go asks for a Workflow. Hosted spend: none.

## Decisions needed

**D1. The S3 abstention finding.**

- **A (recommended): measure answer-v1 as it is.** S4's baseline records the abstention result as
  the model gives it. A prompt change is a follow-up pull request after S4: answer-v2, developed on
  the dev split only, measured with S4's paired comparison against S4's baseline and baselined
  again in that pull request. Why: the first real run sets the baseline (main plan); a label-only
  fix could make the label say `abstain` while the text still gives a value, which the oracle
  catches only for numbers and S5's judge catches in full; and S4 stays one reviewable stage.
- **B: answer-v2 inside S4**, on the dev split only and before the baseline: two prompt versions
  measured on dev, the baseline made with answer-v2.
- Either way, the test split first runs after the prompt is frozen, and no test result is read to
  change a prompt.

**D2. Additions to the answer key you signed off.**

- **A (recommended): additions only, signed off with the golden set.** Locations for the group
  members (the FAQ entries beyond F-53's three, and Device Policy 6.2 for F-17); silence proofs for
  the new unanswerable topics (F-40's `must_not_appear` extended for the tenant B topics, and at
  most two new omission features); a feature for the FAQ Q6 café case. No existing value, label or
  reference answer changes, and the `canaries` and `answer_must_not_contain` lists stay as they
  are, because the published runs are validated against them.
- **B: no change.** Groups only where F-53 already lists the FAQ entry (Q1, Q2, Q8), so R-Q14 and
  R-Q25 keep primary-only labels; the unanswerable cases come from F-32 and F-40's three topics,
  so several repeat a topic in other words; the café case becomes F-55.

**D3. What a published answer may hold.** Two S3 rules would refuse a correct answer:

- Team contacts. `privacy/allowlist-published.txt` says "Contacts, secrets and personal details
  never go here" (your S3 decision, "Allow those IDs only"), so a run whose answer gives the SOC's
  or the Service Desk's address cannot be published. F-46 (the contact, must-not-block) needs that
  address; answers on reporting a compromise (F-30) often add it; and an abstention may point to
  the asker's support contact (R-03).
- Plain attack phrases. Publish refuses any run that holds an `answer_must_not_contain` string,
  and F-47's and F-48's include plain phrases that a correct answer on tenant B's expiry rule (why
  F-35 is left out, Choices row 5), or on NIST's expiry guidance (F-08), can contain.
- **A (recommended):** enumerate the planted team contact addresses of `corpus/SPEC.md` section 6
  in the published allowlist (exact strings, never a pattern, never F-45's personal details), as
  S3 did for the exception ids; and make publish refuse the plain attack phrases only in attack
  runs (S7), while the secret, the personal details, the canary token and the planted links always
  block. Team contacts are not PII (R-19; TEST-PLAN section 7). This rewrites a guard S3's judge
  verified: `tests/unit/test_published_allowlist_scope.py` today requires the list to be exactly
  the exception ids and treats a planted contact under `runs/published/` as a hit; it would then
  enumerate the team contacts as well and keep refusing any address not on the list.
- **B: keep both rules.** S4 drops F-46 and words no case to invite a contact or one of those
  phrases; a run refused for them is recorded and the stage pauses for you.

**D4. v0.1.** The main plan's maturity table puts the release gate in P2 ("Gates": P1 "pr-fast
blocks"; P2 "eval-on-change, nightly, release"), and S3h's move leaves P1 without a host. What the
release gate demands, against what exists at the end of S4:

| Release gate item (main plan) | At the end of S4 |
|---|---|
| security suite, binary | S3's guard tests (tenant, input limits, citation validator) run in pr-fast; the attack suite is S7 |
| test slice | built, not run; under A it runs once at the release |
| promptfoo red team on the real model | S7 |
| trivy, SBOM | P3 (S11) |
| gitleaks history scan, history privacy scan | available: `make secrets` (`gitleaks git`), `make privacy-history` |
| upgrade replay | S8 |
| deploy approval | S10; nothing is deployed |
| a chosen host and a fake-model deploy | moved to P3 with S3h (pull request #10); v0.1 promises a container ready to deploy |

- **A (recommended): a lab release after S4.** A `chore(release): v0.1.0` pull request: the
  version to 0.1.0 (now 0.0.1), a CHANGELOG section, release notes that list every row above as
  run or not built yet, the two history scans run, and the test slice run once at that commit
  (gate release, provenance local, published). You tag `v0.1.0` on the merge commit by hand. If D1
  is A and you want the prompt fix in v0.1, cut the release after the fix, so the one test-slice run
  measures the prompt v0.1 ships.
- **B: no tag until P3**, when a host exists; P1 ends without a version.
- **C: tag the S4 merge commit as it is**, with no test-slice run and the CHANGELOG only.

**D5. This plan:** approve and start, or changes first.

## Approval

The go for this draft (2026-10-18), verbatim: "Draft S4 plan (Recommended)".

Approval of this plan: pending. Your answers to D1 to D5 will be quoted here, verbatim.
