---
stage: S0
nodes: [S0]
---

# S0 ledger: skeleton and hygiene

Plan: [2026-10-05-s0-skeleton.md](2026-10-05-s0-skeleton.md).

## Approval

The user's go, verbatim (2026-10-05): "ok, continue for the commits and branches use semanthic
approach not just the name". AC19 (semantic commits and branches) was added to the plan from it.

## Setup done

- gitleaks 8.30.1 installed with Homebrew (asked first, approved in the go message).
- `willcoliveira/ai-testing-rag-lab` created **private**; bootstrap commit
  `chore: initial commit with licence and readme stub` on `main`; work on `chore/s0-repo-skeleton`.

## Deviations from the plan

- Architecture fixtures are written to a pytest `tmp_path` instead of `tests/fixtures/architecture/`,
  so the planted violations (`import openai` and so on) never sit in the tree where ruff, pyright,
  deptry and semgrep would flag them.
- The workflow rules live in `tests/unit/test_workflow_rules.py` rather than inside
  `test_architecture.py`.
- semgrep and zizmor run through `uvx` at versions pinned in the Makefile, not as project
  dependencies, so their large dependency trees stay out of the lock file and out of pip-audit's
  scope. Dependabot does not update those two pins; they are bumped by hand.
- `tests/unit/test_readme.py` added: the README status diagram must equal diagram 4.

## Developer evidence

(filled in below as each criterion is run)
