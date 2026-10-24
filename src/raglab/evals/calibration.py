"""Judge calibration (S6, docs/plans/2026-10-23-s6-judge-calibration.md): the judge's verdicts set
against the maintainer's blind labels, as how-to 05, "Calibrate the evaluator", describes.

A calibration is one folder under datasets/calibration/ (the first, `judge-v2-c1`), whose files are
written in this order, each pinning what came before it:

1. **The bar**, `bar.toml` (`load_bar`), by hand, before the sample: per calibrated criterion the
   items by the judge's verdict and the bar's two lines; what the bar reads (Cohen's kappa of the
   judge against the sealed labels, the point estimate); the sample's rule and seed; the
   bootstrap; the re-label.
2. **The sample**, `sample.jsonl` (`draw_sample`), drawn once from a published judged record by
   rule s6-1 (`draw`). Its first line holds the pins: the judged record's id and manifest sha256,
   the source run's id, the bar's sha256, the judge prompt and the judge's seed, the seed and the
   rule, the earlier calibrations it excludes (each with its sample's sha256), any shortfall, and
   the time. Then one line per item: its order, case id, trial and criterion, and nothing else, so
   the file shows neither a verdict nor a stratum.
3. **The labels**, `labels.jsonl`, written by `raglab label` (raglab.evals.label) in the judge's
   schema (`LABEL_FIELDS`), and their seal, `labels.seal.json` (`seal`): the file's sha256 and
   time. After the seal nothing changes. The re-label (D3), `relabels.jsonl` and its seal, holds
   12 of the items (`relabel_items`), labelled at least a day after the labels' seal.
4. **The disagreements**, `disagreements.jsonl`: each item where the judge's verdict and the
   sealed label differ, with its class (`CLASSES`) and the maintainer's answer, verbatim.
5. **The record**, `record.json` and `record.md` (`build_record`, `render_record`), generated from
   the files above and the judged record, never edited by hand (`record_problems` regenerates and
   compares).

**Rule s6-1, the draw.** The frame is the judged record's first-pass verdicts (`verdicts`, never
`repeat` or `reversed`) on the bar's criteria with status ok and a verdict of pass or fail; an item
of an earlier calibration is excluded (never measured twice). The strata are the criterion and the
judge's verdict. Within a stratum, the verdicts are sorted by case id and trial, then shuffled with
`random.Random("<seed>:<criterion>:<verdict>")` (a stream of its own, so one stratum's size never
moves another's draw), and taken in that order: an answer (case and trial) already in the sample
is skipped, and so is a case that has already given an item in that stratum, until every case of
the stratum has given one; then second items, in the same order, one more per case each round. The
criteria are drawn in the bar's order, each its judge passes first, then its judge fails. A stratum
smaller than its allocation gives all it has, and the rest of the criterion's items come from its
other stratum, continuing by the same rule; the sample says so (`shortfall`). The labelling order
groups the items by criterion, in the bar's order, and shuffles each criterion's items (sorted by
case id and trial first) with `random.Random("<seed>:order:<criterion>")`.

**The agreement** (per calibrated criterion, and pooled over them), on the sealed labels only: the
confusion table of the judge's verdict and the label in sample counts, raw agreement and Cohen's
kappa, `(po - pe) / (1 - pe)`, undefined when `pe` is 1. TPR is the share of the answers the label
passes that the judge passes, TNR the share of those it fails that the judge fails; since the sample
is stratified by the judge's verdict, each item is weighted by its stratum's frame size over its
sample size, and the unweighted shares are shown beside. The point estimates are exact fractions,
so a bar line is compared without rounding. The intervals are 95% percentile intervals (type 7, as
`raglab compare`) from a bootstrap within strata: each resample draws each stratum's own number of
items from it with replacement, strata in the bar's order (judge passes, then fails); each scope (a
criterion, then pooled) draws its resamples from a stream of its own,
`random.Random(<agreement seed>)`; a resample whose statistic is undefined is counted and reported,
never imputed. Beside them: the judged record's repeatability and order agreement on the
same criteria; the re-label's agreement with the labels (D3); the corrections after the verdicts
were seen (a "human error"), reported and never read by the bar.

**The refusals**: a bar that changed since the sample pinned it; a judged record whose manifest
changed since (a verdict flipped together with its reply and resealed changes the manifest's file
hashes, so its sha256), or one that no longer validates; labels that differ from their seal, that
are not the sample's items in its order, whose shown answer's sha256 is not the judged line's, or
whose quote or passage ids do not follow from what was shown; a re-label inside its gap or off its
seal; a disagreement without a class, or a class on an item that is not a disagreement.
"""

import hashlib
import json
import random
import re
import shutil
import subprocess  # nosec B404
import tomllib
from collections import Counter
from collections.abc import Callable, Iterator, Mapping, Sequence, Set
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from fractions import Fraction
from pathlib import Path
from typing import cast

from raglab.core.types import CRITERIA, Status
from raglab.evals import judged_record, metrics, record

type Json = dict[str, object]
type Key = tuple[str, int, str]  # case id, trial, criterion
type Answer = tuple[str, int]  # case id, trial
type Stratum = tuple[str, str]  # criterion, the judge's verdict

FOLDER = "datasets/calibration"
PUBLISHED = "runs/published"
BAR = "bar.toml"
SAMPLE = "sample.jsonl"
LABELS = "labels.jsonl"
LABELS_SEAL = "labels.seal.json"
RELABELS = "relabels.jsonl"
RELABELS_SEAL = "relabels.seal.json"
DISAGREEMENTS = "disagreements.jsonl"
RECORD_JSON = "record.json"
RECORD_MD = "record.md"
RULE = "s6-1"
RECORD_VERSION = "calibration-record.v1"
SIDES = ("pass", "fail")  # a sampled verdict's and a label's two sides
TRUSTED, REPORTED, NOT_TRUSTED = "trusted", "reported only", "not trusted"
STATUSES = (TRUSTED, REPORTED, NOT_TRUSTED)
# how-to 05 step 5: the four causes of a disagreement
CLASSES = ("criterion badly written", "judge prompt unclear", "human error", "genuine ambiguity")
HUMAN_ERROR = "human error"
TIME = "%Y-%m-%dT%H:%M:%SZ"
PIN_FIELDS = (
    "calibration",
    "rule",
    "seed",
    "bar_sha256",
    "judged_run",
    "judged_manifest_sha256",
    "source_run",
    "judge_prompt",
    "judge_seed",
    "excludes",
    "shortfall",
    "drawn_at",
)
ITEM_FIELDS = ("order", "case_id", "trial", "criterion")
LABEL_FIELDS = (
    *ITEM_FIELDS,
    "verdict",
    "answer_quote",
    "passage_ids",
    "reason",
    "ambiguous",
    "answer_sha256",
    "labelled_at",
    "seconds",
)
SEAL_FIELDS = ("file", "sha256", "lines", "sealed_at")
DISAGREEMENT_FIELDS = (*ITEM_FIELDS, "class", "answer")
# the single-labeller caveat (D3), which every record of one labeller carries
CAVEAT = (
    "one labeller, who also wrote the criteria and signed off the golden set: how-to 05's "
    "agreement between two people is not measured, so whether the judge agrees with a person less "
    "than two people agree with each other cannot be checked; the re-label is a floor on the "
    "labeller's own noise, an optimistic one, not agreement between two people"
)
TRIGGERS = (
    "a change of the judge's model, digest or prompt version; a change of docs/CRITERIA.md or of "
    "the canary set; a new golden set version; S8's drift alert on a judged pass rate; the gate "
    "map's manual calibration re-run before each release"
)
INTEGRITY = (
    "a published judged record's integrity rests on the reviewed commit that publishes it: its "
    "checks hold each verdict to its reply, not the reply to the judge (AV2-J3), and this record "
    "pins the judged record's manifest sha256, so a verdict changed after the pin is refused"
)


class CalibrationError(ValueError):
    """A calibration file is missing, malformed, or no longer what an input pinned."""


def _obj(value: object) -> Json:
    if not isinstance(value, dict):
        raise CalibrationError(f"expected a JSON object, got {type(value).__name__}")
    return {str(k): v for k, v in cast(dict[object, object], value).items()}


def _list(value: object) -> list[object]:
    if not isinstance(value, list):
        raise CalibrationError(f"expected a JSON array, got {type(value).__name__}")
    return list(cast(list[object], value))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stamp(when: datetime) -> str:
    return when.astimezone(UTC).strftime(TIME)


def parse_time(text: str, where: str) -> datetime:
    try:
        return datetime.strptime(text, TIME).replace(tzinfo=UTC)
    except ValueError as error:
        raise CalibrationError(
            f"{where}: {text!r} is not a time like 2026-10-24T09:00:00Z"
        ) from error


def _rng(seed: int, *parts: str) -> random.Random:
    # a seeded shuffle for a reproducible draw, not a secret
    return random.Random(":".join([str(seed), *parts]))  # noqa: S311  # nosec B311


# ---------------------------------------------------------------- the bar


@dataclass(frozen=True)
class CriterionBar:
    """One calibrated criterion: its items by the judge's verdict, and the bar's two lines."""

    name: str
    judge_pass: int
    judge_fail: int
    trusted: Fraction
    stop: Fraction

    @property
    def items(self) -> int:
        return self.judge_pass + self.judge_fail

    def wanted(self, side: str) -> int:
        return self.judge_pass if side == "pass" else self.judge_fail


@dataclass(frozen=True)
class Bar:
    name: str
    judge_prompt: str
    reads: str
    undefined: str
    rule: str
    seed: int
    resamples: int
    level: float
    agreement_seed: int
    relabel_per_criterion: int
    relabel_gap_hours: float
    criteria: tuple[CriterionBar, ...]
    sha256: str

    def criterion(self, name: str) -> CriterionBar:
        for c in self.criteria:
            if c.name == name:
                return c
        raise CalibrationError(f"{name} is not a criterion of the bar {self.name}")

    def status(self, name: str, kappa: Fraction | None) -> str:
        """The bar's status of a criterion with this kappa (the point estimate, exact)."""
        c = self.criterion(name)
        if kappa is None:
            return self.undefined
        if kappa >= c.trusted:
            return TRUSTED
        return REPORTED if kappa >= c.stop else NOT_TRUSTED


def _table(data: Mapping[str, object], name: str, keys: Set[str], where: str) -> dict[str, object]:
    table = data.get(name)
    if not isinstance(table, dict):
        raise CalibrationError(f"{where}: [{name}] is missing")
    found = {str(k): v for k, v in cast(dict[object, object], table).items()}
    if unknown := sorted(set(found) - keys):
        raise CalibrationError(f"{where}: [{name}] has unknown keys {unknown}")
    if missing := sorted(keys - set(found)):
        raise CalibrationError(f"{where}: [{name}] is missing {missing}")
    return found


def _int(value: object, where: str, low: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < low:
        raise CalibrationError(f"{where} must be a whole number of at least {low}")
    return value


def _number(value: object, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise CalibrationError(f"{where} must be a number")
    return float(value)


def load_bar(folder: Path) -> Bar:
    """The calibration's bar.toml, read strictly: an unknown or missing key refuses it."""
    path = folder / BAR
    where = str(path)
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise CalibrationError(f"{where}: the bar is missing ({error})") from error
    data: dict[str, object] = tomllib.loads(raw.decode("utf-8"))
    top = {"name", "judge_prompt", "reads", "undefined", "sample", "agreement", "relabel"}
    top.add("criteria")
    if unknown := sorted(set(data) - top):
        raise CalibrationError(f"{where}: unknown keys {unknown}")
    if missing := sorted(top - set(data)):
        raise CalibrationError(f"{where}: missing {missing}")
    sample = _table(data, "sample", {"rule", "seed"}, where)
    agreement = _table(data, "agreement", {"resamples", "level", "seed"}, where)
    relabel = _table(data, "relabel", {"per_criterion", "min_gap_hours"}, where)
    if data["reads"] != "kappa":
        raise CalibrationError(f"{where}: the bar reads kappa, not {data['reads']!r}")
    if data["undefined"] not in STATUSES or data["undefined"] == TRUSTED:
        raise CalibrationError(f"{where}: an undefined kappa is reported only or not trusted")
    if sample["rule"] != RULE:
        raise CalibrationError(f"{where}: the sample's rule is {RULE}, not {sample['rule']!r}")
    if data["judge_prompt"] not in judged_record.PROMPTS:
        raise CalibrationError(f"{where}: no judge prompt {data['judge_prompt']!r}")
    level = _number(agreement["level"], f"{where}: agreement.level")
    if not 0 < level < 1:
        raise CalibrationError(f"{where}: agreement.level must be in (0, 1)")
    table = data["criteria"]
    if not isinstance(table, dict) or not table:
        raise CalibrationError(f"{where}: [criteria] names at least one criterion")
    rows = cast(dict[str, object], table)
    criteria: list[CriterionBar] = []
    for name in rows:
        if name not in CRITERIA:
            raise CalibrationError(f"{where}: {name!r} is not a criterion of docs/CRITERIA.md")
        row = _table(
            rows, name, {"judge_pass", "judge_fail", "trusted", "stop"}, f"{where}: criteria"
        )
        trusted = Fraction(str(_number(row["trusted"], f"{where}: {name}.trusted")))
        stop = Fraction(str(_number(row["stop"], f"{where}: {name}.stop")))
        if not -1 < stop < trusted <= 1:
            raise CalibrationError(f"{where}: {name} needs -1 < stop < trusted <= 1")
        bar_row = CriterionBar(
            name,
            _int(row["judge_pass"], f"{where}: {name}.judge_pass"),
            _int(row["judge_fail"], f"{where}: {name}.judge_fail"),
            trusted,
            stop,
        )
        if bar_row.items < 1:
            raise CalibrationError(f"{where}: {name} needs at least one item")
        criteria.append(bar_row)
    return Bar(
        name=str(data["name"]),
        judge_prompt=str(data["judge_prompt"]),
        reads=str(data["reads"]),
        undefined=str(data["undefined"]),
        rule=str(sample["rule"]),
        seed=_int(sample["seed"], f"{where}: sample.seed"),
        resamples=_int(agreement["resamples"], f"{where}: agreement.resamples", 1),
        level=level,
        agreement_seed=_int(agreement["seed"], f"{where}: agreement.seed"),
        relabel_per_criterion=_int(relabel["per_criterion"], f"{where}: relabel.per_criterion"),
        relabel_gap_hours=_number(relabel["min_gap_hours"], f"{where}: relabel.min_gap_hours"),
        criteria=tuple(criteria),
        sha256=hashlib.sha256(raw).hexdigest(),
    )


# ---------------------------------------------------------------- the sample: rule s6-1


@dataclass(frozen=True)
class Item:
    """One verdict to label: an answer (a case and trial) on one criterion, at its order."""

    order: int
    case_id: str
    trial: int
    criterion: str

    @property
    def key(self) -> Key:
        return (self.case_id, self.trial, self.criterion)

    def as_json(self) -> Json:
        return {
            "order": self.order,
            "case_id": self.case_id,
            "trial": self.trial,
            "criterion": self.criterion,
        }


@dataclass(frozen=True)
class Sample:
    pins: Json
    items: tuple[Item, ...]
    sha256: str


@dataclass(frozen=True)
class Drawn:
    """A draw's items in their labelling order, its shortfall, and (aggregate only, never written
    to the sample) each stratum's frame size and number drawn."""

    items: tuple[Item, ...]
    shortfall: tuple[Json, ...]
    frame: dict[Stratum, int]
    drawn: dict[Stratum, int]


def frame(
    lines: Sequence[Json], criteria: Sequence[str], excluded: Set[Key] = frozenset()
) -> dict[Stratum, list[Answer]]:
    """Each stratum's answers, sorted by case id and trial: the first-pass verdicts on the given
    criteria with status ok and a verdict of pass or fail, less the excluded items."""
    strata: dict[Stratum, list[Answer]] = {(c, side): [] for c in criteria for side in SIDES}
    for line in lines:
        verdicts = _obj(line.get("verdicts") or {})
        for criterion in criteria:
            if criterion not in verdicts:
                continue
            verdict = _obj(verdicts[criterion])
            if verdict["status"] != Status.OK.value or verdict["verdict"] not in SIDES:
                continue
            answer = (str(line["case_id"]), cast(int, line["trial"]))
            if (*answer, criterion) in excluded:
                continue
            strata[(criterion, str(verdict["verdict"]))].append(answer)
    for answers in strata.values():
        answers.sort()
    return strata


class _Taker:
    """One stratum's answers in the rule's order, and the cases it has given so far."""

    def __init__(self, order: list[Answer]) -> None:
        self.order = order
        self.per_case: Counter[str] = Counter()
        self.rounds = max(Counter(case for case, _ in order).values(), default=0)

    def take(self, wanted: int, in_sample: set[Answer]) -> list[Answer]:
        """Up to `wanted` more answers: one per case each round, skipping answers already in the
        sample (any criterion's)."""
        got: list[Answer] = []
        for round_ in range(1, self.rounds + 1):
            this_round: set[str] = set()
            for answer in self.order:
                if len(got) >= wanted:
                    return got
                case = answer[0]
                if answer in in_sample or case in this_round or self.per_case[case] >= round_:
                    continue
                got.append(answer)
                in_sample.add(answer)
                this_round.add(case)
                self.per_case[case] += 1
        return got


def draw(lines: Sequence[Json], bar: Bar, excluded: Set[Key] = frozenset()) -> Drawn:
    """Rule s6-1 over a judged record's lines (the module's docstring)."""
    strata = frame(lines, [c.name for c in bar.criteria], excluded)
    in_sample: set[Answer] = set()
    shortfall: list[Json] = []
    drawn: dict[Stratum, int] = {}
    items: list[Item] = []
    for c in bar.criteria:
        takers: dict[str, _Taker] = {}
        for side in SIDES:
            order = list(strata[(c.name, side)])
            _rng(bar.seed, c.name, side).shuffle(order)
            takers[side] = _Taker(order)
        got = {side: takers[side].take(c.wanted(side), in_sample) for side in SIDES}
        for side, other in (("pass", "fail"), ("fail", "pass")):
            short = c.wanted(side) - len(got[side])
            if short > 0:
                more = takers[other].take(short, in_sample)
                shortfall.append(
                    {
                        "criterion": c.name,
                        "stratum": f"judge {side}",
                        "wanted": c.wanted(side),
                        "drawn": len(got[side]),
                        "from_other_stratum": len(more),
                    }
                )
                got[other] += more
        for side in SIDES:
            drawn[(c.name, side)] = len(got[side])
        answers = sorted(got["pass"] + got["fail"])
        _rng(bar.seed, "order", c.name).shuffle(answers)
        items += [
            Item(len(items) + n, case, trial, c.name) for n, (case, trial) in enumerate(answers, 1)
        ]
    return Drawn(
        tuple(items),
        tuple(shortfall),
        {k: len(v) for k, v in strata.items()},
        drawn,
    )


def sample_text(pins: Json, items: Sequence[Item]) -> str:
    head = json.dumps({"pins": pins}, ensure_ascii=False)
    return head + "\n" + "".join(json.dumps(i.as_json(), ensure_ascii=False) + "\n" for i in items)


def read_sample(folder: Path) -> Sample:
    """A calibration's sample.jsonl, read strictly: the pins, then the items, numbered from 1 in
    order, each with exactly its order, case id, trial and criterion."""
    path = folder / SAMPLE
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise CalibrationError(
            f"{folder.name}: no sample has been drawn ({SAMPLE} is missing): raglab calibrate "
            "sample draws it from the published judged record"
        ) from error
    rows = [line for line in raw.decode("utf-8").splitlines() if line.strip()]
    if not rows:
        raise CalibrationError(f"{path}: empty")
    head = _obj(json.loads(rows[0]))
    if list(head) != ["pins"]:
        raise CalibrationError(f"{path}: the first line holds the pins only")
    pins = _obj(head["pins"])
    if sorted(pins) != sorted(PIN_FIELDS):
        raise CalibrationError(f"{path}: the pins are {sorted(pins)}, not {sorted(PIN_FIELDS)}")
    items: list[Item] = []
    for number, text in enumerate(rows[1:], start=1):
        row = _obj(json.loads(text))
        if list(row) != list(ITEM_FIELDS):
            raise CalibrationError(
                f"{path}: item {number} has the fields {list(row)}, only {list(ITEM_FIELDS)}"
            )
        if row["order"] != number:
            raise CalibrationError(f"{path}: item {number} has order {row['order']}")
        trial = row["trial"]
        if not isinstance(trial, int) or isinstance(trial, bool):
            raise CalibrationError(f"{path}: item {number}'s trial is not a whole number")
        if row["criterion"] not in CRITERIA:
            raise CalibrationError(f"{path}: item {number}'s criterion is not a criterion")
        items.append(Item(number, str(row["case_id"]), trial, str(row["criterion"])))
    if len({i.key for i in items}) != len(items):
        raise CalibrationError(f"{path}: an item appears twice")
    return Sample(pins, tuple(items), hashlib.sha256(raw).hexdigest())


def calibrations(root: Path) -> list[Path]:
    """Every calibration folder that has drawn its sample, by name."""
    base = root / FOLDER
    if not base.is_dir():
        return []
    return sorted(p for p in base.iterdir() if (p / SAMPLE).is_file())


def earlier(root: Path, folder: Path) -> tuple[list[Json], set[Key]]:
    """The other calibrations' samples (pinned by their sha256) and every item they hold: a new
    sample excludes them all, so no item is ever measured twice."""
    pins: list[Json] = []
    keys: set[Key] = set()
    for other in calibrations(root):
        if other.resolve() == folder.resolve():
            continue
        sample = read_sample(other)
        pins.append({"calibration": other.name, "sample_sha256": sample.sha256})
        keys |= {i.key for i in sample.items}
    return pins, keys


def excluded_by(root: Path, pins: Json) -> set[Key]:
    """The items a sample excluded, from the earlier samples it pins (each still the same file)."""
    keys: set[Key] = set()
    for raw in _list(pins["excludes"]):
        pin = _obj(raw)
        other = root / FOLDER / str(pin["calibration"])
        sample = read_sample(other)
        if sample.sha256 != pin["sample_sha256"]:
            raise CalibrationError(
                f"the earlier calibration {pin['calibration']}'s sample changed since this one "
                f"excluded it (sha256 {str(pin['sample_sha256'])[:12]}, now {sample.sha256[:12]})"
            )
        keys |= {i.key for i in sample.items}
    return keys


@dataclass(frozen=True)
class Judged:
    """A published judged record, read and checked, with the manifest's sha256."""

    directory: Path
    manifest: Json
    lines: list[Json]
    sha256: str


def judged_record_at(root: Path, run_id: str) -> Judged:
    """The published judged record: valid, complete, a judged run."""
    directory = root / PUBLISHED / run_id
    if not (directory / record.MANIFEST).is_file():
        raise CalibrationError(f"the judged record {run_id} is not published")
    if problems := record.validate(directory, root):
        raise CalibrationError(f"{run_id} is not a valid run record: " + "; ".join(problems))
    manifest, lines = record.read(directory)
    if manifest["suite"] != judged_record.JUDGED:
        raise CalibrationError(f"{run_id} is a {manifest['suite']} run, not a judged run")
    if manifest["partial"]:
        raise CalibrationError(f"{run_id} is partial")
    return Judged(directory, manifest, lines, sha256_file(directory / record.MANIFEST))


def draw_sample(
    root: Path,
    folder: Path,
    run_id: str,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> tuple[Sample, Drawn]:
    """`raglab calibrate sample`: rule s6-1 over a published judged record, written once to the
    folder's sample.jsonl."""
    if (folder / SAMPLE).exists():
        raise CalibrationError(f"{folder / SAMPLE} exists: a sample is drawn once, never again")
    bar = load_bar(folder)
    judged = judged_record_at(root, run_id)
    prompt = str(_obj(judged.manifest["judge_prompt"])["version"])
    if prompt != bar.judge_prompt:
        raise CalibrationError(
            f"{run_id} was judged under {prompt}; this bar calibrates {bar.judge_prompt}"
        )
    excludes, excluded = earlier(root, folder)
    drawn = draw(judged.lines, bar, excluded)
    pins: Json = {
        "calibration": folder.name,
        "rule": bar.rule,
        "seed": bar.seed,
        "bar_sha256": bar.sha256,
        "judged_run": run_id,
        "judged_manifest_sha256": judged.sha256,
        "source_run": _obj(judged.manifest["source"])["run_id"],
        "judge_prompt": prompt,
        "judge_seed": judged.manifest["seed"],
        "excludes": excludes,
        "shortfall": list(drawn.shortfall),
        "drawn_at": stamp(clock()),
    }
    (folder / SAMPLE).write_text(sample_text(pins, drawn.items), encoding="utf-8")
    return read_sample(folder), drawn


def redraw_problems(root: Path, folder: Path) -> list[str]:
    """The sample drawn again from the judged record it pins, with the earlier samples it pins:
    each item and pin that differs (the time it was drawn aside)."""
    sample = read_sample(folder)
    pins = sample.pins
    bar = load_bar(folder)
    problems: list[str] = []
    if bar.sha256 != pins["bar_sha256"]:
        problems.append(f"{BAR} changed since the sample pinned it")
    judged = judged_record_at(root, str(pins["judged_run"]))
    if judged.sha256 != pins["judged_manifest_sha256"]:
        problems.append("the judged record's manifest changed since the sample pinned it")
    drawn = draw(judged.lines, bar, excluded_by(root, pins))
    expected: Json = {
        "calibration": folder.name,
        "rule": bar.rule,
        "seed": bar.seed,
        "judged_run": pins["judged_run"],
        "source_run": _obj(judged.manifest["source"])["run_id"],
        "judge_prompt": _obj(judged.manifest["judge_prompt"])["version"],
        "judge_seed": judged.manifest["seed"],
        "shortfall": list(drawn.shortfall),
    }
    for name, value in expected.items():
        if pins[name] != value:
            problems.append(f"pin {name} is {pins[name]!r}, the draw gives {value!r}")
    for got, want in zip(sample.items, drawn.items, strict=False):
        if got != want:
            problems.append(f"item {got.order} is {got.key}, the draw gives {want.key}")
    if len(sample.items) != len(drawn.items):
        problems.append(f"the sample has {len(sample.items)} items, the draw {len(drawn.items)}")
    return problems


# ---------------------------------------------------------------- labels and seals


def read_jsonl(path: Path) -> list[Json]:
    text = path.read_text(encoding="utf-8")
    return [_obj(json.loads(line)) for line in text.splitlines() if line.strip()]


def jsonl_text(rows: Sequence[Json]) -> str:
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)


def label_problems(
    label: Json, item: Item, answer: str, shown: Sequence[str], prompt: str
) -> list[str]:
    """A label that is not in the judge's schema for this item: its fields, its verdict, a quote
    that is not a span of the shown answer, passage ids not among those shown, an empty reason,
    the shown answer's sha256."""
    where = f"item {item.order} ({item.criterion})"
    if list(label) != list(LABEL_FIELDS):
        return [f"{where}: the fields are {list(label)}, not {list(LABEL_FIELDS)}"]
    problems: list[str] = []
    if (label["order"], label["case_id"], label["trial"], label["criterion"]) != (
        item.order,
        item.case_id,
        item.trial,
        item.criterion,
    ):
        problems.append(f"{where}: the label is for another item")
    if label["verdict"] not in SIDES:
        problems.append(f"{where}: the verdict is pass or fail, not {label['verdict']!r}")
    quote = label["answer_quote"]
    if (
        not isinstance(quote, str)
        or judged_record.PROMPTS[prompt].quote_found(quote, answer) is not True
    ):
        problems.append(f"{where}: the quote is not words of the answer shown")
    ids = label["passage_ids"]
    if not isinstance(ids, list) or not all(isinstance(i, str) for i in cast(list[object], ids)):
        problems.append(f"{where}: passage_ids is a list of ids")
    else:
        named = [str(i) for i in cast(list[object], ids)]
        if len(set(named)) != len(named):
            problems.append(f"{where}: a passage id is named twice")
        if outside := [i for i in named if i not in shown]:
            problems.append(f"{where}: passages {outside} were not shown")
    if not isinstance(label["reason"], str) or not label["reason"].strip():
        problems.append(f"{where}: the reason is one sentence, not empty")
    if not isinstance(label["ambiguous"], bool):
        problems.append(f"{where}: ambiguous is true or false")
    if label["answer_sha256"] != judged_record.sha256_text(answer):
        problems.append(f"{where}: answer_sha256 is not the shown answer's")
    seconds = label["seconds"]
    if isinstance(seconds, bool) or not isinstance(seconds, int | float) or seconds < 0:
        problems.append(f"{where}: seconds is a number of at least 0")
    if not isinstance(label["labelled_at"], str):
        problems.append(f"{where}: labelled_at is a time")
    else:
        try:
            parse_time(label["labelled_at"], where)
        except CalibrationError as error:
            problems.append(str(error))
    return problems


def seal(folder: Path, name: str, seal_name: str, clock: Callable[[], datetime]) -> Json:
    """Write the seal of a labels file: its sha256, its line count and the time."""
    path = folder / name
    rows = read_jsonl(path)
    body: Json = {
        "file": name,
        "sha256": sha256_file(path),
        "lines": len(rows),
        "sealed_at": stamp(clock()),
    }
    (folder / seal_name).write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    return body


def read_seal(folder: Path, name: str, seal_name: str) -> Json:
    """A labels file's seal, held to the file: CalibrationError when it is missing, malformed, or
    the file differs from it (a label changed after the seal)."""
    path = folder / seal_name
    try:
        body = _obj(json.loads(path.read_text(encoding="utf-8")))
    except OSError as error:
        raise CalibrationError(f"{name} is not sealed ({seal_name} is missing)") from error
    if list(body) != list(SEAL_FIELDS) or body["file"] != name:
        raise CalibrationError(f"{seal_name} is not a seal of {name}")
    parse_time(str(body["sealed_at"]), seal_name)
    try:
        actual = sha256_file(folder / name)
    except OSError as error:
        raise CalibrationError(f"{name} is missing, but {seal_name} seals it") from error
    if actual != body["sha256"]:
        raise CalibrationError(
            f"{name} changed after its seal ({seal_name}: sha256 {str(body['sha256'])[:12]}, "
            f"now {actual[:12]}): nothing changes after the seal"
        )
    return body


def relabel_items(sample: Sample, bar: Bar) -> list[Item]:
    """D3's re-label: per criterion, `relabel.per_criterion` of its items drawn with
    random.Random("<seed>:relabel:<criterion>"), then all of them in a new order,
    random.Random("<seed>:relabel-order"), numbered from 1."""
    chosen: list[Item] = []
    for c in bar.criteria:
        mine = [i for i in sample.items if i.criterion == c.name]
        count = min(bar.relabel_per_criterion, len(mine))
        chosen += _rng(bar.seed, "relabel", c.name).sample(mine, count)
    _rng(bar.seed, "relabel-order").shuffle(chosen)
    return [Item(n, i.case_id, i.trial, i.criterion) for n, i in enumerate(chosen, start=1)]


# ---------------------------------------------------------------- the agreement


@dataclass(frozen=True)
class Pair:
    """One item: its stratum (criterion and the judge's verdict) and the label's verdict."""

    item: Item
    judge: str
    label: str

    @property
    def stratum(self) -> Stratum:
        return (self.item.criterion, self.judge)


def confusion(pairs: Sequence[Pair]) -> Json:
    """The judge's verdict against the label, in sample counts."""
    return {
        f"judge {j}, label {h}": sum(p.judge == j and p.label == h for p in pairs)
        for j in SIDES
        for h in SIDES
    }


def raw_agreement(pairs: Sequence[Pair]) -> Fraction | None:
    if not pairs:
        return None
    return Fraction(sum(p.judge == p.label for p in pairs), len(pairs))


def kappa(pairs: Sequence[Pair]) -> Fraction | None:
    """Cohen's kappa of two raters on binary labels, (po - pe) / (1 - pe): the judge (or, for the
    re-label, the first label) against the label. None when pe is 1 (both raters used one and the
    same class) or there are no pairs."""
    if not pairs:
        return None
    n = len(pairs)
    po = Fraction(sum(p.judge == p.label for p in pairs), n)
    a_pass = Fraction(sum(p.judge == "pass" for p in pairs), n)
    b_pass = Fraction(sum(p.label == "pass" for p in pairs), n)
    pe = a_pass * b_pass + (1 - a_pass) * (1 - b_pass)
    if pe == 1:
        return None
    return (po - pe) / (1 - pe)


def rates(
    pairs: Sequence[Pair], weights: Mapping[Stratum, Fraction] | None = None
) -> tuple[Fraction | None, Fraction | None]:
    """(TPR, TNR): of the answers the label passes, the share the judge passes; of those it fails,
    the share the judge fails. Weighted, each item counts its stratum's weight."""

    def weight(p: Pair) -> Fraction:
        return Fraction(1) if weights is None else weights[p.stratum]

    out: list[Fraction | None] = []
    for side in SIDES:
        mine = [p for p in pairs if p.label == side]
        total = sum((weight(p) for p in mine), Fraction(0))
        same = sum((weight(p) for p in mine if p.judge == side), Fraction(0))
        out.append(same / total if total else None)
    return out[0], out[1]


def strata_weights(pairs: Sequence[Pair], sizes: Mapping[Stratum, int]) -> dict[Stratum, Fraction]:
    """Each stratum's weight: its frame size over its sample size."""
    counts = Counter(p.stratum for p in pairs)
    return {s: Fraction(sizes[s], n) for s, n in counts.items()}


def resamples(
    pairs: Sequence[Pair], order: Sequence[Stratum], count: int, seed: int
) -> Iterator[list[Pair]]:
    """The bootstrap within strata: each resample draws each stratum's own number of items from
    it with replacement, strata in the given order, from one seeded stream."""
    # a seeded resampler for reproducible intervals, not a secret
    rng = random.Random(seed)  # noqa: S311  # nosec B311
    groups = [[p for p in pairs if p.stratum == s] for s in order]
    groups = [g for g in groups if g]
    for _ in range(count):
        drawn: list[Pair] = []
        for group in groups:
            drawn += [group[rng.randrange(len(group))] for _ in range(len(group))]
        yield drawn


def _float(value: Fraction | None) -> float | None:
    return None if value is None else round(float(value), 6)


def _interval(values: Sequence[float | None], level: float) -> Json:
    defined = [v for v in values if v is not None]
    tail = (1.0 - level) / 2.0
    return {
        "ci_low": round(metrics.quantile(defined, tail), 6) if defined else None,
        "ci_high": round(metrics.quantile(defined, 1.0 - tail), 6) if defined else None,
        "undefined_resamples": len(values) - len(defined),
    }


def agreement(
    pairs: Sequence[Pair],
    sizes: Mapping[Stratum, int],
    order: Sequence[Stratum],
    resample_count: int,
    seed: int,
    level: float,
) -> Json:
    """One scope's agreement (a criterion, or pooled): the confusion table, raw agreement, kappa,
    TPR and TNR weighted and unweighted, the strata, and the bootstrap intervals of kappa and the
    weighted rates."""
    weights = strata_weights(pairs, sizes)
    tpr_w, tnr_w = rates(pairs, weights)
    tpr, tnr = rates(pairs)
    boot: dict[str, list[float | None]] = {"kappa": [], "tpr": [], "tnr": []}
    for drawn in resamples(pairs, order, resample_count, seed):
        boot["kappa"].append(_float(kappa(drawn)))
        t, f = rates(drawn, weights)
        boot["tpr"].append(_float(t))
        boot["tnr"].append(_float(f))
    strata: Json = {}
    for s in order:
        if s in weights:
            strata[f"{s[0]}, judge {s[1]}"] = {
                "frame": sizes[s],
                "sample": sum(p.stratum == s for p in pairs),
                "weight": _float(weights[s]),
            }
    return {
        "items": len(pairs),
        "confusion": confusion(pairs),
        "raw": _float(raw_agreement(pairs)),
        "kappa": {"value": _float(kappa(pairs)), **_interval(boot["kappa"], level)},
        "tpr": {
            "weighted": {"value": _float(tpr_w), **_interval(boot["tpr"], level)},
            "unweighted": _float(tpr),
        },
        "tnr": {
            "weighted": {"value": _float(tnr_w), **_interval(boot["tnr"], level)},
            "unweighted": _float(tnr),
        },
        "strata": strata,
    }


# ---------------------------------------------------------------- leaks (labels never examples)

# a word: letters and digits, an apostrophe inside it kept ("company's" is one word, and so it is
# with a typographic apostrophe, U+2019)
_WORD = re.compile("[a-z0-9]+(?:['\\u2019][a-z0-9]+)*")
# A label leaks into the judge when a judge prompt version holds this many consecutive words of a
# labelled item's answer, quote or reason. Eight, because the rules' own phrases (that the
# documents do not state it) recur in honest answers: measured on 2026-10-24, no published answer
# shares more than six consecutive words with judge-v1 or judge-v2 (the S6 ledger).
LEAK_RUN = 8


def words(text: str) -> list[str]:
    return _WORD.findall(text.casefold())


def longest_shared_run(text: str, other: str) -> int:
    """The longest run of consecutive words the two texts share (letter case and punctuation
    aside)."""
    a, b = words(text), words(other)
    best = 0
    previous = [0] * (len(b) + 1)
    for x in a:
        current = [0] * (len(b) + 1)
        for j, y in enumerate(b, start=1):
            if x == y:
                current[j] = previous[j - 1] + 1
                best = max(best, current[j])
        previous = current
    return best


def labelled_texts(root: Path, folder: Path) -> list[tuple[str, str]]:
    """Each labelled item's answer, quote and reason (labels and re-labels), named: the texts that
    must never become judge examples."""
    sample = read_sample(folder)
    source = root / PUBLISHED / str(sample.pins["source_run"])
    _, _, lines = judged_record.read_source(source)
    answers = {(str(c["case_id"]), cast(int, c["trial"])): str(c["answer"]) for c in lines}
    texts: list[tuple[str, str]] = []
    for name in (LABELS, RELABELS):
        if not (folder / name).exists():
            continue
        for row in read_jsonl(folder / name):
            where = (
                f"{folder.name} {name} item {row['order']} ({row['case_id']} trial {row['trial']})"
            )
            answer = answers.get((str(row["case_id"]), cast(int, row["trial"])), "")
            texts += [
                (f"{where} answer", answer),
                (f"{where} quote", str(row["answer_quote"])),
                (f"{where} reason", str(row["reason"])),
            ]
    return texts


def leak_problems(
    texts: Sequence[tuple[str, str]], prompts: Mapping[str, str], limit: int = LEAK_RUN
) -> tuple[list[str], int]:
    """Each labelled text that shares `limit` or more consecutive words with a judge prompt
    version's text, naming both; and the longest run shared."""
    problems: list[str] = []
    longest = 0
    for where, text in texts:
        for version, prompt in prompts.items():
            run = longest_shared_run(text, prompt)
            longest = max(longest, run)
            if run >= limit:
                problems.append(f"{where}: {run} consecutive words are in {version}'s prompt")
    return problems, longest


def prompt_text(version: str) -> str:
    """Everything a judge prompt version shows the model but the item: its system prompt, its
    blocks and frames, and every criterion's pass and fail rules."""
    prompt = judged_record.PROMPTS[version]
    parts = [
        prompt.SYSTEM,
        prompt.CRITERION_BLOCK,
        prompt.QUESTION_FRAME,
        prompt.PASSAGE_FRAME,
        prompt.PASSAGES_HEADER,
        prompt.NO_PASSAGES,
        prompt.REFERENCE_FRAME,
        prompt.ANSWER_FRAME,
    ]
    for rule in prompt.RULES.values():
        parts += [rule.passes, rule.fails]
    return "\n".join(parts)


# ---------------------------------------------------------------- the record


def _git_commit(root: Path, path: Path) -> str:
    """The last commit that changed path (git log), or "" when it has none."""
    executable = shutil.which("git")
    if executable is None:
        raise CalibrationError("git is not on PATH: the record names the commits of its inputs")
    rel = path.resolve().relative_to(root.resolve()).as_posix()
    # fixed git arguments, no shell
    command = [executable, "log", "-1", "--format=%H", "--", rel]
    done = subprocess.run(  # noqa: S603  # nosec B603
        command, cwd=root, check=False, capture_output=True, text=True
    )
    if done.returncode != 0:
        raise CalibrationError(f"git log cannot name the commit of {rel}: {done.stderr.strip()}")
    return done.stdout.strip()


def git_commits(root: Path, folder: Path) -> dict[str, str]:
    """The commits that wrote the bar, the sample and the labels, read with git log; the record
    names them (the criteria judge checks their order with git log as well)."""
    found = {
        "bar": _git_commit(root, folder / BAR),
        "sample": _git_commit(root, folder / SAMPLE),
        "labels": _git_commit(root, folder / LABELS),
    }
    if missing := [name for name, sha in found.items() if not sha]:
        raise CalibrationError(f"commit {missing} first: the record names the commit of each")
    return found


@dataclass(frozen=True)
class Inputs:
    """Everything a record is computed from, read and checked."""

    bar: Bar
    sample: Sample
    judged: Judged
    answers: dict[Answer, str]
    shown: dict[Key, list[str]]
    labels: list[Json]
    labels_seal: Json
    relabels: list[Json] | None
    relabels_seal: Json | None
    disagreements: list[Json] | None


def _source_answers(
    root: Path, judged: Judged, prompt: str
) -> tuple[dict[Answer, str], dict[Key, list[str]]]:
    """The source run's answers and, per item key, the passage ids each criterion was shown."""
    source = _obj(judged.manifest["source"])
    directory = judged_record.find_source(judged.directory, root, str(source["run_id"]))
    if directory is None:
        raise CalibrationError(f"the source run {source['run_id']} is not published")
    _, _, lines = judged_record.read_source(directory)
    answers: dict[Answer, str] = {}
    shown: dict[Key, list[str]] = {}
    for line in lines:
        answer = (str(line["case_id"]), cast(int, line["trial"]))
        answers[answer] = str(line["answer"])
        for criterion in CRITERIA:
            if "answer" in judged_record.PROMPTS[prompt].RULES[criterion].sees:
                shown[(*answer, criterion)] = judged_record.shown_ids(
                    criterion, line, version=prompt
                )
    return answers, shown


def check_labels(
    rows: Sequence[Json],
    items: Sequence[Item],
    answers: Mapping[Answer, str],
    shown: Mapping[Key, list[str]],
    prompt: str,
    name: str,
) -> list[str]:
    """Labels that are not exactly the items in their order, each in the judge's schema."""
    problems: list[str] = []
    if len(rows) != len(items):
        problems.append(f"{name} has {len(rows)} labels for {len(items)} items")
    for row, item in zip(rows, items, strict=False):
        answer = answers.get((item.case_id, item.trial))
        if answer is None:
            problems.append(f"item {item.order}: no answer in the source run")
            continue
        problems += label_problems(row, item, answer, shown.get(item.key, []), prompt)
    return problems


def read_inputs(root: Path, folder: Path) -> Inputs:
    """Every input of the record, each held to what pinned it; CalibrationError naming the first
    that is not."""
    bar = load_bar(folder)
    sample = read_sample(folder)
    if bar.sha256 != sample.pins["bar_sha256"]:
        raise CalibrationError(
            f"the bar ({folder / BAR}) changed since the sample pinned it: sha256 "
            f"{str(sample.pins['bar_sha256'])[:12]}, now {bar.sha256[:12]}"
        )
    run_id = str(sample.pins["judged_run"])
    manifest_path = root / PUBLISHED / run_id / record.MANIFEST
    try:
        actual = sha256_file(manifest_path)
    except OSError as error:
        raise CalibrationError(f"the judged record {run_id} is not published") from error
    if actual != sample.pins["judged_manifest_sha256"]:
        raise CalibrationError(
            f"the judged record {run_id} changed since the sample pinned it: its manifest's sha256 "
            f"is {actual[:12]}, the sample pins {str(sample.pins['judged_manifest_sha256'])[:12]}"
        )
    judged = judged_record_at(root, run_id)
    prompt = str(sample.pins["judge_prompt"])
    answers, shown = _source_answers(root, judged, prompt)
    labels_seal = read_seal(folder, LABELS, LABELS_SEAL)
    labels = read_jsonl(folder / LABELS)
    if problems := check_labels(labels, sample.items, answers, shown, prompt, LABELS):
        raise CalibrationError("the labels are refused: " + "; ".join(problems))
    by_answer = {(str(c["case_id"]), cast(int, c["trial"])): c for c in judged.lines}
    for row, item in zip(labels, sample.items, strict=True):
        line = by_answer.get((item.case_id, item.trial))
        if line is None or line["answer_sha256"] != row["answer_sha256"]:
            raise CalibrationError(
                f"item {item.order}: the labelled answer's sha256 is not the judged line's"
            )
    relabels: list[Json] | None = None
    relabels_seal: Json | None = None
    if (folder / RELABELS).exists() or (folder / RELABELS_SEAL).exists():
        relabels_seal = read_seal(folder, RELABELS, RELABELS_SEAL)
        relabels = read_jsonl(folder / RELABELS)
        wanted = relabel_items(sample, bar)
        if problems := check_labels(relabels, wanted, answers, shown, prompt, RELABELS):
            raise CalibrationError("the re-label is refused: " + "; ".join(problems))
        earliest = parse_time(str(labels_seal["sealed_at"]), LABELS_SEAL) + timedelta(
            hours=bar.relabel_gap_hours
        )
        for row in relabels:
            if parse_time(str(row["labelled_at"]), RELABELS) < earliest:
                raise CalibrationError(
                    f"re-label item {row['order']} was labelled less than "
                    f"{bar.relabel_gap_hours:g} hours after the labels' seal"
                )
    disagreements: list[Json] | None = None
    if (folder / DISAGREEMENTS).exists():
        disagreements = read_jsonl(folder / DISAGREEMENTS)
    return Inputs(
        bar,
        sample,
        judged,
        answers,
        shown,
        labels,
        labels_seal,
        relabels,
        relabels_seal,
        disagreements,
    )


def pairs_of(inputs: Inputs) -> list[Pair]:
    """Each item's judge verdict (the judged record's first pass) and sealed label."""
    by_answer = {(str(c["case_id"]), cast(int, c["trial"])): c for c in inputs.judged.lines}
    pairs: list[Pair] = []
    for row, item in zip(inputs.labels, inputs.sample.items, strict=True):
        verdict = _obj(_obj(by_answer[(item.case_id, item.trial)]["verdicts"])[item.criterion])
        if verdict["status"] != Status.OK.value or verdict["verdict"] not in SIDES:
            raise CalibrationError(f"item {item.order}: the judged verdict is not pass or fail")
        pairs.append(Pair(item, str(verdict["verdict"]), str(row["verdict"])))
    return pairs


def disagreement_rows(inputs: Inputs, pairs: Sequence[Pair]) -> list[Json]:
    """Each disagreement with its class and the maintainer's answer: CalibrationError when one has
    no class, or a class is given to an item that is not a disagreement."""
    found = {p.item.key: p for p in pairs if p.judge != p.label}
    rows = inputs.disagreements or []
    classed: dict[Key, Json] = {}
    for row in rows:
        if list(row) != list(DISAGREEMENT_FIELDS):
            raise CalibrationError(
                f"{DISAGREEMENTS}: a row has the fields {list(row)}, not "
                f"{list(DISAGREEMENT_FIELDS)}"
            )
        key = (str(row["case_id"]), cast(int, row["trial"]), str(row["criterion"]))
        if key not in found:
            raise CalibrationError(f"{DISAGREEMENTS}: item {row['order']} is not a disagreement")
        if row["class"] not in CLASSES:
            raise CalibrationError(
                f"{DISAGREEMENTS}: item {row['order']}'s class {row['class']!r} is not one of "
                f"{list(CLASSES)}"
            )
        if not isinstance(row["answer"], str) or not row["answer"].strip():
            raise CalibrationError(
                f"{DISAGREEMENTS}: item {row['order']} carries the maintainer's answer, verbatim"
            )
        classed[key] = row
    if missing := [p.item.order for k, p in found.items() if k not in classed]:
        raise CalibrationError(
            f"a disagreement without a class: item(s) {missing} (raglab calibrate disagreements "
            f"lists them; their classes go in {DISAGREEMENTS})"
        )
    return [
        {
            **p.item.as_json(),
            "judge": p.judge,
            "label": p.label,
            "class": classed[p.item.key]["class"],
            "ambiguous": bool(_label_by_key(inputs)[p.item.key]["ambiguous"]),
        }
        for p in pairs
        if p.item.key in found
    ]


def _label_by_key(inputs: Inputs) -> dict[Key, Json]:
    return {
        (str(r["case_id"]), cast(int, r["trial"]), str(r["criterion"])): r for r in inputs.labels
    }


def disagreement_details(root: Path, folder: Path) -> list[Json]:
    """`raglab calibrate disagreements`, after the seal only: each item where the judge's verdict
    and the sealed label differ, with the judge's quote, passages and reason beside the label's,
    for the classes (how-to 05 step 5)."""
    inputs = read_inputs(root, folder)  # refuses labels that are not sealed as written
    by_answer = {(str(c["case_id"]), cast(int, c["trial"])): c for c in inputs.judged.lines}
    labels = _label_by_key(inputs)
    out: list[Json] = []
    for p in pairs_of(inputs):
        if p.judge == p.label:
            continue
        line = by_answer[(p.item.case_id, p.item.trial)]
        verdict = _obj(_obj(line["verdicts"])[p.item.criterion])
        label = labels[p.item.key]
        out.append(
            {
                **p.item.as_json(),
                "judge": {
                    "verdict": p.judge,
                    "answer_quote": verdict["answer_quote"],
                    "passage_ids": verdict["passage_ids"],
                    "reason": verdict["reason"],
                },
                "label": {
                    "verdict": p.label,
                    "answer_quote": label["answer_quote"],
                    "passage_ids": label["passage_ids"],
                    "reason": label["reason"],
                    "ambiguous": label["ambiguous"],
                },
            }
        )
    return out


def build_record(root: Path, folder: Path, commits: Mapping[str, str]) -> Json:
    """record.json: every number computed from the folder's files and the judged record they pin."""
    inputs = read_inputs(root, folder)
    bar, sample, judged = inputs.bar, inputs.sample, inputs.judged
    pairs = pairs_of(inputs)
    rows = disagreement_rows(inputs, pairs)
    names = [c.name for c in bar.criteria]
    excluded = excluded_by(root, sample.pins)
    full = frame(judged.lines, names, excluded)
    sizes = {s: len(v) for s, v in full.items()}
    order = [(c, side) for c in names for side in SIDES]
    scopes: Json = {}
    status: Json = {}
    for c in bar.criteria:
        mine = [p for p in pairs if p.item.criterion == c.name]
        mine_order = [s for s in order if s[0] == c.name]
        scopes[c.name] = agreement(
            mine, sizes, mine_order, bar.resamples, bar.agreement_seed, bar.level
        )
        status[c.name] = bar.status(c.name, kappa(mine))
    scopes["pooled"] = agreement(pairs, sizes, order, bar.resamples, bar.agreement_seed, bar.level)
    results = _obj(judged.manifest["results"])
    block = _obj(results["judged"])
    repeat = _obj(block["repeatability"])
    noise: Json = {}
    for name in names:
        noise[name] = {
            "repeat": repeat.get(name),
            "order": block["order"] if name == judged_record.GROUNDED else None,
        }
    relabel: Json | None = None
    if inputs.relabels is not None and inputs.relabels_seal is not None:
        first = _label_by_key(inputs)
        relabel_pairs = [
            Pair(
                Item(
                    cast(int, r["order"]),
                    str(r["case_id"]),
                    cast(int, r["trial"]),
                    str(r["criterion"]),
                ),
                str(
                    first[(str(r["case_id"]), cast(int, r["trial"]), str(r["criterion"]))][
                        "verdict"
                    ]
                ),
                str(r["verdict"]),
            )
            for r in inputs.relabels
        ]
        gap = parse_time(str(inputs.relabels_seal["sealed_at"]), RELABELS_SEAL) - parse_time(
            str(inputs.labels_seal["sealed_at"]), LABELS_SEAL
        )
        relabel = {
            "items": len(relabel_pairs),
            "sealed_at": inputs.relabels_seal["sealed_at"],
            "hours_after_the_labels_seal": round(gap.total_seconds() / 3600, 2),
            "criteria": {
                name: {
                    "items": sum(p.item.criterion == name for p in relabel_pairs),
                    "raw": _float(
                        raw_agreement([p for p in relabel_pairs if p.item.criterion == name])
                    ),
                    "kappa": _float(kappa([p for p in relabel_pairs if p.item.criterion == name])),
                }
                for name in names
            },
            "pooled": {
                "raw": _float(raw_agreement(relabel_pairs)),
                "kappa": _float(kappa(relabel_pairs)),
            },
        }
    errors = {
        (str(r["case_id"]), cast(int, r["trial"]), str(r["criterion"]))
        for r in rows
        if r["class"] == HUMAN_ERROR
    }
    corrected = [Pair(p.item, p.judge, p.judge if p.item.key in errors else p.label) for p in pairs]
    corrections: Json = {
        "items": len(errors),
        "criteria": {
            name: {
                "raw": _float(raw_agreement([p for p in corrected if p.item.criterion == name])),
                "kappa": _float(kappa([p for p in corrected if p.item.criterion == name])),
            }
            for name in names
        },
    }
    judge = _obj(judged.manifest["judge"])
    prompt = _obj(judged.manifest["judge_prompt"])
    counts = Counter(str(r["class"]) for r in rows)
    files = {
        name: sha256_file(folder / name)
        for name in (BAR, SAMPLE, LABELS, LABELS_SEAL, RELABELS, RELABELS_SEAL, DISAGREEMENTS)
        if (folder / name).exists()
    }
    return {
        "schema_version": RECORD_VERSION,
        "calibration": folder.name,
        "judge": {
            "model": judge["model"],
            "digest": judge["digest"],
            "temperature": judge.get("temperature"),
            "prompt": prompt["version"],
            "prompt_sha256": prompt["sha256"],
        },
        "judged_run": sample.pins["judged_run"],
        "judged_manifest_sha256": sample.pins["judged_manifest_sha256"],
        "source_run": sample.pins["source_run"],
        "files": files,
        "commits": dict(commits),
        "bar": {
            "reads": bar.reads,
            "undefined": bar.undefined,
            "criteria": {
                c.name: {"trusted": float(c.trusted), "stop": float(c.stop)} for c in bar.criteria
            },
        },
        "sample": {
            "rule": sample.pins["rule"],
            "seed": sample.pins["seed"],
            "drawn_at": sample.pins["drawn_at"],
            "items": len(sample.items),
            "shortfall": sample.pins["shortfall"],
            "excludes": sample.pins["excludes"],
            "criteria": {
                name: {
                    "items": sum(p.item.criterion == name for p in pairs),
                    "judge_pass": sum(p.stratum == (name, "pass") for p in pairs),
                    "judge_fail": sum(p.stratum == (name, "fail") for p in pairs),
                    "frame_pass": sizes[(name, "pass")],
                    "frame_fail": sizes[(name, "fail")],
                }
                for name in names
            },
        },
        "labels": {
            "items": len(inputs.labels),
            "sealed_at": inputs.labels_seal["sealed_at"],
            "ambiguous": sum(bool(r["ambiguous"]) for r in inputs.labels),
            "seconds": round(sum(cast(float, r["seconds"]) for r in inputs.labels), 1),
        },
        "agreement": scopes,
        "judge_noise": noise,
        "relabel": relabel,
        "disagreements": {
            "items": len(rows),
            "classes": {name: counts.get(name, 0) for name in CLASSES},
            "rows": rows,
        },
        "corrections": corrections,
        "status": status,
    }


def _fmt(value: object) -> str:
    return "undefined" if value is None else f"{cast(float, value):.3f}"


def _ci(block: Json) -> str:
    if block["ci_low"] is None:
        return "[undefined]"
    return f"[{_fmt(block['ci_low'])}, {_fmt(block['ci_high'])}]"


def _join(names: Sequence[str]) -> str:
    return ", ".join(names) if names else "none"


def render_record(rec: Json) -> str:
    """record.md in how-to 05's template, generated from record.json alone."""
    judge, sample, bar = _obj(rec["judge"]), _obj(rec["sample"]), _obj(rec["bar"])
    labels, commits, status = _obj(rec["labels"]), _obj(rec["commits"]), _obj(rec["status"])
    scopes, noise = _obj(rec["agreement"]), _obj(rec["judge_noise"])
    disagreements = _obj(rec["disagreements"])
    classes = _obj(disagreements["classes"])
    per = _obj(sample["criteria"])
    names = list(per)
    strata = "; ".join(
        f"{name} {_obj(per[name])['items']} ({_obj(per[name])['judge_pass']} judge pass, "
        f"{_obj(per[name])['judge_fail']} judge fail)"
        for name in names
    )
    shortfall = _list(sample["shortfall"])
    lines_of_bar = {
        (float(cast(float, _obj(v)["trusted"])), float(cast(float, _obj(v)["stop"])))
        for v in _obj(bar["criteria"]).values()
    }
    thresholds = "; ".join(
        f"kappa >= {t:.2f} trusted, {s:.2f} to {t:.2f} reported only, < {s:.2f} not trusted"
        for t, s in sorted(lines_of_bar)
    )
    relabel = rec["relabel"]
    if relabel is None:
        relabeller = "the re-label of 12 (D3): not yet, at least a day after the labels' seal"
    else:
        r = _obj(relabel)
        pooled = _obj(r["pooled"])
        relabeller = (
            f"the re-label of {r['items']} (D3), {r['hours_after_the_labels_seal']} hours "
            f"after the labels' seal: raw {_fmt(pooled['raw'])}, kappa {_fmt(pooled['kappa'])} "
            "with the first labels"
        )
    by_status = {s: [n for n in names if status[n] == s] for s in STATUSES}
    missed = by_status[REPORTED] + by_status[NOT_TRUSTED]
    if missed:
        follow = (
            f'a follow-up pull request (D4, "Record it; fix in a follow-up (Recommended)") for '
            f"{_join(missed)}: by the classified causes, a reworded rule (docs/CRITERIA.md's third "
            "sign-off) or judge-v3, the judged baseline judged again as a new record, and a fresh "
            "sample of the same allocation that excludes this one's items, the bar read on it only"
        )
        nxt = f"{follow}; and recalibrate on {TRIGGERS}"
    else:
        nxt = f"recalibrate on {TRIGGERS}"
    out = [
        f"# Judge calibration {rec['calibration']}",
        "",
        "Generated from record.json by `raglab calibrate record`; never edited by hand. "
        "record.json is computed from this folder's files and the published judged record they "
        "pin.",
        "",
        "```",
        f"judge: {judge['model']} @ {str(judge['digest'])[:12]}, {judge['prompt']} "
        f"{str(judge['prompt_sha256'])[:12]}, temperature {judge['temperature']}",
        f"sample: {sample['items']} verdicts of {rec['judged_run']}, drawn "
        f"{str(sample['drawn_at'])[:10]}, rule {sample['rule']}, seed {sample['seed']};",
        f"  {strata}" + (f"; shortfall: {len(shortfall)} stratum(s), below" if shortfall else ""),
        f"labellers: the maintainer (blind), {labels['items']} labels sealed "
        f"{labels['sealed_at']}; {CAVEAT}; {relabeller}",
        "agreement: per criterion and pooled, below: raw, kappa [95% interval], TPR and TNR "
        "weighted [interval] and unweighted; the judge's repeatability and order agreement beside "
        "them",
        f"threshold: {thresholds}",
        f"  (written {str(commits['bar'])[:7]}, before the sample {str(commits['sample'])[:7]} and "
        f"the labels {str(commits['labels'])[:7]})",
        f"disagreements: {disagreements['items']} read: {classes['criterion badly written']} "
        f"criterion, {classes['judge prompt unclear']} prompt, {classes[HUMAN_ERROR]} human error, "
        f"{classes['genuine ambiguity']} ambiguous",
        f"verdict: trusted for {_join(by_status[TRUSTED])}; reported only for "
        f"{_join(by_status[REPORTED])}; not trusted for {_join(by_status[NOT_TRUSTED])}",
        f"next: {nxt}",
        "```",
        "",
        "## Agreement",
        "",
        "The bar reads each criterion's kappa (the point estimate) on the sealed labels. TPR and "
        "TNR are weighted by stratum (frame size over sample size), unweighted beside; the "
        "intervals are 95% percentile intervals from a bootstrap within strata, and a resample "
        "whose statistic is undefined is counted, never imputed.",
        "",
        "| Scope | Items | Raw | Kappa [95%] | TPR weighted [95%] | TNR weighted [95%] | TPR, TNR "
        "unweighted | Undefined resamples (kappa, TPR, TNR) | Status |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for scope in [*names, "pooled"]:
        a = _obj(scopes[scope])
        k, tpr, tnr = _obj(a["kappa"]), _obj(a["tpr"]), _obj(a["tnr"])
        tw, fw = _obj(tpr["weighted"]), _obj(tnr["weighted"])
        out.append(
            f"| {scope} | {a['items']} | {_fmt(a['raw'])} | {_fmt(k['value'])} {_ci(k)} | "
            f"{_fmt(tw['value'])} {_ci(tw)} | {_fmt(fw['value'])} {_ci(fw)} | "
            f"{_fmt(tpr['unweighted'])}, {_fmt(tnr['unweighted'])} | "
            f"{k['undefined_resamples']}, {tw['undefined_resamples']}, "
            f"{fw['undefined_resamples']} | {status.get(scope, 'not read by the bar')} |"
        )
    out += [
        "",
        "## Confusion tables and strata",
        "",
        "| Scope | Judge pass, label pass | Judge pass, label fail | Judge fail, label pass | "
        "Judge fail, label fail | Strata (frame, sample, weight) |",
        "|---|---|---|---|---|---|",
    ]
    for scope in [*names, "pooled"]:
        a = _obj(scopes[scope])
        c = _obj(a["confusion"])
        cells = "; ".join(
            f"{name}: {_obj(v)['frame']}, {_obj(v)['sample']}, {_fmt(_obj(v)['weight'])}"
            for name, v in _obj(a["strata"]).items()
        )
        out.append(
            f"| {scope} | {c['judge pass, label pass']} | {c['judge pass, label fail']} | "
            f"{c['judge fail, label pass']} | {c['judge fail, label fail']} | {cells} |"
        )
    if shortfall:
        out += ["", "Shortfall (rule s6-1: the other stratum gave the rest):", ""]
        for raw in shortfall:
            s = _obj(raw)
            out.append(
                f"- {s['criterion']}, {s['stratum']}: {s['drawn']} of {s['wanted']} drawn; "
                f"{s['from_other_stratum']} more from the other stratum"
            )
    out += [
        "",
        "## The judge's own noise (the judged record, beside the labels)",
        "",
        "| Criterion | Repeatability: agree of pairs | Order (passages reversed): agree of pairs |",
        "|---|---|---|",
    ]
    for name in names:
        n = _obj(noise[name])
        rep = (
            "-"
            if n["repeat"] is None
            else f"{_obj(n['repeat'])['agree']} of {_obj(n['repeat'])['pairs']}"
        )
        order = (
            "-"
            if n["order"] is None
            else f"{_obj(n['order'])['agree']} of {_obj(n['order'])['pairs']}"
        )
        out.append(f"| {name} | {rep} | {order} |")
    out += ["", "## The re-label (D3)", ""]
    if relabel is None:
        out.append("Not yet: at least a day after the labels' seal (`make relabel`).")
    else:
        r = _obj(relabel)
        out += [
            f"{r['items']} items, sealed {r['sealed_at']}, "
            f"{r['hours_after_the_labels_seal']} hours after the labels' seal; the maintainer's "
            "agreement with their own first labels, a floor on their label noise (an optimistic "
            "one), not agreement between two people.",
            "",
            "| Scope | Items | Raw | Kappa |",
            "|---|---|---|---|",
        ]
        for name, raw in _obj(r["criteria"]).items():
            v = _obj(raw)
            out.append(f"| {name} | {v['items']} | {_fmt(v['raw'])} | {_fmt(v['kappa'])} |")
        pooled = _obj(r["pooled"])
        out.append(f"| pooled | {r['items']} | {_fmt(pooled['raw'])} | {_fmt(pooled['kappa'])} |")
    out += [
        "",
        "## Disagreements",
        "",
        "Each read with the judge's reason and the label's side by side and classified (how-to 05 "
        "step 5); the classes are the maintainer's, quoted in the stage ledger.",
        "",
        "| Item | Case | Trial | Criterion | Judge | Label | Ambiguous flag | Class |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for raw in _list(disagreements["rows"]):
        d = _obj(raw)
        out.append(
            f"| {d['order']} | {d['case_id']} | {d['trial']} | {d['criterion']} | {d['judge']} | "
            f"{d['label']} | {'yes' if d['ambiguous'] else 'no'} | {d['class']} |"
        )
    if not _list(disagreements["rows"]):
        out.append("| - | - | - | - | - | - | - | none |")
    corrections = _obj(rec["corrections"])
    out += [
        "",
        "## Corrections after the verdicts were seen (reported, never read by the bar)",
        "",
        f"{corrections['items']} label(s) classed a human error, each read as the judge's verdict "
        "here; the sealed labels above are never replaced.",
        "",
        "| Criterion | Raw | Kappa |",
        "|---|---|---|",
    ]
    for name, raw in _obj(corrections["criteria"]).items():
        v = _obj(raw)
        out.append(f"| {name} | {_fmt(v['raw'])} | {_fmt(v['kappa'])} |")
    out += [
        "",
        "## Limits",
        "",
        "- 30 labels, 15 per criterion: a precursor, not the calibration study; one disagreement "
        "moves a criterion's kappa by about 0.13, and the intervals are wide.",
        f"- {CAVEAT[0].upper()}{CAVEAT[1:]}.",
        f"- {INTEGRITY[0].upper()}{INTEGRITY[1:]}.",
        f"- The labels took {labels['seconds']} s in all; {labels['ambiguous']} carry the "
        "ambiguous flag.",
        "",
    ]
    return "\n".join(out)


def record_texts(rec: Json) -> tuple[str, str]:
    return json.dumps(rec, indent=2, ensure_ascii=False) + "\n", render_record(rec)


def write_record(root: Path, folder: Path, commits: Mapping[str, str]) -> Json:
    """`raglab calibrate record`: record.json and record.md, written from the inputs."""
    rec = build_record(root, folder, commits)
    text, markdown = record_texts(rec)
    (folder / RECORD_JSON).write_text(text, encoding="utf-8")
    (folder / RECORD_MD).write_text(markdown, encoding="utf-8")
    return rec


def record_problems(root: Path, folder: Path) -> list[str]:
    """The record regenerated from its inputs (the commits it names kept, which git log checks)
    and compared with the committed files."""
    try:
        committed = _obj(json.loads((folder / RECORD_JSON).read_text(encoding="utf-8")))
        commits = {str(k): str(v) for k, v in _obj(committed["commits"]).items()}
        text, markdown = record_texts(build_record(root, folder, commits))
    except (CalibrationError, OSError, KeyError, ValueError) as error:
        return [f"the record cannot be regenerated: {error}"]
    problems: list[str] = []
    if (folder / RECORD_JSON).read_text(encoding="utf-8") != text:
        problems.append(f"{RECORD_JSON} is not the record computed from its inputs")
    if (folder / RECORD_MD).read_text(encoding="utf-8") != markdown:
        problems.append(f"{RECORD_MD} is not the one generated from {RECORD_JSON}")
    return problems
