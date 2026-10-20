"""S4 (AC6, AC9; the plan's "Where it runs": "the fake suite over the dev cases, whose record must
validate"). The generation suite through the CLI, as `raglab eval` runs it, on the real golden
file (golden set v1.1: the retrieval questions and the behaviour cases), the real pack and the
real local embedder, with FakeChat (config/fake.toml, one trial). check-dataset runs first, the
record validates (the CLI exits 1 otherwise), and it holds every dev case with its behaviour
results and report section. With the echo model these numbers measure the plumbing, never Q-05,
so none is asserted beyond the shape."""

import json
from pathlib import Path

import pytest

from raglab.__main__ import main
from raglab.evals import golden, record
from tests.conftest import ROOT
from tests.retrieval_support import read_run

pytestmark = [pytest.mark.e2e_fake]


def test_the_fake_suite_over_the_real_dev_cases_writes_a_valid_record(tmp_path: Path, capsys):
    source = (ROOT / "config" / "fake.toml").read_text(encoding="utf-8")
    config = tmp_path / "fake.toml"
    config.write_text(source.replace("trials = 3", "trials = 1"), encoding="utf-8")
    out = tmp_path / "runs"
    command = ["eval", "--suite", "generation", "--config", str(config), "--out", str(out)]
    code = main([*command, "--root", str(ROOT)])
    captured = capsys.readouterr()
    assert code == 0, captured.err
    assert "check-dataset: datasets/golden.v1.jsonl passes" in captured.err
    [run_dir] = list(out.iterdir())
    assert record.validate(run_dir, ROOT) == []
    manifest, cases = read_run(run_dir)
    every = golden.load(ROOT / "datasets" / "golden.v1.jsonl")
    dev = {q.case_id for q in every if q.split == "dev"}
    behaviour_dev = {q.case_id for q in every if q.split == "dev" and q.kind == "behaviour"}
    assert {str(c["case_id"]) for c in cases} == dev
    assert manifest["dataset"]["questions"] == len(dev)
    assert "probes" not in manifest  # the S3 probes are golden cases now
    assert {"P-01", "P-02", "P-03"} <= behaviour_dev
    assert {str(c["case_id"]) for c in cases if c["kind"] == "probe"} == set()
    generation = manifest["results"]["generation"]
    assert generation["behaviour"]["cases"] == len(behaviour_dev)
    assert {"decision_label", "behaviour_pass^1", "pass^1"} <= set(manifest["results"]["metrics"])
    report = (run_dir / record.REPORT).read_text(encoding="utf-8")
    assert "## Behaviour cases" in report
    # the may_quote case keeps its section's chunks and their values, never their text
    quoted = [c for c in cases if "may_quote" in c]
    assert quoted
    for case in quoted:
        assert case["expected"] == "abstain"
        assert all(set(chunk) == {"chunk_id", "values"} for chunk in case["may_quote"]["chunks"])
    # every flag-conflict case's labels carry their sides, from the answer key
    flagged = [c for c in cases if c["kind"] == "behaviour" and c["expected"] == "flag-conflict"]
    assert flagged
    for case in flagged:
        sides = {label.get("side") for label in case["labels"]}
        assert {"governing", "conflict"} <= sides, case["case_id"]
    json.dumps(manifest)  # the manifest is plain JSON
