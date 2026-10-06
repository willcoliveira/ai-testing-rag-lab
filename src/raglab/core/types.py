"""The types every layer shares: a parsed document, its pages and blocks, and its chunks.

Standard library only (scripts/check_architecture.py). A parser turns a file into pages of blocks;
the pipeline adds the document's metadata; a chunker cuts the document's text into chunks that
carry everything retrieval, citation and tenant isolation need.
"""

import hashlib
import re
from dataclasses import dataclass, field
from typing import Literal, NewType

ChunkId = NewType("ChunkId", str)

# The tenants a document can belong to. "shared" documents are visible to every tenant.
TENANTS = frozenset({"tenant-a", "tenant-b", "shared"})

BlockKind = Literal["heading", "paragraph", "item", "table"]

# Blocks of a document's text are separated by a blank line, rows of a table by a newline.
BLOCK_SEPARATOR = "\n\n"

# A section id is the leading token of a heading: 4, 4.1, 3.1.1.2, A, A.2 or Q1 (corpus/SPEC.md,
# section 5), in ASCII digits only (a fullwidth or Arabic-Indic '4' is not one). A heading without
# one is identified by its whole text.
SECTION_ID = re.compile(r"^(?:\d+(?:\.\d+)*|[A-Z](?:\.\d+)*|Q\d+)$", flags=re.ASCII)


# The tenants a retrieval request can name. A person belongs to one company; "shared" is a kind of
# document, not anyone's tenant, so a request for it is refused.
REQUEST_TENANTS = frozenset({"tenant-a", "tenant-b"})


class TenantError(ValueError):
    """A document or chunk has no tenant, or one that is not known: ingestion stops (fails
    closed) rather than index content no tenant filter can scope."""


def check_tenant(tenant: object, where: str) -> str:
    """The tenant, if it is one of TENANTS; otherwise TenantError naming where it came from."""
    if not isinstance(tenant, str) or tenant not in TENANTS:
        raise TenantError(f"{where}: tenant {tenant!r} is not one of {sorted(TENANTS)}")
    return tenant


def visible_tenants(tenant: object) -> frozenset[str]:
    """The chunk tenants a request for this tenant may see: its own and the shared references.
    A request with no tenant, an empty one, "shared" or an unknown one raises TenantError: the
    tenant filter fails closed, it never falls back to "everything"."""
    if not isinstance(tenant, str) or tenant not in REQUEST_TENANTS:
        raise TenantError(
            f"retrieval needs the tenant of the request, one of {sorted(REQUEST_TENANTS)}; "
            f"got {tenant!r}"
        )
    return frozenset({tenant, "shared"})


def check_visible(results: "list[ScoredChunk]", tenant: str) -> "list[ScoredChunk]":
    """The results, after checking that every one is visible to the tenant; a chunk of another
    tenant raises TenantError (the second line of the filter, after the one before ranking)."""
    visible = visible_tenants(tenant)
    for result in results:
        if result.chunk.tenant not in visible:
            raise TenantError(
                f"chunk {result.chunk.chunk_id} of {result.chunk.tenant} was retrieved for {tenant}"
            )
    return results


def split_heading(text: str) -> tuple[str, str]:
    """(section id, title) of a heading: '4.1 Minimum length' -> ('4.1', 'Minimum length').
    A heading whose first token is not a section id is its own id, with the same title."""
    token, _, rest = text.strip().partition(" ")
    if SECTION_ID.match(token) and rest.strip():
        return token, rest.strip()
    return text.strip(), text.strip()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Block:
    """One block of a page as a reader sees it: a heading, a paragraph, a list item ('- ...') or a
    table (one '| cell | cell |' line per row, the header row first)."""

    kind: BlockKind
    text: str
    level: int = 0  # headings: 1 for the title, 2 and deeper for sections

    def __post_init__(self) -> None:
        if not self.text or self.text != self.text.strip():
            raise ValueError(f"a {self.kind} block needs non-empty, stripped text: {self.text!r}")
        if (self.kind == "heading") != (self.level > 0):
            raise ValueError(f"only a heading has a level: {self.kind} at level {self.level}")

    def rows(self) -> list[list[str]]:
        """The cells of a table block, row by row."""
        if self.kind != "table":
            raise ValueError("only a table block has rows")
        return [[c.strip() for c in line.strip().strip("|").split("|")] for line in self.lines()]

    def lines(self) -> list[str]:
        return self.text.split("\n")


def table_block(rows: list[list[str]]) -> Block:
    """A table block from its rows of cell texts (the header row first)."""
    clean = [[" ".join(cell.replace("|", "/").split()) for cell in row] for row in rows]
    return Block("table", "\n".join("| " + " | ".join(row) + " |" for row in clean))


@dataclass(frozen=True)
class Page:
    """A page of a document. number is the print page for the formats that have pages (PDF, the
    scanned PNG), and None for Markdown and HTML."""

    number: int | None
    blocks: tuple[Block, ...]


@dataclass(frozen=True)
class DocumentMeta:
    """What the register and the document's front matter say about a document."""

    doc_id: str
    title: str
    version: str
    status: str  # the register's status: approved, superseded or reference
    tenant: str
    kind: str  # company, external or attack (front matter)
    licence: str
    path: str  # the file ingestion read, relative to the repo root
    format: str  # md, pdf, html or png

    def __post_init__(self) -> None:
        check_tenant(self.tenant, f"document {self.doc_id}")
        for name in ("doc_id", "title", "version", "status", "kind", "licence", "path", "format"):
            if not getattr(self, name):
                raise ValueError(f"document {self.doc_id or '?'}: {name} is empty")


@dataclass(frozen=True)
class Document:
    meta: DocumentMeta
    pages: tuple[Page, ...]

    def placed_blocks(self) -> list["PlacedBlock"]:
        """Every block with its page and its character span in text()."""
        placed: list[PlacedBlock] = []
        offset = 0
        for page in self.pages:
            for block in page.blocks:
                if placed:
                    offset += len(BLOCK_SEPARATOR)
                placed.append(PlacedBlock(block, page.number, offset, offset + len(block.text)))
                offset += len(block.text)
        return placed

    def text(self) -> str:
        """The document's text: every block of every page, separated by a blank line."""
        return BLOCK_SEPARATOR.join(b.text for p in self.pages for b in p.blocks)


@dataclass(frozen=True)
class PlacedBlock:
    block: Block
    page: int | None
    start: int
    end: int


@dataclass(frozen=True)
class Chunk:
    """A contiguous span of a document's text, with the metadata retrieval and citation need.
    The text is document.text()[char_start:char_end] and sha256 is its digest."""

    chunk_id: ChunkId
    doc_id: str
    version: str
    status: str
    tenant: str
    kind: str
    title: str
    section_id: str
    section_title: str
    page: int | None  # the print page the chunk starts on (PDF and PNG only)
    page_end: int | None  # the print page it ends on
    licence: str
    path: str
    char_start: int
    char_end: int
    text: str
    sha256: str = field(default="")

    def __post_init__(self) -> None:
        check_tenant(self.tenant, f"chunk {self.chunk_id}")
        if not self.section_id:
            raise ValueError(f"chunk {self.chunk_id}: no section")
        if not self.text.strip():
            raise ValueError(f"chunk {self.chunk_id}: no text")
        if self.char_end - self.char_start != len(self.text):
            raise ValueError(f"chunk {self.chunk_id}: span does not match its text")
        digest = sha256_text(self.text)
        if not self.sha256:
            object.__setattr__(self, "sha256", digest)
        elif self.sha256 != digest:
            raise ValueError(f"chunk {self.chunk_id}: sha256 does not match its text")


@dataclass(frozen=True)
class ScoredChunk:
    """A retrieved chunk and the score its retriever gave it (higher is better; scores of
    different retrievers are not comparable)."""

    chunk: Chunk
    score: float
