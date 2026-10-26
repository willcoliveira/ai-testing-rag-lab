"""The attack-fixture loader: the files under corpus/attacks/, for attack runs only (S7 and the
deterministic attack suite).

Attack files are not in the register, so `raglab ingest` and pipeline.ingest() never read them;
an attack run adds them on purpose, as pages that arrived outside the register, as a real
poisoned page would. Their status is `unregistered`. Their tenant comes from their own front
matter, since no register entry vouches for them.

What an attack run exposes (S7's decision, corpus/SPEC.md section 3): a page carries its text, its
tenant, its claimed id and version, and the register-derived status `unregistered`. Its title is
its own first heading, as a page a reader opens shows it, never the front matter's title (which
labels the file as test material for humans); its kind is `unregistered` too, never the front
matter's `kind`, and its front matter's `status` and `test_material` are never read. So no
pipeline, and no model, can tell a planted page from a real one by a label only humans should see.
"""

import dataclasses
from pathlib import Path

from raglab.chunk.sections import ChunkSettings, SectionChunker
from raglab.core.types import Chunk, Document
from raglab.ingest import frontmatter, pipeline
from raglab.ingest.register import ATTACKS

UNREGISTERED = "unregistered"


def _first_heading(document: Document) -> str:
    for page in document.pages:
        for block in page.blocks:
            if block.kind == "heading" and block.level == 1:
                return block.text
    return document.meta.doc_id


def attack_documents(root: Path) -> tuple[Document, ...]:
    """Every attack fixture, parsed, in file-name order, as a page outside the register."""
    documents: list[Document] = []
    for path in sorted((root / ATTACKS).glob("*.md")):
        rel = path.relative_to(root).as_posix()
        front = frontmatter.read(path, rel)
        meta = pipeline.describe(
            root, front.get("id", ""), UNREGISTERED, front.get("tenant", ""), rel, "md"
        )
        parsed = pipeline.parse(root, meta)
        shown = dataclasses.replace(meta, title=_first_heading(parsed), kind=UNREGISTERED)
        documents.append(Document(shown, parsed.pages))
    return tuple(documents)


def attack_chunks(root: Path, settings: ChunkSettings | None = None) -> tuple[Chunk, ...]:
    """The chunks of every attack fixture, cut with the same chunker as the clean corpus."""
    chunker = SectionChunker(settings or ChunkSettings())
    return tuple(c for d in attack_documents(root) for c in chunker.chunk(d))
