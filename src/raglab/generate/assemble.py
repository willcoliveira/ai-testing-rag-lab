"""A pipeline built from a generation config (raglab.evals.config.GenerationConfig): the pack
ingested at the config's chunk settings, the pinned embedder, the configured retriever, the chat
model the factory builds, and the default guards. `raglab ask`, `raglab serve` and
`raglab eval --suite generation` all build it here, so they answer the same way.

S7: the instruction scan (raglab.ingest.scan, arrow L9) runs over the chunks before they are
indexed, and a quarantined chunk is never indexed; the inventory itself is unchanged. An attack run
adds its pages outside the register (raglab.ingest.attacks) as `extra`, scanned and indexed the
same way. `chunks` are the chunks the retriever searches.

The provenance is fake when either the embedder or the chat model is fake, else local.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import raglab.evals.retrieval as retrieval
from raglab.adapters import factory
from raglab.core.ports import ChatModel, Embedder, Guardrail
from raglab.core.types import Chunk
from raglab.evals.config import GenerationConfig, GeneratorConfig
from raglab.generate.pipeline import Pipeline
from raglab.guard import default_guards
from raglab.ingest import pipeline as ingest
from raglab.ingest import scan

type Json = dict[str, object]


@dataclass(frozen=True)
class Assembled:
    pipeline: Pipeline
    inventory: ingest.Inventory
    embedder_description: Json
    chat_description: Json
    provenance: str
    scanned: scan.Scanned | None = None  # S7: what the scan kept and quarantined; None: no scan
    pages: tuple[Chunk, ...] = ()  # S7: an attack run's pages outside the register

    @property
    def chunks(self) -> tuple[Chunk, ...]:
        """The chunks the retriever searches: the scan's kept chunks, or, when no scan ran, the
        inventory's and the attack run's pages."""
        if self.scanned is not None:
            return self.scanned.kept
        return (*self.inventory.chunks, *self.pages)


def chat_from_config(spec: GeneratorConfig) -> tuple[ChatModel, Json, str]:
    """The chat model a config names (raglab.adapters.factory), its description and provenance."""
    return factory.chat(
        spec.provider,
        spec.model,
        digest=spec.digest,
        base_url=spec.base_url,
        temperature=spec.temperature,
        top_p=spec.top_p,
        max_tokens=spec.max_tokens,
        timeout_s=spec.timeout_s,
        extra=spec.extra(),
        response_format=spec.response_format or "json_schema",
    )


def assemble(
    config: GenerationConfig,
    root: Path,
    *,
    embedder: tuple[Embedder, Json, str] | None = None,
    chat: tuple[ChatModel, Json, str] | None = None,
    inventory: ingest.Inventory | None = None,
    guards: Sequence[Guardrail] | None = None,
    extra: Sequence[Chunk] = (),
    scan_index: bool = True,
) -> Assembled:
    """The pipeline of a config. The embedder, chat model and inventory are built from the
    config unless given (the tests give small ones); extra chunks (an attack run's pages outside
    the register) are scanned and indexed with the inventory's. scan_index=False indexes without
    the instruction scan: S3's pipeline, the defences-off attack run only."""
    if inventory is None:
        inventory = ingest.ingest(root, config.chunker)
    elif inventory.settings != config.chunker:
        raise ValueError(f"the inventory was chunked at {inventory.settings}, not {config.chunker}")
    spec = config.embedder
    embed, embed_description, embed_provenance = embedder or factory.embedder(
        spec.provider, spec.model, spec.revision
    )
    model, chat_description, chat_provenance = chat or chat_from_config(config.generator)
    everything = [*inventory.chunks, *extra]
    scanned = scan.scan(everything) if scan_index else None
    indexed = list(scanned.kept) if scanned is not None else everything
    retriever = retrieval.build_retriever(config.retriever, embed, indexed)
    pipeline = Pipeline(
        retriever,
        model,
        default_guards(root, inventory.chunks) if guards is None else guards,
        config.retriever.k,
    )
    provenance = "fake" if "fake" in (embed_provenance, chat_provenance) else "local"
    return Assembled(
        pipeline,
        inventory,
        embed_description,
        chat_description,
        provenance,
        scanned,
        tuple(extra),
    )
