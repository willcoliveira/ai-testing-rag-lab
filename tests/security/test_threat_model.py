"""docs/THREAT-MODEL.md (S7, AG1): one row per OWASP Top 10 for LLM Applications 2026 entry,
LLM01:2026 to LLM10:2026 in order, each naming tests pytest collects (the file exists and defines
the function) or saying "not applicable, because"; LLM09:2026 named as the build project's
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
        covered = cells[3]
        tests = TEST.findall(covered)
        if not tests and not covered.startswith("not applicable, because"):
            out.append(f"{entry}: names no test and gives no reason")
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


def test_a_missing_row_fails_naming_its_id():
    text = DOC.read_text(encoding="utf-8")
    broken = "\n".join(line for line in text.splitlines() if not line.startswith("| LLM06:2026 |"))
    assert problems(broken) == ["LLM06:2026: no row"]
