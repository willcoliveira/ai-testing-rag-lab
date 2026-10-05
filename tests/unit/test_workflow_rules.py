"""pr-fast.yml and dependabot.yml follow the hardening rules (AC9, AC12)."""

import re
from pathlib import Path

import pytest
import yaml

from tests.conftest import ROOT

pytestmark = pytest.mark.unit
WORKFLOW_DIR = ROOT / ".github" / "workflows"
WORKFLOWS = sorted([*WORKFLOW_DIR.glob("*.yml"), *WORKFLOW_DIR.glob("*.yaml")])
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
    assert (wf.get("concurrency") or {}).get("cancel-in-progress"), (
        "superseded PR runs must be cancelled"
    )
    for name, job in wf["jobs"].items():
        # a reusable workflow at job level runs someone else's whole workflow; only local ones
        job_uses = job.get("uses")
        assert job_uses is None or job_uses.startswith("./"), (
            f"job {name}: reusable workflow {job_uses} is not local"
        )
        # a job may narrow permissions, never widen them; add a reviewed exception here when a
        # keyed workflow needs more (e.g. id-token: write for OIDC deploys)
        assert job.get("permissions") in (None, {"contents": "read"}), (
            f"job {name} widens permissions to {job.get('permissions')}"
        )
        if job_uses is None:
            assert "timeout-minutes" in job, f"job {name} has no timeout-minutes"
        for step in job.get("steps", []):
            uses = step.get("uses")
            if uses is None:
                continue
            assert PINNED.match(uses), f"{uses}: only GitHub-owned actions, pinned to a full SHA"
            if uses.startswith("actions/checkout@"):
                assert step.get("with", {}).get("persist-credentials") is False
    for uses, rest in re.findall(r"uses: ['\"]?([^'\"\s]+)['\"]?(.*)", text):
        if not uses.startswith("./"):
            assert "# v" in rest, f"{uses} needs a version comment"


def test_rules_reject_the_judge_bypasses(tmp_path, monkeypatch):
    """The S0 judge's bypasses: a third-party reusable workflow, job-level write permissions, a
    .yaml file and a missing concurrency block must each fail the rule check."""
    base = load(WORKFLOW_DIR / "pr-fast.yml")
    variants = {
        "reusable": {"call": {"uses": "someone/else/.github/workflows/b.yml@" + "a" * 40}},
        "write-all": {"x": {**base["jobs"]["check"], "permissions": "write-all"}},
    }
    for label, jobs in variants.items():
        path = tmp_path / f"{label}.yaml"
        path.write_text(yaml.safe_dump({**base, "jobs": jobs}), encoding="utf-8")
        with pytest.raises(AssertionError):
            test_workflow_is_hardened(path)
    no_concurrency = {k: v for k, v in base.items() if k != "concurrency"}
    path = tmp_path / "noconc.yaml"
    path.write_text(yaml.safe_dump(no_concurrency), encoding="utf-8")
    with pytest.raises(AssertionError):
        test_workflow_is_hardened(path)


def test_dependabot_covers_every_ecosystem_monthly():
    config = yaml.safe_load((ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8"))
    ecosystems = {u["package-ecosystem"]: u for u in config["updates"]}
    assert {"uv", "github-actions", "pip"} <= set(ecosystems)
    for update in ecosystems.values():
        assert update["schedule"]["interval"] == "monthly"
        assert update["commit-message"]["prefix"] in {"chore", "ci"}
    assert ecosystems["uv"]["groups"]["python-minor-patch"]["update-types"] == ["minor", "patch"]
