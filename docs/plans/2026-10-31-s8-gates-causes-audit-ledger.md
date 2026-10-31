---
stage: S8
nodes: [S8]
---

# S8 ledger: gates, failure causes and the suite audit

Plan: [2026-10-31-s8-gates-causes-audit.md](2026-10-31-s8-gates-causes-audit.md). Branch
`feat/s8-gates-causes-audit`, cut from `main` at `ef46a61` (the merge of the plan update #34); the
plan's commits are `cdb6810` (the draft) and `4109586` (the approval).

## Approval and decisions

The go for the draft (2026-10-31, about 14:35 UTC), verbatim (quoted in the plan): "yes lets do
that", the answer to the orchestrator's "The S8 plan is unwritten and can be drafted on your go."

The approval (2026-10-31, recorded at 16:24 UTC), verbatim (quoted in the plan's Approval). The
question: "The S8 plan (gates, failure causes, suite audit) is drafted: 18 criteria GA1 to GA18,
your time about 2 to 2.5 h, no Ollama session under the recommended answers. Approve with all five
recommended answers? D1: trusted judged criteria gate by the paired interval, locally (only after
S6's verdicts). D2: the embedder swap is published as a measured result, retrieval only. D3: flake
policy with no automatic retry, one recorded re-run by hand. D4: R-22 is recorded as not covered,
with the reason and the cost. D5: approve and start." The answer: "All five as recommended
(Recommended)".

| Decision | Option chosen (the plan's label) | What it means for the build |
|---|---|---|
| D1 Which judged criteria gate | "Trusted criteria gate by the paired interval, locally" | `raglab gate --judged` fails only on a criterion the calibration record marks trusted whose paired interval lies entirely below zero; reported-only, not-trusted and unnamed criteria never gate; with no record or no trusted criterion the gate refuses |
| D2 The embedder swap | "Published as a measured result, retrieval only" | two retrieval runs on the second embedder, published after the download go; no generation session |
| D3 The flake policy's retry rule | "No automatic retry; one recorded re-run by hand" | no test or job retries itself; a re-run by hand is written in the register; a second entry within 30 days quarantines |
| D4 R-22 | "Not covered, recorded" | the audit's not-covered list and TEST-PLAN's gap row say why and what planting it would cost; the Gate cell says `not covered` |
| D5 This plan | "Approve and start" | the offline build starts on this branch against `main` at `ef46a61`; the parts that need S6, S7b and the dependency pull request #35 wait |

## What the how-tos ask, as the main plan quotes them

The plan asks the developer to read how-to 08, 09 and 10 at the start of the build and to list
what each asks. The handbook itself was **not fetched** at STOP 1 (the build is offline, no network);
what follows is what the main plan (`docs/plans/2026-10-05-raglab-plan.md`) quotes of each, and
the build is held to that.

- **How-to 08, the gate map:** seven columns, "Gate, Trigger, Keys, Blocks, Threshold and reason,
  Owner and runbook, What runs" (the main plan's "Gate map (how-to 08 columns)"), with the rows
  pr-fast, eval-on-change, nightly, manual, weekly, release and prod-sample, and the rule that "the
  gate map in the repo marks each gate `ci` or `local`, so nobody mistakes a local run for an
  automated one".
- **How-to 09 B, the suite audit:** a written report in `docs/audits/` "at the end of v0.2:
  coverage cells against cases, skips, phrase-locked criteria, calibration record, test-split
  contamination, intervals and pairing, thresholds with reasons" (the main plan's "Security and
  audits", part 3); the system audit (part A) is S11's, with its "not covered" list mandatory, and
  the suite audit carries one of its own by the S8 plan.
- **How-to 10, the upgrade record:** the main plan's S8 row asks for an "upgrade record (how-to
  10)"; the S8 plan gives its shape: "what moved (package, from, to, the cooldown read), what was
  replayed (the gates re-run at the upgrade ...), what was tried and not taken, what changed in the
  docs, and the decision with its date", the lab form of the release gate's "upgrade replay".

## What was built (developer, offline, 2026-10-31)

Filled in below as each part lands.
