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

## Developer evidence (Opus 5.5, 2026-10-05)

| # | Result | Evidence |
|---|---|---|
| AC1 | met | clean clone of `chore/s0-repo-skeleton`, `uv sync && make check` exit 0; the clone has only the example list (5 rules), so the real list is not committed |
| AC2 | met | `uv run python -m raglab --version` prints `raglab 0.0.1`; `test_version.py` passes |
| AC3 | met | **break:** `import requests` appended to `core/__init__.py`, `make architecture` exits 2 with `core/__init__.py:2: core may import only the standard library and raglab.core, not requests`; restored |
| AC4 | met | **break:** `import openai` in `__main__.py`, `make architecture` exits 2 with `__main__.py:19: vendor SDK openai is imported outside raglab.adapters`; `test_architecture.py` covers `from anthropic import Anthropic`, `anthropic.Anthropic()`, `importlib.import_module('qdrant_client')`, `__import__('boto3')`, and the same imports inside adapters passing |
| AC5 | met | `test_privacy_check.py::test_refuses_when_real_list_is_tracked` exits 2 with "REFUSING" |
| AC6 | met | **break:** a file with a 12-digit account-id shape, `make privacy` exits 2 (make wraps exit 1); a semantic commit message holding the same shape is rejected by the commit-msg hook |
| AC7 | met | **break:** a generated GitHub-token-shaped string in an untracked file, `make secrets` fails; staged, the pre-commit hook blocks the commit; removed |
| AC8 | met | **break:** a copy of pr-fast.yml with `pull_request_target` and `actions/checkout@v4`, zizmor exits 14 reporting `dangerous-triggers` and `unpinned-uses` |
| AC9 | met | **break:** one `timeout-minutes` removed, `test_workflow_rules.py` fails with `job conventions has no timeout-minutes`; restored (first attempt used a GNU-only sed form that BSD sed ignored, so it changed nothing; redone with Python) |
| AC10 | needs CI | — |
| AC11 | unit met; real PR needs CI | `test_changelog_check.py`: no line fails, a line passes, a blank line does not count, `dependabot[bot]` exempt |
| AC12 | file met; GitHub acceptance needs CI | `test_workflow_rules.py::test_dependabot_covers_every_ecosystem_monthly`; zizmor's `dependabot-cooldown` finding fixed with a 7-day cooldown |
| AC13 | met | **break:** `nodes: [S0, S99]` in the S0 plan, `test_diagram.py` fails; restored. S0 is `wip` until this PR is ready, then `done` |
| AC14 | met | main plan committed without the Background client lines; `git grep -i -w` for the client name returns 0 hits (the 4 substring hits are "trustworthy" in the privacy test); `make privacy` passes with the local real list (42 rules) |
| AC15 | met | README, LICENSE, CONTRIBUTING, SECURITY, CHANGELOG, CLAUDE.md and `.env.example` present |
| AC16 | met | `gh repo view --json visibility` returns `PRIVATE`; `main` holds only the bootstrap commit |
| AC17 | met | `docs/GO-PUBLIC.md` |
| AC18 | met | `git log --format=%B` contains no Co-Authored-By or "Generated with" lines |
| AC19 | met | **break:** `git commit -m "update stuff"` rejected by the commit-msg hook; the six S0 commits went through the hook in Conventional Commits format; `test_conventions.py` covers messages, titles and branches |

Other findings while building:
- bandit flagged the `git` subprocess in `check_changelog.py` (low severity); it is marked
  `# nosec` with the reason on the line above (bandit reads any words after `nosec` as test ids).
- zizmor reports 2 suppressed findings at its default persona; the judge should look at what they are.

## Judge round 1 (Fable 5.1, 2026-10-05)

Verdict: 16 of 19 met, 3 need CI (AC10, AC11 on the real PR, AC12), none not met. Bypasses found,
all fixed in fix round 1, each with a test that reproduces the judge's case:

| # | Severity | Finding | Fix |
|---|---|---|---|
| 1 | medium | pre-commit checked the working tree, so a string staged then cleaned on disk was committed | `scripts/check-staged-privacy.sh` exports the index and checks that; replayed against the real hook: commit blocked, HEAD unchanged |
| 2 | medium | a third-party reusable workflow (job-level `uses`) passed every gate | job-level `uses` must be local (`./`) |
| 3 | low-medium | `.yaml` workflows escaped the rule test | both extensions globbed |
| 4 | low | job-level `permissions: write-all` passed the test (zizmor caught it) | job permissions may only be `contents: read`; exceptions must be added to the test by review |
| 5 | low | whitespace added to an existing CHANGELOG line satisfied the check | added lines that match a removed line once stripped do not count |
| 6 | low | `Merge branch whatever` / `Revert "anything` passed as prefixes | Git subjects matched in full, a revert's inner subject must itself conform; PR titles may not use them; `fixup!`/`squash!`/`amend!` allowed in commits only, around a valid subject |
| 7 | low | aliased `import_module`, computed module names | aliases tracked; any dynamic import with a computed name outside adapters is a violation; `from ... import x` now names `...x` (getattr/exec stay out of reach of a static check, bandit flags exec/eval) |
| 8 | low | a token split at a line break was missed | prose files (md, txt, rst, html, outside `privacy/`) get a view with line breaks removed inside a paragraph; code files are left out because joining them glued decorators into email-shaped strings (seen and fixed during the round) |
| 9 | info | missing `concurrency` raised KeyError; jobs had no names (zizmor's 2 suppressed `anonymous-definition`) | `.get()`; jobs named `check` and `conventions` (ids unchanged for branch protection) |

Also from the security review: hooks now use `uv run --locked`. Not changed, recorded as known
gaps: `uvx` runs semgrep and zizmor at pinned versions but resolves their dependencies unlocked on
each run, and semgrep's `p/python` rules come from the registry (network). Follow-up candidate:
locked tool environments.

Developer slip during the round, recorded: a first replay of finding 1 used `git stash`, which
also stashed the new hook, so it ran against the old hook and a local probe commit (a fake test
string) landed on the branch. It was removed with `git reset --soft HEAD~1` before anything was
pushed; the replay was then redone with the fixes committed and was blocked.
