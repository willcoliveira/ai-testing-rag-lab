"""The retrieval suite: ingest at the config's chunk settings, index, ask every question of the
split as its tenant, score the top k against the resolved labels, and build the run record.

No model judges anything: the labels are sections, so the scores are counts (raglab.evals.metrics).
The embedder is passed in (raglab.adapters.factory builds the real one), with the provenance its
numbers carry: local for the ONNX model, fake only in unit tests.
"""

import platform
import shutil
import subprocess  # nosec B404
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

from raglab import __version__
from raglab.core.ports import Embedder, Retriever
from raglab.core.types import Chunk
from raglab.evals import golden, record
from raglab.evals.config import EvalConfig, canonical_sha256
from raglab.index.memory import InMemoryStore
from raglab.ingest import pipeline
from raglab.retrieve.bm25 import BM25Retriever
from raglab.retrieve.dense import DenseRetriever, index_chunks
from raglab.retrieve.hybrid import HybridRetriever

type Json = dict[str, object]


@dataclass(frozen=True)
class GitState:
    sha: str
    dirty: bool


def git_state(root: Path) -> GitState:
    """HEAD and whether the work tree differs from it (any change, untracked files included)."""

    executable = shutil.which("git")
    if executable is None:
        raise RuntimeError("git is not on PATH: a run records the commit it ran from")

    def git(*args: str) -> str:
        # fixed git arguments, no shell, no input from the user
        command = [executable, *args]
        return subprocess.run(  # noqa: S603  # nosec B603
            command, cwd=root, check=True, capture_output=True, text=True
        ).stdout

    return GitState(git("rev-parse", "HEAD").strip(), bool(git("status", "--porcelain").strip()))


def corpus_sha256(chunks: list[Chunk]) -> str:
    """The inventory the run searched: every chunk id with its text's sha256, in order."""
    return canonical_sha256([[c.chunk_id, c.sha256] for c in chunks])


def build_retriever(config: EvalConfig, embedder: Embedder, chunks: list[Chunk]) -> Retriever:
    def dense() -> DenseRetriever:
        store = InMemoryStore(embedder.dimension)
        index_chunks(embedder, store, chunks)
        return DenseRetriever(embedder, store)

    spec = config.retriever
    if spec.kind == "dense":
        return dense()
    if spec.kind == "bm25":
        return BM25Retriever(chunks)
    if spec.candidates is None or spec.rrf_k is None:
        raise ValueError("a hybrid retriever needs candidates and rrf_k")  # config.load checks it
    return HybridRetriever(dense(), BM25Retriever(chunks), spec.candidates, spec.rrf_k)


def tools(inventory_tools: dict[str, str]) -> dict[str, str]:
    found = {
        "python": platform.python_version(),
        "raglab": __version__,
        "numpy": version("numpy"),
        "rank-bm25": version("rank-bm25"),
    }
    return {**found, **inventory_tools}


def run_id(created: datetime, config: EvalConfig, sha: str) -> str:
    return f"{created:%Y%m%dT%H%M%SZ}-{config.name}-{config.split}-{sha[:7]}"


def run(
    config: EvalConfig,
    root: Path,
    embedder: Embedder,
    embedder_description: Json,
    provenance: str,
    gate: str = "manual",
    git: GitState | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    inventory: pipeline.Inventory | None = None,
) -> tuple[Json, list[Json]]:
    """(manifest without its files block, cases) of one retrieval run. The inventory is ingested
    at the config's chunk settings unless one is given (unit tests pass a small one)."""
    started = time.perf_counter()
    created = clock().replace(microsecond=0)
    git = git or git_state(root)
    dataset_path = root / config.dataset
    questions = golden.select(golden.load(dataset_path), "retrieval", config.split)
    if not questions:
        raise golden.DatasetError(f"{config.dataset}: no retrieval questions in {config.split}")
    if inventory is None:
        inventory = pipeline.ingest(root, config.chunker)
    elif inventory.settings != config.chunker:
        raise ValueError(f"the inventory was chunked at {inventory.settings}, not {config.chunker}")
    chunks = list(inventory.chunks)
    resolved = golden.resolve(questions, chunks)
    retriever = build_retriever(config, embedder, chunks)
    k = config.retriever.k
    cases: list[Json] = []
    for item in resolved:
        question = item.question
        sets = item.label_sets()
        relevant = frozenset[str]().union(*sets)
        tick = time.perf_counter()
        results = retriever.retrieve(question.question, question.tenant, k)
        latency = (time.perf_counter() - tick) * 1000
        ids = [r.chunk.chunk_id for r in results]
        case: Json = {
            "case_id": question.case_id,
            "trial": 1,
            "split": question.split,
            "tenant": question.tenant,
            "question": question.question,
            "labels": [
                {
                    "doc_id": label.doc_id,
                    "section_id": label.section_id,
                    "chunk_ids": list(chunk_ids),
                    "found": bool(set(ids) & set(chunk_ids)),
                }
                for label, chunk_ids in item.groups
            ],
            "retrieved": [
                {
                    "rank": rank,
                    "chunk_id": r.chunk.chunk_id,
                    "score": round(r.score, 6),
                    "relevant": r.chunk.chunk_id in relevant,
                }
                for rank, r in enumerate(results, start=1)
            ],
            **record.case_scores(ids, sets, k),
            "latency_ms": round(latency, 3),
        }
        if question.question_kind:
            case["question_kind"] = question.question_kind
        cases.append(case)
    bootstrap: Json = {
        "resamples": config.bootstrap.resamples,
        "seed": config.bootstrap.seed,
        "level": config.bootstrap.level,
        "method": "percentile",
    }
    resolved_config = config.resolved()
    spec = config.retriever
    retriever_json: Json = {"kind": spec.kind, "k": spec.k}
    if spec.kind == "hybrid":
        retriever_json |= {"candidates": spec.candidates, "rrf_k": spec.rrf_k}
    chunker_json: Json = {
        "chunk_size": config.chunker.chunk_size,
        "overlap": config.chunker.overlap,
    }
    embedder_json: Json = {k2: v for k2, v in embedder_description.items() if k2 != "sha256"}
    manifest: Json = {
        "schema_version": record.SCHEMA_VERSION,
        "run_id": run_id(created, config, git.sha),
        "created_at": created.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "suite": config.suite,
        "gate": gate,
        "split": config.split,
        "trials": 1,
        "seed": config.bootstrap.seed,
        "provenance": provenance,
        "partial": False,
        "git_sha": git.sha,
        "git_dirty": git.dirty,
        "config": {
            "name": config.name,
            "path": config.path,
            "file_sha256": config.file_sha256,
            "sha256": canonical_sha256(resolved_config),
        },
        "chunker": {**chunker_json, "sha256": canonical_sha256(chunker_json)},
        "embedder": {**embedder_json, "sha256": canonical_sha256(embedder_json)},
        "retriever": {**retriever_json, "sha256": canonical_sha256(retriever_json)},
        "dataset": {
            "path": config.dataset,
            "sha256": record.sha256_bytes(dataset_path.read_bytes()),
            "questions": len(cases),
        },
        "corpus": {
            "documents": len({c.doc_id for c in chunks}),
            "chunks": len(chunks),
            "sha256": corpus_sha256(chunks),
        },
        "tools": tools(inventory.tools),
        "bootstrap": bootstrap,
        "results": record.results_from_cases(cases, k, bootstrap),
        "totals": {"cases": len(cases), "duration_s": round(time.perf_counter() - started, 3)},
    }
    return manifest, cases
