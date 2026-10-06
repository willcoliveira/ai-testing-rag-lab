"""Fake adapters for the unit tests. No module of raglab imports this one
(scripts/check_architecture.py, rule 4), so no run or published number can come from it.

HashingEmbedder: a bag of words hashed into a fixed number of buckets (the hashing trick), with a
sign per word, L2-normalised. Two texts that share words have a positive cosine; the same text
always gives the same vector, on any machine (blake2b, not Python's salted hash()). It has no
notion of meaning: it exists so the store, the retrievers and the tenant filter can be tested
without the real model.
"""

import hashlib
import math
import re
from collections.abc import Sequence

WORD = re.compile(r"[a-z0-9]+")


class HashingEmbedder:
    def __init__(self, dimension: int = 256) -> None:
        if dimension < 2:
            raise ValueError(f"dimension must be at least 2, not {dimension}")
        self._dimension = dimension

    @property
    def model(self) -> str:
        return f"hashing-{self._dimension}"

    @property
    def revision(self) -> str:
        return "fake"

    @property
    def dimension(self) -> int:
        return self._dimension

    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * self._dimension
        for word in WORD.findall(text.lower()):
            digest = int.from_bytes(hashlib.blake2b(word.encode(), digest_size=8).digest(), "big")
            vector[digest % self._dimension] += 1.0 if digest >> 63 else -1.0
        norm = math.sqrt(sum(x * x for x in vector))
        return [x / norm for x in vector] if norm else vector

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)
