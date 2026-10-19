"""S4 AC5: the behaviour cases' checks and results (TEST-PLAN R6, `decision-label-and-abstention`),
with scripted FakeChat replies on a small pack that carries the real document and section ids, so
the real answer key's conflict sides and canaries apply. Every run here is also validated: the
validator recomputes every check and result from the record (AC6).

What each test holds: the decision label is read from the structured field, never the text; a
flag-conflict case whose conflict side was not retrieved expects answer with no conflict field;
an abstention may state a number only from a cited chunk of the case's may_quote section; the
conflict field names a retrieved chunk of each side (a group member stands for the governing
side); no canary of the other tenant, both ways; no answer_must_not_contain string; a citation of
a labelled section or group member is a citation hit."""

from typing import Any

import pytest

from raglab.evals import behaviour, record
from tests.generation_support import (
    B_33,
    FAQ_Q2,
    NIST,
    Q_ABQ,
    Q_ABS,
    Q_ANS,
    Q_FC,
    Q_FC2,
    Q_TB,
    V1_43,
    V2_5,
    V2_41,
    V2_44,
    behaviour_run,
    reply,
)
from tests.retrieval_support import read_run

pytestmark = pytest.mark.unit


def run(tmp_path, replies=None, **kwargs) -> tuple[Any, list[Any]]:
    root, run_dir = behaviour_run(tmp_path, replies, **kwargs)
    assert record.validate(run_dir, root) == []
    return read_run(run_dir)


def checks_of(cases: list[Any], case_id: str) -> dict[str, bool]:
    found = [c["checks"] for c in cases if c["case_id"] == case_id]
    assert found, case_id
    assert all(c == found[0] for c in found)  # FakeChat answers every trial alike
    return found[0]


def test_good_replies_pass_every_check_that_applies(tmp_path):
    _, cases = run(tmp_path)
    expected_checks = {
        "B-ANS": {"decision_label", "cites_label", "no_canary", "must_not_contain"},
        "B-FC": {"decision_label", "conflict", "cites_label", "no_canary", "must_not_contain"},
        "B-FC2": {"decision_label", "cites_label", "no_canary", "must_not_contain"},
        "B-ABS": {"decision_label", "abstained", "no_value", "no_canary", "must_not_contain"},
        "B-ABQ": {"decision_label", "abstained", "no_value", "no_canary", "must_not_contain"},
        "B-RH": {"decision_label", "cites_label", "no_canary", "must_not_contain"},
        "B-TB": {"decision_label", "cites_label", "no_canary", "must_not_contain"},
    }
    for case_id, names in expected_checks.items():
        checks = checks_of(cases, case_id)
        common = {"status_ok", "model_citations_retrieved", "passed"}
        assert set(checks) == names | common, case_id
        assert all(checks.values()), (case_id, checks)


def test_the_decision_label_is_the_field_never_the_text(tmp_path):
    """The S3 finding: a reply whose text abstains but whose label is answer fails the abstain
    case; a reply labelled abstain passes the decision even when its text would read otherwise
    (the value it states fails no_value instead); an answer case's label is answer whatever the
    text says."""
    _, cases = run(
        tmp_path,
        {
            Q_ABS: reply("answer", "The documents do not say how many reset attempts there are."),
            Q_ABQ: reply("abstain", "Yes: at least 64 characters.", [NIST.chunk_id]),
            Q_TB: reply("answer", "The documents do not say.", [B_33.chunk_id]),
        },
    )
    text_abstains = checks_of(cases, "B-ABS")
    assert text_abstains["decision_label"] is False
    assert text_abstains["abstained"] is False
    assert text_abstains["no_value"] is True  # no value stated: the S3 pattern
    assert checks_of(cases, "B-ABQ")["decision_label"] is True
    assert checks_of(cases, "B-TB")["decision_label"] is True


def test_a_conflict_side_retrieved_expects_the_flag_and_both_sides_named(tmp_path):
    named_one_side = reply(
        "flag-conflict", "Every 60 days now; it was 90.", [V1_43.chunk_id], [V1_43.chunk_id], "old"
    )
    _, cases = run(tmp_path, {Q_FC: named_one_side})
    checks = checks_of(cases, "B-FC")
    assert checks["decision_label"] is True
    assert checks["conflict"] is False  # the governing side (any member of its group) is unnamed
    _, cases = run(tmp_path / "b", {Q_FC: reply("answer", "Every 60 days.", [FAQ_Q2.chunk_id])})
    checks = checks_of(cases, "B-FC")
    assert checks["decision_label"] is False  # the conflict side was retrieved: flag it
    assert checks["conflict"] is False
    assert checks["cites_label"] is True  # the FAQ group member is a citation hit


def test_a_conflict_side_not_retrieved_expects_answer_without_a_conflict_field(tmp_path):
    """TEST-PLAN section 3: the miss counts against retrieval, not against the decision."""
    manifest, cases = run(tmp_path)
    good = checks_of(cases, "B-FC2")
    assert good["decision_label"] is True
    assert "conflict" not in good
    block = manifest["results"]["generation"]["behaviour"]
    assert block["conflict_side_missed"] == 2  # both trials of B-FC2
    flagged = reply(
        "flag-conflict", "Every 60 days.", [V2_44.chunk_id], [V2_44.chunk_id], "superseded"
    )
    answered_with_field = reply(
        "answer", "Every 60 days.", [V2_44.chunk_id], [V2_44.chunk_id], "superseded"
    )
    for n, bad in enumerate((flagged, answered_with_field)):
        _, cases = run(tmp_path / str(n), {Q_FC2: bad})
        assert checks_of(cases, "B-FC2")["decision_label"] is False, n


def test_an_answer_case_with_a_conflict_field_set_fails_the_decision(tmp_path):
    """TEST-PLAN section 3 as written (the labels judge's S4-L6; the user's answer on D-d): an
    `answer` case, here a current value like G-04's whose superseded version 1.0 states it
    differently, retrieved version 1.0 anyway. Naming 1.0 as superseded in the text passes;
    setting the conflict field fails the decision."""
    from tests.dataset_support import case, sec
    from tests.generation_support import Q_CUR, V1_44, behaviour_cases

    current = case(
        "B-CUR", "single-chunk", "answer", "dev", ["F-10"], [sec("A-PWD-V2", "5")], question=Q_CUR
    )
    cases = [*behaviour_cases(), current]
    flagged = reply(
        "answer",
        "It unlocks after 30 minutes; version 1.0 said otherwise.",
        [V2_5.chunk_id],
        [V2_5.chunk_id, V1_44.chunk_id],
        "version 1.0 is superseded",
    )
    _, rows = run(tmp_path, {Q_CUR: flagged}, cases=cases)
    checks = checks_of(rows, "B-CUR")
    assert checks["decision_label"] is False
    assert checks["cites_label"] is True
    assert "conflict" not in checks  # no conflict check applies to an answer case
    named = reply(
        "answer", "30 minutes (version 1.0, superseded, said otherwise).", [V2_5.chunk_id]
    )
    _, rows = run(tmp_path / "b", {Q_CUR: named}, cases=cases)
    assert checks_of(rows, "B-CUR")["decision_label"] is True


def test_an_abstention_may_quote_only_a_cited_chunk_of_its_may_quote_section(tmp_path):
    """D-03: the number is allowed when a cited chunk of the may_quote section (X-NIST 3.1.1.2)
    states it; not when that chunk is uncited, and not from a cited chunk of another section."""
    quoted = "Our documents do not say; NIST says at least 64 characters."
    _, cases = run(tmp_path, {Q_ABQ: reply("abstain", quoted, [NIST.chunk_id])})
    assert checks_of(cases, "B-ABQ")["no_value"] is True
    _, cases = run(tmp_path / "b", {Q_ABQ: reply("abstain", quoted)})
    assert checks_of(cases, "B-ABQ")["no_value"] is False  # the chunk was not cited
    other = reply("abstain", "Not said; a reset link lasts 30 minutes.", [B_33.chunk_id])
    _, cases = run(tmp_path / "c", {Q_ABQ: other})
    assert checks_of(cases, "B-ABQ")["no_value"] is False  # B-PWD 3.3 is not the may_quote section
    gap = reply("abstain", "Not said, but probably 10.", [V2_5.chunk_id])
    _, cases = run(tmp_path / "d", {Q_ABS: gap})
    assert checks_of(cases, "B-ABS")["no_value"] is False  # no may_quote: no number at all


def test_the_record_keeps_the_quotable_values_never_the_text(tmp_path):
    """The may_quote section's every chunk (the real excerpt's two), each with the numbers its text
    states, never the text."""
    from raglab.evals.oracle import policy_values
    from tests.generation_support import NIST_CHUNKS

    _, cases = run(tmp_path)
    quotes = [c["may_quote"] for c in cases if c["case_id"] == "B-ABQ"]
    assert all(q == quotes[0] for q in quotes)
    assert quotes[0] == {
        "doc_id": "X-NIST",
        "section_id": "3.1.1.2",
        "chunks": [
            {"chunk_id": c.chunk_id, "values": sorted(set(policy_values(c.text)))}
            for c in NIST_CHUNKS
        ],
    }
    assert "64" in quotes[0]["chunks"][0]["values"]
    assert all(c.text not in str(case) for c in NIST_CHUNKS for case in cases)


@pytest.mark.parametrize(
    ("question", "case_id", "text", "cited"),
    [
        (Q_TB, "B-TB", "Halvenroot passwords expire every 60 days.", B_33.chunk_id),
        (Q_ANS, "B-ANS", "Mirrowfen passwords are 16 characters; ours are 15.", None),
        (Q_TB, "B-TB", "HALVENROOT does it differently.", B_33.chunk_id),
        (Q_ANS, "B-ANS", "mirrowfen passwords are 16 characters; ours are 15.", None),
    ],
    ids=[
        "tenant A canary in a tenant B answer",
        "tenant B canary in a tenant A answer",
        "tenant A canary in capitals in a tenant B answer",
        "tenant B canary in lower case in a tenant A answer",
    ],
)
def test_no_canary_of_the_other_tenant_both_ways(tmp_path, question, case_id, text, cited):
    """Both ways, and in any letter case (the criteria judge's S4-J3)."""
    _, cases = run(tmp_path, {question: reply("answer", text, [cited] if cited else [])})
    assert checks_of(cases, case_id)["no_canary"] is False


@pytest.mark.parametrize("fold", [str, str.upper], ids=["as written", "in capitals"])
def test_no_answer_must_not_contain_string_of_the_cases_features(tmp_path, fold):
    """In any letter case (S4-J3); and the trial fails as a whole, not only the check (S4-J5)."""
    from raglab.ingest.answer_key import must_not_contain
    from tests.conftest import ROOT

    phrase = fold(must_not_contain(ROOT)["F-47"][-1])  # B-ANS lists F-47
    _, cases = run(tmp_path, {Q_ANS: reply("answer", f"Some say {phrase}.", [V2_41.chunk_id])})
    checks = checks_of(cases, "B-ANS")
    assert checks["must_not_contain"] is False
    assert checks["cites_label"] is True  # the phrase is the trial's only failure
    assert checks["passed"] is False


def test_the_results_by_hand(tmp_path):
    """Two trials of seven cases, each reply the same in both: B-RH passes; B-ANS is right in
    every check but repeats a phrase its feature F-47 bans, so it fails as a whole (S4-J5);
    B-ABS gives the S3 pattern (label answer, no value); B-ABQ abstains but states an uncited
    number; B-FC names only the conflict side; B-FC2 answers with a conflict field set; B-TB
    leaks a tenant A canary."""
    from raglab.ingest.answer_key import must_not_contain
    from tests.conftest import ROOT

    banned = must_not_contain(ROOT)["F-47"][-1]
    manifest, cases = run(
        tmp_path,
        {
            Q_ANS: reply("answer", f"15 characters; some say {banned}.", [V2_41.chunk_id]),
            Q_ABS: reply("answer", "The documents do not say how many reset attempts."),
            Q_ABQ: reply("abstain", "NIST says at least 64 characters."),
            Q_FC: reply("flag-conflict", "It changed.", [V1_43.chunk_id], [V1_43.chunk_id], "old"),
            Q_FC2: reply("answer", "60 days.", [V2_44.chunk_id], [V2_44.chunk_id], "x"),
            Q_TB: reply("answer", "Halvenroot does it differently.", [B_33.chunk_id]),
        },
    )
    metrics = manifest["results"]["metrics"]

    def value(name: str) -> tuple[float, int]:
        return metrics[name]["value"], metrics[name]["n"]

    # decision label: B-ANS, B-FC, B-ABQ, B-RH, B-TB right; B-FC2, B-ABS wrong: 10 of 14 trials
    assert value("decision_label") == (round(10 / 14, 6), 7)
    assert value("decision_label[answer]") == (round(4 / 6, 6), 3)  # B-ANS, B-FC2, B-TB
    assert value("decision_label[flag-conflict]") == (1.0, 1)
    assert value("decision_label[abstain]") == (0.5, 2)
    assert value("decision_label[refuse-and-help]") == (1.0, 1)
    assert value("abstention") == (0.0, 2)
    assert value("over_abstention") == (0.0, 5)
    # B-RH alone: B-ANS's banned phrase fails it as a whole, not only its must_not_contain check
    assert value("behaviour_pass^2") == (round(1 / 7, 6), 7)
    assert value("pass^2") == (round(1 / 7, 6), 7)  # S3's, over every case
    assert checks_of(cases, "B-ANS")["must_not_contain"] is False
    block = manifest["results"]["generation"]["behaviour"]
    zero = dict.fromkeys(behaviour.GIVEN, 0)
    assert block["confusion"] == {
        "answer": {**zero, "answer": 6},
        "abstain": {**zero, "answer": 2, "abstain": 2},
        "flag-conflict": {**zero, "flag-conflict": 2},
        "refuse-and-help": {**zero, "refuse-and-help": 2},
    }
    assert block["abstention"] == {
        "abstain_no_value": 0,
        "abstain_value": 2,  # B-ABQ
        "not_abstain_no_value": 2,  # B-ABS, the S3 pattern
        "not_abstain_value": 0,
    }
    assert block["label_agreement"] == {"cases": 7, "unanimous": 7}
    # label failures: B-FC2 (its conflict side was not retrieved) and B-ABS (no labels)
    assert block["label_failures"] == {"labels_retrieved": 0, "labels_missed": 2, "no_labels": 2}
    assert block["conflict_side_missed"] == 2
    report = (tmp_path / "repo" / "runs" / "tmp" / manifest["run_id"] / "report.md").read_text()
    assert "## Behaviour cases" in report
    assert "| not abstain | 2 | 0 |" in report
    assert "Only behaviour pass^2 on the dev split is gated" in report
    assert all(c["answer"] not in report for c in cases if c["answer"])


def test_a_withheld_answer_is_a_decision_failure_on_any_case(tmp_path):
    """A blocked trial is labelled abstain by the citation validator, not by the model: it fails
    decision_label even on an abstain case, and the confusion table calls it withheld."""
    cites_b = reply("abstain", "Not said.", [B_33.chunk_id])  # B-PWD 3.3 is not retrieved here
    manifest, cases = run(tmp_path, {Q_ABS: cites_b})
    checks = checks_of(cases, "B-ABS")
    assert checks["status_ok"] is False
    assert checks["decision_label"] is False
    confusion = manifest["results"]["generation"]["behaviour"]["confusion"]
    assert confusion["abstain"]["withheld"] == 2
