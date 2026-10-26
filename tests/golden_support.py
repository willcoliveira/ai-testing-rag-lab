"""Readings of the golden files the tests share, made here and not by raglab's own code, so a test
is a second reading of the file the maintainer signs off:

- the lines of a golden file, and its behaviour cases;
- S2's measure: the longest run of words a question shares with a text (S2 and S4 ledgers);
- the datasheet's Maintenance table: each row's version, file and sha256 (S4-J10, S4-J11; the
  File column since datasheet v2, S4b).
"""

import json
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

from tests.conftest import ROOT
from tests.corpus_text import documents

V1 = ROOT / "datasets" / "golden.v1.jsonl"
V2 = ROOT / "datasets" / "golden.v2.jsonl"
DATASHEET = ROOT / "datasets" / "DATASHEET.md"
WORD = re.compile(r"[a-z0-9]+")  # S2's words: runs of letters and digits, so "on-call" is two


def rows_of(lines: Iterable[str]) -> tuple[dict[str, Any], ...]:
    return tuple(json.loads(line) for line in lines if line.strip())


@cache
def golden_lines(path: Path) -> tuple[dict[str, Any], ...]:
    """Every line of a golden file, parsed, in file order."""
    return rows_of(path.read_text(encoding="utf-8").splitlines())


def behaviour(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if row["kind"] == "behaviour"]


def slot(mix: str) -> str:
    return "paraphrased or misspelled" if mix in ("paraphrase", "misspelling") else mix


# ---------------------------------------------------------------- S2's measure


def words(text: str) -> list[str]:
    return WORD.findall(text.lower())


@dataclass(frozen=True)
class Texts:
    """Texts as one word sequence, each text ended by None, with each word's positions."""

    words: tuple[str | None, ...]
    at: dict[str, tuple[int, ...]]


def texts(items: Iterable[list[str]]) -> Texts:
    sequence: list[str | None] = []
    for item in items:
        sequence += [*item, None]
    at: dict[str, list[int]] = {}
    for position, word in enumerate(sequence):
        if word is not None:
            at.setdefault(word, []).append(position)
    return Texts(tuple(sequence), {w: tuple(p) for w, p in at.items()})


def longest_run(question: Sequence[str], within: Texts) -> int:
    """The most consecutive words of the question that one text holds in the same order."""
    best = 0
    for i, word in enumerate(question):
        for position in within.at.get(word, ()):
            n = 0
            while i + n < len(question) and within.words[position + n] == question[i + n]:
                n += 1
            best = max(best, n)
    return best


@cache
def corpus() -> Texts:
    """The tenant and external documents (the register's 18), not the attack files."""
    docs = [d for d in documents().values() if not d.path.startswith("corpus/attacks/")]
    assert len(docs) == 18
    return texts(words(d.body) for d in docs)


# ---------------------------------------------------------------- the Maintenance table


@dataclass(frozen=True)
class Row:
    version: str
    file: str  # the File cell, backticks taken off
    sha256: str


def maintenance(text: str, heading: str = "Maintenance") -> list[Row]:
    """The version rows of the datasheet's Maintenance table, or (S7) of a table of the same shape
    under another heading, such as the security pack's Versions table: the first table of the
    section, which has a File column, a row being one whose first cell is a version and whose last
    cell is a backticked sha256."""
    section = text.split(f"\n## {heading}\n", 1)[1].split("\n## ", 1)[0]
    table = re.search(r"^\|.*?(?=\n[^|]|\Z)", section.strip("\n"), flags=re.M | re.S)
    assert table, f"the {heading} section has a table"
    header, *lines = table.group(0).splitlines()
    names = [c.strip().lower() for c in header.strip().strip("|").split("|")]
    note = " (datasheet v2)" if heading == "Maintenance" else ""
    assert "file" in names, f"the {heading} table has a File column{note}"
    file_at = names.index("file")
    rows: list[Row] = []
    for line in lines:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        version = re.fullmatch(r"(v\d+(?:\.\d+)*)", cells[0])
        sha = re.fullmatch(r"`([0-9a-f]{64})`", cells[-1])
        if version and sha:
            rows.append(Row(version.group(1), cells[file_at].strip("`"), sha.group(1)))
    return rows
