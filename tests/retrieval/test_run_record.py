"""AC4: a retrieval run writes a run record that validates against schemas/run-record.v1.json:
a manifest with the git sha and dirty flag, config hashes, the model and its revision, the seed
and the provenance; cases.jsonl; and report.md generated from both. The validator also catches a
record edited after the run (hashes, scores, results, report) and the schema validator refuses
keywords it does not support."""

import json
from datetime import UTC, datetime

import pytest

from raglab.evals import record
from raglab.evals.config import canonical_sha256
from raglab.evals.schema import SchemaError, Validator
from tests.conftest import ROOT
from tests.retrieval_support import GIT, PACK, fake_run, lab_root, read_run

pytestmark = [pytest.mark.unit, pytest.mark.retrieval]


def rewrite(path, change) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def test_a_run_writes_a_valid_record_with_its_provenance(tmp_path):
    root = lab_root(tmp_path)
    run_dir = fake_run(root)
    assert sorted(p.name for p in run_dir.iterdir()) == [
        "cases.jsonl",
        "manifest.json",
        "report.md",
    ]
    assert record.validate(run_dir, root) == []
    manifest, cases = read_run(run_dir)
    assert manifest["run_id"] == "20261006T120000Z-retrieval-fake-dev-0123456" == run_dir.name
    assert (manifest["git_sha"], manifest["git_dirty"]) == (GIT.sha, False)
    assert manifest["provenance"] == "fake"
    assert manifest["seed"] == 7
    assert manifest["bootstrap"] == {
        "resamples": 200,
        "seed": 7,
        "level": 0.9,
        "method": "percentile",
    }
    assert manifest["embedder"]["model"] == "hashing-256"
    assert manifest["embedder"]["revision"] == "fake"
    config = manifest["config"]
    text = (root / "config" / "retrieval-fake.toml").read_bytes()
    assert config["file_sha256"] == record.sha256_bytes(text)
    assert config["path"] == "config/retrieval-fake.toml"
    for part in ("chunker", "embedder", "retriever"):
        body = {k: v for k, v in manifest[part].items() if k != "sha256"}
        assert manifest[part]["sha256"] == canonical_sha256(body), part
    assert manifest["dataset"]["sha256"] == record.sha256_bytes(
        (root / "golden.jsonl").read_bytes()
    )
    assert manifest["corpus"] == {
        "documents": 5,
        "chunks": len(PACK),
        "sha256": canonical_sha256([[c.chunk_id, c.sha256] for c in PACK]),
    }
    # the dev retrieval questions only: Q5 is test, Q6 behaviour
    assert [c["case_id"] for c in cases] == ["Q1", "Q2", "Q3", "Q4"]
    assert set(manifest["results"]["metrics"]) == {"hit@2", "mrr@2", "recall@2"}
    assert manifest["results"]["metrics"]["hit@2"]["n"] == 4


def test_cases_carry_labels_ranks_and_scores_without_chunk_text(tmp_path):
    root = lab_root(tmp_path)
    _, cases = read_run(fake_run(root))
    q1 = cases[0]
    assert q1["labels"] == [
        {
            "doc_id": "A-PWD",
            "section_id": "4.1",
            "chunk_ids": ["A-PWD@1.0/4.1/1", "A-PWD@1.0/4.1/2"],
            "found": q1["hit"] == 1,
        }
    ]
    assert [r["rank"] for r in q1["retrieved"]] == [1, 2]
    assert q1["question_kind"] == "plain-rule"
    text = (
        json.dumps(cases)
        + (root / "runs").joinpath("tmp").glob("*/report.md").__next__().read_text()
    )
    assert all(c.text not in text for c in PACK)
    # the tenant B question never sees tenant A chunks
    q4 = next(c for c in cases if c["case_id"] == "Q4")
    assert all(not r["chunk_id"].startswith("A-") for r in q4["retrieved"])


def test_the_real_schema_is_in_the_supported_subset():
    schema = json.loads((ROOT / record.SCHEMA_PATH).read_text(encoding="utf-8"))
    Validator(schema)  # raises SchemaError on an unsupported keyword


@pytest.mark.parametrize(
    ("label", "change", "expected"),
    [
        ("dirty flag a string", lambda m: m.update(git_dirty="no"), "$.manifest.git_dirty"),
        ("no git sha", lambda m: m.pop("git_sha"), "missing 'git_sha'"),
        ("short sha", lambda m: m.update(git_sha="abc"), "$.manifest.git_sha"),
        ("provenance", lambda m: m.update(provenance="guessed"), "$.manifest.provenance"),
        ("no revision", lambda m: m["embedder"].pop("revision"), "missing 'revision'"),
        ("extra key", lambda m: m.update(note="hand edit"), "unexpected property 'note'"),
        ("no seed", lambda m: m.pop("seed"), "missing 'seed'"),
        ("config hash", lambda m: m["config"].update(sha256="x"), "$.manifest.config.sha256"),
    ],
)
def test_the_schema_rejects_a_broken_manifest(tmp_path, label, change, expected):
    root = lab_root(tmp_path)
    run_dir = fake_run(root)
    rewrite(run_dir / record.MANIFEST, change)
    problems = record.validate(run_dir, root)
    assert any(expected in p for p in problems), (label, problems)


def test_an_edited_case_or_report_is_caught(tmp_path):
    root = lab_root(tmp_path)
    run_dir = fake_run(root)
    cases_path = run_dir / record.CASES
    lines = cases_path.read_text(encoding="utf-8").splitlines()
    case = json.loads(lines[1])
    case["hit"], case["recall"] = 1 - case["hit"], 1.0 - case["recall"]
    cases_path.write_text("\n".join([lines[0], json.dumps(case), *lines[2:]]) + "\n")
    problems = record.validate(run_dir, root)
    assert any("cases.jsonl: sha256" in p for p in problems), problems
    assert any("scores" in p and "do not follow from the ranks" in p for p in problems), problems
    assert any("results do not match the cases" in p for p in problems), problems
    assert any("report.md is not the report generated" in p for p in problems), problems

    other = fake_run(root, name="retrieval-other")
    report = other / record.REPORT
    report.write_text(report.read_text(encoding="utf-8").replace("| hit@2 |", "| hit@2 (best) |"))
    problems = record.validate(other, root)
    assert any("report.md: sha256" in p for p in problems), problems
    assert any("report.md is not the report generated" in p for p in problems), problems


def test_a_renamed_run_directory_and_a_missing_file_are_caught(tmp_path):
    root = lab_root(tmp_path)
    run_dir = fake_run(root)
    moved = run_dir.rename(run_dir.with_name("20261006T120000Z-renamed-dev-0123456"))
    assert any("is not the directory name" in p for p in record.validate(moved, root))
    (moved / record.REPORT).unlink()
    assert record.validate(moved, root) == [f"{moved.name}: report.md is missing"]


def test_the_same_inputs_give_the_same_results(tmp_path):
    root = lab_root(tmp_path)
    first = fake_run(root)
    second = fake_run(root, when=datetime(2026, 10, 6, 13, 0, 0, tzinfo=UTC))
    a, a_cases = read_run(first)
    b, b_cases = read_run(second)
    assert a["results"] == b["results"]
    strip = [{k: v for k, v in c.items() if k != "latency_ms"} for c in a_cases]
    assert strip == [{k: v for k, v in c.items() if k != "latency_ms"} for c in b_cases]


@pytest.mark.parametrize(
    ("schema", "match"),
    [
        ({"type": "object", "oneOf": []}, "unsupported keywords"),
        ({"type": "object", "properties": {"a": {"format": "date"}}}, "unsupported keywords"),
        ({"type": "decimal"}, "unknown type"),
    ],
)
def test_the_schema_validator_refuses_what_it_does_not_support(schema, match):
    with pytest.raises(SchemaError, match=match):
        Validator(schema)


def test_the_schema_validator_types_and_constraints():
    v = Validator(
        {
            "type": "object",
            "required": ["n", "flag"],
            "additionalProperties": False,
            "properties": {
                "n": {"type": "integer", "minimum": 1, "maximum": 3},
                "flag": {"type": "boolean"},
                "tags": {
                    "type": "array",
                    "minItems": 1,
                    "items": {"type": "string", "pattern": "^x"},
                },
                "kind": {"enum": ["a", "b"]},
            },
        }
    )
    assert v.errors({"n": 2, "flag": True, "tags": ["xa"], "kind": "a"}) == []
    assert v.errors({"n": 2.0, "flag": False}) == []  # an integer-valued float is an integer
    assert v.errors({"n": True, "flag": True}) == ["$.n: expected integer, got bool"]
    assert v.errors({"n": 4, "flag": 1}) == [
        "$.n: 4 is above the maximum 3",
        "$.flag: expected boolean, got int",
    ]
    assert v.errors({"flag": True, "tags": [], "kind": "c", "x": 1}) == [
        "$: missing 'n'",
        "$.tags: fewer than 1 items",
        "$.kind: 'c' is not one of ['a', 'b']",
        "$: unexpected property 'x'",
    ]
    assert v.errors({"n": 1, "flag": True, "tags": ["y"]}) == ["$.tags[0]: 'y' does not match ^x"]
