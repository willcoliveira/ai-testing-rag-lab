"""Hybrid retrieval: dense and BM25 fused by reciprocal rank (RRF).

Each retriever returns its top `candidates` (deeper than k, so a chunk ranked 7th by one and 2nd
by the other can still make the top k); a chunk's fused score is the sum over the lists it is in
of 1 / (rrf_k + rank), rank counted from 1. rrf_k = 60 is the constant of Cormack, Clarke and
Buettcher (SIGIR 2009). Both inputs are tenant-filtered, and the fused list is checked again.
Ties are broken by chunk id.
"""

from raglab.core.ports import Retriever
from raglab.core.types import Chunk, ScoredChunk, check_visible, visible_tenants

DEFAULT_CANDIDATES = 50
DEFAULT_RRF_K = 60


def reciprocal_rank_fusion(
    rankings: list[list[ScoredChunk]], rrf_k: int = DEFAULT_RRF_K
) -> list[ScoredChunk]:
    """Every chunk of the rankings, by its fused score, best first."""
    scores: dict[str, float] = {}
    chunks: dict[str, Chunk] = {}
    for ranking in rankings:
        for rank, result in enumerate(ranking, start=1):
            key = result.chunk.chunk_id
            scores[key] = scores.get(key, 0.0) + 1.0 / (rrf_k + rank)
            chunks[key] = result.chunk
    ordered = sorted(scores, key=lambda key: (-scores[key], key))
    return [ScoredChunk(chunks[key], scores[key]) for key in ordered]


class HybridRetriever:
    def __init__(
        self,
        dense: Retriever,
        lexical: Retriever,
        candidates: int = DEFAULT_CANDIDATES,
        rrf_k: int = DEFAULT_RRF_K,
    ) -> None:
        if candidates < 1 or rrf_k < 0:
            raise ValueError(
                f"candidates must be at least 1 and rrf_k 0 or more: {candidates}, {rrf_k}"
            )
        self.dense = dense
        self.lexical = lexical
        self.candidates = candidates
        self.rrf_k = rrf_k

    @property
    def name(self) -> str:
        return "hybrid"

    def retrieve(self, query: str, tenant: str, k: int) -> list[ScoredChunk]:
        visible_tenants(tenant)
        if k < 1:
            raise ValueError(f"k must be at least 1, not {k}")
        depth = max(k, self.candidates)
        rankings = [
            self.dense.retrieve(query, tenant, depth),
            self.lexical.retrieve(query, tenant, depth),
        ]
        return check_visible(reciprocal_rank_fusion(rankings, self.rrf_k)[:k], tenant)
