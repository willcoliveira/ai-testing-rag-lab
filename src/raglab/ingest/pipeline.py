"""register -> parse -> chunk -> inventory.

The register (corpus/register.yaml) is the only list of documents a clean run reads. Each entry's
file is parsed by its format; its metadata comes from the register (id, status, tenant, path) and
from the front matter of its canonical Markdown file (title, version, kind, licence): the file
itself for Markdown, the source next to it (same name, `.md`) for the PDF, the HTML export and the
scanned page. Only the front matter of that source is read, never its text: the text of a
rendered document comes from the rendered file (corpus/SPEC.md, section 3).

Every check fails closed: a missing or unknown tenant, a register entry whose front matter names
another id, tenant or format, an unreadable file or a document that yields no chunk stops the run
with an error that names the document.
"""

from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path

from raglab.chunk.sections import ChunkSettings, SectionChunker, empty_sections
from raglab.core.ports import Parser
from raglab.core.types import Chunk, Document, DocumentMeta, TenantError
from raglab.ingest import frontmatter, html, ocr, register
from raglab.ingest.markdown import MarkdownParser
from raglab.ingest.pdf import PdfParser

PARSERS: dict[str, Parser] = {
    p.format: p for p in (MarkdownParser(), PdfParser(), html.HtmlParser(), ocr.OcrParser())
}
FRONT_FIELDS = ("id", "title", "version", "tenant", "kind", "licence", "format")


class IngestError(ValueError):
    pass


@dataclass(frozen=True)
class Inventory:
    settings: ChunkSettings
    tools: dict[str, str]
    documents: tuple[Document, ...]
    chunks: tuple[Chunk, ...]
    # "<path>: <section id>" for every empty leaf section (reported, never chunked)
    empty_sections: tuple[str, ...] = ()


@contextmanager
def _utf8(rel: str, path: Path) -> Generator[None]:
    """A file that is not UTF-8 text stops the run with an error naming the document."""
    try:
        yield
    except UnicodeDecodeError as error:
        raise IngestError(
            f"{rel}: {path.name} is not UTF-8 text ({error.reason} at byte {error.start})"
        ) from error


def metadata_file(root: Path, rel: str) -> Path:
    """The Markdown file whose front matter describes the document at rel."""
    path = root / rel
    source = path if path.suffix == ".md" else path.with_suffix(".md")
    if not source.is_file():
        raise IngestError(f"{rel}: no Markdown source {source.name} with its front matter")
    return source


def describe(root: Path, doc_id: str, status: str, tenant: str, rel: str, fmt: str) -> DocumentMeta:
    """A document's metadata: the caller's id, status and tenant, checked against the front
    matter of its Markdown source, plus the source's title, version, kind and licence."""
    source = metadata_file(root, rel)
    with _utf8(rel, source):
        front = frontmatter.read(source, rel)
    missing = [f for f in FRONT_FIELDS if not front.get(f)]
    if missing:
        raise IngestError(f"{rel}: front matter lacks {', '.join(missing)}")
    for name, expected in (("id", doc_id), ("tenant", tenant), ("format", fmt)):
        if front[name] != expected:
            raise IngestError(
                f"{rel}: front matter {name} {front[name]!r} disagrees with {expected!r}"
            )
    return DocumentMeta(
        doc_id=doc_id,
        title=front["title"],
        version=front["version"],
        status=status,
        tenant=tenant,
        kind=front["kind"],
        licence=front["licence"],
        path=rel,
        format=fmt,
    )


def parse(root: Path, meta: DocumentMeta) -> Document:
    """The document at meta.path, parsed by its format. An HTML export's corpus-id meta, when it
    has one, must name the same document."""
    path = root / meta.path
    with _utf8(meta.path, path):
        if meta.format == "html":
            _, meta_tags = html.read(path)
            if meta_tags.get("id", meta.doc_id) != meta.doc_id:
                raise IngestError(f"{meta.path}: its corpus-id meta names {meta_tags['id']!r}")
        document = Document(meta, PARSERS[meta.format].parse(path))
    if not document.text().strip():
        raise IngestError(f"{meta.path}: no text was extracted")
    return document


def tools(documents: tuple[Document, ...]) -> dict[str, str]:
    """The parser versions the inventory depends on (Tesseract only when a page was OCR'd)."""
    found = {"pypdf": version("pypdf"), "pyyaml": version("pyyaml")}
    if any(d.meta.format == "png" for d in documents):
        found["pytesseract"] = version("pytesseract")
        found["tesseract"] = ocr.tesseract_version()
    return found


def chunk_all(documents: tuple[Document, ...], settings: ChunkSettings) -> tuple[Chunk, ...]:
    """Every document's chunks, in document order; a document with no chunk stops the run."""
    chunker = SectionChunker(settings)
    chunks: list[Chunk] = []
    for document in documents:
        found = chunker.chunk(document)
        if not found:
            raise IngestError(f"{document.meta.path}: no chunk was produced")
        chunks.extend(found)
    owners: dict[str, str] = {}
    for chunk in chunks:
        if (owner := owners.get(chunk.chunk_id)) is not None:
            raise IngestError(f"{chunk.path}: chunk id {chunk.chunk_id} is already used by {owner}")
        owners[chunk.chunk_id] = chunk.path
    return tuple(chunks)


def ingest(root: Path, settings: ChunkSettings | None = None) -> Inventory:
    """The chunk inventory of every document in the register."""
    settings = settings or ChunkSettings()
    try:
        entries = register.read(root)
        documents = tuple(
            parse(root, describe(root, e.doc_id, e.status, e.tenant, e.path, e.format))
            for e in entries
        )
    except (register.RegisterError, frontmatter.FrontMatterError, TenantError) as error:
        raise IngestError(str(error)) from error
    empty = tuple(f"{d.meta.path}: {s}" for d in documents for s in empty_sections(d))
    return Inventory(settings, tools(documents), documents, chunk_all(documents, settings), empty)


def section_chunks(
    root: Path, doc_id: str, section_id: str, settings: ChunkSettings | None = None
) -> tuple[Chunk, ...]:
    """The chunks of one section of one register document at the given settings, in order: the
    same chunks the whole inventory has for it, since a document is chunked on its own. The run
    record validator reads a behaviour case's may_quote section this way (S4)."""
    try:
        entries = {e.doc_id: e for e in register.read(root)}
        if doc_id not in entries:
            raise IngestError(f"{doc_id} is not in the register")
        e = entries[doc_id]
        document = parse(root, describe(root, e.doc_id, e.status, e.tenant, e.path, e.format))
    except (register.RegisterError, frontmatter.FrontMatterError, TenantError) as error:
        raise IngestError(str(error)) from error
    chunker = SectionChunker(settings or ChunkSettings())
    return tuple(c for c in chunker.chunk(document) if c.section_id == section_id)
