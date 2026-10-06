"""The fake embedder, the in-memory store and the three retrievers on small fixtures: the
L10 (embedder-deterministic) and L11 (index-holds-every-chunk) checks with the fake embedder,
ordering, tie-breaks, and reciprocal rank fusion against hand-computed values."""

import math

import pytest

from raglab.adapters.fake import HashingEmbedder
from raglab.core.types import ScoredChunk
from raglab.index.memory import InMemoryStore
from raglab.retrieve.bm25 import BM25Retriever, tokens
from raglab.retrieve.hybrid import HybridRetriever, reciprocal_rank_fusion
from tests.retrieval_support import CHUNKS, dense, make_chunk

pytestmark = [pytest.mark.unit, pytest.mark.retrieval]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def test_hashing_embedder_is_deterministic_normalised_and_word_based():
    embedder = HashingEmbedder(64)
    first = embedder.embed_documents(["Administrators must always use MFA."])[0]
    assert first == embedder.embed_query("Administrators must always use MFA.")
    assert len(first) == 64
    assert math.isclose(math.sqrt(sum(x * x for x in first)), 1.0)
    assert embedder.embed_query("") == [0.0] * 64
    near = embedder.embed_query("administrators use mfa")
    assert cosine(first, near) > cosine(first, embedder.embed_query("kiosk screen saver"))
    with pytest.raises(ValueError, match="dimension"):
        HashingEmbedder(1)


def test_store_holds_every_chunk_once_and_refuses_bad_input():
    embedder = HashingEmbedder()
    store = InMemoryStore(embedder.dimension)
    store.add(CHUNKS, embedder.embed_documents([c.text for c in CHUNKS]))
    assert store.chunk_ids() == [c.chunk_id for c in CHUNKS]
    assert len(store) == len(CHUNKS)
    with pytest.raises(ValueError, match="already in the store"):
        store.add(CHUNKS[:1], [embedder.embed_query("x")])
    with pytest.raises(ValueError, match="2 chunks but 1 vectors"):
        store.add(CHUNKS[:2], [embedder.embed_query("x")])
    with pytest.raises(ValueError, match="dimension"):
        store.add([make_chunk("Z@1/1/1", "tenant-a", "z")], [[1.0, 0.0]])
    with pytest.raises(ValueError, match="dimension"):
        store.search([1.0], "tenant-a", 3)
    with pytest.raises(ValueError, match="k must be"):
        store.search(embedder.embed_query("x"), "tenant-a", 0)


def test_store_ranks_by_cosine_and_breaks_ties_by_chunk_id():
    store = InMemoryStore(2)
    chunks = [make_chunk(f"A-{n}@1/1/1", "tenant-a", f"text {n}") for n in (3, 1, 2)]
    store.add(chunks, [[1.0, 0.0], [0.0, 1.0], [1.0, 0.0]])
    results = store.search([2.0, 0.0], "tenant-a", 3)
    assert [(r.chunk.chunk_id, round(r.score, 6)) for r in results] == [
        ("A-2@1/1/1", 1.0),
        ("A-3@1/1/1", 1.0),
        ("A-1@1/1/1", 0.0),
    ]
    assert [r.chunk.chunk_id for r in store.search([1.0, 0.0], "tenant-a", 1)] == ["A-2@1/1/1"]


def test_dense_retriever_finds_the_chunk_with_the_same_words():
    retriever = dense(CHUNKS)
    top = retriever.retrieve("Administrators must always use MFA.", "tenant-a", 1)
    assert [r.chunk.chunk_id for r in top] == ["A-2@1.0/1/1"]
    assert math.isclose(top[0].score, 1.0)


def test_bm25_tokens_and_ranking():
    assert tokens("MFA, 15 characters; A-MFA@1.0") == [
        "mfa",
        "15",
        "characters",
        "a",
        "mfa",
        "1",
        "0",
    ]
    retriever = BM25Retriever(CHUNKS)
    top = retriever.retrieve("hardware keys", "tenant-b", 5)
    assert top[0].chunk.chunk_id == "B-2@1.0/1/1"
    assert top[0].score > 0
    with pytest.raises(ValueError, match="k must be"):
        retriever.retrieve("x", "tenant-a", 0)


def test_reciprocal_rank_fusion_matches_hand_computed_scores():
    a, b, c = (make_chunk(f"A-{n}@1/1/1", "tenant-a", n) for n in "abc")
    first = [ScoredChunk(a, 0.9), ScoredChunk(b, 0.8)]
    second = [ScoredChunk(c, 7.0), ScoredChunk(a, 3.0)]
    fused = reciprocal_rank_fusion([first, second], rrf_k=60)
    # a: 1/61 + 1/62; c: 1/61; b: 1/62
    assert [r.chunk.chunk_id for r in fused] == ["A-a@1/1/1", "A-c@1/1/1", "A-b@1/1/1"]
    assert math.isclose(fused[0].score, 1 / 61 + 1 / 62)
    assert math.isclose(fused[1].score, 1 / 61)
    assert math.isclose(fused[2].score, 1 / 62)
    # equal fused scores are ordered by chunk id
    tied = reciprocal_rank_fusion([[ScoredChunk(b, 1.0)], [ScoredChunk(a, 1.0)]])
    assert [r.chunk.chunk_id for r in tied] == ["A-a@1/1/1", "A-b@1/1/1"]


class Fixed:
    """A retriever that returns a fixed ranking, cut at k."""

    def __init__(self, ranking: list[ScoredChunk]) -> None:
        self.ranking = ranking
        self.asked: list[int] = []

    @property
    def name(self) -> str:
        return "fixed"

    def retrieve(self, query: str, tenant: str, k: int) -> list[ScoredChunk]:
        self.asked.append(k)
        return self.ranking[:k]


def test_hybrid_fuses_candidate_lists_deeper_than_k():
    chunks = [make_chunk(f"A-{n}@1/1/1", "tenant-a", f"t{n}") for n in range(6)]
    one = Fixed([ScoredChunk(c, 1.0) for c in chunks])  # 0, 1, ..., 5
    two = Fixed([ScoredChunk(c, 1.0) for c in reversed(chunks)])  # 5, 4, ..., 0
    hybrid = HybridRetriever(one, two, candidates=6)
    top = hybrid.retrieve("q", "tenant-a", 2)
    assert one.asked == [6]
    assert two.asked == [6]
    # chunk n has ranks n + 1 and 6 - n, so its fused score is 1/(61+n) + 1/(66-n): largest at
    # the ends (1/61 + 1/66 = 0.031545 > 1/62 + 1/65 > 1/63 + 1/64), and A-0 and A-5 tie, so the
    # chunk id orders them
    assert math.isclose(top[0].score, 1 / 61 + 1 / 66)
    assert math.isclose(top[1].score, 1 / 61 + 1 / 66)
    assert [r.chunk.chunk_id for r in top] == ["A-0@1/1/1", "A-5@1/1/1"]
    with pytest.raises(ValueError, match="candidates must be at least 1"):
        HybridRetriever(one, two, candidates=0)
