"""The instruction scan at ingest (S7, AG3, arrow L9 of docs/TEST-PLAN.md): T-HIDDEN's visible
payload is flagged as a page outside the register and inside a document of a temporary register,
and its chunk is quarantined (never indexed); the clean pack raises no flag, so the inventory, its
snapshot and a clean run's corpus sha256 do not change; a quarantine event names the chunk and the
rule groups, never the text."""

import dataclasses

import pytest

from raglab.evals import retrieval
from raglab.generate.assemble import assemble
from raglab.ingest import scan
from tests import security_support as s
from tests.generation_support import generation_config_text, generation_root
from tests.retrieval_support import PACK

pytestmark = pytest.mark.security


def test_the_planted_instruction_is_quarantined_as_a_page_outside_the_register():
    found = scan.scan(s.clean() + s.pages())
    assert found.quarantined == ("T-HIDDEN@1.0/5/1",)
    assert len(found.kept) == len(s.clean()) + len(s.pages()) - 1


def test_the_planted_instruction_is_quarantined_inside_a_registered_document():
    chunks = s.registered_hidden()
    assert {c.status for c in chunks} == {"approved"}
    found = scan.scan(s.clean() + chunks)
    assert found.quarantined == (f"{s.REGISTERED_ID}@1.0/5/1",)


def test_a_quarantine_event_names_the_chunk_and_the_rule_groups_never_the_text():
    found = scan.scan(s.pages("T-HIDDEN"))
    assert [e.reason for e in found.events] == [
        "chunk T-HIDDEN@1.0/5/1 quarantined: rule groups addressed, change, send"
    ]
    assert {(e.guard, e.stage) for e in found.events} == {(scan.LAYER, "ingest")}
    note = next(c.text for c in s.pages("T-HIDDEN") if c.chunk_id == "T-HIDDEN@1.0/5/1")
    assert not any(
        line.strip() and line.strip() in found.events[0].reason for line in note.split(".")
    )


def test_the_clean_pack_keeps_its_chunks_and_its_corpus_sha256():
    found = scan.scan(s.clean())
    assert found.quarantined == ()
    assert found.kept == s.clean()
    assert retrieval.corpus_sha256(list(found.kept)) == retrieval.corpus_sha256(list(s.clean()))


def test_assemble_indexes_what_the_scan_keeps(tmp_path):
    """A pipeline built from a config searches the scan's kept chunks: the inventory's unchanged
    when nothing is flagged, and an extra page's instruction never indexed."""
    from raglab.adapters.fake import FakeChat, HashingEmbedder
    from raglab.chunk.sections import ChunkSettings
    from raglab.evals import config as eval_config
    from raglab.ingest.pipeline import Inventory

    root = generation_root(tmp_path)
    path = root / "config" / "generation.toml"
    path.parent.mkdir(exist_ok=True)
    path.write_text(generation_config_text(), encoding="utf-8")
    config = eval_config.load_generation(path, root)
    inventory = Inventory(ChunkSettings(), {"pypdf": "x"}, (), tuple(PACK))
    hashing, chat = HashingEmbedder(), FakeChat()
    description = {"provider": "fake", "model": "h", "revision": "fake", "dimension": 256}
    clean = assemble(
        config,
        root,
        embedder=(hashing, description, "fake"),
        chat=(chat, chat.describe(), "fake"),
        inventory=inventory,
    )
    assert clean.chunks == tuple(PACK)
    assert clean.scanned is not None
    assert clean.scanned.quarantined == ()
    note = next(c for c in s.pages("T-HIDDEN") if c.chunk_id == "T-HIDDEN@1.0/5/1")
    planted = dataclasses.replace(note, tenant="tenant-a")
    attacked = assemble(
        config,
        root,
        embedder=(hashing, description, "fake"),
        chat=(chat, chat.describe(), "fake"),
        inventory=inventory,
        extra=(planted,),
    )
    assert attacked.chunks == tuple(PACK)
    assert attacked.scanned is not None
    assert attacked.scanned.quarantined == ("T-HIDDEN@1.0/5/1",)
