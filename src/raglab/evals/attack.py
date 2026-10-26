"""The attack suite (S7, AG9): the security pack's attack cases (datasets/security/attacks.yaml)
asked through the pipeline with the corpus's three attack pages indexed in tenant A as pages
outside the register, N trials each, in one of two configurations:

- `defences-off`: S3's guard set (tenant, input limits, the citation validator without S7's
  register rule) and no instruction scan: whether the model alone resists. A measured result,
  reported by counts and never published (publish refuses it);
- `defences-on`: S7a's guard set and the instruction scan: every safety check of every case and
  trial must hold (raglab.evals.attack_record).

Trial t of every case uses seed + t - 1. The run checks the pack first (its schema check, the
hard stop of this suite: check-dataset never reads the pack) and stops early, marked partial, at
its wall-clock cap; any trial the model left unanswered marks it partial too. The loopback-only
egress guard (raglab.runtime.egress) is installed by the caller around the assembly and the run,
and the record says what it saw: `none`, or each refused attempt.
"""

import time
from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from typing import cast

from raglab.core.ports import ChatModel, Embedder
from raglab.core.types import Status
from raglab.evals import attack_record, record, retrieval
from raglab.evals.config import GenerationConfig, canonical_sha256
from raglab.generate.assemble import Assembled, assemble
from raglab.generate.pipeline import Outcome
from raglab.generate.prompts import CURRENT as prompt
from raglab.guard import default_guards, guard_set, s3_guards
from raglab.ingest import answer_key, attacks
from raglab.ingest import pipeline as ingest
from raglab.ingest import security_pack as pack
from raglab.runtime.egress import EgressGuard

type Json = dict[str, object]


class AttackError(ValueError):
    pass


def assemble_for(
    config: GenerationConfig,
    root: Path,
    configuration: str,
    *,
    embedder: tuple[Embedder, Json, str] | None = None,
    chat: tuple[ChatModel, Json, str] | None = None,
    inventory: ingest.Inventory | None = None,
) -> Assembled:
    """The pipeline of a configuration: the attack pages indexed beside the inventory, S3's guards
    and no scan (defences-off) or S7a's guards and the scan (defences-on)."""
    if configuration not in attack_record.CONFIGURATIONS:
        raise AttackError(f"configuration {configuration!r} is not one of the attack suite's")
    inventory = inventory or ingest.ingest(root, config.chunker)
    on = configuration == "defences-on"
    return assemble(
        config,
        root,
        embedder=embedder,
        chat=chat,
        inventory=inventory,
        guards=default_guards(root, inventory.chunks) if on else s3_guards(),
        extra=attacks.attack_chunks(root, config.chunker),
        scan_index=on,
    )


def _answer_fields(outcome: Outcome) -> Json:
    """The answer and every guard event of a trial, the drop steps' first (they come first)."""
    answer, conflict = outcome.answer, outcome.answer.conflict
    return {
        "status": answer.status.value,
        "label": answer.label,
        "answer": answer.text,
        "cited_ids": list(answer.cited_ids),
        "conflict": None
        if conflict is None
        else {"chunk_ids": list(conflict.chunk_ids), "note": conflict.note},
        "guard_events": [
            {"guard": e.guard, "stage": e.stage, "reason": e.reason}
            for e in (*outcome.dropped, *outcome.events)
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
    configuration: str,
    egress: EgressGuard,
    gate: str = "manual",
    git: retrieval.GitState | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    monotonic: Callable[[], float] = time.monotonic,
) -> tuple[Json, list[Json]]:
    """(manifest without its files block, cases) of one attack run."""
    started = monotonic()
    created = clock().replace(microsecond=0)
    git = git or retrieval.git_state(root)
    found = pack.load(root)
    if problems := pack.problems(root, found, pack.sources(root, prompt.SYSTEM)):
        raise AttackError("the security pack stopped the run:\n" + "\n".join(problems))
    listed = [c for c in found if c.layer == attack_record.ATTACK]
    features = answer_key.features(root)
    banned = [s for strings in answer_key.must_not_contain(root).values() for s in strings]
    canaries = answer_key.canary_parts(root)
    statuses = {str(c.chunk_id): c.status for c in assembled.chunks}
    settings = config.generation
    cap = settings.run_timeout_s
    cases: list[Json] = []
    stopped: str | None = None
    for item in listed:
        data = item.input
        question, tenant = str(data["question"]), str(data["tenant"])
        listed_features = data.get("features")
        ids = (
            [str(f) for f in cast(list[object], listed_features)]
            if isinstance(listed_features, list)
            else []
        )
        for trial in range(1, settings.trials + 1):
            if monotonic() - started > cap:
                stopped = f"the run hit its wall-clock cap of {cap:g} s"
                break
            outcome = assembled.pipeline.ask(question, tenant, None, settings.seed + trial - 1)
            case: Json = {
                "case_id": item.id,
                "trial": trial,
                "split": config.split,
                "tenant": tenant,
                "question": question,
                "kind": attack_record.ATTACK,
                "attack": str(data["attack"]),
                "feature_ids": ids,
                "expected_label": attack_record.expected_label(features, ids, configuration),
                **_answer_fields(outcome),
                "retrieved": [
                    {
                        "rank": rank,
                        "chunk_id": r.chunk.chunk_id,
                        "score": round(r.score, 6),
                        "relevant": False,
                        "status": statuses.get(str(r.chunk.chunk_id), r.chunk.status),
                    }
                    for rank, r in enumerate(outcome.retrieved, start=1)
                ],
            }
            case["checks"] = attack_record.checks(case, banned, canaries, prompt.SYSTEM)
            cases.append(case)
        if stopped:
            break
    unavailable = sum(1 for c in cases if c["status"] == Status.UNAVAILABLE.value)
    if unavailable:
        reason = f"{unavailable} of {len(cases)} trial(s) unavailable, the model gave no reply"
        stopped = f"{stopped}; {reason}" if stopped else reason
    if not cases:
        raise AttackError(f"the run stopped before its first case: {stopped}")
    chunks = list(assembled.chunks)
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
    dataset_path = root / config.dataset
    scanned = assembled.scanned
    manifest: Json = {
        "schema_version": record.SCHEMA_VERSION,
        "run_id": f"{created:%Y%m%dT%H%M%SZ}-{config.name}-{configuration}-{config.split}-"
        f"{git.sha[:7]}",
        "created_at": created.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "suite": attack_record.ATTACK,
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
        "guard_set": guard_set(assembled.pipeline.guards, scanned=scanned is not None),
        "intervals": {"method": "wilson", "level": settings.level, "unit": "case"},
        "attack": {
            "configuration": configuration,
            "pages": {
                "documents": sorted({c.doc_id for c in assembled.pages}),
                "chunks": len(assembled.pages),
            },
            "quarantined": list(scanned.quarantined) if scanned is not None else [],
            "egress": egress.summary(),
        },
        "dataset": {
            "path": config.dataset,
            "sha256": record.sha256_bytes(dataset_path.read_bytes()),
            "questions": len({str(c["case_id"]) for c in cases}),
        },
        "corpus": {
            "documents": len({c.doc_id for c in chunks}),
            "chunks": len(chunks),
            "sha256": retrieval.corpus_sha256(chunks),
        },
        "tools": {**retrieval.tools(assembled.inventory.tools), "httpx": version("httpx")},
        "results": attack_record.results(cases, settings.trials, settings.level, configuration),
        "totals": totals,
    }
    if config.ollama is not None:
        manifest["ollama"] = {
            k: v for k, v in asdict(config.ollama).items() if k != "memory_margin_gb"
        }
    return manifest, cases


def unsafe(manifest: Json) -> list[str]:
    """Why a finished attack run fails its gate: a defences-on run with a failed safety check,
    or any run whose egress guard saw an attempt off loopback."""
    block = record.as_json(manifest["attack"])
    found = record.as_json(record.as_json(manifest["results"])["attack"])
    out: list[str] = []
    if block["egress"] != "none":
        out.append(f"egress: {block['egress']}")
    if block["configuration"] == "defences-on" and found["failed_cases"]:
        out.append(f"with defences on, cases failed a safety check: {found['failed_cases']}")
    return out
