"""docs/TEST-PLAN.md part 1 holds the requirements and their traceability (S1a AC1); part 2 is
the how-to 17 test plan, one named check per pipeline arrow (S1b AC1)."""

import ast
import json
import re
from pathlib import Path

import pytest
import yaml

from tests.conftest import ROOT
from tests.golden_support import maintenance

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


# ---------------------------------------------------------------- the Golden case column (S4, S4b)

# the cells that said "tbd (S4)" (the S4 plan, "Requirements the cases cover"), and S4b's
S4_CELLS = (
    "R-01", "R-02", "R-03", "R-04", "R-05", "R-06", "R-07",
    "R-10", "R-11", "R-12", "R-14", "R-18", "R-23",
)  # fmt: skip
S4B_CELLS = ("R-08", "R-09", "R-13", "R-15", "R-16", "R-17", "R-19", "R-22")
# S4b's cells that say what the golden set does not test, beside their cases (the S4b plan, GV9)
S4B_NOTES = {
    "R-15": "clean runs; the attack runs are S7's",
    "R-17": "clean runs; the attack runs are S7's",
    "R-19": "the allow list; the deny list is S7's",
}
# R-22 stays a gap: the maintainer's D3 answer, "No corpus change; R-22 stays a gap (Recommended)"
R22_CELL = "none: a gap, no planted feature (S4b, D3)"
CASE_RANGE = re.compile(r"\b([GP])-(\d{2,3}) to \1-(\d{2,3})\b")
CASE_ID = re.compile(r"\b[GP]-\d{2,3}\b")


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


def latest_golden() -> tuple[str, Path]:
    """The golden set's latest version and its file: the highest version of the datasheet's
    Maintenance table (whose S4 form, with no File column, versions golden.v1.jsonl)."""
    rows = maintenance((ROOT / "datasets" / "DATASHEET.md").read_text(encoding="utf-8"))
    row = max(rows, key=lambda r: tuple(int(part) for part in r.version[1:].split(".")))
    return row.version, ROOT / "datasets" / (row.file or "golden.v1.jsonl")


def covering_cases(path: Path) -> tuple[set[str], dict[str, set[str]], set[str]]:
    """A golden file's behaviour case ids; each requirement's cases (a case covers the
    requirements its features name in the answer key); and the cases with may_quote, which name
    R-06 by design (datasets/DATASHEET.md: the attributed external quote, D-03)."""
    key = yaml.safe_load((ROOT / "corpus" / "answer-key.yaml").read_text(encoding="utf-8"))
    requirements = {f["id"]: f["requirements"] for f in key["features"]}
    text = path.read_text(encoding="utf-8")
    lines = [json.loads(line) for line in text.splitlines() if line.strip()]
    cases = [line for line in lines if line["kind"] == "behaviour"]
    covering: dict[str, set[str]] = {}
    for case in cases:
        for feature in case["feature_ids"]:
            for rid in requirements[feature]:
                covering.setdefault(rid, set()).add(case["id"])
    quoted = {case["id"] for case in cases if "may_quote" in case}
    return {case["id"] for case in cases}, covering, quoted


def golden_case_problems(cells: dict[str, str], version: str, path: Path) -> list[str]:
    """Each Golden case cell that is not derived from the golden file at path, at version: a cell
    names the behaviour cases whose features carry its requirement (and, for R-06, the may_quote
    cases, by design); R-02 applies to every case. At v1.1 S4b's cells say "tbd (S4b)"; from v2
    they name their cases too, R-15, R-17 and R-19 saying what S7 tests, and R-22 stays a gap."""
    problems = [
        f"{rid}: S4 fills every cell it covers" for rid, c in cells.items() if "tbd (S4)" in c
    ]
    if cells["R-02"] != "every case (`model_citations_retrieved`)":
        problems.append("R-02: every case")
    behaviour, covering, quoted = covering_cases(path)
    # R-06's by-design part names exactly the may_quote cases; one may also cover R-06 by its
    # own feature (v2's G-93, through F-96), which v1.1's lone G-26 did not
    if case_ids(cells["R-06"].partition("by design")[2]) != quoted:
        problems.append(
            f"R-06: by design, the cell does not name the may_quote cases {sorted(quoted)}"
        )
    filled = [rid for rid in S4_CELLS if rid != "R-02"]
    if version == "v1.1":
        problems += [f"{rid} is S4b's" for rid in S4B_CELLS if cells[rid] != "tbd (S4b)"]
    else:
        filled += [rid for rid in S4B_CELLS if rid != "R-22"]
        if cells["R-22"] != R22_CELL:
            problems.append(f"R-22: the cell is {cells['R-22']!r}, not {R22_CELL!r}")
        problems += [
            f"{rid}: the cell does not say {note!r}"
            for rid, note in S4B_NOTES.items()
            if f"({note})" not in cells[rid]
        ]
    for rid in filled:
        named = case_ids(cells[rid])
        if not named <= behaviour:
            problems.append(f"{rid}: {sorted(named - behaviour)} are not behaviour cases")
        wanted = covering.get(rid, set()) | (quoted if rid == "R-06" else set())
        if named != wanted:
            problems.append(f"{rid}: the cell names {sorted(named)}, not {sorted(wanted)}")
    return problems


def test_the_golden_case_column_names_the_cases_that_cover_each_requirement():
    """S4 AC13 and S4b GV9 on the committed files: the Golden case column is derived from the
    golden set's latest version, the datasheet's highest Maintenance row and its file."""
    cells = golden_case_cells()
    assert set(cells) == set(defined_requirements())
    version, path = latest_golden()
    assert golden_case_problems(cells, version, path) == []


def cell_of(ids: set[str], note: str | None = None) -> str:
    """A Golden case cell naming the ids in order, as the column writes them."""
    ordered = sorted(ids, key=lambda i: (i[0] != "P", int(i.split("-")[1])))
    return ", ".join(ordered) + (f" ({note})" if note else "")


def test_on_a_planted_v2_s4bs_cells_name_their_cases_and_each_break_is_named(tmp_path):
    """GV9 before the cases land: the planted v2 (tests/dataset_support.py) with the cells
    written from it passes; R-08's cell back to "tbd (S4b)", or a case dropped from R-13's cell,
    is named."""
    from tests.dataset_support import write_v2

    path = write_v2(tmp_path)
    _, covering, quoted = covering_cases(path)
    cells = {rid: cell_of(covering.get(rid, set()), S4B_NOTES.get(rid)) for rid in covering}
    cells.update({"R-02": "every case (`model_citations_retrieved`)", "R-22": R22_CELL})
    cells["R-06"] = f"{cell_of(covering['R-06'])}; by design, {cell_of(quoted)}"
    assert golden_case_problems(cells, "v2", path) == []
    assert golden_case_problems(cells, "v1.1", path) == [f"{rid} is S4b's" for rid in S4B_CELLS]
    back = {**cells, "R-08": "tbd (S4b)"}
    assert golden_case_problems(back, "v2", path) == [
        f"R-08: the cell names [], not {sorted(covering['R-08'])}"
    ]
    dropped = sorted(covering["R-13"])[0]
    fewer = {**cells, "R-13": cell_of(covering["R-13"] - {dropped})}
    [problem] = golden_case_problems(fewer, "v2", path)
    assert problem.startswith("R-13: the cell names")
    assert f"'{dropped}'" in problem


def test_case_ids_reads_ranges_and_lists():
    assert case_ids("P-01 to P-03, G-24 to G-28, G-37") == {
        "P-01", "P-02", "P-03", "G-24", "G-25", "G-26", "G-27", "G-28", "G-37",
    }  # fmt: skip
    assert case_ids("G-22; by design, G-26 (the attributed external quote, D-03)") == {
        "G-22",
        "G-26",
    }
    assert case_ids("G-98 to G-101, G-117 (clean runs; the attack runs are S7's)") == {
        "G-98", "G-99", "G-100", "G-101", "G-117",
    }  # fmt: skip


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
    golden_set = re.split(r"\ngolden set v\d", template, maxsplit=1)[1].split("\njudges", 1)[0]
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
