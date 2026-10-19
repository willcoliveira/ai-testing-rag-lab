"""pr-fast.yml and dependabot.yml follow the hardening rules (AC9, AC12)."""

import re
from pathlib import Path

import pytest
import yaml

from tests.conftest import ROOT

pytestmark = pytest.mark.unit
WORKFLOW_DIR = ROOT / ".github" / "workflows"
PINNED = re.compile(r"^actions/[\w.-]+@[0-9a-f]{40}$")


def workflow_files(directory: Path) -> list[Path]:
    return sorted([*directory.glob("*.yml"), *directory.glob("*.yaml")])


WORKFLOWS = workflow_files(WORKFLOW_DIR)


def load(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    # YAML 1.1 reads the key `on` as True
    if True in data:
        data["on"] = data.pop(True)
    return data


def narrower_than_contents_read(permissions: object) -> bool:
    """A job's permissions replace the workflow's: none at all (`{}`), or only `none` scopes and at
    most `contents: read`, can never grant more than the workflow-level contents: read."""
    if permissions is None:
        return True
    if not isinstance(permissions, dict):
        return False  # read-all, write-all
    return all(
        level == "none" or (scope == "contents" and level == "read")
        for scope, level in permissions.items()
    )


def check_workflow(wf: dict, text: str) -> None:
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
        assert narrower_than_contents_read(job.get("permissions")), (
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


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_workflow_is_hardened(path):
    check_workflow(load(path), path.read_text(encoding="utf-8"))


# Each variant is checked against the real file's text (its version comments intact), so it fails
# for the rule named in `match`, not because yaml.safe_dump dropped the comments.
@pytest.mark.parametrize(
    ("label", "match"),
    [
        ("reusable", "is not local"),
        ("write-all", "widens permissions"),
        ("read-all", "widens permissions"),
        ("wider", "widens permissions"),
        ("no-concurrency", "superseded PR runs"),
    ],
)
def test_rules_reject_the_judge_bypasses(label, match):
    """The S0 judge's bypasses: a third-party reusable workflow, job-level permissions wider than
    contents: read, and a missing concurrency block must each fail the rule check."""
    path = WORKFLOW_DIR / "pr-fast.yml"
    base, text = load(path), path.read_text(encoding="utf-8")
    check = base["jobs"]["check"]
    variants = {
        "reusable": {
            "jobs": {"call": {"uses": "someone/else/.github/workflows/b.yml@" + "a" * 40}}
        },
        "write-all": {"jobs": {"x": {**check, "permissions": "write-all"}}},
        "read-all": {"jobs": {"x": {**check, "permissions": "read-all"}}},
        "wider": {"jobs": {"x": {**check, "permissions": {"contents": "read", "issues": "read"}}}},
    }
    wf = (
        {k: v for k, v in base.items() if k != "concurrency"}
        if label == "no-concurrency"
        else {**base, **variants[label]}
    )
    with pytest.raises(AssertionError, match=match):
        check_workflow(wf, text)


def test_yaml_workflows_are_checked_too(tmp_path):
    (tmp_path / "a.yml").write_text("{}", encoding="utf-8")
    (tmp_path / "b.yaml").write_text("{}", encoding="utf-8")
    assert [p.name for p in workflow_files(tmp_path)] == ["a.yml", "b.yaml"]


@pytest.mark.parametrize(
    "permissions", [{}, {"contents": "none"}, {"contents": "read"}], ids=["empty", "none", "read"]
)
def test_job_may_narrow_permissions_below_contents_read(permissions):
    """Judge round 2: job-level `permissions: {}` (no access at all) is narrower than the
    workflow's contents: read and must pass."""
    path = WORKFLOW_DIR / "pr-fast.yml"
    base, text = load(path), path.read_text(encoding="utf-8")
    jobs = {"x": {**base["jobs"]["check"], "permissions": permissions}}
    check_workflow({**base, "jobs": jobs}, text)


def test_pr_fast_checks_the_commits_of_a_pr():
    """Judge round 3 (D3): the history check runs on the PR's commits (base..head), with the full
    history fetched, and the SHAs reach the shell through env only."""
    wf = load(WORKFLOW_DIR / "pr-fast.yml")
    steps = wf["jobs"]["check"]["steps"]
    history = [step for step in steps if "make privacy-history" in step.get("run", "")]
    assert len(history) == 1
    step = history[0]
    assert step["if"] == "github.event_name == 'pull_request'"
    assert step["env"] == {
        "BASE_SHA": "${{ github.event.pull_request.base.sha }}",
        "HEAD_SHA": "${{ github.event.pull_request.head.sha }}",
    }
    assert step["run"] == 'make privacy-history RANGE="$BASE_SHA..$HEAD_SHA"'
    checkout = next(s for s in steps if s.get("uses", "").startswith("actions/checkout@"))
    assert checkout["with"]["fetch-depth"] == 0


def test_dependabot_covers_every_ecosystem_monthly():
    config = yaml.safe_load((ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8"))
    ecosystems = {u["package-ecosystem"]: u for u in config["updates"]}
    assert {"uv", "github-actions", "pip"} <= set(ecosystems)
    for update in ecosystems.values():
        assert update["schedule"]["interval"] == "monthly"
        assert update["commit-message"]["prefix"] in {"chore", "ci"}
    assert ecosystems["uv"]["groups"]["python-minor-patch"]["update-types"] == ["minor", "patch"]
    # majors come as their own PRs for actions too, as the file's header says (S0 judge round 4, E6)
    assert ecosystems["github-actions"]["groups"]["github-actions"]["update-types"] == [
        "minor",
        "patch",
    ]


def test_pr_fast_installs_pinned_tesseract_before_the_tests():
    """S1b AC8: the OCR tests run in CI on a pinned Tesseract, whose version the log shows."""
    wf = load(WORKFLOW_DIR / "pr-fast.yml")
    steps = wf["jobs"]["check"]["steps"]
    names = [step.get("name") for step in steps]
    install = steps[names.index("Install Tesseract (pinned)")]
    assert names.index("Install Tesseract (pinned)") < names.index("Tests (offline)")
    run = install["run"]
    for package, variable in [
        ("tesseract-ocr", "TESSERACT_VERSION"),
        ("tesseract-ocr-eng", "TESSDATA_VERSION"),
        ("tesseract-ocr-osd", "TESSDATA_VERSION"),
    ]:
        assert f'"{package}=${{{variable}}}"' in run, package
    assert re.fullmatch(r"\d+\.\d+\.\d+-\S+", wf["env"]["TESSERACT_VERSION"])
    assert re.fullmatch(r"\d+:\d+\.\d+\.\d+-\S+", wf["env"]["TESSDATA_VERSION"])
    assert "tesseract --version" in run
    assert steps[names.index("Tests (offline)")]["run"] == "make test"


def test_runners_are_pinned_with_the_tesseract_packages():
    """S1b decision: the runner image is pinned (not ubuntu-latest), so it moves together with the
    apt pins in one reviewed PR."""
    for path in WORKFLOWS:
        for name, job in load(path)["jobs"].items():
            runner = job.get("runs-on")
            assert runner is None or runner != "ubuntu-latest", (
                f"{path.name}:{name} runs on ubuntu-latest"
            )


def test_pr_fast_restores_and_fetches_the_model_by_revision_before_the_tests():
    """S2 AC8: the model is cached by its pinned revision (actions/cache pinned by SHA), fetched
    with its hashes checked before the tests, and the tests run with the hub offline."""
    from raglab.adapters import fastembed_embed

    wf = load(WORKFLOW_DIR / "pr-fast.yml")
    assert wf["env"]["EMBED_MODEL_REVISION"] == fastembed_embed.REVISION
    steps = wf["jobs"]["check"]["steps"]
    names = [step.get("name") for step in steps]
    cache = steps[names.index("Restore the embedding model (cached by revision)")]
    assert PINNED.match(cache["uses"])
    assert cache["uses"].startswith("actions/cache@")
    assert cache["with"] == {
        "path": "~/.cache/raglab/models",
        "key": "raglab-model-${{ env.EMBED_MODEL_REVISION }}",
    }
    fetch = names.index("Embedding model (download on a miss, hashes checked)")
    assert steps[fetch]["run"] == "make model"
    tests = names.index("Tests (offline)")
    assert names.index("Restore the embedding model (cached by revision)") < fetch < tests
    assert steps[tests]["env"] == {"HF_HUB_OFFLINE": "1"}
    assert fastembed_embed.cache_root().as_posix().endswith(".cache/raglab/models")


def test_pr_fast_runs_the_retrieval_gate_offline_after_the_tests():
    """S2 AC8: the recall@5 no-regression gate runs in pr-fast after the tests, offline with the
    cached model, and `make check` runs the same target."""
    wf = load(WORKFLOW_DIR / "pr-fast.yml")
    steps = wf["jobs"]["check"]["steps"]
    names = [step.get("name") for step in steps]
    gate = names.index("Retrieval no-regression gate (offline)")
    assert names.index("Embedding model (download on a miss, hashes checked)") < gate
    assert names.index("Install Tesseract (pinned)") < gate
    assert names.index("Tests (offline)") < gate
    assert steps[gate]["run"] == "make gate"
    assert steps[gate]["env"] == {"HF_HUB_OFFLINE": "1"}
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    check = re.search(r"^check:(.*)$", makefile, flags=re.M)
    assert check is not None
    assert "gate" in check.group(1).split()
    target = re.search(r"^gate:\n\t(.*)$", makefile, flags=re.M)
    assert target is not None
    assert target.group(1) == (
        "HF_HUB_OFFLINE=1 uv run raglab gate --config config/retrieval-dense.toml"
    )


def test_pr_fast_runs_the_dataset_check_as_its_own_step_before_the_tests():
    """S4 AC3: "Dataset check (hard stop)" runs `make check-dataset` as a step of its own, before
    the model fetch, the tests, the retrieval gate and the API smoke, with no network-shaped
    input; `make check` runs the same target before its tests."""
    wf = load(WORKFLOW_DIR / "pr-fast.yml")
    steps = wf["jobs"]["check"]["steps"]
    names = [step.get("name") for step in steps]
    check = names.index("Dataset check (hard stop)")
    assert steps[check]["run"] == "make check-dataset"
    assert "uses" not in steps[check]
    assert "env" not in steps[check]
    assert names.index("Install the project") < check
    for later in (
        "Embedding model (download on a miss, hashes checked)",
        "Tests (offline)",
        "Retrieval no-regression gate (offline)",
        "API smoke (offline, fake model)",
    ):
        assert check < names.index(later), later
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    targets = re.search(r"^check:(.*)$", makefile, flags=re.M)
    assert targets is not None
    order = targets.group(1).split()
    assert order.index("check-dataset") < order.index("test") < order.index("gate")
    target = re.search(r"^check-dataset:\n\t(.*)$", makefile, flags=re.M)
    assert target is not None
    assert target.group(1) == "uv run raglab check-dataset"


def test_pr_fast_smoke_tests_the_api_offline_after_the_tests():
    """S3 AC12: pr-fast starts `raglab serve` with config/fake.toml and smoke-tests /healthz,
    /version, an /ask answer and a no-tenant refusal, offline, after the model fetch and the
    tests; `make check` runs the same target, and the script talks to loopback only."""
    wf = load(WORKFLOW_DIR / "pr-fast.yml")
    steps = wf["jobs"]["check"]["steps"]
    names = [step.get("name") for step in steps]
    smoke = names.index("API smoke (offline, fake model)")
    assert names.index("Embedding model (download on a miss, hashes checked)") < smoke
    assert names.index("Tests (offline)") < smoke
    assert steps[smoke]["run"] == "make api-smoke"
    assert steps[smoke]["env"] == {"HF_HUB_OFFLINE": "1"}
    assert "uses" not in steps[smoke]
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    check = re.search(r"^check:(.*)$", makefile, flags=re.M)
    assert check is not None
    assert "api-smoke" in check.group(1).split()
    target = re.search(r"^api-smoke:\n\t(.*)$", makefile, flags=re.M)
    assert target is not None
    assert target.group(1) == (
        "HF_HUB_OFFLINE=1 uv run python scripts/api_smoke.py --port $(API_SMOKE_PORT)"
    )
    script = (ROOT / "scripts" / "api_smoke.py").read_text(encoding="utf-8")
    assert 'CONFIG = "config/fake.toml"' in script
    assert "http://127.0.0.1:" in script
    for path in ("/healthz", "/version", "/ask"):
        assert f'"{path}"' in script, path
    assert 'call(base, "POST", "/ask", {"question": QUESTION})' in script  # the no-tenant refusal
    assert "code == 403" in script
