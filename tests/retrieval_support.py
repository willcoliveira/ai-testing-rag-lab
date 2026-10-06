"""Small chunks, retrievers and runs for the retrieval tests, built with the fake embedder."""

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from raglab.adapters.fake import HashingEmbedder
from raglab.chunk.sections import ChunkSettings
from raglab.core.ports import Retriever
from raglab.core.types import Chunk, ChunkId
from raglab.evals import config as eval_config
from raglab.evals import record, retrieval
from raglab.index.memory import InMemoryStore
from raglab.ingest.pipeline import Inventory
from raglab.retrieve.bm25 import BM25Retriever
from raglab.retrieve.dense import DenseRetriever, index_chunks
from raglab.retrieve.hybrid import HybridRetriever
from tests.conftest import ROOT


def make_chunk(chunk_id: str, tenant: str, text: str, section: str = "1") -> Chunk:
    doc = chunk_id.split("@", 1)[0]
    return Chunk(
        chunk_id=ChunkId(chunk_id),
        doc_id=doc,
        version="1.0",
        status="approved",
        tenant=tenant,
        kind="company",
        title=doc,
        section_id=section,
        section_title=section,
        page=None,
        page_end=None,
        licence="CC-BY-4.0",
        path=f"{doc}.md",
        char_start=0,
        char_end=len(text),
        text=text,
    )


# Three tenants' worth of chunks; B-1 and A-1 say almost the same thing, so a query for one
# ranks the other high unless the filter holds.
CHUNKS = [
    make_chunk("A-1@1.0/1/1", "tenant-a", "Passwords must be at least 15 characters long."),
    make_chunk("A-2@1.0/1/1", "tenant-a", "Administrators must always use MFA."),
    make_chunk("B-1@1.0/1/1", "tenant-b", "Passwords must be at least 12 characters long."),
    make_chunk("B-2@1.0/1/1", "tenant-b", "Mirrowfen staff use hardware keys for MFA."),
    make_chunk("X-1@1.0/1/1", "shared", "NIST guidance on password length and MFA."),
]


def dense(chunks: list[Chunk]) -> DenseRetriever:
    embedder = HashingEmbedder()
    store = InMemoryStore(embedder.dimension)
    index_chunks(embedder, store, chunks)
    return DenseRetriever(embedder, store)


def retrievers(chunks: list[Chunk]) -> dict[str, Retriever]:
    d = dense(chunks)
    lexical = BM25Retriever(chunks)
    return {"dense": d, "bm25": lexical, "hybrid": HybridRetriever(d, lexical)}


# ---------------------------------------------------------------- small runs with the fake embedder


PACK = [
    make_chunk("A-PWD@1.0/4.1/1", "tenant-a", "Passwords must be at least 15 characters.", "4.1"),
    make_chunk("A-PWD@1.0/4.1/2", "tenant-a", "Passphrases of four words are allowed.", "4.1"),
    make_chunk("A-PWD@1.0/5/1", "tenant-a", "Accounts lock after 10 failed sign-ins.", "5"),
    make_chunk("A-MFA@1.0/4.1/1", "tenant-a", "Administrators must always use MFA.", "4.1"),
    make_chunk("A-VPN@1.0/4.5/1", "tenant-a", "VPN sessions disconnect after 60 minutes.", "4.5"),
    make_chunk("B-PWD@1.0/3/1", "tenant-b", "Mirrowfen passwords are at least 12 characters.", "3"),
    make_chunk(
        "X-NIST@4/3.1/1", "shared", "Verifiers allow passwords of at least 64 characters.", "3.1"
    ),
]
QUESTIONS = [
    {
        "id": "Q1",
        "kind": "retrieval",
        "split": "dev",
        "tenant": "tenant-a",
        "question": "How many characters must passwords have?",
        "question_kind": "plain-rule",
        "relevant": [{"doc_id": "A-PWD", "section_id": "4.1"}],
    },
    {
        "id": "Q2",
        "kind": "retrieval",
        "split": "dev",
        "tenant": "tenant-a",
        "question": "When do accounts lock after failed sign-ins?",
        "relevant": [{"doc_id": "A-PWD", "section_id": "5"}],
    },
    {
        "id": "Q3",
        "kind": "retrieval",
        "split": "dev",
        "tenant": "tenant-a",
        "question": "Must administrators use MFA, and when do VPN sessions disconnect?",
        "relevant": [
            {"doc_id": "A-MFA", "section_id": "4.1"},
            {"doc_id": "A-VPN", "section_id": "4.5"},
        ],
    },
    {
        "id": "Q4",
        "kind": "retrieval",
        "split": "dev",
        "tenant": "tenant-b",
        "question": "How long are Mirrowfen passwords?",
        "relevant": [{"doc_id": "B-PWD", "section_id": "3"}],
    },
    {
        "id": "Q5",
        "kind": "retrieval",
        "split": "test",
        "tenant": "tenant-a",
        "question": "Are passphrases allowed?",
        "relevant": [{"doc_id": "A-PWD", "section_id": "4.1"}],
    },
    {
        "id": "Q6",
        "kind": "behaviour",
        "split": "dev",
        "tenant": "tenant-a",
        "question": "What is the Wi-Fi password?",
    },
]
GIT = retrieval.GitState("0123456789abcdef0123456789abcdef01234567", False)


def config_text(name: str, kind: str = "dense", k: int = 2, split: str = "dev") -> str:
    hybrid = "candidates = 5\nrrf_k = 60\n" if kind == "hybrid" else ""
    return (
        f'name = "{name}"\nsuite = "retrieval"\n\n[dataset]\npath = "golden.jsonl"\n'
        f'split = "{split}"\n\n[chunker]\nchunk_size = 1200\noverlap = 1\n\n[embedder]\n'
        'provider = "fake"\nmodel = "hashing-256"\nrevision = "fake"\n\n'
        f'[retriever]\nkind = "{kind}"\nk = {k}\n{hybrid}\n'
        "[bootstrap]\nseed = 7\nresamples = 200\nlevel = 0.9\n"
    )


# The documents of the small runs and their tenants: PACK's, and A-Z, the extra chunk of a test
# that changes the corpus. lab_root registers them, because record.validate checks every chunk id
# against the register (S2 judge D3).
LAB_DOCS = {**{c.doc_id: c.tenant for c in PACK}, "A-Z": "tenant-a"}


def write_register(root: Path, docs: dict[str, str]) -> None:
    """corpus/register.yaml naming each document with its tenant, and a placeholder file for each
    (the register's paths must exist)."""
    lines = ["schema_version: 1", "documents:"]
    for doc, tenant in docs.items():
        path = f"corpus/{doc.lower()}.md"
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(f"# {doc}\n", encoding="utf-8")
        lines += [
            f"- id: {doc}",
            "  status: approved",
            "  supersedes: null",
            f"  tenant: {tenant}",
            f"  path: {path}",
        ]
    (root / "corpus" / "register.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def lab_root(tmp_path: Path, questions: list[dict] | None = None) -> Path:
    """A repo root with the real schema, a register of the small runs' documents and a small
    golden file."""
    root = tmp_path / "repo"
    (root / "schemas").mkdir(parents=True)
    shutil.copyfile(ROOT / record.SCHEMA_PATH, root / record.SCHEMA_PATH)
    write_register(root, LAB_DOCS)
    lines = [json.dumps(q) for q in (QUESTIONS if questions is None else questions)]
    (root / "golden.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return root


def fake_run(
    root: Path,
    name: str = "retrieval-fake",
    kind: str = "dense",
    k: int = 2,
    chunks: list[Chunk] | None = None,
    when: datetime = datetime(2026, 10, 6, 12, 0, 0, tzinfo=UTC),
    git: retrieval.GitState = GIT,
    provenance: str = "fake",
) -> Path:
    """A run record written under root/runs/tmp with the fake embedder."""
    path = root / "config" / f"{name}.toml"
    path.parent.mkdir(exist_ok=True)
    path.write_text(config_text(name, kind, k), encoding="utf-8")
    config = eval_config.load(path, root)
    embedder = HashingEmbedder()
    inventory = Inventory(ChunkSettings(), {"pypdf": "x"}, (), tuple(chunks or PACK))
    description = {
        "provider": "fake",
        "model": embedder.model,
        "revision": embedder.revision,
        "dimension": embedder.dimension,
    }
    manifest, cases = retrieval.run(
        config,
        root,
        embedder,
        description,
        provenance,
        git=git,
        clock=lambda: when,
        inventory=inventory,
    )
    return record.write(root / "runs" / "tmp", manifest, cases)


def read_run(run_dir: Path) -> tuple[Any, list[Any]]:
    """record.read, typed loosely for the tests' nested lookups."""
    return record.read(run_dir)


def reseal(run_dir: Path, cases: list[Any]) -> None:
    """Rewrite cases.jsonl with flags, scores, results, report and file hashes that agree, as a
    careful hand edit would: only the tenant check can tell such a record from a real one."""
    manifest, _ = read_run(run_dir)
    k = manifest["retriever"]["k"]
    for case in cases:
        ids = [r["chunk_id"] for r in case["retrieved"]]
        sets = [frozenset(label["chunk_ids"]) for label in case["labels"]]
        for r in case["retrieved"]:
            r["relevant"] = any(r["chunk_id"] in s for s in sets)
        for label, s in zip(case["labels"], sets, strict=True):
            label["found"] = bool(set(ids) & s)
        case.update(record.case_scores(ids, sets, k))
    manifest["results"] = record.results_from_cases(cases, k, manifest["bootstrap"])
    body = {key: v for key, v in manifest.items() if key != "files"}
    cases_bytes = record.cases_text(cases).encode()
    report_bytes = record.render_report(body, cases).encode()
    (run_dir / record.CASES).write_bytes(cases_bytes)
    (run_dir / record.REPORT).write_bytes(report_bytes)
    manifest["files"] = {
        record.CASES: record.sha256_bytes(cases_bytes),
        record.REPORT: record.sha256_bytes(report_bytes),
    }
    (run_dir / record.MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n")
