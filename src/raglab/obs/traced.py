"""The traced embedder (S9): the Embedder port with an `embeddings <model>` span around each query
embedding. The retriever embeds the question itself, so the span is made here, inside the
retrieval span, and the retrievers stay as they are. Indexing (embed_documents, when the server
starts) makes no span: it belongs to no request. Only `raglab serve` wraps its embedder
(raglab.generate.assemble, given a tracer). The span carries the model, its revision and the
dimension, never the text."""

from collections.abc import Mapping, Sequence
from typing import cast
from urllib.parse import urlsplit

from raglab.core.ports import AttributeValue, Embedder, Tracer
from raglab.obs import names


def chat_attributes(
    model: str, description: Mapping[str, object], seed: int, prompt_version: str
) -> list[tuple[str, AttributeValue]]:
    """The attributes of a `chat <model>` span before the call, from what the chat model says
    about itself (ChatModel.describe(): provider, model, digest and the request settings): the
    spec's required and conditionally required keys where they apply (the provider, the model,
    the seed, the prompt's name, the output type when a JSON schema is requested, the server's
    address and port), its recommended request settings, and raglab's digest. Never the
    messages."""
    out: list[tuple[str, AttributeValue]] = [
        (names.OPERATION, names.CHAT),
        (names.PROVIDER, str(description.get("provider", ""))),
        (names.REQUEST_MODEL, model),
        (names.MODEL_DIGEST, str(description.get("digest", ""))),
        (names.REQUEST_SEED, seed),
        (names.PROMPT_NAME, prompt_version),
    ]
    for key, field in ((names.REQUEST_TEMPERATURE, "temperature"), (names.REQUEST_TOP_P, "top_p")):
        value = description.get(field)
        if isinstance(value, int | float) and not isinstance(value, bool):
            out.append((key, float(value)))
    max_tokens = description.get("max_tokens")
    if isinstance(max_tokens, int) and not isinstance(max_tokens, bool):
        out.append((names.REQUEST_MAX_TOKENS, max_tokens))
    extra = description.get("extra")
    effort = (
        cast(Mapping[str, object], extra).get("reasoning_effort")
        if isinstance(extra, Mapping)
        else None
    )
    if isinstance(effort, str):
        out.append((names.REQUEST_REASONING, effort))
    if description.get("response_format") == "json_schema":
        out.append((names.OUTPUT_TYPE, "json"))
    base_url = description.get("base_url")
    if isinstance(base_url, str):
        parts = urlsplit(base_url)
        if parts.hostname:
            out.append((names.SERVER_ADDRESS, parts.hostname))
            if parts.port is not None:
                out.append((names.SERVER_PORT, parts.port))
    return out


class TracedEmbedder:
    def __init__(self, inner: Embedder, tracer: Tracer, provider: str) -> None:
        self.inner = inner
        self.tracer = tracer
        self.provider = provider

    @property
    def model(self) -> str:
        return self.inner.model

    @property
    def revision(self) -> str:
        return self.inner.revision

    @property
    def dimension(self) -> int:
        return self.inner.dimension

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return self.inner.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        with self.tracer.span(f"{names.EMBEDDINGS} {self.inner.model}", "client") as span:
            span.set(names.OPERATION, names.EMBEDDINGS)
            span.set(names.PROVIDER, self.provider)
            span.set(names.REQUEST_MODEL, self.inner.model)
            span.set(names.EMBEDDER_REVISION, self.inner.revision)
            span.set(names.EMBEDDING_DIMENSIONS, self.inner.dimension)
            return self.inner.embed_query(text)
