"""The ports every implementation plugs into. Standard library only; the implementations live in
raglab.ingest and raglab.chunk (ingestion), raglab.adapters (embedders), raglab.index (stores)
and raglab.retrieve (retrievers)."""

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from raglab.core.types import Chunk, ChunkId, Document, Page, ScoredChunk


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


class Embedder(Protocol):
    """Turns text into vectors of a fixed dimension; the same text gives the same vector."""

    @property
    def model(self) -> str:
        """The model id, as its publisher names it (BAAI/bge-small-en-v1.5)."""
        ...

    @property
    def revision(self) -> str:
        """The pinned revision of the model files (a commit id), recorded in every run."""
        ...

    @property
    def dimension(self) -> int: ...

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class VectorStore(Protocol):
    """Holds one vector per chunk and finds the nearest ones visible to a tenant. search refuses
    a request without a known tenant (raglab.core.types.visible_tenants) and never returns a
    chunk of another tenant."""

    def add(self, chunks: Sequence[Chunk], vectors: Sequence[Sequence[float]]) -> None: ...

    def search(self, vector: Sequence[float], tenant: str, k: int) -> list[ScoredChunk]: ...

    def chunk_ids(self) -> list[ChunkId]:
        """Every chunk id in the store, in the order they were added."""
        ...


class Retriever(Protocol):
    """The top k chunks for a question, best first, visible to the request's tenant only."""

    @property
    def name(self) -> str:
        """dense, bm25 or hybrid: recorded in the run's config."""
        ...

    def retrieve(self, query: str, tenant: str, k: int) -> list[ScoredChunk]: ...
