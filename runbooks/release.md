# Runbook: release (lab)

Owner: the maintainer. The gate is `release` in the main plan's gate table
(`docs/plans/2026-10-05-raglab-plan.md`, "Gates"). This is the lab version of a release, as v0.1.0
ran it; the last section says what a production release adds.

## When

At the end of a phase, after its last stage's pull request is merged: v0.1 after S4, then v0.2 and
v0.3 as the main plan's phases close.

## Steps

1. **Plan.** A short release plan in `docs/plans/` with numbered criteria, approved by the
   maintainer before anything runs; the go is quoted verbatim in it.
2. **Branch.** `chore/release-vX.Y.Z` from `main`.
3. **Version.** Set it in `pyproject.toml`, then `uv lock` and `uv lock --check`.
4. **Freeze.** Commit everything but the runs and the notes; `make check` green; the tree clean.
5. **The test slice, once.** `make release-local`: the default retrieval configuration on the test
   split, then one guarded Ollama session (the live contract test, the generation suite on the test
   split x3), both under gate `release`. Ollama runs only inside that session (`docs/LOCAL-MODEL.md`);
   afterwards `make ollama-status` shows no pid, the port closed and nothing loaded.
6. **Publish.** `uv run raglab publish runs/tmp/<run>` for each run. Nobody edits a record. If
   publish refuses a run, the run stays in `runs/tmp/`, the release stops and the maintainer
   decides.
7. **History scans.** `make secrets` (gitleaks over the history) and
   `make privacy-history RANGE=--all` with the maintainer's real list: no leaks, 0 hits.
8. **Release notes.** `docs/releases/vX.Y.Z.md` covers:
   - what the release is and how to run it;
   - every published run with its provenance;
   - the test slice's numbers, copied from the records;
   - the release-gate table, each row run, or not built yet with the stage that builds it;
   - the known limits.
9. **CHANGELOG.** The release's section and its line.
10. **Check and merge.** The criteria judge recomputes the numbers and re-runs the scans. Then the
    pull request (`chore(release): vX.Y.Z`) and pr-fast green. The maintainer merges with a merge
    commit, so every published run's `git_sha` stays reachable.
11. **Tag, by hand.** The maintainer runs `git tag -a vX.Y.Z -m "vX.Y.Z" <merge commit>`, then
    `git push origin vX.Y.Z`. A GitHub release made from the notes is optional.

## The test slice

The test split is held out: `raglab eval` and `raglab publish` refuse it under any gate but
`nightly` and `release` (`datasets/DATASHEET.md`, Split). No threshold is set from it and nothing is
tuned on it; at a release it is run once and reported.

## What a production release adds (lab practice here)

- The tag is cut by CI with keys, inside an Environment with required reviewers.
- The security suite (S7) and the red team on the real model block the release.
- trivy and an SBOM come from S11; artefacts are signed.
- An upgrade replay (S8) and a deploy approval (S10).
- Thresholds on the test slice are agreed before the release, not read from it.
