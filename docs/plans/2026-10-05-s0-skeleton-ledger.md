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

## Judge round 2 and fix round 2

Judge round 2 (2026-10-05) found five defects and three low false positives. N1, N2, N3 and N5
came from fix round 1; N4 was already in the vendored checker. N1 happened for real: a commit made
from a linked worktree of this repo wrote `core.bare=true` to the shared `.git/config`, and the
user restored it. Fix round 2 (Opus 5.5, 2026-10-05) is the last fix round the stage rules allow.
Each test below reproduces the judge's case and fails on the pre-round code.

| # | Severity | Finding | Fix | Test | Commit |
|---|---|---|---|---|---|
| N1 | high | `check-staged-privacy.sh` ran `git init` in its temp copy; in a linked worktree git exports an absolute `GIT_DIR` (`.git/worktrees/<name>`) to hooks, so the init rewrote the shared `.git/config` | the script runs only read-only git commands; before it checks the copy it clears every repo-local `GIT_*` variable (`git rev-parse --local-env-vars`) and sets `GIT_CEILING_DIRECTORIES` to the temp dir | `test_privacy_check.py::test_commit_from_a_linked_worktree_leaves_the_main_repo_intact`: a throwaway repo and linked worktree under `tmp_path`, commits through the real hook's line; `core.bare` is not true, `git status` works, and a staged leak in the worktree is still blocked | `50f1dd8` |
| N2 | high | `git add -f privacy/forbidden-strings.txt` passed the hook (the copy never has the list tracked) | refused in the real repo before the copy: exit 2, `REFUSING`, in CI mode too | `::test_staged_check_refuses_a_staged_real_list[False\|True]` | `50f1dd8` |
| N3 | medium | a force-added ignored file (`.env`) was not scanned: the exported `.gitignore` hid it | the checker reads the list of index entries (`ls-files -z --cached`) through a new `--files-from` option; no ignore rules apply | `::test_staged_check_scans_force_added_ignored_files` | `50f1dd8` |
| N4 | medium | names git C-quotes (`café.md`, `q"uote.md`) were never scanned: `existsSync("caf\303\251.md")` failed silently | `git -c core.quotePath=false ls-files -z`, split on NUL; git's stderr silent; the vendored header lists the change | `::test_files_with_quoted_names_are_scanned` (untracked, tracked and staged) | `12885d8` |
| N5 | low | a token wrapped at a CRLF in prose was not joined: the paragraph split read one CRLF as a blank line | CRLF and CR made LF before the split | `::test_line_join_view_handles_crlf` (CRLF, CR and LF hit; a blank CRLF line still separates paragraphs) | `4d3c83b` |
| (a) | low, false positive | job-level `permissions: {}` failed the workflow rule test | a job may set `{}`, `none` scopes or `contents: read`; `read-all`, `write-all` and any other read scope still fail | `test_workflow_rules.py::test_job_may_narrow_permissions_below_contents_read` | `c317873` |
| (b) | low, false positive | `Merge commit '<sha>' into <branch>` (what `git merge <sha>` writes) was rejected by the commit-msg hook | accepted in commit messages, a hex id only between the quotes; PR titles still reject it | `test_conventions.py::test_good_headers_pass`, `test_bad_headers_fail`, `test_pr_titles_must_be_conventional_commits`, `test_message_uses_first_non_comment_line` | `872c3e2` |
| (c) | low, false positive | a file's own `def import_module(...)` called with a variable was reported as a computed dynamic import | `import_module` counts only when it is importlib's: imported from importlib (by name, alias or `*`), called on a name bound to the importlib module (`import importlib`, `as il`, `import importlib.util`), or bound to either by a simple assignment; `__import__` always counts | `test_architecture.py::test_a_local_function_named_import_module_is_not_an_importer`, plus new cases in `test_vendor_sdk_outside_adapters_is_reported` | `7824f99` |

Found by the developer during the round, outside the judge's list. Each has its own commit, so a
reviewer can drop it:

| # | Severity | Finding | Fix | Test | Commit |
|---|---|---|---|---|---|
| D1 | medium | the path exemption `^privacy/forbidden-strings` skipped any file with that prefix, so an editor backup of the real list (`forbidden-strings.txt~`, `.bak`), which `.gitignore` does not match, could be committed unchecked | only `forbidden-strings.txt` and `forbidden-strings.example.txt` are exempt | `test_privacy_check.py::test_only_the_two_list_files_are_exempt` | `d188f81` |
| D2 | medium | a linked worktree has no copy of the gitignored real list, so its hooks and `make privacy` ran with the example list only (seen in the N1 replay: 5 rules) | with no list of its own, the checker and the staged check use the main worktree's (beside the common `.git`); CI unchanged | `::test_linked_worktree_uses_the_main_worktree_list` | `44f4a3e` |
| D3 | low, test quality | the round-1 workflow bypass test could not fail for the right reason: `yaml.safe_dump` drops the version comments, so every variant also failed the comment rule | the rules are a `check_workflow(data, text)` function; variants are checked against the real file's text with `pytest.raises(match=...)` naming the rule | `test_workflow_rules.py::test_rules_reject_the_judge_bypasses` | `c317873` |

Design choice: the round-2 brief suggested letting the checker walk the exported copy. A walk skips
`node_modules/`, follows a staged symlink to a directory out of the copy, and crashes on a dangling
symlink (`statSync` throws), so the checker reads the list of index entries instead
(`test_staged_check_survives_symlinks` guards this). The staged check runs the working tree's
checker against the copy, as the hook script itself comes from the working tree.

Evidence:

- **Fails without the fix:** the final tests on the pre-round code (`405bd6e` in a scratch copy,
  with the old permission assertion swapped in for (a)) give 22 failures, exactly the new cases.
- **With the fixes:** `make check` exits 0; 120 tests pass.
- **Hand replays** with the real `.githooks/pre-commit` and `commit-msg` in a scratch repo built
  from the working tree, with a fake local list (never the real one):
  - N1: commit from a linked worktree exits 0; the main repo keeps `core.bare=false` and
    `git status` works. An ARN-shaped string staged in the worktree is blocked, HEAD unchanged.
  - N2: `git add -f privacy/forbidden-strings.txt`, then commit: exit 1 with `REFUSING`
    (the staged script exits 2); HEAD unchanged.
  - N3: a force-added `.env` holding an ARN-shaped string is blocked.
  - N4: `café.md` and `q"uote.md` are hit by `make privacy` and by the staged check.
  - N5: a fake name wrapped at a CRLF is hit.
  - D2: from the linked worktree both hooks load 6 rules and block a commit message and a staged
    file that name the fake client.
- The real repo's `core.bare` stayed `false` through all round-2 commits, each made through the
  hooks from the main checkout.

Follow-ups, not part of this repo's S0:

- **Handbook** (`willcoliveira/ai-testing-handbook`, `scripts/check-forbidden.mjs`, as vendored at
  `dfff1aa`): N4 (C-quoted names), #8 (no line-break view; port it with the N5 CRLF fix) and D1
  (prefix exemption) affect the original too. D2 applies if the handbook is worked on from linked
  worktrees.
- **Known gaps, pre-existing:** file names themselves are not checked (a name in a path passes);
  a symlink is read through to its target, not checked as the link text git commits. Also
  `getattr`/`exec` stay out of reach of the static architecture check, and the `uvx` tool
  environments are unlocked (both recorded in round 1).
