# Runbook: eval-on-change (lab)

Owner: quality. The gate is `eval-on-change` in `docs/GATES.md`; mode **local** until ADR-002's
keys exist. This is the lab version; the last section says what production adds.

## When

Before the pull request of any change to the prompt, the generation code, the chunker, the
embedder or the model (the consistency gate's trigger, `docs/THRESHOLDS.md`); and whenever a new
judged run exists, for the judged half.

## Steps

1. **One session.** `make gate-local`: the live contract test, a dev run of the generation suite
   x3, then `raglab gate --config config/local-ollama.toml` against the published local baseline,
   in one guarded Ollama session (`docs/LOCAL-MODEL.md`; on AC power, nothing else running).
2. **The line.** The gate prints one line: pass or fail at the baseline's behaviour pass^3 minus
   the margin of THRESHOLDS.md's consistency row, or a refusal (a stale baseline, a fake or
   partial run, no margin, two consistency rows). The pull request quotes it.
3. **The causes.** The run's report carries its causes section; `make causes RUN=<run>` writes the
   derived file for a published run.
4. **The judged half**, when a new judged run exists (`make judge-local RUN=<run>`, a judge
   session of its own): `raglab compare <A> <B>` on the two judged records under one judge, then
   `raglab gate --judged <B> --against <A>`. The gate reads the calibration record the run names
   (or the one that describes its judge): a trusted criterion fails on an interval entirely below
   zero; a reported-only, not-trusted or unnamed criterion is printed and never gates; with no
   record or no trusted criterion it refuses, and the pull request says so.
5. **A stale baseline.** A new baseline is published only in a reviewed pull request, by S4's
   rule: five sessions, the first complete run the baseline, the margin from the four repeats.

## What a production eval-on-change adds (lab practice here)

- A keyed workflow on `push` to same-repo branches touching those paths, inside an Environment
  with required reviewers; fork changes re-pushed by the maintainer; never `pull_request_target`.
- The judged half on every run, with a hosted judge and its calibration record pinned.
- A margin set from many repeats on the runner itself.
