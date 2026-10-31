"""S8 (GA2): docs/THRESHOLDS.md gives a reason for every gated and every reported metric. Every
metric key under results.metrics of every manifest in runs/published/, every rate and latency of
runs/guard-suites/*.json, and the perf smoke's names (perf/smoke.js) appear as a row of a
THRESHOLDS.md table whose Gate and Reason cells are non-empty, and every row's Gate cell names one
of the gates, a "hard stop" or "enforced in code" phrase, or `reported`. A metric key `name[group]`
or `name_pass^N` is covered by a row that names `name`; `pass^N` and `behaviour_pass^N` by a row
naming them. Each break runs on a copy of the text or of a manifest."""

import json
import re
from pathlib import Path

import pytest

from tests.conftest import ROOT

pytestmark = pytest.mark.unit
DOC = ROOT / "docs" / "THRESHOLDS.md"
PUBLISHED = ROOT / "runs" / "published"
GUARD_SUITES = ROOT / "runs" / "guard-suites"
SMOKE = ROOT / "perf" / "smoke.js"
GATES = ("pr-fast", "eval-on-change", "nightly", "manual", "release", "weekly")
GATE_PHRASES = ("hard stop", "enforced in code", "reported")
PERF_NAMES = ("ask_duration", "checks", "http_req_failed", "p(90)", "p(95)", "min", "max")


def rows(text: str) -> list[tuple[str, str, str, str]]:
    """Every (metric, gate, threshold, reason) row of every four-column table whose header starts
    with Metric and Gate."""
    found: list[tuple[str, str, str, str]] = []
    header = None
    for line in text.splitlines():
        if not line.startswith("|"):
            header = None
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells[:2] == ["Metric", "Gate"]:
            header = cells
            continue
        if header is None or len(cells) != 4 or set(cells[0]) <= {"-"}:
            continue
        found.append((cells[0], cells[1], cells[2], cells[3]))
    return found


def published_metric_keys(published: Path = PUBLISHED) -> dict[str, set[str]]:
    """Each metric key of results.metrics across the published manifests, with its suites."""
    keys: dict[str, set[str]] = {}
    for path in sorted(published.glob("*/manifest.json")):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        for key in manifest["results"]["metrics"]:
            keys.setdefault(key, set()).add(manifest["suite"])
    return keys


def guard_suite_names(folder: Path = GUARD_SUITES) -> set[str]:
    """The rates and the latency names a guard-suites record carries per layer."""
    names: set[str] = set()
    for path in sorted(folder.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for layer in data["layers"].values():
            names |= {k for k in layer if k != "sources"}
    return names


def perf_names(path: Path = SMOKE) -> set[str]:
    text = path.read_text(encoding="utf-8")
    return {name for name in PERF_NAMES if name in text}


def base_name(key: str) -> str:
    """What a row must name to cover a key: `grounded[answer]` and `grounded_pass^3` are
    `grounded`'s; `position[first]` is `position`'s; a plain key is itself."""
    key = key.split("[", 1)[0]
    if re.fullmatch(r"\w+_pass\^\d+", key) and not key.startswith("behaviour_"):
        return key.rsplit("_pass^", 1)[0]
    return key


def names_in(cell: str) -> set[str]:
    """The metric names a Metric cell holds, casefolded: backticked tokens and bare tokens."""
    text = cell.replace("`", "").casefold()
    return set(re.findall(r"[a-z][a-z0-9_@^.\-]*[a-z0-9]|[a-z]", text))


def covered_by(key: str, metric_cell: str) -> bool:
    names = names_in(metric_cell)
    return base_name(key).casefold() in names or key.casefold() in names


def problems(
    text: str,
    keys: dict[str, set[str]],
    guard_names: set[str],
    perf: set[str],
) -> list[str]:
    table = rows(text)
    out: list[str] = []
    for metric, gate, _threshold, reason in table:
        if not gate or not reason:
            out.append(f"{metric}: an empty Gate or Reason cell")
        head = gate.casefold()
        if not any(head.startswith(g) for g in GATES) and not any(p in head for p in GATE_PHRASES):
            out.append(
                f"{metric}: Gate {gate!r} names no gate, hard stop, enforced-in-code or reported"
            )
    for key in sorted(keys):
        if not any(
            covered_by(key, metric) and gate and reason for metric, gate, _, reason in table
        ):
            out.append(
                f"{key} ({', '.join(sorted(keys[key]))}): no THRESHOLDS.md row with a gate and a "
                "reason"
            )
    for name in sorted(guard_names):
        if not any(
            name.casefold() in metric.casefold().replace("`", "")
            for metric, gate, _, reason in table
            if gate and reason
        ):
            out.append(f"guard suites' {name}: no THRESHOLDS.md row with a gate and a reason")
    for name in sorted(perf):
        if not any(
            name in metric.replace("`", "") for metric, gate, _, reason in table if gate and reason
        ):
            out.append(f"perf smoke's {name}: no THRESHOLDS.md row with a gate and a reason")
    return out


def test_every_metric_has_a_row_with_a_gate_and_a_reason():
    keys = published_metric_keys()
    assert {"recall@5", "behaviour_pass^3", "grounded", "safe"} <= set(keys)
    guard_names = guard_suite_names()
    assert {"must_block", "must_not_block", "latency_ms"} <= guard_names
    perf = perf_names()
    assert {"ask_duration", "checks", "http_req_failed"} <= perf
    assert problems(DOC.read_text(encoding="utf-8"), keys, guard_names, perf) == []


def test_every_gate_cell_is_a_gate_a_hard_stop_enforced_in_code_or_reported():
    for metric, gate, _, _ in rows(DOC.read_text(encoding="utf-8")):
        head = gate.casefold()
        assert any(head.startswith(g) for g in GATES) or any(p in head for p in GATE_PHRASES), (
            metric,
            gate,
        )


def test_a_reason_emptied_a_key_renamed_and_a_row_deleted_are_each_named(tmp_path):
    text = DOC.read_text(encoding="utf-8")
    keys, guard_names, perf = published_metric_keys(), guard_suite_names(), perf_names()
    [row] = [line for line in text.splitlines() if line.startswith("| hit@5, MRR@5 |")]
    cells = row.strip().strip("|").split("|")
    cells[3] = " "
    emptied = text.replace(row, "|" + "|".join(cells) + "|", 1)
    found = problems(emptied, keys, guard_names, perf)
    assert "hit@5, MRR@5: an empty Gate or Reason cell" in found
    assert "hit@5 (retrieval): no THRESHOLDS.md row with a gate and a reason" in found
    assert "mrr@5 (retrieval): no THRESHOLDS.md row with a gate and a reason" in found
    deleted = text.replace(row + "\n", "", 1)
    assert problems(deleted, keys, guard_names, perf) == [
        "hit@5 (retrieval): no THRESHOLDS.md row with a gate and a reason",
        "mrr@5 (retrieval): no THRESHOLDS.md row with a gate and a reason",
    ]
    # a metric key renamed in a copied manifest: the copy's key has no row
    copied = tmp_path / "published" / "20261024T090200Z-retrieval-dense-dev-ade9397"
    copied.mkdir(parents=True)
    source = PUBLISHED / copied.name / "manifest.json"
    manifest = json.loads(source.read_text(encoding="utf-8"))
    manifest["results"]["metrics"]["recall@7"] = manifest["results"]["metrics"].pop("recall@5")
    (copied / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert problems(text, published_metric_keys(tmp_path / "published"), set(), set()) == [
        "recall@7 (retrieval): no THRESHOLDS.md row with a gate and a reason"
    ]
    gated = text.replace("| hit@5, MRR@5 | reported |", "| hit@5, MRR@5 | someday |", 1)
    assert problems(gated, keys, guard_names, perf) == [
        "hit@5, MRR@5: Gate 'someday' names no gate, hard stop, enforced-in-code or reported"
    ]


def test_base_names():
    assert base_name("grounded[answer]") == "grounded"
    assert base_name("grounded_pass^3") == "grounded"
    assert base_name("behaviour_pass^3") == "behaviour_pass^3"
    assert base_name("pass^3") == "pass^3"
    assert base_name("position[middle-first]") == "position"
    assert base_name("recall@5") == "recall@5"
    assert covered_by("mrr@5", "hit@5, MRR@5")
    assert covered_by(
        "decision_label[abstain]",
        "decision-label rate; `decision_label` (overall and per expected label)",
    )
    assert not covered_by("safe^3", "status_ok, pass^3")
