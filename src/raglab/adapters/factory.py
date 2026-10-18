"""The only constructors of adapters, chosen by config.

The fake adapters (raglab.adapters.fake) are imported here and nowhere else in the package
(scripts/check_architecture.py, rule 4): FakeChat is built only when a config says
`provider = "fake"`, and a run made with it has provenance fake, which publish refuses.
HashingEmbedder is never built here: the unit tests build it themselves.
"""

from collections.abc import Mapping
from pathlib import Path

import httpx

from raglab.adapters import fake, fastembed_embed, openai_compat
from raglab.core.ports import ChatModel, Embedder

type Json = dict[str, object]


class AdapterError(ValueError):
    pass


def embedder(
    provider: str, model: str, revision: str, root: Path | None = None
) -> tuple[Embedder, Json, str]:
    """(embedder, what the run record says about it, provenance). The config must name the pinned
    model and revision exactly: a run never uses files other than the ones it records."""
    if provider != "fastembed":
        raise AdapterError(f"embedder provider {provider!r}: only fastembed exists (S2)")
    if (model, revision) != (fastembed_embed.MODEL, fastembed_embed.REVISION):
        raise AdapterError(
            f"fastembed {model} at {revision}: the pinned model is {fastembed_embed.MODEL} at "
            f"{fastembed_embed.REVISION}"
        )
    local = fastembed_embed.FastEmbedEmbedder(root)
    return local, local.describe(), "local"


def chat(
    provider: str,
    model: str,
    *,
    digest: str | None = None,
    base_url: str | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
    max_tokens: int | None = None,
    timeout_s: float | None = None,
    extra: Mapping[str, str] | None = None,
    response_format: str = "json_schema",
    client: httpx.Client | None = None,
) -> tuple[ChatModel, Json, str]:
    """(chat model, what the run record says about it, provenance). fake builds FakeChat
    (provenance fake); openai-compat builds the local OpenAI-compatible adapter, which refuses to
    start unless the server has the tag with the pinned digest (provenance local)."""
    if provider == "fake":
        model_ = fake.FakeChat(name=model)
        return model_, model_.describe(), "fake"
    if provider != "openai-compat":
        raise AdapterError(f"chat provider {provider!r}: only fake and openai-compat exist (S3)")
    if None in (digest, base_url, temperature, max_tokens, timeout_s):
        raise AdapterError(
            "an openai-compat model needs digest, base_url, temperature, max_tokens and timeout_s"
        )
    try:
        live = openai_compat.OpenAICompatChat(
            str(base_url),
            model,
            str(digest),
            temperature=float(temperature or 0.0),
            max_tokens=int(max_tokens or 0),
            timeout_s=float(timeout_s or 0.0),
            top_p=top_p,
            extra=extra,
            response_format=response_format,
            client=client,
        )
    except openai_compat.ChatConfigError as error:
        raise AdapterError(str(error)) from error
    return live, live.describe(), "local"
