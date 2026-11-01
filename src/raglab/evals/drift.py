"""The nightly drift alert (S8, GA7; the main plan's nightly row, "alerts: drift from the last
nightly"; S6's recalibration trigger "S8's drift alert on a judged pass rate").

`raglab eval --gate nightly` (a generation run) compares its behaviour pass^N, paired by case,
with the previous published nightly record of the same config (the newest run of that suite,
config and split under gate nightly in runs/published/index.json) and writes an `alert` block in
its manifest and a line in its report: the run compared with, B minus A with its paired bootstrap
interval, the flipped cases, and whether the alert fired, which it does when the interval lies
entirely below zero. It never blocks: the command exits as it would without it. With no published
nightly of the config yet, the first nightly is the reference and the block says so. `raglab
publish` recomputes the block against the index and refuses a mismatch (raglab.evals.publish,
the maintainer's choice 8), so a published alert is never a hand-written one.

`raglab judge --gate nightly` writes the judged alert the same way, between consecutive published
nightly judged records under one judge, on the criteria the calibration record marks trusted
(raglab.evals.judged_gate); when it fires it names S6's recalibration trigger, since a drift on a
judged pass rate makes the calibration record history for the judge it no longer describes. With
no record or no trusted criterion, the block says no judged alert is read.
"""

from collections.abc import Sequence
from pathlib import Path
from typing import cast

from raglab.evals import compare, judged_gate, publish, record
from raglab.evals.record import Json, as_json, as_list

GATE = "nightly"
RECALIBRATION = (
    "S6's recalibration trigger: a drift alert on a judged pass rate makes the calibration "
    "record history for the judge it no longer describes; recalibrate before gating on it again"
)


def previous_nightly(root: Path, manifest: Json) -> Path | None:
    """The newest published run of the same suite, config and split under gate nightly, made
    before this one; None when there is none (this run is the reference)."""
    published = root / publish.PUBLISHED
    config = as_json(manifest["config"])["name"]
    found: list[tuple[str, str]] = []
    for entry in (as_json(e) for e in as_list(publish.read_index(published).get("runs", []))):
        if (entry["suite"], entry["config"], entry["split"]) != (
            manifest["suite"],
            config,
            manifest["split"],
        ):
            continue
        if entry["run_id"] == manifest["run_id"] or str(entry["created_at"]) >= str(
            manifest["created_at"]
        ):
            continue
        try:
            earlier = as_json(
                record.read(published / str(entry["run_id"]))[0]
            )  # the index has no gate: read it
        except (OSError, ValueError):
            continue
        if earlier["gate"] == GATE:
            found.append((str(entry["created_at"]), str(entry["run_id"])))
    if not found:
        return None
    return published / max(found)[1]


def _block(against: str | None, fired: bool, metric: str | None = None, **more: object) -> Json:
    out: Json = {"gate": GATE, "against": against, "fired": fired}
    if metric is not None:
        out["metric"] = metric
    out.update(more)
    return out


def _of(comparison: Json, name: str) -> tuple[Json, Json]:
    m = as_json(as_json(comparison["metrics"])[name])
    diff = {"value": m["diff"], "ci_low": m["ci_low"], "ci_high": m["ci_high"], "n": m["n"]}
    changed = as_json(as_json(comparison["changed"])[name])
    return diff, {"gained": changed["better"], "lost": changed["worse"]}


def alert_for(root: Path, manifest: Json, cases: Sequence[Json]) -> Json:
    """The alert block of a nightly generation run (the module docstring)."""
    previous = previous_nightly(root, manifest)
    if previous is None:
        return _block(None, False, note="the first nightly of this config is the reference")
    try:
        earlier, earlier_cases = record.read(previous)
        comparison = compare.compare_generation(earlier, earlier_cases, manifest, list(cases))
    except (compare.CompareError, OSError, ValueError, KeyError) as error:
        return _block(previous.name, False, note=f"not compared: {error}")
    name = f"behaviour_pass^{manifest['trials']}"
    diff, flipped = _of(comparison, name)
    return _block(previous.name, cast(float, diff["ci_high"]) < 0, name, diff=diff, flipped=flipped)


def judged_alert_for(root: Path, manifest: Json, lines: Sequence[Json]) -> Json:
    """The alert block of a nightly judged run: on the trusted criteria only."""
    try:
        found = judged_gate.find_record(root, manifest)
    except judged_gate.GateError as error:
        return _block(None, False, note=f"no judged alert: {error}")
    if found is None:
        return _block(
            None, False, note="no judged alert: no calibration record describes the judge"
        )
    trusted = judged_gate.trusted_criteria(found[1])
    if not trusted:
        return _block(None, False, criteria=[], note="no judged alert: no trusted criterion")
    previous = previous_nightly(root, manifest)
    if previous is None:
        return _block(
            None, False, criteria=trusted, note="the first nightly judged run is the reference"
        )
    try:
        earlier, earlier_lines = record.read(previous)
        comparison = compare.compare_judged(earlier, earlier_lines, manifest, list(lines))
    except (compare.CompareError, OSError, ValueError, KeyError) as error:
        return _block(previous.name, False, criteria=trusted, note=f"not compared: {error}")
    metrics = as_json(comparison["metrics"])
    compared = [c for c in trusted if c in metrics]
    diffs: Json = {}
    lost: list[str] = []
    gained: list[str] = []
    fired = False
    for criterion in compared:
        diff, flipped = _of(comparison, criterion)
        diffs[criterion] = cast(float, diff["value"])
        diffs[f"{criterion}.ci_low"] = cast(float, diff["ci_low"])
        diffs[f"{criterion}.ci_high"] = cast(float, diff["ci_high"])
        if cast(float, diff["ci_high"]) < 0:
            fired = True
            lost += [i for i in cast(list[str], flipped["lost"]) if i not in lost]
            gained += [i for i in cast(list[str], flipped["gained"]) if i not in gained]
    block = _block(
        previous.name,
        fired,
        "the pass share per trusted criterion",
        criteria=compared,
        diff=diffs,
        flipped={"gained": gained, "lost": lost},
    )
    if fired:
        block["note"] = RECALIBRATION
    return block


def line(alert: Json) -> str:
    """One line for the terminal: what the alert compared with and whether it fired."""
    against = alert["against"]
    head = f"drift alert ({GATE}): "
    if against is None:
        return head + str(alert.get("note", "no reference"))
    if alert["fired"]:
        lost = ", ".join(cast(list[str], as_json(alert["flipped"])["lost"])) or "none"
        return head + (
            f"FIRED against {against}: {alert['metric']} dropped by an interval entirely below "
            f"zero (cases lost: {lost}); it never blocks"
            + (f"; {alert['note']}" if "note" in alert else "")
        )
    return (
        head + f"not fired against {against}" + (f" ({alert['note']})" if "note" in alert else "")
    )


def report_lines(alert: Json) -> list[str]:
    lines = ["", "## Drift alert (nightly)", "", line(alert) + "."]
    if "diff" in alert:
        diff = as_json(alert["diff"])
        lines.append(
            "- B minus A: " + ", ".join(f"{k} {cast(float, v):+.3f}" for k, v in diff.items())
        )
    if "flipped" in alert:
        flipped = as_json(alert["flipped"])
        gained = ", ".join(cast(list[str], flipped["gained"])) or "none"
        lost = ", ".join(cast(list[str], flipped["lost"])) or "none"
        lines.append(f"- Flipped cases: gained {gained}; lost {lost}")
    return lines
