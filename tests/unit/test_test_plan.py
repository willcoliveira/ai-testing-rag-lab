"""docs/TEST-PLAN.md part 1 holds the requirements and their traceability (S1a AC1); part 2 is
the how-to 17 test plan, one named check per pipeline arrow (S1b AC1)."""

import ast
import re

import pytest

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


# ---------------------------------------------------------------- part 2 (S1b AC1)

LATER_STAGES = {"S2", "S3", "S3h", "S4", "S4b", "S5", "S6", "S7", "S8", "S9", "S10", "S11", "S12"}
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
    template = part2().split("## 10. The plan, filled in", 1)[1]
    ingestion = template.split("ingestion (every commit):", 1)[1].split("\nretrieval", 1)[0]
    assert not re.search(r"<[^=\s]", ingestion), "the ingestion line has a <placeholder> left"
