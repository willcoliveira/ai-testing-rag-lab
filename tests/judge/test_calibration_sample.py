"""S6 JC4: the sample, drawn by rule s6-1 (seeded, stratified by criterion and the judge's verdict,
blind), holds the pins and the item keys only, grouped by criterion and shuffled within, and is
drawn again from the published record it pins. The v1.1 judged records serve as fixtures here and
are never sampled for labels: their verdicts are quoted in the S5 and answer-v2 ledgers."""

import json
from collections import Counter
from dataclasses import replace
from pathlib import Path

import pytest

from raglab.evals import calibration
from raglab.evals.calibration import CalibrationError, Item
from tests.calibration_support import FOLDER, published_root, sampled_root
from tests.conftest import ROOT
from tests.retrieval_support import read_run

pytestmark = pytest.mark.unit
COMMITTED_BAR = calibration.load_bar(ROOT / "datasets" / "calibration" / "judge-v2-c1")
V11 = "20261021T081852Z-judge-local-dev-5aa0ec5"


def line(case: str, trial: int, **verdicts: str) -> dict:
    return {
        "case_id": case,
        "trial": trial,
        "verdicts": {c: {"status": "ok", "verdict": v} for c, v in verdicts.items()},
    }


def bar(grounded: tuple[int, int] = (2, 2), abstains: tuple[int, int] | None = None):
    """The committed bar with other allocations (the lines and the seed kept)."""
    lines_of = COMMITTED_BAR.criteria[0]
    allocations = {"grounded": grounded, **({"abstains": abstains} if abstains else {})}
    rows = tuple(
        calibration.CriterionBar(name, p, f, lines_of.trusted, lines_of.stop)
        for name, (p, f) in allocations.items()
    )
    return replace(COMMITTED_BAR, criteria=rows)


def test_the_draw_on_a_v11_record_is_stratified_seeded_and_one_answer_once():
    """Rule s6-1 on 5aa0ec5 with the committed bar: 15 items per criterion, the judge's passes and
    fails as allocated (the abstains judge-pass stratum short: 6 verdicts of 3 cases, one answer
    already taken by grounded), every answer once, the same draw twice."""
    _, lines = read_run(ROOT / "runs" / "published" / V11)
    drawn = calibration.draw(lines, COMMITTED_BAR)
    assert Counter(i.criterion for i in drawn.items) == {"grounded": 15, "abstains": 15}
    assert drawn.frame == {
        ("grounded", "pass"): 125,
        ("grounded", "fail"): 19,
        ("abstains", "pass"): 6,
        ("abstains", "fail"): 11,
    }
    assert drawn.drawn[("grounded", "pass")] == 7
    assert drawn.drawn[("grounded", "fail")] == 8
    assert drawn.shortfall == (
        {
            "criterion": "abstains",
            "stratum": "judge pass",
            "wanted": 7,
            "drawn": 5,
            "from_other_stratum": 2,
        },
    )
    answers = [(i.case_id, i.trial) for i in drawn.items]
    assert len(set(answers)) == len(answers)
    assert calibration.draw(lines, COMMITTED_BAR) == drawn
    verdict = {
        (c["case_id"], c["trial"], k): v["verdict"] for c in lines for k, v in c["verdicts"].items()
    }
    for i in drawn.items:
        assert verdict[i.key] in ("pass", "fail")


def test_one_item_per_case_first_then_second_trials_in_the_same_order():
    """Case A has three trials in the stratum, B and C one each: four items take A, B and C
    first, then a second trial of A."""
    lines = [line("A", t, grounded="pass") for t in (1, 2, 3)]
    lines += [line("B", 1, grounded="pass"), line("C", 1, grounded="pass")]
    lines += [line("D", t, grounded="fail") for t in (1, 2)]
    drawn = calibration.draw(lines, bar(grounded=(4, 2)))
    passes = [(i.case_id, i.trial) for i in drawn.items if i.case_id != "D"]
    assert Counter(case for case, _ in passes) == {"A": 2, "B": 1, "C": 1}
    assert drawn.shortfall == ()


def test_an_answer_already_in_the_sample_is_skipped():
    """An abstain case's answer judged on both criteria is drawn for one of them only."""
    lines = [line("X", 1, grounded="pass", abstains="pass"), line("Y", 1, grounded="fail")]
    lines.append(line("Z", 1, abstains="fail"))
    drawn = calibration.draw(lines, bar(grounded=(1, 1), abstains=(1, 1)))
    assert [(i.case_id, i.criterion) for i in drawn.items if i.case_id == "X"] == [
        ("X", "grounded")
    ]
    assert drawn.shortfall[0]["criterion"] == "abstains"


def test_a_short_stratum_gives_all_it_has_and_the_other_stratum_gives_the_rest():
    lines = [line("P1", 1, grounded="pass")] + [line(f"F{n}", 1, grounded="fail") for n in range(5)]
    drawn = calibration.draw(lines, bar(grounded=(3, 2)))
    assert len(drawn.items) == 5
    assert drawn.drawn == {("grounded", "pass"): 1, ("grounded", "fail"): 4}
    assert drawn.shortfall == (
        {
            "criterion": "grounded",
            "stratum": "judge pass",
            "wanted": 3,
            "drawn": 1,
            "from_other_stratum": 2,
        },
    )


def test_only_first_pass_ok_verdicts_of_pass_or_fail_are_in_the_frame():
    lines = [line("A", 1, grounded="pass"), line("B", 1, grounded="fail")]
    lines.append(
        {
            "case_id": "C",
            "trial": 1,
            "verdicts": {"grounded": {"status": "invalid_output", "verdict": "unable_to_verify"}},
            "repeat": {"grounded": {"status": "ok", "verdict": "fail"}},
        }
    )
    undecided = line("D", 1, grounded="unable_to_verify")
    lines.append(undecided)
    strata = calibration.frame(lines, ["grounded"])
    assert strata == {("grounded", "pass"): [("A", 1)], ("grounded", "fail"): [("B", 1)]}


def test_the_sample_file_holds_the_pins_and_the_item_keys_only(tmp_path):
    """The field test: the first line is the pins, each other line an item's order, case id,
    trial and criterion, and nothing else: no verdict and no stratum."""
    root, folder, run_id, _ = sampled_root(tmp_path)
    rows = [json.loads(x) for x in (folder / calibration.SAMPLE).read_text().splitlines()]
    assert list(rows[0]) == ["pins"]
    pins = rows[0]["pins"]
    assert list(pins) == list(calibration.PIN_FIELDS)
    manifest = root / "runs" / "published" / run_id / "manifest.json"
    assert pins["judged_run"] == run_id
    assert pins["judged_manifest_sha256"] == calibration.sha256_file(manifest)
    assert pins["bar_sha256"] == calibration.sha256_file(folder / calibration.BAR)
    assert (pins["rule"], pins["seed"], pins["judge_prompt"]) == ("s6-1", 20261023, "judge-v2")
    for row in rows[1:]:
        assert list(row) == list(calibration.ITEM_FIELDS)
    text = (folder / calibration.SAMPLE).read_text()
    for word in ('"verdict"', '"stratum"', "REASON", "QUOTE"):
        assert word not in text


def test_a_sample_with_a_verdict_field_is_refused(tmp_path):
    """JC4's break, in a fixture: a verdict field added to an item."""
    _, folder, _, _ = sampled_root(tmp_path)
    path = folder / calibration.SAMPLE
    rows = path.read_text().splitlines()
    item = json.loads(rows[1])
    rows[1] = json.dumps({**item, "verdict": "pass"})
    path.write_text("\n".join(rows) + "\n")
    with pytest.raises(CalibrationError, match="only"):
        calibration.read_sample(folder)


def order_problems(sample: calibration.Sample, bar_: calibration.Bar) -> list[str]:
    """The order test: the items grouped by criterion in the bar's order, and within each, the
    seeded shuffle of its items sorted by case id and trial."""
    problems: list[str] = []
    names = [c.name for c in bar_.criteria]
    seen = [i.criterion for i in sample.items]
    grouped = [n for n in names if n in seen]
    if seen != [n for n in grouped for _ in range(seen.count(n))]:
        problems.append("the items are not grouped by criterion in the bar's order")
    for name in grouped:
        mine = [(i.case_id, i.trial) for i in sample.items if i.criterion == name]
        expected = sorted(mine)
        calibration._rng(bar_.seed, "order", name).shuffle(expected)  # pyright: ignore[reportPrivateUsage]
        if mine != expected:
            problems.append(f"{name}'s items are not in the seeded shuffle's order")
    return problems


def test_the_items_are_grouped_by_criterion_and_shuffled_within(tmp_path):
    _, folder, _, _ = sampled_root(tmp_path)
    sample = calibration.read_sample(folder)
    assert order_problems(sample, calibration.load_bar(folder)) == []
    assert {i.criterion for i in sample.items} == {"grounded", "abstains"}


def test_items_written_in_verdict_order_fail_the_order_and_redraw_tests(tmp_path):
    """JC4's break, in a fixture: one criterion's items rewritten in the judge's verdict order."""
    root, folder, run_id, _ = sampled_root(tmp_path)
    _, lines = read_run(root / "runs" / "published" / run_id)
    verdict = {(c["case_id"], c["trial"]): c["verdicts"] for c in lines}
    sample = calibration.read_sample(folder)
    grounded = [i for i in sample.items if i.criterion == "grounded"]
    by_verdict = sorted(
        grounded, key=lambda i: verdict[(i.case_id, i.trial)]["grounded"]["verdict"]
    )
    assert by_verdict != grounded, "the fixture's shuffle mixes the verdicts"
    rest = [i for i in sample.items if i.criterion != "grounded"]
    items = [Item(n, i.case_id, i.trial, i.criterion) for n, i in enumerate(by_verdict + rest, 1)]
    (folder / calibration.SAMPLE).write_text(calibration.sample_text(sample.pins, items))
    resealed = calibration.read_sample(folder)
    assert order_problems(resealed, calibration.load_bar(folder))
    assert calibration.redraw_problems(root, folder)


def test_the_sample_is_drawn_again_from_the_published_record(tmp_path):
    root, folder, _, _ = sampled_root(tmp_path)
    assert calibration.redraw_problems(root, folder) == []


def test_one_item_swapped_by_hand_fails_the_redraw_naming_it(tmp_path):
    """JC4's break, in a fixture: one item replaced by an answer the draw did not take."""
    root, folder, run_id, _ = sampled_root(tmp_path)
    sample = calibration.read_sample(folder)
    _, lines = read_run(root / "runs" / "published" / run_id)
    taken = {(i.case_id, i.trial) for i in sample.items}
    spare = next(
        (c["case_id"], c["trial"])
        for c in lines
        if (c["case_id"], c["trial"]) not in taken and "grounded" in c["verdicts"]
    )
    first = sample.items[0]
    items = [Item(1, spare[0], spare[1], first.criterion), *sample.items[1:]]
    (folder / calibration.SAMPLE).write_text(calibration.sample_text(sample.pins, items))
    problems = calibration.redraw_problems(root, folder)
    assert any(p.startswith("item 1 is ") for p in problems), problems


def test_a_sample_is_drawn_once_and_only_from_a_published_judged_record(tmp_path):
    root, run_id, source, _ = published_root(tmp_path)
    folder = root / FOLDER
    with pytest.raises(CalibrationError, match="not published"):
        calibration.draw_sample(root, folder, "20261020T000000Z-judge-test-dev-0000000")
    with pytest.raises(CalibrationError, match="not a judged run"):
        calibration.draw_sample(root, folder, source)
    calibration.draw_sample(root, folder, run_id)
    with pytest.raises(CalibrationError, match="drawn once"):
        calibration.draw_sample(root, folder, run_id)


@pytest.mark.parametrize("folder", calibration.calibrations(ROOT), ids=lambda p: Path(p).name)
def test_every_committed_sample_is_drawn_again_from_its_published_record(folder):
    """The re-draw test on the repository: each committed sample equals rule s6-1 over the
    published judged record it pins (none is drawn until S4b's run is judged)."""
    assert calibration.redraw_problems(ROOT, folder) == []
    sample = calibration.read_sample(folder)
    assert order_problems(sample, calibration.load_bar(folder)) == []
