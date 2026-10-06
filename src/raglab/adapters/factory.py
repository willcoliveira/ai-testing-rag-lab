"""The only constructors of real adapters, chosen by config. The fake ones are built only by the
unit tests (scripts/check_architecture.py, rule 4)."""

from pathlib import Path

from raglab.adapters import fastembed_embed
from raglab.core.ports import Embedder

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
