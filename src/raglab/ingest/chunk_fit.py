"""Which planted features a chunk setting keeps together (S1b's chunk experiment, moved here in
S8 so the cause rule can read it; `scripts/chunk_experiment.py` prints it).

A planted feature (corpus/answer-key.yaml) cites values at locations: a document, a section and
sometimes a table cell. For each feature and each (document, section) it cites, the feature is
**kept** when one chunk of that section holds every value cited there, and for a table cell, the
table's header row and the cell's row with the value in its column (so the value can still be
read as "row, column"). Otherwise it is **split**, with the reason. AC5's rule and exception
(F-15: A-MFA 4.1 paragraphs 1 and 2) is one such group. Attack documents are not in a clean
inventory, so their features are skipped.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import yaml

from raglab.core.text import normalise_space
from raglab.core.types import Chunk

ANSWER_KEY = "corpus/answer-key.yaml"


@dataclass(frozen=True)
class TableCell:
    caption: str
    row: str
    column: str
    value: str


@dataclass(frozen=True)
class Group:
    """What one feature cites in one section of one document."""

    feature: str
    doc: str
    section: str
    values: tuple[str, ...]
    cells: tuple[TableCell, ...]


@dataclass(frozen=True)
class Split:
    group: Group
    reason: str

    def __str__(self) -> str:
        g = self.group
        return f"{g.feature} {g.doc} {g.section}: {self.reason}"


def _as_dict(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"expected a mapping, got {type(value).__name__}")
    return {str(k): v for k, v in cast(dict[object, object], value).items()}


def _as_list(value: object) -> list[object]:
    if not isinstance(value, list):
        raise ValueError(f"expected a list, got {type(value).__name__}")
    return list(cast(list[object], value))


def groups(answer_key: dict[str, object]) -> list[Group]:
    """Each feature's cited values, grouped by document and section, in key order."""
    out: list[Group] = []
    for raw in _as_list(answer_key["features"]):
        feature = _as_dict(raw)
        found: dict[tuple[str, str], tuple[list[str], list[TableCell]]] = {}
        for raw_location in _as_list(feature.get("locations", [])):
            location = _as_dict(raw_location)
            key = (str(location["doc"]), str(location["section"]))
            values, cells = found.setdefault(key, ([], []))
            location_values = [str(v) for v in _as_list(location.get("values", []))]
            if "table" in location:
                table = _as_dict(location["table"])
                cells.extend(
                    TableCell(str(table["caption"]), str(table["row"]), str(table["column"]), v)
                    for v in location_values
                )
            else:
                values.extend(location_values)
        out.extend(
            Group(str(feature["id"]), doc, section, tuple(values), tuple(cells))
            for (doc, section), (values, cells) in found.items()
        )
    return out


def _table_rows(text: str) -> list[list[str]]:
    return [
        [c.strip() for c in line.strip().strip("|").split("|")]
        for line in text.split("\n")
        if line.startswith("| ")
    ]


def holds_cell(chunk: Chunk, cell: TableCell) -> bool:
    """The chunk has the caption, a header row naming the column, and the row with the value."""
    if cell.caption not in chunk.text:
        return False
    rows = _table_rows(chunk.text.split(cell.caption, 1)[1])
    if not rows or cell.column not in rows[0]:
        return False
    column = rows[0].index(cell.column)
    return any(
        row[0] == cell.row and len(row) > column and cell.value in row[column] for row in rows[1:]
    )


def missing(chunk: Chunk, group: Group) -> list[str]:
    """What the group cites that this chunk does not hold."""
    text = normalise_space(chunk.text)
    lost = [repr(v) for v in group.values if normalise_space(v) not in text]
    lost += [
        f"{c.caption} [{c.row}, {c.column}] = {c.value!r}"
        for c in group.cells
        if not holds_cell(chunk, c)
    ]
    return lost


def split_groups(chunks: Sequence[Chunk], key: dict[str, object]) -> list[Split]:
    """The feature groups no single chunk of their section holds."""
    docs = {c.doc_id for c in chunks}
    splits: list[Split] = []
    for group in groups(key):
        if group.doc not in docs:
            continue  # an attack document: not in a clean inventory
        section = [c for c in chunks if c.doc_id == group.doc and c.section_id == group.section]
        if not section:
            splits.append(Split(group, "no chunk has this section"))
        else:
            best = min(section, key=lambda c: len(missing(c, group)))
            if lost := missing(best, group):
                splits.append(
                    Split(
                        group,
                        f"{len(section)} chunks; the closest, {best.chunk_id}, lacks "
                        + "; ".join(lost),
                    )
                )
    return splits


def read_answer_key(root: Path) -> dict[str, object]:
    return _as_dict(yaml.safe_load((root / ANSWER_KEY).read_text(encoding="utf-8")))


def split_features(chunks: Sequence[Chunk], root: Path) -> frozenset[str]:
    """The ids of the features split at these chunks' settings (S8, the cause rule's ingestion
    clause): a feature whose cited values no single chunk of a section holds together."""
    return frozenset(split.group.feature for split in split_groups(chunks, read_answer_key(root)))
