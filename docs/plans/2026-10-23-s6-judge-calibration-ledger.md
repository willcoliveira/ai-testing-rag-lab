---
stage: S6
nodes: [S6]
---

# S6 ledger: judge calibration on 30 blind labels

Plan: [2026-10-23-s6-judge-calibration.md](2026-10-23-s6-judge-calibration.md). Branch
`feat/s6-judge-calibration`, cut from `main` at `2b9ba60` (answer-v2's merge); the plan's commit
is `88202a5`.

This ledger covers **phase 1, the offline build** (the plan's "How it will run", step 2): everything
the plan allows before S4b merges. The judged baseline on golden set v2 (JC3), the cap (JC2's
config change), the sample (JC4's committed file), the labels (JC5 to JC8) and the numbers (JC10 to
JC12's) wait for S4b's merge, the dry run and the judge session, each named below.

## Approval and decisions

The go for the plan's draft (2026-10-23, about 22:45 WEST) is quoted in the plan's Approval.

**The approval (2026-10-23, about 23:30 WEST).** The question, verbatim: "S6, judge calibration.
Approve with all five recommended answers? D1: calibrate grounded and abstains, 15 labels each. D2:
kappa 0.80 or more trusts a criterion, under 0.60 stops it. D3: you label alone, plus a blind
re-label of 12 at least a day later. D4: a miss is recorded and fixed in a follow-up PR. D5: approve
and start. Your time is about 3 h 20 min to 5 h 20 min, and the Mac needs one judge session of
about 2 h 15 min after S4b merges."

The answer, verbatim: "All five as recommended (Recommended)". It selects each decision's
recommended option:

| Decision | The option it selects | What is done |
|---|---|---|
| D1 Which criteria the 30 labels calibrate | "grounded and abstains, 15 each (Recommended)" | `bar.toml` allocates 7 judge passes and 8 judge fails to each of `grounded` and `abstains`; the other five criteria stay reported, uncalibrated and never gated |
| D2 The bar | "kappa 0.80 trusts, under 0.60 stops (Recommended)" | `bar.toml` and THRESHOLDS.md: per criterion, kappa 0.80 or more trusted, 0.60 to under 0.80 reported only, under 0.60 not trusted |
| D3 The second labeller | "One labeller, plus a blind re-label of 12 (Recommended)" | `raglab label --relabel`: 6 per criterion, seeded, in a new order, at least 24 hours after the seal; the record carries the single-labeller caveat |
| D4 If a criterion misses the bar | "Record it; fix in a follow-up (Recommended)" | a miss is recorded with its classified causes and the follow-up in the record's "next" line; nothing is signed off or judged again in S6 |
| D5 This plan | "Approve and start (Recommended)" | the offline build started on `feat/s6-judge-calibration` at `88202a5`; the first live step waits for S4b's merge |

## Blindness, from the moment the v2 record exists

Once the judged baseline on v2 exists, this ledger, the pull request's drafts and every message to
the maintainer give its aggregate numbers only: no item-level verdict (a case, trial and criterion
with its verdict, quote or reason) is quoted until the labels are sealed (the plan, "Blindness
starts here").

## The state of `main` at the start

`make audit` is red on `main`, before any S6 change: advisories published on 2026-10-23 hit
Pillow, pypdf and filelock. The orchestrator fixes it in a pull request of its own; S6 never
touches the Makefile's `AUDIT_SKIP`. Until that merges, "green" here means `make -k check` with
only `audit` red. From `make audit` on this branch at `88202a5` (2026-10-23, 23:48 WEST): the first
audit line (the main environment) stopped with "Found 6 known vulnerabilities, ignored 43 in 3
packages" and "make: *** [audit] Error 1", and its table named six advisories:

| Package | Version | Advisories | Fix version |
|---|---|---|---|
| filelock | 4.0.12 | 1 | 4.2.1 |
| pillow | 12.3.0 | 2 | 13.0.0 |
| pypdf | 6.19.0 | 3 | 6.21.2 |

The advisory ids are left out here: the repository's privacy check reads a CVE id (the letters,
the year and a number, joined by hyphens) as a ticket id, and the pre-commit hook refused the commit
that quoted them (six hits of the generic ticket rule); the S5 ledger counted its advisories in
words too.
