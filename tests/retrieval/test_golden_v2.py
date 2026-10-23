"""S4b GV1 to GV3: golden set v2 (datasets/golden.v2.jsonl) beside golden set v1.1
(datasets/golden.v1.jsonl, frozen).

- **GV1:** v2 holds v1.1's 74 lines byte for byte, then 80 new behaviour cases from G-38 (ids in
  order, none reused), all `origin: synthetic`: 120 behaviour cases in the mix 45/24/24/12/15
  and the 34 retrieval questions; no question asked twice by one tenant; S2's measure computed
  for the new cases (the longest run of words shared with a document, a retrieval question and
  another case), which the datasheet reports with no threshold.
- **GV2:** coverage, derived from the file and the answer key: every requirement with a planted
  feature has a behaviour case by its features; the gaps (R-02 every case, R-20 and R-21 by
  design, R-22 by the maintainer's D3 answer) are named by no feature; every feature kind but
  secret-in-doc, pii-in-doc and near-duplicate starts a case; a kind with two or more cases has a
  dev case; the label floors, must-not-block and tenant B.
- **GV3:** golden.v1.jsonl is byte for byte the file signed off in S4, and every published record
  of v1.1 names a file that still holds its bytes, so its labels, behaviour fields and reference
  answers are derived again in full (`raglab.evals.record.current_golden`).

The file is read here, line by line, never through raglab's loader: a second reading of the file
the maintainer signs off. Each check is a function of the lines, held now on the planted v2
(tests/dataset_support.py) and on the committed file once the cases are integrated.
"""

import hashlib
import json
from collections import Counter
from collections.abc import Sequence
from typing import Any

import pytest
import yaml

from raglab.evals import publish, record
from tests.conftest import ROOT
from tests.dataset_support import edited_lines, v2_lines
from tests.golden_support import (
    DATASHEET,
    V1,
    V2,
    behaviour,
    corpus,
    golden_lines,
    longest_run,
    maintenance,
    rows_of,
    slot,
    texts,
    words,
)

pytestmark = pytest.mark.retrieval
# the S4b plan's mix by slot (paraphrase and misspelling share one) and its floors (rule 9)
MIX = {
    "single-chunk": 45,
    "multi-chunk": 24,
    "unanswerable": 24,
    "version-conflict": 12,
    "paraphrased or misspelled": 15,
}
FLOORS = {"answer": 55, "abstain": 24, "flag-conflict": 12, "refuse-and-help": 14}
NEW = 80  # G-38 to G-117
# the signed-off golden set v1.1 (S4 ledger, "The sign-off on golden set v1.1"), never changed
V1_1_SHA256 = "5f8cdaf1878336710335adca98d5691b2ba6e0432698510642c9c7b3dc62e59a"
# feature kinds that start no case by design (the S4b plan, "Every question type"): the planted
# secret and personal details go to S7 with the output guard, and F-53 counts through groups
NO_CASE_KINDS = frozenset({"secret-in-doc", "pii-in-doc", "near-duplicate"})
needs_v2 = pytest.mark.skipif(not V2.exists(), reason="golden.v2.jsonl lands at the integration")


def v1_lines() -> list[str]:
    return V1.read_text(encoding="utf-8").splitlines()


@pytest.fixture(scope="module")
def planted() -> list[str]:
    return v2_lines()


# ---------------------------------------------------------------- GV1: the file


def frozen_problems(lines: Sequence[str]) -> list[str]:
    """Each v1.1 line that v2 does not hold byte for byte, in its place, naming the case and the
    fields that differ."""
    old = v1_lines()
    problems: list[str] = []
    for number, (mine, theirs) in enumerate(zip(old, lines, strict=False), start=1):
        if mine != theirs:
            a, b = json.loads(mine), json.loads(theirs)
            fields = sorted(k for k in {*a, *b} if a.get(k) != b.get(k)) or ["the bytes"]
            problems.append(f"line {number} ({a['id']}): {', '.join(fields)} differ from v1.1's")
    if len(lines) < len(old):
        problems.append(f"v2 has {len(lines)} lines, fewer than v1.1's {len(old)}")
    return problems


def new_case_problems(lines: Sequence[str]) -> list[str]:
    """The lines after v1.1's: behaviour cases only, ids G-38 on in order and never reused,
    origin synthetic; then the whole file's counts and mix, and no question asked twice by one
    tenant."""
    rows = rows_of(lines)
    old_ids = {row["id"] for row in rows_of(v1_lines())}
    new = rows[len(old_ids) :]
    problems: list[str] = []
    wanted = [f"G-{n}" for n in range(38, 38 + NEW)]
    if [row["id"] for row in new] != wanted:
        problems.append(f"the new cases are not G-38 to G-117 in order: {[r['id'] for r in new]}")
    problems += [f"{r['id']} reuses an id of v1.1" for r in new if r["id"] in old_ids]
    problems += [f"{r['id']} is not a behaviour case" for r in new if r["kind"] != "behaviour"]
    problems += [f"{r['id']} is not synthetic" for r in new if r.get("origin") != "synthetic"]
    cases = behaviour(rows)
    retrieval = [row for row in rows if row["kind"] == "retrieval"]
    if (len(retrieval), len(cases)) != (34, 120):
        problems.append(f"{len(retrieval)} retrieval questions and {len(cases)} behaviour cases")
    found = Counter(slot(case["mix"]) for case in cases)
    problems += [
        f"{kind}: {found[kind]} case(s), the mix asks for {n}"
        for kind, n in MIX.items()
        if found[kind] != n
    ]
    asked: dict[tuple[str, str], str] = {}
    for row in rows:
        key = (row["tenant"], " ".join(words(row["question"])))
        if key in asked:
            problems.append(f"{row['id']} asks {asked[key]}'s question as {row['tenant']}")
        asked.setdefault(key, row["id"])
    return problems


def test_the_planted_v2_passes_and_each_break_is_named(planted):
    assert frozen_problems(planted) == []
    assert new_case_problems(planted) == []
    # GV1's break: one v1.1 line edited inside v2 (its split flipped) is named with the field
    number = 1 + next(n for n, line in enumerate(planted) if json.loads(line)["id"] == "G-04")
    split = json.loads(planted[number - 1])["split"]
    flipped = edited_lines(planted, "G-04", split="dev" if split == "test" else "test")
    assert frozen_problems(flipped) == [f"line {number} (G-04): split differ from v1.1's"]
    # a new case given an existing id (rule 1 of check-dataset names it too), or not a case
    reused = edited_lines(planted, "G-117", id="G-26")
    assert "G-26 reuses an id of v1.1" in new_case_problems(reused)
    retrieval = edited_lines(planted, "G-117", kind="retrieval")
    assert "G-117 is not a behaviour case" in new_case_problems(retrieval)
    moved = edited_lines(planted, "G-38", mix="multi-chunk")
    assert new_case_problems(moved) == [
        "single-chunk: 44 case(s), the mix asks for 45",
        "multi-chunk: 25 case(s), the mix asks for 24",
    ]
    repeated = edited_lines(planted, "G-39", question=json.loads(planted[74])["question"])
    assert new_case_problems(repeated) == ["G-39 asks G-38's question as tenant-a"]


@needs_v2
def test_v2_holds_v1_1_byte_for_byte_then_80_new_cases():
    lines = V2.read_text(encoding="utf-8").splitlines()
    assert frozen_problems(lines) == []
    assert new_case_problems(lines) == []


def overlap(lines: Sequence[str]) -> dict[str, int]:
    """S2's measure for the new cases (no threshold): the longest run of words a new question
    shares with a document, with a retrieval question, and with another behaviour case."""
    rows = rows_of(lines)
    new = rows[len(v1_lines()) :]
    asked = texts(words(r["question"]) for r in rows if r["kind"] == "retrieval")
    cases = behaviour(rows)
    return {
        "document": max(longest_run(words(r["question"]), corpus()) for r in new),
        "retrieval question": max(longest_run(words(r["question"]), asked) for r in new),
        "another case": max(
            longest_run(
                words(r["question"]),
                texts(words(c["question"]) for c in cases if c["id"] != r["id"]),
            )
            for r in new
        ),
    }


def test_the_overlap_measure_on_the_planted_cases(planted):
    """The planted questions read 'Fixture case G-nn: a question on F-nn?': two on one feature
    share "a question on f nn", five words, and they share fewer with anything else. The measure
    is reported, never bounded."""
    found = overlap(planted)
    assert found["another case"] == 5
    assert found["document"] < found["another case"]
    assert found["retrieval question"] < found["another case"]


# ---------------------------------------------------------------- GV2: coverage


def answer_key() -> dict[str, Any]:
    return yaml.safe_load((ROOT / "corpus" / "answer-key.yaml").read_text(encoding="utf-8"))


def coverage_problems(rows: Sequence[dict[str, Any]], key: dict[str, Any]) -> list[str]:
    """GV2, derived from the lines and the answer key."""
    features = {f["id"]: f for f in key["features"]}
    gaps = {g["requirement"] for g in key["gaps"]}
    cases = behaviour(rows)
    problems: list[str] = []
    planted = {rid for f in features.values() for rid in f["requirements"]}
    covered = {
        rid for c in cases for fid in c["feature_ids"] for rid in features[fid]["requirements"]
    }
    problems += [f"no behaviour case covers {rid}" for rid in sorted(planted - gaps - covered)]
    problems += [f"{rid} is a gap but a feature names it" for rid in sorted(gaps & planted)]
    if not {"R-02", "R-20", "R-21", "R-22"} <= gaps:
        problems.append(f"the gaps are {sorted(gaps)}, not R-02, R-20, R-21 and R-22")
    by_kind: dict[str, list[dict[str, Any]]] = {}
    for case in cases:
        by_kind.setdefault(features[case["feature_ids"][0]]["kind"], []).append(case)
    for kind in sorted({f["kind"] for f in features.values()} - NO_CASE_KINDS):
        started = by_kind.get(kind, [])
        if not started:
            problems.append(f"no case starts with a feature of kind {kind}")
        elif len(started) >= 2 and not any(c["split"] == "dev" for c in started):
            ids = ", ".join(c["id"] for c in started)
            problems.append(f"the {kind} kind's cases ({ids}) are all in test")
    labels = Counter(c["expected"] for c in cases)
    problems += [
        f"{labels[label]} {label} case(s), at least {n}"
        for label, n in FLOORS.items()
        if labels[label] < n
    ]
    blocking = [
        c for c in cases if any(features[f]["kind"] == "must-not-block" for f in c["feature_ids"])
    ]
    if len(blocking) < 8:
        problems.append(f"{len(blocking)} must-not-block case(s), at least 8")
    tenant_b = [c for c in cases if c["tenant"] == "tenant-b"]
    if len(tenant_b) < 28:
        problems.append(f"{len(tenant_b)} tenant B case(s), at least 28")
    return problems


def test_the_planted_v2_covers_every_requirement_and_kind(planted):
    assert coverage_problems(rows_of(planted), answer_key()) == []


def test_coverage_names_a_requirement_left_without_a_case(planted):
    """GV2's break: the case carrying F-18 (R-08's only one here) re-pointed to F-20."""
    rows = rows_of(planted)
    [g] = [r for r in behaviour(rows) if r["feature_ids"] == ["F-18"]]
    moved = [{**r, "feature_ids": ["F-20"]} if r is g else r for r in rows]
    found = coverage_problems(moved, answer_key())
    assert "no behaviour case covers R-08" in found
    assert "no case starts with a feature of kind cross-reference" in found


def test_coverage_names_a_kind_whose_cases_are_all_in_test(planted):
    """GV2's break, R-23 included: v1.1's only procedure case (G-20) is in test; a second F-57
    case in dev covers the kind, and moved to test, the procedure kind is named."""
    rows = rows_of(planted)
    [g20] = [r for r in rows if r["id"] == "G-20"]
    assert (g20["feature_ids"][0], g20["split"]) == ("F-57", "test")
    second = {**g20, "id": "G-81", "split": "dev"}
    rows = [second if r["id"] == "G-81" else r for r in rows]
    assert coverage_problems(rows, answer_key()) == []
    rows = [{**r, "split": "test"} if r["id"] == "G-81" else r for r in rows]
    assert coverage_problems(rows, answer_key()) == [
        "the procedure kind's cases (G-20, G-81) are all in test"
    ]


def test_r22_stays_a_gap_and_no_feature_names_r20_or_r21():
    """The maintainer's D3 answer, "No corpus change; R-22 stays a gap (Recommended)"."""
    key = answer_key()
    gaps = {g["requirement"]: g for g in key["gaps"]}
    named = {rid for f in key["features"] for rid in f["requirements"]}
    assert {"R-02", "R-20", "R-21", "R-22"} <= set(gaps)
    assert not named & {"R-02", "R-20", "R-21", "R-22"}


@needs_v2
def test_v2_covers_every_requirement_and_every_question_type():
    assert coverage_problems(golden_lines(V2), answer_key()) == []


# ---------------------------------------------------------------- GV3: v1.1 frozen


def v1_1_manifests() -> list[dict[str, Any]]:
    """Every published manifest that names golden set v1.1's sha256, as the Maintenance table
    lists it for golden.v1.jsonl."""
    rows = maintenance(DATASHEET.read_text(encoding="utf-8"))
    [v1_1] = [r.sha256 for r in rows if r.version == "v1.1" and r.file in (None, V1.name)]
    found: list[dict[str, Any]] = []
    for path in sorted((ROOT / publish.PUBLISHED).glob(f"*/{record.MANIFEST}")):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if manifest["dataset"]["sha256"] == v1_1:
            found.append({**manifest, "run": path.parent.name})
    return found


def test_golden_set_v1_1_is_the_file_signed_off_in_s4():
    assert hashlib.sha256(V1.read_bytes()).hexdigest() == V1_1_SHA256
    rows = maintenance(DATASHEET.read_text(encoding="utf-8"))
    assert [r.sha256 for r in rows if r.version == "v1.1"] == [V1_1_SHA256]


def test_every_v1_1_record_names_a_file_that_still_holds_its_bytes():
    """GV3: the 20 published records of v1.1 (S4's runs, the v0.1.0 test slice, the judged and
    position records, answer-v2's runs) stay fully checked: each names golden.v1.jsonl, whose
    bytes are still theirs, so the validator derives their labels, behaviour fields and reference
    answers again (`record.current_golden`). One byte appended to the file and every one falls
    back to history (the break)."""
    manifests = v1_1_manifests()
    assert len(manifests) == 20
    stale = [m["run"] for m in manifests if record.current_golden(m, ROOT) is None]
    assert stale == []
    assert {m["dataset"]["path"] for m in manifests} == {"datasets/golden.v1.jsonl"}
