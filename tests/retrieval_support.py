"""Small chunks and retrievers for the retrieval tests, built with the fake embedder."""

from raglab.adapters.fake import HashingEmbedder
from raglab.core.ports import Retriever
from raglab.core.types import Chunk, ChunkId
from raglab.index.memory import InMemoryStore
from raglab.retrieve.bm25 import BM25Retriever
from raglab.retrieve.dense import DenseRetriever, index_chunks
from raglab.retrieve.hybrid import HybridRetriever


def make_chunk(chunk_id: str, tenant: str, text: str, section: str = "1") -> Chunk:
    doc = chunk_id.split("@", 1)[0]
    return Chunk(
        chunk_id=ChunkId(chunk_id),
        doc_id=doc,
        version="1.0",
        status="approved",
        tenant=tenant,
        kind="company",
        title=doc,
        section_id=section,
        section_title=section,
        page=None,
        page_end=None,
        licence="CC-BY-4.0",
        path=f"{doc}.md",
        char_start=0,
        char_end=len(text),
        text=text,
    )


# Three tenants' worth of chunks; B-1 and A-1 say almost the same thing, so a query for one
# ranks the other high unless the filter holds.
CHUNKS = [
    make_chunk("A-1@1.0/1/1", "tenant-a", "Passwords must be at least 15 characters long."),
    make_chunk("A-2@1.0/1/1", "tenant-a", "Administrators must always use MFA."),
    make_chunk("B-1@1.0/1/1", "tenant-b", "Passwords must be at least 12 characters long."),
    make_chunk("B-2@1.0/1/1", "tenant-b", "Mirrowfen staff use hardware keys for MFA."),
    make_chunk("X-1@1.0/1/1", "shared", "NIST guidance on password length and MFA."),
]


def dense(chunks: list[Chunk]) -> DenseRetriever:
    embedder = HashingEmbedder()
    store = InMemoryStore(embedder.dimension)
    index_chunks(embedder, store, chunks)
    return DenseRetriever(embedder, store)


def retrievers(chunks: list[Chunk]) -> dict[str, Retriever]:
    d = dense(chunks)
    lexical = BM25Retriever(chunks)
    return {"dense": d, "bm25": lexical, "hybrid": HybridRetriever(d, lexical)}
