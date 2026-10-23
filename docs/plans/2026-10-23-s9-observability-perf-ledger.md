---
stage: S9
nodes: [S9]
---

# S9 ledger: tracing with redaction, a perf mode that prod refuses, and a k6 smoke in CI

Plan: [2026-10-23-s9-observability-perf.md](2026-10-23-s9-observability-perf.md). Branch
`feat/s9-observability-perf`, cut from `main` at `2b9ba60` (answer-v2's merge); the plan's commit
is `1f8e111`.

## Approval and decisions

The message that opened S9 planning (2026-10-23, about 22:45 WEST), verbatim, as the plan quotes
it: asked "Which planners should I launch now, next to S4b's? Each writes its plan only, in its
own worktree, and stops for your approval.", the maintainer answered "S6 planner (Recommended), S7
planner (Recommended), S9 planner".

The maintainer's answer (2026-10-23, about 23:30 WEST, through the orchestrator's question
prompt), with its question, verbatim. The question: "S9, observability and performance. Approve
with all five recommended answers? D1: merge when ready and ship in v0.2, bringing this v0.3
stage forward. D2: the OpenTelemetry collector runs in CI only, with no account. D3: k6 runs in
its own parallel pr-fast job, with the median gated at 2× the slowest of ten runs (you then add
`perf` to the required checks). D4: message content in traces is opt-in, for local debugging only.
D5: approve and start. Your time is about 1.5–2 h, with no Ollama sessions." The answer: "All five
as recommended (Recommended)".

It selects each decision's recommended option, named by its label in the plan:

| Decision | Option selected | What was done |
|---|---|---|
| D1 When S9 merges, and which release ships it | "Merge when ready, ship in v0.2" | The main plan's dated note (2026-10-23) quotes the question and the answer; the phase map, in its three copies (the main plan, `docs/ARCHITECTURE.md`, `README.md`), has `S8 --> S3h` where it had `S8 --> S9`; S9 is `wip` in the two status copies |
| D2 The collector and Langfuse | "Collector in CI only, no account" | The collector runs only inside `make perf-smoke` (pr-fast's perf job, and locally while building); the Langfuse pipeline is built and validated and stays off. OB8 is not applicable, by D2. The main plan's open variable "Langfuse cloud as an optional sink" is answered for S9 |
| D3 The k6 smoke in pr-fast | "Own parallel job; median gated at 2× the slowest of ten runs" | A `perf` job beside `check`; the maintainer adds `perf` to the required checks once it has run |
| D4 Message content in traces | "Opt-in for local debugging only" | Off by default; one setting turns it on, honoured only where `RAGLAB_ENV` is `ci` or `local` |
| D5 This plan | "Approve and start (Recommended)" | The plan's status is `approved`; the build started at 23:36 WEST on `feat/s9-observability-perf` at `1f8e111` |

## The state of `main` before the build

`make audit` is red on `main` from advisories published on 2026-10-23, before any change of S9's.
On the clean tree at `1f8e111`, `make -i audit` (both audit lines run) gave, for the main
environment, "Found 6 known vulnerabilities, ignored 43 in 3 packages": filelock 4.0.12 (one
advisory, fixed in 4.2.1), pillow 12.3.0 (two, fixed in 13.0.0) and pypdf 6.19.0 (three, fixed in
6.21.2); and for the DeepEval tool's exported lock, "Found 5 known vulnerabilities, ignored 43 in 2
packages": the same pillow and pypdf lines. (Their ids are in pip-audit's output; the privacy
check's ticket-id pattern refuses them in a committed file.) The orchestrator fixes them in a separate pull request; this branch
never touches `AUDIT_SKIP`. Here "green" means `make -k check` with only `audit` red, from exactly
these lines.
