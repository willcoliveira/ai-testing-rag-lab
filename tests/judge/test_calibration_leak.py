"""S6 JC9: labels never become judge examples, and never measure twice. No judge prompt version
holds a run of 8 or more words of a labelled item's answer, quote or reason (the longest shared
run reported); nothing under src/raglab/judge/ names the calibration; a later calibration's
sampler excludes every item of an earlier one."""

import re
from pathlib import Path

import pytest

from raglab.evals import calibration, judged_record
from tests.calibration_support import FOLDER, published_root
from tests.conftest import ROOT

pytestmark = pytest.mark.unit
PROMPTS = {v: calibration.prompt_text(v) for v in judged_record.PROMPTS}


def test_the_longest_shared_run_counts_words_by_hand():
    assert calibration.longest_shared_run("a b c d", "x b c d y") == 3
    assert calibration.longest_shared_run("The Company's rule, stated.", "the company's rule") == 3
    assert calibration.longest_shared_run("one two", "three four") == 0
    assert calibration.words("Don't say the company\u2019s") == [
        "don't",
        "say",
        "the",
        "company\u2019s",
    ]


def test_every_judge_prompt_version_is_read_whole():
    """The prompt text the leak test reads holds each version's system prompt and every rule."""
    for version, text in PROMPTS.items():
        prompt = judged_record.PROMPTS[version]
        assert prompt.SYSTEM in text
        for rule in prompt.RULES.values():
            assert rule.passes in text
            assert rule.fails in text


def test_a_labelled_sentence_pasted_into_a_prompt_is_found_naming_the_item():
    """JC9's break, in a fixture: a labelled reason pasted into a version's rules."""
    reason = "The answer gives five attempts a day, which no passage states anywhere at all."
    texts = [("c1 labels.jsonl item 7 (G-04 trial 2) reason", reason)]
    # by hand: "the answer gives" and "no passage states" are the rules' own phrases, 3 words
    assert calibration.leak_problems(texts, PROMPTS) == ([], 3)
    pasted = {**PROMPTS, "judge-v2": PROMPTS["judge-v2"] + "\n" + reason}
    problems, longest = calibration.leak_problems(texts, pasted)
    assert longest == len(calibration.words(reason))
    assert problems == [
        f"c1 labels.jsonl item 7 (G-04 trial 2) reason: {longest} consecutive words are in "
        "judge-v2's prompt"
    ]


@pytest.mark.parametrize(
    "folder",
    [f for f in calibration.calibrations(ROOT) if (f / calibration.LABELS).exists()],
    ids=lambda p: p.name,
)
def test_no_judge_prompt_version_holds_a_labelled_run_of_eight_words(folder):
    """The leak test on the repository: every committed calibration's labelled answers, quotes
    and reasons against every judge prompt version (none is labelled until the seal)."""
    problems, longest = calibration.leak_problems(calibration.labelled_texts(ROOT, folder), PROMPTS)
    assert problems == []
    assert longest < calibration.LEAK_RUN


def test_nothing_under_the_judge_package_names_the_calibration():
    """The path test: no judge module reads a calibration folder, a label file or the calibration
    and label modules, so no label can reach a judge prompt by code."""
    names = re.compile(r"calibration|labels?\.jsonl|relabels|raglab\.evals\.label", re.I)
    found = [
        f"{path.relative_to(ROOT)}:{n}"
        for path in sorted((ROOT / "src" / "raglab" / "judge").rglob("*.py"))
        for n, text in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if names.search(text)
    ]
    assert found == []
    config = (ROOT / "config" / "judge-local.toml").read_text(encoding="utf-8")
    assert not names.search(config)


def test_a_later_calibration_excludes_every_item_of_an_earlier_one(tmp_path):
    """The exclusion test: a second calibration of the same judged record draws none of the
    first's items, and its sample names the first, pinned by its sample's sha256."""
    root, run_id, _, _ = published_root(tmp_path)
    first = root / FOLDER
    second = root / "datasets" / "calibration" / "test-c2"
    second.mkdir()
    (second / calibration.BAR).write_text((first / calibration.BAR).read_text())
    a, _ = calibration.draw_sample(root, first, run_id)
    b, _ = calibration.draw_sample(root, second, run_id)
    assert {i.key for i in a.items}.isdisjoint({i.key for i in b.items})
    assert b.pins["excludes"] == [{"calibration": "test-c1", "sample_sha256": a.sha256}]
    assert a.pins["excludes"] == []
    assert calibration.redraw_problems(root, second) == []
    assert calibration.redraw_problems(root, first) == []  # the later one is not excluded from it
    path = first / calibration.SAMPLE
    path.write_text(path.read_text() + "\n")
    with pytest.raises(calibration.CalibrationError, match="changed since this one excluded it"):
        calibration.redraw_problems(root, second)


def test_the_committed_calibrations_never_share_an_item():
    folders = calibration.calibrations(ROOT)
    samples = {f.name: calibration.read_sample(f) for f in folders}
    for name, sample in samples.items():
        for other in [o for o in samples if o != name]:
            if any(p["calibration"] == other for p in sample.pins["excludes"]):  # type: ignore[union-attr]
                assert {i.key for i in sample.items}.isdisjoint(
                    {i.key for i in samples[other].items}
                )
    assert len({Path(f).name for f in folders}) == len(folders)
