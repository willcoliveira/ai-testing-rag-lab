"""`raglab check-dataset` (S4, per version since S4b): a golden file held to its contract before
any run.

It reads the golden file, corpus/answer-key.yaml, corpus/register.yaml and
corpus/inventory.snapshot.json (no model and no embedder) and reports every problem, each naming
its case (or the file) and its rule. Rules 1, 2 and 8 hold for every line, rules 3 to 7 for the
behaviour cases, and rules 9 and 10 for the file, each by the file's own version:

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
9. **mix**, by the file's version (`CONTRACTS`): the behaviour cases are not in the version's mix
   by slot (single-chunk, multi-chunk, unanswerable, version-conflict, paraphrased or
   misspelled), 15/8/8/4/5 for v1.1 and 45/24/24/12/15 for v2; a mix slot or a label has no test
   case; an S3 probe (P-01 to P-03) is missing or not in dev. v2 adds the S4b plan's floors: at
   least 55 answer, 24 abstain, 12 flag-conflict and 14 refuse-and-help cases, 8 must-not-block
   cases (a feature of kind must-not-block, as rule 6 reads it), 3 abstain cases with may_quote
   and 28 tenant B cases; a test case for each tenant; and a tenant B test case under every label
   tenant B has. A version with no contract here is a problem: a new version brings its rules.
10. **version**: the datasheet's latest version line for the file does not carry its sha256.

**The version a file is held to** is that of the latest row (the highest version) of the
datasheet's Maintenance table for the file's name: the table's File column names each row's file
(datasheet v2, S4b). The S4 datasheet's table has no File column; until it gains one, each of
its rows is the checked file's (the S4b ledger, developer choice 1).

A section may sit in several groups of one question (a FAQ entry that restates two rules); the
loader refuses it twice as a label of its own, twice in one group, or as both (raglab.evals.golden).

`raglab eval` and `raglab gate` run this first on their config's file and stop on any problem
(`raglab.__main__`); `raglab check-dataset` checks every golden file, `datasets/golden.v*.jsonl`.
"""

import hashlib
import json
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from raglab.core.types import LABELS, REQUEST_TENANTS
from raglab.evals import golden
from raglab.ingest import answer_key, register

SNAPSHOT = "corpus/inventory.snapshot.json"
DATASHEET = "DATASHEET.md"  # next to the golden file
MAINTENANCE = "## Maintenance"  # the datasheet's section whose first table lists the versions
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
S3_PROBES = ("P-01", "P-02", "P-03")
CONFLICTS = frozenset({"version", "external"})
GOVERNING_SIDES = frozenset({"new", "company"})
CONFLICT_SIDES = frozenset({"old", "external"})
MUST_NOT_BLOCK = "must-not-block"  # the feature kind rule 6 holds to answer (F-54 to F-56)
TENANT_B = "tenant-b"
# the first cell of a version row of the Maintenance table: a version, bold or not
VERSION_CELL = re.compile(r"^(?:\*\*)?v(\d+(?:\.\d+)*)(?:\*\*)?$")


@dataclass(frozen=True)
class Contract:
    """Rule 9 for one version of the golden set: the S4 plan's for v1.1, the S4b plan's for v2.
    Every version also has a test case for every mix slot and every label, and the S3 probes in
    dev."""

    mix: dict[str, int]  # behaviour cases per mix slot, exactly; paraphrase and misspelling share
    at_least: dict[str, int]  # behaviour cases per expected label, at least
    must_not_block: int  # cases with a feature of kind must-not-block, at least
    may_quote: int  # abstain cases with may_quote, at least
    tenant_b: int  # cases asked as tenant B, at least
    tenants_tested: bool  # a test case for each tenant, and a tenant B one under each of its labels


CONTRACTS: dict[str, Contract] = {
    "v1.1": Contract(
        mix={
            "single-chunk": 15,
            "multi-chunk": 8,
            "unanswerable": 8,
            "version-conflict": 4,
            "paraphrased or misspelled": 5,
        },
        at_least={},
        must_not_block=0,
        may_quote=0,
        tenant_b=0,
        tenants_tested=False,
    ),
    "v2": Contract(
        mix={
            "single-chunk": 45,
            "multi-chunk": 24,
            "unanswerable": 24,
            "version-conflict": 12,
            "paraphrased or misspelled": 15,
        },
        at_least={"answer": 55, "abstain": 24, "flag-conflict": 12, "refuse-and-help": 14},
        must_not_block=8,
        may_quote=3,
        tenant_b=28,
        tenants_tested=True,
    ),
}


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
    version: str | None = None  # the version the file was held to, from its Maintenance row

    @property
    def passed(self) -> bool:
        return not self.problems

    def lines(self) -> list[str]:
        """What `raglab check-dataset` prints: every problem, then one verdict."""
        verdict = (
            f"check-dataset: {self.dataset} passes as {self.version} ({self.retrieval} "
            f"retrieval questions, {self.behaviour} behaviour cases, sha256 {self.sha256[:12]})"
            if self.passed
            else f"check-dataset: {self.dataset} fails {len(self.problems)} check(s)"
        )
        return [*(str(p) for p in self.problems), verdict]


@dataclass(frozen=True)
class VersionRow:
    """A version row of the datasheet's Maintenance table."""

    version: str  # "v2"
    file: str | None  # its File cell; None in a table without a File column (the S4 datasheet)
    sha256: str  # its last cell, the backticks taken off

    @property
    def number(self) -> tuple[int, ...]:
        return tuple(int(part) for part in self.version[1:].split("."))


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def maintenance_rows(text: str) -> list[VersionRow]:
    """The version rows of the datasheet's Maintenance table: the first table of the section
    headed "## Maintenance", up to the next "## " heading. A row is a version row when its first
    cell is a version (`v1.1`, bold or not); its File cell, when the header has a File column,
    names its golden file, and its last cell holds the file's sha256 (backticked)."""
    marker = f"\n{MAINTENANCE}\n"
    if marker not in f"\n{text}":
        return []
    section = f"\n{text}".split(marker, 1)[1].split("\n## ", 1)[0]
    table: list[list[str]] = []
    for line in section.splitlines():
        if line.lstrip().startswith("|"):
            table.append(_cells(line))
        elif table:
            break  # the first table only
    if not table:
        return []
    header = [cell.lower() for cell in table[0]]
    file_at = header.index("file") if "file" in header else None
    rows: list[VersionRow] = []
    for cells in table[1:]:
        match = VERSION_CELL.match(cells[0])
        if match is None:
            continue
        file = None
        if file_at is not None:
            file = cells[file_at].strip("`").strip() if file_at < len(cells) else ""
        rows.append(VersionRow(f"v{match.group(1)}", file, cells[-1].strip("`").strip()))
    return rows


def latest_row(dataset: Path) -> VersionRow | str:
    """The latest (highest) version row of the Maintenance table of the datasheet next to the
    golden file that is that file's, or the reason there is none (a rule 10 problem)."""
    path = dataset.parent / DATASHEET
    if not path.is_file():
        return f"no datasheet at {path.name} next to the golden file"
    rows = maintenance_rows(path.read_text(encoding="utf-8"))
    if not rows:
        return (
            f"{path.name} has no version line in its Maintenance table "
            f"('| v2 | <date> | <stage> | `{dataset.name}` | <what changed> | `<sha256>` |')"
        )
    mine = [row for row in rows if row.file in (None, dataset.name)]
    if not mine:
        return f"no version line of {path.name}'s Maintenance table names {dataset.name}"
    return max(mine, key=lambda row: row.number)


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
    row = latest_row(dataset)
    version = row.version if isinstance(row, VersionRow) else None
    if version is not None:
        mix(checker, dataset.name, behaviour, version)
    if isinstance(row, str):  # rule 10, after rule 9 as before
        checker.add(dataset.name, 10, f"{row}, so the file has no version and rule 9 no contract")
    elif row.sha256 != sha:
        checker.add(
            dataset.name,
            10,
            f"the latest version line of {DATASHEET} for {dataset.name} ({row.version}) does not "
            f"carry the file's sha256 {sha}",
        )
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
        version=version,
    )


def mix(
    checker: _Checker,
    name: str,
    cases: Sequence[tuple[golden.Question, golden.Behaviour]],
    version: str,
) -> None:
    """Rule 9, by the file's version (CONTRACTS): its mix by slot and floors, a test case for
    every mix slot and label (and, from v2, each tenant and each label tenant B has), and the S3
    probes in dev."""
    contract = CONTRACTS.get(version)
    if contract is None:
        known = ", ".join(CONTRACTS)
        checker.add(name, 9, f"{version} has no contract in check-dataset (it knows {known})")
        return
    counts = Counter(slot(b.mix) for _, b in cases)
    for kind, wanted in contract.mix.items():
        if counts[kind] != wanted:
            checker.add(name, 9, f"{counts[kind]} {kind} case(s), the mix asks for {wanted}")
    labels = Counter(b.expected for _, b in cases)
    features = checker.inputs.features
    floors = [
        *((f"{label} case(s)", labels[label], n) for label, n in contract.at_least.items()),
        (
            "must-not-block case(s)",
            sum(
                any(f in features and features[f].kind == MUST_NOT_BLOCK for f in b.feature_ids)
                for _, b in cases
            ),
            contract.must_not_block,
        ),
        (
            "abstain case(s) with may_quote",
            sum(b.expected == "abstain" and b.may_quote is not None for _, b in cases),
            contract.may_quote,
        ),
        (f"{TENANT_B} case(s)", sum(q.tenant == TENANT_B for q, _ in cases), contract.tenant_b),
    ]
    for what, found, least in floors:
        if found < least:
            checker.add(name, 9, f"{found} {what}, {version} asks for at least {least}")
    tested = [(q, b) for q, b in cases if q.split == "test"]
    tested_kinds = {slot(b.mix) for _, b in tested}
    for kind in contract.mix:
        if kind not in tested_kinds:
            checker.add(name, 9, f"no {kind} case is in the test split")
    tested_labels = {b.expected for _, b in tested}
    for label in LABELS:
        if label not in tested_labels:
            checker.add(name, 9, f"no {label} case is in the test split")
    if contract.tenants_tested:
        for tenant in sorted(REQUEST_TENANTS - {q.tenant for q, _ in tested}):
            checker.add(name, 9, f"no {tenant} case is in the test split")
        own = {b.expected for q, b in cases if q.tenant == TENANT_B}
        own_tested = {b.expected for q, b in tested if q.tenant == TENANT_B}
        for label in LABELS:
            if label in own and label not in own_tested:
                checker.add(name, 9, f"no {TENANT_B} {label} case is in the test split")
    by_id = {q.case_id: q for q, _ in cases}
    for probe in S3_PROBES:
        if probe not in by_id:
            checker.add(name, 9, f"the S3 probe {probe} is not a behaviour case of the set")
        elif by_id[probe].split != "dev":
            checker.add(probe, 9, "an S3 probe stays in dev (S3 has run it)")
