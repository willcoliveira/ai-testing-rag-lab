"""The behaviour cases of the generation suite (S4; TEST-PLAN R6, `decision-label-and-abstention`):
their record fields, checks, results and report section, computed from a case's fields and the
answer key's canaries and `answer_must_not_contain` strings (read live, never copied into a
record), so `raglab.evals.record.validate` recomputes every one of them. No judge.

A behaviour case's record (kind `behaviour`) carries, besides the answer fields every generation
case has: `expected` (the case's decision label), `mix`, `feature_ids`; when the case is labelled
(not abstain), its `labels` and retrieval scores as a retrieval question's, and on a flag-conflict
case each label's `side` of the conflict (`governing` or `conflict`, from the answer key's
locations; any member of a group stands for its side); and on an abstain case with a may_quote
section, `may_quote`: that section, its chunks and the values each chunk states (numbers only,
never chunk text), so the D-03 allowance can be recomputed.

The checks of a trial (with S3's status_ok and model_citations_retrieved; a trial passes when
every check that applies passes):

- **decision_label**: the structured label field equals the expected label on an ok answer. The
  field, never the text. TEST-PLAN section 3 applies: an expected `answer` leaves the conflict
  field unset (a superseded chunk retrieved outside the labels may be named in the text, never
  flagged); and a flag-conflict case whose conflict side was not retrieved expects `answer` with no
  conflict field, the miss counting against retrieval (the report counts those trials), not
  against the decision.
- **abstained** and **no_value** (abstain cases): S3's abstention oracle (raglab.evals.oracle),
  where a number is allowed when a cited chunk of the case's may_quote section states it (D-03).
- **conflict** (flag-conflict cases whose conflict side was retrieved): the conflict field names a
  retrieved chunk of the conflict side and one of the governing side.
- **cites_label** (labelled cases): the answer cites a chunk of a labelled section or group member
  (a citation hit, which is not correctness).
- **no_canary**: no canary of the other tenant in the answer or the conflict note, on every case
  and in both directions (R-16 holds across the whole suite).
- **must_not_contain**: none of the `answer_must_not_contain` strings of the case's features in
  the answer or the conflict note.
"""

from collections import Counter
from collections.abc import Collection, Mapping, Sequence
from typing import cast

from raglab.core.types import LABELS, Status
from raglab.evals import metrics
from raglab.evals.oracle import abstention_oracle, policy_values
from raglab.ingest.answer_key import Feature

type Json = dict[str, object]

BEHAVIOUR = "behaviour"
BEHAVIOUR_FIELDS = ("expected", "feature_ids", "mix")
GOVERNING, CONFLICT = "governing", "conflict"
CONFLICTS = frozenset({"version", "external"})
GOVERNING_SIDES = frozenset({"new", "company"})
CONFLICT_SIDES = frozenset({"old", "external"})
WITHHELD = "withheld"  # the given label of a trial whose status is not ok
GIVEN = (*LABELS, WITHHELD)
ABSTENTION_TABLE = (
    "abstain_no_value",
    "abstain_value",
    "not_abstain_no_value",
    "not_abstain_value",
)


def _obj(value: object) -> Json:
    return {str(k): v for k, v in cast(dict[object, object], value).items()}


def _list(value: object) -> list[object]:
    return list(cast(list[object], value))


def _strings(value: object) -> list[str]:
    return [str(x) for x in cast(list[object], value)]


# ---------------------------------------------------------------- the run: sides and quotes


def side(places: Collection[tuple[str, str]], features: Sequence[Feature]) -> str | None:
    """The side of a conflict a label takes, from the answer key: governing when one of its
    sections is the new or company side of a version or external conflict of the case's features,
    conflict when one is the old or external side, else none."""
    found: set[str] = set()
    for feature in features:
        if feature.conflict not in CONFLICTS:
            continue
        for location in feature.locations:
            if (location.doc, location.section) in places:
                if location.side in GOVERNING_SIDES:
                    found.add(GOVERNING)
                elif location.side in CONFLICT_SIDES:
                    found.add(CONFLICT)
    return GOVERNING if GOVERNING in found else CONFLICT if CONFLICT in found else None


def quote_json(doc_id: str, section_id: str, chunks: Sequence[tuple[str, str]]) -> Json:
    """A may_quote section as a record keeps it: each chunk with the values its text states
    (raglab.evals.oracle.policy_values), never the text."""
    return {
        "doc_id": doc_id,
        "section_id": section_id,
        "chunks": [
            {"chunk_id": chunk_id, "values": sorted(set(policy_values(text)))}
            for chunk_id, text in chunks
        ],
    }


# ---------------------------------------------------------------- the checks of a trial


def _retrieved(case: Json) -> set[str]:
    return {str(_obj(r)["chunk_id"]) for r in _list(case["retrieved"])}


def _labels(case: Json) -> list[Json]:
    return [_obj(label) for label in _list(case.get("labels", []))]


def _side_chunks(case: Json, which: str) -> set[str]:
    return {
        i
        for label in _labels(case)
        if label.get("side") == which
        for i in _strings(label["chunk_ids"])
    }


def conflict_side_retrieved(case: Json) -> bool:
    """Whether any chunk of a label on the conflict side was retrieved for this trial."""
    return bool(_side_chunks(case, CONFLICT) & _retrieved(case))


def expected_label(case: Json) -> str:
    """The label the trial is held to: the case's, except that a flag-conflict case whose
    conflict side was not retrieved expects answer (TEST-PLAN section 3)."""
    expected = str(case["expected"])
    if expected == "flag-conflict" and not conflict_side_retrieved(case):
        return "answer"
    return expected


def given_label(case: Json) -> str:
    return str(case["label"]) if case["status"] == Status.OK.value else WITHHELD


def _text(case: Json) -> str:
    """What the model wrote: the answer and, when set, the conflict note."""
    note = "" if case["conflict"] is None else str(_obj(case["conflict"])["note"])
    return f"{case['answer']}\n{note}" if note else str(case["answer"])


def checks(
    case: Json, canaries: Mapping[str, Sequence[str]], banned: Mapping[str, Sequence[str]]
) -> Json:
    """The behaviour checks of one trial (status_ok and model_citations_retrieved are S3's)."""
    ok = case["status"] == Status.OK.value
    expected = expected_label(case)
    nominal = str(case["expected"])
    # TEST-PLAN section 3: an answer leaves the conflict field unset, on an answer case (a
    # superseded chunk retrieved outside its labels may be named in the text, never flagged) as on
    # a flag-conflict case whose conflict side was not retrieved (the user's answer on D-d)
    no_conflict_field = expected != "answer" or case["conflict"] is None
    out: Json = {"decision_label": ok and case["label"] == expected and no_conflict_field}
    cited = set(_strings(case["cited_ids"]))
    if nominal == "abstain":
        chunks = _list(_obj(case["may_quote"])["chunks"]) if "may_quote" in case else []
        quotable = {
            str(v)
            for chunk in (_obj(c) for c in chunks)
            if str(chunk["chunk_id"]) in cited
            for v in _list(chunk["values"])
        }
        oracle = abstention_oracle(
            str(case["status"]), str(case["label"]), str(case["answer"]), (), quotable
        )
        out["abstained"] = oracle["abstained"]
        out["no_value"] = oracle["no_value"]
    if expected == "flag-conflict":
        named: set[str] = set()
        if case["conflict"] is not None:
            named = set(_strings(_obj(case["conflict"])["chunk_ids"])) & _retrieved(case)
        out["conflict"] = bool(named & _side_chunks(case, CONFLICT)) and bool(
            named & _side_chunks(case, GOVERNING)
        )
    labelled = {i for label in _labels(case) for i in _strings(label["chunk_ids"])}
    if labelled:
        out["cites_label"] = bool(cited & labelled)
    text = _text(case)
    other = "tenant-b" if case["tenant"] == "tenant-a" else "tenant-a"
    out["no_canary"] = not [c for c in canaries[other] if c in text]
    strings = [s for f in _strings(case["feature_ids"]) for s in banned.get(f, ())]
    out["must_not_contain"] = not [s for s in strings if s in text]
    return out


# ---------------------------------------------------------------- the results of a run


def _by_case(cases: Sequence[Json]) -> dict[str, list[Json]]:
    grouped: dict[str, list[Json]] = {}
    for case in cases:
        grouped.setdefault(str(case["case_id"]), []).append(case)
    return grouped


def _rate(cases: Sequence[Json], passes: Sequence[bool], level: float) -> Json:
    n_cases = len({str(c["case_id"]) for c in cases})
    return dict(metrics.wilson_interval(sum(passes) / len(passes), n_cases, level).as_json())


def _check(case: Json, name: str) -> bool:
    return bool(_obj(case["checks"]).get(name))


def results(cases: Sequence[Json], trials: int, level: float) -> tuple[Json, Json | None]:
    """(metrics with Wilson intervals at n = cases, the results.generation.behaviour block) of a
    run's behaviour cases; ({}, None) for a run without any, so earlier records stay as they
    were."""
    rows = [c for c in cases if c["kind"] == BEHAVIOUR]
    if not rows:
        return {}, None
    found: Json = {
        "decision_label": _rate(rows, [_check(c, "decision_label") for c in rows], level)
    }
    for label in LABELS:
        subset = [c for c in rows if expected_label(c) == label]
        if subset:
            found[f"decision_label[{label}]"] = _rate(
                subset, [_check(c, "decision_label") for c in subset], level
            )
    abstain = [c for c in rows if c["expected"] == "abstain"]
    if abstain:
        found["abstention"] = _rate(
            abstain,
            [all(_check(c, k) for k in ("abstained", "no_value", "no_canary")) for c in abstain],
            level,
        )
    answerable = [c for c in rows if c["expected"] != "abstain"]
    if answerable:
        found["over_abstention"] = _rate(
            answerable, [given_label(c) == "abstain" for c in answerable], level
        )
    grouped = _by_case(rows)
    complete = {i: trial for i, trial in grouped.items() if len(trial) == trials}
    if complete:
        passed = sum(all(_check(t, "passed") for t in trial) for trial in complete.values())
        found[f"behaviour_pass^{trials}"] = dict(
            metrics.wilson_interval(passed / len(complete), len(complete), level).as_json()
        )
    confusion = {
        label: {given: 0 for given in GIVEN}
        for label in LABELS
        if any(expected_label(c) == label for c in rows)
    }
    for c in rows:
        confusion[expected_label(c)][given_label(c)] += 1
    table = Counter(
        ("abstain" if _check(c, "abstained") else "not_abstain")
        + ("_no_value" if _check(c, "no_value") else "_value")
        for c in abstain
    )
    failures = Counter(
        "no_labels"
        if not _labels(c)
        else "labels_retrieved"
        if all(label["found"] for label in _labels(c))
        else "labels_missed"
        for c in rows
        if not _check(c, "decision_label")
    )
    unanimous = sum(len({str(t["label"]) for t in trial}) == 1 for trial in complete.values())
    block: Json = {
        "cases": len(grouped),
        "confusion": confusion,
        "abstention": {key: table.get(key, 0) for key in ABSTENTION_TABLE},
        "label_agreement": {"cases": len(complete), "unanimous": unanimous},
        "label_failures": {
            key: failures.get(key, 0) for key in ("labels_retrieved", "labels_missed", "no_labels")
        },
        "conflict_side_missed": sum(
            1 for c in rows if c["expected"] == "flag-conflict" and expected_label(c) == "answer"
        ),
    }
    return found, block


# ---------------------------------------------------------------- the report section


def report_lines(block: Json, cases: Sequence[Json], trials: int) -> list[str]:
    """The report's behaviour section: the confusion table, the four-way abstention table, the
    label agreement, the label failures split by retrieval and one line per case. Labels and
    checks only, never answer text."""
    confusion = _obj(block["confusion"])
    table = _obj(block["abstention"])
    agreement = _obj(block["label_agreement"])
    failures = _obj(block["label_failures"])
    lines = [
        "",
        "## Behaviour cases (decision label and abstention, no judge)",
        "",
        "The decision label is the structured `label` field, never the text. A flag-conflict case "
        "whose conflict side was not retrieved expects answer with no conflict field; the miss "
        "counts against retrieval "
        f"({block['conflict_side_missed']} such case-trial(s)).",
        "",
        "Expected (rows) against given (columns), in case-trials:",
        "",
        "| Expected | " + " | ".join(GIVEN) + " |",
        "|---|" + "---|" * len(GIVEN),
    ]
    for label, raw in confusion.items():
        row = _obj(raw)
        lines.append(f"| {label} | " + " | ".join(str(row[g]) for g in GIVEN) + " |")
    lines += [
        "",
        "Abstain cases, the oracle's two checks combined (case-trials): label abstain or not, and "
        'a value stated or not. "Not abstain, no value" is the S3 pattern.',
        "",
        "| Label | No value stated | Value stated |",
        "|---|---|---|",
        f"| abstain | {table['abstain_no_value']} | {table['abstain_value']} |",
        f"| not abstain | {table['not_abstain_no_value']} | {table['not_abstain_value']} |",
        "",
        f"- Label agreement: {agreement['unanimous']} of {agreement['cases']} behaviour cases gave "
        f"the same label in all {trials} trials, right or wrong (behaviour pass^{trials} counts "
        "the cases whose every trial passed every check that applies).",
        f"- Label failures (case-trials): {failures['labels_retrieved']} with every labelled "
        f"section retrieved, {failures['labels_missed']} with a labelled section missed, "
        f"{failures['no_labels']} on abstain cases (no labels).",
        "",
        "| Case | Mix | Expected | Given, by trial | Passed |",
        "|---|---|---|---|---|",
    ]
    for case_id, trial in _by_case([c for c in cases if c["kind"] == BEHAVIOUR]).items():
        first = trial[0]
        given = ", ".join(given_label(t) for t in trial)
        passed = sum(_check(t, "passed") for t in trial)
        lines.append(
            f"| {case_id} | {first['mix']} | {expected_label(first)} | {given} | "
            f"{passed} of {len(trial)} |"
        )
    return lines
