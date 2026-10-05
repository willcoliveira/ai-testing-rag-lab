# Working rules for this repo

These apply to every session and every account working here.

- **Plans first.** Each stage has a plan in `docs/plans/` with numbered acceptance criteria. The
  user approves the plan before code; their go message is quoted verbatim in the plan or ledger.
- **Stage loop.** Planner writes criteria; developer builds and records evidence in the stage
  ledger; an independent judge (a different model, separate context) re-runs the evidence and
  tries to break each gate, then restores it; at most two fix rounds; the PR body is the stage
  report (n of m met, what needs CI, what was cut).
- **Pull requests only.** Never push to `main`. The user reviews and merges by hand. No auto-merge.
- **Conventional Commits and semantic branches** (see CONTRIBUTING.md). The hooks and CI check them.
- **No AI attribution** in commits, PR bodies or files: no Co-Authored-By trailers, no "Generated
  with" lines.
- **Isolation rule.** Patterns from earlier production work are re-implemented, never ported. Never
  open, read or copy any other codebase into this one, and never name past clients or employers.
  `make privacy` and the commit-msg hook enforce the names on a maintainer's machine.
- **Honest numbers.** A result is published only from a real run with its provenance (fake, local,
  hosted). Never write a number that a run did not produce.
- **Keys** live in a local `.env` (gitignored) or GitHub Environment secrets. Never in the repo.
- Run `make check` before pushing; CI runs the same.
