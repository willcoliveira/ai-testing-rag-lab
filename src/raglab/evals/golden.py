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

**Label groups (S4, the decision S2 deferred).** A `relevant` entry may also be a group,
`{"any_of": [{"doc_id": ..., "section_id": ...}, ...]}`: sections that state the same rule (the
FAQ restatements of F-53, Device Policy 6.2 for the expiry rule of Policy Exceptions Process
4.2). The first member is the primary section. A group is one thing to find: it resolves to the
chunks of every member together (`Resolved.label_sets`), so hit@k and MRR take the first chunk of
any member and recall@k counts the group once, found when any member's chunk is in the top k.
Citing any member is a citation hit.

**Behaviour cases (S4).** A `kind: behaviour` line also has `mix` (the build project's kinds),
`expected` (the decision label of TEST-PLAN section 3), `feature_ids` (the first is the feature the
case is built on), `reference_answer` (null for abstain), `relevant` (empty for abstain),
optionally `may_quote` (abstain only: a shared reference section whose value the answer may quote,
attributed) and `origin`. The loader keeps them as extra fields and `behaviour` reads them; the
full contract is `raglab check-dataset`'s (raglab.evals.dataset_check), which every run passes
first.
"""

import json
from collections.abc import Collection, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

from raglab.core.types import LABELS, REQUEST_TENANTS, Chunk, ChunkId, visible_tenants

KINDS = frozenset({"retrieval", "behaviour"})
SPLITS = frozenset({"dev", "test"})
REQUIRED = ("id", "kind", "split", "tenant", "question")
# the build project's mix (Stage 4): five kinds, paraphrased and misspelled sharing one slot
MIX = (
    "single-chunk",
    "multi-chunk",
    "unanswerable",
    "version-conflict",
    "paraphrase",
    "misspelling",
)

type Json = dict[str, object]


class DatasetError(ValueError):
    """A line of the golden file is not a valid question."""


class LabelError(ValueError):
    """A label does not resolve to a chunk the asker may see."""


@dataclass(frozen=True)
class Label:
    doc_id: str
    section_id: str


@dataclass(frozen=True)
class Group:
    """Sections that state the same rule: one thing to find. members[0] is the primary section."""

    members: tuple[Label, ...]


type Entry = Label | Group


def members(entry: Entry) -> tuple[Label, ...]:
    """The sections of one relevant entry: a section alone, or every member of a group."""
    return entry.members if isinstance(entry, Group) else (entry,)


@dataclass(frozen=True)
class Question:
    case_id: str
    kind: str
    split: str
    tenant: str
    question: str
    labels: tuple[Entry, ...]
    extra: dict[str, object] = field(default_factory=dict[str, object])

    @property
    def question_kind(self) -> str | None:
        value = self.extra.get("question_kind")
        return value if isinstance(value, str) else None

    def sections(self) -> tuple[Label, ...]:
        """Every labelled section, the members of each group included, in order, each once (a
        section may sit in several groups)."""
        return tuple(dict.fromkeys(s for entry in self.labels for s in members(entry)))


@dataclass(frozen=True)
class Behaviour:
    """The fields of a behaviour case (kind behaviour)."""

    mix: str
    expected: str
    feature_ids: tuple[str, ...]
    reference_answer: str | None
    may_quote: Label | None


def _text(row: dict[str, object], name: str, where: str) -> str:
    value = row.get(name)
    if not isinstance(value, str) or not value.strip():
        raise DatasetError(f"{where}: {name} must be a non-empty string, got {value!r}")
    return value


def _section(item: object, where: str) -> Label:
    if not isinstance(item, dict):
        raise DatasetError(f"{where}: each relevant section is an object")
    entry = {str(k): v for k, v in cast(dict[object, object], item).items()}
    return Label(_text(entry, "doc_id", where), _text(entry, "section_id", where))


def _entry(item: object, where: str) -> Entry:
    if not isinstance(item, dict):
        raise DatasetError(f"{where}: each relevant section is an object")
    row = {str(k): v for k, v in cast(dict[object, object], item).items()}
    if "any_of" not in row:
        return _section(row, where)
    listed = row["any_of"]
    if set(row) != {"any_of"} or not isinstance(listed, list):
        raise DatasetError(f'{where}: a group is {{"any_of": [sections]}} and nothing else')
    sections = tuple(_section(m, where) for m in cast(list[object], listed))
    if len(sections) < 2:
        raise DatasetError(f"{where}: a group (any_of) lists at least two sections")
    return Group(sections)


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
    relevant = row.get("relevant", [])
    if not isinstance(relevant, list):
        raise DatasetError(f"{where}: relevant must be a list of sections")
    labels = tuple(_entry(item, where) for item in cast(list[object], relevant))
    if kind == "retrieval" and not labels:
        raise DatasetError(f"{where}: a retrieval question needs at least one relevant section")
    # A section is listed once as a label, and once in a group; it may sit in several groups (a
    # FAQ entry that restates two rules is a member of the group of each), never in a group and
    # as a label of its own, and no two groups are the same.
    plain = [e for e in labels if isinstance(e, Label)]
    groups = [e for e in labels if isinstance(e, Group)]
    in_groups = {s for g in groups for s in g.members}
    if (
        len(set(plain)) != len(plain)
        or any(len(set(g.members)) != len(g.members) for g in groups)
        or set(plain) & in_groups
        or len({frozenset(g.members) for g in groups}) != len(groups)
    ):
        raise DatasetError(f"{where}: a relevant section is listed twice")
    extra = {k: v for k, v in row.items() if k not in (*REQUIRED, "relevant")}
    return Question(case_id, kind, split, tenant, question, labels, extra)


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


def quote_section(question: Question) -> Label | None:
    """A behaviour case's may_quote section, if it names one."""
    value = question.extra.get("may_quote")
    if value is None:
        return None
    return _section(value, f"{question.case_id}: may_quote")


def behaviour(question: Question) -> Behaviour:
    """The behaviour fields of a case, or DatasetError naming the case and the field. Only their
    shape is read here; `raglab check-dataset` holds them to the answer key."""
    where = question.case_id
    if question.kind != "behaviour":
        raise DatasetError(f"{where}: kind {question.kind!r} is not behaviour")
    extra = question.extra
    mix, expected = extra.get("mix"), extra.get("expected")
    if mix not in MIX:
        raise DatasetError(f"{where}: mix {mix!r} is not one of {list(MIX)}")
    if expected not in LABELS:
        raise DatasetError(f"{where}: expected {expected!r} is not one of {list(LABELS)}")
    ids = extra.get("feature_ids")
    if (
        not isinstance(ids, list)
        or not ids
        or not all(isinstance(i, str) and i for i in cast(list[object], ids))
    ):
        raise DatasetError(f"{where}: feature_ids must list the case's features, the first first")
    reference = extra.get("reference_answer")
    if reference is not None and not isinstance(reference, str):
        raise DatasetError(f"{where}: reference_answer must be a string or null")
    return Behaviour(
        str(mix),
        str(expected),
        tuple(cast(list[str], ids)),
        reference,
        quote_section(question),
    )


@dataclass(frozen=True)
class Found:
    """One relevant entry resolved: each of its sections with that section's chunks."""

    entry: Entry
    sections: tuple[tuple[Label, tuple[ChunkId, ...]], ...]

    @property
    def chunk_ids(self) -> tuple[ChunkId, ...]:
        """The chunks of every section of the entry, in member order, each once."""
        return tuple(dict.fromkeys(i for _, ids in self.sections for i in ids))

    def as_json(self, retrieved: Collection[str]) -> Json:
        """The entry as a run record holds it: the primary section's ids, every chunk of the
        entry (a group's members together) and whether one was retrieved; a group also lists its
        members with their own chunks (`any_of`)."""
        primary = members(self.entry)[0]
        row: Json = {
            "doc_id": primary.doc_id,
            "section_id": primary.section_id,
            "chunk_ids": list(self.chunk_ids),
            "found": any(i in retrieved for i in self.chunk_ids),
        }
        if isinstance(self.entry, Group):
            row["any_of"] = [
                {"doc_id": s.doc_id, "section_id": s.section_id, "chunk_ids": list(ids)}
                for s, ids in self.sections
            ]
        return row


@dataclass(frozen=True)
class Resolved:
    question: Question
    entries: tuple[Found, ...]
    quote: tuple[ChunkId, ...] = ()  # the chunks of a behaviour case's may_quote section

    def label_sets(self) -> list[frozenset[str]]:
        """One chunk set per thing to find (raglab.evals.metrics): a section's chunks, or the
        chunks of every member of a group together, so a group is found, ranked and counted
        once, as a section is."""
        return [frozenset(found.chunk_ids) for found in self.entries]

    def labels_json(self, retrieved: Collection[str]) -> list[Json]:
        return [found.as_json(retrieved) for found in self.entries]


def resolve(questions: Sequence[Question], chunks: Sequence[Chunk]) -> list[Resolved]:
    """Each question with its labels (and a behaviour case's may_quote section) resolved to chunk
    ids; LabelError names every section that has no chunk or that the asker's tenant cannot see."""
    by_section: dict[tuple[str, str], list[Chunk]] = {}
    for chunk in chunks:
        by_section.setdefault((chunk.doc_id, chunk.section_id), []).append(chunk)
    problems: list[str] = []

    def chunks_of(question: Question, label: Label) -> tuple[ChunkId, ...]:
        found = by_section.get((label.doc_id, label.section_id), [])
        if not found:
            problems.append(
                f"{question.case_id}: {label.doc_id} section {label.section_id} has no chunk"
            )
        elif found[0].tenant not in visible_tenants(question.tenant):
            problems.append(
                f"{question.case_id}: {label.doc_id} is {found[0].tenant}, "
                f"which {question.tenant} cannot see"
            )
        return tuple(c.chunk_id for c in found)

    resolved: list[Resolved] = []
    for question in questions:
        entries = tuple(
            Found(entry, tuple((s, chunks_of(question, s)) for s in members(entry)))
            for entry in question.labels
        )
        quote = quote_section(question) if question.kind == "behaviour" else None
        quoted = chunks_of(question, quote) if quote is not None else ()
        resolved.append(Resolved(question, entries, quoted))
    if problems:
        raise LabelError("labels that do not resolve:\n" + "\n".join(problems))
    return resolved
