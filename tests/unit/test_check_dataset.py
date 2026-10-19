"""S4 AC3: `raglab check-dataset` is a hard stop. Each of its ten rules is broken on a planted copy
of a valid golden set (tests/dataset_support.py: the committed retrieval questions and 40
behaviour cases from the plan's draft) and the check exits 1 naming the case and the rule; the
valid copy and the committed file exit 0. Every `raglab eval` and `raglab gate` runs it first and
stops before any model, embedder or ingestion starts."""

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from raglab.__main__ import main
from raglab.evals import dataset_check
from tests.conftest import ROOT
from tests.dataset_support import CASES, edited, sec, write_dataset

pytestmark = pytest.mark.unit
COMMITTED = ROOT / "datasets" / "golden.v1.jsonl"


def problems(path: Path) -> list[str]:
    return [str(p) for p in dataset_check.check(ROOT, path).problems]


def has(found: list[str], case: str, rule: int, text: str = "") -> bool:
    head = f"{case}: rule {rule} ({dataset_check.RULES[rule]}): "
    return any(p.startswith(head) and text in p for p in found)


def test_the_valid_copy_and_the_committed_file_pass(tmp_path, capsys):
    path = write_dataset(tmp_path)
    report = dataset_check.check(ROOT, path)
    assert report.problems == ()
    assert (report.retrieval, report.behaviour) == (34, 40)
    assert main(["check-dataset", "--dataset", str(path), "--root", str(ROOT)]) == 0
    assert "passes (34 retrieval questions, 40 behaviour cases" in capsys.readouterr().out
    assert main(["check-dataset", "--root", str(ROOT)]) == 0
    out = capsys.readouterr().out.splitlines()
    assert len(out) == 1
    assert out[0].startswith(
        "check-dataset: datasets/golden.v1.jsonl passes (34 retrieval questions, 40 behaviour"
    )


def test_the_committed_datasheet_records_the_committed_file():
    """Rule 10 on the committed pair: the datasheet's latest version line is v1.1 and carries the
    golden file's sha256; one byte more in the file and the rule fails (the next test's copy)."""
    text = (ROOT / "datasets" / "DATASHEET.md").read_text(encoding="utf-8")
    latest = dataset_check.latest_version(text)
    assert latest is not None
    assert latest[0] == "v1.1"
    assert hashlib.sha256(COMMITTED.read_bytes()).hexdigest() in latest[1]


def test_a_golden_file_edited_without_a_new_version_line_fails_rule_10(tmp_path):
    copy = tmp_path / COMMITTED.name
    copy.write_bytes(COMMITTED.read_bytes() + b"\n")
    (tmp_path / "DATASHEET.md").write_bytes((ROOT / "datasets" / "DATASHEET.md").read_bytes())
    found = problems(copy)
    assert found == [
        f"{copy.name}: rule 10 (version): the latest version line of DATASHEET.md (v1.1) does "
        f"not carry the file's sha256 {hashlib.sha256(copy.read_bytes()).hexdigest()}"
    ]


def check_planted(tmp_path: Path, cases: list[dict[str, Any]], case: str, rule: int, text: str):
    path = write_dataset(tmp_path, cases)
    found = problems(path)
    assert has(found, case, rule, text), found
    return found


# ---------------------------------------------------------------- rule 1


def test_rule_1_lines_that_do_not_parse(tmp_path):
    path = write_dataset(tmp_path)
    lines = path.read_text(encoding="utf-8").splitlines()
    bad = [
        "{not json",
        json.dumps({**CASES[0], "id": "G-01"}),  # the id again
        json.dumps({**CASES[1], "id": "G-90", "mix": "riddle"}),
        json.dumps({**CASES[2], "id": "G-91", "expected": "maybe"}),
        json.dumps({**CASES[3], "id": "G-92", "split": "train"}),
        json.dumps({**CASES[4], "id": "G-93", "question": CASES[5]["question"]}),  # same tenant
    ]
    path.write_text("\n".join([*lines, *bad]) + "\n", encoding="utf-8")
    found = problems(path)
    assert has(found, f"golden.v1.jsonl:{len(lines) + 1}", 1, "not JSON")
    assert has(found, "G-01", 1, "the id is used twice")
    assert has(found, "G-90", 1, "mix 'riddle' is not one of")
    assert has(found, "G-91", 1, "expected 'maybe' is not one of")
    assert has(found, "G-92", 1, "split 'train' is not one of")
    assert has(found, "G-93", 1, "it repeats the question of G-06 for tenant-a")


def test_rule_1_the_same_question_as_two_tenants_is_two_cases(tmp_path):
    """P-01 and P-02 ask the same words as tenant A and tenant B (S3): no repeat."""
    path = write_dataset(tmp_path)
    assert not [p for p in problems(path) if "repeats the question" in p]
    [p01] = [c for c in CASES if c["id"] == "P-01"]
    [p02] = [c for c in CASES if c["id"] == "P-02"]
    assert p01["question"] == p02["question"]
    assert p01["tenant"] != p02["tenant"]


# ---------------------------------------------------------------- rule 2


def test_rule_2_labels_and_features(tmp_path):
    cases = edited("G-03", relevant=[sec("A-LIFE", "6.2")])  # no such section
    cases = edited("G-14", cases=cases, relevant=[sec("A-MFA", "7.1")])  # tenant A, asked as B
    cases = edited("G-06", cases=cases, feature_ids=["F-24", "F-99"])
    cases = edited(
        "G-01",
        cases=cases,
        relevant=[{"any_of": [sec("A-PWD-V2", "4.1"), sec("A-FAQ", "Q12")]}],
    )
    found = check_planted(tmp_path, cases, "G-03", 2, "A-LIFE 6.2 has no chunk in the inventory")
    assert has(found, "G-14", 2, "A-MFA 7.1 is tenant-a, which tenant-b cannot see")
    assert has(found, "G-06", 2, "feature F-99 is not in the answer key")
    assert has(found, "G-01", 2, "group member A-FAQ Q12 is not an answer-key location of F-01")


# ---------------------------------------------------------------- rules 3 and 4


def test_rule_3_answer_shape(tmp_path):
    cases = edited("G-02", reference_answer=None)
    cases = edited("G-04", cases=cases, relevant=[])
    cases = edited("G-31", cases=cases, relevant=[sec("A-PWD-V2", "4.1"), sec("A-PWD-V1", "4.1")])
    found = check_planted(tmp_path, cases, "G-02", 3, "needs a reference answer")
    assert has(found, "G-04", 3, "needs a labelled section")
    assert has(found, "G-31", 3, "A-PWD-V1 4.1, the superseded or external side of F-05")


def test_rule_4_abstain_shape(tmp_path):
    cases = edited("G-25", relevant=[sec("B-PWD", "3.1")], reference_answer="x")
    cases = edited("G-27", cases=cases, feature_ids=["F-40"])  # its proof covers tenant B only
    cases = edited("G-28", cases=cases, may_quote=sec("B-PWD", "3.1"))  # tenant B, not shared
    cases = edited("G-24", cases=cases, may_quote=sec("X-NIST", "3.1.1.2"), expected="answer")
    found = check_planted(tmp_path, cases, "G-25", 4, "an abstain case labels no section")
    assert has(found, "G-25", 4, "an abstain case has no reference answer")
    assert has(found, "G-27", 4, "F-40 has no silence proof covering tenant-a")
    assert has(found, "G-28", 4, "may_quote B-PWD 3.1 is not a shared reference section")
    assert has(found, "G-24", 4, "may_quote is for abstain cases only")


# ---------------------------------------------------------------- rules 5 to 7


def test_rule_5_conflict_shape(tmp_path):
    cases = edited("G-29", relevant=[sec("A-PWD-V2", "4.4")])  # no conflict side
    cases = edited("G-22", cases=cases, relevant=[sec("X-NIST", "3.1.1.2")])  # no governing
    cases = edited(
        "G-30",
        cases=cases,
        relevant=[{"any_of": [sec("A-PWD-V2", "4.4"), sec("A-PWD-V1", "4.3")]}],
    )
    found = check_planted(tmp_path, cases, "G-29", 5, "lack every conflict side of F-04")
    assert has(found, "G-22", 5, "lack the governing section of F-08")
    assert has(found, "G-30", 5, "a group mixes the governing side and a conflict side")


def test_rule_6_refusal_shapes(tmp_path):
    cases = edited("G-13", relevant=[sec("A-PWD-V2", "4.1")])  # not F-42's route
    cases = edited("G-12", cases=cases, expected="refuse-and-help")  # F-56 must not be blocked
    found = check_planted(tmp_path, cases, "G-13", 6, "labels no route section")
    assert has(found, "G-12", 6, "F-56 must not be blocked")
    assert has(found, "G-12", 6, "its first feature F-56 is not a refuse-and-help feature")


def test_rule_7_the_expected_label_is_the_first_features(tmp_path):
    cases = edited("G-05", expected="refuse-and-help")
    check_planted(tmp_path, cases, "G-05", 7, "the clean-run label of F-15 is answer")


# ---------------------------------------------------------------- rule 8


def test_rule_8_no_planted_string_or_other_tenant_canary_in_a_question(tmp_path):
    from raglab.ingest.answer_key import canaries, must_not_contain

    phrase = must_not_contain(ROOT)["F-47"][-1]  # a plain attack phrase
    canary = canaries(ROOT)["tenant-a"][0]  # tenant A's name
    cases = edited("G-06", question=f"Is it true that {phrase.upper()}?")
    cases = edited("G-14", cases=cases, question=f"Does {canary.lower()} do it too?")
    found = check_planted(tmp_path, cases, "G-06", 8, "F-47's")
    assert has(found, "G-14", 8, "a canary of tenant-a")


# ---------------------------------------------------------------- rules 9 and 10


def test_rule_9_the_mix_the_test_split_and_the_probes(tmp_path):
    """AC1's breaks: one case's mix moved from single-chunk to multi-chunk (still 40 cases); the
    test-split refuse-and-help cases moved to dev; and an S3 probe moved to test."""
    cases = edited("G-02", mix="multi-chunk")
    found = check_planted(tmp_path, cases, "golden.v1.jsonl", 9, "14 single-chunk case(s)")
    assert has(found, "golden.v1.jsonl", 9, "9 multi-chunk case(s), the mix asks for 8")
    assert len(found) == 2, found
    moved = edited("G-34", cases=edited("G-23", split="dev"), split="dev")
    found = check_planted(tmp_path / "b", moved, "golden.v1.jsonl", 9, "no refuse-and-help case")
    probe = edited("P-02", split="test")
    check_planted(tmp_path / "c", probe, "P-02", 9, "an S3 probe stays in dev")
    gone = [c for c in CASES if c["id"] != "P-03"]
    check_planted(tmp_path / "d", gone, "golden.v1.jsonl", 9, "the S3 probe P-03 is not")


def test_rule_10_the_datasheets_latest_version_line_carries_the_sha256(tmp_path):
    stale = (
        "| Version | sha256 |\n|---|---|\n| v1 | x |\n| v1.1 | " + "a" * 64 + " |\n"
    )  # a sha256, but another file's
    path = write_dataset(tmp_path, datasheet=stale)
    assert has(problems(path), "golden.v1.jsonl", 10, "(v1.1) does not carry the file's sha256")
    path = write_dataset(tmp_path / "b", datasheet="# no versions here\n")
    assert has(problems(path), "golden.v1.jsonl", 10, "has no version line")
    path = write_dataset(tmp_path / "c")
    (path.parent / "DATASHEET.md").unlink()
    assert has(problems(path), "golden.v1.jsonl", 10, "no datasheet")


def test_the_latest_version_is_the_highest_one_listed():
    text = "- **v1** (S2): x\n| v2 | y |\n| v1.1 | z |\nVersion v9 in prose is not a line.\n"
    assert dataset_check.latest_version(text) == ("v2", "| v2 | y |")
    assert dataset_check.latest_version("nothing") is None


# ---------------------------------------------------------------- the CLI and the hard stop


def test_the_cli_exits_1_naming_the_case_and_the_rule(tmp_path, capsys):
    path = write_dataset(tmp_path, edited("G-03", relevant=[sec("A-LIFE", "6.2")]))
    assert main(["check-dataset", "--dataset", str(path), "--root", str(ROOT)]) == 1
    out = capsys.readouterr().out
    assert "G-03: rule 2 (labels and features): labelled section A-LIFE 6.2 has no chunk" in out
    assert "fails 1 check(s)" in out


@pytest.mark.parametrize("suite", ["retrieval", "generation"])
def test_every_eval_and_gate_runs_it_first_and_stops(tmp_path, monkeypatch, capsys, suite):
    """A broken dataset stops `raglab eval` (both suites) and `raglab gate` before the embedder,
    the model or the ingestion is built: those are patched to fail the test if reached."""
    from raglab.adapters import factory
    from raglab.generate import assemble

    def reached(*args: object, **kwargs: object) -> None:
        raise AssertionError("the run started before check-dataset stopped it")

    monkeypatch.setattr(factory, "embedder", reached)
    monkeypatch.setattr(assemble, "assemble", reached)
    path = write_dataset(tmp_path, edited("G-29", relevant=[sec("A-PWD-V2", "4.4")]))
    source = ROOT / "config" / ("retrieval-dense.toml" if suite == "retrieval" else "fake.toml")
    config = tmp_path / source.name
    config.write_text(
        source.read_text(encoding="utf-8").replace("datasets/golden.v1.jsonl", str(path)),
        encoding="utf-8",
    )
    commands = [["eval", "--suite", suite, "--config", str(config), "--root", str(ROOT)]]
    if suite == "retrieval":
        commands.append(["gate", "--config", str(config), "--root", str(ROOT)])
    for command in commands:
        assert main(command) == 1, command
        err = capsys.readouterr().err
        assert "check-dataset stopped the run" in err
        assert "G-29: rule 5 (conflict shape)" in err
