"""AC4: every chunk carries doc id, version, status, tenant, section, print page where it applies,
and licence; no chunk lacks a tenant (ingestion fails closed); chunk ids are deterministic.
Also: no attack file reaches the default inventory, and the attack-fixture loader reads them."""

import dataclasses
import re
from pathlib import Path

import pytest
import yaml

from raglab.chunk.sections import ChunkSettings, SectionChunker
from raglab.core.types import TENANTS, Chunk, ChunkId, DocumentMeta, TenantError, sha256_text
from raglab.ingest import attacks, frontmatter, pipeline
from tests.conftest import ROOT
from tests.ingestion_support import answer_key, default_inventory, entries, parsed

pytestmark = pytest.mark.ingestion
# the full inventory OCRs the scanned page, so the tests that build it carry the ocr marker too
full = pytest.mark.ocr

CHUNK_ID = re.compile(r"^[A-Z]+(?:-[A-Z0-9]+)*@[A-Za-z0-9._-]+/[A-Za-z0-9._~-]+/\d+$")


def front_of(doc_id: str) -> dict[str, str]:
    path = ROOT / entries()[doc_id].path
    source = path if path.suffix == ".md" else path.with_suffix(".md")
    return frontmatter.read(source, doc_id)


@full
def test_every_chunk_carries_its_metadata():
    inventory = default_inventory()
    documents = {d.meta.doc_id: d for d in inventory.documents}
    for chunk in inventory.chunks:
        entry = entries()[chunk.doc_id]
        front = front_of(chunk.doc_id)
        where = chunk.chunk_id
        assert chunk.tenant == entry.tenant, where
        assert chunk.tenant in TENANTS, where
        assert chunk.status == entry.status, where
        assert chunk.path == entry.path, where
        assert chunk.version == front["version"], where
        assert chunk.licence == front["licence"], where
        assert chunk.kind == front["kind"], where
        assert chunk.title == front["title"], where
        assert chunk.section_id, where
        assert chunk.section_title, where
        if entry.format in ("pdf", "png"):
            assert chunk.page is not None, where
            assert chunk.page_end is not None, where
            assert 1 <= chunk.page <= chunk.page_end <= int(front["pages"]), where
        else:
            assert (chunk.page, chunk.page_end) == (None, None), where
        document = documents[chunk.doc_id]
        assert document.text()[chunk.char_start : chunk.char_end] == chunk.text, where
        assert chunk.sha256 == sha256_text(chunk.text), where


@full
def test_every_register_document_yields_chunks():
    inventory = default_inventory()
    assert [d.meta.doc_id for d in inventory.documents] == list(entries())
    assert {c.doc_id for c in inventory.chunks} == set(entries())


@full
def test_chunk_ids_are_unique_readable_and_deterministic():
    inventory = default_inventory()
    ids = [c.chunk_id for c in inventory.chunks]
    assert len(ids) == len(set(ids))
    for chunk in inventory.chunks:
        assert CHUNK_ID.match(chunk.chunk_id), chunk.chunk_id
        assert chunk.chunk_id.startswith(f"{chunk.doc_id}@")
    again = pipeline.ingest(ROOT)
    assert [(c.chunk_id, c.sha256) for c in again.chunks] == [
        (c.chunk_id, c.sha256) for c in inventory.chunks
    ]
    chunker = SectionChunker(ChunkSettings())
    for doc_id in ("A-MFA", "A-PWD-V2", "A-IR"):
        assert chunker.chunk(parsed(doc_id)) == chunker.chunk(parsed(doc_id))


def attack_payloads() -> set[str]:
    """The values the answer key cites in the attack files (canary, links, addresses, rules)."""
    attack_docs = {"T-HIDDEN", "T-POISON", "T-FAKE"}
    return {
        value
        for f in answer_key()["features"]
        for loc in f.get("locations", [])
        if loc["doc"] in attack_docs
        for value in loc.get("values", [])
    }


@full
def test_no_attack_file_reaches_the_default_inventory():
    inventory = default_inventory()
    attack_ids = {d.meta.doc_id for d in attacks.attack_documents(ROOT)}
    assert attack_ids == {"T-HIDDEN", "T-POISON", "T-FAKE"}
    assert not attack_ids & {c.doc_id for c in inventory.chunks}
    assert not any(c.path.startswith("corpus/attacks/") for c in inventory.chunks)
    text = "\n".join(c.text for c in inventory.chunks)
    payloads = attack_payloads()
    assert len(payloads) >= 9
    found = sorted(p for p in payloads if p in text)
    assert found == [], found


def test_the_attack_loader_reads_the_attack_files_as_unregistered_pages():
    chunks = attacks.attack_chunks(ROOT)
    assert {c.doc_id for c in chunks} == {"T-HIDDEN", "T-POISON", "T-FAKE"}
    assert {c.status for c in chunks} == {attacks.UNREGISTERED}
    assert {c.tenant for c in chunks} == {"tenant-a"}
    text = "\n".join(c.text for c in chunks)
    assert all(p in text for p in attack_payloads()), attack_payloads() - {
        p for p in attack_payloads() if p in text
    }


# ---------------------------------------------------------------- fails closed


def meta(**changes: object) -> DocumentMeta:
    base = DocumentMeta(
        "A-X", "Title", "1.0", "approved", "tenant-a", "company", "CC-BY-4.0", "x.md", "md"
    )
    return dataclasses.replace(base, **changes)  # type: ignore[arg-type]


@pytest.mark.unit
@pytest.mark.parametrize("tenant", [None, "", "tenant-c", "Tenant-A", " tenant-a"])
def test_a_chunk_or_document_without_a_known_tenant_cannot_exist(tenant):
    with pytest.raises(TenantError):
        meta(tenant=tenant)
    good = Chunk(
        ChunkId("A-X@1.0/1/1"), "A-X", "1.0", "approved", "tenant-a", "company", "T", "1", "S",
        None, None, "CC-BY-4.0", "x.md", 0, 4, "text",
    )  # fmt: skip
    with pytest.raises(TenantError):
        dataclasses.replace(good, tenant=tenant)


def mini_corpus(tmp_path: Path, entry: dict[str, object], front: str) -> Path:
    """A repo root with one Markdown document and a register naming it."""
    (tmp_path / "corpus" / "tenant-a").mkdir(parents=True)
    (tmp_path / "corpus" / "tenant-a" / "doc.md").write_text(
        f"---\n{front}---\n\n# Title\n\n## 1 Scope\n\nSome text.\n", encoding="utf-8"
    )
    register = {"schema_version": 1, "documents": [entry]}
    (tmp_path / "corpus" / "register.yaml").write_text(yaml.safe_dump(register), encoding="utf-8")
    return tmp_path


FRONT = (
    "id: A-X\ntitle: Title\nversion: '1.0'\ntenant: tenant-a\nkind: company\n"
    "licence: CC-BY-4.0\nformat: md\n"
)
ENTRY = {
    "id": "A-X",
    "status": "approved",
    "supersedes": None,
    "tenant": "tenant-a",
    "path": "corpus/tenant-a/doc.md",
}


@pytest.mark.unit
def test_the_mini_corpus_ingests(tmp_path):
    inventory = pipeline.ingest(mini_corpus(tmp_path, ENTRY, FRONT))
    assert [c.chunk_id for c in inventory.chunks] == ["A-X@1.0/1/1"]
    assert inventory.chunks[0].tenant == "tenant-a"


@pytest.mark.unit
@pytest.mark.parametrize(
    ("entry", "front", "message"),
    [
        ({**ENTRY, "tenant": None}, FRONT, "tenant None"),
        ({k: v for k, v in ENTRY.items() if k != "tenant"}, FRONT, "tenant None"),
        ({**ENTRY, "tenant": "tenant-c"}, FRONT, "tenant 'tenant-c'"),
        (ENTRY, FRONT.replace("tenant: tenant-a", "tenant: tenant-b"), "tenant 'tenant-b'"),
        (ENTRY, FRONT.replace("tenant: tenant-a\n", ""), "lacks tenant"),
        (ENTRY, FRONT.replace("id: A-X", "id: A-Y"), "id 'A-Y'"),
        ({**ENTRY, "status": "current"}, FRONT, "status 'current'"),
        ({**ENTRY, "path": "corpus/attacks/doc.md"}, FRONT, "attack file"),
        ({**ENTRY, "path": "../outside.md"}, FRONT, "without '..'"),
        ({**ENTRY, "path": "corpus/tenant-a/missing.md"}, FRONT, "does not exist"),
    ],
    ids=[
        "null-tenant",
        "no-tenant",
        "unknown-tenant",
        "front-matter-tenant-differs",
        "front-matter-without-tenant",
        "front-matter-id-differs",
        "unknown-status",
        "attack-path",
        "outside-path",
        "missing-file",
    ],
)
def test_ingestion_fails_closed_and_names_the_document(tmp_path, entry, front, message):
    root = mini_corpus(tmp_path, entry, front)
    (root / "corpus" / "attacks").mkdir()
    (root / "corpus" / "attacks" / "doc.md").write_text("x", encoding="utf-8")
    with pytest.raises(pipeline.IngestError, match=re.escape(message)):
        pipeline.ingest(root)


@pytest.mark.unit
def test_a_document_without_text_fails(tmp_path):
    root = mini_corpus(tmp_path, ENTRY, FRONT)
    (root / "corpus" / "tenant-a" / "doc.md").write_text(f"---\n{FRONT}---\n\n", encoding="utf-8")
    with pytest.raises(pipeline.IngestError, match="no text"):
        pipeline.ingest(root)


@pytest.mark.unit
def test_a_document_with_only_headings_yields_no_chunk_and_fails(tmp_path):
    root = mini_corpus(tmp_path, ENTRY, FRONT)
    (root / "corpus" / "tenant-a" / "doc.md").write_text(
        f"---\n{FRONT}---\n\n# Title\n\n## 1 Scope\n", encoding="utf-8"
    )
    with pytest.raises(pipeline.IngestError, match="no chunk"):
        pipeline.ingest(root)
