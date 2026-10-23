---
stage: S7
nodes: [S7]
---

# S7 ledger: attack, guardrails and red team

Plan: [2026-10-23-s7-attack-guardrails.md](2026-10-23-s7-attack-guardrails.md). Branch
`feat/s7-attack-guardrails`, cut from `main` at `2b9ba60` (answer-v2's merge); the plan's commit is
`bfbe6ec`. One ledger in two parts (the plan's choice 13): Part S7a now, Part S7b after S6.

## Approval and decisions

The go for the draft (2026-10-23, about 22:45 WEST), verbatim (quoted in the plan): "S6 planner
(Recommended), S7 planner (Recommended), S9 planner", the answer to "Which planners should I launch
now, next to S4b's? Each writes its plan only, in its own worktree, and stops for your approval.",
after the question "can we launch more sub agents in parallel to that one to speed up the
development phase for upcoming steps into the plan?".

The approval (2026-10-23, about 23:30 WEST), verbatim (quoted in the plan's Approval). The question:
"S7, attack, guardrails and red team. Approve with all five recommended answers? D1: split into S7a
now (threat model, rule-layer guards, attack suite, block and must-not-block suites, 10–20 min of
Mac) and S7b after S6 (promptfoo red team, Guardrails AI). D2: no corpus change; new attack inputs
go in a separate security pack. D3: the new guards are on by default, proven to change nothing by
replaying S4b's v2 runs. D4: no sign-up, so Prompt Guard 2 is not covered. D5: approve and start.
Your time is about 3.5–5 h over both parts." The answer: "All five as recommended (Recommended)".

The answer selects each decision's recommended option:

| Decision | Option chosen (the plan's label) | What it means for the build |
|---|---|---|
| D1 Scope | "Split: S7a now, S7b after S6 (Recommended)" | S7a (threat model, rule layer, deterministic attack suite, suites per filter, the live attack runs) is built now; S7b (promptfoo, Guardrails AI) after S6 merges; two pull requests under the one node S7 |
| D2 The attack material and the corpus | "No corpus change; a separate security pack (Recommended)" | no change to the register, the clean inventory or the answer key; new inputs in `datasets/security/` |
| D3 The new guards and the v2 baselines | "On by default, proven inert by replay (Recommended)" | the layers join `default_guards()`; the guard set joins the staleness rule; a committed replay with zero events keeps the baseline current |
| D4 Sign-ups | "No sign-up; Prompt Guard not covered (Recommended)" | THREAT-MODEL.md lists Llama Prompt Guard 2 as not covered |
| D5 This plan | "Approve and start (Recommended)" | S7a's build starts on this branch |

## Part S7a

(The developer fills this part from the build: what was built, the evidence per criterion, the
breaks, the runs, and the `make check` tail.)

## Part S7b

(After S6 and S7a merge.)
