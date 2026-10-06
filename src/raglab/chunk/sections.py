"""The section-aware chunker.

1. **Sections.** A document splits at every heading of level 2 or deeper; its section id is the
   heading's leading token (4.1, A.2, Q3). The text under the title before the first section is
   the section `intro`. A section with no text under its heading gives no chunk (its heading is a
   parent, such as "4 Password rules", whose text is all in 4.1, 4.2, ...).
2. **Units.** Each paragraph, list item and table of a section is one unit; the section heading
   travels with the first unit. A unit longer than the budget is split, a table between rows and a
   paragraph between sentences, into pieces that each fit (a single row or sentence longer than
   the budget is kept whole: a chunk exceeds the budget only then).
3. **Packing.** Units are packed in order into chunks of at most `chunk_size` characters. Each
   chunk after the first of a section starts with the last `overlap` units of the one before
   (fewer when they would not fit next to a new unit). Chunks never cross a section boundary.

A chunk is a contiguous span of the document's text, so its text, its character span and its
sha256 agree. Ids are `<doc id>@<version>/<section id>/<n>`: the same document and settings give
the same ids. The contextual prefix (document and section title before each chunk) is off; S2
decides whether to turn it on.
"""

import re
from dataclasses import dataclass

from raglab.core.types import (
    BLOCK_SEPARATOR,
    Chunk,
    ChunkId,
    Document,
    PlacedBlock,
    split_heading,
)

DEFAULT_CHUNK_SIZE = 1200
DEFAULT_OVERLAP = 1
INTRO = "intro"
SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class ChunkSettings:
    chunk_size: int = DEFAULT_CHUNK_SIZE
    overlap: int = DEFAULT_OVERLAP  # paragraphs (units) repeated at the start of the next chunk

    def __post_init__(self) -> None:
        if self.chunk_size < 1:
            raise ValueError(f"chunk size must be at least 1 character, not {self.chunk_size}")
        if self.overlap < 0:
            raise ValueError(f"overlap must be 0 or more paragraphs, not {self.overlap}")


@dataclass(frozen=True)
class Section:
    section_id: str
    title: str
    heading: PlacedBlock | None
    body: tuple[PlacedBlock, ...]


@dataclass(frozen=True)
class Unit:
    start: int
    end: int
    page: int | None
    page_end: int | None


def sections(document: Document) -> list[Section]:
    """The sections of a document, in order (the intro first, even when it is empty)."""
    out: list[Section] = []
    section_id, title = INTRO, document.meta.title
    heading: PlacedBlock | None = None
    body: list[PlacedBlock] = []
    for placed in document.placed_blocks():
        block = placed.block
        if block.kind == "heading" and block.level >= 2:
            out.append(Section(section_id, title, heading, tuple(body)))
            section_id, title = split_heading(block.text)
            heading, body = placed, []
        elif block.kind == "heading" and section_id == INTRO and heading is None and not body:
            heading, title = placed, block.text  # the document title opens the intro
        else:
            body.append(placed)
    out.append(Section(section_id, title, heading, tuple(body)))
    return out


def empty_sections(document: Document) -> list[str]:
    """Leaf sections with a heading and no text: '## 2 Reserved' gives no chunk, like a parent
    heading, but unlike a parent nothing under it carries its text, so it is reported (S1b,
    user decision: report it, and fail when the project's own pack has one)."""
    found = sections(document)
    out: list[str] = []
    for i, section in enumerate(found):
        if section.section_id == INTRO or section.body:
            continue
        following = found[i + 1].section_id if i + 1 < len(found) else ""
        if not following.startswith(f"{section.section_id}."):
            out.append(section.section_id)
    return out


def _pieces(placed: PlacedBlock, budget: int, lead: int = 0) -> list[Unit]:
    """A block as units of at most budget characters: whole if it fits, else split between table
    rows or sentences, consecutive pieces packed together while they fit. lead is the length of
    the text that will precede the first unit (the section heading and its separator)."""
    block = placed.block
    if lead + len(block.text) <= budget:
        return [Unit(placed.start, placed.end, placed.page, placed.page)]
    separator = re.compile(r"\n") if block.kind == "table" else SENTENCE_END
    bounds: list[tuple[int, int]] = []
    position = 0
    for match in separator.finditer(block.text):
        bounds.append((position, match.start()))
        position = match.end()
    bounds.append((position, len(block.text)))
    units: list[Unit] = []
    lo, hi = bounds[0]
    for start, end in bounds[1:]:
        if (0 if units else lead) + end - lo <= budget:
            hi = end
        else:
            units.append(Unit(placed.start + lo, placed.start + hi, placed.page, placed.page))
            lo, hi = start, end
    units.append(Unit(placed.start + lo, placed.start + hi, placed.page, placed.page))
    return units


def _units(section: Section, budget: int) -> list[Unit]:
    heading = section.heading
    lead = heading.end - heading.start + len(BLOCK_SEPARATOR) if heading else 0
    units: list[Unit] = []
    for placed in section.body:
        units.extend(_pieces(placed, budget, 0 if units else lead))
    if units and heading is not None:
        first = units[0]
        units[0] = Unit(heading.start, first.end, heading.page, first.page_end)
    return units


def _groups(units: list[Unit], settings: ChunkSettings) -> list[tuple[int, int]]:
    """Unit index ranges [lo, hi) of each chunk of a section."""

    def length(lo: int, hi: int) -> int:
        return units[hi - 1].end - units[lo].start

    groups: list[tuple[int, int]] = []
    new = 0
    while new < len(units):
        # overlap: start with the last units of the chunk before, never all of it
        lo = max(new - settings.overlap, groups[-1][0] + 1) if groups else new
        while lo < new and length(lo, new + 1) > settings.chunk_size:
            lo += 1
        hi = new + 1
        while hi < len(units) and length(lo, hi + 1) <= settings.chunk_size:
            hi += 1
        groups.append((lo, hi))
        new = hi
    return groups


def _slug(text: str) -> str:
    """An id-safe form of a version or section id: whitespace as '_', other symbols as '-'."""
    text = re.sub(r"\s+", "_", text.strip())
    return re.sub(r"[^A-Za-z0-9._-]+", "-", text) or "-"


class SectionChunker:
    def __init__(self, settings: ChunkSettings | None = None) -> None:
        self.settings = settings or ChunkSettings()

    def chunk(self, document: Document) -> list[Chunk]:
        meta = document.meta
        text = document.text()
        chunks: list[Chunk] = []
        seen: dict[str, int] = {}
        for section in sections(document):
            units = _units(section, self.settings.chunk_size)
            if not units:
                continue
            key = _slug(section.section_id)
            # a repeated section id, or two that slug alike ('Ä x' and 'Ö x'), stays unique
            seen[key] = seen.get(key, 0) + 1
            if seen[key] > 1:
                key += f"~{seen[key]}"
            for n, (lo, hi) in enumerate(_groups(units, self.settings), start=1):
                start, end = units[lo].start, units[hi - 1].end
                chunks.append(
                    Chunk(
                        chunk_id=ChunkId(f"{meta.doc_id}@{_slug(meta.version)}/{key}/{n}"),
                        doc_id=meta.doc_id,
                        version=meta.version,
                        status=meta.status,
                        tenant=meta.tenant,
                        kind=meta.kind,
                        title=meta.title,
                        section_id=section.section_id,
                        section_title=section.title,
                        page=units[lo].page,
                        page_end=units[hi - 1].page_end,
                        licence=meta.licence,
                        path=meta.path,
                        char_start=start,
                        char_end=end,
                        text=text[start:end],
                    )
                )
        return chunks
