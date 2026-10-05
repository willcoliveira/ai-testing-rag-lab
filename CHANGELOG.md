# Changelog

One line per change, newest first, grouped by release. Each pull request adds its line
(checked in CI; Dependabot is exempt).

## Unreleased (v0.1)

- S0: repo skeleton with `make check` and the pr-fast workflow (format, lint, types, deptry,
  vulture, pip-audit, bandit, semgrep, zizmor, gitleaks, privacy, architecture rules, offline
  tests), Conventional Commits and semantic branch checks, the changelog check, Dependabot, the
  architecture progress map and the committed plans. After the judge's review: the pre-commit
  privacy check reads the staged index, and the workflow, conventions, architecture and changelog
  checks close the bypasses it found.
