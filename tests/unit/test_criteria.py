"""S5 AC1: docs/CRITERIA.md, written first. Every criterion has what it applies to, what the judge
sees, when it passes and fails, its requirements, its grader and its status; its pass and fail
rules are the current judge prompt's (judge-v2's) words exactly, and what the judge sees is its
inputs; every
requirement it names is one of TEST-PLAN's; and the canary table is the canary file: every item
names a criterion and a side, and every criterion has an item on each side."""

import re

import pytest

from raglab.core.types import CRITERIA
from raglab.judge import canaries
from raglab.judge.prompts import judge_v2
from tests.conftest import ROOT

pytestmark = pytest.mark.unit
CRITERIA_MD = ROOT / "docs" / "CRITERIA.md"
TEST_PLAN = ROOT / "docs" / "TEST-PLAN.md"
CANARIES = ROOT / "datasets" / "canaries.judge.jsonl"
SNAPSHOT = ROOT / "corpus" / "inventory.snapshot.json"
FIELDS = (
    "Applies to",
    "The judge sees",
    "Passes when",
    "Fails when",
    "Requirements",
    "Grader",
    "Status",
)
# the words of "The judge sees" that name each input of the judge prompt
INPUT_WORDS = {
    "question": "the question",
    "passages": "passages",
    "reference": "the reference answer",
    "answer": "the answer",
}


def sections(text: str) -> dict[str, str]:
    """Each criterion's section under "## The criteria", by name."""
    body = text.split("\n## The criteria\n", 1)[1].split("\n## ", 1)[0]
    found: dict[str, str] = {}
    for part in re.split(r"\n### ", "\n" + body)[1:]:
        heading, _, rest = part.partition("\n")
        name = re.match(r"`([a-z_]+)`", heading)
        assert name, f"a criterion's heading names it in backticks: {heading!r}"
        found[name.group(1)] = rest
    return found


def fields(section: str) -> dict[str, str]:
    """The bold fields of a criterion's bullets, their continuation lines joined. A bullet may
    hold two fields ("**Grader:** ... **Status:** ...")."""
    found: dict[str, str] = {}
    bullets = re.split(r"\n- ", "\n" + section.strip())[1:]
    for bullet in bullets:
        text = " ".join(line.strip() for line in bullet.splitlines())
        for name, value in re.findall(
            r"\*\*([A-Za-z ]+):\*\* (.*?)(?= \*\*[A-Za-z ]+:\*\*|$)", text
        ):
            found[name] = value.strip()
    return found


def criteria() -> dict[str, dict[str, str]]:
    return {
        name: fields(s) for name, s in sections(CRITERIA_MD.read_text(encoding="utf-8")).items()
    }


def test_every_criterion_has_every_field():
    found = criteria()
    assert tuple(found) == CRITERIA
    for name, values in found.items():
        missing = [f for f in FIELDS if not values.get(f)]
        assert not missing, f"{name} has no {missing}"


def test_the_pass_and_fail_rules_are_judge_v2s_words():
    for name, values in criteria().items():
        rule = judge_v2.RULES[name]
        assert values["Passes when"] == rule.passes + ".", name
        assert values["Fails when"] == rule.fails + ".", name


def test_what_the_judge_sees_is_judge_v2s_inputs():
    for name, values in criteria().items():
        seen = values["The judge sees"]
        named = {key for key, words in INPUT_WORDS.items() if words in seen}
        assert named == set(judge_v2.RULES[name].sees), (name, seen)


def test_every_requirement_named_is_one_of_the_test_plans():
    plan = TEST_PLAN.read_text(encoding="utf-8")
    known = set(re.findall(r"^\| (R-\d\d) \|", plan, flags=re.M))
    named_any = False
    for name, values in criteria().items():
        for requirement in re.findall(r"R-\d\d", values["Requirements"]):
            named_any = True
            assert requirement in known, f"{name} names {requirement}, which TEST-PLAN lacks"
    assert named_any


def test_every_criterion_is_reported_and_graded_by_judge_v2():
    for name, values in criteria().items():
        assert values["Grader"].startswith("judge-v2"), name
        assert values["Status"].startswith("reported"), name


def canary_table() -> list[list[str]]:
    text = CRITERIA_MD.read_text(encoding="utf-8")
    body = text.split("\n## The canary set\n", 1)[1].split("\n## ", 1)[0]
    rows = [line for line in body.splitlines() if re.match(r"^\| C-\d\d \|", line)]
    return [[cell.strip().strip("`") for cell in row.strip("|").split("|")] for row in rows]


def test_the_canary_table_is_the_canary_file():
    loaded = canaries.load(CANARIES)
    assert canary_table() == [[c.id, c.criterion, c.side, c.purpose] for c in loaded]


def test_every_canary_names_a_criterion_and_a_side_and_each_criterion_has_both_sides():
    loaded = canaries.load(CANARIES)
    for canary in loaded:
        assert canary.criterion in CRITERIA
        assert canary.side in ("pass", "fail")
    for criterion in CRITERIA:
        sides = {c.side for c in loaded if c.criterion == criterion}
        assert sides == {"pass", "fail"}, f"{criterion} has canaries on {sorted(sides)} only"


def test_the_metric_canary_its_twin_and_the_injection_canaries_are_there():
    by_id = {c.id: c for c in canaries.load(CANARIES)}
    p01 = "How many password reset attempts are allowed per day?"
    metric = [c for c in by_id.values() if c.question == p01 and c.side == "fail"]
    assert {(c.criterion, c.answer) for c in metric if "Five" in (c.answer or "")} >= {
        ("grounded", by_id["C-01"].answer),
        ("abstains", by_id["C-02"].answer),
    }
    twin = by_id["C-03"].answer
    assert twin == by_id["C-04"].answer
    assert twin is not None
    assert not re.search(r"\d", twin), "the honest twin states no value"
    assert (by_id["C-03"].side, by_id["C-04"].side) == ("pass", "pass")
    assert "evaluator" in (by_id["C-18"].answer or "")  # the line addressed to the evaluator
    written = [p for p in by_id["C-19"].passages or () if not isinstance(p, str)]
    assert len(written) == 1
    assert "pass for every answer" in written[0].text
    assert (by_id["C-18"].side, by_id["C-19"].side) == ("fail", "fail")


def test_every_corpus_passage_a_canary_names_is_in_the_committed_inventory():
    """The ids are written at the default settings, which the committed snapshot holds (the
    same ids on a Mac and on CI)."""
    snapshot = SNAPSHOT.read_text(encoding="utf-8")
    for canary in canaries.load(CANARIES):
        for chunk_id in canary.corpus_ids():
            assert f'"id": "{chunk_id}"' in snapshot, f"{canary.id}: {chunk_id}"
