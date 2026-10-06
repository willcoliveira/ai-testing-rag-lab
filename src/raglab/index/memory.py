"""The in-memory vector store: one numpy matrix of unit vectors, searched by cosine similarity.

The tenant filter runs before ranking: a request's tenant (raglab.core.types.visible_tenants)
selects the rows it may see, and only those are scored. A request without a known tenant is
refused, never answered from every tenant, and the results are checked once more on the way out
(check_visible). Ties are broken by chunk id, so a search is deterministic. Lab scale: the 228
chunks of the pack need no database; Qdrant can sit behind the same port later.
"""

from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray

from raglab.core.types import Chunk, ChunkId, ScoredChunk, check_visible, visible_tenants


def _unit_rows(vectors: NDArray[np.float64]) -> NDArray[np.float64]:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return np.divide(vectors, norms, out=np.zeros_like(vectors), where=norms > 0)


class InMemoryStore:
    def __init__(self, dimension: int) -> None:
        if dimension < 1:
            raise ValueError(f"dimension must be at least 1, not {dimension}")
        self.dimension = dimension
        self._chunks: list[Chunk] = []
        self._matrix: NDArray[np.float64] = np.zeros((0, dimension))

    def __len__(self) -> int:
        return len(self._chunks)

    def add(self, chunks: Sequence[Chunk], vectors: Sequence[Sequence[float]]) -> None:
        if len(chunks) != len(vectors):
            raise ValueError(f"{len(chunks)} chunks but {len(vectors)} vectors")
        if not chunks:
            return
        matrix = np.asarray(vectors, dtype=np.float64)
        if matrix.ndim != 2 or matrix.shape[1] != self.dimension:
            raise ValueError(f"vectors must have dimension {self.dimension}, got {matrix.shape}")
        known = {c.chunk_id for c in self._chunks}
        for chunk in chunks:
            if chunk.chunk_id in known:
                raise ValueError(f"chunk {chunk.chunk_id} is already in the store")
            known.add(chunk.chunk_id)
        self._chunks.extend(chunks)
        self._matrix = np.vstack([self._matrix, _unit_rows(matrix)])

    def chunk_ids(self) -> list[ChunkId]:
        return [c.chunk_id for c in self._chunks]

    def search(self, vector: Sequence[float], tenant: str, k: int) -> list[ScoredChunk]:
        visible = visible_tenants(tenant)
        if k < 1:
            raise ValueError(f"k must be at least 1, not {k}")
        query = np.asarray(vector, dtype=np.float64)
        if query.shape != (self.dimension,):
            raise ValueError(f"the query must have dimension {self.dimension}, got {query.shape}")
        rows = [i for i, c in enumerate(self._chunks) if c.tenant in visible]
        if not rows:
            return []
        norm = float(np.linalg.norm(query))
        unit = query / norm if norm else query
        scores = self._matrix[rows] @ unit
        ranked = sorted(
            zip(rows, scores.tolist(), strict=True),
            key=lambda pair: (-pair[1], self._chunks[pair[0]].chunk_id),
        )
        results = [ScoredChunk(self._chunks[i], float(score)) for i, score in ranked[:k]]
        return check_visible(results, tenant)
