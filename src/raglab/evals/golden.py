"""The golden questions (datasets/golden.v1.jsonl) and their labels resolved to chunk ids.

One JSON object per line. Every line has an `id` (unique), a `kind` (retrieval or behaviour), a
`split` (dev or test), the asker's `tenant` (tenant-a or tenant-b) and the `question`. A retrieval
question has `relevant`: the sections that answer it, each `{"doc_id": ..., "section_id": ...}`.
Other fields (question_kind, feature_ids, notes) are kept as they are.

Labels name sections, not chunks: `resolve` maps each to the chunks that section has at the run's
chunk settings, so a re-chunk updates them mechanically, and a label whose section has no chunk,
or whose document the asker's tenant cannot see, stops the run (LabelError). A label resolves to
every chunk of its section, and the section counts as found when any one of them is retrieved
(raglab.evals.metrics): a section split into several chunks is still one thing to find, even when
the sentence a question needs is in only one of them (datasets/DATASHEET.md, known limits).
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

from raglab.core.types import REQUEST_TENANTS, Chunk, ChunkId, visible_tenants

KINDS = frozenset({"retrieval", "behaviour"})
SPLITS = frozenset({"dev", "test"})
REQUIRED = ("id", "kind", "split", "tenant", "question")


class DatasetError(ValueError):
    """A line of the golden file is not a valid question."""


class LabelError(ValueError):
    """A label does not resolve to a chunk the asker may see."""


@dataclass(frozen=True)
class Label:
    doc_id: str
    section_id: str


@dataclass(frozen=True)
class Question:
    case_id: str
    kind: str
    split: str
    tenant: str
    question: str
    labels: tuple[Label, ...]
    extra: dict[str, object] = field(default_factory=dict[str, object])

    @property
    def question_kind(self) -> str | None:
        value = self.extra.get("question_kind")
        return value if isinstance(value, str) else None


@dataclass(frozen=True)
class Resolved:
    question: Question
    groups: tuple[tuple[Label, tuple[ChunkId, ...]], ...]  # each label and its chunks

    def label_sets(self) -> list[frozenset[str]]:
        return [frozenset(ids) for _, ids in self.groups]


def _text(row: dict[str, object], name: str, where: str) -> str:
    value = row.get(name)
    if not isinstance(value, str) or not value.strip():
        raise DatasetError(f"{where}: {name} must be a non-empty string, got {value!r}")
    return value


def parse_line(line: str, where: str) -> Question:
    try:
        raw: object = json.loads(line)
    except json.JSONDecodeError as error:
        raise DatasetError(f"{where}: not JSON ({error.msg})") from error
    if not isinstance(raw, dict):
        raise DatasetError(f"{where}: a question is a JSON object")
    row = {str(k): v for k, v in cast(dict[object, object], raw).items()}
    case_id = _text(row, "id", where)
    where = f"{where} ({case_id})"  # every later error names the question as well as the line
    kind, split, tenant, question = (_text(row, f, where) for f in REQUIRED[1:])
    if kind not in KINDS:
        raise DatasetError(f"{where}: kind {kind!r} is not one of {sorted(KINDS)}")
    if split not in SPLITS:
        raise DatasetError(f"{where}: split {split!r} is not one of {sorted(SPLITS)}")
    if tenant not in REQUEST_TENANTS:
        raise DatasetError(f"{where}: tenant {tenant!r} is not one of {sorted(REQUEST_TENANTS)}")
    labels: list[Label] = []
    relevant = row.get("relevant", [])
    if not isinstance(relevant, list):
        raise DatasetError(f"{where}: relevant must be a list of sections")
    for item in cast(list[object], relevant):
        if not isinstance(item, dict):
            raise DatasetError(f"{where}: each relevant section is an object")
        entry = {str(k): v for k, v in cast(dict[object, object], item).items()}
        labels.append(Label(_text(entry, "doc_id", where), _text(entry, "section_id", where)))
    if kind == "retrieval" and not labels:
        raise DatasetError(f"{where}: a retrieval question needs at least one relevant section")
    if len(set(labels)) != len(labels):
        raise DatasetError(f"{where}: a relevant section is listed twice")
    extra = {k: v for k, v in row.items() if k not in (*REQUIRED, "relevant")}
    return Question(case_id, kind, split, tenant, question, tuple(labels), extra)


def load(path: Path) -> list[Question]:
    """Every question of the golden file, in file order."""
    questions: list[Question] = []
    seen: set[str] = set()
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        question = parse_line(line, f"{path.name}:{number}")
        if question.case_id in seen:
            raise DatasetError(f"{path.name}:{number}: id {question.case_id} is used twice")
        seen.add(question.case_id)
        questions.append(question)
    if not questions:
        raise DatasetError(f"{path.name}: no questions")
    return questions


def select(questions: Sequence[Question], kind: str, split: str) -> list[Question]:
    """The questions of one kind in one split ("all" for both splits)."""
    return [q for q in questions if q.kind == kind and split in (q.split, "all")]


def resolve(questions: Sequence[Question], chunks: Sequence[Chunk]) -> list[Resolved]:
    """Each question with its labels resolved to chunk ids; LabelError names every label that
    has no chunk or that the asker's tenant cannot see."""
    by_section: dict[tuple[str, str], list[Chunk]] = {}
    for chunk in chunks:
        by_section.setdefault((chunk.doc_id, chunk.section_id), []).append(chunk)
    problems: list[str] = []
    resolved: list[Resolved] = []
    for question in questions:
        visible = visible_tenants(question.tenant)
        groups: list[tuple[Label, tuple[ChunkId, ...]]] = []
        for label in question.labels:
            found = by_section.get((label.doc_id, label.section_id), [])
            if not found:
                problems.append(
                    f"{question.case_id}: {label.doc_id} section {label.section_id} has no chunk"
                )
            elif found[0].tenant not in visible:
                problems.append(
                    f"{question.case_id}: {label.doc_id} is {found[0].tenant}, "
                    f"which {question.tenant} cannot see"
                )
            groups.append((label, tuple(c.chunk_id for c in found)))
        resolved.append(Resolved(question, tuple(groups)))
    if problems:
        raise LabelError("labels that do not resolve:\n" + "\n".join(problems))
    return resolved
