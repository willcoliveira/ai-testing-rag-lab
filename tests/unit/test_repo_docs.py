"""The contributor docs state the rules the gates depend on (AC15, AC17)."""

import re

import pytest

from tests.conftest import ROOT

pytestmark = pytest.mark.unit


def text(name: str) -> str:
    # one line per paragraph, so a phrase wrapped across lines still matches
    return re.sub(r"\s+", " ", (ROOT / name).read_text(encoding="utf-8"))


# Judge round 3 (D3): hooks are opt-in per clone, so the docs must say they are required, and the
# go-public scan must cover the history, not only HEAD.
@pytest.mark.parametrize("name", ["README.md", "CONTRIBUTING.md"])
def test_hooks_are_required_in_every_clone(name):
    assert "make hooks is required in every clone" in text(name).replace("`", "")
    assert "pre-push" in text(name)


def test_hooks_target_installs_the_pre_push_hook():
    assert (ROOT / ".githooks" / "pre-push").is_file()
    assert "git config core.hooksPath .githooks" in text("Makefile")


def test_go_public_scans_the_whole_history_with_the_real_list():
    assert "make privacy-history RANGE=--all` with the maintainer's real list" in text(
        "docs/GO-PUBLIC.md"
    )


# AC15: CLAUDE.md carries the rules the plan lists, so a second account follows them too. Judge
# round 3 (D10): "label lab practice as lab" was missing.
@pytest.mark.parametrize(
    "rule",
    [
        "No AI attribution",
        "Pull requests only",
        "Stage loop",
        "Isolation rule",
        "make hooks is required in every clone",
        "Label lab practice as lab",
    ],
)
def test_claude_md_carries_the_planned_rules(rule):
    assert rule in text("CLAUDE.md").replace("`", "").replace("*", "")
