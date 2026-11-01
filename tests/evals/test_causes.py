"""S8 (GA4, GA5): the cause rule (raglab.evals.causes) on hand-built case lines, one per rule and
one per pair of rules so the order is decided; the counts per case-trial and per case; the
validator recomputing a record's causes while the corpus is the record's (a copy of the published
v2 consistency baseline, tagged, resealed, then edited); `raglab causes` writing a sealed file
beside the published runs without touching them; the committed runs/causes/ files equal to a fresh
derivation; a fake run carrying causes."""

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from raglab.__main__ import main
from raglab.evals import causes, publish, record
from tests.conftest import ROOT
from tests.retrieval_support import read_run

pytestmark = pytest.mark.unit
BASELINE = "20261024T090351Z-generation-local-ollama-dev-ade9397"
DENSE = "20261024T090200Z-retrieval-dense-dev-ade9397"
ATTACK = "20261025T205853Z-attack-local-defences-on-dev-762b163"
JUDGED = "20261021T081852Z-judge-local-dev-5aa0ec5"
A1, A2, B1 = "A-PWD@1.0/4.1/1", "A-PWD@1.0/4.1/2", "A-PWD@1.0/5/1"
CONTEXT = causes.Context(searched=frozenset({A1, A2, B1}), split_features=frozenset({"F-9"}))


def line(
    passed: bool = False,
    status: str = "ok",
    label: str = "answer",
    expected: str | None = "answer",
    labels: list[tuple[list[str], bool]] | None = None,
    features: list[str] | None = None,
    checks: dict[str, bool] | None = None,
    case_id: str = "G-1",
    trial: int = 1,
) -> dict[str, Any]:
    """A generation case line with what the rule reads."""
    out: dict[str, Any] = {
        "case_id": case_id,
        "trial": trial,
        "kind": "behaviour",
        "status": status,
        "label": label,
        "feature_ids": features or ["F-1"],
        "checks": {**(checks or {}), "passed": passed},
    }
    if expected is not None:
        out["expected"] = expected
    if labels is not None:
        out["labels"] = [{"chunk_ids": ids, "found": found} for ids, found in labels]
    return out


def retrieval_line(recall: float, labels: list[list[str]], case_id: str = "R-Q1") -> dict[str, Any]:
    return {
        "case_id": case_id,
        "trial": 1,
        "recall": recall,
        "labels": [{"chunk_ids": ids, "found": recall == 1} for ids in labels],
    }


# ---------------------------------------------------------------- one case per rule


def test_a_passed_trial_and_the_fallback_statuses_have_no_cause():
    assert causes.cause_of(line(passed=True, labels=[([A1], True)]), CONTEXT) is None
    for status in ("unavailable", "invalid_output"):
        withheld = line(status=status, label="abstain", labels=[([A1], False)])
        assert causes.cause_of(withheld, CONTEXT) is None, status
    assert causes.cause_of(retrieval_line(1.0, [[A1]]), CONTEXT) is None


def test_rule_1_ingestion_a_labelled_chunk_the_run_did_not_search():
    unsearched = line(labels=[([A1, "A-PWD@1.0/9/1"], True)])
    assert causes.cause_of(unsearched, CONTEXT) == "ingestion"
    grouped = line(labels=[([A1], True)])
    grouped["labels"][0]["any_of"] = [{"chunk_ids": [A1]}, {"chunk_ids": ["X-9@1/1/1"]}]
    assert causes.cause_of(grouped, CONTEXT) == "ingestion"
    assert causes.cause_of(retrieval_line(0.5, [[A1], ["Z@1/1/1"]]), CONTEXT) == "ingestion"


def test_rule_1_ingestion_a_feature_split_at_the_chunk_settings():
    split = line(labels=[([A1], True)], features=["F-9"])
    assert causes.cause_of(split, CONTEXT) == "ingestion"
    # without a context (the corpus is not the record's) rule 1 is not read
    assert causes.cause_of(split, None) == "generation"


def test_rule_2_retrieval_a_labelled_section_not_retrieved():
    assert causes.cause_of(line(labels=[([A1], True), ([B1], False)]), CONTEXT) == "retrieval"
    assert causes.cause_of(retrieval_line(0.0, [[A1]]), CONTEXT) == "retrieval"
    # a flag-conflict case whose conflict side was not retrieved: that label is not found
    missed = line(expected="flag-conflict", labels=[([A1], True), ([B1], False)])
    assert causes.cause_of(missed, CONTEXT) == "retrieval"


def test_rule_3_abstention():
    answered = line(expected="abstain", checks={"abstained": False, "no_value": True})
    assert causes.cause_of(answered, CONTEXT) == "abstention"
    valued = line(
        expected="abstain", label="abstain", checks={"abstained": True, "no_value": False}
    )
    assert causes.cause_of(valued, CONTEXT) == "abstention"
    over = line(label="abstain", labels=[([A1], True)], checks={"decision_label": False})
    assert causes.cause_of(over, CONTEXT) == "abstention"
    probe = {**line(expected="abstain", checks={"abstained": False}), "kind": "probe"}
    assert causes.cause_of(probe, CONTEXT) == "abstention"


def test_rule_4_generation_everything_else_with_its_labels_retrieved():
    wrong = line(labels=[([A1], True)], checks={"decision_label": False})
    assert causes.cause_of(wrong, CONTEXT) == "generation"
    blocked = line(status="blocked", label="abstain", labels=[([A1], True)])
    assert causes.cause_of(blocked, CONTEXT) == "generation"
    canary = line(
        expected="abstain",
        label="abstain",
        checks={"abstained": True, "no_value": True, "no_canary": False},
    )
    assert causes.cause_of(canary, CONTEXT) == "generation"
    position = {**line(checks={"cites_answering": False}), "kind": "position"}
    position.pop("expected")
    assert causes.cause_of(position, CONTEXT) == "generation"


# ---------------------------------------------------------------- one case per pair: the order


PAIRS = {
    "1 over 2": (line(labels=[(["Z@1/1/1"], False)]), "ingestion"),
    "1 over 3": (
        line(expected="abstain", labels=[(["Z@1/1/1"], True)], checks={"abstained": False}),
        "ingestion",
    ),
    "1 over 4": (
        line(features=["F-9"], labels=[([A1], True)], checks={"must_not_contain": False}),
        "ingestion",
    ),
    "2 over 3": (line(label="abstain", labels=[([A1], False)]), "retrieval"),
    "2 over 4": (line(labels=[([A1], False)], checks={"no_canary": False}), "retrieval"),
    "3 over 4": (
        line(expected="abstain", checks={"abstained": False, "no_canary": False}),
        "abstention",
    ),
}


@pytest.mark.parametrize(("case", "winner"), list(PAIRS.values()), ids=list(PAIRS))
def test_the_first_rule_that_applies_decides(case, winner):
    assert causes.cause_of(case, CONTEXT) == winner


def test_the_order_swapped_would_change_the_pairs():
    """What the pair tests hold: ingestion before retrieval before abstention before generation,
    as CAUSES lists them, which counts() uses to give a case its earliest cause."""
    assert causes.CAUSES == ("ingestion", "retrieval", "abstention", "generation")


# ---------------------------------------------------------------- the counts


def test_counts_per_case_trial_and_per_case():
    wrong = line(case_id="A", trial=1, labels=[([A1], True)], checks={"decision_label": False})
    rows = [
        {**wrong, "cause": "generation"},
        {**line(case_id="A", trial=2, labels=[([A1], False)]), "cause": "retrieval"},
        {**line(case_id="A", trial=3, passed=True), "cause": None},
        {**line(case_id="B", trial=1, status="unavailable", label="abstain"), "cause": None},
        {**line(case_id="B", trial=2, labels=[([A1], True)]), "cause": "generation"},
        {**line(case_id="B", trial=3, status="unavailable", label="abstain"), "cause": None},
        {**line(case_id="C", trial=1, passed=True), "cause": None},
        {**line(case_id="C", trial=2, passed=True), "cause": None},
        {**line(case_id="C", trial=3, passed=True), "cause": None},
        {**line(case_id="D", trial=1, status="invalid_output", label="abstain"), "cause": None},
    ]  # fmt: skip
    assert causes.counts(rows) == {
        "case_trials": {
            "ingestion": 0, "retrieval": 1, "abstention": 0, "generation": 2,
            "passed": 4, "no_cause": 3,
        },
        "cases": {
            "ingestion": 0, "retrieval": 1, "abstention": 0, "generation": 1,
            "passed": 1, "no_cause": 1,
        },
    }  # fmt: skip


# ---------------------------------------------------------------- the validator, on a real record


def tagged_copy(tmp_path: Path, run_id: str = BASELINE) -> tuple[Path, dict, list]:
    """A copy of a published record with every line tagged by the rule (the corpus is the
    record's) and results.causes added, resealed."""
    run_dir = tmp_path / run_id
    shutil.copytree(ROOT / publish.PUBLISHED / run_id, run_dir)
    manifest, cases = read_run(run_dir)
    context = causes.Context.for_record(manifest, ROOT)
    assert context is not None, "the corpus is the record's"
    for case, cause in zip(cases, causes.tag(cases, context), strict=True):
        case["cause"] = cause
    reseal(run_dir, manifest, cases)
    return run_dir, manifest, cases


def reseal(run_dir: Path, manifest: dict, cases: list) -> None:
    body = {k: v for k, v in manifest.items() if k != "files"}
    body["results"] = record.expected_results(body, cases)
    cases_bytes = record.cases_text(cases).encode()
    report_bytes = record.render(body, cases).encode()
    (run_dir / record.CASES).write_bytes(cases_bytes)
    (run_dir / record.REPORT).write_bytes(report_bytes)
    body["files"] = {
        record.CASES: record.sha256_bytes(cases_bytes),
        record.REPORT: record.sha256_bytes(report_bytes),
    }
    (run_dir / record.MANIFEST).write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")


def test_the_v2_baseline_tagged_by_the_rule_validates_and_an_edited_cause_is_named(tmp_path):
    run_dir, manifest, cases = tagged_copy(tmp_path)
    assert record.validate(run_dir, ROOT) == []
    assert "## Causes (no judge)" in (run_dir / record.REPORT).read_text(encoding="utf-8")
    first = next(c for c in cases if c["cause"] == "retrieval")
    first["cause"] = "generation"
    reseal(run_dir, manifest, cases)
    assert record.validate(run_dir, ROOT) == [
        f"case {first['case_id']} trial {first['trial']}: cause 'generation', but the rule gives "
        "'retrieval'"
    ]
    first["cause"] = "retrieval"
    passed = next(c for c in cases if c["cause"] is None and c["checks"]["passed"])
    passed["cause"] = "abstention"
    reseal(run_dir, manifest, cases)
    assert record.validate(run_dir, ROOT) == [
        f"case {passed['case_id']} trial {passed['trial']}: a passed trial, or one with no cause, "
        "has cause 'abstention'"
    ]
    passed["cause"] = None
    reseal(run_dir, manifest, cases)
    manifest, cases = read_run(run_dir)
    manifest["results"]["causes"]["cases"]["retrieval"] += 1
    reseal_keeping_results(run_dir, manifest, cases)
    problems = record.validate(run_dir, ROOT)
    assert any(p.startswith("results.causes {") and "are not the counts" in p for p in problems)


def reseal_keeping_results(run_dir: Path, manifest: dict, cases: list) -> None:
    """Reseal with the manifest's results as they are (an edited count kept)."""
    body = {k: v for k, v in manifest.items() if k != "files"}
    cases_bytes = record.cases_text(cases).encode()
    report_bytes = record.render(body, cases).encode()
    (run_dir / record.CASES).write_bytes(cases_bytes)
    (run_dir / record.REPORT).write_bytes(report_bytes)
    body["files"] = {
        record.CASES: record.sha256_bytes(cases_bytes),
        record.REPORT: record.sha256_bytes(report_bytes),
    }
    (run_dir / record.MANIFEST).write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")


def test_a_record_without_causes_validates_as_it_did_and_cause_is_optional(tmp_path):
    """Every committed record has no cause field and stays valid (the committed-runs test holds
    that); here the schema is read: `cause` and `results.causes` are optional, and a schema copy
    that requires `cause` refuses the published baseline."""
    schema = json.loads((ROOT / record.SCHEMA_PATH).read_text(encoding="utf-8"))
    assert "cause" not in schema["$defs"]["case"]["required"]
    assert "causes" not in schema["$defs"]["manifest"]["properties"]["results"]["required"]
    schema["$defs"]["case"]["required"].append("cause")
    root = tmp_path / "root"
    (root / "schemas").mkdir(parents=True)
    (root / record.SCHEMA_PATH).write_text(json.dumps(schema), encoding="utf-8")
    problems = record.validate(ROOT / publish.PUBLISHED / BASELINE, root)
    assert problems
    assert all("missing 'cause'" in p for p in problems)


def test_the_context_is_none_when_the_corpus_is_not_the_records(tmp_path):
    manifest, _ = read_run(ROOT / publish.PUBLISHED / BASELINE)
    other = {**manifest, "corpus": {**manifest["corpus"], "sha256": "0" * 64}}
    assert causes.Context.for_record(other, ROOT) is None
    attack, _ = read_run(ROOT / publish.PUBLISHED / ATTACK)
    assert causes.Context.for_record(attack, ROOT) is None  # attack records keep their checks
    assert causes.Context.for_record(manifest, ROOT) is not None


# ---------------------------------------------------------------- raglab causes: derived files


def test_derive_reads_a_published_run_without_change_and_seals_the_file(tmp_path):
    run_dir = ROOT / publish.PUBLISHED / BASELINE
    before = {name: (run_dir / name).read_bytes() for name in publish.FILES}
    manifest, cases = read_run(run_dir)
    data: Any = causes.derive(manifest, cases, (run_dir / record.MANIFEST).read_bytes(), ROOT)
    assert {name: (run_dir / name).read_bytes() for name in publish.FILES} == before
    assert data["recomputed"] is True
    assert data["run_id"] == BASELINE
    trials = data["counts"]["case_trials"]
    assert sum(trials.values()) == len(cases) == manifest["results"]["generation"]["case_trials"]
    assert sum(data["counts"]["cases"].values()) == manifest["results"]["generation"]["cases"]
    assert len(data["cases"]) == len(cases)
    path = causes.write(tmp_path, data)
    assert path == tmp_path / causes.OUT / f"{BASELINE}.json"
    assert causes.check_file(path) == []
    edited = json.loads(path.read_text(encoding="utf-8"))
    edited["counts"]["case_trials"]["retrieval"] += 1
    path.write_text(json.dumps(edited), encoding="utf-8")
    assert causes.check_file(path) == [
        f"{path.name}: its sha256 is not its content's: the file was edited"
    ]


def test_the_committed_causes_files_are_what_a_fresh_derivation_gives():
    """runs/causes/ holds the command's output for the published runs it names: each file is
    sealed, names a published run, and equals (sha256 for sha256) a fresh derivation."""
    files = sorted((ROOT / causes.OUT).glob("*.json"))
    assert files, "no derived file"
    for path in files:
        assert causes.check_file(path) == [], path.name
        data: Any = json.loads(path.read_text(encoding="utf-8"))
        run_dir = ROOT / publish.PUBLISHED / str(data["run_id"])
        assert path.name == f"{data['run_id']}.json"
        assert run_dir.is_dir(), f"{path.name} names an unpublished run"
        manifest, cases = read_run(run_dir)
        fresh = causes.derive(manifest, cases, (run_dir / record.MANIFEST).read_bytes(), ROOT)
        assert fresh["sha256"] == data["sha256"], path.name
        assert fresh["manifest_sha256"] == record.sha256_bytes(
            (run_dir / record.MANIFEST).read_bytes()
        )


def test_the_attack_and_judged_records_get_their_own_counts():
    manifest, cases = read_run(ROOT / publish.PUBLISHED / ATTACK)
    data: Any = causes.derive(manifest, cases, b"", ROOT)
    claim = data["counts"]["other_tenant_claim"]
    assert set(claim) == {"case_trials", "cases"}
    assert data["cause"] == "generation"
    assert len(data["cases"]) == len(cases)
    manifest, cases = read_run(ROOT / publish.PUBLISHED / JUDGED)
    data: Any = causes.derive(manifest, cases, b"", ROOT)
    split = data["counts"]["failed_verdicts"]
    assert set(split) <= {
        "grounded", "cites_support", "correct", "relevant", "abstains", "refuses_and_helps",
    }  # fmt: skip
    assert all(set(v) == {"retrieval", "generation"} for v in split.values())
    assert "context_sufficient" not in split
    assert data["counts"]["rests_on"].startswith("context_sufficient, uncalibrated")


def test_the_cli_writes_the_file_where_told_and_refuses_an_invalid_record(tmp_path, capsys):
    out = tmp_path / "derived"
    code = main(["causes", BASELINE, "--root", str(ROOT), "--out", str(out)])
    captured = capsys.readouterr()
    assert code == 0, captured.err
    assert captured.out.startswith(f"{BASELINE} (generation)\n  causes recomputed from the corpus:")
    assert "  retrieval: " in captured.out
    assert f"written: {out / BASELINE}.json (sha256 " in captured.out
    assert causes.check_file(out / f"{BASELINE}.json") == []
    broken = tmp_path / "broken" / BASELINE
    shutil.copytree(ROOT / publish.PUBLISHED / BASELINE, broken)
    (broken / record.REPORT).write_text("edited\n", encoding="utf-8")
    code = main(["causes", str(broken), "--root", str(ROOT), "--out", str(out)])
    assert code == 1
    assert "causes refused: " in capsys.readouterr().err


# ---------------------------------------------------------------- a new run carries causes


def test_a_fake_generation_run_carries_a_cause_on_every_line_and_the_counts(tmp_path):
    from tests.generation_support import behaviour_run

    root, run_dir = behaviour_run(tmp_path)
    assert record.validate(run_dir, root) == []
    manifest, cases = read_run(run_dir)
    assert all("cause" in c for c in cases)
    assert manifest["results"]["causes"] == causes.counts(cases)
    assert "## Causes (no judge)" in (run_dir / record.REPORT).read_text(encoding="utf-8")
    # the fixture's chunks are not the lab root's corpus, so the tags stand as recorded
    assert causes.Context.for_record(manifest, root) is None
    data: Any = causes.derive(manifest, cases, (run_dir / record.MANIFEST).read_bytes(), root)
    assert data["recomputed"] is False
    assert data["counts"] == manifest["results"]["causes"]


def test_a_fake_retrieval_run_carries_causes_too(tmp_path):
    from tests.retrieval_support import fake_run, lab_root, read_run

    root = lab_root(tmp_path)
    run_dir = fake_run(root)
    assert record.validate(run_dir, root) == []
    manifest, cases = read_run(run_dir)
    assert all("cause" in c for c in cases)
    assert all(c["cause"] in (None, "retrieval", "ingestion") for c in cases)
    assert manifest["results"]["causes"] == causes.counts(cases)
    assert "## Causes (no judge)" in (run_dir / record.REPORT).read_text(encoding="utf-8")
