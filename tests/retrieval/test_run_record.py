"""AC4: a retrieval run writes a run record that validates against schemas/run-record.v1.json:
a manifest with the git sha and dirty flag, config hashes, the model and its revision, the seed
and the provenance; cases.jsonl; and report.md generated from both. The validator also catches a
record edited after the run (hashes, scores, results, report) and the schema validator refuses
keywords it does not support."""

import contextlib
import json
from datetime import UTC, datetime

import pytest

from raglab.evals import record
from raglab.evals.config import canonical_sha256
from raglab.evals.schema import SchemaError, Validator
from raglab.generate import prompts
from tests.conftest import ROOT
from tests.retrieval_support import GIT, PACK, fake_run, lab_root, read_run, reseal

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


def test_a_label_group_is_recorded_with_its_members_and_an_edited_group_is_refused(tmp_path):
    """S4 (AC2): a group is one label in the record: the primary's ids, every member's chunks
    together, `any_of` with each member's chunks; the report says how a group is found. A group
    whose chunk ids or primary were edited apart from its members is refused, even resealed."""
    from tests.retrieval_support import QUESTIONS

    group = {
        "any_of": [
            {"doc_id": "A-PWD", "section_id": "4.1"},
            {"doc_id": "X-NIST", "section_id": "3.1"},
        ]
    }
    questions = [{**q, "relevant": [group]} if q["id"] == "Q1" else q for q in QUESTIONS]
    root = lab_root(tmp_path, questions)
    run_dir = fake_run(root)
    assert record.validate(run_dir, root) == []
    _, cases = read_run(run_dir)
    [label] = cases[0]["labels"]
    assert (label["doc_id"], label["section_id"]) == ("A-PWD", "4.1")
    assert label["chunk_ids"] == ["A-PWD@1.0/4.1/1", "A-PWD@1.0/4.1/2", "X-NIST@4/3.1/1"]
    assert [m["chunk_ids"] for m in label["any_of"]] == [
        ["A-PWD@1.0/4.1/1", "A-PWD@1.0/4.1/2"],
        ["X-NIST@4/3.1/1"],
    ]
    assert "is one thing to find" in (run_dir / record.REPORT).read_text(encoding="utf-8")
    label["chunk_ids"] = label["chunk_ids"][:2]  # the second member dropped from the union
    reseal(run_dir, cases)
    problems = record.validate(run_dir, root)
    assert any("a group's chunk_ids are not its members' chunks together" in p for p in problems)
    label["chunk_ids"] = [*label["chunk_ids"], "X-NIST@4/3.1/1"]
    label["doc_id"], label["section_id"] = "X-NIST", "3.1"
    reseal(run_dir, cases)
    problems = record.validate(run_dir, root)
    assert problems == ["case Q1: a group's doc_id and section_id are its first member's"]


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


# ---------------------------------------------------------------- tenants (S2 judge D3)


def test_a_record_that_shows_another_tenants_chunk_is_refused(tmp_path):
    root = lab_root(tmp_path)
    run_dir = fake_run(root)
    _, cases = read_run(run_dir)
    q1 = next(c for c in cases if c["case_id"] == "Q1")
    assert q1["tenant"] == "tenant-a"
    q1["retrieved"][0]["chunk_id"] = "B-PWD@1.0/3/1"
    reseal(run_dir, cases)
    assert record.validate(run_dir, root) == [
        "case Q1 (tenant-a): chunk B-PWD@1.0/3/1 is tenant-b, which it cannot see"
    ]


def test_a_tenant_b_label_on_a_tenant_a_case_is_refused(tmp_path):
    root = lab_root(tmp_path)
    run_dir = fake_run(root)
    _, cases = read_run(run_dir)
    q2 = next(c for c in cases if c["case_id"] == "Q2")
    q2["labels"][0]["chunk_ids"] = ["B-PWD@1.0/3/1"]
    reseal(run_dir, cases)
    assert record.validate(run_dir, root) == [
        # since S4's fix round 1 the label check sees it too: the chunk is not A-PWD 5's
        "case Q2 trial 1: label A-PWD 5 has chunk ids ['B-PWD@1.0/3/1'], not the section's "
        "chunks at 1200/1 ['A-PWD@1.0/5/1']",
        "case Q2 (tenant-a): chunk B-PWD@1.0/3/1 is tenant-b, which it cannot see",
    ]


def test_shared_chunks_pass_and_an_unregistered_document_is_refused(tmp_path):
    root = lab_root(tmp_path)
    run_dir = fake_run(root)
    _, cases = read_run(run_dir)
    q4 = next(c for c in cases if c["case_id"] == "Q4")
    assert q4["tenant"] == "tenant-b"
    q4["retrieved"][0]["chunk_id"] = "X-NIST@4/3.1/1"  # shared: every tenant may see it
    reseal(run_dir, cases)
    assert record.validate(run_dir, root) == []
    q4["retrieved"][0]["chunk_id"] = "Q-NONE@1/1/1"
    reseal(run_dir, cases)
    assert record.validate(run_dir, root) == [
        "case Q4 (tenant-b): chunk Q-NONE@1/1/1 names Q-NONE, which is not in the register"
    ]


def test_a_root_without_a_register_fails_closed(tmp_path):
    root = lab_root(tmp_path)
    run_dir = fake_run(root)
    (root / "corpus" / "register.yaml").unlink()
    [problem] = record.validate(run_dir, root)
    assert problem.startswith("the register cannot be read, so the tenants are unchecked")


# ---------------------------------------------------------------- S3 AC8: generation runs


S2_RUNS = (
    "20261006T172928Z-retrieval-dense-dev-5f1d3a0",
    "20261006T172957Z-retrieval-hybrid-dev-5f1d3a0",
    "20261006T173026Z-retrieval-dense-600-dev-5f1d3a0",
)


@pytest.mark.parametrize("run_id", S2_RUNS)
def test_the_three_s2_runs_still_validate_under_the_extended_schema(run_id):
    run_dir = ROOT / "runs" / "published" / run_id
    assert record.validate(run_dir, ROOT) == []
    manifest, _ = read_run(run_dir)
    assert manifest["suite"] == "retrieval"
    assert "generator" not in manifest


S3_RUN = "20261018T162604Z-generation-local-ollama-dev-3b66ea3"


def test_the_s3_run_still_validates_unchanged():
    """S4 AC6: run record v1 stays additive. The S3 run (probe cases, a probes block, no behaviour
    case) validates as it is: its checks, results and report are recomputed from its fields, the
    probes' oracle included, and match its files."""
    run_dir = ROOT / "runs" / "published" / S3_RUN
    assert record.validate(run_dir, ROOT) == []
    manifest, cases = read_run(run_dir)
    assert "probes" in manifest
    assert "behaviour" not in manifest["results"]["generation"]
    assert {c["kind"] for c in cases} == {"retrieval", "probe"}


def _reseal_generation(run_dir, cases, recheck: bool = True) -> None:
    """Rewrite a generation run's cases with results, report and hashes that agree, as a careful
    hand edit would; with recheck, the checks too (from the live answer key)."""
    from raglab.evals import generation_record
    from raglab.ingest.answer_key import canaries, must_not_contain

    manifest, _ = read_run(run_dir)
    if recheck:
        for case in cases:
            with contextlib.suppress(KeyError, ValueError, TypeError):
                case["checks"] = generation_record.case_checks(
                    case, canaries(ROOT), must_not_contain(ROOT)
                )
    with contextlib.suppress(KeyError, ValueError, TypeError):
        manifest["results"] = record.expected_results(manifest, cases)
    body = {k: v for k, v in manifest.items() if k != "files"}
    cases_bytes = record.cases_text(cases).encode()
    try:
        report_bytes = record.render(body, cases).encode()
    except (KeyError, ValueError, TypeError):
        report_bytes = (run_dir / record.REPORT).read_bytes()
    (run_dir / record.CASES).write_bytes(cases_bytes)
    (run_dir / record.REPORT).write_bytes(report_bytes)
    manifest["files"] = {
        record.CASES: record.sha256_bytes(cases_bytes),
        record.REPORT: record.sha256_bytes(report_bytes),
    }
    (run_dir / record.MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n")


def _first(cases, case_id):
    return next(c for c in cases if c["case_id"] == case_id)


@pytest.mark.parametrize(
    ("label", "case_id", "change", "expected"),
    [
        (
            "no expected label",
            "B-ANS",
            lambda c: c.pop("expected"),
            "a behaviour case needs ['expected']",
        ),
        ("no mix", "B-ABS", lambda c: c.pop("mix"), "a behaviour case needs ['mix']"),
        (
            "labels on an abstain case",
            "B-ABS",
            lambda c: c.update(
                labels=[
                    {"doc_id": "A", "section_id": "1", "chunk_ids": ["A@1/1/1"], "found": False}
                ]
            ),
            "a behaviour case has no ['labels']",
        ),
        (
            "may_quote on a labelled case",
            "B-ANS",
            lambda c: c.update(
                may_quote={
                    "doc_id": "X-NIST",
                    "section_id": "3.1.1.2",
                    "chunks": [{"chunk_id": "X-NIST@4/3.1.1.2/1", "values": ["64"]}],
                }
            ),
            "a behaviour case has no ['may_quote']",
        ),
        (
            "a side on a case that does not flag a conflict",
            "B-ANS",
            lambda c: c["labels"][0].update(side="governing"),
            "only a flag-conflict case's labels take a side",
        ),
        (
            "an unretrieved citation",
            "B-ANS",
            lambda c: c.update(cited_ids=["A-PWD-V2@2.0/4.6/1"]),
            "cites ids that were not retrieved: ['A-PWD-V2@2.0/4.6/1']",
        ),
        (
            "canaries_of on a behaviour case",
            "B-ABS",
            lambda c: c.update(canaries_of=None),
            "a behaviour case has no ['canaries_of']",
        ),
    ],
)
def test_a_broken_behaviour_case_is_refused(tmp_path, label, case_id, change, expected):
    from tests.generation_support import behaviour_run

    root, run_dir = behaviour_run(tmp_path)
    assert record.validate(run_dir, root) == []
    _, cases = read_run(run_dir)
    for case in cases:
        if case["case_id"] == case_id:
            change(case)
    _reseal_generation(run_dir, cases)
    problems = record.validate(run_dir, root)
    assert any(expected in p for p in problems), (label, problems)


def _flip_conflict_side(case) -> None:
    if case["case_id"] == "B-FC":
        for label in case["labels"]:
            if label.get("side") == "conflict":
                label["side"] = "governing"


def _add_quotable_value(case) -> None:
    if case["case_id"] == "B-ABQ":
        case["may_quote"]["chunks"][-1]["values"].append("30")


def _relabel(case) -> None:
    if case["case_id"] == "B-RH":
        case["expected"] = "answer"


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        (_flip_conflict_side, "case B-FC trial 1: its labels or their conflict sides are not"),
        (_add_quotable_value, "case B-ABQ trial 1: its may_quote chunks or values are not"),
        (_relabel, "case B-RH trial 1: its expected label, mix or features are not"),
    ],
    ids=["a conflict side flipped", "a quotable value added", "an expected label changed"],
)
def test_a_forged_record_of_the_current_golden_file_is_refused(tmp_path, change, expected):
    """S4, the orchestrator's decision (the class of S3-S2): a record whose dataset is the golden
    file as it stands has its behaviour fields derived again from that file, the answer key and
    the corpus, so a hand edit that moves a check (a side, a quotable value, the expected label)
    is refused even with its checks, results, report and hashes resealed. The same record, once
    the golden file has moved on, is history: its recorded fields are kept as they are."""
    from tests.generation_support import behaviour_run

    root, run_dir = behaviour_run(tmp_path)
    assert record.validate(run_dir, root) == []
    _, cases = read_run(run_dir)
    for case in cases:
        change(case)
    _reseal_generation(run_dir, cases)
    problems = record.validate(run_dir, root)
    assert any(p.startswith(expected) for p in problems), problems
    golden_file = root / "golden.jsonl"
    golden_file.write_text(golden_file.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    assert record.validate(run_dir, root) == []  # another dataset version: kept as recorded


S4_REPEAT = "20261019T174018Z-generation-local-ollama-dev-97011a7"
S4_DENSE_600 = "20261019T180529Z-retrieval-dense-600-dev-97011a7"


def _published_copy(tmp_path, run_id: str):
    import shutil

    run_dir = tmp_path / run_id
    shutil.copytree(ROOT / "runs" / "published" / run_id, run_dir)
    return run_dir


def _rescore(case, k: int) -> None:
    """A labelled case's flags and scores from its (edited) chunk ids, as a careful edit would."""
    ids = [r["chunk_id"] for r in case["retrieved"]]
    sets = [frozenset(label["chunk_ids"]) for label in case["labels"]]
    for r in case["retrieved"]:
        r["relevant"] = any(r["chunk_id"] in s for s in sets)
    for label, s in zip(case["labels"], sets, strict=True):
        label["found"] = bool(set(ids) & s)
    case.update(record.case_scores(ids, sets, k))


def test_a_forged_label_chunk_id_is_refused(tmp_path):
    """S4-J2, the criteria judge's edit (fix round 1; the user's answer: "Fix it now
    (Recommended)"). In a copy of a published S4 repeat, G-12 fails only cites_label; the chunk
    the model cited is added to its label (and to a group's last member), and the case is
    rescored, rechecked and resealed, which lifted the run from 14 to 15 of 27. The record still
    holds the golden file's current sha256, so each label is derived again from the corpus at the
    record's settings and the edit is refused."""
    run_dir = _published_copy(tmp_path, S4_REPEAT)
    assert record.validate(run_dir, ROOT) == []
    _, cases = read_run(run_dir)
    edited = 0
    for case in cases:
        if case["case_id"] == "G-12" and not case["checks"]["cites_label"] and case["cited_ids"]:
            extra, label = case["cited_ids"][0], case["labels"][0]
            assert extra not in label["chunk_ids"]
            label["chunk_ids"].append(extra)
            if "any_of" in label:
                label["any_of"][-1]["chunk_ids"].append(extra)
            _rescore(case, 5)
            edited += 1
    assert edited
    _reseal_generation(run_dir, cases)
    passing = {c["case_id"] for c in cases if c["kind"] == "behaviour"} - {
        c["case_id"] for c in cases if c["kind"] == "behaviour" and not c["checks"]["passed"]
    }
    assert "G-12" in passing  # the edit made G-12 pass every trial
    problems = record.validate(run_dir, ROOT)
    assert any(p.startswith("case G-12 trial ") and "chunk ids" in p for p in problems), problems


def test_a_forged_label_chunk_id_of_a_retrieval_run_at_another_chunk_size_is_refused(tmp_path):
    """The same for a retrieval record at chunk size 600, whose sections are chunked again from
    the corpus (the inventory snapshot holds the default size only): one more chunk in R-Q16's
    label, the case rescored and the record resealed, is refused."""
    run_dir = _published_copy(tmp_path, S4_DENSE_600)
    assert record.validate(run_dir, ROOT) == []
    _, cases = read_run(run_dir)
    case = next(c for c in cases if c["case_id"] == "R-Q16")
    extra = next(r["chunk_id"] for r in case["retrieved"] if not r["relevant"])
    case["labels"][0]["chunk_ids"].append(extra)
    reseal(run_dir, cases)
    problems = record.validate(run_dir, ROOT)
    assert any(p.startswith("case R-Q16 trial 1:") and "chunk ids" in p for p in problems), problems


def test_behaviour_checks_that_do_not_follow_from_the_fields_are_refused(tmp_path):
    """A behaviour case's checks are recomputed from its fields: a decision_label turned true on
    the S3 pattern (label answer on an abstain case), or a must_not_contain hidden, is caught even
    when the results, the report and the hashes were made to agree."""
    from tests.generation_support import Q_ABS, behaviour_run, reply

    pattern = reply("answer", "The documents do not say how many reset attempts.")
    root, run_dir = behaviour_run(tmp_path, {Q_ABS: pattern})
    _, cases = read_run(run_dir)
    for case in cases:
        if case["case_id"] == "B-ABS":
            assert case["checks"]["decision_label"] is False
            case["checks"]["decision_label"] = True
            case["checks"]["passed"] = all(
                v for k, v in case["checks"].items() if k != "passed" and k != "abstained"
            )
    _reseal_generation(run_dir, cases, recheck=False)
    problems = record.validate(run_dir, root)
    assert any("B-ABS" in p and "do not follow from the fields" in p for p in problems), problems


def test_a_generation_run_writes_a_valid_record(tmp_path):
    from tests.generation_support import fake_generation_run, generation_root

    root = generation_root(tmp_path)
    run_dir = fake_generation_run(root)
    assert record.validate(run_dir, root) == []
    manifest, cases = read_run(run_dir)
    assert manifest["run_id"] == "20261018T120000Z-generation-fake-dev-0123456"
    assert (manifest["suite"], manifest["provenance"], manifest["trials"]) == (
        "generation",
        "fake",
        2,
    )
    assert manifest["prompt"] == {"version": "answer-v1", "sha256": prompts.CURRENT.fingerprint()}
    guards = [
        "tenant",
        "input-limits",
        "injection",
        "register",
        "citations",
        "links",
        "secrets-pii",
        "prompt-leak",
    ]
    assert manifest["guards"] == guards  # S7: the default guard set
    assert [layer["name"] for layer in manifest["guard_set"]["layers"]] == [
        "instruction-scan",
        *guards,
    ]
    assert manifest["generator"]["model"] == "fake-echo"
    assert manifest["intervals"] == {"method": "wilson", "level": 0.95, "unit": "case"}
    assert "bootstrap" not in manifest
    # four dev retrieval questions and one probe, two trials each
    assert [(c["case_id"], c["trial"]) for c in cases] == [
        (q, t) for q in ("Q1", "Q2", "Q3", "Q4", "P-01") for t in (1, 2)
    ]
    probe = cases[-1]
    assert probe["kind"] == "probe"
    assert "labels" not in probe
    assert probe["canaries_of"] is None
    assert set(probe["checks"]) == {
        "status_ok",
        "model_citations_retrieved",
        "abstained",
        "no_value",
        "no_canary",
        "passed",
    }
    metrics = manifest["results"]["metrics"]
    assert set(metrics) == {
        "status_ok",
        "model_citations_retrieved",
        "probe_abstention",
        "citation_hit",
        "pass^2",
    }
    assert metrics["probe_abstention"]["n"] == 1
    assert metrics["citation_hit"]["n"] == 4
    assert metrics["status_ok"]["value"] == 1.0
    generation = manifest["results"]["generation"]
    assert generation["probes"] == [
        {
            "case_id": "P-01",
            "feature_ids": ["F-32"],
            "tenant": "tenant-a",
            "abstained": 0,
            "trials": 2,
        }
    ]
    assert generation["status_counts"]["ok"] == 10
    report = (run_dir / record.REPORT).read_text(encoding="utf-8")
    assert "it is not correctness" in report
    assert all(c["answer"] not in report for c in cases if c["answer"])


def _edit_case(run_dir, index, change):
    """Edit one case and reseal the record (checks, results, report and hashes made to agree),
    as a careful hand edit would."""
    from raglab.evals import generation_record
    from raglab.ingest.answer_key import canaries

    manifest, cases = read_run(run_dir)
    change(cases[index])
    for case in cases:
        if "checks" in case and all(f in case for f in ("status", "kind", "cited_ids", "conflict")):
            with contextlib.suppress(KeyError):
                case["checks"] = generation_record.case_checks(case, canaries(ROOT))
    with contextlib.suppress(KeyError, ValueError, TypeError):
        manifest["results"] = record.expected_results(manifest, cases)
    body = {k: v for k, v in manifest.items() if k != "files"}
    cases_bytes = record.cases_text(cases).encode()
    try:
        report_bytes = record.render(body, cases).encode()
    except (KeyError, ValueError, TypeError):
        report_bytes = (run_dir / record.REPORT).read_bytes()
    (run_dir / record.CASES).write_bytes(cases_bytes)
    (run_dir / record.REPORT).write_bytes(report_bytes)
    manifest["files"] = {
        record.CASES: record.sha256_bytes(cases_bytes),
        record.REPORT: record.sha256_bytes(report_bytes),
    }
    (run_dir / record.MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n")


@pytest.mark.parametrize(
    ("label", "change", "expected"),
    [
        ("no label", lambda c: c.pop("label"), "a generation case needs ['label']"),
        ("no status", lambda c: c.pop("status"), "needs ['status']"),
        ("no checks", lambda c: c.pop("checks"), "needs ['checks']"),
        (
            "unretrieved citation",
            lambda c: c.update(cited_ids=["B-PWD@1.0/3/1"]),
            "cites ids that were not retrieved: ['B-PWD@1.0/3/1']",
        ),
        (
            "unretrieved conflict",
            lambda c: c.update(conflict={"chunk_ids": ["A-MFA@1.0/4.1/1"], "note": "x"}),
            "cites ids that were not retrieved",
        ),
        (
            "text on a withheld answer",
            lambda c: c.update(status="unavailable", label="abstain", cited_ids=[]),
            "a unavailable answer is withheld",
        ),
        ("unknown label", lambda c: c.update(label="maybe"), "'maybe' is not one of"),
        ("retrieval fields on a probe", lambda c: c.update(hit=1), "a probe case has no ['hit']"),
        (
            "a citations event on an ok answer",
            lambda c: c.update(
                guard_events=[{"guard": "citations", "stage": "output", "reason": "cited X"}]
            ),
            "the citation validator fired, so the answer is blocked",
        ),
    ],
)
def test_a_broken_generation_case_is_refused(tmp_path, label, change, expected):
    from tests.generation_support import fake_generation_run, generation_root

    root = generation_root(tmp_path)
    run_dir = fake_generation_run(root)
    index = -1 if "probe" in label else 0
    _edit_case(run_dir, index, change)
    problems = record.validate(run_dir, root)
    assert any(expected in p for p in problems), (label, problems)


def test_edited_checks_or_a_missing_trial_are_refused(tmp_path):
    from tests.generation_support import fake_generation_run, generation_root

    root = generation_root(tmp_path)
    run_dir = fake_generation_run(root)
    cases_path = run_dir / record.CASES
    lines = cases_path.read_text(encoding="utf-8").splitlines()
    case = json.loads(lines[0])
    case["checks"]["passed"] = not case["checks"]["passed"]
    cases_path.write_text("\n".join([json.dumps(case), *lines[1:]]) + "\n")
    problems = record.validate(run_dir, root)
    assert any("do not follow from the fields" in p for p in problems), problems
    cases_path.write_text("\n".join(lines[1:]) + "\n")
    problems = record.validate(run_dir, root)
    assert any("case Q1: trials [2], not 1 to 2" in p for p in problems), problems


def test_fields_of_one_suite_are_refused_in_the_other(tmp_path):
    from tests.generation_support import fake_generation_run, generation_root

    root = generation_root(tmp_path)
    retrieval_dir = fake_run(root)
    rewrite(retrieval_dir / record.MANIFEST, lambda m: m.update(guards=["tenant"]))
    assert any("no generation fields" in p for p in record.validate(retrieval_dir, root))
    generation_dir = fake_generation_run(root)
    rewrite(generation_dir / record.MANIFEST, lambda m: m.pop("prompt"))
    assert any(
        "a generation run needs ['prompt']" in p for p in record.validate(generation_dir, root)
    )


def test_a_retrieval_case_without_its_scores_is_still_refused(tmp_path):
    """The schema no longer requires the four retrieval fields (a probe has none); validate
    requires them for every case of a retrieval run."""
    root = lab_root(tmp_path)
    run_dir = fake_run(root)
    _edit_case(run_dir, 0, lambda c: c.pop("recall"))
    problems = record.validate(run_dir, root)
    assert any("a retrieval case needs ['recall']" in p for p in problems), problems


def test_a_generation_answer_citing_another_tenants_chunk_is_refused(tmp_path):
    """The register check (S2 judge D3) covers what a generation case cites: a tenant B chunk
    cited by a tenant A case is refused even when it is also listed as retrieved."""
    from tests.generation_support import fake_generation_run, generation_root

    root = generation_root(tmp_path)
    run_dir = fake_generation_run(root)

    def cite_b(case):
        case["retrieved"][0]["chunk_id"] = "B-PWD@1.0/3/1"
        case["cited_ids"] = ["B-PWD@1.0/3/1"]

    _edit_case(run_dir, 0, cite_b)
    problems = record.validate(run_dir, root)
    assert any("B-PWD@1.0/3/1 is tenant-b, which it cannot see" in p for p in problems), problems


def test_a_record_with_unavailable_trials_marked_complete_is_refused(tmp_path):
    """Judge S3-J10: one trial without a reply (an HTTP error, not a timeout); the record, edited
    to partial false and resealed, is refused."""
    from raglab.adapters.fake import FakeChat, echo
    from raglab.core.types import ChatUnavailable
    from tests.generation_support import fake_generation_run, generation_root

    calls: list[int] = []

    def flaky(request):
        calls.append(1)
        if len(calls) == 1:
            raise ChatUnavailable("HTTP 503 from /v1/chat/completions")
        return echo(request)

    root = generation_root(tmp_path)
    run_dir = fake_generation_run(root, FakeChat(flaky))
    manifest, cases = read_run(run_dir)
    assert [c["status"] for c in cases].count("unavailable") == 1
    manifest["partial"] = False
    manifest["totals"].pop("stopped", None)
    body = {k: v for k, v in manifest.items() if k != "files"}
    report = record.render(body, cases).encode()
    (run_dir / record.REPORT).write_bytes(report)
    manifest["files"][record.REPORT] = record.sha256_bytes(report)
    (run_dir / record.MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n")
    problems = record.validate(run_dir, root)
    assert any("1 trial(s) unavailable but partial is false" in p for p in problems), problems
