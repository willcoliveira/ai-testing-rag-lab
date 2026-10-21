"""The canary set (S5): hand-written items, each a question, its passages, an answer (or a reference
answer), the criterion it is judged on and the side it must land on (docs/CRITERIA.md, "The
canary set"). It is a hard stop on the judge, not on the system: the canaries run first in every
judge session, right after the judge's live contract test, and one item on its wrong side stops
the session before any judged call, naming the item; no judged record is written. Every item is
judged, so a stop names every item off its side, not only the first.

One JSON object per line (datasets/canaries.judge.jsonl): `id`, `criterion`, `side` (pass or
fail), `purpose` (what the item plants), and exactly the inputs its criterion sees
(raglab.judge.prompts.judge_v2.RULES): `question`, `passages`, `reference`, `answer`. A passage is
a corpus chunk id, whose text is read from the register's documents at the default chunk settings
(1,200 characters, overlap 1), the settings the ids are written at; or an object written by hand
(`chunk_id`, `document`, `version`, `section`, `status`, `text`), for a passage the corpus does not
hold, such as the planted instruction of an injection canary.
"""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from raglab.chunk.sections import ChunkSettings
from raglab.core.ports import Judge
from raglab.core.types import CRITERIA, JudgeItem, Passage, Status, Verdict
from raglab.ingest import pipeline
from raglab.judge.prompts import judge_v2

type Json = dict[str, object]
SIDES = ("pass", "fail")
PASSAGE_FIELDS = ("chunk_id", "document", "version", "section", "status", "text")
# the settings the canary set's chunk ids are written at
SETTINGS = ChunkSettings()


class CanaryError(ValueError):
    """The canary file is not a valid canary set, or names a chunk the corpus does not hold."""


class CanaryStop(RuntimeError):
    """A canary landed on its wrong side: the judge session stops before any judged call."""


@dataclass(frozen=True)
class Canary:
    id: str
    criterion: str
    side: str
    purpose: str
    question: str | None
    passages: tuple[str | Passage, ...] | None
    reference: str | None
    answer: str | None

    def corpus_ids(self) -> tuple[str, ...]:
        """The corpus chunk ids its passages name (a hand-written passage names none)."""
        return tuple(p for p in self.passages or () if isinstance(p, str))


def _text(row: Json, name: str, where: str) -> str:
    value = row.get(name)
    if not isinstance(value, str) or not value.strip():
        raise CanaryError(f"{where}: {name} must be a non-empty string")
    return value


def _passage(item: object, where: str) -> str | Passage:
    if isinstance(item, str) and item.strip():
        return item
    if not isinstance(item, dict):
        raise CanaryError(f"{where}: a passage is a chunk id or an object")
    row = {str(k): v for k, v in cast(dict[object, object], item).items()}
    if sorted(row) != sorted(PASSAGE_FIELDS):
        raise CanaryError(f"{where}: a written passage has exactly {list(PASSAGE_FIELDS)}")
    return Passage(*(_text(row, name, where) for name in PASSAGE_FIELDS))


def parse_line(line: str, where: str) -> Canary:
    try:
        raw: object = json.loads(line)
    except json.JSONDecodeError as error:
        raise CanaryError(f"{where}: not JSON ({error.msg})") from error
    if not isinstance(raw, dict):
        raise CanaryError(f"{where}: a canary is a JSON object")
    row = {str(k): v for k, v in cast(dict[object, object], raw).items()}
    canary_id = _text(row, "id", where)
    where = f"{where} ({canary_id})"
    criterion, side = _text(row, "criterion", where), _text(row, "side", where)
    if criterion not in CRITERIA:
        raise CanaryError(f"{where}: criterion {criterion!r} is not one of {list(CRITERIA)}")
    if side not in SIDES:
        raise CanaryError(f"{where}: side {side!r} is not pass or fail")
    sees = judge_v2.RULES[criterion].sees
    inputs = set(row) - {"id", "criterion", "side", "purpose"}
    if inputs != set(sees):
        raise CanaryError(
            f"{where}: a {criterion} item has exactly the inputs {criterion} sees, {list(sees)}; "
            f"it has {sorted(inputs)}"
        )
    passages = None
    if "passages" in row:
        listed = row["passages"]
        if not isinstance(listed, list):
            raise CanaryError(f"{where}: passages is a list")
        passages = tuple(_passage(p, where) for p in cast(list[object], listed))
    return Canary(
        canary_id,
        criterion,
        side,
        _text(row, "purpose", where),
        _text(row, "question", where) if "question" in row else None,
        passages,
        _text(row, "reference", where) if "reference" in row else None,
        _text(row, "answer", where) if "answer" in row else None,
    )


def load(path: Path) -> list[Canary]:
    """Every canary of the file, in file order; CanaryError names the line and the item."""
    canaries: list[Canary] = []
    seen: set[str] = set()
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        canary = parse_line(line, f"{path.name}:{number}")
        if canary.id in seen:
            raise CanaryError(f"{path.name}:{number}: id {canary.id} is used twice")
        seen.add(canary.id)
        canaries.append(canary)
    if not canaries:
        raise CanaryError(f"{path.name}: no canaries")
    return canaries


def corpus_passages(root: Path, canaries: Sequence[Canary]) -> dict[str, Passage]:
    """The corpus passages the canaries name, by chunk id, from their documents chunked at the
    canary set's settings; CanaryError names an id no document holds."""
    wanted = sorted({i for c in canaries for i in c.corpus_ids()})
    found: dict[str, Passage] = {}
    for doc in sorted({i.split("@", 1)[0] for i in wanted}):
        try:
            chunks = pipeline.document_chunks(root, doc, SETTINGS)
        except pipeline.IngestError as error:
            raise CanaryError(f"the canaries name {doc}, which cannot be read: {error}") from error
        found |= {c.chunk_id: Passage.of(c) for c in chunks if c.chunk_id in wanted}
    if missing := [i for i in wanted if i not in found]:
        raise CanaryError(f"the canaries name chunks the corpus does not hold: {missing}")
    return found


def item(canary: Canary, passages: Mapping[str, Passage], seed: int) -> JudgeItem:
    """The judge call of one canary."""
    shown = None
    if canary.passages is not None:
        shown = tuple(passages[p] if isinstance(p, str) else p for p in canary.passages)
    return JudgeItem(
        canary.criterion, canary.question, shown, canary.reference, canary.answer, seed
    )


@dataclass(frozen=True)
class CanaryResult:
    canary: Canary
    verdict: Verdict

    @property
    def on_side(self) -> bool:
        """The verdict landed on the item's side: unable_to_verify, or a reply off the schema or
        none, is on neither side."""
        return self.verdict.status is Status.OK and self.verdict.verdict == self.canary.side


def run(
    judge: Judge, canaries: Sequence[Canary], passages: Mapping[str, Passage], seed: int
) -> list[CanaryResult]:
    """Every canary judged, in file order."""
    return [CanaryResult(c, judge.judge(item(c, passages, seed))) for c in canaries]


def off_side(results: Sequence[CanaryResult]) -> list[str]:
    """One line per canary that landed off its side, naming it."""
    return [
        f"canary {r.canary.id} ({r.canary.criterion}) must {r.canary.side}, but the judge gave "
        f"{r.verdict.verdict} (status {r.verdict.status.value}): {r.canary.purpose}"
        for r in results
        if not r.on_side
    ]


def require_on_side(results: Sequence[CanaryResult]) -> None:
    """The hard stop: CanaryStop naming every canary off its side."""
    if problems := off_side(results):
        raise CanaryStop(
            "the canaries stopped the judge before any judged call:\n- " + "\n- ".join(problems)
        )


def verdict_json(verdict: Verdict) -> Json:
    """A verdict as a judged record keeps it: what it rests on, the reply as it came, and what it
    cost. Never a passage's text: passages are named by id."""
    return {
        "verdict": verdict.verdict,
        "status": verdict.status.value,
        "answer_quote": verdict.answer_quote,
        "quote_found": verdict.quote_found,
        "passage_ids": list(verdict.passage_ids),
        "passages_given": verdict.passages_given,
        "shown_ids": list(verdict.shown_ids),
        "reason": verdict.reason,
        "reply": verdict.reply,
        "prompt_tokens": verdict.prompt_tokens,
        "completion_tokens": verdict.completion_tokens,
        "latency_ms": verdict.latency_ms,
        "error": verdict.error,
    }


def results_json(results: Sequence[CanaryResult]) -> list[Json]:
    """The canary results a judged manifest carries, in file order."""
    return [
        {
            "id": r.canary.id,
            "criterion": r.canary.criterion,
            "side": r.canary.side,
            "on_side": r.on_side,
            **verdict_json(r.verdict),
        }
        for r in results
    ]
