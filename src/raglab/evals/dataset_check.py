"""`raglab check-dataset` (S4): the golden file held to its contract before any run.

It reads the golden file, corpus/answer-key.yaml, corpus/register.yaml and
corpus/inventory.snapshot.json (no model and no embedder) and reports every problem, each naming
its case (or the file) and its rule. Rules 1, 2 and 8 hold for every line, rules 3 to 7 for the
behaviour cases, and rules 9 and 10 for the file:

1. **parse**: a line is not a question; an id repeats, or a question repeats for the same tenant
   (the same words asked as two tenants are two cases, as S3's P-01 and P-02 are); a kind, split,
   tenant, mix kind or label is outside its set.
2. **labels and features**: a labelled section, a group member or a may_quote section has no chunk
   in the inventory, or is in a document outside the register or of a tenant the asker may not
   see; a feature id is not in the answer key; a group member is not an answer-key location of
   the case's features.
3. **answer shape**: a case expected to answer, flag a conflict or refuse and help has no
   reference answer or no labelled section; a case not labelled flag-conflict labels a conflict
   side (a location with side old or external of a feature whose conflict is version or
   external): such a case is flag-conflict (TEST-PLAN section 3; SPEC section 11, check 12).
4. **abstain shape**: an abstain case with a reference answer or a labelled section; its first
   feature has no silence proof covering the asker's tenant (`must_not_appear`, scope corpus or
   that tenant); a may_quote section that is not a shared reference section, or on a case that
   does not abstain.
5. **conflict shape**: a flag-conflict case with no feature whose conflict is version or
   external, or whose labels lack that conflict's governing section or every conflict side; a
   group that mixes the two sides.
6. **refusal shapes**: a refuse-and-help case whose first feature is not a refuse-and-help
   feature, or with no labelled route section (a location of that feature); a must-not-block
   feature (F-54 to F-56) on a case not labelled answer.
7. **label**: the expected label differs from the clean-run label of the case's first feature.
8. **planted strings**: a question holds an `answer_must_not_contain` string or a canary of the
   other tenant (any letter case): a run record carries the questions, and publish refuses a
   record with such a string. The plan names rule 8 for the behaviour cases; it holds for the
   retrieval questions too, which runs carry the same way.
9. **mix**: the behaviour cases are not 15/8/8/4/5 (single-chunk, multi-chunk, unanswerable,
   version-conflict, paraphrased or misspelled); a mix kind or a label has no test case; an S3
   probe (P-01 to P-03) is missing or not in dev.
10. **version**: the datasheet's latest version line does not carry the file's sha256.

A section may sit in several groups of one question (a FAQ entry that restates two rules); the
loader refuses it twice as a label of its own, twice in one group, or as both (raglab.evals.golden).

`raglab eval` and `raglab gate` run this first and stop on any problem (`raglab.__main__`).
"""

import hashlib
import json
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from raglab.core.types import LABELS
from raglab.evals import golden
from raglab.ingest import answer_key, register

SNAPSHOT = "corpus/inventory.snapshot.json"
DATASHEET = "DATASHEET.md"  # next to the golden file
RULES = {
    1: "parse",
    2: "labels and features",
    3: "answer shape",
    4: "abstain shape",
    5: "conflict shape",
    6: "refusal shapes",
    7: "label",
    8: "planted strings",
    9: "mix",
    10: "version",
}
# the build project's mix, by slot: paraphrased and misspelled cases share one
MIX_SLOTS = {
    "single-chunk": 15,
    "multi-chunk": 8,
    "unanswerable": 8,
    "version-conflict": 4,
    "paraphrased or misspelled": 5,
}
S3_PROBES = ("P-01", "P-02", "P-03")
CONFLICTS = frozenset({"version", "external"})
GOVERNING_SIDES = frozenset({"new", "company"})
CONFLICT_SIDES = frozenset({"old", "external"})
# a version line of the datasheet: a list item or a table row that starts with a version
VERSION_LINE = re.compile(r"^\s*(?:[-*]\s+|\|\s*)(?:\*\*)?v(\d+(?:\.\d+)*)(?:\*\*)?(?![\w.])")


class CheckError(ValueError):
    """An input the check needs cannot be read: no check, so no run."""


@dataclass(frozen=True)
class Problem:
    case: str  # the case id, or the file's name for rules 9 and 10
    rule: int
    message: str

    def __str__(self) -> str:
        return f"{self.case}: rule {self.rule} ({RULES[self.rule]}): {self.message}"


@dataclass(frozen=True)
class Report:
    dataset: str
    sha256: str
    retrieval: int
    behaviour: int
    problems: tuple[Problem, ...]

    @property
    def passed(self) -> bool:
        return not self.problems

    def lines(self) -> list[str]:
        """What `raglab check-dataset` prints: every problem, then one verdict."""
        verdict = (
            f"check-dataset: {self.dataset} passes ({self.retrieval} retrieval questions, "
            f"{self.behaviour} behaviour cases, sha256 {self.sha256[:12]})"
            if self.passed
            else f"check-dataset: {self.dataset} fails {len(self.problems)} check(s)"
        )
        return [*(str(p) for p in self.problems), verdict]


def slot(mix: str) -> str:
    return "paraphrased or misspelled" if mix in ("paraphrase", "misspelling") else mix


@dataclass(frozen=True)
class Inputs:
    """What the rules read besides the golden file."""

    sections: frozenset[tuple[str, str]]  # every (document, section) with a chunk
    documents: dict[str, register.Entry]
    features: dict[str, answer_key.Feature]
    canaries: dict[str, list[str]]
    banned: dict[str, list[str]]  # answer_must_not_contain, by feature

    def conflict_sides(self) -> dict[tuple[str, str], list[str]]:
        """Each place that is a conflict side (old or external) of a version or external
        conflict, with the features it is that side of."""
        found: dict[tuple[str, str], list[str]] = {}
        for feature in self.features.values():
            if feature.conflict not in CONFLICTS:
                continue
            for location in feature.locations:
                if location.side in CONFLICT_SIDES:
                    found.setdefault((location.doc, location.section), []).append(feature.id)
        return found


def read_inputs(root: Path) -> Inputs:
    try:
        snapshot = json.loads((root / SNAPSHOT).read_text(encoding="utf-8"))
        rows = cast(list[dict[str, object]], snapshot["chunks"])
        sections = frozenset((str(r["doc"]), str(r["section"])) for r in rows)
        documents = {e.doc_id: e for e in register.read(root)}
        features = answer_key.features(root)
        canaries = answer_key.canaries(root)
        banned = answer_key.must_not_contain(root)
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise CheckError(f"check-dataset cannot read its inputs ({error})") from error
    return Inputs(sections, documents, features, canaries, banned)


def _case_of(text: str, where: str) -> str:
    """The id a line names, for a problem on a line that does not parse."""
    try:
        raw: object = json.loads(text)
    except json.JSONDecodeError:
        return where
    if isinstance(raw, dict):
        case = cast(dict[str, object], raw).get("id")
        if isinstance(case, str) and case.strip():
            return case
    return where


def _places(entry: golden.Entry) -> set[tuple[str, str]]:
    return {(s.doc_id, s.section_id) for s in golden.members(entry)}


class _Checker:
    def __init__(self, inputs: Inputs) -> None:
        self.inputs = inputs
        self.problems: list[Problem] = []
        self.conflict_sides = inputs.conflict_sides()

    def add(self, case: str, rule: int, message: str) -> None:
        self.problems.append(Problem(case, rule, message))

    # ------------------------------------------------------------ rule 2

    def section(self, q: golden.Question, label: golden.Label, what: str) -> None:
        entry = self.inputs.documents.get(label.doc_id)
        name = f"{what} {label.doc_id} {label.section_id}"
        if entry is None:
            self.add(q.case_id, 2, f"{name}: {label.doc_id} is not in the register")
        elif entry.tenant not in (q.tenant, "shared"):
            self.add(q.case_id, 2, f"{name} is {entry.tenant}, which {q.tenant} cannot see")
        if (label.doc_id, label.section_id) not in self.inputs.sections:
            self.add(q.case_id, 2, f"{name} has no chunk in the inventory")

    def labels_and_features(
        self, q: golden.Question, feature_ids: Sequence[str], quote: golden.Label | None
    ) -> None:
        for label in q.sections():
            self.section(q, label, "labelled section")
        if quote is not None:
            self.section(q, quote, "may_quote section")
        known = [self.inputs.features[i] for i in feature_ids if i in self.inputs.features]
        for missing in [i for i in feature_ids if i not in self.inputs.features]:
            self.add(q.case_id, 2, f"feature {missing} is not in the answer key")
        locations = {(loc.doc, loc.section) for f in known for loc in f.locations}
        for entry in q.labels:
            if not isinstance(entry, golden.Group):
                continue
            for member in entry.members:
                if (member.doc_id, member.section_id) not in locations:
                    self.add(
                        q.case_id,
                        2,
                        f"group member {member.doc_id} {member.section_id} is not an answer-key "
                        f"location of {', '.join(feature_ids)}",
                    )

    # ------------------------------------------------------------ rules 3 to 7

    def behaviour(self, q: golden.Question, b: golden.Behaviour) -> None:
        case = q.case_id
        known = [self.inputs.features[i] for i in b.feature_ids if i in self.inputs.features]
        first = self.inputs.features.get(b.feature_ids[0])
        if b.expected != "abstain":  # rule 3
            if not (b.reference_answer and b.reference_answer.strip()):
                self.add(case, 3, f"a case expected to {b.expected} needs a reference answer")
            if not q.labels:
                self.add(case, 3, f"a case expected to {b.expected} needs a labelled section")
            if b.expected != "flag-conflict":
                for place in sorted({p for entry in q.labels for p in _places(entry)}):
                    if place in self.conflict_sides:
                        self.add(
                            case,
                            3,
                            f"it labels {place[0]} {place[1]}, the superseded or external side "
                            f"of {', '.join(self.conflict_sides[place])}: such a case is "
                            "flag-conflict",
                        )
        else:  # rule 4
            if b.reference_answer is not None:
                self.add(case, 4, "an abstain case has no reference answer (null)")
            if q.labels:
                self.add(case, 4, "an abstain case labels no section")
            silence = first.silence if first else None
            if first and (
                silence is None or not silence.phrases or silence.scope not in ("corpus", q.tenant)
            ):
                self.add(
                    case,
                    4,
                    f"{first.id} has no silence proof covering {q.tenant} (must_not_appear with "
                    f"scope corpus or {q.tenant})",
                )
        if b.may_quote is not None:
            if b.expected != "abstain":
                self.add(case, 4, "may_quote is for abstain cases only")
            entry = self.inputs.documents.get(b.may_quote.doc_id)
            if entry is None or (entry.tenant, entry.status) != ("shared", "reference"):
                self.add(
                    case,
                    4,
                    f"may_quote {b.may_quote.doc_id} {b.may_quote.section_id} is not a shared "
                    "reference section",
                )
        if b.expected == "flag-conflict":  # rule 5
            self.conflict(q, known)
        if b.expected == "refuse-and-help" and first is not None:  # rule 6
            if first.kind != "refuse-and-help":
                self.add(case, 6, f"its first feature {first.id} is not a refuse-and-help feature")
            route = {(loc.doc, loc.section) for loc in first.locations}
            if not any(place in route for entry in q.labels for place in _places(entry)):
                self.add(case, 6, f"it labels no route section (a location of {first.id})")
        blocking = [f.id for f in known if f.kind == "must-not-block"]
        if blocking and b.expected != "answer":
            self.add(
                case,
                6,
                f"{', '.join(blocking)} must not be blocked: the case is labelled answer, "
                f"not {b.expected}",
            )
        if first is not None and b.expected != first.expected:  # rule 7
            self.add(
                case,
                7,
                f"expected {b.expected}, but the clean-run label of {first.id} is {first.expected}",
            )

    def conflict(self, q: golden.Question, known: Sequence[answer_key.Feature]) -> None:
        conflicted = [f for f in known if f.conflict in CONFLICTS]
        if not conflicted:
            self.add(q.case_id, 5, "a flag-conflict case needs a version or external conflict")
            return
        governing = {
            (loc.doc, loc.section)
            for f in conflicted
            for loc in f.locations
            if loc.side in GOVERNING_SIDES
        }
        sides = {
            (loc.doc, loc.section)
            for f in conflicted
            for loc in f.locations
            if loc.side in CONFLICT_SIDES
        }
        names = ", ".join(f.id for f in conflicted)
        if not any(_places(entry) & governing for entry in q.labels):
            self.add(q.case_id, 5, f"its labels lack the governing section of {names}")
        if not any(_places(entry) & sides for entry in q.labels):
            self.add(q.case_id, 5, f"its labels lack every conflict side of {names}")
        for entry in q.labels:
            if (
                isinstance(entry, golden.Group)
                and _places(entry) & governing
                and _places(entry) & sides
            ):
                self.add(q.case_id, 5, "a group mixes the governing side and a conflict side")

    # ------------------------------------------------------------ rule 8

    def planted(self, q: golden.Question) -> None:
        text = q.question.lower()
        for feature, strings in sorted(self.inputs.banned.items()):
            for s in strings:
                if s.lower() in text:
                    self.add(q.case_id, 8, f"the question holds {feature}'s {s!r}")
        other = "tenant-b" if q.tenant == "tenant-a" else "tenant-a"
        for canary in self.inputs.canaries.get(other, []):
            if canary.lower() in text:
                self.add(q.case_id, 8, f"the question holds a canary of {other}: {canary!r}")


def check(root: Path, dataset: Path) -> Report:
    """Every problem of the golden file at dataset, against the answer key, the register and the
    inventory snapshot under root."""
    inputs = read_inputs(root)
    try:
        data = dataset.read_bytes()
    except OSError as error:
        raise CheckError(f"check-dataset cannot read {dataset} ({error})") from error
    sha = hashlib.sha256(data).hexdigest()
    checker = _Checker(inputs)
    seen_ids: dict[str, int] = {}
    seen_questions: dict[tuple[str, str], str] = {}
    retrieval: list[golden.Question] = []
    behaviour: list[tuple[golden.Question, golden.Behaviour]] = []
    for number, text in enumerate(data.decode("utf-8").splitlines(), start=1):
        if not text.strip():
            continue
        where = f"{dataset.name}:{number}"
        try:
            q = golden.parse_line(text, where)
            b = golden.behaviour(q) if q.kind == "behaviour" else None
        except golden.DatasetError as error:
            checker.add(_case_of(text, where), 1, str(error))
            continue
        if q.case_id in seen_ids:
            checker.add(
                q.case_id, 1, f"the id is used twice (lines {seen_ids[q.case_id]}, {number})"
            )
            continue
        seen_ids[q.case_id] = number
        asked = (q.tenant, " ".join(q.question.lower().split()))
        if asked in seen_questions:
            checker.add(
                q.case_id, 1, f"it repeats the question of {seen_questions[asked]} for {q.tenant}"
            )
        seen_questions.setdefault(asked, q.case_id)
        listed = q.extra.get("feature_ids", [])
        feature_ids = (
            list(b.feature_ids)
            if b
            else [str(i) for i in cast(list[object], listed)]
            if isinstance(listed, list)
            else []
        )
        checker.labels_and_features(q, feature_ids, b.may_quote if b else None)
        checker.planted(q)
        if b is None:
            retrieval.append(q)
        else:
            checker.behaviour(q, b)
            behaviour.append((q, b))
    mix(checker, dataset.name, behaviour)
    version(checker, dataset, sha)
    try:
        shown = dataset.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        shown = str(dataset)
    return Report(
        dataset=shown,
        sha256=sha,
        retrieval=len(retrieval),
        behaviour=len(behaviour),
        problems=tuple(checker.problems),
    )


def mix(
    checker: _Checker, name: str, cases: Sequence[tuple[golden.Question, golden.Behaviour]]
) -> None:
    """Rule 9: the build project's mix, a test case for every mix kind and label, and the S3
    probes in dev."""
    counts = Counter(slot(b.mix) for _, b in cases)
    for kind, wanted in MIX_SLOTS.items():
        if counts[kind] != wanted:
            checker.add(name, 9, f"{counts[kind]} {kind} case(s), the mix asks for {wanted}")
    tested_kinds = {slot(b.mix) for q, b in cases if q.split == "test"}
    for kind in MIX_SLOTS:
        if kind not in tested_kinds:
            checker.add(name, 9, f"no {kind} case is in the test split")
    tested_labels = {b.expected for q, b in cases if q.split == "test"}
    for label in LABELS:
        if label not in tested_labels:
            checker.add(name, 9, f"no {label} case is in the test split")
    by_id = {q.case_id: q for q, _ in cases}
    for probe in S3_PROBES:
        if probe not in by_id:
            checker.add(name, 9, f"the S3 probe {probe} is not a behaviour case of the set")
        elif by_id[probe].split != "dev":
            checker.add(probe, 9, "an S3 probe stays in dev (S3 has run it)")


def latest_version(text: str) -> tuple[str, str] | None:
    """(version, line) of the datasheet's latest version line: the highest version a list item or
    table row starts with."""
    found: list[tuple[tuple[int, ...], str, str]] = []
    for line in text.splitlines():
        match = VERSION_LINE.match(line)
        if match:
            number = match.group(1)
            found.append((tuple(int(p) for p in number.split(".")), f"v{number}", line))
    if not found:
        return None
    _, label, line = max(found, key=lambda item: item[0])
    return label, line


def version(checker: _Checker, dataset: Path, sha: str) -> None:
    """Rule 10: the datasheet next to the golden file records this file's sha256 on its latest
    version line."""
    path = dataset.parent / DATASHEET
    if not path.is_file():
        checker.add(dataset.name, 10, f"no datasheet at {path.name} next to the golden file")
        return
    latest = latest_version(path.read_text(encoding="utf-8"))
    if latest is None:
        checker.add(dataset.name, 10, f"{path.name} has no version line ('| v1.1 | ...')")
    elif sha not in latest[1]:
        checker.add(
            dataset.name,
            10,
            f"the latest version line of {path.name} ({latest[0]}) does not carry the file's "
            f"sha256 {sha}",
        )
