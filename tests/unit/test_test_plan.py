"""docs/TEST-PLAN.md part 1 holds the requirements and their traceability (S1a AC1)."""

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
