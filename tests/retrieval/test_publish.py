"""`raglab publish` validates a run, runs the privacy check on its files, copies it to
runs/published/<run_id>/ and rebuilds index.json (AC9: the index the playground reads); a dirty,
fake, invalid or private run is refused. And the no-regression gate against the baseline."""

import json
import shutil
from datetime import UTC, datetime

import pytest

from raglab.evals import gate, publish, record, retrieval
from tests.conftest import ROOT
from tests.retrieval_support import fake_run, lab_root, read_run

pytestmark = [pytest.mark.unit, pytest.mark.retrieval]


def clean(run_dir, root):
    return []


def local_run(root, **kwargs):
    """A fake-embedder run labelled local, so publish's provenance rule lets it through: only for
    testing the publishing mechanics."""
    return fake_run(root, provenance="local", **kwargs)


def test_publish_copies_the_run_and_builds_the_index(tmp_path):
    root = lab_root(tmp_path)
    first = local_run(root, name="retrieval-a")
    second = local_run(
        root, name="retrieval-b", kind="hybrid", when=datetime(2026, 10, 7, 9, 0, 0, tzinfo=UTC)
    )
    dest = publish.publish(first, root, baseline=True, privacy=clean)
    publish.publish(second, root, privacy=clean)
    assert dest == root / "runs" / "published" / first.name
    for name in publish.FILES:
        assert (dest / name).read_bytes() == (first / name).read_bytes()
    index = json.loads((root / "runs" / "published" / "index.json").read_text())
    assert index["schema_version"] == "published-index.v1"
    assert [r["run_id"] for r in index["runs"]] == [second.name, first.name]  # newest first
    entry = index["runs"][1]
    manifest, _ = read_run(first)
    assert entry == {
        "run_id": first.name,
        "path": f"{first.name}/",
        "created_at": "2026-10-06T12:00:00Z",
        "suite": "retrieval",
        "split": "dev",
        "config": "retrieval-a",
        "provenance": "local",
        "git_sha": manifest["git_sha"],
        "embedder": "hashing-256@fake",
        "retriever": "dense",
        "k": 2,
        "chunk_size": 1200,
        "n": 4,
        "metrics": manifest["results"]["metrics"],
    }
    assert index["baselines"] == {"retrieval/retrieval-a/dev": first.name}
    assert publish.baseline_run(root, "retrieval/retrieval-a/dev") == dest
    assert publish.baseline_run(root, "retrieval/retrieval-b/dev") is None
    # publishing the same run again changes nothing
    publish.publish(first, root, privacy=clean)
    assert json.loads((root / "runs" / "published" / "index.json").read_text()) == index


@pytest.mark.parametrize(
    ("label", "kwargs", "match"),
    [
        ("dirty", {"git": retrieval.GitState("a" * 40, True)}, "dirty work tree"),
        ("fake", {"provenance": "fake"}, "fake provenance"),
    ],
)
def test_a_dirty_or_fake_run_is_refused(tmp_path, label, kwargs, match):
    root = lab_root(tmp_path)
    run_dir = fake_run(root, **kwargs)
    with pytest.raises(publish.PublishError, match=match):
        publish.publish(run_dir, root, privacy=clean)
    assert not (root / "runs" / "published").exists(), label


def test_an_invalid_or_private_run_is_refused(tmp_path):
    root = lab_root(tmp_path)
    run_dir = local_run(root)
    with pytest.raises(publish.PublishError, match="the privacy check found"):
        publish.publish(run_dir, root, privacy=lambda d, r: ["cases.jsonl:3: a private name"])
    (run_dir / record.REPORT).write_text("edited by hand\n")
    with pytest.raises(publish.PublishError, match="not a valid run record"):
        publish.publish(run_dir, root, privacy=clean)
    assert not (root / "runs" / "published").exists()


def test_a_published_run_is_never_replaced_by_other_files(tmp_path):
    root = lab_root(tmp_path)
    run_dir = local_run(root)
    publish.publish(run_dir, root, privacy=clean)
    dest = root / "runs" / "published" / run_dir.name
    (dest / record.REPORT).write_text("changed\n")
    with pytest.raises(publish.PublishError, match="already published with different files"):
        publish.publish(run_dir, root, privacy=clean)


@pytest.mark.skipif(shutil.which("node") is None, reason="the privacy check needs node")
def test_the_real_privacy_check_runs_on_the_run_files(tmp_path):
    """The repo's checker (example list) over a run's directory: clean, then with a string the
    example list forbids (an email address outside the allowlist) planted in the report."""
    root = lab_root(tmp_path)
    shutil.copytree(ROOT / "scripts", root / "scripts")
    shutil.copytree(
        ROOT / "privacy", root / "privacy", ignore=shutil.ignore_patterns("forbidden-strings.txt")
    )
    run_dir = local_run(root)
    assert publish.node_privacy_check(run_dir, root) == []
    report = run_dir / record.REPORT
    address = "@".join(["someone", "private-domain.org"])  # joined here, so this file stays clean
    report.write_text(report.read_text() + f"contact {address}\n")
    assert publish.node_privacy_check(run_dir, root) != []


def test_the_gate_passes_within_one_question_and_fails_below(tmp_path):
    root = lab_root(tmp_path)
    baseline, _ = read_run(local_run(root))
    k = baseline["retriever"]["k"]
    name = f"recall@{k}"
    value = baseline["results"]["metrics"][name]["value"]
    n = baseline["results"]["metrics"][name]["n"]

    def current(recall: float, dataset_sha256: str | None = None):
        manifest = json.loads(json.dumps(baseline))
        manifest["run_id"] = "now"
        manifest["results"]["metrics"][name]["value"] = recall
        if dataset_sha256:
            manifest["dataset"]["sha256"] = dataset_sha256
        return manifest

    assert gate.check(baseline, current(value)).passed
    assert gate.check(baseline, current(round(value - 1 / n, 6))).passed
    verdict = gate.check(baseline, current(round(value - 1 / n - 0.01, 6)))
    assert not verdict.passed
    assert "fails" in verdict.message
    assert f"minus one question (1/{n})" in verdict.message
    stale = gate.check(baseline, current(value, dataset_sha256="0" * 64))
    assert not stale.passed
    assert "publish a new baseline" in stale.message


# ---------------------------------------------------------------- the committed published runs


def test_the_committed_runs_are_valid_local_dev_runs_with_a_current_baseline():
    """runs/published holds real, clean, complete local runs on the dev split only (the test
    split is never published), index.json is what publish builds from them, and the dense dev
    baseline the gate reads was made with today's dataset and config (else the gate is stale)."""
    from raglab.evals import config as eval_config

    published = ROOT / publish.PUBLISHED
    index = publish.read_index(published)
    runs = sorted(p.parent for p in published.glob(f"*/{record.MANIFEST}"))
    assert runs, "no published run"
    for run_dir in runs:
        assert record.validate(run_dir, ROOT) == [], run_dir.name
        manifest, cases = record.read(run_dir)
        assert manifest["provenance"] == "local", run_dir.name
        assert manifest["git_dirty"] is False, run_dir.name
        assert manifest["partial"] is False, run_dir.name
        assert manifest["split"] == "dev", run_dir.name
        assert {c["split"] for c in cases} == {"dev"}, run_dir.name
    baselines = {str(k): str(v) for k, v in record.as_json(index["baselines"]).items()}
    assert index == publish.build_index(published, baselines)
    key = "retrieval/retrieval-dense/dev"
    baseline_dir = publish.baseline_run(ROOT, key)
    assert baseline_dir is not None, f"no baseline for {key}"
    baseline, _ = record.read(baseline_dir)
    dense = eval_config.load(ROOT / "config" / "retrieval-dense.toml", ROOT)
    dataset = record.as_json(baseline["dataset"])
    assert dataset["sha256"] == record.sha256_bytes((ROOT / dense.dataset).read_bytes())
    used = record.as_json(baseline["config"])
    assert used["sha256"] == eval_config.canonical_sha256(dense.resolved())
