"""docs/THREAT-MODEL.md (S7, AG1): one row per OWASP Top 10 for LLM Applications 2026 entry,
LLM01:2026 to LLM10:2026 in order, each naming tests pytest collects (the file exists and defines
the function) or saying "not applicable, because"; a row with no layer (a Layer cell with no letter
in it: `—`, a look-alike or nothing) says "not applicable, because" even when it names a test (the
criteria judge's S7a-J7 and S7a-J9); LLM09:2026 named as the build project's LLM08:2025; the
lethal-trifecta check and the not-covered list. Each break runs on a copy of the file's text."""

import ast
import re
from functools import cache

import pytest

from tests.conftest import ROOT

pytestmark = pytest.mark.security
DOC = ROOT / "docs" / "THREAT-MODEL.md"
TEST = re.compile(r"`(tests/[\w/]+\.py)::(test_\w+)`")
IDS = [f"LLM{n:02d}:2026" for n in range(1, 11)]


def no_layer(cell: str) -> bool:
    """A Layer cell with no letter in it: the em dash the document uses, a look-alike such as an
    en dash, or an empty cell (S7a-J9)."""
    return not any(char.isalpha() for char in cell)


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


def problems(text: str) -> list[str]:
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
        if no_layer(layer) and not reason:
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


@pytest.mark.parametrize(
    "layer", [EM_DASH, EN_DASH, ""], ids=["the em dash", "an en dash look-alike", "empty"]
)
def test_a_row_without_a_layer_must_give_its_reason_even_when_it_names_a_test(layer):
    """S7a-J7 and S7a-J9: LLM03's row has no layer and names a test inside its reason. With its
    reason reworded it fails, naming the row, whether its Layer cell is the em dash, a look-alike
    with no letter in it, or empty."""
    text = DOC.read_text(encoding="utf-8")
    [row] = [line for line in text.splitlines() if line.startswith("| LLM03:2026 |")]
    assert TEST.findall(row), "LLM03's row names a test"
    cells = row.strip().strip("|").split("|")
    assert no_layer(cells[-1]), "LLM03's row has no layer"
    cells[3] = cells[3].replace("not applicable, because", "does not apply, as", 1)
    cells[-1] = f" {layer} "
    broken = text.replace(row, "|" + "|".join(cells) + "|")
    assert problems(broken) == [
        'LLM03:2026: has no layer but does not say "not applicable, because"'
    ]


def test_a_missing_row_fails_naming_its_id():
    text = DOC.read_text(encoding="utf-8")
    broken = "\n".join(line for line in text.splitlines() if not line.startswith("| LLM06:2026 |"))
    assert problems(broken) == ["LLM06:2026: no row"]
