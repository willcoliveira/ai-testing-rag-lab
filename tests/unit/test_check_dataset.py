"""S4 AC3 and S4b GV4: `raglab check-dataset` is a hard stop, per golden file and per version.
Each of its ten rules is broken on a planted copy of a valid golden set (tests/dataset_support.py:
v1.1, the committed retrieval questions and 40 behaviour cases from the S4 plan's draft; v2,
golden set v1.1's lines and 80 planted cases split by scripts/split_golden.py) and the check
exits 1 naming the case and the rule; the valid copies and the committed files exit 0. Rules 9
and 10 hold each file to its own version, read from the datasheet's Maintenance row for the file.
Every `raglab eval` and `raglab gate` runs it first on its config's file and stops before any
model, embedder or ingestion starts."""

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pytest

from raglab.__main__ import main
from raglab.evals import dataset_check
from tests.conftest import ROOT
from tests.dataset_support import (
    CASES,
    HEADER,
    V2_CASES,
    edited,
    edited_lines,
    maintenance,
    sec,
    v2_lines,
    write_dataset,
    write_v2,
)

pytestmark = pytest.mark.unit
COMMITTED = ROOT / "datasets" / "golden.v1.jsonl"
DATASHEET = ROOT / "datasets" / "DATASHEET.md"


def problems(path: Path) -> list[str]:
    return [str(p) for p in dataset_check.check(ROOT, path).problems]


def has(found: list[str], case: str, rule: int, text: str = "") -> bool:
    head = f"{case}: rule {rule} ({dataset_check.RULES[rule]}): "
    return any(p.startswith(head) and text in p for p in found)


def test_the_valid_copies_and_the_committed_files_pass(tmp_path, capsys):
    path = write_dataset(tmp_path / "v1")
    report = dataset_check.check(ROOT, path)
    assert report.problems == ()
    assert (report.retrieval, report.behaviour, report.version) == (34, 40, "v1.1")
    path2 = write_v2(tmp_path / "v2")
    report = dataset_check.check(ROOT, path2)
    assert report.problems == ()
    assert (report.retrieval, report.behaviour, report.version) == (34, 120, "v2")
    assert main(["check-dataset", "--dataset", str(path), "--root", str(ROOT)]) == 0
    assert "passes as v1.1 (34 retrieval questions, 40 behaviour cases" in capsys.readouterr().out
    assert main(["check-dataset", "--dataset", str(path2), "--root", str(ROOT)]) == 0
    assert "passes as v2 (34 retrieval questions, 120 behaviour cases" in capsys.readouterr().out
    # with no --dataset, every golden file of the repo, one verdict line each
    golden = sorted((ROOT / "datasets").glob("golden.v*.jsonl"))
    assert COMMITTED in golden
    assert main(["check-dataset", "--root", str(ROOT)]) == 0
    out = capsys.readouterr().out.splitlines()
    assert [line.split(" passes as ")[0] for line in out] == [
        f"check-dataset: datasets/{p.name}" for p in golden
    ]
    assert out[0] == (
        "check-dataset: datasets/golden.v1.jsonl passes as v1.1 (34 retrieval questions, 40 "
        f"behaviour cases, sha256 {hashlib.sha256(COMMITTED.read_bytes()).hexdigest()[:12]})"
    )


def test_both_files_are_checked_and_one_failing_file_fails_the_command(tmp_path, capsys):
    v1 = write_dataset(tmp_path / "v1")
    v2 = write_v2(tmp_path / "v2", edited_lines(v2_lines(), "G-38", mix="multi-chunk"))
    assert main(["check-dataset", "--dataset", str(v1), "--dataset", str(v2)]) == 1
    out = capsys.readouterr().out
    assert f"check-dataset: {v1} passes as v1.1" in out
    assert "golden.v2.jsonl: rule 9 (mix): 44 single-chunk case(s), the mix asks for 45" in out
    assert f"check-dataset: {v2} fails 2 check(s)" in out


def test_the_committed_datasheet_records_the_committed_v1_file():
    """Rule 10 on the committed pair: the latest Maintenance row for golden.v1.jsonl is v1.1 and
    carries the file's sha256; one byte more in the file and the rule fails (the next test)."""
    row = dataset_check.latest_row(COMMITTED)
    assert isinstance(row, dataset_check.VersionRow)
    assert row.version == "v1.1"
    assert row.sha256 == hashlib.sha256(COMMITTED.read_bytes()).hexdigest()


def test_a_golden_file_edited_without_a_new_version_line_fails_rule_10(tmp_path):
    copy = tmp_path / COMMITTED.name
    copy.write_bytes(COMMITTED.read_bytes() + b"\n")
    (tmp_path / "DATASHEET.md").write_bytes(DATASHEET.read_bytes())
    found = problems(copy)
    assert found == [
        f"{copy.name}: rule 10 (version): the latest version line of DATASHEET.md for "
        f"{copy.name} (v1.1) does not carry the file's sha256 "
        f"{hashlib.sha256(copy.read_bytes()).hexdigest()}"
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


def test_rule_1_in_v2_a_new_case_given_an_existing_id_or_no_split(tmp_path):
    """GV1's break: a new case given an existing id (G-26's) is named by rule 1; and a case left
    without a split (the script not run) does not parse."""
    reused = edited_lines(v2_lines(), "G-117", id="G-26")
    assert has(problems(write_v2(tmp_path / "a", reused)), "G-26", 1, "the id is used twice")
    unsplit = v2_lines(split=False)
    found = problems(write_v2(tmp_path / "b", unsplit))
    assert has(found, "G-38", 1, "split must be a non-empty string, got None")


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


# ---------------------------------------------------------------- rule 9: v1.1


def test_rule_9_v1_1_the_mix_the_test_split_and_the_probes(tmp_path):
    """S4 AC1's breaks, kept for v1.1: one case's mix moved from single-chunk to multi-chunk
    (still 40 cases); the test-split refuse-and-help cases moved to dev; and an S3 probe moved to
    test or dropped."""
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


def test_rule_9_v1_1_asks_for_no_floor_and_no_tenant_test_case(tmp_path):
    """v1.1 keeps S4's rule 9 only: its committed file has no tenant B test case under some of
    tenant B's labels and fewer cases than v2's floors, and it passes."""
    cases = edited("G-15", split="dev")  # tenant B's only test answer
    assert not problems(write_dataset(tmp_path, cases))


# ---------------------------------------------------------------- rule 9: v2 (S4b GV4)


def v2_problems(tmp_path: Path, lines: list[str], name: str = "v2") -> list[str]:
    return problems(write_v2(tmp_path / name, lines))


def ids_where(lines: list[str], **fields: Any) -> list[str]:
    rows = [json.loads(line) for line in lines]
    return [r["id"] for r in rows if all(r.get(k) == v for k, v in fields.items())]


def test_rule_9_v2_a_case_moved_to_another_slot_names_both(tmp_path):
    """GV4's break: in v2, one single-chunk case made multi-chunk names both slots."""
    found = v2_problems(tmp_path, edited_lines(v2_lines(), "G-38", mix="multi-chunk"))
    assert found == [  # write_v2's row carries the edited file's sha256: rule 10 passes
        "golden.v2.jsonl: rule 9 (mix): 44 single-chunk case(s), the mix asks for 45",
        "golden.v2.jsonl: rule 9 (mix): 25 multi-chunk case(s), the mix asks for 24",
    ]


def test_rule_9_v2_every_tenant_b_test_case_of_a_label_moved_to_dev_names_the_label(tmp_path):
    """GV4's break: every tenant B test case of one label moved to dev, the label named; every
    tenant B test case moved to dev, the tenant named too."""
    lines = v2_lines()
    tested = ids_where(lines, tenant="tenant-b", split="test", expected="abstain")
    assert tested
    for case_id in tested:
        lines = edited_lines(lines, case_id, split="dev")
    found = v2_problems(tmp_path, lines)
    assert has(found, "golden.v2.jsonl", 9, "no tenant-b abstain case is in the test split")
    assert [p for p in found if "rule 9" in p] == [
        "golden.v2.jsonl: rule 9 (mix): no tenant-b abstain case is in the test split"
    ]
    for case_id in ids_where(lines, tenant="tenant-b", split="test"):
        lines = edited_lines(lines, case_id, split="dev")
    found = v2_problems(tmp_path, lines, "all")
    assert has(found, "golden.v2.jsonl", 9, "no tenant-b case is in the test split")
    assert has(found, "golden.v2.jsonl", 9, "no tenant-b answer case is in the test split")


@pytest.mark.parametrize(
    ("change", "message"),
    [
        # three must-not-block cases built on F-10, a table value at the same section, instead
        (
            {"G-45": {"feature_ids": ["F-10"]}, "G-46": {"feature_ids": ["F-10"]},
             "G-47": {"feature_ids": ["F-10"]}},
            "6 must-not-block case(s), v2 asks for at least 8",
        ),
        (
            {"G-84": {"may_quote": None}, "G-85": {"may_quote": None}},
            "1 abstain case(s) with may_quote, v2 asks for at least 3",
        ),
        (
            {"G-93": {"tenant": "tenant-a"}, "G-94": {"tenant": "tenant-a"}},
            "27 tenant-b case(s), v2 asks for at least 28",
        ),
    ],
)  # fmt: skip
def test_rule_9_v2_a_floor_one_case_short_is_named(tmp_path, change, message):
    lines = v2_lines()
    for case_id, fields in change.items():
        row = json.loads(next(line for line in lines if json.loads(line)["id"] == case_id))
        row = {k: v for k, v in {**row, **fields}.items() if v is not None}
        lines = [json.dumps(row) if json.loads(t)["id"] == case_id else t for t in lines]
    found = v2_problems(tmp_path, lines)
    assert [p for p in found if "rule 9" in p] == [f"golden.v2.jsonl: rule 9 (mix): {message}"]
    assert [p for p in found if "rule 9" not in p and "rule 10" not in p] == []


def test_rule_9_the_version_comes_from_the_files_row(tmp_path):
    """The v1.1 copy held to v2 by its row meets v2's contract nowhere; the v2 copy held to v1.1
    meets v1.1's mix nowhere; a version with no contract is named."""
    path = write_dataset(tmp_path / "a")
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    (path.parent / "DATASHEET.md").write_text(maintenance(("v2", path.name, sha)), "utf-8")
    found = problems(path)
    for text in (
        "15 single-chunk case(s), the mix asks for 45",
        "25 answer case(s), v2 asks for at least 55",
        "9 abstain case(s), v2 asks for at least 24",
        "3 flag-conflict case(s), v2 asks for at least 12",
        "3 refuse-and-help case(s), v2 asks for at least 14",
        "3 must-not-block case(s), v2 asks for at least 8",  # the fixture's G-21 is on F-55
        "1 abstain case(s) with may_quote, v2 asks for at least 3",
        "8 tenant-b case(s), v2 asks for at least 28",
    ):
        assert has(found, path.name, 9, text), (text, found)
    assert not has(found, path.name, 9, "test split")  # tenant B's two labels are tested
    assert not has(found, path.name, 10)
    path2 = write_v2(tmp_path / "b")
    sha2 = hashlib.sha256(path2.read_bytes()).hexdigest()
    (path2.parent / "DATASHEET.md").write_text(maintenance(("v1.1", path2.name, sha2)), "utf-8")
    found = problems(path2)
    assert has(found, path2.name, 9, "45 single-chunk case(s), the mix asks for 15")
    assert not has(found, path2.name, 9, "asks for at least")
    (path2.parent / "DATASHEET.md").write_text(maintenance(("v1.2", path2.name, sha2)), "utf-8")
    assert problems(path2) == [
        "golden.v2.jsonl: rule 9 (mix): v1.2 has no contract in check-dataset (it knows v1.1, v2)"
    ]


def test_rule_9_v2_the_s3_probes_stay_in_dev(tmp_path):
    found = v2_problems(tmp_path, edited_lines(v2_lines(), "P-02", split="test"))
    assert has(found, "P-02", 9, "an S3 probe stays in dev")


def test_the_planted_v2_cases_meet_v2_without_their_v1_1_neighbours():
    """The planted cases are 80, from G-38, with no split until the script assigns one."""
    assert [c["id"] for c in V2_CASES] == [f"G-{n}" for n in range(38, 118)]
    assert all("split" not in c for c in V2_CASES)


# ---------------------------------------------------------------- rule 10


def test_rule_10_the_latest_row_for_the_file_carries_the_sha256(tmp_path):
    stale = maintenance(("v1", "golden.v1.jsonl", "x"), ("v1.1", "golden.v1.jsonl", "a" * 64))
    path = write_dataset(tmp_path, datasheet=stale)  # a sha256, but another file's
    assert has(problems(path), "golden.v1.jsonl", 10, "for golden.v1.jsonl (v1.1) does not carry")
    path = write_dataset(tmp_path / "b", datasheet="# no versions here\n")
    assert has(problems(path), "golden.v1.jsonl", 10, "has no version line")
    path = write_dataset(tmp_path / "c")
    (path.parent / "DATASHEET.md").unlink()
    assert has(problems(path), "golden.v1.jsonl", 10, "no datasheet")
    other = maintenance(("v2", "golden.v2.jsonl", "a" * 64))
    path = write_dataset(tmp_path / "d", datasheet=other)
    assert problems(path) == [
        "golden.v1.jsonl: rule 10 (version): no version line of DATASHEET.md's Maintenance table "
        "names golden.v1.jsonl, so the file has no version and rule 9 no contract"
    ]


def test_rule_10_each_file_is_held_to_its_own_rows(tmp_path):
    """Two files beside one datasheet: each passes on its own row, and an edit of one fails only
    that one."""
    v2 = write_v2(tmp_path)
    v1 = tmp_path / "golden.v1.jsonl"
    v1.write_bytes(COMMITTED.read_bytes())
    assert problems(v1) == []
    assert problems(v2) == []
    v1.write_bytes(COMMITTED.read_bytes() + b"\n")
    assert has(problems(v1), "golden.v1.jsonl", 10, "for golden.v1.jsonl (v1.1)")
    assert problems(v2) == []


def test_the_versions_are_read_from_the_maintenance_tables_rows_only():
    """A version in prose, in another section's table or in a second table of the Maintenance
    section is no row; the File column names each row's file; bold versions are versions."""
    sha = "b" * 64
    text = (
        "# Datasheet\n\nVersion v9 in prose.\n\n## Collection\n\n"
        "| Version | sha256 |\n|---|---|\n| v8 | `" + "c" * 64 + "` |\n\n"
        "## Maintenance\n\n"
        + HEADER
        + "| v1 | d | S2 | `golden.v1.jsonl` | x | `"
        + "0" * 64
        + "` |\n| **v1.1** | d | S4 | `golden.v1.jsonl` | x | `"
        + sha
        + "` |\n"
        "| v2 | d | S4b | `golden.v2.jsonl` | x | `" + "e" * 64 + "` |\n\n"
        "Then prose.\n\n| v7 | a second table |\n\n## Known limits\n\n| v6 | x |\n"
    )
    rows = dataset_check.maintenance_rows(text)
    assert [(r.version, r.file) for r in rows] == [
        ("v1", "golden.v1.jsonl"),
        ("v1.1", "golden.v1.jsonl"),
        ("v2", "golden.v2.jsonl"),
    ]
    assert rows[1].sha256 == sha
    assert rows[1].number == (1, 1)
    assert dataset_check.maintenance_rows("no table") == []


def test_the_s4_table_without_a_file_column_is_the_checked_files(tmp_path):
    """Until the datasheet gains its File column (the integration of v2's cases), the S4 table
    has none, and each of its rows is the checked file's, as before S4b: the committed datasheet
    reads so today (developer choice 1)."""
    path = write_dataset(tmp_path)
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    legacy = (
        "## Maintenance\n\n| Version | Date | Stage | What changed | sha256 of golden.v1.jsonl |\n"
        f"|---|---|---|---|---|\n| v1 | d | S2 | x | `{'0' * 64}` |\n"
        f"| v1.1 | d | S4 | x | `{sha}` |\n"
    )
    (path.parent / "DATASHEET.md").write_text(legacy, encoding="utf-8")
    assert problems(path) == []
    assert [r.file for r in dataset_check.maintenance_rows(legacy)] == [None, None]
    committed = dataset_check.maintenance_rows(DATASHEET.read_text(encoding="utf-8"))
    assert {r.file for r in committed} <= {None, "golden.v1.jsonl", "golden.v2.jsonl"}


# ---------------------------------------------------------------- the CLI and the hard stop


def test_the_cli_exits_1_naming_the_case_and_the_rule(tmp_path, capsys):
    path = write_dataset(tmp_path, edited("G-03", relevant=[sec("A-LIFE", "6.2")]))
    assert main(["check-dataset", "--dataset", str(path), "--root", str(ROOT)]) == 1
    out = capsys.readouterr().out
    assert "G-03: rule 2 (labels and features): labelled section A-LIFE 6.2 has no chunk" in out
    assert "fails 1 check(s)" in out


def planted_config(source: Path, path: Path, directory: Path) -> Path:
    """The committed config with its dataset path set to the planted file, whatever golden file
    it names (v1.1 until the freeze F, v2 from it)."""
    text = source.read_text(encoding="utf-8")
    pattern = r'^path = "datasets/golden\.v\d+\.jsonl"$'
    planted, count = re.subn(pattern, f'path = "{path}"', text, flags=re.M)
    assert count == 1, source
    config = directory / source.name
    config.write_text(planted, encoding="utf-8")
    return config


@pytest.mark.parametrize("version", ["v1.1", "v2"])
@pytest.mark.parametrize("suite", ["retrieval", "generation"])
def test_every_eval_and_gate_runs_it_first_and_stops(tmp_path, monkeypatch, capsys, suite, version):
    """A broken dataset stops `raglab eval` (both suites) and `raglab gate` before the embedder,
    the model or the ingestion is built: those are patched to fail the test if reached. A v1.1
    copy breaks rule 5; a v2 copy breaks v2's mix."""
    from raglab.adapters import factory
    from raglab.generate import assemble

    def reached(*args: object, **kwargs: object) -> None:
        raise AssertionError("the run started before check-dataset stopped it")

    monkeypatch.setattr(factory, "embedder", reached)
    monkeypatch.setattr(assemble, "assemble", reached)
    if version == "v1.1":
        path = write_dataset(tmp_path, edited("G-29", relevant=[sec("A-PWD-V2", "4.4")]))
        expected = "G-29: rule 5 (conflict shape)"
    else:
        path = write_v2(tmp_path, edited_lines(v2_lines(), "G-38", mix="multi-chunk"))
        expected = "golden.v2.jsonl: rule 9 (mix): 44 single-chunk case(s)"
    source = ROOT / "config" / ("retrieval-dense.toml" if suite == "retrieval" else "fake.toml")
    config = planted_config(source, path, tmp_path)
    commands = [["eval", "--suite", suite, "--config", str(config), "--root", str(ROOT)]]
    if suite == "retrieval":
        commands.append(["gate", "--config", str(config), "--root", str(ROOT)])
    for command in commands:
        assert main(command) == 1, command
        err = capsys.readouterr().err
        assert "check-dataset stopped the run" in err
        assert expected in err
