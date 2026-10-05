"""The vendored privacy check refuses a tracked real list and finds what lists name (AC5, AC6)."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.conftest import ROOT

pytestmark = pytest.mark.unit
NODE = shutil.which("node")


def clean_env(*, ci: bool = False, **extra: str) -> dict[str, str]:
    """The environment without CI and without any GIT_* variable, so a git command in a test can
    only reach the throwaway repo it runs in (never the checkout the tests run from, even when
    pytest itself runs inside a git hook)."""
    env = {k: v for k, v in os.environ.items() if k != "CI" and not k.startswith("GIT_")}
    if ci:
        env["CI"] = "1"
    return {**env, **extra}


def git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, env=clean_env())


@pytest.fixture
def repo(tmp_path):
    if NODE is None:
        pytest.fail("node is required for the privacy check")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "privacy").mkdir()
    shutil.copy(ROOT / "scripts" / "check-forbidden.mjs", tmp_path / "scripts")
    shutil.copy(ROOT / "scripts" / "check-staged-privacy.sh", tmp_path / "scripts")
    shutil.copy(ROOT / "privacy" / "forbidden-strings.example.txt", tmp_path / "privacy")
    shutil.copy(ROOT / "privacy" / "allowlist.txt", tmp_path / "privacy")
    shutil.copy(ROOT / ".gitignore", tmp_path)
    (tmp_path / "privacy" / "forbidden-strings.txt").write_text(
        "/\\bacmeclient\\b/i\n", encoding="utf-8"
    )
    (tmp_path / "notes.md").write_text("trustworthy text\n", encoding="utf-8")
    git(tmp_path, "init", "-q")
    git(
        tmp_path,
        "add",
        ".gitignore",
        "scripts",
        "privacy/forbidden-strings.example.txt",
        "privacy/allowlist.txt",
        "notes.md",
    )
    return tmp_path


def run(cwd: Path, *args: str, ci: bool = False) -> subprocess.CompletedProcess[str]:
    assert NODE is not None
    return subprocess.run(
        [NODE, "scripts/check-forbidden.mjs", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        env=clean_env(ci=ci),
    )


def staged(cwd: Path, *, ci: bool = True) -> subprocess.CompletedProcess[str]:
    """The pre-commit privacy check, run by hand on the repo's index."""
    return subprocess.run(
        ["sh", "scripts/check-staged-privacy.sh"],
        cwd=cwd,
        capture_output=True,
        text=True,
        env=clean_env(ci=ci),
    )


def arn() -> str:
    # built at runtime so this file does not itself contain the pattern
    return "ref arn" + ":aws:iam::x\n"


def test_clean_repo_passes(repo):
    assert run(repo).returncode == 0


def test_refuses_when_real_list_is_tracked(repo):
    git(repo, "add", "-f", "privacy/forbidden-strings.txt")
    result = run(repo)
    assert result.returncode == 2
    assert "REFUSING" in result.stderr


def test_real_list_word_boundary_rule_hits_and_spares_substrings(repo):
    (repo / "leak.md").write_text("worked for AcmeClient last year\n", encoding="utf-8")
    result = run(repo)
    assert result.returncode == 1
    assert "leak.md:1" in result.stdout
    assert "notes.md" not in result.stdout  # "trustworthy"-style substrings do not match


def test_example_list_pattern_hits_in_ci_mode(repo):
    # built at runtime so this file does not itself contain a 12-digit account-id shape
    (repo / "ids.md").write_text("account " + "1234567890" + "12" + "\n", encoding="utf-8")
    assert run(repo, ci=True).returncode == 1


def test_file_mode_checks_one_commit_message(repo):
    msg = repo / "MSG"
    msg.write_text("chore: mention acmeclient\n", encoding="utf-8")
    assert run(repo, "--file", "MSG").returncode == 1
    msg.write_text("chore(repo): add skeleton\n", encoding="utf-8")
    assert run(repo, "--file", "MSG").returncode == 0


def test_token_split_at_a_line_break_is_found(repo):
    (repo / "split.md").write_text("see arn:\naws:iam for details\n", encoding="utf-8")
    result = run(repo, ci=True)
    assert result.returncode == 1
    assert "split.md" in result.stdout


def test_staged_check_reads_the_index_not_the_working_tree(repo):
    """The S0 judge's bypass: stage a forbidden string, clean the file on disk, commit."""
    note = repo / "note.md"
    note.write_text(arn(), encoding="utf-8")
    git(repo, "add", "note.md")
    note.write_text("clean text\n", encoding="utf-8")
    result = staged(repo)
    assert result.returncode == 1
    assert "note.md" in result.stdout
    git(repo, "add", "note.md")
    assert staged(repo).returncode == 0


# Judge round 2 (N2): the throwaway copy of the index never has the real list tracked, so the
# staged check must refuse a staged real list itself, in CI mode too.
@pytest.mark.parametrize("ci", [False, True])
def test_staged_check_refuses_a_staged_real_list(repo, ci):
    git(repo, "add", "-f", "privacy/forbidden-strings.txt")
    result = staged(repo, ci=ci)
    assert result.returncode == 2
    assert "REFUSING" in result.stderr


# Judge round 2 (N3): a force-added file that .gitignore matches is in the commit, so it is checked.
def test_staged_check_scans_force_added_ignored_files(repo):
    (repo / ".env").write_text("KEY=" + arn(), encoding="utf-8")
    git(repo, "add", "-f", ".env")
    result = staged(repo)
    assert result.returncode == 1
    assert ".env:1" in result.stdout


# Judge round 2 (N4): git C-quotes these names ("caf\303\251.md"), which no file is called.
@pytest.mark.parametrize("name", ["caf\u00e9.md", 'q"uote.md'])
def test_files_with_quoted_names_are_scanned(repo, name):
    (repo / name).write_text(arn(), encoding="utf-8")
    untracked = run(repo, ci=True)
    assert untracked.returncode == 1
    assert f"{name}:1" in untracked.stdout
    git(repo, "add", name)
    tracked = run(repo, ci=True)
    assert tracked.returncode == 1
    assert f"{name}:1" in tracked.stdout
    in_index = staged(repo)
    assert in_index.returncode == 1
    assert f"{name}:1" in in_index.stdout


# Judge round 2 (N5): a single CRLF inside a paragraph read as a blank line, so the token wrapped
# at it was not joined. A blank CRLF line still separates paragraphs.
@pytest.mark.parametrize(
    ("content", "hit"),
    [
        (b"Acme\r\nClient\r\n", True),
        (b"Acme\rClient\r", True),
        (b"Acme\nClient\n", True),
        (b"Acme\r\n\r\nClient\r\n", False),
        (b"Acme\r\n \t\r\nClient\r\n", False),
    ],
)
def test_line_join_view_handles_crlf(repo, content, hit):
    (repo / "x.md").write_bytes(content)
    result = run(repo)
    assert result.returncode == (1 if hit else 0), result.stdout
    assert ("x.md: matches" in result.stdout) is hit


# Found while fixing round 2: the path rule exempted every file whose name starts with
# privacy/forbidden-strings, so an editor backup of the real list was never scanned.
@pytest.mark.parametrize("name", ["forbidden-strings.txt~", "forbidden-strings.txt.bak"])
def test_only_the_two_list_files_are_exempt(repo, name):
    (repo / "privacy" / name).write_text("acmeclient\n", encoding="utf-8")
    result = run(repo)
    assert result.returncode == 1
    assert f"privacy/{name}:1" in result.stdout
    git(repo, "add", f"privacy/{name}")
    assert staged(repo, ci=False).returncode == 1


def test_staged_check_survives_symlinks(repo):
    """A staged symlink (dangling, or to a directory) neither crashes the check nor walks out of
    the copy of the index."""
    (repo / "dangling.md").symlink_to("missing.md")
    (repo / "up").symlink_to("..")
    git(repo, "add", "dangling.md", "up")
    result = staged(repo)
    assert result.returncode == 0, result.stdout + result.stderr


def pre_commit_privacy_line() -> str:
    """The line of the real pre-commit hook that runs the staged privacy check."""
    text = (ROOT / ".githooks" / "pre-commit").read_text(encoding="utf-8")
    return next(line for line in text.splitlines() if "check-staged-privacy.sh" in line)


# Judge round 2 (N1): git exports an absolute GIT_DIR (.git/worktrees/<name>) to hooks; the round-1
# script ran `git init` under it and wrote core.bare=true to the shared .git/config. Reproduced only
# in a throwaway repo under tmp_path.
def test_commit_from_a_linked_worktree_leaves_the_main_repo_intact(tmp_path):
    main = tmp_path / "main"
    for sub in ("scripts", "privacy", ".githooks"):
        (main / sub).mkdir(parents=True)
    shutil.copy(ROOT / "scripts" / "check-forbidden.mjs", main / "scripts")
    shutil.copy(ROOT / "scripts" / "check-staged-privacy.sh", main / "scripts")
    shutil.copy(ROOT / "privacy" / "forbidden-strings.example.txt", main / "privacy")
    hook = main / ".githooks" / "pre-commit"
    hook.write_text(f"#!/bin/sh\n{pre_commit_privacy_line()}\n", encoding="utf-8")
    hook.chmod(0o755)
    (tmp_path / "gitconfig").write_text("", encoding="utf-8")
    env = clean_env(ci=True, GIT_CONFIG_GLOBAL=str(tmp_path / "gitconfig"), GIT_CONFIG_NOSYSTEM="1")

    def g(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, env=env)

    assert g(main, "init", "-q", "-b", "main").returncode == 0
    for key, value in (
        ("user.name", "Test"),
        ("user.email", "test@example.com"),
        ("commit.gpgsign", "false"),
        ("core.hooksPath", ".githooks"),
    ):
        assert g(main, "config", key, value).returncode == 0
    assert g(main, "add", "-A").returncode == 0
    first = g(main, "commit", "-q", "-m", "chore: initial commit")  # through the hook
    assert first.returncode == 0, first.stdout + first.stderr
    assert g(main, "worktree", "add", "-q", "-b", "docs/note", str(tmp_path / "wt")).returncode == 0
    wt = tmp_path / "wt"

    (wt / "note.md").write_text("clean text\n", encoding="utf-8")
    assert g(wt, "add", "note.md").returncode == 0
    commit = g(wt, "commit", "-q", "-m", "docs: add a note")
    assert commit.returncode == 0, commit.stdout + commit.stderr

    assert g(main, "config", "--get", "core.bare").stdout.strip() != "true"
    assert g(main, "status", "--porcelain").returncode == 0
    assert g(main, "rev-parse", "--is-bare-repository").stdout.strip() == "false"
    assert g(wt, "status", "--porcelain").returncode == 0

    # and the hook still blocks a forbidden string staged in the linked worktree
    head = g(wt, "rev-parse", "HEAD").stdout
    (wt / "leak.md").write_text(arn(), encoding="utf-8")
    assert g(wt, "add", "leak.md").returncode == 0
    blocked = g(wt, "commit", "-q", "-m", "docs: add a leak")
    assert blocked.returncode != 0
    assert "leak.md:1" in blocked.stderr  # git shows hook output on stderr
    assert g(wt, "rev-parse", "HEAD").stdout == head
    assert g(main, "config", "--get", "core.bare").stdout.strip() != "true"
