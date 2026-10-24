"""The guard set joins the staleness rule (S7, AG10; D3 "On by default, proven inert by replay").

A pipeline with more guards is a different pipeline. The consistency baseline is current for
today's guard set (raglab.guard.guard_set over default_guards: each layer's name and the sha256 of
its rules, the instruction scan first) only when its manifest recorded that set, or a committed
replay record (runs/replays/) shows that set inert, zero events, on the baseline and its repeats
as published. This is the committed-runs test's guard-set rule, in its own file so the shared
tests/retrieval/test_publish.py waits for S4b's merge (the plan's merge order)."""

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest

from raglab.evals import publish, record, replay
from raglab.evals.retrieval import GitState
from raglab.guard import default_guards, guard_set
from tests import security_support as s
from tests.conftest import ROOT

pytestmark = pytest.mark.security
GIT = GitState("0123456789abcdef0123456789abcdef01234567", False)


def today() -> str:
    return str(guard_set(default_guards(ROOT, s.clean()))["sha256"])


def test_the_consistency_baseline_is_current_for_todays_guard_set():
    baseline_dir = publish.baseline_run(ROOT, replay.KEY)
    assert baseline_dir is not None
    current, why = replay.current_for(ROOT, baseline_dir, today())
    assert current, f"the consistency baseline is stale for the guard set: {why}"


def test_every_replay_record_names_published_runs_and_no_event():
    records = sorted((ROOT / replay.REPLAYS).glob("*.json"))
    assert records, "no replay record"
    for path in records:
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["events"] == [], path.name
        assert data["schema_version"] == replay.SCHEMA_VERSION
        assert path.name == f"{data['baseline']}--{data['guard_set']['sha256'][:12]}.json"
        for run in data["runs"]:
            manifest = ROOT / publish.PUBLISHED / run["run_id"] / record.MANIFEST
            assert record.sha256_bytes(manifest.read_bytes()) == run["manifest_sha256"]


# ---------------------------------------------------------------- the rule, on a copy


@pytest.fixture
def lab(tmp_path: Path) -> tuple[Path, Path]:
    """A root with the published baseline and its index entry, and nothing else published."""
    baseline_dir = publish.baseline_run(ROOT, replay.KEY)
    assert baseline_dir is not None
    root = tmp_path / "repo"
    target = root / publish.PUBLISHED / baseline_dir.name
    shutil.copytree(baseline_dir, target)
    index = {
        "schema_version": publish.INDEX_VERSION,
        "runs": [],
        "baselines": {replay.KEY: baseline_dir.name},
    }
    (root / publish.PUBLISHED / publish.INDEX).write_text(json.dumps(index), encoding="utf-8")
    return root, target


def test_a_new_guard_set_without_a_replay_record_is_stale_naming_it(lab):
    root, baseline_dir = lab
    sha = today()
    current, why = replay.current_for(root, baseline_dir, sha)
    assert not current
    assert f"guard set {sha[:12]}" in why


def test_a_zero_event_replay_makes_it_current_and_an_edited_manifest_does_not(lab):
    root, baseline_dir = lab
    guards = default_guards(ROOT, s.clean())
    result = replay.replay(replay.baseline_runs(root), guards, s.clean())
    assert result.events == []
    data = replay.record_json(result, guards, GIT, clock=lambda: datetime(2026, 10, 24, tzinfo=UTC))
    replay.write(root, data)
    assert replay.current_for(root, baseline_dir, today())[0]
    manifest = baseline_dir / record.MANIFEST
    manifest.write_text(manifest.read_text(encoding="utf-8") + " ", encoding="utf-8")
    current, why = replay.current_for(root, baseline_dir, today())
    assert not current
    assert "replayed another manifest" in why


def test_a_recorded_answer_with_a_foreign_link_is_an_event_and_writes_no_record(lab):
    root, baseline_dir = lab
    cases = (baseline_dir / record.CASES).read_text(encoding="utf-8").splitlines()
    first = next(i for i, line in enumerate(cases) if json.loads(line)["status"] == "ok")
    case = json.loads(cases[first])
    case["answer"] += " See https://example.net/x for more."
    cases[first] = json.dumps(case, sort_keys=True, ensure_ascii=False)
    (baseline_dir / record.CASES).write_text("\n".join(cases) + "\n", encoding="utf-8")
    guards = default_guards(ROOT, s.clean())
    result = replay.replay(replay.baseline_runs(root), guards, s.clean())
    assert [(e.case, e.trial, e.guard, e.stage) for e in result.events] == [
        (case["case_id"], case["trial"], "links", "output")
    ]
    with pytest.raises(replay.ReplayError, match="writes no record"):
        replay.record_json(result, guards, GIT)
    assert not (root / replay.REPLAYS).exists()
