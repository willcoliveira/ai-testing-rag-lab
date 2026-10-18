"""The generation suite (S3): every retrieval question of the config's split and every abstention
probe (datasets/probes.s3.jsonl), each asked N times as its tenant through the pipeline, scored
by the checks of raglab.evals.generation_record, and written as run record v1.

Trial t of every case uses seed + t - 1, so the trials differ only where the model samples. The
run stops early, and is marked partial, when its wall-clock cap (generation.run_timeout_s) is hit.
Any trial whose model gave no reply (status unavailable: a timeout, a connection error or an HTTP
error) also marks the run partial, with the count in the manifest (judge S3-J10): a run with
unanswered trials is never complete, and a partial run is never published. A reply outside the
answer schema (invalid_output) does not: the model did answer.

No model judges anything here: the checks are counts (S5 adds judged metrics). The abstention
probes are scored by the named oracle `abstention_oracle` (raglab.evals.generation_record, where
the run record validator recomputes it): label abstain, no policy value in the text (R-18), and,
for a tenant-isolation probe, no canary of the other tenant (R-16).
"""

import time
from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from typing import cast

from raglab.core.types import ScoredChunk, Status
from raglab.evals import generation_record, golden, record, retrieval
from raglab.evals.config import GenerationConfig, canonical_sha256
from raglab.evals.generation_record import abstention_oracle, policy_values
from raglab.generate.assemble import Assembled
from raglab.generate.pipeline import Outcome
from raglab.generate.prompts import answer_v1 as prompt
from raglab.ingest import answer_key

type Json = dict[str, object]

__all__ = ["abstention_oracle", "load_probes", "policy_values", "run"]


def load_probes(path: Path) -> list[golden.Question]:
    """The abstention probes: behaviour questions that expect abstain, each with the features it
    probes and, for a tenant-isolation probe, the tenant whose canaries its answer must not hold
    (canaries_of; null otherwise)."""
    probes = golden.load(path)
    for probe in probes:
        where = f"{path.name} ({probe.case_id})"
        extra = probe.extra
        if probe.kind != "behaviour" or extra.get("expected") != "abstain":
            raise golden.DatasetError(f"{where}: a probe is a behaviour question expecting abstain")
        value = extra.get("feature_ids")
        if (
            not isinstance(value, list)
            or not value
            or not all(isinstance(v, str) and v for v in cast(list[object], value))
        ):
            raise golden.DatasetError(f"{where}: a probe names the features it probes")
        of = extra.get("canaries_of")
        if of is not None and (of not in ("tenant-a", "tenant-b") or of == probe.tenant):
            raise golden.DatasetError(f"{where}: canaries_of names the other tenant, or is null")
    return probes


def _retrieved(results: tuple[ScoredChunk, ...], relevant: frozenset[str]) -> list[Json]:
    return [
        {
            "rank": rank,
            "chunk_id": r.chunk.chunk_id,
            "score": round(r.score, 6),
            "relevant": r.chunk.chunk_id in relevant,
        }
        for rank, r in enumerate(results, start=1)
    ]


def _answer_fields(outcome: Outcome) -> Json:
    answer = outcome.answer
    conflict = answer.conflict
    return {
        "status": answer.status.value,
        "label": answer.label,
        "answer": answer.text,
        "cited_ids": list(answer.cited_ids),
        "conflict": None
        if conflict is None
        else {"chunk_ids": list(conflict.chunk_ids), "note": conflict.note},
        "guard_events": [
            {"guard": e.guard, "stage": e.stage, "reason": e.reason} for e in outcome.events
        ],
        "error": outcome.error,
        "prompt_tokens": outcome.prompt_tokens,
        "completion_tokens": outcome.completion_tokens,
        "latency_ms": outcome.latency_ms,
    }


def run(
    config: GenerationConfig,
    root: Path,
    assembled: Assembled,
    gate: str = "manual",
    git: retrieval.GitState | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    monotonic: Callable[[], float] = time.monotonic,
) -> tuple[Json, list[Json]]:
    """(manifest without its files block, cases) of one generation run."""
    started = monotonic()
    created = clock().replace(microsecond=0)
    git = git or retrieval.git_state(root)
    dataset_path, probes_path = root / config.dataset, root / config.generation.probes
    questions = golden.select(golden.load(dataset_path), "retrieval", config.split)
    probes = [p for p in load_probes(probes_path) if config.split in (p.split, "all")]
    if not questions and not probes:
        raise golden.DatasetError(f"no retrieval question or probe in split {config.split}")
    chunks = list(assembled.chunks)
    resolved = golden.resolve(questions, chunks)
    canaries = answer_key.canaries(root)
    settings = config.generation
    cap = settings.run_timeout_s
    items: list[tuple[golden.Question, golden.Resolved | None]] = [
        *((item.question, item) for item in resolved),
        *((p, None) for p in probes),
    ]
    cases: list[Json] = []
    stopped: str | None = None
    timed_out = 0
    for question, item in items:
        for trial in range(1, settings.trials + 1):
            if monotonic() - started > cap:
                stopped = f"the run hit its wall-clock cap of {cap:g} s"
                break
            outcome = assembled.pipeline.ask(
                question.question, question.tenant, None, settings.seed + trial - 1
            )
            timed_out += outcome.timed_out
            case: Json = {
                "case_id": question.case_id,
                "trial": trial,
                "split": question.split,
                "tenant": question.tenant,
                "question": question.question,
                **_answer_fields(outcome),
            }
            if question.question_kind:
                case["question_kind"] = question.question_kind
            ids = [r.chunk.chunk_id for r in outcome.retrieved]
            if item is None:
                case |= {
                    "kind": generation_record.PROBE,
                    "expected": question.extra["expected"],
                    "feature_ids": question.extra["feature_ids"],
                    "canaries_of": question.extra.get("canaries_of"),
                    "retrieved": _retrieved(outcome.retrieved, frozenset()),
                }
            else:
                sets = item.label_sets()
                case |= {
                    "kind": generation_record.RETRIEVAL,
                    "labels": [
                        {
                            "doc_id": label.doc_id,
                            "section_id": label.section_id,
                            "chunk_ids": list(chunk_ids),
                            "found": bool(set(ids) & set(chunk_ids)),
                        }
                        for label, chunk_ids in item.groups
                    ],
                    "retrieved": _retrieved(outcome.retrieved, frozenset[str]().union(*sets)),
                    **record.case_scores(ids, sets, config.retriever.k),
                }
            case["checks"] = generation_record.case_checks(case, canaries)
            cases.append(case)
        if stopped:
            break
    unavailable = sum(1 for case in cases if case["status"] == Status.UNAVAILABLE.value)
    if unavailable:
        reason = (
            f"{unavailable} of {len(cases)} trial(s) unavailable, the model gave no reply "
            f"({timed_out} timed out, {unavailable - timed_out} a connection or HTTP error)"
        )
        stopped = f"{stopped}; {reason}" if stopped else reason
    if not cases:
        raise golden.DatasetError(f"the run stopped before its first case: {stopped}")
    spec = config.retriever
    retriever_json: Json = {"kind": spec.kind, "k": spec.k}
    if spec.kind == "hybrid":
        retriever_json |= {"candidates": spec.candidates, "rrf_k": spec.rrf_k}
    chunker_json: Json = {
        "chunk_size": config.chunker.chunk_size,
        "overlap": config.chunker.overlap,
    }
    embedder_json = {k: v for k, v in assembled.embedder_description.items() if k != "sha256"}
    generator_json = {k: v for k, v in assembled.chat_description.items() if k != "sha256"}
    totals: Json = {"cases": len(cases), "duration_s": round(monotonic() - started, 3)}
    if stopped:
        totals["stopped"] = stopped
    manifest: Json = {
        "schema_version": record.SCHEMA_VERSION,
        "run_id": f"{created:%Y%m%dT%H%M%SZ}-{config.name}-{config.split}-{git.sha[:7]}",
        "created_at": created.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "suite": config.suite,
        "gate": gate,
        "split": config.split,
        "trials": settings.trials,
        "seed": settings.seed,
        "provenance": assembled.provenance,
        "partial": stopped is not None,
        "git_sha": git.sha,
        "git_dirty": git.dirty,
        "config": {
            "name": config.name,
            "path": config.path,
            "file_sha256": config.file_sha256,
            "sha256": canonical_sha256(config.resolved()),
        },
        "chunker": {**chunker_json, "sha256": canonical_sha256(chunker_json)},
        "embedder": {**embedder_json, "sha256": canonical_sha256(embedder_json)},
        "retriever": {**retriever_json, "sha256": canonical_sha256(retriever_json)},
        "generator": {**generator_json, "sha256": canonical_sha256(generator_json)},
        "prompt": {"version": prompt.VERSION, "sha256": prompt.fingerprint()},
        "guards": [guard.name for guard in assembled.pipeline.guards],
        "intervals": {"method": "wilson", "level": settings.level, "unit": "case"},
        "dataset": {
            "path": config.dataset,
            "sha256": record.sha256_bytes(dataset_path.read_bytes()),
            "questions": len({str(c["case_id"]) for c in cases}),
        },
        "probes": {
            "path": config.generation.probes,
            "sha256": record.sha256_bytes(probes_path.read_bytes()),
            "questions": len(probes),
        },
        "corpus": {
            "documents": len({c.doc_id for c in chunks}),
            "chunks": len(chunks),
            "sha256": retrieval.corpus_sha256(chunks),
        },
        "tools": {
            **retrieval.tools(assembled.inventory.tools),
            "httpx": version("httpx"),
        },
        "results": generation_record.results(cases, settings.trials, settings.level),
        "totals": totals,
    }
    if config.ollama is not None:
        manifest["ollama"] = {
            k: v for k, v in asdict(config.ollama).items() if k != "memory_margin_gb"
        }
    return manifest, cases
