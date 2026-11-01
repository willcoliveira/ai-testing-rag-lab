# Gates

The gate map of the main plan (`docs/plans/2026-10-05-raglab-plan.md`, "Gate map (how-to 08
columns)"), filled in from what exists at S8: one row per gate in how-to 08's seven columns (Gate,
Trigger, Keys, Blocks, Threshold and reason, Owner and runbook, What runs) plus a **Mode**, so
nobody mistakes a local run for an automated one:

- **ci**: runs in GitHub Actions on every pull request and push to `main`
  (`.github/workflows/pr-fast.yml`); nothing else runs in CI until ADR-002's keys exist.
- **local**: run by hand on the maintainer's Mac through the named `make` target, inside one
  guarded model session where a model is needed (`docs/LOCAL-MODEL.md`), and its line is quoted
  in the pull request or the ledger. The lab form of a keyed workflow behind an Environment with
  required reviewers (S10 switches the CI versions on).
- **documented only**: not run in the lab; the row says what production would run.

`tests/unit/test_gates_doc.py` parses this table: the eight columns and a mode on every row, every
`make` target named exists in the Makefile, every runbook named exists, every pytest marker named
is registered, and pr-fast's "What runs" names every `make` step of the workflow, read from the
workflow, so a new CI step without a mention here fails. Every threshold lives in
`docs/THRESHOLDS.md` with its reason (`tests/unit/test_thresholds_cover_the_metrics.py` holds a row
for every metric the published records carry).

## The gates

| Gate | Trigger | Keys | Blocks | Threshold and reason | Owner and runbook | What runs | Mode |
|---|---|---|---|---|---|---|---|
| pr-fast | every pull request, forks included, and every push to `main` | none | yes | THRESHOLDS.md: the retrieval no-regression row (recall@5 on dev at least the baseline's minus one question), the Guards section (every must-block and must-not-block case binary per build), the Performance section (the k6 smoke's median under 40 ms, checks rate 1, no failed request), the dataset check as a hard stop | quality, `runbooks/pr-fast.md` | the `check` job: `make check-dataset`, `make model`, `make format`, `make lint`, `make types`, `make deps`, `make audit`, `make sast`, `make workflows`, `make secrets`, `make privacy`, `make privacy-history` (the pull request's commits), `make architecture`, `make test` (markers `unit`, `contract`, `ingestion`, `retrieval`, `e2e_fake`, `security`, `ocr`; never `live`, `judged`, `guardrails`, `perf` or `flaky`), `make gate`, `make api-smoke`; the `perf` job: `make perf-smoke`; the `conventions` job: the title, the branch name and the CHANGELOG line | ci |
| eval-on-change | a change to the prompt, the generation code, the chunker, the embedder or the model: by hand, before the pull request; the keyed workflow (`push` to same-repo branches touching those paths, inside an Environment with required reviewers, never `pull_request_target`) waits for ADR-002's keys | none locally; a hosted judge would need them | yes, locally: the consistency gate's one line is quoted in the pull request; the judged half gates only on a criterion the calibration record marks trusted (D1 A), by the paired interval, and refuses otherwise | THRESHOLDS.md: the consistency row (margin: 1 case); the judged gate row (an interval entirely below zero on a trusted criterion); until S6's record trusts a criterion, nothing judged gates and `raglab gate --judged` says so | quality, `runbooks/eval.md` | `make gate-local` (the live contract test, a dev run x3, `raglab gate --config config/local-ollama.toml` against the published baseline); when a new judged run exists (`make judge-local RUN=<run>`), `raglab compare <A> <B>` on the two judged records and `raglab gate --judged <B> --against <A>` | local |
| nightly | by hand (`make nightly-local`) until keys exist; cron then | none locally | alerts only: the record's `alert` block and report line, never a failure; published alerts are recomputed at publish time against the index, and a mismatch is refused | THRESHOLDS.md: the drift row (behaviour pass^3 against the previous published nightly of the config, paired by case; the alert fires when the interval lies entirely below zero; the first nightly on golden set v2 is the reference) | quality, `runbooks/nightly.md` | `make nightly-local` (the live contract test, every split x3 under gate nightly, `raglab eval --gate nightly`); the judged alert on the trusted criteria with `make judge-local RUN=<the nightly run>` under gate nightly, by hand; the test split's guard suites, `raglab guard-suites --split test --gate nightly` | local |
| manual | dispatch by hand, on the maintainer's go | none locally | no | — | maintainer | `make attack-local` (the live attack runs, defences off and on), `make guard-suites`, `make replay`, `make position-local`, `make judge-canaries`, `make causes RUN=<run>`, `raglab publish`; S6's calibration re-run (`raglab calibrate`, after S6 merges) and the red team (S7b, after it merges) | local |
| weekly | cron, when keys exist | yes (security: none) | alerts | — | maintainer | the full judged suite x5 (no `make` target yet: one judge session per run, 2 h 20 min 53 s measured by S6 on v2's dev split), the trivy re-scan of the published image (S11) | documented only |
| release | a tag, by hand, at the end of a phase | none locally | yes: the test slice once, the security suite binary, the history scans clean | THRESHOLDS.md: the test split is never a threshold's source; the release notes' release-gate table (`docs/releases/`) | maintainer, `runbooks/release.md` | `make release-local` (the default retrieval configuration on the test split, then one session with the generation suite on the test split x3, under gate release), `make secrets`, `make privacy-history` over the whole history, `raglab publish`; the upgrade replay (`docs/UPGRADES.md`: `make check`, `make gate`, `make replay`, `make guard-suites`); trivy, the SBOM and the deploy approval wait for S10 and S11 | local |
| prod-sample | not run in the lab | — | — | — | — | production samples live traffic and scores it with the same judged criteria; the lab has no traffic (the main plan's path to production) | documented only |

Lab practice: a production system runs eval-on-change, nightly and weekly in CI with keys, inside
Environments with required reviewers, and alerts a channel; here each `local` row is one `make`
target run by hand with its line quoted, and the CI versions are switched on when keys exist.

## Flakes

**A flake** is a test or a gate that fails and passes at the same commit with the same inputs and
no change. **Not a flake**: an environment failure (a slow runner, a package mirror, the Mac asleep,
a model not loaded), which is recorded as such and fixed in the environment; and a real failure,
which is a fix. The policy follows S9's perf rule ("ten report-only runs ... none dropped and none
run again for a better number") and the honest-numbers rule.

**The retry rule (D3 A, the maintainer's answer of 2026-10-31: "No automatic retry; one recorded
re-run by hand").** No test and no job retries itself. A failed CI job or local run may be re-run
once, by hand, and a pass with no change is written in the register below (the test, the run id,
the date, the suspected cause) and reviewed; a second entry for the same test within 30 days
quarantines it. A re-run never replaces a recorded number: a measured result that a re-run
improved keeps its first value, and the re-run is written beside it.

**Quarantine.** A quarantined test carries the `flaky` marker (registered in `pyproject.toml`
under `--strict-markers`), which `make check` and pr-fast never select (`PYTEST_OFFLINE` in the
Makefile excludes it) and `make test-flaky` runs on its own. Every quarantined test has a row in
the register (test id, first seen, the run or session, the suspected cause, the owner, the removal
date at most 30 days after it was first seen); `tests/unit/test_flake_register.py` fails on a test
marked `flaky` without a row, on a row whose test is not marked, on a removal date past or more than
30 days out, and on `flaky` missing from `PYTEST_OFFLINE`'s exclusion.

### Register

Empty at S8: no test is quarantined.

| Test id | First seen | Run or session | Suspected cause | Owner | Removal date |
|---|---|---|---|---|---|

### Seen so far (environment failures, not flakes)

- pr-fast's test step took 346 s on one run and 451 s on another on 2026-10-23 (docs/THRESHOLDS.md,
  Performance): a shared runner's speed, not a test that fails and passes; the perf smoke's margin
  was set from it.
- The S7a judge's session saw "transient 'no verdict' classifier failures ... which succeeded on
  retry" (the S7 ledger): the local model's reply, not a test; the judged record counts an
  unavailable verdict and marks the run partial rather than retrying it.

Lab practice: production would track flake rates per test from CI's history and quarantine
automatically; here the register is a table and the marker a rule.
