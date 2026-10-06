# Changelog

One line per change, newest first, grouped by release. Each pull request adds its line
(checked in CI; Dependabot is exempt).

## Unreleased (v0.1)

- S0: repo skeleton with `make check` and the pr-fast workflow (format, lint, types, deptry,
  vulture, pip-audit, bandit, semgrep, zizmor, gitleaks, privacy, architecture rules, offline
  tests), Conventional Commits and semantic branch checks, the changelog check, Dependabot, the
  architecture progress map and the committed plans. After the judge's review: the pre-commit
  privacy check reads the staged index, and the workflow, conventions, architecture and changelog
  checks close the bypasses the judges found over four rounds (staged index, history and
  pre-push scans, commit identities, tag messages, copies of the real list). After the second review: the staged check never writes to
  the repo (safe in linked worktrees), refuses a staged real list and covers force-added and
  quoted file names, and three false positives are gone. After the third review: the privacy
  check refuses a committed real list in CI too, checks the example list, the checker and
  `uv.lock` with the real list, reads a symlink as its link text and a commit message as prose; a
  history scan checks every commit in a pull request, before each push (a new pre-push hook) and
  before going public; the conventions, architecture and changelog checks close the rest.
