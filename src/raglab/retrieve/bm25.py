"""Lexical retrieval: BM25 (Okapi, rank-bm25's defaults k1 1.5, b 0.75) over the chunk text.

The filter runs before ranking: each request tenant gets its own BM25 index, built over the chunks
it may see only, so another tenant's chunks are neither ranked nor counted in the term statistics.
Words are lower-cased runs of letters and digits; no stemming and no stop words (lab choice: the
policy pack's questions reuse its words). Ties are broken by chunk id.
"""

import re
from collections.abc import Sequence

from rank_bm25 import BM25Okapi

from raglab.core.types import Chunk, ScoredChunk, check_visible, visible_tenants

WORD = re.compile(r"[a-z0-9]+")


def tokens(text: str) -> list[str]:
    return WORD.findall(text.lower())


class BM25Retriever:
    def __init__(self, chunks: Sequence[Chunk]) -> None:
        self.chunks = list(chunks)
        self._indexes: dict[frozenset[str], tuple[list[Chunk], BM25Okapi | None]] = {}

    @property
    def name(self) -> str:
        return "bm25"

    def _index(self, visible: frozenset[str]) -> tuple[list[Chunk], BM25Okapi | None]:
        if visible not in self._indexes:
            own = [c for c in self.chunks if c.tenant in visible]
            self._indexes[visible] = (
                own,
                BM25Okapi([tokens(c.text) for c in own]) if own else None,
            )
        return self._indexes[visible]

    def retrieve(self, query: str, tenant: str, k: int) -> list[ScoredChunk]:
        visible = visible_tenants(tenant)
        if k < 1:
            raise ValueError(f"k must be at least 1, not {k}")
        chunks, index = self._index(visible)
        if index is None:
            return []
        scores = index.get_scores(tokens(query)).tolist()
        ranked = sorted(
            zip(chunks, scores, strict=True), key=lambda pair: (-pair[1], pair[0].chunk_id)
        )
        return check_visible([ScoredChunk(c, float(s)) for c, s in ranked[:k]], tenant)
