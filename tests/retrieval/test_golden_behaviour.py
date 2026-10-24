"""S4 AC1: the committed golden file's behaviour cases. 40 cases in the build project's mix
(15/8/8/4/5); a test case for every mix kind and every label; S3's probes P-01 to P-03 kept in dev
with S3's ids, tenants and questions; about two thirds dev; no behaviour question repeats a
retrieval question's wording; every requirement whose traceability cell said "tbd (S4)" has a
case; and the longest run of words a question shares with a document (S2's measure), which the
datasheet reports and this file checks against the documents, with no threshold.

`raglab check-dataset` holds the mix and split rules too (rule 9). This file reads the committed
lines itself, so it is a second reading of the file the user signs off, not a copy of the rule.
Golden set v1.1 is frozen since S4b, which holds v2 in tests/retrieval/test_golden_v2.py; S2's
measure and the file's reading live in tests/golden_support.py, shared by both.
"""

import json
from collections import Counter
from typing import Any

import pytest

from tests.conftest import ROOT
from tests.corpus_text import answer_key, norm
from tests.golden_support import (
    V1,
    corpus,
    golden_lines,
    longest_run,
    slot,
    texts,
    words,
)

pytestmark = pytest.mark.retrieval
DATASET = V1
DATASHEET = ROOT / "datasets" / "DATASHEET.md"
PROBES = ROOT / "datasets" / "probes.s3.jsonl"
# the build project's mix (the S4 plan); a paraphrase and a misspelling share one slot
MIX = {
    "single-chunk": 15,
    "multi-chunk": 8,
    "unanswerable": 8,
    "version-conflict": 4,
    "paraphrased or misspelled": 5,
}
LABELS = ("answer", "abstain", "flag-conflict", "refuse-and-help")
# the traceability cells that said "tbd (S4)" (the S4 plan, "Requirements the cases cover")
S4_REQUIREMENTS = (
    "R-01", "R-02", "R-03", "R-04", "R-05", "R-06", "R-07",
    "R-10", "R-11", "R-12", "R-14", "R-18", "R-23",
)  # fmt: skip


def lines() -> tuple[dict[str, Any], ...]:
    return golden_lines(DATASET)


def cases() -> list[dict[str, Any]]:
    return [line for line in lines() if line["kind"] == "behaviour"]


def test_the_set_has_40_behaviour_cases_in_the_build_projects_mix():
    found = Counter(slot(c["mix"]) for c in cases())
    assert len(cases()) == 40
    wrong = [f"{k}: {found[k]}, the mix asks for {n}" for k, n in MIX.items() if found[k] != n]
    wrong += [f"{k} is no slot of the mix" for k in found if k not in MIX]
    assert not wrong, "the mix 15/8/8/4/5: " + "; ".join(wrong)


def test_every_mix_kind_and_every_label_has_a_test_case():
    tested = [c for c in cases() if c["split"] == "test"]
    missing = [k for k in MIX if k not in {slot(c["mix"]) for c in tested}]
    missing += [label for label in LABELS if label not in {c["expected"] for c in tested}]
    assert not missing, f"every mix kind and every label has a test case: none for {missing}"


def test_the_s3_probes_are_dev_cases_with_their_ids_tenants_and_questions():
    text = PROBES.read_text(encoding="utf-8")
    probes = [json.loads(line) for line in text.splitlines() if line.strip()]
    assert [p["id"] for p in probes] == ["P-01", "P-02", "P-03"]
    by_id = {c["id"]: c for c in cases()}
    for probe in probes:
        case = by_id.get(probe["id"])
        assert case is not None, f"the S3 probe {probe['id']} is not a behaviour case"
        assert (case["tenant"], case["question"]) == (probe["tenant"], probe["question"])
        assert (case["expected"], case["feature_ids"]) == (probe["expected"], probe["feature_ids"])
        assert case["split"] == "dev", f"{probe['id']}: an S3 probe stays in dev (S3 has run it)"


def test_about_two_thirds_of_the_cases_are_dev():
    """Two thirds of 40 is 26.7: 27 dev, give or take one case."""
    splits = Counter(c["split"] for c in cases())
    assert set(splits) == {"dev", "test"}
    assert abs(splits["dev"] - round(len(cases()) * 2 / 3)) <= 1, dict(splits)


def contains(longer: list[str], shorter: list[str]) -> bool:
    return f" {' '.join(shorter)} " in f" {' '.join(longer)} "


def test_no_behaviour_question_repeats_a_retrieval_questions_wording():
    """Neither question's words, in order, hold the other's, in either tenant."""
    retrieval = [(q["id"], words(q["question"])) for q in lines() if q["kind"] == "retrieval"]
    assert len(retrieval) == 34
    for case in cases():
        mine = words(case["question"])
        for rid, theirs in retrieval:
            repeats = contains(mine, theirs) or contains(theirs, mine)
            assert not repeats, f"{case['id']} repeats the wording of {rid}"


def covered() -> dict[str, set[str]]:
    """Each requirement's behaviour cases: a case covers the requirements its features name in
    the answer key."""
    requirements = {f["id"]: f["requirements"] for f in answer_key()["features"]}  # type: ignore[index]
    out: dict[str, set[str]] = {}
    for case in cases():
        for feature in case["feature_ids"]:
            for rid in requirements[feature]:
                out.setdefault(rid, set()).add(case["id"])
    return out


def test_every_requirement_s4_covers_has_a_case():
    """R-02 (citation integrity) is the answer key's gap among them: no document can plant it,
    and S3's model_citations_retrieved check applies to every case of every kind."""
    gaps = {g["requirement"] for g in answer_key()["gaps"]}  # type: ignore[union-attr]
    found = covered()
    assert [rid for rid in S4_REQUIREMENTS if rid in gaps] == ["R-02"]
    missing = [rid for rid in S4_REQUIREMENTS if rid not in gaps and not found.get(rid)]
    assert not missing, f"no behaviour case covers {missing}"


# ---------------------------------------------------------------- S2's measure


def measure() -> dict[str, int]:
    retrieval = [words(q["question"]) for q in lines() if q["kind"] == "retrieval"]
    behaviour = [words(c["question"]) for c in cases()]
    asked = texts(retrieval)
    return {
        "retrieval": max(longest_run(q, corpus()) for q in retrieval),
        "behaviour": max(longest_run(q, corpus()) for q in behaviour),
        "behaviour against retrieval": max(longest_run(q, asked) for q in behaviour),
    }


def test_the_datasheet_reports_the_longest_run_a_question_shares_with_a_document():
    """S2's measure, from the documents and the committed questions. The datasheet reports it
    and nothing bounds it: the test holds the report to the measure, not the measure to a
    limit."""
    found = measure()
    text = norm(DATASHEET.read_text(encoding="utf-8"))
    reported = {
        "retrieval": "the longest run of words a question shares with any of them is {} words",
        "behaviour": "The longest run any behaviour case shares with a document is {} words",
        "behaviour against retrieval": "retrieval questions: the longest shared run is {} words",
    }
    for name, sentence in reported.items():
        assert sentence.format(found[name]) in text, f"{name}: {found[name]} words, not reported"


def test_the_measure_finds_a_known_run():
    """The measure on a small input: the run crosses no text boundary, and a word split by a
    hyphen counts as two words."""
    within = texts([words("Call the network operations on-call rota today."), words("the rota")])
    assert longest_run(words("Who is on the network operations on-call rota?"), within) == 6
    assert longest_run(words("today the rota"), within) == 2  # not 3 across the two texts
    assert longest_run(words("nothing here"), within) == 0
