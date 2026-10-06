"""The chunk inventory as JSON, its committed snapshot, and the diff between two snapshots.

- The inventory (`runs/tmp/inventory.json`, not committed) has every chunk with its text and
  metadata, the settings and the parser versions.
- The snapshot (`corpus/inventory.snapshot.json`, committed) has per chunk its id, document,
  section, page, length, first words and sha256, so a chunker or parser change shows up as a
  reviewed diff. `make inventory-snapshot` regenerates it on purpose.
"""

import json
from dataclasses import asdict
from pathlib import Path
from typing import cast

from raglab.core.types import Chunk
from raglab.ingest.pipeline import Inventory

SCHEMA_VERSION = 1
FIRST_WORDS = 8

type Json = dict[str, object]


def inventory_json(inventory: Inventory) -> Json:
    return {
        "schema_version": SCHEMA_VERSION,
        "settings": asdict(inventory.settings),
        "tools": inventory.tools,
        "documents": [
            {
                **asdict(d.meta),
                "pages": sum(1 for p in d.pages if p.number is not None) or None,
                "chars": len(d.text()),
                "chunks": sum(1 for c in inventory.chunks if c.doc_id == d.meta.doc_id),
            }
            for d in inventory.documents
        ],
        "chunks": [asdict(c) for c in inventory.chunks],
    }


def snapshot_row(chunk: Chunk) -> Json:
    return {
        "id": chunk.chunk_id,
        "doc": chunk.doc_id,
        "section": chunk.section_id,
        "page": chunk.page,
        "length": len(chunk.text),
        "first_words": " ".join(chunk.text.split()[:FIRST_WORDS]),
        "sha256": chunk.sha256,
    }


def snapshot_json(inventory: Inventory) -> Json:
    return {
        "schema_version": SCHEMA_VERSION,
        "settings": asdict(inventory.settings),
        "tools": inventory.tools,
        "documents": [
            {
                "doc": d.meta.doc_id,
                "format": d.meta.format,
                "chunks": sum(1 for c in inventory.chunks if c.doc_id == d.meta.doc_id),
            }
            for d in inventory.documents
        ],
        "chunks": [snapshot_row(c) for c in inventory.chunks],
    }


def write_json(path: Path, data: Json) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _rows(snapshot: Json) -> dict[str, Json]:
    rows = snapshot.get("chunks")
    if not isinstance(rows, list):
        raise ValueError("a snapshot has a chunks list")
    out: dict[str, Json] = {}
    for row in cast(list[object], rows):
        if not isinstance(row, dict):
            raise ValueError("a snapshot chunk is a mapping")
        item: Json = {str(k): v for k, v in cast(dict[object, object], row).items()}
        out[str(item["id"])] = item
    return out


def diff(old: Json, new: Json) -> dict[str, list[str]]:
    """Chunk ids added, removed and changed (any field) from old to new, and those unchanged."""
    before, after = _rows(old), _rows(new)
    return {
        "added": [i for i in after if i not in before],
        "removed": [i for i in before if i not in after],
        "changed": [i for i in after if i in before and after[i] != before[i]],
        "unchanged": [i for i in after if i in before and after[i] == before[i]],
    }


def diff_summary(old: Json, new: Json) -> str:
    """The diff as a few lines a reviewer can read, per document."""
    changes = diff(old, new)
    lines = [
        f"chunks: {len(_rows(old))} -> {len(_rows(new))}; "
        + ", ".join(f"{len(ids)} {kind}" for kind, ids in changes.items())
    ]
    for field in ("settings", "tools"):
        if old.get(field) != new.get(field):
            lines.append(f"{field}: {old.get(field)} -> {new.get(field)}")
    docs = sorted(
        {i.split("@", 1)[0] for kind in ("added", "removed", "changed") for i in changes[kind]}
    )
    for doc in docs:
        counts = {
            kind: sum(1 for i in changes[kind] if i.split("@", 1)[0] == doc)
            for kind in ("added", "removed", "changed")
        }
        lines.append(f"  {doc}: " + ", ".join(f"{n} {k}" for k, n in counts.items() if n))
    return "\n".join(lines)
