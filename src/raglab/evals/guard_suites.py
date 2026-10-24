"""The suites per filter (S7, AG6; how-to 07): every guard layer over its must-block and
must-not-block cases, each decision binary, with the miss rate, the false-block rate and the
latency each layer adds.

The cases of a layer:

- **handwritten**, from the security pack (raglab.ingest.security_pack, datasets/security/), with
  planted values and team contacts resolved by reference;
- **derived**, each carrying its source's sign-off: the golden set's questions of the split (the
  input layers; dev unless the gate is nightly or release, as for every run), the clean
  inventory's chunks (the instruction scan and the register filter, must-not-block), the attack
  pages' chunks (the register filter, must-block; the instruction scan, must-block where a chunk
  of F-47's locations holds its payload), and the recorded answers of the consistency baseline
  and its repeats (the output layers, must-not-block: the replay of D3).

`decide` runs one layer on one input and says whether it blocked: refused at input, a chunk left
out or a chunk quarantined, or the answer withheld. `run` measures each call with
time.perf_counter and reports, per layer: must-block n and misses, must-not-block n and false
blocks, each rate with its 95% Wilson interval (0 of n reported with its upper bound), and p50 and
p95 of the added latency in milliseconds over all the layer's calls. The record is local
provenance: a real run on this machine.
"""

import json
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from raglab.core.ports import Guardrail
from raglab.core.types import Answer, Chunk, Conflict, ScoredChunk, Status
from raglab.evals import golden, metrics, record
from raglab.evals.record import Json, as_json, as_list
from raglab.evals.retrieval import GitState
from raglab.guard import guard_set
from raglab.ingest import answer_key, scan
from raglab.ingest import security_pack as pack

SCHEMA_VERSION = "guard-suites.v1"
OUT = "runs/guard-suites"
INPUT_LAYERS = ("tenant", "input-limits", "injection")
OUTPUT_LAYERS = ("citations", "links", "secrets-pii", "prompt-leak")
LEVEL = 0.95


class SuiteError(ValueError):
    pass


def pack_chunk(item: dict[str, object]) -> Chunk:
    """A chunk of a pack case: its id (`<doc>@<version>/<section>/<n>`), document, tenant and
    status, with a placeholder text."""
    chunk_id = str(item["id"])
    version = chunk_id.split("@", 1)[1].split("/", 1)[0] if "@" in chunk_id else "1"
    text = f"text of {chunk_id}"
    return Chunk(
        chunk_id=chunk_id,  # type: ignore[arg-type]
        doc_id=str(item["doc"]),
        version=version,
        status=str(item["status"]),
        tenant=str(item["tenant"]),
        kind="company",
        title=str(item["doc"]),
        section_id="1",
        section_title="1",
        page=None,
        page_end=None,
        licence="CC-BY-4.0",
        path=f"corpus/{str(item['doc']).lower()}.md",
        char_start=0,
        char_end=len(text),
        text=text,
    )


def _chunks(value: object) -> tuple[ScoredChunk, ...]:
    items = [as_json(i) for i in as_list(value or [])]
    out: list[ScoredChunk] = []
    for n, item in enumerate(items):
        if "id" not in item:
            item = {**item, "id": f"{item['doc']}@1.0/1/{n + 1}"}
        out.append(ScoredChunk(pack_chunk(item), 1.0))
    return tuple(out)


def output_answer(data: dict[str, object]) -> Answer:
    """The answer of an output-stage case: its text, citations, and a conflict when it names
    conflict ids or a note."""
    cited = tuple(str(i) for i in as_list(data.get("cited") or []))
    conflict_ids = tuple(str(i) for i in as_list(data.get("conflict") or []))
    note = str(data.get("note") or "")
    conflict = None
    if conflict_ids or note:
        conflict = Conflict(conflict_ids or cited or ("A-PWD-V2@2.0/4.4/1",), note)
    return Answer(str(data.get("answer", "")), cited, "answer", conflict, Status.OK)


def decide(layer: str, data: dict[str, object], guards: dict[str, Guardrail]) -> bool:
    """Whether the layer blocks this input (see the module docstring)."""
    stage = data.get("stage")
    if layer == scan.LAYER:
        return scan.flags(str(data["text"]))
    guard = guards[layer]
    if stage == "input":
        question = str(data.get("question", "")) * int(cast(int, data.get("repeat", 1)))
        tenant = data.get("tenant")
        caller = data.get("caller")
        callers = None if caller is None else frozenset(str(t) for t in as_list(caller))
        return (
            guard.check_input(question, None if tenant is None else str(tenant), callers)
            is not None
        )
    if stage == "retrieved":
        tenant = str(data["tenant"])
        retrieved = _chunks(data.get("chunks"))
        if guard.check_retrieved(tenant, retrieved) is not None:
            return True
        kept, dropped = guard.drop_retrieved(tenant, retrieved)
        return bool(dropped) or len(kept) != len(retrieved)
    if stage == "output":
        return guard.check_output(output_answer(data), _chunks(data.get("chunks"))) is not None
    raise SuiteError(f"{layer}: an input of stage {stage!r} has no check")


@dataclass(frozen=True)
class Item:
    """One case of a layer's suite: its id, kind (must_block or must_not_block), source and the
    call that decides it."""

    case_id: str
    kind: str
    source: str
    call: Callable[[], bool]


def handwritten(root: Path, guards: dict[str, Guardrail], system: str) -> dict[str, list[Item]]:
    found = pack.sources(root, system)
    suites: dict[str, list[Item]] = {}
    for case in pack.load(root):
        if case.layer == "attack":
            continue
        data = pack.resolved_input(case, found)
        layer = case.layer

        def call(layer: str = layer, data: dict[str, object] = data) -> bool:
            return decide(layer, data, guards)

        suites.setdefault(layer, []).append(Item(case.id, case.kind, case.file, call))
    return suites


def derived(
    root: Path,
    guards: dict[str, Guardrail],
    questions: Sequence[golden.Question],
    clean: Sequence[Chunk],
    attack: Sequence[Chunk],
    answers: Sequence[tuple[str, Json, tuple[ScoredChunk, ...]]],
) -> dict[str, list[Item]]:
    """The derived suites (see the module docstring); answers: (where, case line, its resolved
    retrieved chunks) of the recorded runs."""
    suites: dict[str, list[Item]] = {}
    for layer in INPUT_LAYERS:
        for q in questions:
            data: dict[str, object] = {"stage": "input", "question": q.question, "tenant": q.tenant}

            def ask(layer: str = layer, data: dict[str, object] = data) -> bool:
                return decide(layer, data, guards)

            suites.setdefault(layer, []).append(
                Item(f"{q.case_id}", "must_not_block", "golden set", ask)
            )
    register = guards["register"]

    def dropped(chunk: Chunk) -> Callable[[], bool]:
        def call() -> bool:
            kept, _ = register.drop_retrieved(chunk.tenant, (ScoredChunk(chunk, 1.0),))
            return not kept

        return call

    def flagged(chunk: Chunk) -> Callable[[], bool]:
        return lambda: scan.flags(chunk.text)

    # F-47's payload where the answer key locates it (T-HIDDEN's note; its HTML comment is not
    # text a reader sees, so the parser drops it and no chunk holds it)
    planted = answer_key.features(root)["F-47"].locations
    for chunk in clean:
        suites.setdefault("register", []).append(
            Item(chunk.chunk_id, "must_not_block", "clean inventory", dropped(chunk))
        )
        suites.setdefault(scan.LAYER, []).append(
            Item(chunk.chunk_id, "must_not_block", "clean inventory", flagged(chunk))
        )
    for chunk in attack:
        suites.setdefault("register", []).append(
            Item(chunk.chunk_id, "must_block", "attack pages", dropped(chunk))
        )
        if any(
            (chunk.doc_id, chunk.section_id) == (loc.doc, loc.section)
            and any(v in chunk.text for v in loc.values)
            for loc in planted
        ):
            suites.setdefault(scan.LAYER, []).append(
                Item(chunk.chunk_id, "must_block", "attack pages (F-47)", flagged(chunk))
            )
    for where, case, retrieved in answers:
        answer = Answer(
            str(case["answer"]),
            tuple(str(i) for i in as_list(case["cited_ids"])),
            cast(str, case["label"]),  # type: ignore[arg-type]
            None
            if case["conflict"] is None
            else Conflict(
                tuple(str(i) for i in as_list(as_json(case["conflict"])["chunk_ids"])),
                str(as_json(case["conflict"])["note"]),
            ),
            Status.OK,
        )
        for layer in OUTPUT_LAYERS:
            guard = guards[layer]

            def check(
                guard: Guardrail = guard,
                answer: Answer = answer,
                retrieved: tuple[ScoredChunk, ...] = retrieved,
            ) -> bool:
                return guard.check_output(answer, retrieved) is not None

            suites.setdefault(layer, []).append(
                Item(where, "must_not_block", "recorded answers", check)
            )
    return suites


def recorded_answers(
    runs: Sequence[Path], chunks: Sequence[Chunk]
) -> list[tuple[str, Json, tuple[ScoredChunk, ...]]]:
    """Every answered case line (status ok) of the runs, with its retrieved chunks resolved in
    the inventory; SuiteError when an id no longer resolves."""
    by_id: dict[str, Chunk] = {str(c.chunk_id): c for c in chunks}
    out: list[tuple[str, Json, tuple[ScoredChunk, ...]]] = []
    for run_dir in runs:
        _, cases = record.read(run_dir)
        for case in cases:
            if case["status"] != Status.OK.value:
                continue
            ids = [str(as_json(r)["chunk_id"]) for r in as_list(case["retrieved"])]
            if missing := [i for i in ids if i not in by_id]:
                raise SuiteError(f"{run_dir.name}: {missing} are not in the inventory")
            where = f"{run_dir.name}:{case['case_id']}:{case['trial']}"
            out.append((where, case, tuple(ScoredChunk(by_id[i], 0.0) for i in ids)))
    return out


def _rate(failures: int, n: int) -> Json:
    if n == 0:
        return {"n": 0}
    interval = metrics.wilson_interval(failures / n, n, LEVEL)
    return {"failures": failures, **interval.as_json()}


def run(suites: dict[str, list[Item]]) -> tuple[Json, list[str]]:
    """Each layer's results, and one line per wrong decision naming the case and the layer."""
    layers: Json = {}
    wrong: list[str] = []
    for layer, items in sorted(suites.items()):
        seconds: list[float] = []
        misses = false_blocks = blocks = passes = 0
        for item in items:
            started = time.perf_counter()
            blocked = item.call()
            seconds.append(time.perf_counter() - started)
            if item.kind == "must_block":
                blocks += 1
                if not blocked:
                    misses += 1
                    wrong.append(f"{layer}: {item.case_id} ({item.source}) was not blocked")
            else:
                passes += 1
                if blocked:
                    false_blocks += 1
                    wrong.append(f"{layer}: {item.case_id} ({item.source}) was blocked")
        ms = [s * 1000 for s in seconds]
        layers[layer] = {
            "must_block": {"n": blocks, **_rate(misses, blocks)},
            "must_not_block": {"n": passes, **_rate(false_blocks, passes)},
            "sources": sorted({i.source for i in items}),
            "latency_ms": {
                "n": len(ms),
                "p50": round(metrics.quantile(ms, 0.5), 6),
                "p95": round(metrics.quantile(ms, 0.95), 6),
            },
        }
    return layers, wrong


def record_json(
    layers: Json,
    guards: Sequence[Guardrail],
    git: GitState,
    split: str,
    runs: Sequence[Path],
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> Json:
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": clock().replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_sha": git.sha,
        "git_dirty": git.dirty,
        "provenance": "local",
        "split": split,
        "replayed_runs": [r.name for r in runs],
        "guard_set": guard_set(guards),
        "interval": {"method": "wilson", "level": LEVEL},
        "layers": layers,
    }


def render(layers: Json) -> str:
    """A table of the results, one row per layer."""
    lines = [
        "| Layer | Must-block: misses / n (95% Wilson) | Must-not-block: false blocks / n "
        "(95% Wilson) | Added latency p50 / p95 (ms) |",
        "|---|---|---|---|",
    ]
    for layer, raw in layers.items():
        result = as_json(raw)
        cells: list[str] = []
        for part in ("must_block", "must_not_block"):
            r = as_json(result[part])
            if r["n"] == 0:
                cells.append("none")
                continue
            low, high = cast(float, r["ci_low"]), cast(float, r["ci_high"])
            cells.append(f"{r['failures']} / {r['n']} ({low:.3f} to {high:.3f})")
        latency = as_json(result["latency_ms"])
        lines.append(
            f"| {layer} | {cells[0]} | {cells[1]} | "
            f"{cast(float, latency['p50']):.3f} / {cast(float, latency['p95']):.3f} |"
        )
    return "\n".join(lines) + "\n"


def write(root: Path, data: Json, out: str = OUT) -> Path:
    stamp = str(data["created_at"]).replace("-", "").replace(":", "")
    path = root / out / f"{stamp}-{str(data['git_sha'])[:7]}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
