"""Dense retrieval: the question's vector against the store's, by cosine similarity."""

from raglab.core.ports import Embedder, VectorStore
from raglab.core.types import Chunk, ScoredChunk, check_visible, visible_tenants


def index_chunks(embedder: Embedder, store: VectorStore, chunks: list[Chunk]) -> None:
    """Embed every chunk's text and add it to the store."""
    store.add(chunks, embedder.embed_documents([c.text for c in chunks]))


class DenseRetriever:
    def __init__(self, embedder: Embedder, store: VectorStore) -> None:
        self.embedder = embedder
        self.store = store

    @property
    def name(self) -> str:
        return "dense"

    def retrieve(self, query: str, tenant: str, k: int) -> list[ScoredChunk]:
        visible_tenants(tenant)  # refuse before any work
        results = self.store.search(self.embedder.embed_query(query), tenant, k)
        return check_visible(results, tenant)
