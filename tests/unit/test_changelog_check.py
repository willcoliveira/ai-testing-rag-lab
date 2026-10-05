"""A PR must add a CHANGELOG line unless a bot opened it (AC11)."""

import subprocess
from pathlib import Path

import pytest

from tests.conftest import load_script

pytestmark = pytest.mark.unit
changelog = load_script("check_changelog")


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path, monkeypatch):
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.email", "test@example.com")
    git(tmp_path, "config", "user.name", "test")
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "chore: base")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def commit(repo: Path, name: str, text: str) -> str:
    path = repo / name
    path.write_text(
        path.read_text(encoding="utf-8") + text if path.exists() else text, encoding="utf-8"
    )
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", f"chore: change {name}")
    return git(repo, "rev-parse", "HEAD")


def test_pr_without_changelog_line_fails(repo):
    base = git(repo, "rev-parse", "HEAD")
    head = commit(repo, "code.py", "x = 1\n")
    assert changelog.main(["--base", base, "--head", head, "--author", "willcoliveira"]) == 1


def test_pr_with_changelog_line_passes(repo):
    base = git(repo, "rev-parse", "HEAD")
    commit(repo, "code.py", "x = 1\n")
    head = commit(repo, "CHANGELOG.md", "- S0: skeleton\n")
    assert changelog.main(["--base", base, "--head", head, "--author", "willcoliveira"]) == 0


def test_blank_line_does_not_count(repo):
    base = git(repo, "rev-parse", "HEAD")
    head = commit(repo, "CHANGELOG.md", "\n\n")
    assert changelog.main(["--base", base, "--head", head, "--author", "willcoliveira"]) == 1


def test_whitespace_change_to_an_existing_line_does_not_count(repo):
    commit(repo, "CHANGELOG.md", "- S0: skeleton\n")
    base = git(repo, "rev-parse", "HEAD")
    path = repo / "CHANGELOG.md"
    path.write_text(path.read_text(encoding="utf-8").replace("- S0: skeleton", "- S0: skeleton   "))
    git(repo, "commit", "-q", "-am", "chore: whitespace")
    head = git(repo, "rev-parse", "HEAD")
    assert changelog.main(["--base", base, "--head", head, "--author", "willcoliveira"]) == 1


def test_bot_is_exempt(repo):
    base = git(repo, "rev-parse", "HEAD")
    head = commit(repo, "uv.lock", "bump\n")
    assert changelog.main(["--base", base, "--head", head, "--author", "dependabot[bot]"]) == 0
