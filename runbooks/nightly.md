# Runbook: nightly (lab)

Owner: quality. The gate is `nightly` in `docs/GATES.md`; mode **local** until ADR-002's keys
exist. It alerts and never blocks. This is the lab version; the last section says what production
adds.

## When

By hand, on the maintainer's go, with the Mac free; cron when keys exist. The first nightly on
golden set v2 is the reference: no published nightly on v2 exists at S8.

## Steps

1. **One session.** `make nightly-local`: the live contract test, then every retrieval question
   and behaviour case of every split (dev and test) x3 under gate nightly
   (`raglab eval --suite generation --config config/local-ollama-nightly.toml --gate nightly`). The
   test split runs only here and at a release.
2. **The drift alert.** The run's manifest carries an `alert` block and its report a line: the
   previous published nightly of the same config it was compared with (paired by case), behaviour
   pass^3's B minus A with its paired bootstrap interval, the flipped cases, and whether it fired
   (an interval entirely below zero). With no previous nightly the block says the run is the
   reference. The command exits as it would without the alert.
3. **Publish.** `raglab publish runs/tmp/<run>`: the nightly gate may hold the test cases. The
   next nightly compares with it.
4. **The judged alert**, by hand: `make judge-local RUN=<the nightly run>` under gate nightly
   writes the judged alert on the criteria the calibration record marks trusted, against the
   previous published nightly judged record under one judge; when it fires it names S6's
   recalibration trigger (a drift on a judged pass rate makes the calibration record history for
   the judge it no longer describes). With no record or no trusted criterion the block says no
   judged alert is read.
5. **The test split's guards.** `raglab guard-suites --split test --gate nightly`.
6. **If it fired.** An alert is a reason to look, not a failure: the flipped cases and the causes
   section of the record say where; a fix comes through eval-on-change.

## What a production nightly adds (lab practice here)

- Cron, keys, an alert channel, and the alert's history kept beside the records.
- The 20-case regression slice x3 of the main plan's map on the real model endpoint; here the
  whole golden set runs, since one session covers it.
