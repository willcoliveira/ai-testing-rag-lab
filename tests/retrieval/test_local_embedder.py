"""The real local embedder, loaded from the pinned files in the cache (`make model` downloads them
outside the tests; the no-network guard stays on). L10 `embedder-deterministic` and L11
`index-holds-every-chunk` of docs/TEST-PLAN.md."""

from functools import cache

import numpy as np
import pytest

from raglab.adapters.fastembed_embed import DIMENSION, MODEL, REVISION, FastEmbedEmbedder
from raglab.index.memory import InMemoryStore
from raglab.retrieve.dense import DenseRetriever, index_chunks
from tests.ingestion_support import default_inventory

pytestmark = pytest.mark.retrieval


@cache
def embedder() -> FastEmbedEmbedder:
    return FastEmbedEmbedder()


def test_the_same_text_gives_the_same_vector_of_the_index_dimension():
    model = embedder()
    assert (model.model, model.revision, model.dimension) == (MODEL, REVISION, DIMENSION)
    text = "Administrators must always use MFA."
    first = model.embed_documents([text, "Kiosk devices lock after 5 minutes."])
    again = FastEmbedEmbedder().embed_documents([text, "Kiosk devices lock after 5 minutes."])
    assert first == again
    assert [len(v) for v in first] == [DIMENSION, DIMENSION]
    assert np.isclose(np.linalg.norm(first[0]), 1.0, atol=1e-5)
    assert model.embed_query(text) == model.embed_query(text)
    assert model.describe()["revision"] == REVISION


def test_meaning_not_only_words():
    """A paraphrase is nearer than an unrelated sentence: the model is the real one."""
    model = embedder()
    rule, paraphrase, other = model.embed_documents(
        [
            "Passwords must be at least 15 characters long.",
            "What is the minimum length of a password?",
            "The SOC monitors VPN sessions of the on-call rota.",
        ]
    )
    assert float(np.dot(rule, paraphrase)) > float(np.dot(rule, other))


@pytest.mark.ocr
def test_the_index_holds_every_chunk_once_with_its_tenant():
    chunks = list(default_inventory().chunks)
    store = InMemoryStore(DIMENSION)
    index_chunks(embedder(), store, chunks)
    assert store.chunk_ids() == [c.chunk_id for c in chunks]
    assert len(set(store.chunk_ids())) == len(chunks)
    retriever = DenseRetriever(embedder(), store)
    for tenant in ("tenant-a", "tenant-b"):
        found = retriever.retrieve("password length", tenant, len(chunks))
        expected = {c.chunk_id for c in chunks if c.tenant in {tenant, "shared"}}
        assert {r.chunk.chunk_id for r in found} == expected
