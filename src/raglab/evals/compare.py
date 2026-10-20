"""Compare two runs on the same questions: per metric, B minus A with a paired bootstrap interval
(raglab.evals.metrics), and the questions whose outcome flipped.

Two retrieval runs must be valid run records of the same split, dataset (sha256), k and case
ids; anything else is not a paired comparison and is refused. The bootstrap uses run A's seed,
resample count and level.

Two generation runs (S4) must be valid run records of the same split, dataset (sha256) and number
of trials, with the same behaviour cases. They are paired by case id, never by position: per case,
whether all its trials passed (behaviour pass^N) and the share of its trials whose decision label
was right, and B minus A of each with a percentile bootstrap over cases (`random.Random(seed)`,
A's seed and interval level, 2,000 resamples, as the retrieval comparison); the flipped cases are
those that passed every trial in one run and not in the other. A retrieval run against a
generation run is refused.

`write` puts compare.json and compare.md (generated, never edited) in a directory of their own.
"""

import json
from pathlib import Path
from typing import cast

from raglab.evals import behaviour, metrics, record
from raglab.evals.record import Json, as_json

SCHEMA_VERSION = "compare.v1"


class CompareError(ValueError):
    pass


def _same(a: Json, b: Json, *path: str) -> bool:
    x: object = a
    y: object = b
    for key in path:
        x, y = as_json(x)[key], as_json(y)[key]
    return x == y


def compare(a_dir: Path, b_dir: Path, root: Path) -> Json:
    for run_dir in (a_dir, b_dir):
        if problems := record.validate(run_dir, root):
            raise CompareError(f"{run_dir.name} is not a valid run record: " + "; ".join(problems))
    a, a_cases = record.read(a_dir)
    b, b_cases = record.read(b_dir)
    if a["suite"] != b["suite"]:
        raise CompareError(f"a {a['suite']} run and a {b['suite']} run are not paired")
    if a["suite"] == "generation":
        return compare_generation(a, a_cases, b, b_cases)
    for path in (("suite",), ("split",), ("dataset", "sha256"), ("retriever", "k")):
        if not _same(a, b, *path):
            raise CompareError(f"not the same {'.'.join(path)}: the runs are not paired")
    by_id = {str(c["case_id"]): c for c in b_cases}
    ids = [str(c["case_id"]) for c in a_cases]
    if set(ids) != set(by_id):
        raise CompareError("the runs do not have the same case ids")
    boot = as_json(a["bootstrap"])
    seed, resamples = cast(int, boot["seed"]), cast(int, boot["resamples"])
    level = cast(float, boot["level"])
    k = cast(int, as_json(a["retriever"])["k"])
    out_metrics: Json = {}
    changed: Json = {}
    for field, name in record.metric_names(k).items():
        va = [float(cast(float, c[field])) for c in a_cases]
        vb = [float(cast(float, by_id[i][field])) for i in ids]
        diff = metrics.paired_difference(va, vb, seed, resamples, level)
        out_metrics[name] = {
            "a": round(metrics.mean(va), 6),
            "b": round(metrics.mean(vb), 6),
            "diff": round(diff.value, 6),
            "ci_low": round(diff.low, 6),
            "ci_high": round(diff.high, 6),
            "n": diff.n,
        }
        changed[name] = {
            "better": [i for i, x, y in zip(ids, va, vb, strict=True) if y > x],
            "worse": [i for i, x, y in zip(ids, va, vb, strict=True) if y < x],
        }
    hit = as_json(changed[f"hit@{k}"])
    return {
        "schema_version": SCHEMA_VERSION,
        "a": a["run_id"],
        "b": b["run_id"],
        "a_config": as_json(a["config"])["name"],
        "b_config": as_json(b["config"])["name"],
        "suite": a["suite"],
        "split": a["split"],
        "dataset_sha256": as_json(a["dataset"])["sha256"],
        "n": len(ids),
        "bootstrap": {"resamples": resamples, "seed": seed, "level": level, "method": "percentile"},
        "metrics": out_metrics,
        "flipped": {"gained": hit["better"], "lost": hit["worse"]},
        "changed": changed,
    }


def _behaviour_by_case(cases: list[Json]) -> dict[str, list[Json]]:
    """Each behaviour case's trials, by case id, in the record's order."""
    grouped: dict[str, list[Json]] = {}
    for case in cases:
        if case["kind"] == behaviour.BEHAVIOUR:
            grouped.setdefault(str(case["case_id"]), []).append(case)
    return grouped


def _passed(trials: list[Json], name: str) -> list[bool]:
    return [bool(as_json(t["checks"]).get(name)) for t in trials]


def compare_generation(a: Json, a_cases: list[Json], b: Json, b_cases: list[Json]) -> Json:
    """Two generation runs paired by behaviour case id: behaviour pass^N and the decision-label
    rate per case, B minus A with a bootstrap over cases, and the flipped cases."""
    for path in (("split",), ("dataset", "sha256"), ("trials",)):
        if not _same(a, b, *path):
            raise CompareError(f"not the same {'.'.join(path)}: the runs are not paired")
    for run in (a, b):
        if run["partial"]:
            raise CompareError(f"{run['run_id']} is partial: a comparison reads complete runs")
    a_by, b_by = _behaviour_by_case(a_cases), _behaviour_by_case(b_cases)
    if not a_by:
        raise CompareError("the runs have no behaviour cases to compare")
    if set(a_by) != set(b_by):
        raise CompareError("the runs do not have the same behaviour cases")
    ids = list(a_by)  # A's order; every value below is looked up by case id, never by position
    trials = cast(int, a["trials"])
    seed = cast(int, a["seed"])
    level = cast(float, as_json(a["intervals"])["level"])
    resamples = metrics.DEFAULT_RESAMPLES

    def pass_n(trials_: list[Json]) -> float:
        return float(all(_passed(trials_, "passed")))

    def decision(trials_: list[Json]) -> float:
        right = _passed(trials_, "decision_label")
        return sum(right) / len(right)

    out_metrics: Json = {}
    changed: Json = {}
    for name, per_case in ((f"behaviour_pass^{trials}", pass_n), ("decision_label", decision)):
        va = [per_case(a_by[i]) for i in ids]
        vb = [per_case(b_by[i]) for i in ids]
        diff = metrics.paired_difference(va, vb, seed, resamples, level)
        out_metrics[name] = {
            "a": round(metrics.mean(va), 6),
            "b": round(metrics.mean(vb), 6),
            "diff": round(diff.value, 6),
            "ci_low": round(diff.low, 6),
            "ci_high": round(diff.high, 6),
            "n": diff.n,
        }
        changed[name] = {
            "better": [i for i, x, y in zip(ids, va, vb, strict=True) if y > x],
            "worse": [i for i, x, y in zip(ids, va, vb, strict=True) if y < x],
        }
    flips = as_json(changed[f"behaviour_pass^{trials}"])
    return {
        "schema_version": SCHEMA_VERSION,
        "a": a["run_id"],
        "b": b["run_id"],
        "a_config": as_json(a["config"])["name"],
        "b_config": as_json(b["config"])["name"],
        "suite": "generation",
        "split": a["split"],
        "dataset_sha256": as_json(a["dataset"])["sha256"],
        "trials": trials,
        "n": len(ids),
        "bootstrap": {"resamples": resamples, "seed": seed, "level": level, "method": "percentile"},
        "metrics": out_metrics,
        "flipped": {"gained": flips["better"], "lost": flips["worse"]},
        "changed": changed,
    }


def _fmt(value: object) -> str:
    return f"{cast(float, value):+.3f}"


def render(result: Json) -> str:
    level = round(cast(float, as_json(result["bootstrap"])["level"]) * 100)
    generation = result["suite"] == "generation"
    paired = "behaviour cases (by case id)" if generation else "questions"
    lines = [
        f"# Compare {result['a_config']} (A) with {result['b_config']} (B)",
        "",
        "Generated by `raglab compare`; never edited by hand.",
        "",
        f"- A: `{result['a']}`",
        f"- B: `{result['b']}`",
        f"- {result['n']} paired {paired}, split {result['split']}; differences are B minus A, "
        f"with a {level}% paired bootstrap interval "
        f"({as_json(result['bootstrap'])['resamples']} resamples, "
        f"seed {as_json(result['bootstrap'])['seed']}).",
        "",
        f"| Metric | A | B | B minus A | {level}% interval | n |",
        "|---|---|---|---|---|---|",
    ]
    for name, raw in as_json(result["metrics"]).items():
        m = as_json(raw)
        lines.append(
            f"| {name} | {cast(float, m['a']):.3f} | {cast(float, m['b']):.3f} | "
            f"{_fmt(m['diff'])} | {_fmt(m['ci_low'])} to {_fmt(m['ci_high'])} | {m['n']} |"
        )
    flipped = as_json(result["flipped"])
    gained = cast(list[str], flipped["gained"])
    lost = cast(list[str], flipped["lost"])
    if generation:
        heading = f"## Flipped cases (behaviour pass^{result['trials']})"
        b_only, a_only = "Passed every trial in B only", "Passed every trial in A only"
        flip_metric = f"behaviour_pass^{result['trials']}"
    else:
        heading = "## Flipped questions (hit)"
        b_only, a_only = "Found by B only", "Found by A only"
        flip_metric = ""
    lines += [
        "",
        heading,
        "",
        f"- {b_only} ({len(gained)}): {', '.join(gained) or 'none'}",
        f"- {a_only} ({len(lost)}): {', '.join(lost) or 'none'}",
        "",
        "## Other changes",
        "",
    ]
    for name, raw in as_json(result["changed"]).items():
        if name.startswith("hit@") or name == flip_metric:
            continue
        c = as_json(raw)
        better = cast(list[str], c["better"])
        worse = cast(list[str], c["worse"])
        lines.append(
            f"- {name}: better in B for {', '.join(better) or 'none'}; "
            f"worse in B for {', '.join(worse) or 'none'}"
        )
    return "\n".join(lines) + "\n"


def write(result: Json, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "compare.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (out_dir / "compare.md").write_text(render(result), encoding="utf-8")
    return out_dir
