"""The attack-fixture loader: the files under corpus/attacks/, for attack runs only (S7 and the
deterministic attack suite).

Attack files are not in the register, so `raglab ingest` and pipeline.ingest() never read them;
an attack run adds them on purpose, as pages that arrived outside the register, as a real
poisoned page would. Their status is `unregistered`. Their tenant comes from their own front
matter, since no register entry vouches for them. Which other metadata an attack run exposes
(kind, title) is S7's decision; a pipeline must never use kind or status as a defence signal
(corpus/SPEC.md, section 3).
"""

from pathlib import Path

from raglab.chunk.sections import ChunkSettings, SectionChunker
from raglab.core.types import Chunk, Document
from raglab.ingest import frontmatter, pipeline
from raglab.ingest.register import ATTACKS

UNREGISTERED = "unregistered"


def attack_documents(root: Path) -> tuple[Document, ...]:
    """Every attack fixture, parsed, in file-name order."""
    documents: list[Document] = []
    for path in sorted((root / ATTACKS).glob("*.md")):
        rel = path.relative_to(root).as_posix()
        front = frontmatter.read(path, rel)
        meta = pipeline.describe(
            root, front.get("id", ""), UNREGISTERED, front.get("tenant", ""), rel, "md"
        )
        documents.append(pipeline.parse(root, meta))
    return tuple(documents)


def attack_chunks(root: Path, settings: ChunkSettings | None = None) -> tuple[Chunk, ...]:
    """The chunks of every attack fixture, cut with the same chunker as the clean corpus."""
    chunker = SectionChunker(settings or ChunkSettings())
    return tuple(c for d in attack_documents(root) for c in chunker.chunk(d))
