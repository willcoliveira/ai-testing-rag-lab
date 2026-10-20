"""AC5: `raglab compare` gives, per metric, B minus A with a paired bootstrap interval, and lists
the flipped questions by id; runs that are not paired are refused. S4 AC8: two generation runs
are paired by behaviour case id (behaviour pass^N and the decision-label rate)."""

import json
from datetime import UTC, datetime
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


# ---------------------------------------------------------------- S4 AC8: generation runs

LATER = datetime(2026, 10, 19, 13, 0, 0, tzinfo=UTC)


def reversed_record(run_dir) -> None:
    """The run's case lines in reverse order, resealed (results, report, hashes): the same run, so
    a comparison that pairs by position instead of case id reads it wrong."""
    manifest, cases = read_run(run_dir)
    cases.reverse()
    manifest["results"] = record.expected_results(manifest, cases)
    body = {k: v for k, v in manifest.items() if k != "files"}
    cases_bytes = record.cases_text(cases).encode()
    report_bytes = record.render(body, cases).encode()
    (run_dir / record.CASES).write_bytes(cases_bytes)
    (run_dir / record.REPORT).write_bytes(report_bytes)
    manifest["files"] = {
        record.CASES: record.sha256_bytes(cases_bytes),
        record.REPORT: record.sha256_bytes(report_bytes),
    }
    (run_dir / record.MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n")


def test_paired_generation_differences_and_flipped_cases_by_hand(tmp_path):
    """A passes every check on all seven behaviour cases; in B, B-FC2 answers with a conflict
    field, B-ABS gives the S3 pattern (decisions wrong) and B-TB leaks a tenant A canary (decision
    right, a check failed). B's lines are reversed, so only pairing by case id gets this right."""
    from tests.generation_support import Q_ABS, Q_FC2, Q_TB, V2_44, behaviour_run, reply

    root, a = behaviour_run(tmp_path)
    worse = {
        Q_FC2: reply("answer", "60 days.", [V2_44.chunk_id], [V2_44.chunk_id], "x"),
        Q_ABS: reply("answer", "The documents do not say."),
        Q_TB: reply("answer", "Halvenroot does it too.", []),
    }
    _, b = behaviour_run(tmp_path, worse, root=root, when=LATER)
    reversed_record(b)
    assert record.validate(b, root) == []
    result: Any = compare.compare(a, b, root)
    assert (result["suite"], result["trials"], result["n"]) == ("generation", 2, 7)
    ids = ["B-ANS", "B-FC", "B-FC2", "B-ABS", "B-ABQ", "B-RH", "B-TB"]  # A's order
    passes_b = [1, 1, 0, 0, 1, 1, 0]
    right_b = [1, 1, 0, 0, 1, 1, 1]
    m = result["metrics"]
    assert (m["behaviour_pass^2"]["a"], m["behaviour_pass^2"]["b"]) == (1.0, round(4 / 7, 6))
    assert m["behaviour_pass^2"]["diff"] == round(-3 / 7, 6)
    assert (m["decision_label"]["a"], m["decision_label"]["b"]) == (1.0, round(5 / 7, 6))
    assert m["decision_label"]["diff"] == round(-2 / 7, 6)
    for name, values in (("behaviour_pass^2", passes_b), ("decision_label", right_b)):
        expected = metrics.paired_difference([1.0] * 7, values, seed=7, resamples=2000)
        assert (m[name]["ci_low"], m[name]["ci_high"], m[name]["n"]) == (
            round(expected.low, 6),
            round(expected.high, 6),
            7,
        ), name
    assert result["bootstrap"] == {
        "resamples": 2000,
        "seed": 7,
        "level": 0.95,
        "method": "percentile",
    }
    assert result["flipped"] == {"gained": [], "lost": ["B-FC2", "B-ABS", "B-TB"]}
    assert result["changed"]["decision_label"] == {"better": [], "worse": ["B-FC2", "B-ABS"]}
    assert [i for i in ids if i in result["flipped"]["lost"]] == result["flipped"]["lost"]
    text = compare.render(result)
    assert "- 7 paired behaviour cases (by case id), split dev" in text
    assert "| behaviour_pass^2 | 1.000 | 0.571 | -0.429 |" in text
    assert "Passed every trial in A only (3): B-FC2, B-ABS, B-TB" in text
    assert "decision_label: better in B for none; worse in B for B-FC2, B-ABS" in text


def test_unpaired_generation_runs_are_refused(tmp_path):
    from tests.generation_support import behaviour_run

    root, a = behaviour_run(tmp_path)
    _, three = behaviour_run(tmp_path, root=root, trials=3, when=LATER)
    with pytest.raises(compare.CompareError, match="not the same trials"):
        compare.compare(a, three, root)
    golden = root / "golden.jsonl"
    golden.write_text(golden.read_text() + "\n")
    _, other = behaviour_run(tmp_path, root=root, when=datetime(2026, 10, 19, 14, 0, tzinfo=UTC))
    with pytest.raises(compare.CompareError, match=r"not the same dataset\.sha256"):
        compare.compare(a, other, root)
    # a retrieval run beside it: the small pack's documents registered too, a retrieval question
    from tests.generation_support import BEHAVIOUR_CHUNKS
    from tests.retrieval_support import LAB_DOCS, QUESTIONS, write_register, write_snapshot

    write_register(root, {**LAB_DOCS, **{c.doc_id: c.tenant for c in BEHAVIOUR_CHUNKS}})
    write_snapshot(root, [*BEHAVIOUR_CHUNKS, *PACK])
    golden.write_text(golden.read_text() + json.dumps(QUESTIONS[0]) + "\n")
    retrieval_run = fake_run(root, name="retrieval-a")
    assert record.validate(retrieval_run, root) == []
    with pytest.raises(compare.CompareError, match="a generation run and a retrieval run"):
        compare.compare(a, retrieval_run, root)
