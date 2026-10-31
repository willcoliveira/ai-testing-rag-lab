# Runbook: pr-fast (lab)

Owner: quality. The gate is `pr-fast` in `docs/GATES.md`; mode **ci**. Every pull request, forks
included, and every push to `main` run it (`.github/workflows/pr-fast.yml`). This is the lab
version; the last section says what production adds.

## When

On every pull request and push to `main`; by hand before pushing, as `make check` (the same
targets, `/usr/bin/time -p make -k check` in a stage ledger).

## Steps

1. **The dataset hard stop.** `make check-dataset`: every golden file against its ten rules, before
   any model or run. A problem stops the job.
2. **The embedding model.** `make model`: the pinned ONNX files from the cache keyed by revision,
   every sha256 checked; a download only on a cache miss.
3. **Static checks.** `make format`, `make lint`, `make types`, `make deps`, `make audit`,
   `make sast`, `make workflows`, `make secrets`, `make privacy`, `make privacy-history` over the
   pull request's commits, `make architecture`.
4. **Tests, offline.** `make test`: the offline markers only (`PYTEST_OFFLINE` in the Makefile);
   `live`, `judged`, `guardrails`, `perf` and `flaky` never run here.
5. **The retrieval no-regression gate.** `make gate`: a fresh run of the default retrieval
   configuration on the dev split against the published baseline, within one question of its
   recall@5 (`docs/THRESHOLDS.md`).
6. **The API smoke.** `make api-smoke`: `raglab serve` on the fake model, loopback only.
7. **The perf job**, beside `check`: `make perf-smoke`, the k6 smoke on the perf stub, the median
   under its threshold.
8. **The conventions job**: the pull request's title, its branch name and its CHANGELOG line.

## If it fails

- A red `audit`: a new advisory. The skips and their review date are the Makefile's
  (`AUDIT_SKIP`); a dependency pull request takes the fix, never a skip without its reason.
- A red `gate`: a retrieval regression, or a stale baseline (another dataset or config sha256). A
  new baseline is published only in a reviewed pull request.
- A red test: a fix. A pass on a re-run by hand with no change is a flake and goes in the
  register (`docs/GATES.md`, Flakes); never a silent re-run.
- A slow runner: the `check` job has 20 minutes; its time before and after a stage is in the
  stage ledger.

## What a production pr-fast adds (lab practice here)

- The same checks against a managed model endpoint, with keys in an Environment.
- A container image scan (trivy) on every change to the image (S11 brings it to release).
- Flake rates tracked from CI's history, not a register kept by hand.
