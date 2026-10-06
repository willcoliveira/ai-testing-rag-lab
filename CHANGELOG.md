# Changelog

One line per change, newest first, grouped by release. Each pull request adds its line
(checked in CI; Dependabot is exempt).

## Unreleased (v0.1)

- S1b: ingestion and chunking: the register reader, Markdown, PDF (tables read as rows), HTML and
  OCR (Tesseract) parsers, the section-aware chunker (1,200 characters, one paragraph of overlap,
  deterministic ids), `raglab ingest` and the committed inventory snapshot
  (`make inventory-snapshot`), a separate attack-fixture loader for S7, docs/TEST-PLAN.md part 2
  (one named check per pipeline arrow), one test module per criterion, a parser-library
  architecture rule, a no-network guard for tests, and a pinned Tesseract in pr-fast.
- S1a: requirements (docs/TEST-PLAN.md part 1) and the fictional Halvenroot and Mirrowfen policy
  corpus (21 documents adapted from strongdm/comply, NIST and NCSC excerpts, and three labelled
  attack files), with the planted-feature answer key, the machine-readable register
  (corpus/register.yaml), SOURCES.md and licence notes, a deterministic build of the PDF, HTML
  export and scanned page, a corpus-only privacy allowlist, and tests for the plan, the key, the
  sources, the build and the allowlist scope.
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
