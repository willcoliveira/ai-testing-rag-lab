"""S4b GV6: the seeded, stratified split of golden set v2's new cases (scripts/split_golden.py),
committed before any v2 case existed. The rule is held on small files built here, and the
committed v2 file is split again, with its new cases' splits taken out, and compared: a split set
by hand fails, naming the case."""

import json
import random
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from tests.conftest import ROOT, load_script

pytestmark = pytest.mark.unit
V1 = ROOT / "datasets" / "golden.v1.jsonl"
V2 = ROOT / "datasets" / "golden.v2.jsonl"


@pytest.fixture(scope="module")
def script() -> ModuleType:
    return load_script("split_golden")


def case(case_id: str, mix: str, expected: str, tenant: str = "tenant-a") -> dict[str, Any]:
    """A new case as the question author writes it: no split."""
    return {
        "id": case_id,
        "kind": "behaviour",
        "tenant": tenant,
        "question": f"Placeholder question of {case_id}?",
        "mix": mix,
        "expected": expected,
        "feature_ids": ["F-01"],
        "reference_answer": None if expected == "abstain" else "A placeholder.",
        "relevant": [],
        "origin": "synthetic",
    }


BASE = [
    {"id": "G-01", "kind": "behaviour", "tenant": "tenant-a", "question": "Old one?",
     "split": "test", "mix": "single-chunk", "expected": "answer"},
    {"id": "R-Q01", "kind": "retrieval", "tenant": "tenant-a", "question": "Old two?",
     "split": "dev", "relevant": []},
]  # fmt: skip
NEW = [
    # a stratum of four: split on its own, one to test (round(4 / 3) = 1)
    case("G-38", "single-chunk", "answer"),
    case("G-39", "single-chunk", "answer"),
    case("G-100", "single-chunk", "answer"),
    case("G-41", "single-chunk", "answer"),
    # three strata of one or two cases labelled answer: one pool of three, one to test
    case("G-42", "multi-chunk", "answer"),
    case("G-43", "paraphrase", "answer", "tenant-b"),
    case("G-44", "misspelling", "answer", "tenant-b"),  # the same slot as G-43
    # a stratum of two abstain cases: the label's only pool, one to test (round(2 / 3) = 1)
    case("G-45", "unanswerable", "abstain", "tenant-b"),
    case("G-46", "unanswerable", "abstain", "tenant-b"),
    # a stratum of five refusals: two to test
    *(case(f"G-{n}", "single-chunk", "refuse-and-help") for n in range(47, 52)),
]


def lines_of(rows: Sequence[dict[str, Any]]) -> list[str]:
    return [json.dumps(row) for row in rows]


def base_ids() -> frozenset[str]:
    return frozenset(str(row["id"]) for row in BASE)


def test_the_rule_strata_pools_and_one_third_to_test(script):
    out, drawn = script.split(lines_of([*BASE, *NEW]), base_ids())
    by_name = {unit.name: unit for unit in drawn}
    assert list(by_name) == [
        "single-chunk / answer / tenant-a",
        "single-chunk / refuse-and-help / tenant-a",
        "pool of abstain",
        "pool of answer",
    ]
    assert by_name["single-chunk / answer / tenant-a"].ids == ("G-38", "G-39", "G-41", "G-100")
    assert by_name["pool of answer"].ids == ("G-42", "G-43", "G-44")
    assert by_name["pool of abstain"].ids == ("G-45", "G-46")
    assert [len(unit.test) for unit in drawn] == [1, 2, 1, 1]
    for unit in drawn:
        assert len(unit.test) == round(len(unit.ids) / 3)
        assert set(unit.test) <= set(unit.ids)
    rows = [json.loads(line) for line in out]
    test = {str(row["id"]) for row in rows[len(BASE) :] if row["split"] == "test"}
    assert test == {case_id for unit in drawn for case_id in unit.test}


def test_the_draw_is_the_seeds_shuffle_of_the_ids_sorted_by_number(script):
    """The draw, computed again here: one random.Random(20261023) over the units in their order,
    each unit's ids sorted by number, shuffled, the first round(n / 3) to test."""
    assert script.SEED == 20261023
    _, drawn = script.split(lines_of([*BASE, *NEW]), base_ids())
    rng = random.Random(20261023)  # noqa: S311
    for unit in drawn:
        shuffled = list(unit.ids)
        rng.shuffle(shuffled)
        assert unit.test == tuple(shuffled[: round(len(shuffled) / 3)]), unit.name


def test_the_base_lines_and_every_other_field_are_kept(script):
    lines = lines_of([*BASE, *NEW])
    out, _ = script.split(lines, base_ids())
    assert out[: len(BASE)] == lines[: len(BASE)]  # byte for byte
    for before, after in zip(NEW, out[len(BASE) :], strict=True):
        row = json.loads(after)
        assert row["split"] in ("dev", "test")
        keys = list(row)
        assert keys[keys.index("question") + 1] == "split"  # where v1.1's lines have it
        assert {k: v for k, v in row.items() if k != "split"} == before
    assert script.split(lines, base_ids()) == script.split(lines, base_ids())  # seeded


def test_a_split_file_is_left_as_it_is(script, tmp_path, capsys):
    path = tmp_path / "golden.v2.jsonl"
    base = tmp_path / "golden.v1.jsonl"
    base.write_text("\n".join(lines_of(BASE)) + "\n", encoding="utf-8")
    path.write_text("\n".join(lines_of([*BASE, *NEW])) + "\n", encoding="utf-8")
    assert script.main(["--dataset", str(path), "--base", str(base)]) == 0
    first = path.read_bytes()
    out = capsys.readouterr().out
    assert "split_golden: 14 new cases, 9 dev and 5 test (seed 20261023)" in out
    assert "pool of answer: 3 case(s); test: " in out
    assert first.endswith(b"\n")
    assert script.main(["--dataset", str(path), "--base", str(base)]) == 0
    assert "has its split; nothing written" in capsys.readouterr().out
    assert path.read_bytes() == first


def without(row: dict[str, Any], *names: str, **changes: Any) -> dict[str, Any]:
    return {k: v for k, v in {**row, **changes}.items() if k not in names}


@pytest.mark.parametrize(
    ("rows", "message"),
    [
        ([*BASE, without(BASE[1], "split", id="R-Q09")], "only a new behaviour case is split"),
        ([without(BASE[0], "split")], "a line of the base file keeps its split"),
        ([*BASE, case("G-38", "single-chunk", "answer"), case("G-38", "multi-chunk", "answer")],
         "the id is used twice"),
        ([*BASE, case("g38", "single-chunk", "answer")], "an id is a prefix and a number"),
        ([*BASE, without(case("G-38", "single-chunk", "answer"), "mix")],
         "mix must be a non-empty string"),
    ],
)  # fmt: skip
def test_a_line_the_rule_cannot_split_is_refused(script, rows, message):
    with pytest.raises(script.SplitError, match=message):
        script.split(lines_of(rows), base_ids())


# ---------------------------------------------------------------- split again and compare


def unsplit(lines: Sequence[str], keep: frozenset[str]) -> list[str]:
    """Every line whose id is not in keep, with its split taken out."""
    out: list[str] = []
    for text in lines:
        row = json.loads(text)
        if row["id"] not in keep:
            row.pop("split")
        out.append(json.dumps(row, ensure_ascii=False))
    return out


def resplit_problems(script: ModuleType, lines: Sequence[str], keep: frozenset[str]) -> list[str]:
    """Each line the script does not give again: a new case whose split differs from the
    seeded rule's, or a line written otherwise."""
    again, _ = script.split(unsplit(lines, keep), keep)
    problems: list[str] = []
    for mine, theirs in zip(lines, again, strict=True):
        if mine != theirs:
            row, rule = json.loads(mine), json.loads(theirs)
            problems.append(
                f"{row['id']}: split {row.get('split')}, the seeded rule gives {rule['split']}"
                if row.get("split") != rule["split"]
                else f"{row['id']}: the line is not the script's"
            )
    return problems


def test_split_again_the_planted_file_gives_the_same_bytes(script):
    out, _ = script.split(lines_of([*BASE, *NEW]), base_ids())
    assert resplit_problems(script, out, base_ids()) == []


def test_a_split_set_by_hand_is_named(script):
    out, _ = script.split(lines_of([*BASE, *NEW]), base_ids())
    index = len(BASE)  # G-38
    row = json.loads(out[index])
    flipped = "dev" if row["split"] == "test" else "test"
    out[index] = out[index].replace(f'"split": "{row["split"]}"', f'"split": "{flipped}"')
    assert resplit_problems(script, out, base_ids()) == [
        f"G-38: split {flipped}, the seeded rule gives {row['split']}"
    ]


@pytest.mark.skipif(not V2.exists(), reason="golden.v2.jsonl lands at the integration of the cases")
def test_the_committed_v2_file_is_the_scripts_split_of_its_new_cases(script):
    """The plan: "The developer runs it once on the author's cases, and a test runs it again and
    compares." v1.1's ids keep their splits; every other line is split again."""
    lines = V2.read_text(encoding="utf-8").splitlines()
    assert resplit_problems(script, lines, script.ids_of(V1)) == []


def test_the_default_paths_are_v2_and_v1(script):
    assert (script.DATASET, script.BASE) == ("datasets/golden.v2.jsonl", "datasets/golden.v1.jsonl")
    assert Path(ROOT / script.BASE).is_file()
