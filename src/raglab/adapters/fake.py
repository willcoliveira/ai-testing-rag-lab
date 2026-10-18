"""Fake adapters. Only raglab.adapters.factory imports this module, and it builds FakeChat only
when a config says `provider = "fake"` (scripts/check_architecture.py, rule 4); a run made with it
has provenance fake, and publish refuses every fake run, so no published number comes from here.
HashingEmbedder is built by the unit tests only.

FakeChat: a deterministic, scriptable chat model. By default it echoes: its answer is the text of
every chunk framed in the prompt, citing each chunk's id (label abstain when there is none). A
script replaces the echo: a function of the request, or a list of replies used in order, where a
ChatUnavailable in the list is raised instead of replied. It reports no token counts.

HashingEmbedder: a bag of words hashed into a fixed number of buckets (the hashing trick), with a
sign per word, L2-normalised. Two texts that share words have a positive cosine; the same text
always gives the same vector, on any machine (blake2b, not Python's salted hash()). It has no
notion of meaning: it exists so the store, the retrievers and the tenant filter can be tested
without the real model.
"""

import hashlib
import json
import math
import re
from collections.abc import Callable, Sequence

from raglab.core.types import ChatReply, ChatRequest, ChatUnavailable

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


# a chunk as raglab.generate.prompts frames it: its id, then its text on the lines inside the frame
CHUNK_FRAME = re.compile(r'<chunk id="([^"]*)"[^>]*>\n(.*?)\n</chunk>', flags=re.S)

type Script = Callable[[ChatRequest], str] | Sequence[str | ChatUnavailable]


def echo(request: ChatRequest) -> str:
    """The echo reply: every framed chunk's text, citing each one."""
    user = request.messages[-1].content
    chunks = CHUNK_FRAME.findall(user)
    reply = {
        "label": "answer" if chunks else "abstain",
        "answer": "\n\n".join(text for _, text in chunks) or "The documents do not say.",
        "cited_ids": [chunk_id for chunk_id, _ in chunks],
        "conflict_ids": [],
        "conflict_note": "",
    }
    return json.dumps(reply, ensure_ascii=False)


class FakeChat:
    def __init__(self, script: Script | None = None, name: str = "fake-echo") -> None:
        self._name = name
        self._function = script if callable(script) else None
        self._replies = None if script is None or callable(script) else list(script)
        self.requests: list[ChatRequest] = []

    @property
    def model(self) -> str:
        return self._name

    def describe(self) -> dict[str, object]:
        return {"provider": "fake", "model": self._name, "digest": "fake"}

    def complete(self, request: ChatRequest) -> ChatReply:
        self.requests.append(request)
        if self._function is not None:
            return ChatReply(self._function(request))
        if self._replies is None:
            return ChatReply(echo(request))
        if not self._replies:
            raise ChatUnavailable("the fake's script has no reply left")
        reply = self._replies.pop(0)
        if isinstance(reply, ChatUnavailable):
            raise reply
        return ChatReply(reply)
