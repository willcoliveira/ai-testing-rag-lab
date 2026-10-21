"""The position test's lines in a generation record (S5; the run is raglab.evals.position): the code
checks of a trial, the results by position, and the checks of the lines against the record's
settings and the golden file, so `raglab.evals.record.validate` recomputes them.

A position line (kind `position`) has, besides the answer fields of every generation line: its
golden case (`golden_id`), its `position` (first, middle or last), `expected` (answer), the golden
case's `feature_ids`, its `answering_chunk` and the count of its `fillers`; its case id is
`<golden id>:<position>`. Its retrieved list is the context in order, the answering chunk the only
relevant one.

The checks: `status_ok`, `model_citations_retrieved`, `answered` (label answer on an ok answer),
`cites_answering` (the answer cites the answering chunk) and `states_value` (it states the
answering section's values as the answer key writes them, `value_stated`, R-11); a trial passes
when all pass.
"""

import hashlib
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

from raglab.core.text import normalise_space
from raglab.core.types import Status
from raglab.evals import golden, metrics
from raglab.evals.oracle import NUMBER, REFERENCE_WORDS
from raglab.ingest.answer_key import Feature

type Json = dict[str, object]

POSITION = "position"
POSITIONS = ("first", "middle", "last")
POSITION_FIELDS = ("golden_id", "position", "expected", "feature_ids", "answering_chunk", "fillers")


def section_of(chunk_id: str) -> tuple[str, str]:
    """(document, section) of a chunk id `<doc>@<version>/<section>/<n>`."""
    doc, _, rest = chunk_id.partition("@")
    parts = rest.split("/")
    return doc, parts[1] if len(parts) > 2 else ""


def answering_index(position: str, fillers: int) -> int:
    """Where the answering chunk sits among the n + 1 chunks of a context."""
    return {"first": 0, "middle": fillers // 2, "last": fillers}[position]


def number_units(value: str) -> list[str]:
    """Each number a value states, with the word after it when there is one ("30 seconds",
    "64 characters", "2 break-glass"); a number after a reference word is not a value."""
    found: list[str] = []
    for match in NUMBER.finditer(value):
        before = value[: match.start()].split()
        if before and before[-1].strip("(:,").lower() in REFERENCE_WORDS:
            continue
        after = value[match.end() :].split()
        unit = re.sub(r"[^\w-]", "", after[0]) if after else ""
        found.append(f"{match.group()} {unit}".strip())
    return found


def value_stated(value: str, answer: str) -> bool:
    """A value is stated when the answer holds it as the answer key writes it, whitespace runs
    and letter case aside; a value that holds numbers is also stated when the answer holds each of
    its numbers with the word after it (R-11: exact numbers and units)."""
    text = normalise_space(answer).casefold()
    if normalise_space(value).casefold() in text:
        return True
    pairs = number_units(value)
    return bool(pairs) and all(normalise_space(p).casefold() in text for p in pairs)


def values_of(case: Json, features: Mapping[str, Feature]) -> list[str]:
    """The values the answer key writes for the case's first feature at its answering section."""
    feature = features.get(str(cast(list[object], case["feature_ids"])[0]))
    place = section_of(str(case["answering_chunk"]))
    if feature is None:
        return []
    return [v for loc in feature.locations if (loc.doc, loc.section) == place for v in loc.values]


def checks(case: Json, features: Mapping[str, Feature]) -> Json:
    """The code checks of a position trial; it passes when every one passes."""
    ok = case["status"] == Status.OK.value
    retrieved = {str(cast(Json, r)["chunk_id"]) for r in cast(list[object], case["retrieved"])}
    cited = [str(i) for i in cast(list[object], case["cited_ids"])]
    events = [str(cast(Json, e)["guard"]) for e in cast(list[object], case["guard_events"])]
    values = values_of(case, features)
    found: Json = {
        "status_ok": ok,
        "model_citations_retrieved": "citations" not in events and set(cited) <= retrieved,
        "answered": ok and case["label"] == "answer",
        "cites_answering": case["answering_chunk"] in cited,
        "states_value": ok
        and bool(values)
        and all(value_stated(v, str(case["answer"])) for v in values),
    }
    found["passed"] = all(bool(v) for v in found.values())
    return found


def _passes(cases: Sequence[Json], where: str) -> dict[str, list[bool]]:
    """Each golden case's trial passes at one position, in case order."""
    found: dict[str, list[bool]] = {}
    for case in cases:
        if case.get("kind") == POSITION and case["position"] == where:
            passed = bool(cast(Json, case["checks"])["passed"])
            found.setdefault(str(case["golden_id"]), []).append(passed)
    return found


def results(cases: Sequence[Json], level: float, seed: int, resamples: int) -> Json:
    """Each position's pass rate with a Wilson interval at n = cases, and the paired differences
    middle minus first and middle minus last, per case (its pass rate over its trials), with a
    seeded bootstrap over cases."""
    found: Json = {}
    rates: dict[str, dict[str, float]] = {}
    for where in POSITIONS:
        by_case = _passes(cases, where)
        if not by_case:
            continue
        trials = [p for passes in by_case.values() for p in passes]
        found[f"position[{where}]"] = dict(
            metrics.wilson_interval(sum(trials) / len(trials), len(by_case), level).as_json()
        )
        rates[where] = {case_id: sum(p) / len(p) for case_id, p in by_case.items()}
    for other in ("first", "last"):
        if "middle" not in rates or other not in rates:
            continue
        ids = [i for i in rates["middle"] if i in rates[other]]
        if not ids:
            continue
        difference = metrics.paired_difference(
            [rates[other][i] for i in ids],
            [rates["middle"][i] for i in ids],
            seed,
            resamples,
            level,
        )
        found[f"position[middle-{other}]"] = dict(difference.as_json())
    return found


def report_lines(found: Json, cases: Sequence[Json]) -> list[str]:
    """The report's position section: one line per case and position, passes out of trials."""
    lines = [
        "",
        "## Position test (how-to 17 step 8, scored by code)",
        "",
        "The answering chunk first, in the middle or last of a long context of the asker's "
        "tenant's other chunks. A trial passes when its label is answer, it cites the answering "
        "chunk and it states the section's values as the answer key writes them. The differences "
        "are middle minus first and middle minus last, per case, with a seeded bootstrap over "
        "cases. Reported, not gated.",
        "",
        "| Case | Fillers | First | Middle | Last |",
        "|---|---|---|---|---|",
    ]
    by_case: dict[str, dict[str, list[bool]]] = {}
    fillers: dict[str, object] = {}
    for case in cases:
        if case.get("kind") != POSITION:
            continue
        golden_id = str(case["golden_id"])
        passed = bool(cast(Json, case["checks"])["passed"])
        by_case.setdefault(golden_id, {}).setdefault(str(case["position"]), []).append(passed)
        fillers[golden_id] = case["fillers"]
    for golden_id, positions in by_case.items():
        cells = [
            f"{sum(positions[w])} of {len(positions[w])}" if w in positions else "-"
            for w in POSITIONS
        ]
        lines.append(f"| {golden_id} | {fillers[golden_id]} | " + " | ".join(cells) + " |")
    if not found:
        lines.append("")
    return lines


def problems(manifest: Json, cases: Sequence[Json], root: Path) -> list[str]:
    """A position run's lines against its settings and, while the golden file is the one the
    record names, against the golden file: each line's case is one the manifest names; its
    answering chunk sits where its position says and is the only relevant chunk; every trial and
    position of a case has the same fillers, in the same order; the answering chunk is the case's
    labelled section's, and no filler belongs to a labelled section or group member of the
    case."""
    found: list[str] = []
    if "position" not in manifest:
        return ["a generation run with position cases needs its position block"]
    settings = cast(Json, manifest["position"])
    named = [str(i) for i in cast(list[object], settings["cases"])]
    questions: dict[str, golden.Question] = {}
    dataset = cast(Json, manifest["dataset"])
    path = root / str(dataset["path"])
    try:
        current = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        current = ""
    if current == dataset["sha256"]:
        questions = {q.case_id: q for q in golden.load(path)}
    seen: dict[str, list[str]] = {}
    for case in cases:
        where = f"case {case['case_id']} trial {case['trial']}"
        golden_id, position = str(case["golden_id"]), str(case["position"])
        if golden_id not in named or case["case_id"] != f"{golden_id}:{position}":
            found.append(f"{where}: not a position of a case the manifest names")
            continue
        rows = [cast(Json, r) for r in cast(list[object], case["retrieved"])]
        ids = [str(r["chunk_id"]) for r in rows]
        answering = str(case["answering_chunk"])
        if ids.count(answering) != 1:
            found.append(f"{where}: its context holds its answering chunk once")
            continue
        filler = [i for i in ids if i != answering]
        index = answering_index(position, len(filler))
        if ids.index(answering) != index or case["fillers"] != len(filler):
            found.append(f"{where}: its answering chunk is not where {position} puts it")
        if [bool(r["relevant"]) for r in rows] != [i == answering for i in ids]:
            found.append(f"{where}: only its answering chunk is relevant")
        if [r["rank"] for r in rows] != list(range(1, len(rows) + 1)):
            found.append(f"{where}: its context is ranked 1 to n")
        if seen.setdefault(golden_id, filler) != filler:
            found.append(f"{where}: its fillers are not its case's other positions' fillers")
        question = questions.get(golden_id)
        if question is None:
            continue
        labelled = {(s.doc_id, s.section_id) for s in question.sections()}
        primary = golden.members(question.labels[0])[0] if question.labels else None
        if primary is None or section_of(answering) != (primary.doc_id, primary.section_id):
            found.append(f"{where}: its answering chunk is not its labelled section's")
        if any(section_of(i) in labelled for i in filler):
            found.append(f"{where}: a filler belongs to a labelled section or group member")
        if case["feature_ids"] != question.extra.get("feature_ids"):
            found.append(f"{where}: its features are not the golden case's")
    return found
