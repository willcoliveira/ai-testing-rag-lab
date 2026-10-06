"""The ports of the ingestion side: a parser per file format and a chunker. Standard library only;
the implementations live in raglab.ingest and raglab.chunk."""

from pathlib import Path
from typing import Protocol

from raglab.core.types import Chunk, Document, Page


class Parser(Protocol):
    """Reads one file format into pages of blocks: the text a reader of that file sees."""

    @property
    def format(self) -> str:
        """The format this parser reads: md, pdf, html or png."""
        ...

    def parse(self, path: Path) -> tuple[Page, ...]: ...


class Chunker(Protocol):
    """Cuts a parsed document into chunks; the same document and settings give the same chunks."""

    def chunk(self, document: Document) -> list[Chunk]: ...
