"""The judged gate (S8, GA6; the main plan's eval-on-change rule, "the paired-diff interval must
not cross zero downward", under D1 A: "Trusted criteria gate by the paired interval, locally").

`raglab gate --judged B --against A` compares two judged records under one judge
(raglab.evals.compare.compare_judged) and reads the calibration record (S6, `record.json` under
datasets/calibration/<name>/, written by `raglab calibrate`): the one B's manifest names in
`judge.calibration_record` (its sha256 must still match, so a record edited after the pin is
refused), or, for a record that predates the pin (S6's v2 baseline), the one whose `judge` block
describes B's judge by identity (model, digest, prompt version and fingerprint). The record's
`status` names each calibrated criterion trusted, reported only or not trusted (S6's bar: kappa
0.80 or more, 0.60 to under 0.80, under 0.60).

The rule: a criterion the record marks **trusted** fails the gate when B minus A's paired
interval lies entirely below zero (a drop the data supports; the stricter reading, a lower bound
below zero, would fail on noise alone at 79 cases); a reported-only or not-trusted criterion is
printed and never gates; a criterion the record does not name is printed as uncalibrated and never
gates. With no record for the judge, or with no trusted criterion, the gate refuses: nothing
judged gates until S6's verdicts trust a criterion. No margin is invented; the interval carries
the uncertainty, and the record's weighted TPR and TNR are quoted beside the verdict as the judge's
own error, never folded into a number.
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from raglab.evals import compare, record
from raglab.evals.record import Json, as_json

NAME = "judged gate (eval-on-change)"
CALIBRATION_DIR = "datasets/calibration"
RECORD = "record.json"
TRUSTED, REPORTED, NOT_TRUSTED = "trusted", "reported only", "not trusted"
STATUSES = (TRUSTED, REPORTED, NOT_TRUSTED)
# what names a judge in a calibration record's judge block, against a judged manifest
IDENTITY = (
    ("model", ("judge", "model")),
    ("digest", ("judge", "digest")),
    ("prompt", ("judge_prompt", "version")),
    ("prompt_sha256", ("judge_prompt", "sha256")),
)


class GateError(ValueError):
    pass


@dataclass(frozen=True)
class Outcome:
    passed: bool
    lines: list[str]


def read_record(path: Path) -> Json:
    """A calibration record's JSON; GateError when it is not one."""
    try:
        data = as_json(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError) as error:
        raise GateError(f"{path} is not a calibration record ({error})") from error
    if "status" not in data or "judge" not in data:
        raise GateError(f"{path} is not a calibration record: no status or judge block")
    status = as_json(data["status"])
    if bad := {k: v for k, v in status.items() if v not in STATUSES}:
        raise GateError(f"{path}: statuses {bad} are not one of {STATUSES}")
    return data


def describes(data: Json, manifest: Json) -> bool:
    """Whether a calibration record's judge block is the judged manifest's judge."""
    judge = as_json(data["judge"])
    return all(judge.get(name) == as_json(manifest[part])[key] for name, (part, key) in IDENTITY)


def find_record(root: Path, manifest: Json) -> tuple[Path, Json] | None:
    """The calibration record for a judged manifest: the one it names (GateError when that
    file changed since the pin or does not describe the judge), else the one under
    datasets/calibration/ that describes its judge by identity; None when there is none."""
    named = as_json(manifest["judge"]).get("calibration_record")
    if named is not None:
        pin = as_json(named)
        path = root / str(pin["path"])
        if not path.is_file():
            raise GateError(f"{manifest['run_id']} names {pin['path']}, which does not exist")
        if record.sha256_bytes(path.read_bytes()) != pin["sha256"]:
            raise GateError(
                f"{pin['path']} changed since {manifest['run_id']} pinned it (sha256 "
                f"{str(pin['sha256'])[:12]}): a judged run gates on the record it names"
            )
        data = read_record(path)
        if not describes(data, manifest):
            raise GateError(f"{pin['path']} does not describe the judge of {manifest['run_id']}")
        return path, data
    for path in sorted((root / CALIBRATION_DIR).glob(f"*/{RECORD}")):
        data = read_record(path)
        if describes(data, manifest):
            return path, data
    return None


def _error(agreement: Json, criterion: str) -> str:
    """The judge's own error on a criterion, as the record reports it (weighted TPR and TNR),
    quoted beside the verdict."""
    block = as_json(agreement.get(criterion) or {})
    parts: list[str] = []
    for name in ("tpr_weighted", "tnr_weighted", "tpr", "tnr", "kappa"):
        value = block.get(name)
        if isinstance(value, dict):
            value = as_json(cast(object, value)).get("value")
        if isinstance(value, int | float) and not isinstance(value, bool):
            parts.append(f"{name} {value:.3f}")
    return ", ".join(parts) or "no agreement numbers in the record"


def verdict(comparison: Json, data: Json, where: str = RECORD) -> Outcome:
    """The gate's outcome on a judged comparison with a calibration record's statuses."""
    status = {str(k): str(v) for k, v in as_json(data["status"]).items()}
    agreement = as_json(data.get("agreement") or {})
    metrics = as_json(comparison["metrics"])
    lines = [
        f"{NAME}: {comparison['b']} against {comparison['a']}, record {where} "
        f"({data.get('calibration', '?')})"
    ]
    failed: list[str] = []
    trusted: list[str] = []
    for criterion, raw in metrics.items():
        m = as_json(raw)
        interval = (
            f"B minus A {cast(float, m['diff']):+.3f} [{cast(float, m['ci_low']):+.3f}, "
            f"{cast(float, m['ci_high']):+.3f}] over {m['n']} cases"
        )
        state = status.get(criterion)
        if state == TRUSTED:
            trusted.append(criterion)
            below = cast(float, m["ci_high"]) < 0
            word = "FAILS" if below else "passes"
            lines.append(
                f"  {criterion}: trusted, {word}: {interval} ("
                f"{'entirely' if below else 'not entirely'} below zero; the judge's own error: "
                f"{_error(agreement, criterion)})"
            )
            if below:
                failed.append(criterion)
        elif state in (REPORTED, NOT_TRUSTED):
            lines.append(f"  {criterion}: {state}, never gates: {interval}")
        else:
            lines.append(
                f"  {criterion}: not calibrated (no status in the record), never gates: {interval}"
            )
    if not trusted:
        lines.append(
            "refused: the record marks no compared criterion trusted, so nothing judged gates "
            "(S6's bar: kappa 0.80 or more trusts a criterion)"
        )
        return Outcome(False, lines)
    if failed:
        lines.append(f"fails: {', '.join(failed)} dropped by an interval entirely below zero")
        return Outcome(False, lines)
    lines.append(f"passes: no trusted criterion ({', '.join(trusted)}) dropped")
    return Outcome(True, lines)


def check(root: Path, b_dir: Path, a_dir: Path, calibration: Path | None = None) -> Outcome:
    """The gate end to end: both records validated and compared under one judge, the record
    found (or the given one), the verdict."""
    comparison = compare.compare(a_dir, b_dir, root)
    if comparison["suite"] != "judged":
        raise GateError(
            f"{b_dir.name} is a {comparison['suite']} run: the judged gate reads judged runs"
        )
    b_manifest, _ = record.read(b_dir)
    if calibration is not None:
        path = calibration if calibration.is_absolute() else root / calibration
        data = read_record(path)
        if not describes(data, b_manifest):
            raise GateError(f"{calibration} does not describe the judge of {b_dir.name}")
        found: tuple[Path, Json] | None = (path, data)
    else:
        found = find_record(root, b_manifest)
    if found is None:
        raise GateError(
            f"no calibration record under {CALIBRATION_DIR}/ describes the judge of "
            f"{b_dir.name} (model {as_json(b_manifest['judge'])['model']}, prompt "
            f"{as_json(b_manifest['judge_prompt'])['version']}): nothing judged gates until S6's "
            "record trusts a criterion"
        )
    path, data = found
    where = path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path)
    return verdict(comparison, data, where)


def trusted_criteria(data: Json) -> list[str]:
    return [str(k) for k, v in as_json(data["status"]).items() if v == TRUSTED]


def names(criteria: Sequence[str]) -> str:
    return ", ".join(criteria) if criteria else "none"
