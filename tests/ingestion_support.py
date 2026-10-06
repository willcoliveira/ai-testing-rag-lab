"""Shared helpers for the ingestion tests: the register, parsed documents, the default inventory
and the answer key's locations per document (each computed once per test session)."""

from functools import cache

import pytest
import yaml

from raglab.chunk.sections import sections
from raglab.core.types import Block, Document
from raglab.ingest import pipeline, register
from raglab.ingest.pipeline import Inventory
from tests.conftest import ROOT


@cache
def entries() -> dict[str, register.Entry]:
    return {e.doc_id: e for e in register.read(ROOT)}


@cache
def parsed(doc_id: str) -> Document:
    e = entries()[doc_id]
    meta = pipeline.describe(ROOT, e.doc_id, e.status, e.tenant, e.path, e.format)
    return pipeline.parse(ROOT, meta)


@cache
def default_inventory() -> Inventory:
    return pipeline.ingest(ROOT)


def doc_params() -> list:
    """One pytest param per register document; the scanned page also carries the ocr marker."""
    return [
        pytest.param(doc_id, marks=[pytest.mark.ocr] if e.format == "png" else [], id=doc_id)
        for doc_id, e in entries().items()
    ]


@cache
def answer_key() -> dict:
    return yaml.safe_load((ROOT / "corpus" / "answer-key.yaml").read_text(encoding="utf-8"))


def locations(doc_id: str) -> list[tuple[str, dict]]:
    """(feature id, location) for every answer-key location in this document."""
    return [
        (f["id"], loc)
        for f in answer_key()["features"]
        for loc in f.get("locations", [])
        if loc["doc"] == doc_id
    ]


def section_body(document: Document, section_id: str) -> tuple[Block | None, list[Block]]:
    """The heading and the body blocks of one section."""
    found = [s for s in sections(document) if s.section_id == section_id]
    assert len(found) == 1, f"{document.meta.doc_id}: section {section_id} found {len(found)} times"
    section = found[0]
    heading = section.heading.block if section.heading else None
    return heading, [p.block for p in section.body]


def section_pages(document: Document, section_id: str) -> set[int | None]:
    section = next(s for s in sections(document) if s.section_id == section_id)
    placed = [section.heading] if section.heading else []
    return {p.page for p in [*placed, *section.body]}


def table_cell(blocks: list[Block], caption: str, row: str, column: str) -> str:
    """The text of one cell of the table whose caption paragraph is `caption`."""
    at = next(i for i, b in enumerate(blocks) if b.text == caption)
    table = next(b for b in blocks[at + 1 :] if b.kind == "table")
    header, *rows = table.rows()
    line = next(r for r in rows if r[0] == row)
    return line[header.index(column)]
