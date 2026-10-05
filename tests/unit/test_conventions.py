"""Commit messages, PR titles and branch names follow the convention (AC19)."""

import pytest

from tests.conftest import load_script

pytestmark = pytest.mark.unit
conv = load_script("check_conventions")


@pytest.mark.parametrize(
    "header",
    [
        "chore(repo): add skeleton",
        "feat(retrieval): add BM25 hybrid search",
        "fix: handle an empty corpus",
        "feat(api)!: rename /ask to /answer",
        "ci(deps): bump actions/checkout",
        'Revert "feat(api): add /ask"',
        "Merge branch 'main' into feat/s2-retrieval",
    ],
)
def test_good_headers_pass(header):
    assert conv.check_header(header) is None


@pytest.mark.parametrize(
    "header",
    [
        "update stuff",
        "Feat(api): capital type",
        "feat(API): uppercase scope",
        "feat:missing space",
        "feature(api): unknown type",
        "feat(api): " + "x" * 100,
        "",
    ],
)
def test_bad_headers_fail(header):
    assert conv.check_header(header) is not None


def test_message_uses_first_non_comment_line():
    assert conv.check_message("# a comment\n\nchore(repo): add skeleton\n\nbody text\n") is None
    assert conv.check_message("# only comments\n") == "empty commit message"
    assert conv.check_message("WIP\n") is not None


@pytest.mark.parametrize(
    "branch",
    [
        "chore/s0-repo-skeleton",
        "feat/s1a-policy-corpus",
        "fix/s3h-cold-start",
        "docs/readme-status",
        "main",
        "dependabot/uv/ruff-0.17",
    ],
)
def test_good_branches_pass(branch):
    assert conv.check_branch(branch) is None


@pytest.mark.parametrize(
    "branch",
    ["s0-skeleton", "my-branch", "feature/s1-corpus", "feat/S1-Corpus", "feat/", "feat/s1a_policy"],
)
def test_bad_branches_fail(branch):
    assert conv.check_branch(branch) is not None


def test_cli(tmp_path):
    msg = tmp_path / "MSG"
    msg.write_text("update stuff\n", encoding="utf-8")
    assert conv.main(["--message-file", str(msg)]) == 1
    msg.write_text("chore(repo): add skeleton\n", encoding="utf-8")
    assert conv.main(["--message-file", str(msg)]) == 0
    assert conv.main(["--branch", "s0-skeleton"]) == 1
    assert conv.main(["--title", "chore(repo): add skeleton"]) == 0
