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

## What was built (developer, offline)

Filled as the build lands.

## Evidence per criterion

| GV | Status | Evidence | Break (restored from git) |
|---|---|---|---|
| GV1 | not started | | |
| GV2 | not started | | |
| GV3 | not started | | |
| GV4 | not started | | |
| GV5 | waits for the cases | | |
| GV6 | not started | | |
| GV7 | waits for the labels judge, the sign-off and F | | |
| GV8 | not started | | |
| GV9 | not started | | |
| GV10 | waits for F | | |
| GV11 | waits for F (live) | | |
| GV12 | not started | | |
| GV13 | not started | | |
| GV14 | not started | | |

## Runs S4b made

None yet. S4b makes no test-split run (the plan, "The runs S4b makes").

## make check at the plan commit

`f6f7d7e`, before any change (`make check`, this Mac): **exit 2, stopped at `audit`**. pip-audit
found 5 advisories that are not in the Makefile's skip list, all published after the last one was
added (`8a330b7`, 2026-10-22): two for Pillow 12.3.0 (fixed in 13.0.0) and three for pypdf 6.19.0
(fixed in 6.21.2), each reported under a CVE id only (the ids are left out here: the privacy
check reads that shape as a ticket number): "Found 5 known vulnerabilities, ignored 43 in 2
packages". The skip list holds two decisions of the maintainer
(the Makefile's comment), so S4b does not extend it; the failure is the same on `main`, whose
Makefile and lock this commit shares. Every other target of `make check`, run in one `make`
call: exit 0, "251 files already formatted", "All checks passed!", "0 errors, 0 warnings, 0
informations", gitleaks "no leaks found" twice, privacy "0 hits across 367 files (42 rules)", "0
architecture violations in src/raglab", "check-dataset: datasets/golden.v1.jsonl passes (34
retrieval questions, 40 behaviour cases, sha256 5f8cdaf18783)", "1369 passed, 2 deselected, 1
warning in 168.06s", "recall@5 0.682 (n 22) passes", "api-smoke: passed".

## Developer choices (for the review)

Filled as the build lands.

## Notes

- The developer's command guard refuses some command shapes (a heredoc, a subshell, `time` with
  some arguments); each such command was split into plain ones, never routed around.
