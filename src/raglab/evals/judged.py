"""The judged run (S5): the judge's verdicts on a finished generation run, written as run record v1
(suite judged; raglab.evals.judged_record).

1. **The source** is a valid, complete generation record (S5 judges the published consistency
   baseline). Its passages are rebuilt from the corpus at its chunk settings, after the corpus and
   dataset sha256 are checked against it, and the reference answers come from the golden file.
   No answer is generated here.
2. **The canaries first** (raglab.judge.canaries): one item off its side stops the run before any
   judged call (CanaryStop), and no record is written.
3. **Every answer** on the criteria its case takes (docs/CRITERIA.md), one call per criterion;
   `context_sufficient` once per case when every trial retrieved the same chunks.
4. **The checks on the judge**, after every answer is judged: trial 1 of every behaviour case
   judged a second time (repeatability), then `grounded` on trial 1 of every case with the
   passages in reverse order (the order check).

The run stops early, and is marked partial, when its wall-clock cap (judging.run_timeout_s) is
hit; a judge call with no reply also marks it partial. A partial run is never published.
"""

import hashlib
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from typing import cast

from raglab.chunk.sections import ChunkSettings
from raglab.core.ports import Judge
from raglab.core.types import JudgeItem, Passage, Status, Verdict
from raglab.evals import judged_record, record, retrieval
from raglab.evals.config import JudgeConfig, canonical_sha256
from raglab.ingest import pipeline
from raglab.judge import canaries
from raglab.judge.prompts import judge_v1

type Json = dict[str, object]
CONTEXT = judged_record.CONTEXT


class JudgedError(ValueError):
    """The source cannot be judged: invalid, partial, not a generation run, or its corpus or
    dataset has changed since it ran."""


def judge_item(
    criterion: str,
    source: Json,
    passages: Mapping[str, Passage],
    reference: str | None,
    seed: int,
    reverse: bool = False,
) -> JudgeItem:
    """The call of one criterion on one source answer: exactly the inputs the criterion sees."""
    sees = judge_v1.RULES[criterion].sees
    ids = judged_record.shown_ids(criterion, source, reverse)
    if "reference" in sees and reference is None:
        raise JudgedError(f"case {source['case_id']}: {criterion} needs a reference answer")
    return JudgeItem(
        criterion,
        str(source["question"]) if "question" in sees else None,
        tuple(passages[i] for i in ids) if "passages" in sees else None,
        reference if "reference" in sees else None,
        str(source["answer"]) if "answer" in sees else None,
        seed,
    )


def base_line(source: Json, reference: str | None) -> Json:
    """A judged line's fields copied from (or derived from) its source line."""
    line: Json = {
        "case_id": source["case_id"],
        "trial": source["trial"],
        "split": source["split"],
        "tenant": source["tenant"],
        "question": source["question"],
        "retrieved": source["retrieved"],
        "kind": source["kind"],
        "source_status": source["status"],
        "answer_sha256": judged_record.sha256_text(str(source["answer"])),
        "source_called": judged_record.source_called(source),
        "source_tokens": {
            "prompt": source["prompt_tokens"],
            "completion": source["completion_tokens"],
        },
        "reference_sha256": None if reference is None else judged_record.sha256_text(reference),
    }
    for name in ("question_kind", "expected", "golden_id", "position"):
        if name in source:
            line[name] = source[name]
    return line


def source_record(source_dir: Path, root: Path) -> tuple[bytes, Json, list[Json]]:
    """A valid, complete generation record, read; JudgedError otherwise."""
    if problems := record.validate(source_dir, root):
        raise JudgedError(f"{source_dir.name} is not a valid run record: " + "; ".join(problems))
    raw, manifest, cases = judged_record.read_source(source_dir)
    if manifest["suite"] != "generation":
        raise JudgedError(
            f"{source_dir.name} is a {manifest['suite']} run: only generation runs are judged"
        )
    if manifest["partial"]:
        raise JudgedError(f"{source_dir.name} is partial: only a complete run is judged")
    return raw, manifest, cases


def run(
    config: JudgeConfig,
    root: Path,
    source_dir: Path,
    judge: Judge,
    judge_description: Json,
    judge_provenance: str,
    gate: str = "manual",
    git: retrieval.GitState | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    monotonic: Callable[[], float] = time.monotonic,
    inventory: pipeline.Inventory | None = None,
    say: Callable[[str], None] = lambda text: None,
) -> tuple[Json, list[Json]]:
    """(manifest without its files block, lines) of one judged run. CanaryStop when a canary is
    off its side: then no judged call was made."""
    started = monotonic()
    created = clock().replace(microsecond=0)
    git = git or retrieval.git_state(root)
    raw, source_manifest, sources = source_record(source_dir, root)
    chunker = cast(dict[str, int], source_manifest["chunker"])
    settings = ChunkSettings(chunker["chunk_size"], chunker["overlap"])
    inventory = inventory or pipeline.ingest(root, settings)
    if inventory.settings != settings:
        raise JudgedError(f"the inventory was chunked at {inventory.settings}, not {settings}")
    chunks = list(inventory.chunks)
    corpus = cast(Json, source_manifest["corpus"])
    if retrieval.corpus_sha256(chunks) != corpus["sha256"]:
        raise JudgedError(
            f"the corpus has changed since {source_dir.name} ran (its sha256 is not "
            f"{str(corpus['sha256'])[:12]}): its passages cannot be rebuilt"
        )
    dataset = cast(Json, source_manifest["dataset"])
    dataset_path = root / str(dataset["path"])
    if record.sha256_bytes(dataset_path.read_bytes()) != dataset["sha256"]:
        raise JudgedError(f"{dataset['path']} has changed since {source_dir.name} ran")
    passages: dict[str, Passage] = {str(c.chunk_id): Passage.of(c) for c in chunks}
    refs = judged_record.references(root, dataset_path)
    seed = config.judging.seed

    # the canaries first: a hard stop on the judge, before any judged call
    canary_path = root / config.judging.canaries
    items = canaries.load(canary_path)
    canary_passages = (
        {i: passages[i] for c in items for i in c.corpus_ids()}
        if settings == canaries.SETTINGS
        else canaries.corpus_passages(root, items)
    )
    say(f"canaries: judging {len(items)} items first")
    canary_results = canaries.run(judge, items, canary_passages, seed)
    canaries.require_on_side(canary_results)
    say(f"canaries: all {len(items)} on their side")

    cap = config.judging.run_timeout_s
    stopped: str | None = None
    grouped: dict[str, list[Json]] = {}
    for source in sources:
        grouped.setdefault(str(source["case_id"]), []).append(source)
    context_at = {
        (case_id, trial)
        for case_id, rows in grouped.items()
        for trial in judged_record.context_trials(
            [{**r, "source_status": r["status"]} for r in rows]
        )
    }
    lines: list[Json] = []
    pairs: list[tuple[Json, Json]] = []

    def over_cap() -> bool:
        nonlocal stopped
        if stopped is None and monotonic() - started > cap:
            stopped = f"the run hit its wall-clock cap of {cap:g} s"
        return stopped is not None

    def call(criterion: str, source: Json, reverse: bool = False) -> Verdict:
        reference = judged_record.reference_of(source, refs)
        return judge.judge(judge_item(criterion, source, passages, reference, seed, reverse))

    for source in sources:
        if over_cap():
            break
        line = base_line(source, judged_record.reference_of(source, refs))
        verdicts: dict[str, Verdict] = {}
        for criterion in judged_record.trial_criteria(line):
            verdicts[criterion] = call(criterion, source)
        if (str(source["case_id"]), cast(int, source["trial"])) in context_at:
            verdicts[CONTEXT] = call(CONTEXT, source)
        line["verdicts"] = {k: canaries.verdict_json(v) for k, v in verdicts.items()}
        lines.append(line)
        pairs.append((line, source))
    say(f"judged {len(lines)} case-trials")
    # the checks on the judge, after every answer is judged
    for line, source in pairs:
        if line["trial"] != 1 or line["source_status"] != Status.OK.value:
            continue
        if line["kind"] == "behaviour":
            repeat: Json = {}
            for criterion in judged_record.trial_criteria(line):
                if over_cap():
                    break
                repeat[criterion] = canaries.verdict_json(call(criterion, source))
            line["repeat"] = repeat
    for line, source in pairs:
        trial_one = line["trial"] == 1 and line["source_status"] == Status.OK.value
        if trial_one and judged_record.GROUNDED in judged_record.trial_criteria(line):
            if over_cap():
                break
            verdict = call(judged_record.GROUNDED, source, reverse=True)
            line["reversed"] = {judged_record.GROUNDED: canaries.verdict_json(verdict)}
    for line in lines:
        latencies = [
            cast(float, cast(Json, v)["latency_ms"])
            for field in ("verdicts", "repeat", "reversed")
            for v in cast(Json, line.get(field) or {}).values()
        ]
        line["latency_ms"] = round(sum(latencies), 3)
    unavailable = sum(
        cast(Json, v)["status"] == Status.UNAVAILABLE.value
        for line in lines
        for field in ("verdicts", "repeat", "reversed")
        for v in cast(Json, line.get(field) or {}).values()
    )
    if unavailable:
        reason = f"{unavailable} judge call(s) unavailable, the judge gave no reply"
        stopped = f"{stopped}; {reason}" if stopped else reason
    if not lines:
        raise JudgedError(f"the run stopped before its first case-trial: {stopped}")
    level = config.judging.level
    trials = cast(int, source_manifest["trials"])
    canary_rows = canaries.results_json(canary_results)
    description = {k: v for k, v in judge_description.items() if k != "sha256"}
    provenance = (
        "fake"
        if "fake" in (judge_provenance, source_manifest["provenance"])
        else (judge_provenance)
    )
    totals: Json = {"cases": len(lines), "duration_s": round(monotonic() - started, 3)}
    if stopped:
        totals["stopped"] = stopped
    manifest: Json = {
        "schema_version": record.SCHEMA_VERSION,
        "run_id": (
            f"{created:%Y%m%dT%H%M%SZ}-{config.name}-{source_manifest['split']}-{git.sha[:7]}"
        ),
        "created_at": created.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "suite": judged_record.JUDGED,
        "gate": gate,
        "split": source_manifest["split"],
        "trials": trials,
        "seed": seed,
        "provenance": provenance,
        "partial": stopped is not None,
        "git_sha": git.sha,
        "git_dirty": git.dirty,
        "config": {
            "name": config.name,
            "path": config.path,
            "file_sha256": config.file_sha256,
            "sha256": canonical_sha256(config.resolved()),
        },
        "chunker": source_manifest["chunker"],
        "embedder": source_manifest["embedder"],
        "retriever": source_manifest["retriever"],
        "dataset": source_manifest["dataset"],
        "corpus": source_manifest["corpus"],
        "tools": {**retrieval.tools(inventory.tools), "httpx": version("httpx")},
        "judge": {**description, "sha256": canonical_sha256(description)},
        "judge_prompt": {"version": judge.version, "sha256": judge.fingerprint()},
        "source": {
            "run_id": source_manifest["run_id"],
            "suite": source_manifest["suite"],
            "manifest_sha256": hashlib.sha256(raw).hexdigest(),
        },
        "criteria": {
            "path": config.judging.criteria,
            "sha256": record.sha256_bytes((root / config.judging.criteria).read_bytes()),
        },
        "canaries": {
            "path": config.judging.canaries,
            "sha256": record.sha256_bytes(canary_path.read_bytes()),
            "results": canary_rows,
        },
        "intervals": {"method": "wilson", "level": level, "unit": "case"},
        "results": judged_record.results(lines, trials, level, canary_rows),
        "totals": totals,
    }
    if config.ollama is not None:
        manifest["ollama"] = {
            k: v for k, v in asdict(config.ollama).items() if k != "memory_margin_gb"
        }
    return manifest, lines


def summary(results: Sequence[canaries.CanaryResult]) -> list[str]:
    """One line per canary: its id, criterion, side and verdict (raglab canaries)."""
    return [
        f"{r.canary.id} {r.canary.criterion}: must {r.canary.side}, judged {r.verdict.verdict} "
        f"({r.verdict.status.value}) {'on side' if r.on_side else 'OFF ITS SIDE'}"
        for r in results
    ]
