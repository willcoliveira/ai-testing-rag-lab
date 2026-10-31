"""S8 (GA12, D3 A): the flake policy's mechanics. The `flaky` marker is registered; `make check`
and pr-fast never select it (`PYTEST_OFFLINE` excludes it) and `make test-flaky` runs it alone;
every test marked `flaky` has a row in docs/GATES.md's register with a removal date at most 30
days after it was first seen and not past; a row names a marked test. The register is empty at
S8. Each break runs on hand-built inputs."""

import ast
import datetime as dt
import re
import tomllib
from pathlib import Path

import pytest

from tests.conftest import ROOT

pytestmark = pytest.mark.unit
DOC = ROOT / "docs" / "GATES.md"
MAKEFILE = ROOT / "Makefile"
COLUMNS = ("Test id", "First seen", "Run or session", "Suspected cause", "Owner", "Removal date")
MAX_DAYS = 30


def register_rows(text: str) -> list[dict[str, str]]:
    body = text.split("\n### Register\n", 1)[1].split("\n### ", 1)[0]
    lines = [line for line in body.splitlines() if line.startswith("|")]
    header = tuple(c.strip() for c in lines[0].strip().strip("|").split("|"))
    assert header == COLUMNS, header
    return [
        dict(zip(COLUMNS, (c.strip() for c in line.strip().strip("|").split("|")), strict=False))
        for line in lines[2:]
    ]


def _is_flaky(node: ast.expr) -> bool:
    """`pytest.mark.flaky`, `mark.flaky` (after `from pytest import mark`), or either called."""
    target = node.func if isinstance(node, ast.Call) else node
    if not isinstance(target, ast.Attribute) or target.attr != "flaky":
        return False
    owner = target.value
    return (isinstance(owner, ast.Attribute) and owner.attr == "mark") or (
        isinstance(owner, ast.Name) and owner.id == "mark"
    )


def _tests(body: list[ast.stmt], prefix: str = "") -> list[tuple[str, ast.FunctionDef, bool]]:
    """Every test function of a module body, and of each test class in it (the judge's S8-J14),
    as (dotted name, node, whether its class carries the marker)."""
    found: list[tuple[str, ast.FunctionDef, bool]] = []
    for node in body:
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            found.append((f"{prefix}{node.name}", node, False))
        elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            marked = any(_is_flaky(d) for d in node.decorator_list)
            found += [
                (f"{prefix}{node.name}::{name}", fn, marked or via_class)
                for name, fn, via_class in _tests(node.body, "")
            ]
    return found


def marked_tests(tests_dir: Path = ROOT / "tests") -> set[str]:
    """Every test id (path::name) whose function, or whose module's `pytestmark`, carries the
    flaky marker, read from the syntax tree (a mention in a string is not a marker)."""
    found: set[str] = set()
    for path in sorted(tests_dir.rglob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        rel = path.relative_to(tests_dir.parent).as_posix()
        module_marked = any(
            isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "pytestmark" for t in n.targets)
            and any(_is_flaky(e) for e in ast.walk(n.value) if isinstance(e, ast.expr))
            for n in tree.body
        )
        for name, test, via_class in _tests(tree.body):
            if module_marked or via_class or any(_is_flaky(d) for d in test.decorator_list):
                found.add(f"{rel}::{name}")
    return found


def problems(text: str, marked: set[str], today: dt.date) -> list[str]:
    rows = register_rows(text)
    listed = {row["Test id"].strip("`") for row in rows}
    out = [f"{test} is marked flaky but has no register row" for test in sorted(marked - listed)]
    for row in rows:
        test = row["Test id"].strip("`")
        if test not in marked:
            out.append(f"{test} has a register row but is not marked flaky")
        try:
            first = dt.date.fromisoformat(row["First seen"])
            removal = dt.date.fromisoformat(row["Removal date"])
        except ValueError:
            out.append(f"{test}: the dates are not ISO dates")
            continue
        if removal < today:
            out.append(f"{test}: its removal date {removal} has passed")
        if (removal - first).days > MAX_DAYS:
            out.append(f"{test}: its removal date is more than {MAX_DAYS} days after {first}")
        if not row["Suspected cause"] or not row["Owner"] or not row["Run or session"]:
            out.append(f"{test}: a row names its run, its suspected cause and its owner")
    return out


def test_the_marker_is_registered_and_out_of_make_check():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    markers = {m.split(":", 1)[0] for m in data["tool"]["pytest"]["ini_options"]["markers"]}
    assert "flaky" in markers
    assert "--strict-markers" in data["tool"]["pytest"]["ini_options"]["addopts"]
    makefile = MAKEFILE.read_text(encoding="utf-8")
    offline = re.search(r"^PYTEST_OFFLINE := (.*)$", makefile, flags=re.M)
    assert offline, "the Makefile defines PYTEST_OFFLINE"
    assert "not flaky" in offline.group(1)
    assert re.search(
        r"^test-flaky:\n\tHF_HUB_OFFLINE=1 uv run pytest -m flaky$", makefile, flags=re.M
    )
    check = re.search(r"^check: (.*)$", makefile, flags=re.M)
    assert check
    assert "test-flaky" not in check.group(1)
    workflow = (ROOT / ".github" / "workflows" / "pr-fast.yml").read_text(encoding="utf-8")
    assert "test-flaky" not in workflow


def test_the_register_is_consistent_with_the_marked_tests():
    assert problems(DOC.read_text(encoding="utf-8"), marked_tests(), dt.date.today()) == []


def test_the_register_is_empty_at_s8():
    assert register_rows(DOC.read_text(encoding="utf-8")) == []
    assert marked_tests() == set()


def test_the_policy_states_its_rules():
    text = re.sub(r"\s+", " ", DOC.read_text(encoding="utf-8").split("\n## Flakes\n", 1)[1])
    for phrase in (
        "No automatic retry; one recorded re-run by hand",
        "never replaces a recorded number",
        "`flaky` marker",
        "`make test-flaky`",
        "at most 30 days",
        "Seen so far (environment failures, not flakes)",
        "Lab practice",
    ):
        assert phrase in text, phrase


def test_a_marked_test_without_a_row_a_past_date_and_a_stale_row_are_each_named(tmp_path):
    text = DOC.read_text(encoding="utf-8")
    today = dt.date(2026, 10, 31)
    marked = {"tests/unit/test_example.py::test_wobbles"}
    assert problems(text, marked, today) == [
        "tests/unit/test_example.py::test_wobbles is marked flaky but has no register row"
    ]
    row = (
        "| `tests/unit/test_example.py::test_wobbles` | 2026-10-30 | pr-fast run 1 | a timing "
        "window | quality | {} |\n"
    )
    anchor = "| " + " | ".join(COLUMNS) + " |\n|---|---|---|---|---|---|\n"
    assert text.count(anchor) == 1
    with_row = text.replace(anchor, anchor + row.format("2026-11-20"), 1)
    assert problems(with_row, marked, today) == []
    assert problems(with_row, set(), today) == [
        "tests/unit/test_example.py::test_wobbles has a register row but is not marked flaky"
    ]
    past = text.replace(anchor, anchor + row.format("2026-10-30"), 1)
    assert problems(past, marked, today) == [
        "tests/unit/test_example.py::test_wobbles: its removal date 2026-10-30 has passed"
    ]
    far = text.replace(anchor, anchor + row.format("2026-12-15"), 1)
    assert problems(far, marked, today) == [
        "tests/unit/test_example.py::test_wobbles: its removal date is more than 30 days after "
        "2026-10-30"
    ]
    # a planted test file carrying the marker is found by the scan
    planted = tmp_path / "tests" / "unit"
    planted.mkdir(parents=True)
    lines = ["import pytest", "", "", "@pytest.mark.flaky", "def test_wobbles():", "    pass"]
    lines += ["", "", "def test_steady():", "    pass", ""]
    (planted / "test_example.py").write_text("\n".join(lines), encoding="utf-8")
    assert marked_tests(tmp_path / "tests") == marked


def test_the_scan_reads_class_methods_and_the_imported_mark(tmp_path):
    """The judge's S8-J14: a method of a test class, a class marked as a whole, and `@mark.flaky`
    after `from pytest import mark` are found; a class not named Test* and a helper are not."""
    planted = tmp_path / "tests" / "unit"
    planted.mkdir(parents=True)
    lines = [
        "from pytest import mark",
        "import pytest",
        "",
        "",
        "class TestThings:",
        "    @mark.flaky",
        "    def test_in_a_class(self):",
        "        pass",
        "",
        "    def test_steady_in_a_class(self):",
        "        pass",
        "",
        "",
        "@pytest.mark.flaky(reason='a timing window')",
        "class TestAllOfThem:",
        "    def test_one(self):",
        "        pass",
        "",
        "    def helper(self):",
        "        pass",
        "",
        "",
        "@mark.flaky",
        "def test_imported_mark():",
        "    pass",
        "",
        "",
        "class Helper:",
        "    @mark.flaky",
        "    def test_not_collected(self):",
        "        pass",
        "",
    ]
    (planted / "test_forms.py").write_text("\n".join(lines), encoding="utf-8")
    assert marked_tests(tmp_path / "tests") == {
        "tests/unit/test_forms.py::TestThings::test_in_a_class",
        "tests/unit/test_forms.py::TestAllOfThem::test_one",
        "tests/unit/test_forms.py::test_imported_mark",
    }


def test_flaky_left_in_the_offline_selection_is_named():
    """The break: `flaky` dropped from PYTEST_OFFLINE's exclusion."""
    makefile = MAKEFILE.read_text(encoding="utf-8")
    broken = makefile.replace(" and not flaky", "", 1)
    offline = re.search(r"^PYTEST_OFFLINE := (.*)$", broken, flags=re.M)
    assert offline
    assert "not flaky" not in offline.group(1)
