"""The seeded, stratified split of golden set v2's new behaviour cases (S4b plan, "The split:
seeded, stratified, decided before any run"). Written and committed before any v2 case existed;
its second pass, the repair, was added after the first draw was seen (below).

Usage: uv run python scripts/split_golden.py [--dataset datasets/golden.v2.jsonl]
           [--base datasets/golden.v1.jsonl] [--root .]

The question author writes every new case without a `split` key (the plan's rule 10, "No split
while writing"); this script assigns the splits, once, and the developer commits the result.
tests/unit/test_split_golden.py runs it again on the committed file, with the new cases' splits
taken out, and compares.

The rule, as the plan states it, with the choices the plan leaves open written down here:

- **The new cases** are the lines with no `split` key. Each must be a behaviour case whose id is
  not a line of the base file (golden set v1.1, whose lines keep their splits). A line that has a
  split is kept byte for byte.
- **Strata:** (mix slot, expected label, tenant). The mix slot joins `paraphrase` and
  `misspelling` into "paraphrased or misspelled", as the build project's mix does.
- **Pools:** a stratum of one or two cases is pooled with its label's other strata of one or two
  cases, so each expected label has at most one pool, split as one stratum; a stratum of three or
  more is split on its own.
- **The draw:** one `random.Random(20261023)`. The units are taken in a fixed order: the strata
  of three or more sorted by (slot, label, tenant), then the pools sorted by label. In each unit
  the ids are sorted by their number (G-38 before G-100) and shuffled with that generator, and
  the first round(n / 3) go to test, the rest to dev. n / 3 is never a half, so no tie is rounded.
- **The repair, a second pass after the draw.** Added on 2026-10-24, after the first draw was
  seen, by the maintainer's answer to the labels judge's call C1, verbatim "Repair in the
  committed script (Recommended)" (the S4b ledger keeps the first draw's output): the draw had
  left every case of three first-feature kinds in test. For each first-feature kind (the kind, in
  corpus/answer-key.yaml, of a behaviour case's first feature) that has two or more behaviour
  cases in the whole file, v1.1's included, and none in dev, taken in the order of the kinds'
  names: (a) the kind's lowest-numbered new test case moves to dev; (b) among the new dev cases
  of that case's stratum, those whose own kind would still have a dev case in the whole file
  after they moved are eligible; they are sorted by number and shuffled with a fresh
  `random.Random(20261023)`, made once for the pass (the generator chosen and written down before
  the pass first ran), and the first moves to test. So each stratum keeps its count of test cases.
  A kind with no new case to move, or a stratum with no eligible case, stops the script, and
  nothing is written.
- **The file:** a new case's line is written again with `split` after `question`, where v1.1's
  lines have it (json.dumps with its default separators, non-ASCII text kept as it is).
"""

import argparse
import json
import random
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from raglab.ingest import answer_key

SEED = 20261023
DATASET = "datasets/golden.v2.jsonl"
BASE = "datasets/golden.v1.jsonl"
CASE_ID = re.compile(r"([A-Z]+)-(\d+)")
NEEDED = ("question", "mix", "expected", "tenant")

type Row = dict[str, object]


class SplitError(ValueError):
    """The file cannot be split by the rule; nothing is written."""


@dataclass(frozen=True)
class Unit:
    """A stratum of three or more new cases, or one label's pool of its strata of one or two."""

    name: str
    ids: tuple[str, ...]  # sorted by number
    test: tuple[str, ...]  # the first round(n / 3) of the shuffled ids


@dataclass(frozen=True)
class Repair:
    """One move of the second pass: a kind's new test case to dev, a case of its stratum to
    test."""

    kind: str
    to_dev: str
    to_test: str
    stratum: str


def slot(mix: str) -> str:
    return "paraphrased or misspelled" if mix in ("paraphrase", "misspelling") else mix


def stratum(row: Row) -> tuple[str, str, str]:
    return slot(str(row["mix"])), str(row["expected"]), str(row["tenant"])


def number(case_id: str) -> tuple[str, int]:
    """An id's sort key: its prefix and its number, so G-38 comes before G-100."""
    match = CASE_ID.fullmatch(case_id)
    if match is None:
        raise SplitError(f"{case_id}: an id is a prefix and a number, such as G-38")
    return match.group(1), int(match.group(2))


def parse(text: str, where: str) -> Row:
    try:
        raw: object = json.loads(text)
    except json.JSONDecodeError as error:
        raise SplitError(f"{where}: not JSON ({error.msg})") from error
    if not isinstance(raw, dict):
        raise SplitError(f"{where}: a line is a JSON object")
    return {str(k): v for k, v in cast(dict[object, object], raw).items()}


def field(row: Row, name: str, where: str) -> str:
    value = row.get(name)
    if not isinstance(value, str) or not value.strip():
        raise SplitError(f"{where}: {name} must be a non-empty string, got {value!r}")
    return value


def units(cases: Sequence[Row]) -> list[Unit]:
    """The strata and pools of the new cases, in the order of the draw, each drawn."""
    strata: dict[tuple[str, str, str], list[str]] = {}
    for row in cases:
        strata.setdefault(stratum(row), []).append(str(row["id"]))
    order: list[tuple[str, list[str]]] = []
    pools: dict[str, list[str]] = {}
    for key in sorted(strata):
        if len(strata[key]) >= 3:
            order.append((" / ".join(key), strata[key]))
        else:
            pools.setdefault(key[1], []).extend(strata[key])
    order += [(f"pool of {label}", pools[label]) for label in sorted(pools)]
    # a reproducible split, not a secret: the seeded generator is the point
    rng = random.Random(SEED)  # noqa: S311  # nosec B311
    drawn: list[Unit] = []
    for name, ids in order:
        ranked = sorted(ids, key=number)
        shuffled = list(ranked)
        rng.shuffle(shuffled)
        drawn.append(Unit(name, tuple(ranked), tuple(shuffled[: round(len(ranked) / 3)])))
    return drawn


def kind_of(row: Row, kinds: Mapping[str, str]) -> str:
    """The kind of a behaviour case's first feature."""
    features = row.get("feature_ids")
    if not isinstance(features, list) or not features:
        raise SplitError(f"{row['id']}: a behaviour case lists its feature ids")
    first = str(cast(list[object], features)[0])
    if first not in kinds:
        raise SplitError(f"{row['id']}: feature {first} is not in the answer key")
    return kinds[first]


def repair(
    cases: Sequence[Row], splits: dict[str, str], new: frozenset[str], kinds: Mapping[str, str]
) -> list[Repair]:
    """The second pass (see the module docstring): splits, every behaviour case's split by id
    after the draw, is changed in place, and each move is returned."""
    by_kind: dict[str, list[Row]] = {}
    for row in cases:
        by_kind.setdefault(kind_of(row, kinds), []).append(row)
    # the pass's own generator, made once: chosen and written down before the pass first ran
    rng = random.Random(SEED)  # noqa: S311  # nosec B311
    moves: list[Repair] = []
    for kind in sorted(by_kind):
        rows = by_kind[kind]
        if len(rows) < 2 or any(splits[str(r["id"])] == "dev" for r in rows):
            continue
        movable = sorted((str(r["id"]) for r in rows if r["id"] in new), key=number)
        if not movable:
            raise SplitError(f"the {kind} kind has no dev case and no new case to move")
        moved = next(r for r in rows if r["id"] == movable[0])
        splits[movable[0]] = "dev"
        dev = {k: sum(splits[str(r["id"])] == "dev" for r in v) for k, v in by_kind.items()}
        eligible = sorted(
            (
                str(r["id"])
                for r in cases
                if r["id"] in new
                and splits[str(r["id"])] == "dev"
                and stratum(r) == stratum(moved)
                and dev[kind_of(r, kinds)] >= 2
            ),
            key=number,
        )
        name = " / ".join(stratum(moved))
        if not eligible:
            raise SplitError(f"no case of {name} can move to test for the {kind} kind's move")
        rng.shuffle(eligible)
        splits[eligible[0]] = "test"
        moves.append(Repair(kind, movable[0], eligible[0], name))
    return moves


def with_split(row: Row, split: str) -> str:
    """The case's line with `split` after `question`."""
    out: Row = {}
    for key, value in row.items():
        out[key] = value
        if key == "question":
            out["split"] = split
    return json.dumps(out, ensure_ascii=False)


def split(
    lines: Sequence[str], base_ids: frozenset[str], kinds: Mapping[str, str]
) -> tuple[list[str], list[Unit], list[Repair]]:
    """The lines with every new case given its split, the units drawn (none when every line has
    its split) and the second pass's moves; kinds maps each feature id to its kind."""
    new: list[tuple[int, Row]] = []
    cases: list[Row] = []  # every behaviour case, for the second pass
    seen: set[str] = set()
    for index, text in enumerate(lines):
        if not text.strip():
            continue
        where = f"line {index + 1}"
        row = parse(text, where)
        case_id = field(row, "id", where)
        if case_id in seen:
            raise SplitError(f"{where} ({case_id}): the id is used twice")
        seen.add(case_id)
        if row.get("kind") == "behaviour":
            cases.append(row)
        if "split" in row:
            continue
        where = f"{where} ({case_id})"
        if field(row, "kind", where) != "behaviour":
            raise SplitError(f"{where}: only a new behaviour case is split here")
        if case_id in base_ids:
            raise SplitError(f"{where}: a line of the base file keeps its split")
        for name in NEEDED:
            field(row, name, where)
        number(case_id)
        new.append((index, row))
    if not new:
        return list(lines), [], []
    drawn = units([row for _, row in new])
    test = {case_id for unit in drawn for case_id in unit.test}
    splits = {
        str(row["id"]): str(row["split"])
        if "split" in row
        else "test"
        if row["id"] in test
        else "dev"
        for row in cases
    }
    moves = repair(cases, splits, frozenset(str(row["id"]) for _, row in new), kinds)
    out = list(lines)
    for index, row in new:
        out[index] = with_split(row, splits[str(row["id"])])
    return out, drawn, moves


def feature_kinds(root: Path) -> dict[str, str]:
    """Each feature id's kind, from the answer key under root."""
    return {f.id: f.kind for f in answer_key.features(root).values()}


def ids_of(path: Path) -> frozenset[str]:
    """The ids of a golden file's lines."""
    found: set[str] = set()
    for n, text in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if text.strip():
            found.add(field(parse(text, f"{path.name}:{n}"), "id", f"{path.name}:{n}"))
    return frozenset(found)


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description="The seeded split of golden set v2's new cases.")
    parser.add_argument("--dataset", type=Path, default=Path(DATASET), help="file to split")
    parser.add_argument("--base", type=Path, default=Path(BASE), help="lines that keep their split")
    parser.add_argument("--root", type=Path, default=Path(), help="repo root, for the answer key")
    args = parser.parse_args(argv)
    dataset: Path = args.dataset
    try:
        text = dataset.read_text(encoding="utf-8")
        lines, drawn, moves = split(text.splitlines(), ids_of(args.base), feature_kinds(args.root))
    except (OSError, ValueError) as error:  # SplitError, or an answer key that cannot be read
        print(f"split_golden: {error}", file=sys.stderr)
        return 1
    if not drawn:
        print(f"split_golden: every line of {dataset} has its split; nothing written")
        return 0
    dataset.write_text("\n".join(lines) + ("\n" if text.endswith("\n") else ""), encoding="utf-8")
    for unit in drawn:
        print(f"{unit.name}: {len(unit.ids)} case(s); test: {', '.join(unit.test) or 'none'}")
    for move in moves:
        print(f"repair, {move.kind}: {move.to_dev} to dev; {move.to_test} to test ({move.stratum})")
    total = sum(len(unit.ids) for unit in drawn)
    tested = sum(len(unit.test) for unit in drawn)
    print(f"split_golden: {total} new cases, {total - tested} dev and {tested} test (seed {SEED})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
