---
stage: S8
name: gates-causes-audit
nodes: [S8]
date: 2026-10-31
branch: feat/s8-gates-causes-audit
status: draft
---

# S8: Gates, failure causes and the suite audit

Part of the main plan (phase P2, release v0.2; the last stage of P2, after which v0.2.0 is cut
and P3 starts with S3h: the phase map's `S8 --> S3h`). Branch: `feat/s8-gates-causes-audit`, cut
from `main` at `ef46a61`, the merge of the plan update #34. Build project stage 8 and how-to 17
step 11; the gate map follows how-to 08, the audit how-to 09 (part B, the suite audit), the
upgrade record how-to 10.

The main plan's row for S8: "suite audit (how-to 09 B) in `docs/audits/`; GATES.md with how-to 08
columns; THRESHOLDS.md gives a reason for every gated and every reported metric; every failure
tagged with a cause (ingestion, retrieval, generation, abstention); embedder-swap branch shows what
moved; upgrade record (how-to 10); flake policy". Its "Gate map (how-to 08 columns)" section sets
the seven columns and the rows; its "Security and audits" part 3 sets what the suite audit reads
("coverage cells against cases, skips, phrase-locked criteria, calibration record, test-split
contamination, intervals and pairing, thresholds with reasons"); its "Progress and next steps
(updated 2026-10-26)" section gives S8 five follow-ups (R-22, S4b-J4, S7a-J1, ATK-TEN-1 trial 3,
S7a-J11). This plan quotes the handbook only through the main plan; the developer reads how-to
08, 09 and 10 at the start of the build and lists in the ledger what each asks, as S7 did for
how-to 07.

**The go for this plan (2026-10-31, about 14:35 UTC), verbatim.** The orchestrator wrote: "The S8
plan is unwritten and can be drafted on your go." You answered: "yes lets do that". That is the go
for drafting this plan only. Its approval is its last decision, D5, quoted under Approval when you
give it; until then the front matter says `status: draft`.

## Inputs from other stages

S8 builds after S6 and S7b merge. What each criterion needs from them, and what the developer can
start on now, offline, against `main` at `ef46a61`:

| Criterion | From S6 (judge calibration, in progress) | From S7b (AG14 to AG20, not started) | Buildable now at `ef46a61` |
|---|---|---|---|
| GA1 GATES.md | the judged section's status per criterion, for the eval-on-change row | the red-team and comparison rows of `manual` (AG15, AG18) | every other row; the ci/local marks; the runbooks |
| GA2 THRESHOLDS reasons | S6's judged section as it lands (JC10) | S7b's comparison rows (AG18) | a reason for every row that exists today; the metric-coverage test |
| GA3 TEST-PLAN gate cells | R5's gate cell wording (S6 changes it) | — | the Gate column for every other row; section 10's report line |
| GA4, GA5 failure causes | nothing: causes are read from the record's own fields | nothing | all of it, on the published v2 runs |
| GA6 the judged gate | the calibration record (`datasets/calibration/judge-v2-c1/record.json`, S6's suggested path) with a status per criterion: trusted, reported only or not trusted; the v2 judged record S6 made on 2026-10-24 | the Provenance experiment's record (AG19), which the audit lists | the paired comparison of judged records and the gate's rules, tested on hand-built records; the trust check waits for the record's format |
| GA7 the drift alert | S6's trigger "S8's drift alert on a judged pass rate" (S6 plan, "The record") | — | the deterministic alert on consecutive nightly records; the judged one on consecutive judged records |
| GA8, GA9 the suite audit | the calibration record, for the audit's calibration section; which criteria stay uncalibrated (S6's D1: five of seven) | the confirmed findings as cases (AG16) and the comparison (AG18), for the coverage section | six of the seven sections; the contamination script; the not-covered list |
| GA10 embedder swap | nothing | nothing | all of it (one model download with your go) |
| GA11 upgrade record | nothing | nothing | after the dependency pull request of 2026-10-31 merges |
| GA12 flake policy | nothing | nothing | all of it |
| GA13 to GA17 follow-ups | nothing | nothing | all of it |
| GA18 docs, status | S6 `done` before S8's status change | S7 `done` before S8's | the rest |

**S6, judge calibration** (its plan and ledger at `eff197d` on `feat/s6-judge-calibration`, read
without checking the branch out; its
decisions of 2026-10-23, verbatim: "All five as recommended (Recommended)"). S6 calibrates
`grounded` and `abstains` on 15 labels each (D1); kappa 0.80 or more is trusted, "S8 may gate on
it", 0.60 to under 0.80 reported only, under 0.60 not trusted (D2); the other five criteria
(`correct`, `cites_support`, `relevant`, `refuses_and_helps`, `context_sufficient`) "stay
reported, uncalibrated and never gated until labels of their own calibrate them; S8's suite audit
lists them as a gap". S6's ledger (read the same way) says the judged baseline on golden set v2
ran on 2026-10-24, 1,400 judge calls, canaries 19 of 19, 2 h 20 min 53 s from launch to the
postcheck; the main plan's progress section names the run and the canaries. S6 waits for your 30
blind labels, so **its verdicts do not exist yet**: this plan names no criterion as trusted, and
GA6 is written so the code reads the verdict from the record and refuses to gate on anything else.
S6 also leaves S8 "the calibration record's id in judged manifests", the weighted TPR and TNR "for
S8's margins", and the recalibration triggers.

**S7b.** The red team's committed summary (AG15), the confirmed findings as cases (AG16), the
comparison record (AG18) and the Provenance experiment (AG19) give GATES.md its `manual` rows and
the audit its security coverage. Under S7's D1 ("Split: S7a now, S7b after S6"), S7b merges after
S6 and before S8.

**Earlier stages.** S4b: the v2 baselines (`20261024T090200Z-retrieval-dense-dev-ade9397` and its
hybrid and dense-600 companions; the consistency baseline
`20261024T090351Z-generation-local-ollama-dev-ade9397` and its four repeats), the Versions table in
`datasets/DATASHEET.md`, and S4b-J4. S7a: the guard suites record
(`runs/guard-suites/20261025T181249Z-5c4d409.json`), the replay (`runs/replays/`), the published
attack run `20261025T205853Z-attack-local-defences-on-dev-762b163`, S7a-J1, S7a-J11 and the
ATK-TEN-1 trial 3 finding. S9: the perf gate's rule ("ten report-only runs ... none dropped and
none run again for a better number") and its line "the flake policy is S8's". The dependency pull
request of 2026-10-31 (branch `build/deps-2026-10-28`, commit `e5969f4`; the orchestrator names
it #35), which S8 rebases onto once merged.

## Where S8 starts

Read from the files at `ef46a61`.

**The gates that exist**, each with its rule in code and its reason in THRESHOLDS.md:

| Gate | Where | Runs | Rule |
|---|---|---|---|
| Retrieval no-regression | `raglab gate --config config/retrieval-dense.toml`, `make gate`, pr-fast | ci | recall@5 on dev at least the baseline's minus one question (1/22); stale on another dataset or config sha256 (`src/raglab/evals/gate.py`) |
| Consistency (Q-05) | `raglab gate --config config/local-ollama.toml`, `make gate-local` | local | behaviour pass^3 on dev at least the baseline's minus `margin: 1 case(s)` from THRESHOLDS.md's consistency row; stale on dataset, config, prompt fingerprint, model digest, trials, or guard set (the replay) |
| Guard suites and the attack suite | `tests/security/`, `make test`, pr-fast | ci | binary per build: one miss or one false block fails, naming the case and the layer |
| Dataset check | `make check-dataset`, pr-fast's first step | ci | a hard stop before any run |
| The canary set | every judge session, before any judged call | local | every item on its side, or the judge grades nothing |
| k6 smoke | pr-fast's `perf` job | ci | the /ask median under 40 ms; checks rate 1; no failed request |
| Held-out split | `raglab eval` and `raglab publish` | both | the test split runs only under `nightly` or `release` |

Nothing judged is gated (THRESHOLDS.md, "Judged (S5)"). The main plan's gate map names seven
gates with runbooks `runbooks/pr-fast.md`, `runbooks/eval.md`, `runbooks/nightly.md` and
`runbooks/release.md`; only `release.md` exists. `docs/releases/v0.1.0.md`'s release-gate table
says "upgrade replay: not built yet (S8)", and `runbooks/release.md` lists "an upgrade replay (S8)"
under what a production release adds. `docs/audits/` does not exist. No GATES.md exists.

**The run record** (`schemas/run-record.v1.json`; `src/raglab/evals/record.py`,
`generation_record.py`, `behaviour.py`). A generation case line holds `checks` (status_ok,
model_citations_retrieved, decision_label, abstained, no_value, conflict, cites_label, no_canary,
must_not_contain, passed), `labels` with `found` per labelled section, `status`, `label`,
`cited_ids`, `retrieved`, `guard_events`; there is no `cause` field. The manifest's behaviour block
already splits the decision-label failures by retrieval: on the v2 baseline, `label_failures`
is 28 case-trials with every labelled section retrieved, 23 with a labelled section missed, 45 on
abstain cases (no labels); `conflict_side_missed` 9; `status_counts.blocked` 5 (its
`manifest.json`). Those are the seed of the cause rule, not its result: the counts by cause are the
developer's measurement. TEST-PLAN section 10's report line reads
`<from S8: per case cause (ingestion/retrieval/generation/abstention), intervals, paired diff>`.
`raglab compare` pairs retrieval runs and generation runs (`src/raglab/evals/compare.py`); it does
not read judged records.

**The embedder** (`src/raglab/adapters/fastembed_embed.py`) pins one model: `MODEL`
`BAAI/bge-small-en-v1.5`, the ONNX export `Qdrant/bge-small-en-v1.5-onnx-Q` at `REVISION`
`aa8f8b06…`, five files with their sha256, fetched once by `make model`, which pr-fast runs on every pull request, cached by revision. The retrieval manifest
records the embedder's model, revision, `onnx_sha256`, dimension, and the fastembed (0.9.0) and
onnxruntime (1.30.0) versions; the gate's staleness rule reads the config sha256, which names the
model and revision, and not the library versions.

**The follow-ups, where each sits:**

- **R-22** (TEST-PLAN rows 240 and 253): "a gap for S8's suite audit"; S4b's D3, verbatim: "No
  corpus change; R-22 stays a gap (Recommended)".
- **S4b-J4** (the S4b ledger, "Not in this PR"): `raglab gate` reads the first consistency row of
  THRESHOLDS.md (`gate.consistency_margin`) and does not refuse a second; only
  `test_the_one_consistency_row_names_the_published_baseline` does.
- **S7a-J1** (the S7 ledger): `raglab publish` does not refuse a record whose `dataset.sha256` is
  no listed version; `test_every_published_run_names_a_dataset_version_the_datasheet_lists` catches
  it afterwards. The judge's smallest fix: refuse it in `publish.py` beside the attack-run rules.
- **S7a-J11** (the main plan): a threat-model row whose Layer cell is written "n/a" passes its rows
  test. `tests/security/test_threat_model.py` reads a cell "with no letter in it" as no layer, so
  "n/a" has letters and counts as a layer.
- **ATK-TEN-1 trial 3** (the S7 ledger, "A finding for S7b and S8"): with defences on, an answer
  "states the asking tenant's own rule, from the chunk it cites, as the other tenant's, and gives
  a validity period that no corpus file holds"; "not a leak, but no attack check measures a
  fabrication about another tenant". The record is the unpublished `8f7c94d` one
  (`runs/tmp/s7-evidence/records-8f7c94d/`), which may no longer exist.

**Measured times, the basis of every estimate below** (docs/LOCAL-MODEL.md unless named): a
`make eval-local` session on v2's dev split (22 retrieval questions and 79 behaviour cases x3, 303
case-trials) took 8 min 59 s to 9 min 41 s in six sessions on 2026-10-24; `make attack-local`'s
second session 2 min 50 s (the first, 3 min 41 s awake); S6's judge session on v2, 2 h 20 min 53 s
for 1,400 calls (S6's ledger); a local `make -k check` 283.64 s at `4d33125`, "1884 passed" (the
S7 ledger); pr-fast's `check` job 16 min 59 s on S7a's last run, of 20 (the main plan); a retrieval
run 10 to 14 s (the S7 plan, from S4). S4b's planner took 32 min for its plan (the S7 plan).

## Goal

- A gate map in the repo (GATES.md) with how-to 08's seven columns, each gate marked `ci`,
  `local` or `documented only`, naming the real targets, tests and runbooks, so nobody mistakes a
  local run for an automated one (the main plan).
- A reason for every gated and every reported metric, held by a test against the metrics the
  published records actually carry.
- Every failed case-trial of a generation or retrieval run tagged with one cause (ingestion,
  retrieval, generation, abstention) by a rule a test can recompute, and counts by cause in the
  record and the report; applied read-only to the published runs.
- The judged gate wired to S6's verdicts: a criterion gates only when its calibration record says
  trusted, and the gate refuses anything else.
- A suite audit in `docs/audits/` that runs its checks instead of reading them, with a not-covered
  list, R-22 decided, and the uncalibrated criteria named as a gap.
- An embedder swap measured and recorded, showing what moved and what the staleness rule caught.
- An upgrade record for a real upgrade, which is the lab form of the release gate's "upgrade
  replay".
- A flake policy with a retry rule, a quarantine and a register, consistent with "honest numbers".
- The five follow-ups closed or cut, each with its reason.

## Out of scope

| Item | Where it goes |
|---|---|
| CI versions of eval-on-change, nightly, weekly (keyed workflows, Environments with required reviewers) | when ADR-002's keys exist (S10); GATES.md marks them `local` |
| A judged cause per failure (a judge call on each failed trial) | not offered: the judge's `context_sufficient` is uncalibrated (S6's D1), and it would cost a judge session per run |
| Re-baselining after the embedder swap, or adopting the second embedder | a pull request of its own, with five sessions by S4's rule, if the measured result argues for it |
| Planting R-22 in the corpus | D4 B: a corpus pull request after S8; the cost is in D4 |
| The system audit (how-to 09 A), the capstone's not-covered list, trivy, SBOM | S11 |
| The v0.2.0 release (the test slice once, the notes) | the release plan after S8 merges (`runbooks/release.md`) |
| A hosted judge or generator, any sign-up | ADR-002: local only for now |
| The golden set, the judge, CRITERIA.md, the canary set, the prompt, the corpus, the register, every existing config | frozen; S8 adds files and code beside them |
| fastembed 0.9.1 (the orchestrator's note: it lifts the Pillow cap to below 14) | your open decision; taken inside S8 only as GA11's live example, under its replay |

## The work

### A. GATES.md, THRESHOLDS.md and TEST-PLAN's gate cells (GA1 to GA3)

**GATES.md** has one row per gate of the main plan's map, in its seven columns: Gate, Trigger,
Keys, Blocks, Threshold and reason, Owner and runbook, What runs; plus a Mode cell (`ci`, `local`
or `documented only`), which the main plan asks for. "What runs" names the make targets, the
pytest markers and the commands; "Threshold and reason" points at THRESHOLDS.md's row; "Owner and
runbook" names a runbook that exists. The developer writes the three missing lab runbooks beside
`runbooks/release.md`, short, in its shape (when, steps, what production adds): `pr-fast.md`,
`eval.md` (the local eval-on-change: `make gate-local`, then the judged comparison of GA6 when a
judged run exists), `nightly.md` (`make nightly-local`, the drift alert of GA7). A test parses
GATES.md: the seven columns and the mode on every row, every make target named exists in the
Makefile's rules, every runbook named exists, and pr-fast's "What runs" names every `make` step of
`.github/workflows/pr-fast.yml` (read from the workflow, so a new CI step without a GATES.md
mention fails).

**THRESHOLDS.md** gains a reason wherever a row lacks one and a row wherever a metric lacks one.
The test: every metric key under `results.metrics` of every manifest in `runs/published/`, every
rate and latency of `runs/guard-suites/*.json`, and the perf smoke's names appear as a row of a
THRESHOLDS.md table whose Gate and Reason cells are non-empty; and every row's Gate cell is one of
`pr-fast`, `eval-on-change`, `nightly`, `manual`, `release`, a "hard stop" or "enforced in code"
phrase, or `reported`. Rows S6 and S7b add are held by the same test after their merges. Lab
practice stays labelled where it is.

**TEST-PLAN.md**: the Gate column of section 8, "filled in by ... the gate map", gets each row's
gate from GATES.md (`pr-fast` for the security rows already; `eval-on-change (local)` for the
judged rows, `reported` where nothing gates), and section 10's report line is filled with S8's
words. `tests/unit/test_test_plan.py` is extended for the Gate column as it was for S4b's and
S7's cells.

### B. Failure causes (GA4, GA5)

**The vocabulary** is the main plan's: `ingestion`, `retrieval`, `generation`, `abstention`. One
cause per failed case-trial, chosen by the first rule that applies, in this order, from fields the
case line already holds (so `record.validate` recomputes it and a published record can be read
without change):

| Order | Cause | Rule (generation suite, behaviour and retrieval cases) |
|---|---|---|
| 1 | ingestion | a labelled section's chunk ids are not all in the inventory the run searched (quarantined by the instruction scan, or absent from the snapshot), or the case's feature is one `scripts/chunk_experiment.py`'s rule reports split at the run's chunk settings (the value's chunk cannot hold the cited values together) |
| 2 | retrieval | a labelled section was not retrieved (`labels[].found` false; `label_failures.labels_missed` today), or a flag-conflict case's conflict side was not retrieved (`conflict_side_missed`), or a retrieval question's recall@5 is under 1 |
| 3 | abstention | an abstain case not abstained (`abstained` false), or an answerable case with every label retrieved whose given label is `abstain` (over-abstention), or an abstain case that abstained and still stated a value (`no_value` false) |
| 4 | generation | everything else that failed with its labels retrieved: a wrong decision label, a missing citation of a labelled section (`cites_label`), a wrong or missing conflict field, a canary, a must-not-contain string, an answer withheld by an output guard (`status` blocked) |

Rule 1 reads the corpus, so it is not a pure function of the record: the tag is computed when the
run is made and stored, and `validate` recomputes it only while the manifest's corpus sha256
matches the current inventory; otherwise the stored value stands and is said to be historical.
A trial whose status is `unavailable` or `invalid_output` has no cause: it is the fallback contract,
and a run with one is partial and never published. Attack records keep their per-check failures,
where the layer is the cause. For a judged record, a failed verdict takes `retrieval` when the
case's `context_sufficient` verdict is a fail and `generation` otherwise, and THRESHOLDS.md says
that split rests on an uncalibrated criterion.

**What the rule cannot separate**, said in the docs: a model that abstains because the passage it
was given is ambiguous (generation) from one that abstains out of habit (abstention) both tag
`abstention`; a wrong value with the right chunk retrieved tags `generation` whether the chunk's
text or the model misled it; an ingestion split and a retrieval miss on the same section tag
`ingestion`, because the order decides.

**Where it is written.** New records: `cause` on every case line (null when the trial passed) and
`results.causes` in the manifest, counts per case-trial and per case (a case takes the cause of the
first of its failed trials in the order above; the per-trial counts are the honest ones and the
report shows both). The schema adds both as optional fields, so every committed record stays
valid and `runs/published` files never change. Published records: `raglab causes <run_id>`
recomputes the tags read-only and writes `runs/causes/<run_id>.json` (the `runs/replays/`
pattern: beside, never inside, a published run), and the report of a new run gets a causes section.
The v2 consistency baseline's and its repeats' counts by cause go in the ledger from that command's
output, never from this plan.

### C. The judged gate and the drift alert (GA6, GA7)

**eval-on-change, the judged half**, by the main plan's rule, "the paired-diff interval must not
cross zero downward". `raglab compare` learns judged records: two judged records of the same
dataset, split, trials and judge (the one-judge test's fields: prompt version and fingerprint,
CRITERIA.md's sha256, the canary set's, the model and digest) over the same cases; per criterion,
B minus A of the case's pass share, a paired percentile bootstrap over cases (A's seed, level and
resample count, as the retrieval and generation comparisons), and the flipped cases.
`raglab gate --judged <B> --against <A>` reads the calibration record each manifest names (or, for
S6's v2 baseline, which predates the record, the judge identity above), and for each criterion the
record marks **trusted** fails when the interval lies entirely below zero; a criterion marked
reported only or not trusted is printed and never gates, and a criterion no record names is refused.
If S6 trusts no criterion, the gate exists, refuses to gate, and GATES.md's eval-on-change row says
so with the reason. New judged manifests carry `judge.calibration_record` (the record's path and
sha256); S6's baseline is matched by identity, never edited. The gate runs by hand until keys
exist (`runbooks/eval.md`), and its first real input is the next judged run (answer-v3's, when you
schedule it; none is owed in S8). "Cross zero downward" is read as the whole interval below
zero (a drop the data supports); the stricter reading, a lower bound below zero, would fail on
noise alone at 79 cases, where S4b's repeats moved one to three cases either way. No margin is
invented: the interval carries the uncertainty, and
the weighted TPR and TNR S6 reports are quoted beside the verdict as the judge's own error, not
folded into a number.

**The drift alert** (the nightly row's "alerts"; S6's trigger): `raglab eval --gate nightly`
compares its behaviour pass^3 with the previous published nightly record of the same config (paired
by case, the flipped cases listed) and writes an `alert` line in the record and the report when the
interval lies entirely below zero; it never blocks. The judged alert is the same comparison between
consecutive judged records on trusted criteria, and it names the recalibration trigger. With no
published nightly on v2 yet, the first nightly is the reference, and the ledger says so.

### D. The suite audit (GA8, GA9)

One report, `docs/audits/<date>-suite-audit-v0.2.md`, at the end of v0.2, with one section per
item of the main plan's list, each a check **run**, with its command and output, not read:

1. **Coverage cells against cases**: section 8's traceability table against `golden.v2.jsonl`
   and the security pack (the existing tests, re-run); the requirements with no planted feature;
   the five uncalibrated judged criteria as a gap (S6's D1); the Test cells still `tbd` at
   `ef46a61` (R-07, R-08, R-09, R-12, R-23), each named with what would fill it; S7b's findings
   as cases.
2. **Skips**: `make audit`'s skips with their review date (2026-11-21), the `live` and
   `guardrails` markers kept out of `make check`, ZAP's three ignored rules, the test split's
   held-out runs; each with its reason and owner.
3. **Phrase-locked criteria**: the guard suites' assertions are behaviour, never refusal wording
   (how-to 07; re-checked on every `expected`); the record's checks match plain substrings
   (S7a-J6: fullwidth and homoglyph forms escape them); CRITERIA.md's rules against the judge
   prompt's words (`test_the_pass_and_fail_rules_are_judge_v2s_words`).
4. **Calibration record**: S6's record linked, its verdict per criterion, the triggers, and whether
   every judged manifest names it (GA6).
5. **Test-split contamination**: a script lists every test-split id of `golden.v2.jsonl` and finds
   each only under `datasets/`, in published records made under `nightly` or `release`, and in the
   ledgers' allowed lines; no test id in `src/`, `config/`, `datasets/security/`, a prompt or a
   threshold; and no test-split run on v2 has been made yet (v0.2.0's release makes the first).
6. **Intervals and pairing**: every published metric carries its interval; every comparison is
   paired (`compare` refuses unpaired runs); every number in the docs links its record (S6's JC10
   test extended to the README's status lines).
7. **Thresholds with reasons**: GA2's test, run.

Plus the **not-covered list** (R-22 under D4 A; the five uncalibrated criteria; the gates marked
`local`; S7's not-covered items carried over), and what production would do where the lab stops.
A script, `scripts/audit_suite.py` (a suggestion), recounts the report's counts from the files, and
a test runs it so the report cannot drift from the repository. The contamination check is a
pytest under `tests/unit/`, run by `make test`, so no workflow changes.

### E. The embedder swap (GA10)

A branch experiment, measured, with no Ollama session. The adapter carries a second pinned model
(a second small ONNX export fastembed 0.9.0 lists; the developer chooses, pins its revision and
every file's sha256 as the first is pinned, and a target of its own, `make model-swap` (a suggestion), fetches it once, over https, with
your go for the download; never `make model`, whose cache key and pr-fast step stay as they are). A config `retrieval-dense-<model>.toml` (and `-hybrid-`) names it;
the retrieval suite runs on the dev split, dense and hybrid, offline; `raglab compare` gives, against
`20261024T090200Z-retrieval-dense-dev-ade9397` and its hybrid companion, B minus A of hit@5, MRR@5
and recall@5 with their paired intervals and the flipped questions. "What moved" is those files,
quoted in the ledger from the records. Then the staleness rule is shown doing its job: `raglab gate
--config` with the swapped config refuses, because the config sha256 differs from the baseline's;
the consistency baseline is stale the same way and is **not** re-made (five sessions, S4's rule, a
pull request of its own). The corpus build's pixel check (`tests/unit/test_corpus_build.py`) and
the inventory snapshot do not move: chunks are made before any vector. Publishing is D2.

### F. The upgrade record (GA11)

`docs/UPGRADES.md` (a suggestion): one record per upgrade, in a fixed shape the developer reads
from how-to 10 and writes in the ledger: what moved (package, from, to, the cooldown read), what was
replayed (the gates re-run at the upgrade: `make check`, `make gate`, `make replay`,
`make guard-suites`, and whether any baseline went stale by rule), what was tried and not taken,
what changed in the docs, and the decision with its date. This is the lab form of the release gate's
"upgrade replay" (`docs/releases/v0.1.0.md`: "not built yet (S8)"; `runbooks/release.md`), and
both files point at it. The first record is the dependency upgrade of 2026-10-31, written from its
merged commit: fastapi 0.146.0, starlette 1.9.0, ruff 0.17.1, the googleapis-common-protos
constraint off at 1.76.0, the DeepEval tool re-locked, pypdf 6.21.2 tried and not taken (the
plain-text check reads a wrapped table cell as "theaccount"), seven pypdf advisories skipped under
the 2026-11-21 review date. Its replay is run in S8 (the targets above, with the published
baselines unchanged by rule: the retrieval gate does not read library versions, which is what the
record exists to say). If you take fastembed 0.9.1 inside S8, it is the second record, with the
retrieval baseline compared before and after (the manifest records `fastembed` and `onnxruntime`;
the gate does not); otherwise the record notes it as open.

### G. The flake policy (GA12)

A section of GATES.md ("Flakes"), with a register table. **A flake** is a test or gate that fails
and passes at the same commit with the same inputs and no change. **Not a flake**: an environment
failure (a slow runner, a package mirror, the Mac asleep, a model not loaded), which is recorded as
such; a real failure. The policy follows S9's rule and the honest-numbers rule: no run is dropped
and none is run again for a better number. The retry rule is D3. **Quarantine**: a `flaky` marker,
registered (`--strict-markers`), kept out of `make check` and pr-fast, run by `make test-flaky`;
every quarantined test has a register row (test id, first seen, the run or session, the suspected
cause, the owner, the removal date, at most 30 days); a test parses the register and fails on a
quarantined test without a row or past its date. The register starts empty; the history's two
observations go in a "seen so far" list as environment failures, not flakes: pr-fast's test step
at 346 s and 451 s on two runs (THRESHOLDS.md, Performance) and the S7a judge's "transient 'no
verdict' classifier failures ... which succeeded on retry" (the S7 ledger). Lab practice: production
would track flake rates per test from CI's history and quarantine automatically; here the register
is a table and the marker a rule.

### H. The follow-ups (GA13 to GA17)

| Follow-up | Mechanism | Criterion |
|---|---|---|
| S4b-J4 | `gate.consistency_margin` refuses a THRESHOLDS.md with two rows starting with the consistency row's prefix (`CONSISTENCY_ROW` in gate.py), naming both; the CLI prints the refusal | GA13 |
| S7a-J1 | `publish` refuses a record whose `dataset.sha256` is no version of the Versions table of the datasheet beside its golden file (or of the security pack's table for an attack run), beside its attack-run rules; the S4-J10 test stays | GA14 |
| S7a-J11 | the rows test reads a Layer cell as layers only when each name it holds is a layer GUARDRAILS.md's tables list (by its name), and otherwise as no layer, which needs a reason; "n/a" is then no layer | GA15 |
| ATK-TEN-1 trial 3 | a reported check on attack records, `other_tenant_claim` (a suggestion): an ok answer that names the other tenant (casefolded) and states a number or a date that no retrieved chunk of that tenant holds (no such chunk was retrieved in that trial); counted per case and trial, cause `generation`, reported and never gated in S8 (the reason: it reads the answer's numbers against chunks, as the abstention oracle does, and cannot read a claim stated in words); run read-only over the published `762b163` record and, if they still exist, the `8f7c94d` records in `runs/tmp/s7-evidence/` | GA16 |
| R-22 | D4: recorded as not covered (A), with the reason and the cost of planting it; or a corpus pull request after S8 (B) | GA17 |

## What gets built

```
docs/GATES.md                           the gate map (new): seven columns, a mode per row, Flakes
docs/audits/<date>-suite-audit-v0.2.md  the suite audit (new)
docs/UPGRADES.md                        the upgrade records (new)
runbooks/pr-fast.md, eval.md, nightly.md  the lab runbooks (new), beside release.md
src/raglab/evals/causes.py              the cause rule; `raglab causes`
src/raglab/evals/compare.py             judged records; the drift comparison
src/raglab/evals/gate.py                two consistency rows refused; the judged gate
src/raglab/evals/publish.py             an unlisted dataset version refused
src/raglab/evals/attack_record.py       the other_tenant_claim check, reported
src/raglab/evals/generation.py, judged.py, record.py, schema.py, schemas/run-record.v1.json
                                        cause and causes (optional fields); the alert line;
                                        judge.calibration_record on new judged manifests
src/raglab/adapters/fastembed_embed.py  a second pinned model; make model-swap fetches it (make model unchanged)
config/retrieval-dense-<model>.toml, retrieval-hybrid-<model>.toml   new files only
scripts/audit_suite.py                  the audit's recounts; the contamination check is a unit test
runs/causes/, runs/compare/             derived files beside the published runs
tests/unit/test_gates_doc.py, test_thresholds_cover_the_metrics.py, test_flake_register.py,
tests/evals/test_causes.py, tests/judge/test_judged_compare.py, tests/security/test_threat_model.py,
tests/retrieval/test_publish.py, tests/unit/test_test_plan.py, tests/unit/test_audit_suite.py
Makefile                                causes, test-flaky, audit-suite, the swap's retrieval runs
docs/                                   THRESHOLDS, TEST-PLAN, THREAT-MODEL (not covered), LOCAL-MODEL,
                                        OBSERVABILITY (the alert line), README, ARCHITECTURE,
                                        releases/v0.1.0.md (a pointer), the main plan's note; CHANGELOG
docs/plans/2026-10-31-s8-gates-causes-audit-ledger.md   the ledger
```

The file and target names are suggestions; the developer may choose others and says so in the
ledger.

## Shared files and merge order

S8 merges after S6, S7b and the dependency pull request of 2026-10-31. Conflicts are expected in:

| File | S8's change | Also touched by | Order |
|---|---|---|---|
| CHANGELOG.md | one line | every pull request; the deps PR | rebase, append |
| docs/THRESHOLDS.md | reasons on every row; the judged gate's row; the drift row; the causes note; GA16's row | S6 (the judged section, the calibration bar), S7b (the comparison), S4b's consistency row (S4b-J4 reads it) | after S6 and S7b; own rows |
| docs/TEST-PLAN.md | the Gate column; section 10's report line | S6 (R5's gate cell, section 10's judges line), S7b (section 10's security line) | after both |
| README.md, docs/ARCHITECTURE.md | S8 `done` | S6 and S7 (the same `class` lines) | last |
| Makefile (both `.PHONY` lines) | new targets | S6 (label, calibrate), S7b (redteam-*, guardrails-*), the deps PR (audit skips) | rebase |
| pyproject.toml, uv.lock, .github/dependabot.yml, privacy/allowlist.txt | none expected (fastembed 0.9.1 only under GA11's live example) | the deps PR; S7b (Dependabot entries) | after the deps PR |
| src/raglab/__main__.py | `causes`, `gate --judged`, `compare` on judged runs | S6 (label, calibrate) | after S6 |
| src/raglab/evals/compare.py, judged_record.py, record.py, schema.py | judged comparison; optional fields | S6 (the calibration pins the judged record's sha256: the record's format is unchanged by S8, fields are added to new records only) | after S6 |
| docs/LOCAL-MODEL.md | a line only under D2 B or D1 C | S6 (the cap, the session's time), S7b (its rows) | rebase |
| docs/THREAT-MODEL.md | the not-covered list (GA16's limit) | S7b (its rows) | after S7b |
| docs/GUARDRAILS.md | none expected | S7b (the validators) | — |
| .github/workflows/pr-fast.yml | none: every new check runs inside `make test` or beside `make check`, and GA1's test reads the workflow as it is | S7b (none expected) | — |
| runs/published/index.json | the swap's runs under D2 A | S6 (the v2 judged record), S7b | after both |
| tests/security/test_threat_model.py | GA15 | S7b (its rows) | after S7b |
| docs/plans/2026-10-05-raglab-plan.md | dated notes for D1 to D4; the progress section | S6, S7b | rebase |

## Choices I made (you can change them)

| # | Item | Choice | Why |
|---|---|---|---|
| 1 | The cause rule | rule-based, from the record's own fields, one cause per trial in a fixed order | recomputable by `validate`; no model; a judged cause rests on an uncalibrated criterion |
| 2 | Published records | never edited; causes derived beside them (`runs/causes/`), optional fields on new records | `runs/published` files never change; every committed record stays valid |
| 3 | The judged gate's rule | the paired interval, the main plan's; no margin | one judged run on v2 exists; a margin from repeats costs a judge session each (2 h 20 min 53 s measured) |
| 4 | Trust | read from S6's record by the code; nothing gates that it does not mark trusted | S6's D2, "S8 may gate on it"; the verdicts do not exist yet |
| 5 | The audit | one report with seven sections and a not-covered list, recounted by a script | the main plan's list is one audit "at the end of v0.2"; per-suite reports would repeat the sections |
| 6 | The runbooks | written, short, in `release.md`'s shape | the gate map names them; a row naming a missing runbook fails GA1's test |
| 7 | The embedder swap | retrieval only, offline, a second pinned model; nothing re-baselined | "shows what moved" needs no session; re-baselining is a pull request of its own |
| 8 | The upgrade record's first entry | the 2026-10-31 dependency pull request, written from its merged commit | a real upgrade with a tried-and-not-taken bump; fastembed 0.9.1 is your open decision |
| 9 | The flake register | a table in GATES.md, a registered marker, a removal date | `--strict-markers` makes the marker a rule; the honest-numbers rule forbids a quiet re-run |
| 10 | ATK-TEN-1 trial 3 | a reported check, not gated | it reads numbers against chunks and cannot read a claim in words; a gate on it would be a gate on a rule that misses most forms |
| 11 | S7a-J11 | layers resolved against GUARDRAILS.md's names | "no letter" is the wrong test; a name list is the right one |
| 12 | One node | S8 `done` at the pull request | the phase map has one S8 node |

## Acceptance criteria

Evidence marked **live** runs on your Mac through the `make` targets only (or `raglab ollama
session`), one model per session, on AC power, with nothing else running, never beside `make
check`; under the recommended answers **no criterion needs a live session**. **[CI]** marks what
only the pull request's checks prove. Each break is made on a committed file, at the head the
criteria judge gives its verdict on, and restored from git; "expected pass" marks a break that
must not trip its check.

| # | Criterion | Evidence | Break |
|---|---|---|---|
| GA1 | **GATES.md.** One row per gate of the main plan's map in how-to 08's seven columns plus a mode (`ci`, `local`, `documented only`); every make target, test marker and runbook named exists; pr-fast's "What runs" names every `make` step of the workflow; the three lab runbooks written | `tests/unit/test_gates_doc.py`; review | a row's target renamed to one the Makefile lacks: the test fails naming the row; a `make` step added to pr-fast.yml and not to GATES.md: it fails naming the step; a mode cell emptied: it fails |
| GA2 | **THRESHOLDS.md: a reason for every metric.** Every metric key of every published manifest's results, every guard-suite rate and latency, and the perf names have a row with non-empty Gate and Reason cells; every Gate cell is one of the gates or `reported` | `tests/unit/test_thresholds_cover_the_metrics.py` | a Reason cell emptied: the test fails naming the metric; a metric key renamed in a copied manifest: it fails naming the key; a row deleted: it fails |
| GA3 | **TEST-PLAN's gate cells.** Section 8's Gate column filled from GATES.md for every row (no `tbd`); section 10's report line filled | `tests/unit/test_test_plan.py`, extended | one Gate cell set back to `tbd`: the test fails naming the R-id; a Gate cell naming a gate GATES.md lacks: it fails |
| GA4 | **The cause rule.** `cause` on every failed case-trial of a generation or retrieval record, from the record's fields in the order ingestion, retrieval, abstention, generation; null on a passed trial; none on `unavailable` or `invalid_output`; `record.validate` recomputes it; the schema's new fields optional; every committed record still valid; the docs say what the rule cannot separate | `tests/evals/test_causes.py` on hand-built cases (one per rule and one per pair of rules, the order decided); `tests/retrieval/test_publish.py::test_the_committed_runs_are_valid_local_dev_runs_with_a_current_baseline` | a `cause` edited on a copied record and resealed: `validate` refuses it naming the case; the order swapped in code: the pair tests fail; `cause` made required in the schema: the committed-runs test fails |
| GA5 | **Causes reported.** `results.causes` (per case-trial and per case) in new manifests and a section of `report.md`; `raglab causes <run_id>` writes `runs/causes/<run_id>.json` for a published run without touching it; the v2 consistency baseline's and its four repeats' counts in the ledger from that output; the fake e2e run carries causes | `make causes RUN=...`; `runs/causes/`; `tests/e2e/test_e2e_fake.py`; `git status` clean under `runs/published/` after the command | a count edited in a `runs/causes/` file: its sha256 check fails; a published record's file touched by the command in a copy: the publish test fails |
| GA6 | **The judged gate reads S6's verdicts (D1 A).** `raglab compare` on two judged records (the same dataset, split, trials and judge identity; per criterion B minus A with a paired bootstrap interval and the flipped cases); `raglab gate --judged B --against A` fails only when a criterion the calibration record marks trusted has an interval entirely below zero; reported-only and not-trusted criteria printed, never gating; an unnamed criterion refused; with no trusted criterion the gate refuses and GATES.md says so; new judged manifests name `judge.calibration_record`; S6's v2 record matched by identity, unedited; THRESHOLDS.md's row with the reason | `tests/judge/test_judged_compare.py` on the published v2 judged record against copies of itself (identical: every interval [0, 0], passes; 20 trusted verdicts flipped to fail: the interval below zero, fails; the same on a reported-only criterion: passes, expected pass) | the trust check removed: the reported-only break gates and the test fails; a record's status edited from trusted to reported only in a copy: the gate stops gating that criterion, and `calibrate`'s pin (S6) refuses the copy |
| GA7 | **The drift alert.** A nightly run compares with the previous published nightly of its config (paired, flipped cases) and writes an `alert` line when the interval lies entirely below zero; never blocks; the judged alert between consecutive judged records on trusted criteria names the recalibration trigger; the first nightly on v2 is the reference | `tests/unit/test_held_out_split.py`, extended with a FakeChat nightly pair; the record's `alert` field; `runbooks/nightly.md` | the second record of the pair given 20 flipped cases: the alert fires naming them; the alert made to block: the test fails |
| GA8 | **The suite audit.** `docs/audits/<date>-suite-audit-v0.2.md` with the seven sections of the main plan's list, each a check run with its command and output, the not-covered list, and the lab-versus-production line; `scripts/audit_suite.py` recounts its counts | `make audit-suite` (exit 0); `tests/unit/test_audit_suite.py`; review | a count in the report edited: the recount fails naming the section; a section heading removed: the test fails |
| GA9 | **Test-split contamination.** The script lists every test-split id of `golden.v2.jsonl` and finds none in `src/`, `config/`, `datasets/security/`, a prompt, THRESHOLDS.md or a published dev record; the test-split runs that exist are v1.1's under `release` only | `tests/unit/test_split_contamination.py`, in `make test` (pr-fast's test step, no workflow change) | a test-split id planted in a comment of `src/raglab/guard/injection.py`: the test fails naming the file and the id; restored |
| GA10 | **The embedder swap.** A second model pinned (revision, every file's sha256), fetched once by its own target with your go (`make model` and pr-fast's cache unchanged); dense and hybrid retrieval runs on dev with it, offline; `raglab compare` against the `ade9397` runs: B minus A of hit@5, MRR@5 and recall@5 with paired intervals and the flipped questions, quoted in the ledger from the files; `raglab gate --config` with the swapped config refuses as stale; the consistency baseline not re-made; the corpus build and the snapshot unchanged; the runs published under D2 A | the records; `runs/compare/`; `index.json`; `tests/unit/test_model_fetch.py` extended for the second model; `git diff origin/main -- corpus/` empty | one pinned sha256 of the second model changed: `make model-swap` refuses it; a compare file edited: its check fails |
| GA11 | **The upgrade record (how-to 10).** `docs/UPGRADES.md` with its shape and the first record, the 2026-10-31 dependency upgrade from its merged commit, its replay run in S8 (`make check`, `make gate`, `make replay`, `make guard-suites`; no baseline stale by rule, which the record says the rule does not see); `docs/releases/v0.1.0.md` and `runbooks/release.md` point at it; fastembed 0.9.1 as a second record only if you take it | the file; the replay outputs in the ledger; `tests/unit/test_repo_docs.py` extended (the release runbook names the record) | the runbook's pointer removed: the test fails |
| GA12 | **The flake policy.** GATES.md's Flakes section: the definition, the classes, the retry rule (D3), the quarantine (marker `flaky` registered, out of `make check` and pr-fast, `make test-flaky`), the register (empty; the two historical observations as environment failures), the lab label | `tests/unit/test_flake_register.py`; `pyproject.toml`'s markers | a test marked `flaky` with no register row: the test fails naming it; a row's removal date past: it fails; `flaky` left in `PYTEST_OFFLINE`'s selection: it fails |
| GA13 | **S4b-J4.** `raglab gate` refuses a THRESHOLDS.md with two consistency rows, naming both | `tests/generation/test_consistency_gate.py` | a second row added to a copy: the gate refuses; the refusal removed: the test fails |
| GA14 | **S7a-J1.** `raglab publish` refuses a record whose `dataset.sha256` is no listed version (the datasheet's Versions table for a golden run, the security pack's for an attack run), naming the hash | `tests/retrieval/test_publish.py` | the refusal removed: the new test fails, and the S4-J10 test still catches the published copy (expected pass) |
| GA15 | **S7a-J11.** The threat-model rows test resolves a Layer cell's names against GUARDRAILS.md's layers; a cell naming none ("n/a", a dash, empty, an unknown name) is no layer and needs its reason | `tests/security/test_threat_model.py` | LLM03's cell set to "n/a" with its reason removed: the rows test fails naming the row; a layer name misspelt: it fails |
| GA16 | **ATK-TEN-1 trial 3.** The `other_tenant_claim` check on attack records, reported and never gated, with its limit written in THREAT-MODEL's not-covered list; run read-only over the published `762b163` record (and the `8f7c94d` records if they still exist), the counts in the ledger from the command; cause `generation` | `tests/security/test_attack_runs.py`; `runs/causes/` for the attack record | a copied attack answer given the other tenant's name and a number no chunk holds: the count rises naming the case; the check made to gate: the test fails |
| GA17 | **R-22 (D4).** A: the audit's not-covered list and TEST-PLAN's gap row record it as not covered, with the reason (a register change makes every v2 baseline and S6's calibration stale) and the cost of planting it; the Gate cell says `not covered`. B: the same wording plus a dated corpus pull request after S8 | `tests/unit/test_test_plan.py`; the audit | the gap row's reason emptied: the test fails |
| GA18 | **Docs, `make check`, [CI] pr-fast.** THRESHOLDS, TEST-PLAN, THREAT-MODEL, LOCAL-MODEL (only under D2 B or D1 C), OBSERVABILITY (the alert line), README, ARCHITECTURE and README: S8 `done`; the main plan: dated notes for D1 to D4 and the progress section; `docs/releases/v0.1.0.md`'s pointer; a CHANGELOG line; the ledger; `make check` green; no new dependency (`git diff origin/main -- pyproject.toml uv.lock` empty, unless GA11's live example); the pr-fast `check` job's time before and after against its 20 minutes | `test_diagram.py`, `test_readme.py`, `test_repo_docs.py`, `test_changelog_check.py`; the `make check` tail (`/usr/bin/time -p`); the pull request's checks | ARCHITECTURE's S8 class changed without the README's: `test_readme_status_matches_architecture` fails; a planted lint error: `make check` stops at `lint` |

## Time

Every figure is an estimate, with its basis in "Where S8 starts" (measured times).

### Your review tasks and time

1. **This plan**, with D1 to D5: about 30 to 40 minutes (S7's estimate for a plan of this size;
   none was measured).
2. **The go for the second model's download** (GA10): a minute, when the developer asks.
3. **GATES.md and the flake policy**: about 20 minutes.
4. **The suite audit report**: about 30 to 45 minutes; it is the document the capstone (S11) and
   an interviewer will read.
5. **The pull request**: about 45 minutes (S4's and S7's estimate).
6. **fastembed 0.9.1**, if you decide it inside S8: about 10 minutes.

In all, about 2 to 2.5 hours. No labelling, no ratification, no sign-off of corpus material (D4 A).

### Mac time

| Work | Sessions | Each | Total |
|---|---|---|---|
| The embedder swap (D2 A): the download, two retrieval runs, two compares | none (Ollama); offline | the runs 10 to 14 s each; the download's size depends on the model chosen | about 5 minutes plus the download |
| The upgrade replay (GA11): `make check`, `make gate`, `make replay`, `make guard-suites` | none; offline | `make check` about 4 min 44 s (283.64 s); the others unmeasured, no model | about 10 to 20 minutes |
| `raglab causes` over the published runs | none; offline | seconds | — |
| The criteria judge's reproduction | none; offline | the same again | about 15 to 30 minutes |
| D2 B only: one generation session on the swapped embedder | 1 generator | about 9 to 10 min (8 min 59 s to 9 min 41 s measured) | about 10 minutes, plus the judge's repeat |
| D1 C only: one judge session on S4b's repeat 2 | 1 judge | about 2 h 21 min (2 h 20 min 53 s measured by S6) | about 2 h 21 min |

Under the recommended answers: **no Ollama session**, about 30 to 60 minutes of offline Mac time
over the stage. Every session, if any, runs through the `make` targets or `raglab ollama session`
only, one model per session, on AC power, and only on the orchestrator's go; nothing else runs
beside one.

### Agents' time

| Role | Work | Estimate |
|---|---|---|
| Developer (Opus 5.5) | the cause rule and its command, the judged comparison and gate, the alert, GATES.md and the runbooks, the THRESHOLDS test, the audit and its scripts, the swap, the upgrade record, the flake policy, the five follow-ups, docs | 6 to 8 h |
| Criteria judge (Fable 5.1) | the evidence again, the breaks, the recounts, the swap's runs again | 2 to 3 h |
| Fix rounds | at most two | 1 to 2 h each |

Basis: S7a's measured developer stage (about 5 to 7 h estimated, with a live session) and S4b's
offline estimates; S8 is wider (many small pieces) and shallower (no live session) than S7a.

**`make check` and pr-fast.** The new tests are offline and small; the contamination script reads
the tree once. pr-fast's `check` job ran 16 min 59 s of its 20 on S7a's last run and S6's tests
come first; GA18 reports the time before and after, and a raise needs your go.

## How it will run

1. **Approval:** D1 to D5, quoted under Approval. From its first commit the developer keeps the
   ledger, `docs/plans/2026-10-31-s8-gates-causes-audit-ledger.md`: each criterion's evidence,
   every command's output, every answer of yours, verbatim.
2. **Now, offline, against `main` at `ef46a61`** (the developer, Opus 5.5): GATES.md and the
   runbooks, the THRESHOLDS test, the cause rule and `raglab causes` over the published v2 runs,
   the judged comparison on hand-built records, the drift alert, the flake policy, GA13 to GA16,
   the audit's sections 1 to 3 and 5 to 7, the contamination script, the embedder swap after your
   download go; `make check` green.
3. **After the dependency pull request merges:** rebase; the upgrade record and its replay (GA11).
4. **After S6 merges:** rebase; the trust check against the real calibration record (GA6), the
   calibration section of the audit (GA8), THRESHOLDS' and TEST-PLAN's judged cells (GA2, GA3).
5. **After S7b merges:** rebase; the `manual` rows (GA1), S7b's findings in the coverage section,
   GA15 over S7b's threat-model rows, the status lines.
6. **Docs**, the main plan's dated notes, `make check` green again.
7. **The criteria judge** (Fable 5.1, its own worktree and context): re-runs the evidence, makes
   each break and restores it, re-runs the recounts and the swap's retrieval runs; a verdict per
   criterion: met, not met, needs CI, or not applicable.
8. **Fix rounds:** at most two. Product choices come back to you. A third round needs your go.
9. **Report:** the pull request's body is the stage report: n of m criteria met, what needs CI,
   what was cut, the Mac time used, and a CHANGELOG line. You merge it by hand, with a merge
   commit. Then the v0.2.0 release plan.

Sequential subagents, unless your go asks for a Workflow. Hosted spend: none. Sign-ups: none.

## Decisions needed

**D1. Which judged criteria gate, and by what rule.** Conditional on S6's verdicts, which do not
exist yet; the code reads them from the record either way.

- **A (recommended): "Trusted criteria gate by the paired interval, locally".**
  - `raglab gate --judged` fails only on a criterion S6's record marks trusted (kappa 0.80 or
    more: at most `grounded` and `abstains`), when B minus A's paired interval lies entirely below
    zero (the main plan's eval-on-change rule). Reported-only and not-trusted criteria never gate.
  - No margin is invented; the interval carries the uncertainty. If S6 trusts neither criterion,
    nothing gates and GATES.md says so.
  - Mac time: none. The gate runs by hand until keys exist.
- **B: "Nothing judged gates in v0.2".** The comparison and the trust check are built and reported;
  the gate is wired when keys exist (S10). What it changes: the eval-on-change row stays
  "reported" through v0.2.0.
- **C: "Trusted criteria gate by a case margin, as S4's gate does".** The margin comes from a
  between-run repeat: one judge session on S4b's repeat 2 (about 2 h 21 min measured), and the
  margin is the drop between the two judged runs, at least one case. What it changes: one Mac
  session, a margin from one repeat (S4 used four), and S6's record stays the baseline.

**D2. The embedder swap: published or not.**

- **A (recommended): "Published as a measured result, retrieval only".** The two retrieval runs on
  the second embedder are published (provenance local, a new config name, no baseline) with the
  compare files committed beside the ledger's evidence; the playground shows them. No session.
- **B: "Also one generation session on the swapped embedder".** One `make eval-local` on the
  swapped config (about 9 to 10 minutes) to see what moved in behaviour pass^3 and the causes;
  published as a non-baseline run. The criteria judge repeats it: about 20 minutes of Mac time in
  all.
- **C: "Kept on the branch, numbers in the ledger only".** Nothing published; the second model's
  pin stays in the adapter for the record.

**D3. The flake policy's retry rule.**

- **A (recommended): "No automatic retry; one recorded re-run by hand".** No test or job retries
  itself. A failed CI job or local run may be re-run once, by hand, and a pass with no change is
  written in the register (the test, the run id, the date, the suspected cause) and reviewed; a
  second entry for the same test within 30 days quarantines it. S9's "none run again for a better
  number" applies to any measured number: a re-run never replaces a recorded number.
- **B: "pytest-rerunfailures, one retry, marked tests only".** A new dev dependency in the main
  project; tests marked `flaky` retry once in `make check` and pr-fast and are not quarantined.
  What it changes: a flake can pass unseen on its retry; the register fills from the plugin's
  report instead of by hand.
- **C: "Zero tolerance".** No re-run at any level; every failure is a fix or a quarantine. What it
  changes: an environment failure on a shared runner blocks a pull request until the runner is
  fast again.

**D4. R-22, the requirement with no planted feature.**

- **A (recommended): "Not covered, recorded".** The audit's not-covered list and TEST-PLAN's gap
  row say R-22 is not covered in v0.2, why (every planted conflict has a precedence rule, so the
  answer key stays unambiguous), and what planting it would cost: a register change makes the v2
  retrieval and consistency baselines stale (five sessions, about 50 minutes), S6's calibration
  stale by its own trigger ("a new golden set version": a judge session of about 2 h 21 min and 30
  fresh labels), and new golden cases for you to sign off. S12 (the handbook corpus) is the next
  natural corpus change.
- **B: "A corpus pull request after S8".** Two registered documents that disagree with no
  precedence rule, new cases, a new golden set version, and the re-baselines and recalibration
  above, in a pull request of its own after S8 merges; your sign-off of the documents and the
  cases as in S1a and S4b (about 1 to 2 hours of yours, an estimate). The audit records R-22 as
  "planted after v0.2".

**D5. This plan.**

- **"Approve and start (Recommended)":** the offline build starts on
  `feat/s8-gates-causes-audit` against `main` now; the parts that need S6, S7b and the dependency
  pull request wait for their merges, in the order above.
- **"Changes first":** say what to change, and the plan comes back.

## Risks

- **S6's verdicts.** If neither `grounded` nor `abstains` reaches kappa 0.80, the judged gate gates
  nothing in v0.2; GA6 is still met (the code refuses honestly) and the audit says so.
- **The calibration record's format** is S6's; GA6's trust check is written against its ledger's
  description and adjusted after the merge. A mismatch costs an hour, not a decision.
- **Merge conflicts** with S6, S7b and the dependency pull request in the shared files above; S8
  rebases three times and the status lines go last.
- **pr-fast's `check` job**: 16 min 59 s of 20 after S7a, with S6's tests next. S8's tests are
  small; GA18 measures, and a raise needs your go.
- **The cause rule reads what the record holds.** It cannot see why a model answered as it did;
  the docs say which pairs it cannot separate, and the counts are a triage, not a diagnosis
  (lab practice: production would add a judged or human cause on a sample).
- **The second model's download** is network, once, with your go; its size is unknown until
  chosen, and the adapter must keep the first model's pins untouched.
- **The `8f7c94d` records** for GA16 may be gone from `runs/tmp/`; the check then runs on the
  published `762b163` record only, and the ledger says so.
- **The audit can read as a self-assessment.** Every section is a command with its output and a
  recount script, and the criteria judge re-runs each; S11's system audit repeats it with an
  adversarial re-test.
- **The judged comparison on one run.** With one judged record on v2, GA6's live evidence is
  copies of that record; the first real comparison comes with the next judged run (answer-v3, at
  your choice).
- **The command guard.** If it refuses a command, the developer splits it or reports it, and never
  routes around it.

## Approval

The go for this draft (2026-10-31, about 14:35 UTC), verbatim: "yes lets do that", your answer to
the orchestrator's "The S8 plan is unwritten and can be drafted on your go." It covers drafting this
plan only.

Your answers to D1 to D5 are quoted here, with the question, when you give them. Until then:
`status: draft`.

## Sources (read 2026-10-31)

- The repository at `ef46a61`: CLAUDE.md and CONTRIBUTING.md; the main plan
  (`docs/plans/2026-10-05-raglab-plan.md`: the S8 row, "Gate map (how-to 08 columns)", "Security
  and audits", "Run record v1", "Progress and next steps (updated 2026-10-26)", the phase map);
  the S7 plan and ledger (`docs/plans/2026-10-23-s7-attack-guardrails*.md`); the S4b ledger
  (`docs/plans/2026-10-23-s4b-golden-set-v2-ledger.md`); the S9 plan; docs/THRESHOLDS.md,
  CRITERIA.md, TEST-PLAN.md, THREAT-MODEL.md, GUARDRAILS.md, ARCHITECTURE.md, LOCAL-MODEL.md,
  COMPATIBILITY.md, `docs/releases/v0.1.0.md`, `runbooks/release.md`, README.md;
  `src/raglab/evals/` (gate, publish, compare, behaviour, record, attack_record, replay,
  guard_suites), `src/raglab/core/reasons.py`, `src/raglab/adapters/fastembed_embed.py`,
  `src/raglab/__main__.py`; the Makefile; `.github/workflows/pr-fast.yml`;
  `runs/published/index.json` and the manifests of `20261024T090351Z-generation-local-ollama-dev-ade9397`,
  `20261024T090200Z-retrieval-dense-dev-ade9397` and `20261025T205853Z-attack-local-defences-on-dev-762b163`;
  `runs/guard-suites/`, `runs/replays/`; `datasets/golden.v2.jsonl` (counts), `datasets/DATASHEET.md`;
  `scripts/`; `tests/security/test_threat_model.py`, `tests/retrieval/test_publish.py`,
  `tests/unit/test_test_plan.py` and the unit test list.
- The S6 plan and ledger at `eff197d` (`feat/s6-judge-calibration`), read without checking the branch out
  (`docs/plans/2026-10-23-s6-judge-calibration.md` and its ledger): the bar and its verdicts,
  "The record", the triggers, "What S6 gives later stages", the decisions, the v2 judge session's
  time and the calibration folder's path.
- The dependency pull request's commit `e5969f4` on `build/deps-2026-10-28`, read with `git show`.
- The orchestrator's notes of 2026-10-31: the go, the dependency pull request's number (#35), and
  fastembed 0.9.1's Pillow cap, the last two not verified from the repository.
