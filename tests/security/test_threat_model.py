"""docs/THREAT-MODEL.md (S7, AG1): one row per OWASP Top 10 for LLM Applications 2026 entry,
LLM01:2026 to LLM10:2026 in order, each naming tests pytest collects (the file exists and defines
the function) or saying "not applicable, because"; a row's Layer cell is read as layers only when
each name it holds is a layer docs/GUARDRAILS.md's tables list or a control THREAT-MODEL's own
"Controls outside the guard layers" table lists (S8, the criteria judge's S7a-J11: the old test
read "no letter in it" as no layer, so "n/a" counted as a layer); a cell naming none (`—`, a
look-alike, nothing, "n/a", a misspelt name) is no layer, and such a row says "not applicable,
because" even when it names a test (S7a-J7 and S7a-J9); LLM09:2026 named as the build project's
LLM08:2025; the lethal-trifecta check and the not-covered list. Each break runs on a copy of the
file's text."""

import ast
import re
from functools import cache

import pytest

from tests.conftest import ROOT

pytestmark = pytest.mark.security
DOC = ROOT / "docs" / "THREAT-MODEL.md"
TEST = re.compile(r"`(tests/[\w/]+\.py)::(test_\w+)`")
IDS = [f"LLM{n:02d}:2026" for n in range(1, 11)]


GUARDRAILS = ROOT / "docs" / "GUARDRAILS.md"
CONTROLS = "### Controls outside the guard layers"
LAYER_TABLES = re.compile(r"^## (?:The layers.*|Later layers)$", flags=re.M)
PARENS = re.compile(r"\([^)]*\)")


def _name(cell: str) -> str:
    """A layer's name as both documents write it: casefolded, backticks off, a qualifier after a
    comma or in parentheses dropped ("Citation validator, extended" is the citation validator),
    a leading "the" dropped."""
    text = PARENS.sub("", cell).replace("`", "").split(",", 1)[0].strip().casefold()
    return text[4:] if text.startswith("the ") else text


def first_column(text: str, heading: str) -> list[str]:
    """The first cell of every body row of the first table under a heading."""
    body = text.split(heading + "\n", 1)[1].split("\n## ", 1)[0]
    cells = re.findall(r"^\| (.+?) \|", body, flags=re.M)
    return [cell for cell in cells[1:] if cell.strip("-")]


@cache
def known_layers() -> frozenset[str]:
    """Every name a Layer cell may hold: the Layer column of GUARDRAILS.md's layer tables (S3,
    S7a and the later layers) and the Control column of THREAT-MODEL.md's controls table, read
    from the documents."""
    guards = GUARDRAILS.read_text(encoding="utf-8")
    names = {
        _name(cell)
        for heading in LAYER_TABLES.findall(guards)
        for cell in first_column(guards, heading)
    }
    names |= {_name(cell) for cell in first_column(DOC.read_text(encoding="utf-8"), CONTROLS)}
    return frozenset(n for n in names if n)


def layer_names(cell: str) -> list[str]:
    """The names a Layer cell holds: its parentheses dropped, split at commas and semicolons; a
    part with no letter or digit in it (the em dash, a look-alike) names nothing."""
    parts = [_name(part) for part in re.split(r"[,;]", PARENS.sub("", cell))]
    return [part for part in parts if any(char.isalnum() for char in part)]


def no_layer(cell: str, known: frozenset[str] | None = None) -> bool:
    """A Layer cell that names no known layer or control: the em dash the document uses, a
    look-alike, an empty cell, "n/a", or only unknown names (S7a-J9, S7a-J11)."""
    return not any(name in (known or known_layers()) for name in layer_names(cell))


@cache
def defined(path: str) -> frozenset[str]:
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    return frozenset(n.name for n in tree.body if isinstance(n, ast.FunctionDef))


def rows(text: str) -> dict[str, list[str]]:
    """The OWASP table's rows by entry id: entry, title, in this lab, covered by, R-ids, layer."""
    found: dict[str, list[str]] = {}
    for line in text.splitlines():
        if re.match(r"^\| LLM\d\d:2026 \|", line):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            found[cells[0]] = cells
    return found


def problems(text: str, known: frozenset[str] | None = None) -> list[str]:
    known = known or known_layers()
    found = rows(text)
    out = [f"{entry}: no row" for entry in IDS if entry not in found]
    if [e for e in found if e in IDS] != [e for e in IDS if e in found]:
        out.append("the rows are not in id order")
    for entry, cells in found.items():
        if len(cells) != 6:
            out.append(f"{entry}: {len(cells)} cells, not 6")
            continue
        covered, layer = cells[3], cells[5]
        tests = TEST.findall(covered)
        reason = covered.startswith("not applicable, because")
        if not tests and not reason:
            out.append(f"{entry}: names no test and gives no reason")
        if unknown := [name for name in layer_names(layer) if name not in known]:
            out.append(
                f"{entry}: Layer names {unknown}, which neither GUARDRAILS.md's layers nor the "
                "controls table lists"
            )
        if no_layer(layer, known) and not reason:
            out.append(f'{entry}: has no layer but does not say "not applicable, because"')
        for path, name in tests:
            if not (ROOT / path).is_file() or name not in defined(path):
                out.append(f"{entry}: {path}::{name} does not exist")
    return out


def test_every_2026_entry_has_a_row_naming_tests_or_a_reason():
    assert problems(DOC.read_text(encoding="utf-8")) == []


def test_the_threat_model_keeps_its_sections():
    text = DOC.read_text(encoding="utf-8")
    assert "https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/" in text
    assert "LLM08:2025" in text
    assert "LLM09:2026" in rows(text)
    assert "Vector and Embedding Weaknesses" in rows(text)["LLM09:2026"][1]
    for heading in ("## The lethal trifecta", "## Not covered", "## The attack table"):
        assert heading in text
    for item in ("garak", "Petri", "Prompt Guard 2", "Non-English", "new document"):
        assert item in text.split("## Not covered", 1)[1], item


def test_a_row_naming_a_test_that_does_not_exist_fails_naming_the_row():
    text = DOC.read_text(encoding="utf-8")
    broken = text.replace(
        "test_the_page_and_the_playground_write_text_only", "test_the_page_is_safe", 1
    )
    assert problems(broken) == [
        "LLM10:2026: tests/security/test_egress_guard.py::test_the_page_is_safe does not exist"
    ]


EM_DASH, EN_DASH = chr(0x2014), chr(0x2013)  # the document's mark and a look-alike
UNKNOWN = "which neither GUARDRAILS.md's layers nor the controls table lists"


@pytest.mark.parametrize(
    "layer",
    [EM_DASH, EN_DASH, "", "n/a"],
    ids=["the em dash", "an en dash look-alike", "empty", "n/a"],
)
def test_a_row_without_a_layer_must_give_its_reason_even_when_it_names_a_test(layer):
    """S7a-J7, S7a-J9 and S7a-J11: LLM03's row has no layer and names a test inside its reason.
    With its reason reworded it fails, naming the row, whether its Layer cell is the em dash, a
    look-alike, empty, or "n/a" (which the old "no letter" rule read as a layer)."""
    text = DOC.read_text(encoding="utf-8")
    [row] = [line for line in text.splitlines() if line.startswith("| LLM03:2026 |")]
    assert TEST.findall(row), "LLM03's row names a test"
    cells = row.strip().strip("|").split("|")
    assert no_layer(cells[-1]), "LLM03's row has no layer"
    cells[3] = cells[3].replace("not applicable, because", "does not apply, as", 1)
    cells[-1] = f" {layer} "
    broken = text.replace(row, "|" + "|".join(cells) + "|")
    expected = ['LLM03:2026: has no layer but does not say "not applicable, because"']
    if layer == "n/a":
        expected.insert(0, f"LLM03:2026: Layer names ['n/a'], {UNKNOWN}")
    assert problems(broken) == expected


def test_every_layer_cell_resolves_against_the_two_name_lists():
    """S8 (GA15): every name every Layer cell holds is a GUARDRAILS.md layer or a listed control,
    and the lists are read from the documents (never written here)."""
    known = known_layers()
    assert {"register filter", "link guard", "tenant guard", "input limits"} <= known
    assert {"tenant filter", "egress guard", "text-only rendering", "make audit"} <= known
    assert "n/a" not in known
    for entry, cells in rows(DOC.read_text(encoding="utf-8")).items():
        names = layer_names(cells[5])
        assert all(name in known for name in names), (entry, names)
        assert bool(names) == (entry != "LLM03:2026"), entry


def test_a_misspelt_layer_name_fails_naming_the_row_and_the_name():
    """S8 (GA15): "register filtre" on LLM05's row is no layer; the row keeps its other layer, so
    only the unknown name is reported; with the whole cell "n/a" the row has no layer too."""
    text = DOC.read_text(encoding="utf-8")
    [row] = [line for line in text.splitlines() if line.startswith("| LLM05:2026 |")]
    assert "register filter, citation validator |" in row
    misspelt = row.replace("register filter, citation", "register filtre, citation")
    assert problems(text.replace(row, misspelt)) == [
        f"LLM05:2026: Layer names ['register filtre'], {UNKNOWN}"
    ]
    alone = row.replace("register filter, citation validator |", "n/a |")
    assert problems(text.replace(row, alone)) == [
        f"LLM05:2026: Layer names ['n/a'], {UNKNOWN}",
        'LLM05:2026: has no layer but does not say "not applicable, because"',
    ]


def test_a_missing_row_fails_naming_its_id():
    text = DOC.read_text(encoding="utf-8")
    broken = "\n".join(line for line in text.splitlines() if not line.startswith("| LLM06:2026 |"))
    assert problems(broken) == ["LLM06:2026: no row"]
