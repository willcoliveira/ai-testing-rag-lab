"""The ports every implementation plugs into. Standard library only; the implementations live in
raglab.ingest and raglab.chunk (ingestion), raglab.adapters (embedders and chat models),
raglab.index (stores), raglab.retrieve (retrievers) and raglab.guard (guardrails)."""

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from raglab.core.types import (
    Answer,
    ChatReply,
    ChatRequest,
    Chunk,
    ChunkId,
    Document,
    GuardEvent,
    JudgeItem,
    Page,
    ScoredChunk,
    Verdict,
)


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


class ChatModel(Protocol):
    """A chat model behind one port: the fake one for tests and the fake container, an
    OpenAI-compatible server (Ollama) for live runs. complete raises ChatUnavailable when no reply
    came (timeout, connection error, HTTP error); a reply that does not fit the schema is returned
    as it came, and the caller decides (status invalid_output)."""

    @property
    def model(self) -> str:
        """The model as the run record names it: a pinned tag, or the fake's name."""
        ...

    def describe(self) -> dict[str, object]:
        """What the run record and /version say about the model: provider, model, digest and the
        request settings."""
        ...

    def complete(self, request: ChatRequest) -> ChatReply: ...


class Judge(Protocol):
    """One criterion of docs/CRITERIA.md judged per call (S5): the judge model behind the
    ChatModel port (raglab.judge.llm), or a scripted model in the tests. judge never raises for a
    model that gave no reply or a reply off the verdict schema: the verdict is unable_to_verify,
    with status unavailable or invalid_output, and the caller counts it."""

    @property
    def version(self) -> str:
        """The judge prompt's version (judge-v2 since the second sign-off), recorded with every
        judged run."""
        ...

    def fingerprint(self) -> str:
        """The sha256 of the judge prompt's texts, frames, criteria and schema."""
        ...

    def describe(self) -> dict[str, object]:
        """What a judged record says about the judge model: provider, model, digest, settings."""
        ...

    def judge(self, item: JudgeItem) -> Verdict: ...


class Guardrail(Protocol):
    """One guard layer, with a check at each stage of a request (docs/GUARDRAILS.md). A check that
    returns an event stops the request: at input it is refused before retrieval, after retrieval
    or on the output the answer is withheld (status blocked). drop_retrieved (S7) is the one step
    that does not stop it: it leaves chunks out of the prompt, with an event per document, and the
    answer goes on from the rest. An event's reason names the rule and the layer, never the text a
    check removed or withheld."""

    @property
    def name(self) -> str: ...

    def fingerprint(self) -> str:
        """The sha256 of this layer's rules (S7): a baseline made under another guard set is
        stale until a replay shows the new set changes nothing on its records."""
        ...

    def check_input(
        self, question: str, tenant: str | None, caller_tenants: frozenset[str] | None
    ) -> GuardEvent | None:
        """caller_tenants: the tenants the caller may use (the API's token), None for a local run
        (CLI, eval) with no caller."""
        ...

    def check_retrieved(
        self, tenant: str, retrieved: Sequence[ScoredChunk]
    ) -> GuardEvent | None: ...

    def drop_retrieved(
        self, tenant: str, retrieved: Sequence[ScoredChunk]
    ) -> tuple[tuple[ScoredChunk, ...], tuple[GuardEvent, ...]]:
        """(the chunks kept, in rank order; an event per document left out)."""
        ...

    def check_output(self, answer: Answer, retrieved: Sequence[ScoredChunk]) -> GuardEvent | None:
        """retrieved: the chunks the prompt was built from, after every drop step."""
        ...
