"""docs/TEST-PLAN.md part 1 holds the requirements and their traceability (S1a AC1); part 2 is
the how-to 17 test plan, one named check per pipeline arrow (S1b AC1)."""

import ast
import json
import re

import pytest
import yaml

from tests.conftest import ROOT

pytestmark = pytest.mark.unit

PART1_SECTIONS = [
    "## 1. Problem and product",
    "## 2. Users and their jobs",
    "## 3. Functional requirements",
    "## 4. Safety and security requirements",
    "## 5. Quality attributes",
    "## 6. Out of scope",
    "## 8. Traceability",
    "### Gaps (requirements with no planted feature)",
]
USERS = ["Employee", "New joiner", "IT admin", "Security analyst", "Auditor"]


def part1() -> str:
    text = (ROOT / "docs" / "TEST-PLAN.md").read_text(encoding="utf-8")
    assert "# Part 1: Requirements" in text
    return text.split("# Part 1: Requirements", 1)[1].split("\n# Part 2", 1)[0]


def section(title: str) -> str:
    body = part1().split(title + "\n", 1)[1]
    return re.split(r"\n## ", body, maxsplit=1)[0]


def defined_requirements() -> list[str]:
    text = section("## 3. Functional requirements") + section(
        "## 4. Safety and security requirements"
    )
    return re.findall(r"^\| (R-\d{2}) \|", text, flags=re.M)


def test_part1_has_every_section_in_order():
    text = part1()
    positions = [text.find(title + "\n") for title in PART1_SECTIONS]
    assert all(p >= 0 for p in positions), [
        t for t, p in zip(PART1_SECTIONS, positions, strict=True) if p < 0
    ]
    assert positions == sorted(positions)


def test_users_and_jobs_name_the_five_users():
    users = section("## 2. Users and their jobs")
    for user in USERS:
        assert f"| **{user}**" in users, user


def test_requirement_ids_are_unique_and_numbered():
    ids = defined_requirements()
    assert len(ids) >= 20
    assert len(ids) == len(set(ids)), "an R-id is defined twice"
    numbers = sorted(int(i[2:]) for i in ids)
    assert numbers == list(range(1, len(ids) + 1)), "R-ids are not R-01..R-nn without holes"


def test_safety_requirements_cover_the_four_never_rules():
    safety = section("## 4. Safety and security requirements")
    for phrase in [
        "another tenant's content",
        "instructions found in documents",
        "invent a policy value",
        "secrets or PII",
    ]:
        assert phrase in safety, phrase


def test_quality_attributes_and_out_of_scope_are_filled():
    assert re.search(r"^\| Q-01 \|", section("## 5. Quality attributes"), flags=re.M)
    assert section("## 6. Out of scope").count("\n- ") >= 3


def test_every_requirement_is_in_the_traceability_table():
    table = section("## 8. Traceability").split("### Gaps", 1)[0]
    rows = re.findall(r"^\| (R-\d{2}) \| [^|]+ \| ([^|]+) \|", table, flags=re.M)
    traced = {rid for rid, _ in rows}
    assert traced == set(defined_requirements())
    gaps = {rid for rid, cell in rows if cell.strip().startswith("gap")}
    gaps_list = part1().split("### Gaps", 1)[1]
    listed = set(re.findall(r"^\| (R-\d{2}) \|", gaps_list, flags=re.M))
    assert gaps == listed, "every gap in the table has a reason in the gaps list, and only those"
    for rid, cell in rows:
        assert cell.strip().startswith("gap") or re.search(r"F-\d+", cell), rid


# ---------------------------------------------------------------- the Golden case column (S4)

# the cells that said "tbd (S4)" (the S4 plan, "Requirements the cases cover"), and S4b's
S4_CELLS = (
    "R-01", "R-02", "R-03", "R-04", "R-05", "R-06", "R-07",
    "R-10", "R-11", "R-12", "R-14", "R-18", "R-23",
)  # fmt: skip
S4B_CELLS = ("R-08", "R-09", "R-13", "R-15", "R-16", "R-17", "R-19", "R-22")
# a case named by design, not by its features' requirements (datasets/DATASHEET.md, the R-06 row)
BY_DESIGN = {"R-06": {"G-26"}}
CASE_RANGE = re.compile(r"\b([GP])-(\d{2}) to \1-(\d{2})\b")
CASE_ID = re.compile(r"\b[GP]-\d{2}\b")


def golden_case_cells() -> dict[str, str]:
    table = section("## 8. Traceability").split("### Gaps", 1)[0]
    rows = re.findall(r"^\| (R-\d{2}) \| [^|]+ \| [^|]+ \| ([^|]+) \|", table, flags=re.M)
    return {rid: cell.strip() for rid, cell in rows}


def case_ids(cell: str) -> set[str]:
    """The case ids of a cell: "G-24 to G-28, G-37" as a set of ids."""
    ids = {
        f"{prefix}-{n:02d}"
        for prefix, lo, hi in CASE_RANGE.findall(cell)
        for n in range(int(lo), int(hi) + 1)
    }
    return ids | set(CASE_ID.findall(CASE_RANGE.sub("", cell)))


def covering_cases() -> tuple[set[str], dict[str, set[str]]]:
    """The committed golden file's behaviour case ids, and each requirement's cases: a case
    covers the requirements its features name in the answer key."""
    key = yaml.safe_load((ROOT / "corpus" / "answer-key.yaml").read_text(encoding="utf-8"))
    requirements = {f["id"]: f["requirements"] for f in key["features"]}
    text = (ROOT / "datasets" / "golden.v1.jsonl").read_text(encoding="utf-8")
    lines = [json.loads(line) for line in text.splitlines() if line.strip()]
    cases = [line for line in lines if line["kind"] == "behaviour"]
    covering: dict[str, set[str]] = {}
    for case in cases:
        for feature in case["feature_ids"]:
            for rid in requirements[feature]:
                covering.setdefault(rid, set()).add(case["id"])
    return {case["id"] for case in cases}, covering


def test_the_golden_case_column_names_the_cases_that_cover_each_requirement():
    """S4 AC13: every "tbd (S4)" cell names the behaviour cases whose features carry its
    requirement (and the one case named by design); R-02 applies to every case; S4b's cells
    stay."""
    cells = golden_case_cells()
    assert set(cells) == set(defined_requirements())
    left = [rid for rid, cell in cells.items() if "tbd (S4)" in cell]
    assert not left, f"{left}: S4 fills every cell it covers"
    for rid in S4B_CELLS:
        assert cells[rid] == "tbd (S4b)", f"{rid} is S4b's"
    assert cells["R-02"] == "every case (`model_citations_retrieved`)"
    behaviour, covering = covering_cases()
    for rid, extra in BY_DESIGN.items():
        assert not extra & covering.get(rid, set()), f"{rid}: {extra} is not by design"
    for rid in S4_CELLS:
        if rid == "R-02":
            continue
        named = case_ids(cells[rid])
        assert named <= behaviour, f"{rid}: {sorted(named - behaviour)} are not behaviour cases"
        wanted = covering.get(rid, set()) | BY_DESIGN.get(rid, set())
        assert named == wanted, f"{rid}: the cell names {sorted(named)}, not {sorted(wanted)}"


def test_case_ids_reads_ranges_and_lists():
    assert case_ids("P-01 to P-03, G-24 to G-28, G-37") == {
        "P-01", "P-02", "P-03", "G-24", "G-25", "G-26", "G-27", "G-28", "G-37",
    }  # fmt: skip
    assert case_ids("G-22; by design, G-26 (the attributed external quote, D-03)") == {
        "G-22",
        "G-26",
    }


# ---------------------------------------------------------------- part 2 (S1b AC1)

LATER_STAGES = {"S3", "S3h", "S4", "S4b", "S5", "S6", "S7", "S8", "S9", "S10", "S11", "S12"}
TEST_ID = re.compile(r"`(tests/[\w/]+\.py)::(test_\w+)`")
WHERE_LATER = re.compile(r"^from (S\d+[a-z]?)$")


def part2() -> str:
    text = (ROOT / "docs" / "TEST-PLAN.md").read_text(encoding="utf-8")
    assert "\n# Part 2: Test plan (how-to 17)\n" in text
    return text.split("\n# Part 2: Test plan (how-to 17)\n", 1)[1]


def flow_rows(title: str) -> list[list[str]]:
    """The rows of one flow's table: id, arrow, check, oracle, where, gate."""
    body = part2().split(title + "\n", 1)[1]
    body = re.split(r"\n#{2,3} ", body, maxsplit=1)[0]
    return [
        [c.strip() for c in line.strip().strip("|").split("|")]
        for line in body.splitlines()
        if re.match(r"^\| [LR]\d+ \|", line)
    ]


def all_rows() -> list[list[str]]:
    return flow_rows("### 9.1 Load flow (every commit, no model)") + flow_rows(
        "### 9.2 Retrieve flow (per question)"
    )


def defined_tests(path: str) -> set[str]:
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    return {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}


def test_part2_draws_both_flows_as_arrows():
    text = part2()
    diagram = re.search(r"```mermaid\n(.*?)```", text, flags=re.S)
    assert diagram, "the pipeline is drawn as a diagram"
    load, retrieve = (
        flow_rows("### 9.1 Load flow (every commit, no model)"),
        flow_rows("### 9.2 Retrieve flow (per question)"),
    )
    assert len(load) >= 8
    assert len(retrieve) >= 6
    for row in load + retrieve:
        assert len(row) == 6, row
        assert "→" in row[1], f"{row[0]}: {row[1]} is not an arrow"
        assert re.search(rf"-->\|{row[0]}[ |]", diagram.group(1)), f"{row[0]} is not drawn"


def test_each_arrow_has_one_named_check_mapped_to_tests_or_a_later_stage():
    rows = all_rows()
    ids, arrows, checks = ([r[i] for r in rows] for i in (0, 1, 2))
    assert len(set(ids)) == len(ids), "an arrow id is used twice"
    assert len(set(arrows)) == len(arrows), "an arrow has two checks"
    assert len(set(checks)) == len(checks), "a check name is used twice"
    for row in rows:
        check, where = row[2], row[4]
        assert re.fullmatch(r"`[a-z0-9-]+`", check), f"{row[0]}: check {check!r} is not named"
        later = WHERE_LATER.match(where)
        if later:
            assert later.group(1) in LATER_STAGES, f"{row[0]}: {where} is not a later stage"
            continue
        tests = TEST_ID.findall(where)
        assert tests, f"{row[0]}: {where!r} names no test and no later stage"
        assert TEST_ID.sub("", where).replace(",", "").strip() == "", f"{row[0]}: {where!r}"
        for path, name in tests:
            assert (ROOT / path).is_file(), f"{row[0]}: {path} does not exist"
            assert name in defined_tests(path), f"{row[0]}: {path}::{name} does not exist"


def test_the_stages_so_far_are_filled_in():
    load = {r[0]: r for r in flow_rows("### 9.1 Load flow (every commit, no model)")}
    for arrow in ("L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8"):
        assert load[arrow][4].startswith("`tests/"), f"{arrow} is S1b's and must name its tests"
    rows = {r[0]: r for r in all_rows()}
    for arrow in ("L10", "L11", "R2", "R3"):
        assert rows[arrow][4].startswith("`tests/"), f"{arrow} is S2's and must name its tests"
    for arrow in ("R1", "R4", "R7"):
        assert rows[arrow][4].startswith("`tests/"), f"{arrow} is S3's and must name its tests"
    assert rows["R6"][4].startswith("`tests/"), "R6 is S4's and must name its tests"
    template = part2().split("## 10. The plan, filled in", 1)[1]
    ingestion = template.split("ingestion (every commit):", 1)[1].split("\nretrieval", 1)[0]
    assert not re.search(r"<[^=\s]", ingestion), "the ingestion line has a <placeholder> left"
    retrieval = template.split("retrieval (every commit, no judge):", 1)[1].split("\ngolden", 1)[0]
    assert not re.search(r"<[^=\s]", retrieval), "the retrieval line has a <placeholder> left"
    golden_set = template.split("\ngolden set v1", 1)[1].split("\njudges", 1)[0]
    assert not re.search(r"<[^=\s]", golden_set), "the golden-set line has a <placeholder> left"


# ---------------------------------------------------------------- S5: the judged criteria


def criteria_requirements() -> dict[str, list[str]]:
    """Each requirement docs/CRITERIA.md names, with the criteria that name it, in its order."""
    text = (ROOT / "docs" / "CRITERIA.md").read_text(encoding="utf-8")
    body = text.split("\n## The criteria\n", 1)[1].split("\n## ", 1)[0]
    covers: dict[str, list[str]] = {}
    for part in re.split(r"\n### ", "\n" + body)[1:]:
        name = re.match(r"`([a-z_]+)`", part)
        req = re.search(r"\*\*Requirements:\*\* (.*?)(?:\n- |\Z)", part, flags=re.S)
        assert name
        assert req
        for rid in re.findall(r"R-\d\d", req.group(1)):
            covers.setdefault(rid, []).append(name.group(1))
    return covers


def test_r5_names_its_tests_and_its_gate_local_until_keys_reported_until_s6():
    """S5 AC14: R5 is built, so it names its tests (the arrows test checks each exists) and its
    gate says local until keys and reported until S6; its oracle says what is judged and what
    stays label-based."""
    rows = {r[0]: r for r in all_rows()}
    r5 = rows["R5"]
    assert r5[4].startswith("`tests/"), "R5 is S5's and must name its tests"
    assert "local until keys" in r5[5]
    assert "reported, not gated, until S6" in r5[5]
    assert "docs/CRITERIA.md" in r5[3]
    assert "label-based" in r5[3]


def test_the_test_column_names_the_judged_criteria_for_the_requirements_they_cover():
    """S5 AC14: each requirement a criterion names in docs/CRITERIA.md has, in the traceability
    table's Test column, those criteria, reported."""
    table = section("## 8. Traceability").split("### Gaps", 1)[0]
    cells = {
        m.group(1): [c.strip() for c in m.group(0).strip().strip("|").split("|")][4]
        for m in re.finditer(r"^\| (R-\d{2}) \|.*$", table, flags=re.M)
    }
    covers = criteria_requirements()
    assert covers, "docs/CRITERIA.md names requirements"
    for rid, names in covers.items():
        judged = "judged (S5, reported): " + ", ".join(f"`{n}`" for n in names)
        assert judged in cells[rid], f"{rid}: {cells[rid]!r} lacks {judged!r}"
    for rid, cell in cells.items():
        if rid not in covers:
            assert "judged (S5" not in cell, f"{rid} names a criterion that names no {rid}"
