"""pr-fast.yml and dependabot.yml follow the hardening rules (AC9, AC12)."""

import re
from pathlib import Path

import pytest
import yaml

from tests.conftest import ROOT

pytestmark = pytest.mark.unit
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
PINNED = re.compile(r"^actions/[\w.-]+@[0-9a-f]{40}$")


def load(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    # YAML 1.1 reads the key `on` as True
    if True in data:
        data["on"] = data.pop(True)
    return data


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_workflow_is_hardened(path):
    wf = load(path)
    text = path.read_text(encoding="utf-8")
    assert wf.get("permissions") == {"contents": "read"}, (
        "top-level permissions must be contents: read"
    )
    assert "pull_request_target" not in wf["on"], "pull_request_target runs fork code with secrets"
    assert wf["concurrency"]["cancel-in-progress"], "superseded PR runs must be cancelled"
    for name, job in wf["jobs"].items():
        assert "timeout-minutes" in job, f"job {name} has no timeout-minutes"
        for step in job.get("steps", []):
            uses = step.get("uses")
            if uses is None:
                continue
            assert PINNED.match(uses), f"{uses}: only GitHub-owned actions, pinned to a full SHA"
            if uses.startswith("actions/checkout@"):
                assert step.get("with", {}).get("persist-credentials") is False
    for uses_line in re.findall(r"uses: (\S+)(.*)", text):
        assert "# v" in uses_line[1], f"{uses_line[0]} needs a version comment"


def test_dependabot_covers_every_ecosystem_monthly():
    config = yaml.safe_load((ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8"))
    ecosystems = {u["package-ecosystem"]: u for u in config["updates"]}
    assert {"uv", "github-actions", "pip"} <= set(ecosystems)
    for update in ecosystems.values():
        assert update["schedule"]["interval"] == "monthly"
        assert update["commit-message"]["prefix"] in {"chore", "ci"}
    assert ecosystems["uv"]["groups"]["python-minor-patch"]["update-types"] == ["minor", "patch"]
