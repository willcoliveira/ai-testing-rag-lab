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

## Judge round 3 and fix round 3

Judge round 3 (Fable 5.1, 2026-10-05) confirmed ten defects at `ee3546a`, each reproduced
independently. The plan allows two fix rounds; the user approved a third. Their answer, verbatim:
"Full round 3" (fix all ten, full three-judge panel). Fix round 3: Opus 5.5, 2026-10-05. Below,
D1 to D10 are this round's findings (not the developer extras of round 2).

| # | Severity | Finding | Fix or limit | Test | Commit |
|---|---|---|---|---|---|
| D1 | medium | in CI the checker never refused or scanned a committed real list (refusal skipped when CI was set, the path exempt, gitleaks allowlisting it), so a list committed with `--no-verify` or from a clone without hooks passed pr-fast | fixed: the checker refuses (exit 2) whenever the real list, or any other `privacy/forbidden-strings*` name but the example list, in any case, is in the index, in every mode, CI included. The staged check passes its index entries to the checker, which applies the same rule. gitleaks keeps its path allowlist, for the untracked local list `gitleaks dir` reads | `test_privacy_check.py::test_a_committed_real_list_is_refused_in_every_mode` (exact name, a `.bak` copy, an upper-case name; local and `CI=1`; tree, `--file` and staged modes); `::test_only_the_two_list_files_are_exempt` now expects a staged backup to be refused | `ecf61e3` |
| D2 | medium | the example list, the checker and `uv.lock` were exempt by path, so real names pasted into them (the copy step run backwards, say) were committed unscanned | fixed: only the real list is skipped. The three files are exempt from the example shapes only and checked with the real list's rules; the example list is also read as the text its regexes match. The example list may hold only comments, `<placeholders>` (at least one) and `/regex/` lines, in every mode; locally, a line it shares with the real list fails. The offending line is not echoed. Two example ids in the checker's comments that a real rule matched were reworded | `::test_a_plain_line_in_the_example_list_fails_in_every_mode`, `::test_the_copy_step_run_backwards_is_caught` (local and CI), `::test_a_real_name_written_as_a_regex_in_the_example_list_is_found`, `::test_the_checker_and_the_lock_file_are_checked_with_the_real_list`; expected pass: `::test_the_example_shapes_still_do_not_trip_the_files_that_state_them` | `69712ce` |
| D3 | medium | the go-public scan covered HEAD's files and commit messages only; hooks are opt-in per clone and there was no pre-push hook, so a string committed without hooks and removed later survived in history unseen | fixed: `check-forbidden.mjs --history <revisions>` checks every commit message (as prose) and every added line per file (a merge counts only lines new to every parent; a committed copy of the real list is reported without its lines). `make privacy-history RANGE=...` (default `--all`); `.githooks/pre-push` runs it on the commits being pushed; pr-fast on `base..head` of a PR with the example list; GO-PUBLIC step 1 over `--all` with the real list. README, CONTRIBUTING and CLAUDE.md say `make hooks` is required in every clone. Reviewed false positives go in `privacy/history-exceptions.txt` | `::test_history_finds_a_string_committed_and_removed_later`, `::test_history_checks_commit_messages_as_prose`, `::test_history_uses_the_real_list_locally`, `::test_history_reports_a_real_list_committed_and_removed`, `::test_a_history_exception_covers_one_line_of_one_commit`, `::test_history_accepts_revisions_only`, `::test_pre_push_hook_blocks_a_leak_removed_before_the_push` (the real hook, a local bare remote); `test_workflow_rules.py::test_pr_fast_checks_the_commits_of_a_pr`; `test_repo_docs.py` (hooks required, pre-push installed, GO-PUBLIC step 1) | `6c684a4`, `d4c19d0`, `ff2ea02`, `f877306` |
| D4 | low | the commit-msg hook rejected two subjects Git writes itself: `Reapply "<subject>"` and the octopus merge `Merge branches 'a', 'b' and 'c'` | fixed: merge subjects follow git's fmt-merge-msg grammar in full (groups of branches, remote-tracking branches, tags and commits; sources joined by `; `; `of`, `into`); `Reapply` is handled like `Revert`, so its inner subject must conform; PR titles reject both. A ref name in a merge subject may no longer hold whitespace, so `Merge branch 'anything i like'` now fails | `test_conventions.py::test_good_headers_pass`, `::test_bad_headers_fail`, `::test_pr_titles_must_be_conventional_commits`; the accepted forms were checked against subjects Git 2.54 wrote in a scratch repo (octopus, branches and a tag, revert, reapply) | `209fd31` |
| D5 | low | importlib bound by `__import__('importlib')`, by tuple unpacking or through `sys.modules['importlib']` was no longer an importer | fixed: a run-time import is found by the call: any attribute call named `import_module` or `__import__`, `getattr(<x>, 'import_module')`, and a bare `import_module` unless the file defines a function of that name; aliases follow simple, tuple and `:=` assignments. Cost: a method of that name called with a computed name outside adapters is reported (two round-2 test cases moved to a test that records this) | `test_architecture.py::test_vendor_sdk_outside_adapters_is_reported` (eight new cases), `::test_any_import_module_attribute_call_is_an_importer`; the round-2 fix holds: `::test_a_local_function_named_import_module_is_not_an_importer` | `fcf13a4` |
| D6 | low | `pkgutil.resolve_name`, `importlib.util.find_spec` (then `module_from_spec`, `exec_module`) and `sys.modules['openai']` passed the vendor rule | fixed: `find_spec`, `resolve_name` and `run_module` are importers, with `pkg.mod:obj` names and relative names against a literal `package` resolved; `sys.modules[...]` and its `get`/`pop`/`setdefault` count when sys is bound by an import, an assignment or a run-time import. A computed name through any of them is reported outside adapters; `__name__` and `__package__` are this module. A plain string (`provider = "openai"`, a config dict) is never reported | `::test_vendor_sdk_outside_adapters_is_reported` (17 new cases), `::test_run_time_import_in_core_must_name_the_stdlib`; expected pass: `::test_data_and_this_module_are_not_imports` | `3a3525c` |
| D7 | low | a symlink whose link text held a forbidden string was committed unscanned (a dangling one was skipped), and a link to an outside file was read through | fixed: tree entries are read with lstat, and a symlink is checked as its link text (what git stores for mode 120000); `--dir` walks no longer follow links; `--file` still follows (`/dev/stdin`) | `::test_a_symlink_is_checked_as_its_link_text` (untracked, tracked, staged), `::test_a_symlink_to_an_outside_file_is_not_read_through`, `::test_dir_mode_does_not_follow_a_symlink_loop` | `fa86c30` |
| D8 | low | `--file` input had no line-join view, so a token wrapped at a line break in a commit message was missed | fixed: `--file` input is prose. None of the repo's 26 commit messages at the time tripped it | `::test_a_token_wrapped_in_a_commit_message_is_found` (an example shape in CI mode, a real-list name locally) | `74d8086` |
| D9 | low | only leading and trailing whitespace was normalised, so an internal extra space in an existing CHANGELOG line counted as a new entry | fixed: added and removed lines compared with whitespace runs collapsed | `test_changelog_check.py::test_whitespace_inside_an_existing_line_does_not_count` (double space, tab, after the dash; trailing whitespace is the expected pass that already worked) | `5d98ecc` |
| D10 | low | CLAUDE.md lacked the planned rule "label lab practice as lab" (AC15) | fixed: the bullet is in, and the privacy rule says `make hooks` is required in every clone | `test_repo_docs.py::test_claude_md_carries_the_planned_rules` (every rule the plan lists) | `0db94ec` |

Evidence:

- **Fails without the fix:** this round's test files copied into a scratch clone at `ee3546a`
  give 75 failures out of 215 tests; the 140 that pass are the earlier tests and the expected
  passes. Per item: D1 7, D2 8, D3 16, D4 8, D5 8, D6 19, D7 3, D8 2, D9 3, D10 1. Every item
  has at least one failing test.
- **With the fixes:** `make check` exits 0 with 215 tests; zizmor reports no findings; `make
  privacy` with the real list gives 0 hits across 50 files.
- **This branch's history:** `make privacy-history` over `--all` with the real list gives 0 hits
  in 37 commits, with the two reviewed exceptions below. The range the pre-push hook checks on this
  branch's first push (`HEAD --not --remotes=origin`) and the PR range in CI mode both give 0 hits.
- **Hand replays** with the real `.githooks/` (pre-commit, commit-msg, pre-push), in a throwaway
  repo under the scratchpad built from `git archive HEAD`, with a fake local list and a local bare
  remote:
  - D1: `git add -f` of the list, then commit: blocked with `REFUSING`. Committed with
    `--no-verify`: the `CI=1` checker exits 2, the push is blocked by pre-push and the remote is
    unchanged. Untracked again in a later commit: the CI-mode tree scan passes and the CI-mode
    history scan of the range reports the committed copy.
  - D2: the copy step run backwards, then commit: blocked (a line of the real list, no
    placeholder left, the name itself). Committed with `--no-verify`: the CI-mode check fails (no
    placeholder left). A fake name in the checker's comments, then in `uv.lock`: each commit
    blocked.
  - D3: a fake name committed and removed without hooks: the tree scan gives 0 hits,
    `make privacy-history` 1, the push is blocked and the remote is unchanged. An ARN shape
    committed and removed: the CI-mode history scan of the PR range finds it.
  - D7: a symlink whose link text holds an ARN shape: commit blocked, and found by the CI-mode
    tree scan. A symlink to an outside file holding a fake name: commit and push allowed.
- The main repo's `core.bare` stayed `false`; every commit of the round went through the hooks.

Design choices:

- D1 goes beyond the brief: any `privacy/forbidden-strings*` name but the example list, in any
  case, is refused while in the index. A backup or a case variant of the real list is just as
  private, and in CI it would otherwise be scanned with the example list only.
- D2: a rule against plain lines cannot catch a reversed copy of a real list written as regex
  lines, so the example list must also keep at least one `<placeholder>` (it is the template for
  the real list). Locally, a line shared with the real list and the regex-as-text view catch a
  real name written as a regex.
- D3: the history scan is a mode of the checker, so it shares the file scan's rules, views and
  per-path policy. It takes git log revisions; only revisions and the ref-selecting options
  (`--all`, `--not`, `--branches`, `--tags`, `--remotes`) are accepted, so no other git option
  reaches git log.
- **History exceptions.** Over `--all` with the real list, the new scan found 2 hits in this
  branch: the vendoring commit `3f29c73` put two made-up example ids in a checker comment, of a
  shape a rule of the real list forbids (the comment was reworded under D2). Rewriting 28 unpushed
  commits, and with them every commit id this ledger cites, is the user's decision, so the two
  lines are listed in `privacy/history-exceptions.txt` with the reason. An entry is a full commit
  id, a path and a line; a commit cannot change without changing its id, so an entry covers one
  line of one commit. **User decision before the first push:** keep the two exceptions, or rewrite
  the branch and empty the file.

Remaining known limits, with the reason:

- CI has only the example list, so a real name anywhere (a regex line of the example list, the
  checker, `uv.lock`, any file or commit) passes CI and is caught only where the hooks or
  `make check` run with the real list. Inherent: the real list never leaves the maintainer's
  machine.
- Hooks can be skipped (`--no-verify`, a clone without `make hooks`); CI then re-checks the PR's
  files and commits with the example list only. Deliberate evasion by the owner is out of scope.
- The history scan does not cover annotated tag messages, notes, ref names or file names (file
  names were already a gap); GO-PUBLIC step 1 says to check tag messages with `--file`. CI checks
  a PR's commits, not a direct push to `main` (branch protection, GO-PUBLIC step 7).
- A PR can weaken the example list, the allowlist or the history exceptions in the same change;
  only a reviewer reading the diff sees it. Out of reach of a static check.
- Architecture: names reached through `vars()`, `__dict__` or a non-literal `getattr`, loading by
  file path (`spec_from_file_location`, `SourceFileLoader`), `zipimport`, and `exec` or `eval`
  (bandit flags those two) stay out of reach of a static check, and bindings are not told apart by
  scope. A method named `import_module`, `find_spec`, `resolve_name` or `run_module` called with
  a computed name outside adapters is reported by design.
- An example-shape hit prints the matched text, so in CI it lands in the job log, which is public
  once the repo is. Pre-existing; follow-up candidate: print only the location in CI.
- Unchanged from round 1: the `uvx` tool environments are unlocked and semgrep's `p/python` rules
  come from the registry.
- Closed from round 2's known gaps: a symlink is no longer read through to its target (D7).

Handbook follow-ups (`willcoliveira/ai-testing-handbook`, `scripts/check-forbidden.mjs` as
vendored at `dfff1aa`). The handbook was not opened; each item is inferred from the vendored copy
and its list of local changes:

- From round 2: N4 (C-quoted names), #8 with N5 (no line-break view; CRLF), the round-2 extra D1
  (prefix exemption), and the round-2 extra D2 if the handbook is worked on from linked worktrees.
- From round 3: D1 (the refusal is skipped when CI is set); D2 (the checker and the package file
  exempt by path; the checker's comment holds the two example ids that a rule of this repo's real
  list matches, and that list was built from the handbook's, so the handbook's own checker likely
  carries a hit its path exemption hides); D7 (symlinks read through); D8 (`--file` input not read
  as prose, once the line-break view is ported); D3 if the handbook has no history scan or pre-push
  hook.

## Judge round 4 and the E fixes (2026-10-06)

Judge round 4 (three Fable judges in clones, workflow wf_301194ae-d06) re-ran AC1-AC19 and every
finding from rounds 1-3: all met or fixed, `make check` clean in each clone, the main checkout
intact. Two judges stalled after a usage-limit pause and were retried by the workflow; the safety
classifier timed out once while the security judge ran, so the main checkout was checked by hand
afterwards (core.bare false, tree clean, no worktrees). Six new defects were reproduced
independently (none rejected, none high). The user's go to fix them: "continue" (after the choice
between fixing E1-E6 and shipping with them as follow-ups). Fixed by the main session directly,
as they were small:

| # | Severity | Finding | Fix | Test |
|---|---|---|---|---|
| E1 | medium | a \b-anchored real rule does not match its own text, and the "line of the real list" check ran on the example list only, so a copy of the list elsewhere or a rule pasted into a note passed | in every mode, a /regex/ line equal to a real-list line is reported without its text; any line with escapes is also read with the escapes dropped, against the real rules only; `**/forbidden-strings.txt` and editor backups in privacy/ are gitignored | `test_a_copy_of_the_real_list_at_another_path_is_found` (tree, staged, history), `test_a_real_rule_pasted_into_a_note_is_found`; expected pass: `test_escapes_in_code_do_not_trip_the_example_shapes` |
| E2 | low | a CI variable left in the shell turned the real list off in the hooks | every hook runs `unset CI` before the checker | `test_pre_push_uses_the_real_list_even_with_ci_set`, `test_every_privacy_hook_unsets_ci` |
| E3 | medium | author and committer identities were never checked | `--history` checks both identities with every rule except the generic email shape | `test_history_checks_author_and_committer` (a name locally, an internal domain in CI) |
| E4 | low | the pre-push checked commits only; an annotated tag's message was pushed | pre-push checks an annotated tag's message (without the object header) as prose | `test_pre_push_checks_an_annotated_tag_message` (real hook, local bare remote) |
| E5 | low | Git's "Merge branch 'x' (early part)" was rejected | accepted for branch items in commit messages; PR titles still reject merges | `test_good_headers_pass` / `test_bad_headers_fail` cases |
| E6 | low | major action updates were grouped with minor and patch, against the file's header | `update-types: ["minor", "patch"]` on the github-actions group | `test_dependabot_covers_every_ecosystem_monthly` |

Fails without the fix: the new tests run against f86dad1 give 14 failures, all of them the new
cases (including the backup-file test, whose expectation changed with the new ignore rule).
`make check` exit 0, 230 tests.

## E-fix check and the F fixes (2026-10-06)

The E1-E6 check (one Fable judge, workflow wf_ba297a8d-fff) found every E fix holding, `make check`
clean (230 tests), no regressions (ordinary code, GitHub noreply addresses, lightweight and signed
tags, this branch's own CI history range), and four new low defects, each reproduced independently.
The user's go: "Fix all four, then PR".

| # | Finding | Fix | Test |
|---|---|---|---|
| F1 | a copy of the list printed fragments of itself through the across-lines pass and its comment line | the list's long comment lines count as list lines; once a file holds a list line, the across-lines views are skipped for it | `test_a_copy_of_the_list_prints_none_of_it` |
| F2 | pre-push checked a tag's message, not its tagger | new `--identity <file>` mode (identity rules: every rule but the email shape); pre-push feeds it the tagger's name and address | `test_pre_push_checks_the_tagger`, `test_identity_mode_skips_the_email_shape_only` |
| F3 | rules with `?`, `{n}` or digit classes were missed when written another way (flag dropped, in code) | list lines compared without flags; the escapes view drops quantifiers and reads `\d{m}` as m zeros. Measured against the real list (counts only): 37 of 37 rules caught verbatim, without the flag and inside `re.compile(r"...")` | `test_a_rule_written_another_way_is_found` (4 cases) |
| F4 | Dependabot's `Signed-off-by: ... <support@github.com>` tripped the generic email shape, so every Dependabot PR would fail pr-fast's history step | GitHub's noreply and support addresses are exempt when the whole match is the address, so a real-list name inside a noreply address is still found by its own rule | `test_github_trailer_addresses_pass_the_email_shape` |

Fails without the fix: 8 of the new tests fail against af30b89, all of them the new cases.
`make check` exit 0, 238 tests.

## F-fix check and the last fixes (2026-10-06)

The F1-F4 check (one Fable judge, workflow wf_7492a20f-7b3) found all four fixed (37 of 37 real
rules caught verbatim, flagless, in `re.compile`, as JS literals and quoted), `make check` clean
(238 tests), no regressions from the new escapes view on ordinary code, and three new defects,
each reproduced independently. Fixed directly under the same go ("Fix all four, then PR"):

| # | Severity | Finding | Fix | Test |
|---|---|---|---|---|
| D1 | medium | a real list made by filling in the example's placeholders (as the template said) repeated the example's generic rules, so the tracked files that state them were flagged for that contributor | the two lists may not share a line: the check refuses with the reason (keep only private names in the real list; no private rule in the example), without printing the line; the template's instructions now say the real list holds private names only. A first attempt that dropped shared lines from the real rules was reverted before commit: it hid a private rule pasted into the example list | `test_a_real_list_that_repeats_the_example_is_refused`; updated `test_the_copy_step_run_backwards_is_caught`, `test_a_real_name_written_as_a_regex_in_the_example_list_is_found` (now refused, exit 2) |
| D2 | low | a copy of the list quoted, bulleted or numbered printed its rules | quote markers, bullets and line numbers are stripped before the list-line comparison | `test_a_prefixed_copy_of_the_list_prints_none_of_it` (4 prefixes) |
| D3 | low | a history exception on one line hid the same string wrapped across other lines | an exempted line no longer marks its match as reported | `test_a_history_exception_does_not_hide_a_wrapped_copy` |

Fails without the fix: 9 tests fail against e7034a8, all of them new or changed cases.
`make check` exit 0, 244 tests.

## Stage S0 result

AC1-AC9 and AC13-AC19 met (re-verified by judges in four rounds plus two targeted checks); AC10,
AC11 (the real PR) and AC12 need CI and are checked on the pull request. Not run further: another
judge round on D1-D3. The adversarial rounds kept finding narrower edge cases of a gate whose job
is accidental leaks; the PR's CI is the next check.

Known limits, recorded rather than patched (static checks, threat model is accidental leaks):
`getattr`/`exec`/`vars()` and file-path module loading in the architecture rule; file names
themselves are not checked for forbidden strings; `uvx` tool environments resolve their
dependencies unlocked; semgrep's `p/python` rules need the network. Handbook follow-up (not done
here): the handbook's original `check-forbidden.mjs` has the quoted-file-name, line-wrap, CRLF and
prefix-path issues fixed in this repo's vendored copy.
