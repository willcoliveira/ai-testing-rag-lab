"""docs/ONBOARDING.md names only paths, make targets and raglab commands that exist, so the guide
fails a test instead of going stale when a stage renames something."""

import re

import pytest

from raglab.__main__ import main
from tests.conftest import ROOT

pytestmark = pytest.mark.unit

GUIDE = (ROOT / "docs" / "ONBOARDING.md").read_text(encoding="utf-8")
FENCED = re.findall(r"^```\w*\n(.*?)^```", GUIDE, re.M | re.S)
CODE = re.findall(r"`([^`\n]+)`", GUIDE) + [line for block in FENCED for line in block.splitlines()]
TOP = ("src/", "tests/", "scripts/", "corpus/", "datasets/", "docs/", "schemas/", "config/")
DOTTED = (".github/", ".githooks/")


def named_paths() -> list[str]:
    paths: set[str] = set()
    for code in CODE:
        for word in code.split():
            word = word.rstrip(",.;:)")
            if word.startswith(TOP + DOTTED) and "<" not in word:
                paths.add(word)
    return sorted(paths)


def named(prefix: str) -> list[str]:
    found = {m.group(1) for code in CODE for m in re.finditer(rf"\b{prefix} ([a-z][a-z-]*)", code)}
    return sorted(found)


def test_the_guide_names_paths_targets_and_commands():
    assert len(named_paths()) >= 30
    assert {"check", "gate", "model", "playground"} <= set(named("make"))
    assert {"ingest", "eval", "compare"} <= set(named("raglab"))


@pytest.mark.parametrize("path", named_paths())
def test_every_named_path_exists(path):
    assert (ROOT / path).exists(), f"docs/ONBOARDING.md names {path}, which does not exist"


@pytest.mark.parametrize("target", named("make"))
def test_every_make_target_exists(target):
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert re.search(rf"^{re.escape(target)}:", makefile, re.M), f"no make target {target}"


@pytest.mark.parametrize("command", named("raglab"))
def test_every_raglab_command_exists(command, capsys):
    with pytest.raises(SystemExit) as stop:
        main([command, "--help"])
    assert stop.value.code == 0, f"raglab has no command {command}"
    capsys.readouterr()
