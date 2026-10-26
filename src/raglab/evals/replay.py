"""The guard replay (S7, D3 "On by default, proven inert by replay"): a guard set is replayed
over the published records of the consistency baseline and its repeats, with no model, and a
baseline made under another guard set stays current only when the replay shows zero events.

What a replay checks, on every case line of every run:

- the input layers on the recorded question (asked as its tenant, no caller, as the run asked);
- the instruction scan and the retrieved-stage layers (their checks and drop steps) on the
  recorded retrieved chunk ids, resolved in the current inventory (an id that no longer resolves
  is an event: the record cannot be replayed);
- the output layers on every recorded answer (status ok) with its cited ids, its conflict and its
  resolved retrieved chunks.

Zero events means those recorded trials are exactly what the new pipeline gives on them: no
request refused, no chunk left out or quarantined, no answer withheld. Then `raglab replay`
writes the record under runs/replays/ (committed; runs/published never changes), named by the
baseline and the guard set's sha256. Any event is printed by layer and case, and no record is
written: the stage pauses for the maintainer (D3 B, a new baseline, follows).

`current_for` is the staleness rule's guard-set part: a baseline is current for a guard set when
its manifest recorded that set, or when a replay record for it, that set and the baseline's and
repeats' published manifests shows zero events.
"""

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from raglab.core.ports import Guardrail
from raglab.core.types import Answer, Chunk, Conflict, ScoredChunk, Status
from raglab.evals import publish, record
from raglab.evals.record import Json, as_json, as_list
from raglab.evals.retrieval import GitState
from raglab.guard import guard_set
from raglab.ingest import scan

REPLAYS = "runs/replays"
SCHEMA_VERSION = "guard-replay.v1"
KEY = "generation/generation-local-ollama/dev"
# the manifest fields that make a run a repeat of the baseline: the staleness fields of the
# consistency gate (raglab.evals.gate.STALE) and the baseline key
SAME = (
    ("dataset", "sha256"),
    ("config", "sha256"),
    ("prompt", "sha256"),
    ("generator", "digest"),
    ("", "trials"),
    ("", "suite"),
    ("", "split"),
)


class ReplayError(ValueError):
    pass


def _field(manifest: Json, section: str, key: str) -> object:
    return manifest.get(key) if not section else as_json(manifest.get(section, {})).get(key)


def baseline_runs(root: Path, key: str = KEY) -> list[Path]:
    """The baseline of key in runs/published/index.json, then its repeats: the published runs of
    the same config whose staleness fields equal the baseline's, oldest first."""
    baseline_dir = publish.baseline_run(root, key)
    if baseline_dir is None:
        raise ReplayError(f"no published baseline for {key}")
    baseline, _ = record.read(baseline_dir)
    name = as_json(baseline["config"])["name"]
    runs = [baseline_dir]
    for path in sorted((root / publish.PUBLISHED).glob(f"*/{record.MANIFEST}")):
        run_dir = path.parent
        if run_dir == baseline_dir:
            continue
        manifest, _ = record.read(run_dir)
        if as_json(manifest["config"]).get("name") != name:
            continue
        if all(_field(manifest, s, k) == _field(baseline, s, k) for s, k in SAME):
            runs.append(run_dir)
    return runs


@dataclass(frozen=True)
class Event:
    run: str
    case: str
    trial: int
    guard: str
    stage: str

    def line(self) -> str:
        return f"{self.run} {self.case} trial {self.trial}: {self.guard} at {self.stage}"


@dataclass
class Replay:
    runs: list[Path]
    checked: dict[str, int] = field(default_factory=dict[str, int])
    events: list[Event] = field(default_factory=list[Event])

    def count(self, what: str, n: int = 1) -> None:
        self.checked[what] = self.checked.get(what, 0) + n


def _answer(case: Json) -> Answer:
    conflict = case["conflict"]
    found = None
    if conflict is not None:
        block = as_json(conflict)
        ids = tuple(str(i) for i in as_list(block["chunk_ids"]))
        found = Conflict(ids, str(block["note"])) if ids else None
    cited = tuple(str(i) for i in as_list(case["cited_ids"]))
    label = cast(str, case["label"])
    return Answer(str(case["answer"]), cited, label, found, Status.OK)  # type: ignore[arg-type]


def replay(runs: Sequence[Path], guards: Sequence[Guardrail], chunks: Sequence[Chunk]) -> Replay:
    """The replay of guards over every case line of runs (see the module docstring)."""
    by_id: dict[str, Chunk] = {str(c.chunk_id): c for c in chunks}
    result = Replay(list(runs))
    for run_dir in runs:
        _, cases = record.read(run_dir)
        for case in cases:
            where = (run_dir.name, str(case["case_id"]), cast(int, case["trial"]))

            def event(guard: str, stage: str, at: tuple[str, str, int] = where) -> None:
                result.events.append(Event(*at, guard, stage))

            question, tenant = str(case["question"]), str(case["tenant"])
            result.count("questions")
            for guard in guards:
                if guard.check_input(question, tenant, None) is not None:
                    event(guard.name, "input")
            ids = [str(as_json(r)["chunk_id"]) for r in as_list(case["retrieved"])]
            missing = [i for i in ids if i not in by_id]
            if missing:
                event("replay", "retrieved")
                continue
            retrieved = tuple(ScoredChunk(by_id[i], 0.0) for i in ids)
            result.count("retrieved lists")
            result.count("retrieved chunks", len(ids))
            if scan.scan([r.chunk for r in retrieved]).quarantined:
                event(scan.LAYER, "ingest")
            for guard in guards:
                if guard.check_retrieved(tenant, retrieved) is not None:
                    event(guard.name, "retrieved")
                kept, dropped = guard.drop_retrieved(tenant, retrieved)
                if dropped or len(kept) != len(retrieved):
                    event(guard.name, "retrieved")
            if case["status"] != Status.OK.value:
                continue
            result.count("answers")
            answer = _answer(case)
            for guard in guards:
                if guard.check_output(answer, retrieved) is not None:
                    event(guard.name, "output")
    return result


def record_path(root: Path, baseline: str, guards_sha256: str) -> Path:
    return root / REPLAYS / f"{baseline}--{guards_sha256[:12]}.json"


def record_json(
    result: Replay,
    guards: Sequence[Guardrail],
    git: GitState,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> Json:
    """The replay record of a replay with zero events."""
    if result.events:
        raise ReplayError(f"{len(result.events)} event(s): a replay with events writes no record")
    baseline, _ = record.read(result.runs[0])
    runs: list[Json] = [
        {
            "run_id": run_dir.name,
            "manifest_sha256": record.sha256_bytes((run_dir / record.MANIFEST).read_bytes()),
        }
        for run_dir in result.runs
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": clock().replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_sha": git.sha,
        "git_dirty": git.dirty,
        "provenance": "local",
        "baseline": result.runs[0].name,
        "key": publish.baseline_key(baseline),
        "recorded_guards": baseline.get("guards", []),
        "runs": runs,
        "guard_set": guard_set(guards),
        "checked": dict(sorted(result.checked.items())),
        "events": [],
    }


def write(root: Path, data: Json) -> Path:
    guards_sha = str(as_json(data["guard_set"])["sha256"])
    path = record_path(root, str(data["baseline"]), guards_sha)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def current_for(root: Path, baseline_dir: Path, guards_sha256: str) -> tuple[bool, str]:
    """Whether the baseline is current for the guard set (see the module docstring), and why."""
    baseline, _ = record.read(baseline_dir)
    recorded: object = baseline.get("guard_set")
    if recorded is not None and as_json(recorded).get("sha256") == guards_sha256:
        return True, f"{baseline_dir.name} was made under guard set {guards_sha256[:12]}"
    path = record_path(root, baseline_dir.name, guards_sha256)
    if not path.is_file():
        return False, (
            f"the baseline {baseline_dir.name} was made under another guard set and no replay "
            f"record shows guard set {guards_sha256[:12]} inert on it ({path.name} is missing): "
            "run `raglab replay`, or publish a new baseline"
        )
    data = as_json(json.loads(path.read_text(encoding="utf-8")))
    if as_json(data["guard_set"]).get("sha256") != guards_sha256 or data.get("events"):
        return False, f"{path.name} is not a zero-event replay of guard set {guards_sha256[:12]}"
    published = root / publish.PUBLISHED
    for run in (as_json(r) for r in as_list(data["runs"])):
        manifest = published / str(run["run_id"]) / record.MANIFEST
        if not manifest.is_file():
            return False, f"{path.name} names {run['run_id']}, which is not published"
        if record.sha256_bytes(manifest.read_bytes()) != run["manifest_sha256"]:
            return False, f"{path.name} replayed another manifest of {run['run_id']}"
    if as_json(as_list(data["runs"])[0])["run_id"] != baseline_dir.name:
        return False, f"{path.name} does not start with the baseline {baseline_dir.name}"
    return True, f"{path.name} shows guard set {guards_sha256[:12]} inert on the baseline"
