"""The vendored privacy check refuses a tracked real list and finds what lists name (AC5, AC6)."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.conftest import ROOT

pytestmark = pytest.mark.unit
NODE = shutil.which("node")


def git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    if NODE is None:
        pytest.fail("node is required for the privacy check")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "privacy").mkdir()
    shutil.copy(ROOT / "scripts" / "check-forbidden.mjs", tmp_path / "scripts")
    shutil.copy(ROOT / "privacy" / "forbidden-strings.example.txt", tmp_path / "privacy")
    (tmp_path / "privacy" / "forbidden-strings.txt").write_text(
        "/\\bacmeclient\\b/i\n", encoding="utf-8"
    )
    (tmp_path / "notes.md").write_text("trustworthy text\n", encoding="utf-8")
    git(tmp_path, "init", "-q")
    git(tmp_path, "add", "scripts", "privacy/forbidden-strings.example.txt", "notes.md")
    return tmp_path


def run(cwd: Path, *args: str, ci: bool = False) -> subprocess.CompletedProcess[str]:
    assert NODE is not None
    env = {k: v for k, v in os.environ.items() if k != "CI"}
    if ci:
        env["CI"] = "1"
    return subprocess.run(
        [NODE, "scripts/check-forbidden.mjs", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        env=env,
    )


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
    shutil.copy(ROOT / "scripts" / "check-staged-privacy.sh", repo / "scripts")
    git(repo, "add", "scripts/check-staged-privacy.sh")
    note = repo / "note.md"
    # built at runtime so this file does not itself contain the pattern
    note.write_text("ref arn" + ":aws:iam::x\n", encoding="utf-8")
    git(repo, "add", "note.md")
    note.write_text("clean text\n", encoding="utf-8")
    env = {**os.environ, "CI": "1"}
    staged = subprocess.run(
        ["sh", "scripts/check-staged-privacy.sh"], cwd=repo, capture_output=True, text=True, env=env
    )
    assert staged.returncode == 1
    assert "note.md" in staged.stdout
    git(repo, "add", "note.md")
    clean = subprocess.run(
        ["sh", "scripts/check-staged-privacy.sh"], cwd=repo, capture_output=True, text=True, env=env
    )
    assert clean.returncode == 0
