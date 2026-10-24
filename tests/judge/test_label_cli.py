"""S6 JC5 and JC7: the blind label CLI. Each item is the JudgeItem the judged run built, rebuilt
from the source run and the corpus; the screen holds none of the judge's fields and is the same
without the judged record's lines; a label is recorded in the judge's schema (a quote found in the
answer, passage ids among those shown); it resumes, redoes and seals, and refuses any change after
the seal; the re-label opens a day after the seal and shows no first label."""

import json
from datetime import timedelta

import pytest

from raglab.__main__ import main
from raglab.evals import calibration, label
from raglab.evals.calibration import CalibrationError
from tests.calibration_support import (
    QUOTE,
    REASON,
    SEALED,
    answers_for,
    asker,
    inventory,
    sampled_root,
    ticking,
)

pytestmark = pytest.mark.unit


def shown(root, folder, relabel=False):
    sample = calibration.read_sample(folder)
    bar = calibration.load_bar(folder)
    items = calibration.relabel_items(sample, bar) if relabel else list(sample.items)
    return label.shown_items(root, sample, items, inventory())


def session(root, folder, answers, **kwargs):
    """A label session with scripted answers; (exit code, everything it said)."""
    said: list[str] = []
    code = label.run(
        root,
        folder,
        ask=asker(answers),
        say=said.append,
        clock=kwargs.pop("clock", ticking()),
        monotonic=kwargs.pop("monotonic", iter(range(10**6)).__next__),
        inventory=inventory(),
        **kwargs,
    )
    return code, "\n".join(said)


def test_each_item_is_the_judge_item_the_judged_run_built(tmp_path):
    root, folder, _, recording = sampled_root(tmp_path)
    items = shown(root, folder)
    assert items
    for s in items:
        assert s.judge_item in recording.items, s.item
        assert s.judge_item.criterion == s.item.criterion


def test_the_screen_shows_the_judges_inputs_and_rules_and_none_of_its_fields(tmp_path):
    """The blindness test: the criterion's rules and every input the judge saw are shown; no
    judge reason, quote or verdict line is."""
    root, folder, _, _ = sampled_root(tmp_path)
    items = shown(root, folder)
    code, screen = session(root, folder, answers_for(items))
    assert code == 0
    for s in items:
        assert f"Criterion: {s.item.criterion}\nPass when " in screen
        assert s.answer in screen
        assert s.judge_item.question is not None
        assert s.judge_item.question in screen
        for p in s.judge_item.passages or ():
            assert p.text in screen
            assert f'id="{p.chunk_id}"' in screen
    assert REASON not in screen
    assert QUOTE not in screen
    for field in ('"verdict"', '"reason"', '"answer_quote"', "passages_given", "quote_found"):
        assert field not in screen


def test_the_screen_is_the_same_without_the_judged_records_lines(tmp_path):
    """The CLI never opens the judged record's cases.jsonl: removed, the session says the same."""
    root, folder, run_id, _ = sampled_root(tmp_path)
    answers = answers_for(shown(root, folder))
    _, before = session(root, folder, answers)
    (folder / calibration.LABELS).unlink()
    (root / "runs" / "published" / run_id / "cases.jsonl").unlink()
    _, after = session(root, folder, answers)
    assert after == before


def test_a_label_is_recorded_in_the_judges_schema(tmp_path):
    root, folder, _, _ = sampled_root(tmp_path)
    items = shown(root, folder)
    session(root, folder, answers_for(items, {1: "fail"}))
    rows = calibration.read_jsonl(folder / calibration.LABELS)
    assert [r["order"] for r in rows] == [s.item.order for s in items]
    first = rows[0]
    assert list(first) == list(calibration.LABEL_FIELDS)
    assert first["verdict"] == "fail"
    assert first["answer_quote"] == items[0].answer.split()[0]
    assert first["passage_ids"] == list(items[0].ids[:1])
    assert first["ambiguous"] is False
    assert first["answer_sha256"] == calibration.judged_record.sha256_text(items[0].answer)
    assert first["seconds"] == 1  # the monotonic clock read when the item is shown and labelled
    assert str(first["labelled_at"]).startswith("2026-10-24T09:00:")
    for row, s in zip(rows, items, strict=True):
        assert calibration.label_problems(row, s.item, s.answer, s.ids, "judge-v2") == []


def test_a_quote_not_in_the_answer_is_refused(tmp_path):
    root, folder, _, _ = sampled_root(tmp_path)
    items = shown(root, folder)
    answers = answers_for(items)
    answers[1:1] = ["words the answer never says"]  # the first item's first quote
    _, screen = session(root, folder, answers)
    assert "That quote is not in the answer" in screen
    row = calibration.read_jsonl(folder / calibration.LABELS)[0]
    assert row["answer_quote"] == items[0].answer.split()[0]
    edited = {**row, "answer_quote": "words the answer never says"}
    problems = calibration.label_problems(
        edited, items[0].item, items[0].answer, items[0].ids, "judge-v2"
    )
    assert problems == [
        f"item 1 ({items[0].item.criterion}): the quote is not words of the answer shown"
    ]


def test_passage_ids_outside_those_shown_are_refused(tmp_path):
    """The schema test: a passage number or id the item did not show is asked again, and a
    label that names one is refused."""
    root, folder, _, _ = sampled_root(tmp_path)
    items = shown(root, folder)
    assert items[0].ids
    with pytest.raises(ValueError, match="not a passage shown"):
        label.passage_ids("9", items[0].ids)
    with pytest.raises(ValueError, match="not a passage shown"):
        label.passage_ids("B-PWD@1.0/9.9/1", items[0].ids)
    with pytest.raises(ValueError, match="named twice"):
        label.passage_ids(f"1, {items[0].ids[0]}", items[0].ids)
    assert label.passage_ids(" none ", items[0].ids) == []
    answers = answers_for(items)
    answers[2:2] = ["99"]
    _, screen = session(root, folder, answers)
    assert "'99' is not a passage shown" in screen
    row = calibration.read_jsonl(folder / calibration.LABELS)[0]
    edited = {**row, "passage_ids": ["X@1.0/1/1"]}
    problems = calibration.label_problems(
        edited, items[0].item, items[0].answer, items[0].ids, "judge-v2"
    )
    assert any("were not shown" in p for p in problems)


def test_it_resumes_redoes_and_seals_and_refuses_any_change_after_the_seal(tmp_path):
    root, folder, _, _ = sampled_root(tmp_path)
    items = shown(root, folder)
    answers = answers_for(items)
    code, screen = session(root, folder, [*answers[:5], "q"])  # one item, then stop
    assert code == 0
    assert "stopped at item 2: 1 of" in screen
    with pytest.raises(CalibrationError, match="have no label yet"):
        session(root, folder, [], seal=True)
    session(root, folder, answers[5:])
    assert len(calibration.read_jsonl(folder / calibration.LABELS)) == len(items)
    session(root, folder, ["f", items[0].answer.split()[0], "", "Changed my mind.", "y"], redo=1)
    first = calibration.read_jsonl(folder / calibration.LABELS)[0]
    assert (first["verdict"], first["ambiguous"]) == ("fail", True)
    code, screen = session(root, folder, [], seal=True, clock=lambda: SEALED)
    assert code == 0
    seal = json.loads((folder / calibration.LABELS_SEAL).read_text())
    assert seal == {
        "file": calibration.LABELS,
        "sha256": calibration.sha256_file(folder / calibration.LABELS),
        "lines": len(items),
        "sealed_at": "2026-10-24T09:00:00Z",
    }
    for kwargs in ({}, {"redo": 1}, {"seal": True}):
        with pytest.raises(CalibrationError, match="nothing changes after the seal"):
            session(root, folder, answers, **kwargs)
    path = folder / calibration.LABELS
    path.write_text(path.read_text().replace('"verdict": "fail"', '"verdict": "pass"', 1))
    with pytest.raises(CalibrationError, match="changed after its seal"):
        session(root, folder, answers)
    with pytest.raises(CalibrationError, match="changed after its seal"):
        calibration.read_inputs(root, folder)


def sealed(tmp_path):
    root, folder, run_id, _ = sampled_root(tmp_path)
    items = shown(root, folder)
    session(root, folder, answers_for(items))
    session(root, folder, [], seal=True, clock=lambda: SEALED)
    return root, folder, run_id, items


def test_the_relabel_opens_a_day_after_the_seal(tmp_path):
    root, folder, _, _ = sealed(tmp_path)
    early = SEALED + timedelta(hours=23, minutes=59)
    with pytest.raises(CalibrationError, match="opens 24 hours after the labels' seal"):
        session(root, folder, [], relabel=True, clock=lambda: early)
    relabels = shown(root, folder, relabel=True)
    assert len(relabels) == 2  # the test bar: one per criterion
    code, _ = session(
        root, folder, answers_for(relabels), relabel=True, clock=ticking(SEALED + timedelta(days=1))
    )
    assert code == 0
    assert len(calibration.read_jsonl(folder / calibration.RELABELS)) == 2


def test_the_relabel_shows_neither_the_first_labels_nor_the_judges_fields(tmp_path):
    """JC7's blindness test: the first labels' reasons and the judge's never reach the screen."""
    root, folder, _, items = sealed(tmp_path)
    reasons = {str(r["reason"]) for r in calibration.read_jsonl(folder / calibration.LABELS)}
    assert reasons == {"Labelled pass."}  # the first labels, sealed
    relabels = shown(root, folder, relabel=True)
    _, screen = session(
        root, folder, answers_for(relabels), relabel=True, clock=ticking(SEALED + timedelta(days=1))
    )
    assert "Labelled pass." not in screen
    assert REASON not in screen
    assert "Re-label item 1 of 2" in screen
    keys = {s.item.key for s in items}
    assert {s.item.key for s in relabels} <= keys


def test_the_relabel_items_are_seeded_per_criterion_in_a_new_order(tmp_path):
    _, folder, _, _ = sampled_root(tmp_path)
    sample = calibration.read_sample(folder)
    bar = calibration.load_bar(folder)
    first = calibration.relabel_items(sample, bar)
    assert first == calibration.relabel_items(sample, bar)
    assert [i.order for i in first] == [1, 2]
    assert sorted(i.criterion for i in first) == ["abstains", "grounded"]


def test_the_label_command_refuses_a_folder_without_a_sample(tmp_path, capsys):
    (tmp_path / "empty").mkdir()
    code = main(["label", "--folder", "empty", "--root", str(tmp_path)])
    assert code == 1
    assert "label refused" in capsys.readouterr().err
