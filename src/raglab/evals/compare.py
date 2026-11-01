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

Two judged runs (S8, GA6) must be valid run records of the same split, dataset (sha256) and trials
under one judge (the one-judge test's fields: the judge model and digest, the judge prompt's
version and fingerprint, CRITERIA.md's sha256, the canary set's), over the same cases. Per
criterion, each case's pass share over its judged verdicts (the first-pass `verdicts`, never the
repeat or order checks; a case with no verdict on a criterion in either run is left out of that
criterion), B minus A with the same paired bootstrap, and the cases whose share moved. Nothing
here gates: `raglab gate --judged` reads this comparison with the calibration record
(raglab.evals.judged_gate).

`write` puts compare.json and compare.md (generated, never edited) in a directory of their own.
"""

import json
from pathlib import Path
from typing import cast

from raglab.evals import behaviour, judged_record, metrics, record
from raglab.evals.record import Json, as_json

SCHEMA_VERSION = "compare.v1"
# the fields two judged records must share to compare under one judge (S8, GA6)
JUDGE_IDENTITY = (
    ("judge", "model"),
    ("judge", "digest"),
    ("judge_prompt", "version"),
    ("judge_prompt", "sha256"),
    ("criteria", "sha256"),
    ("canaries", "sha256"),
)


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
    if a["suite"] == judged_record.JUDGED:  # S8
        return compare_judged(a, a_cases, b, b_cases)
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


def judge_identity(manifest: Json) -> Json:
    """What names the judge of a judged record (JUDGE_IDENTITY), as the comparison records it."""
    return {f"{part}.{key}": as_json(manifest[part])[key] for part, key in JUDGE_IDENTITY}


def _pass_share(trials: list[Json], criterion: str) -> float | None:
    """A case's pass share on one criterion over its judged verdicts; None when none."""
    verdicts = [
        as_json(as_json(t.get("verdicts") or {})[criterion])
        for t in trials
        if criterion in as_json(t.get("verdicts") or {})
    ]
    if not verdicts:
        return None
    return sum(v["verdict"] == "pass" for v in verdicts) / len(verdicts)


def compare_judged(a: Json, a_cases: list[Json], b: Json, b_cases: list[Json]) -> Json:
    """Two judged runs under one judge, paired by case id: per criterion, B minus A of the
    case's pass share with a bootstrap over cases, and the cases whose share moved."""
    for path in (("split",), ("dataset", "sha256"), ("trials",)):
        if not _same(a, b, *path):
            raise CompareError(f"not the same {'.'.join(path)}: the runs are not paired")
    for part, key in JUDGE_IDENTITY:
        if not _same(a, b, part, key):
            raise CompareError(
                f"not the same {part}.{key}: two judged runs compare only under one judge"
            )
    for run in (a, b):
        if run["partial"]:
            raise CompareError(f"{run['run_id']} is partial: a comparison reads complete runs")
    a_by, b_by = record_by_case(a_cases), record_by_case(b_cases)
    if set(a_by) != set(b_by):
        raise CompareError("the runs do not have the same cases")
    ids = list(a_by)
    seed = cast(int, a["seed"])
    level = cast(float, as_json(a["intervals"])["level"])
    resamples = metrics.DEFAULT_RESAMPLES
    criteria = [
        name
        for name in judged_record.CRITERIA_ORDER
        if any(name in as_json(t.get("verdicts") or {}) for i in ids for t in a_by[i])
    ]
    if not criteria:
        raise CompareError("the runs have no judged verdicts to compare")
    out_metrics: Json = {}
    changed: Json = {}
    for criterion in criteria:
        pairs = [
            (i, x, y)
            for i in ids
            for x in [_pass_share(a_by[i], criterion)]
            for y in [_pass_share(b_by[i], criterion)]
            if x is not None and y is not None
        ]
        if not pairs:
            continue
        va, vb = [x for _, x, _ in pairs], [y for _, _, y in pairs]
        diff = metrics.paired_difference(va, vb, seed, resamples, level)
        out_metrics[criterion] = {
            "a": round(metrics.mean(va), 6),
            "b": round(metrics.mean(vb), 6),
            "diff": round(diff.value, 6),
            "ci_low": round(diff.low, 6),
            "ci_high": round(diff.high, 6),
            "n": diff.n,
        }
        changed[criterion] = {
            "better": [i for i, x, y in pairs if y > x],
            "worse": [i for i, x, y in pairs if y < x],
        }
    first = as_json(changed[next(iter(out_metrics))])
    return {
        "schema_version": SCHEMA_VERSION,
        "a": a["run_id"],
        "b": b["run_id"],
        "a_config": as_json(a["config"])["name"],
        "b_config": as_json(b["config"])["name"],
        "suite": judged_record.JUDGED,
        "split": a["split"],
        "dataset_sha256": as_json(a["dataset"])["sha256"],
        "trials": a["trials"],
        "n": len(ids),
        "judge": judge_identity(a),
        "sources": {"a": as_json(a["source"])["run_id"], "b": as_json(b["source"])["run_id"]},
        "bootstrap": {"resamples": resamples, "seed": seed, "level": level, "method": "percentile"},
        "metrics": out_metrics,
        "flipped": {"gained": first["better"], "lost": first["worse"]},
        "changed": changed,
    }


def record_by_case(cases: list[Json]) -> dict[str, list[Json]]:
    """Each case's lines, by case id, in the record's order."""
    grouped: dict[str, list[Json]] = {}
    for case in cases:
        grouped.setdefault(str(case["case_id"]), []).append(case)
    return grouped


def _fmt(value: object) -> str:
    return f"{cast(float, value):+.3f}"


def render(result: Json) -> str:
    level = round(cast(float, as_json(result["bootstrap"])["level"]) * 100)
    generation = result["suite"] == "generation"
    judged = result["suite"] == judged_record.JUDGED
    paired = (
        "behaviour cases (by case id)"
        if generation
        else "cases (by case id; per criterion, the case's pass share over its judged verdicts)"
        if judged
        else "questions"
    )
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
    if judged:
        identity = as_json(result["judge"])
        sources = as_json(result["sources"])
        lines[7:7] = [
            f"- One judge: {identity['judge.model']} (digest "
            f"{str(identity['judge.digest'])[:12]}), {identity['judge_prompt.version']} "
            f"(sha256 {str(identity['judge_prompt.sha256'])[:12]}), CRITERIA.md "
            f"{str(identity['criteria.sha256'])[:12]}, canaries "
            f"{str(identity['canaries.sha256'])[:12]}; the sources are `{sources['a']}` (A) and "
            f"`{sources['b']}` (B). Nothing here gates: `raglab gate --judged` reads the "
            "calibration record.",
        ]
    flipped = as_json(result["flipped"])
    gained = cast(list[str], flipped["gained"])
    lost = cast(list[str], flipped["lost"])
    if generation:
        heading = f"## Flipped cases (behaviour pass^{result['trials']})"
        b_only, a_only = "Passed every trial in B only", "Passed every trial in A only"
        flip_metric = f"behaviour_pass^{result['trials']}"
    elif judged:
        flip_metric = next(iter(as_json(result["metrics"])))
        heading = f"## Cases whose pass share moved ({flip_metric})"
        b_only, a_only = "Higher in B", "Higher in A"
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
