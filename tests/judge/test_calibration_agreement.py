"""S6 JC6 to JC8: the agreement, computed by code and tested on hand-computed tables; the
refusals of `raglab calibrate`; the record in how-to 05's template, generated and never edited by
hand; the bar read on the sealed labels only; the single-labeller caveat."""

import json
from collections import Counter
from datetime import timedelta
from fractions import Fraction
from typing import Any

import pytest

from raglab.evals import calibration
from raglab.evals.calibration import CalibrationError, Item, Pair
from tests.calibration_support import SEALED, answers_for, asker, inventory, sampled_root, ticking
from tests.conftest import ROOT
from tests.judge_support import reseal
from tests.retrieval_support import read_run

pytestmark = pytest.mark.unit
BAR = calibration.load_bar(ROOT / "datasets" / "calibration" / "judge-v2-c1")
COMMITS = {"bar": "a" * 40, "sample": "b" * 40, "labels": "c" * 40}


def table(a: int, b: int, c: int, d: int, criterion: str = "grounded") -> list[Pair]:
    """a: judge pass, label pass; b: judge pass, label fail; c: judge fail, label pass; d: judge
    fail, label fail."""
    cells = [("pass", "pass")] * a + [("pass", "fail")] * b
    cells += [("fail", "pass")] * c + [("fail", "fail")] * d
    return [Pair(Item(n, f"G-{n:02d}", 1, criterion), j, h) for n, (j, h) in enumerate(cells, 1)]


# The plan's table, 15 items with 7 judge passes and 8 judge fails, each kappa by hand:
# po = (a + d) / 15, pe = (7/15)(a + c)/15 + (8/15)(b + d)/15, kappa = (po - pe) / (1 - pe).
@pytest.mark.parametrize(
    ("b", "c", "expected", "status"),
    [
        (0, 0, Fraction(1), "trusted"),
        (1, 0, Fraction(32, 37), "trusted"),  # 0.865: (210 - 114) / (225 - 114)
        (0, 1, Fraction(98, 113), "trusted"),  # 0.867: (210 - 112) / (225 - 112)
        (2, 0, Fraction(8, 11), "reported only"),  # 0.727
        (0, 2, Fraction(14, 19), "reported only"),  # 0.737
        (3, 0, Fraction(64, 109), "not trusted"),  # 0.587
        (2, 1, Fraction(22, 37), "not trusted"),  # 0.595
        (1, 2, Fraction(68, 113), "reported only"),  # 0.602
        (0, 3, Fraction(14, 23), "reported only"),  # 0.609
        (4, 0, Fraction(4, 9), "not trusted"),  # 0.444
        (0, 4, Fraction(14, 29), "not trusted"),  # 0.483
    ],
)
def test_kappa_and_the_bar_on_the_plans_table(b, c, expected, status):
    pairs = table(7 - b, b, c, 8 - c)
    assert calibration.kappa(pairs) == expected
    assert calibration.raw_agreement(pairs) == Fraction(15 - b - c, 15)
    assert BAR.status("grounded", calibration.kappa(pairs)) == status


def test_kappa_is_undefined_when_both_raters_use_one_class_and_the_bar_says_so():
    pairs = table(15, 0, 0, 0)
    assert calibration.kappa(pairs) is None
    assert BAR.status("grounded", None) == "reported only"
    assert calibration.kappa(table(10, 5, 0, 0)) == 0  # the judge passes all: no better than chance


def test_tpr_and_tnr_by_hand_weighted_and_unweighted():
    """The plan's illustration: a sampled judge pass stands for 40 verdicts and a judge fail for
    5 (frames of 280 and 40, samples of 7 and 8); one judge pass the label fails takes the
    weighted TNR to one half, where the unweighted TNR is 8 of 9."""
    pairs = table(6, 1, 0, 8)
    sizes = {("grounded", "pass"): 280, ("grounded", "fail"): 40}
    weights = calibration.strata_weights(pairs, sizes)
    assert weights == {("grounded", "pass"): Fraction(40), ("grounded", "fail"): Fraction(5)}
    assert calibration.rates(pairs) == (Fraction(6, 6), Fraction(8, 9))
    assert calibration.rates(pairs, weights) == (Fraction(1), Fraction(1, 2))
    # TPR is the share of the label's passes the judge passes: 5 of 7 here, TNR 8 of 8
    assert calibration.rates(table(5, 0, 2, 8)) == (Fraction(5, 7), Fraction(1))
    tpr, tnr = calibration.rates(table(5, 0, 2, 8), weights)
    assert (tpr, tnr) == (Fraction(5 * 40, 5 * 40 + 2 * 5), Fraction(1))


def test_the_bootstrap_resamples_within_strata():
    """Each resample draws each stratum's own number of items from it, so the judge's verdicts
    keep their counts in every resample; seeded, so the same seed gives the same resamples."""
    pairs = table(4, 3, 2, 6)
    order = [("grounded", "pass"), ("grounded", "fail")]
    counts = Counter(p.stratum for p in pairs)
    drawn = list(calibration.resamples(pairs, order, 200, 7))
    for resample in drawn:
        assert Counter(p.stratum for p in resample) == counts
        for p in resample:
            assert p in pairs
    assert drawn == list(calibration.resamples(pairs, order, 200, 7))
    assert drawn != list(calibration.resamples(pairs, order, 200, 8))
    perfect: Any = calibration.agreement(
        table(7, 0, 0, 8), {s: 50 for s in order}, order, 500, 20261023, 0.95
    )
    assert perfect["kappa"] == {
        "value": 1.0,
        "ci_low": 1.0,
        "ci_high": 1.0,
        "undefined_resamples": 0,
    }


def test_an_undefined_resample_is_counted_never_imputed():
    """A judge-fail stratum of one label pass and one label fail: a resample that draws the fail
    twice has no label pass, so its TPR is undefined; it is counted and left out of the interval."""
    pairs = table(0, 1, 1, 1)
    order = [("grounded", "pass"), ("grounded", "fail")]
    sizes = {s: 10 for s in order}
    result: Any = calibration.agreement(pairs, sizes, order, 400, 3, 0.95)
    undefined = result["tpr"]["weighted"]["undefined_resamples"]
    assert 0 < undefined < 400
    assert result["tpr"]["weighted"]["value"] == 0.0


# ---------------------------------------------------------------- the record on a fixture


def judge_verdicts(root, run_id):
    _, lines = read_run(root / "runs" / "published" / run_id)
    return {
        (c["case_id"], c["trial"], k): v["verdict"] for c in lines for k, v in c["verdicts"].items()
    }


def labelled(tmp_path, disagree=(), relabel=False):
    """A fixture calibration with every item labelled as the judge's verdict but the orders in
    `disagree`, sealed at SEALED; with `relabel`, the re-label sealed a day later."""
    root, folder, run_id, _ = sampled_root(tmp_path)
    verdict = judge_verdicts(root, run_id)
    sample = calibration.read_sample(folder)
    flip = {"pass": "fail", "fail": "pass"}
    chosen = {
        i.order: flip[verdict[i.key]] if i.order in disagree else verdict[i.key]
        for i in sample.items
    }
    from raglab.evals import label

    shown = label.shown_items(root, sample, list(sample.items), inventory())
    label.run(root, folder, ask=asker(answers_for(shown, chosen)), say=lambda _: None,
              clock=ticking(), inventory=inventory())  # fmt: skip
    label.run(root, folder, seal=True, say=lambda _: None, clock=lambda: SEALED,
              inventory=inventory())  # fmt: skip
    if relabel:
        bar = calibration.load_bar(folder)
        again = label.shown_items(root, sample, calibration.relabel_items(sample, bar), inventory())
        later = SEALED + timedelta(days=1, hours=2)
        label.run(root, folder, relabel=True, ask=asker(answers_for(again)), say=lambda _: None,
                  clock=ticking(later), inventory=inventory())  # fmt: skip
        label.run(root, folder, relabel=True, seal=True, say=lambda _: None,
                  clock=lambda: later + timedelta(hours=1), inventory=inventory())  # fmt: skip
    return root, folder, run_id, sample, verdict


def classify(folder, sample, verdict, classes):
    rows = []
    for item in sample.items:
        if item.order in classes:
            rows.append(
                {**item.as_json(), "class": classes[item.order], "answer": "Yes, that class."}
            )
    (folder / calibration.DISAGREEMENTS).write_text(calibration.jsonl_text(rows))


def grounded_pass_order(sample, verdict):
    return next(
        i.order for i in sample.items if i.criterion == "grounded" and verdict[i.key] == "pass"
    )


def test_the_record_computes_the_agreement_from_the_sealed_labels(tmp_path):
    """One grounded judge pass labelled fail: grounded's table is 2, 1, 0, 3 (by hand: po 5/6,
    pe 1/2, kappa 2/3, reported only); the weights are the fixture's frame (8 judge passes and
    6 judge fails) over the sample (3 and 3): TNR weighted 6 / (8/3 + 6) = 9/13."""
    root, folder, _, sample, verdict = labelled(tmp_path)
    n = grounded_pass_order(sample, verdict)
    root, folder, _, sample, verdict = labelled(tmp_path / "x", disagree=(n,))
    classify(folder, sample, verdict, {n: "genuine ambiguity"})
    rec: Any = calibration.build_record(root, folder, COMMITS)
    grounded = rec["agreement"]["grounded"]
    assert grounded["confusion"] == {
        "judge pass, label pass": 2,
        "judge pass, label fail": 1,
        "judge fail, label pass": 0,
        "judge fail, label fail": 3,
    }
    assert grounded["raw"] == round(5 / 6, 6)
    assert grounded["kappa"]["value"] == round(2 / 3, 6)
    assert rec["status"]["grounded"] == "reported only"
    assert grounded["tnr"]["weighted"]["value"] == round(9 / 13, 6)
    assert grounded["tnr"]["unweighted"] == 0.75
    assert grounded["tpr"]["weighted"]["value"] == 1.0
    assert grounded["strata"]["grounded, judge pass"] == {
        "frame": 8,
        "sample": 3,
        "weight": round(8 / 3, 6),
    }
    assert rec["disagreements"]["classes"]["genuine ambiguity"] == 1
    assert rec["judge_noise"]["grounded"]["order"] is not None
    assert rec["relabel"] is None


def test_the_bar_reads_the_sealed_labels_and_a_correction_is_reported_beside(tmp_path):
    """The sealed-file test: a disagreement classed a human error is reported as a correction
    (the label read as the judge's verdict) beside the sealed label, never in the bar's number."""
    root, folder, _, sample, verdict = labelled(tmp_path)
    n = grounded_pass_order(sample, verdict)
    root, folder, _, sample, verdict = labelled(tmp_path / "x", disagree=(n,))
    classify(folder, sample, verdict, {n: "human error"})
    rec: Any = calibration.build_record(root, folder, COMMITS)
    assert rec["agreement"]["grounded"]["kappa"]["value"] == round(2 / 3, 6)
    assert rec["status"]["grounded"] == "reported only"
    assert rec["corrections"]["items"] == 1
    assert rec["corrections"]["criteria"]["grounded"]["kappa"] == 1.0


def test_a_disagreement_without_a_class_or_a_class_without_a_disagreement_is_refused(tmp_path):
    root, folder, _, sample, verdict = labelled(tmp_path)
    n = grounded_pass_order(sample, verdict)
    root, folder, _, sample, verdict = labelled(tmp_path / "x", disagree=(n,))
    with pytest.raises(
        CalibrationError, match=rf"a disagreement without a class: item\(s\) \[{n}\]"
    ):
        calibration.build_record(root, folder, COMMITS)
    other = next(i.order for i in sample.items if i.order != n)
    classify(folder, sample, verdict, {n: "human error", other: "human error"})
    with pytest.raises(CalibrationError, match=f"item {other} is not a disagreement"):
        calibration.build_record(root, folder, COMMITS)
    classify(folder, sample, verdict, {n: "the judge was wrong"})
    with pytest.raises(CalibrationError, match="is not one of"):
        calibration.build_record(root, folder, COMMITS)


def test_calibrate_refuses_a_bar_that_changed_since_the_sample(tmp_path):
    """JC1's break, in a fixture: the trusted line moved after the sample, 0.80 to 0.70."""
    root, folder, _, _, _ = labelled(tmp_path)
    path = folder / calibration.BAR
    path.write_text(path.read_text().replace("trusted = 0.80", "trusted = 0.70", 1))
    with pytest.raises(CalibrationError, match=r"the bar \(.*bar\.toml\) changed since the sample"):
        calibration.build_record(root, folder, COMMITS)


def test_calibrate_refuses_a_judged_verdict_flipped_with_its_reply_and_resealed(tmp_path):
    """JC6's break and AV2-J3's limit, in a fixture: one judged verdict flipped together with its
    reply and resealed validates as a run record, and calibrate refuses it by the manifest's
    sha256 the sample pinned."""
    root, folder, run_id, sample, _ = labelled(tmp_path)
    run_dir = root / "runs" / "published" / run_id
    manifest, lines = read_run(run_dir)
    item = sample.items[0]
    line = next(c for c in lines if (c["case_id"], c["trial"]) == (item.case_id, item.trial))
    held = line["verdicts"][item.criterion]
    flipped = "fail" if held["verdict"] == "pass" else "pass"
    reply = json.loads(held["reply"])
    held["verdict"], held["reply"] = flipped, json.dumps({**reply, "verdict": flipped})
    reseal(run_dir, manifest, lines)
    assert calibration.record.validate(run_dir, root) == []  # the record cannot tell
    with pytest.raises(CalibrationError, match="its manifest's sha256 is"):
        calibration.build_record(root, folder, COMMITS)


def test_calibrate_refuses_labels_off_their_seal_or_off_the_shown_answer(tmp_path):
    root, folder, _, _, _ = labelled(tmp_path)
    path = folder / calibration.LABELS
    rows = calibration.read_jsonl(path)
    rows[0] = {**rows[0], "answer_sha256": "0" * 64}
    path.write_text(calibration.jsonl_text(rows))
    with pytest.raises(CalibrationError, match="changed after its seal"):
        calibration.build_record(root, folder, COMMITS)
    calibration.seal(folder, calibration.LABELS, calibration.LABELS_SEAL, lambda: SEALED)
    with pytest.raises(CalibrationError, match="answer_sha256 is not the shown answer's"):
        calibration.build_record(root, folder, COMMITS)


def test_the_relabel_is_reported_with_the_gap_between_the_seals(tmp_path):
    root, folder, _, _, _ = labelled(tmp_path, relabel=True)
    rec: Any = calibration.build_record(root, folder, COMMITS)
    relabel = rec["relabel"]
    assert relabel["items"] == 2
    assert relabel["hours_after_the_labels_seal"] == 27.0
    assert relabel["pooled"]["raw"] is not None


def test_a_relabel_inside_its_gap_is_refused(tmp_path):
    root, folder, _, _, _ = labelled(tmp_path, relabel=True)
    path = folder / calibration.RELABELS
    rows = calibration.read_jsonl(path)
    rows[0] = {**rows[0], "labelled_at": "2026-10-24T10:00:00Z"}
    path.write_text(calibration.jsonl_text(rows))
    calibration.seal(folder, calibration.RELABELS, calibration.RELABELS_SEAL, lambda: SEALED)
    with pytest.raises(CalibrationError, match="less than 24 hours after the labels' seal"):
        calibration.build_record(root, folder, COMMITS)


def test_the_record_follows_how_to_05s_template_with_the_caveat(tmp_path):
    root, folder, run_id, _, _ = labelled(tmp_path)
    rec: Any = calibration.write_record(root, folder, COMMITS)
    text = (folder / calibration.RECORD_MD).read_text()
    block = text.split("```\n", 1)[1].split("```", 1)[0]
    keys = [line.split(":", 1)[0] for line in block.splitlines() if not line.startswith("  ")]
    assert keys == [
        "judge",
        "sample",
        "labellers",
        "agreement",
        "threshold",
        "disagreements",
        "verdict",
        "next",
    ]
    assert f"sample: {len(calibration.read_sample(folder).items)} verdicts of {run_id}" in text
    assert (
        "threshold: kappa >= 0.80 trusted, 0.60 to 0.80 reported only, < 0.60 not trusted" in text
    )
    assert "(written aaaaaaa, before the sample bbbbbbb and the labels ccccccc)" in text
    assert calibration.CAVEAT in text
    assert "labellers: the maintainer (blind)" in text
    assert calibration.TRIGGERS in text
    assert rec["status"] == {"grounded": "trusted", "abstains": "trusted"}
    assert "verdict: trusted for grounded, abstains; reported only for none" in text


def test_the_record_is_generated_never_edited_by_hand(tmp_path):
    """The regenerate test: record.md edited by hand, or a number of record.json, is found."""
    root, folder, _, _, _ = labelled(tmp_path)
    calibration.write_record(root, folder, COMMITS)
    assert calibration.record_problems(root, folder) == []
    md = folder / calibration.RECORD_MD
    md.write_text(md.read_text().replace("trusted for grounded", "trusted for grounded (sure)"))
    assert calibration.record_problems(root, folder) == [
        "record.md is not the one generated from record.json"
    ]
    calibration.write_record(root, folder, COMMITS)
    path = folder / calibration.RECORD_JSON
    data = json.loads(path.read_text())
    data["agreement"]["grounded"]["kappa"]["value"] = 0.95
    path.write_text(json.dumps(data, indent=2) + "\n")
    assert "record.json is not the record computed from its inputs" in calibration.record_problems(
        root, folder
    )


@pytest.mark.parametrize(
    "folder",
    [f for f in calibration.calibrations(ROOT) if (f / calibration.RECORD_JSON).exists()],
    ids=lambda p: p.name,
)
def test_every_committed_record_regenerates_from_its_inputs(folder):
    """The regenerate test on the repository (no record exists until the labels are sealed)."""
    assert calibration.record_problems(ROOT, folder) == []
