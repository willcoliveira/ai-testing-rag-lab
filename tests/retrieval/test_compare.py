"""AC5: `raglab compare` gives, per metric, B minus A with a paired bootstrap interval, and lists
the flipped questions by id; runs that are not paired are refused."""

import json
from typing import Any

import pytest

from raglab.__main__ import main
from raglab.evals import compare, metrics, record
from tests.retrieval_support import PACK, fake_run, lab_root, make_chunk, read_run

pytestmark = [pytest.mark.unit, pytest.mark.retrieval]


def edit_cases(run_dir, change) -> None:
    """Rewrite a run's cases (and regenerate what depends on them) as if the run had retrieved
    differently, so a comparison with hand-known per-question values can be built."""
    manifest, cases = read_run(run_dir)
    for case in cases:
        change(case)
        ids = [r["chunk_id"] for r in case["retrieved"]]
        sets = [frozenset(label["chunk_ids"]) for label in case["labels"]]
        for r in case["retrieved"]:
            r["relevant"] = any(r["chunk_id"] in s for s in sets)
        for label, s in zip(case["labels"], sets, strict=True):
            label["found"] = bool(set(ids) & s)
        case.update(record.case_scores(ids, sets, manifest["retriever"]["k"]))
    manifest["results"] = record.results_from_cases(
        cases, manifest["retriever"]["k"], manifest["bootstrap"]
    )
    body = {k: v for k, v in manifest.items() if k != "files"}
    cases_bytes = record.cases_text(cases).encode()
    report_bytes = record.render_report(body, cases).encode()
    (run_dir / record.CASES).write_bytes(cases_bytes)
    (run_dir / record.REPORT).write_bytes(report_bytes)
    manifest["files"] = {
        record.CASES: record.sha256_bytes(cases_bytes),
        record.REPORT: record.sha256_bytes(report_bytes),
    }
    (run_dir / record.MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n")
    assert record.validate(run_dir, run_dir.parent.parent.parent) == []


def retrieve(ids_by_case):
    def change(case):
        ids = ids_by_case[case["case_id"]]
        case["retrieved"] = [
            {"rank": n, "chunk_id": i, "score": 1.0 / n, "relevant": False}
            for n, i in enumerate(ids, start=1)
        ]

    return change


def test_paired_differences_and_flipped_questions_by_hand(tmp_path):
    root = lab_root(tmp_path)
    a = fake_run(root, name="retrieval-a")
    b = fake_run(root, name="retrieval-b")
    x = "X-NIST@4/3.1/1"
    # A: Q1 at rank 1, Q2 missed, Q3 one of two sections, Q4 at rank 2
    edit_cases(
        a,
        retrieve(
            {
                "Q1": ["A-PWD@1.0/4.1/2", x],
                "Q2": [x, "A-MFA@1.0/4.1/1"],
                "Q3": ["A-MFA@1.0/4.1/1", x],
                "Q4": [x, "B-PWD@1.0/3/1"],
            }
        ),
    )
    # B: Q1 missed, Q2 at rank 2, Q3 both sections, Q4 at rank 1
    edit_cases(
        b,
        retrieve(
            {
                "Q1": [x, "A-MFA@1.0/4.1/1"],
                "Q2": [x, "A-PWD@1.0/5/1"],
                "Q3": ["A-VPN@1.0/4.5/1", "A-MFA@1.0/4.1/1"],
                "Q4": ["B-PWD@1.0/3/1", x],
            }
        ),
    )
    result: Any = compare.compare(a, b, root)
    m = result["metrics"]
    # hit: A 1,0,1,1 B 0,1,1,1 -> 0.75 and 0.75, diff 0
    assert (m["hit@2"]["a"], m["hit@2"]["b"], m["hit@2"]["diff"]) == (0.75, 0.75, 0.0)
    # RR: A 1, 0, 1, 0.5 = 0.625; B 0, 0.5, 1, 1 = 0.625; per question -1, 0.5, 0, 0.5
    assert (m["mrr@2"]["a"], m["mrr@2"]["b"], m["mrr@2"]["diff"]) == (0.625, 0.625, 0.0)
    # recall: A 1, 0, 0.5, 1 = 0.625; B 0, 1, 1, 1 = 0.75; diff 0.125
    assert (m["recall@2"]["a"], m["recall@2"]["b"], m["recall@2"]["diff"]) == (0.625, 0.75, 0.125)
    expected = metrics.paired_difference(
        [1, 0, 0.5, 1], [0, 1, 1, 1], seed=7, resamples=200, level=0.9
    )
    assert (m["recall@2"]["ci_low"], m["recall@2"]["ci_high"]) == (
        round(expected.low, 6),
        round(expected.high, 6),
    )
    assert m["recall@2"]["n"] == 4
    assert result["flipped"] == {"gained": ["Q2"], "lost": ["Q1"]}
    assert result["changed"]["recall@2"] == {"better": ["Q2", "Q3"], "worse": ["Q1"]}
    assert result["changed"]["mrr@2"] == {"better": ["Q2", "Q4"], "worse": ["Q1"]}
    text = compare.render(result)
    assert "| recall@2 | 0.625 | 0.750 | +0.125 |" in text
    assert "Found by B only (1): Q2" in text
    assert "Found by A only (1): Q1" in text


def test_the_cli_writes_compare_json_and_md(tmp_path, capsys):
    root = lab_root(tmp_path)
    a = fake_run(root, name="retrieval-a")
    b = fake_run(root, name="retrieval-b", kind="hybrid")
    out = tmp_path / "cmp"
    assert main(["compare", str(a), str(b), "--out", str(out), "--root", str(root)]) == 0
    data: Any = json.loads((out / "compare.json").read_text())
    assert (data["a_config"], data["b_config"], data["n"]) == ("retrieval-a", "retrieval-b", 4)
    assert (out / "compare.md").read_text() == compare.render(data)
    assert "B minus A" in capsys.readouterr().out


def test_runs_that_are_not_paired_are_refused(tmp_path, capsys):
    root = lab_root(tmp_path)
    a = fake_run(root, name="retrieval-a")
    b = fake_run(root, name="retrieval-b", k=3)
    with pytest.raises(compare.CompareError, match=r"not the same retriever\.k"):
        compare.compare(a, b, root)
    golden = root / "golden.jsonl"
    golden.write_text(golden.read_text() + "\n")
    c = fake_run(root, name="retrieval-c")
    with pytest.raises(compare.CompareError, match=r"not the same dataset\.sha256"):
        compare.compare(a, c, root)
    (a / record.REPORT).write_text("edited")
    with pytest.raises(compare.CompareError, match="not a valid run record"):
        compare.compare(a, c, root)
    assert main(["compare", "nowhere", str(c), "--root", str(root)]) == 1
    assert "no run record at nowhere" in capsys.readouterr().err


def test_different_case_ids_are_refused(tmp_path):
    root = lab_root(tmp_path)
    a = fake_run(root, name="retrieval-a")
    b = fake_run(
        root, name="retrieval-b", chunks=[*PACK, make_chunk("A-Z@1/9/1", "tenant-a", "z", "9")]
    )
    edit_cases(b, lambda case: case.update(case_id=case["case_id"].replace("Q4", "Q9")))
    with pytest.raises(compare.CompareError, match="same case ids"):
        compare.compare(a, b, root)
