"""Run record v1: a directory per run with manifest.json, cases.jsonl and report.md.

- `write` puts the cases and the generated report in place, then the manifest with the sha256 of
  both files.
- `validate` reads a run directory back and lists every problem: the schema
  (schemas/run-record.v1.json, both files read as one object), the run id against the directory
  name, the file hashes, the case count, the results recomputed from the cases (the same seeded
  bootstrap gives the same intervals), and report.md against a fresh render, so the report is
  never edited by hand.

The report and the cases carry chunk ids and scores, never chunk text.
"""

import hashlib
import json
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from raglab.evals import metrics
from raglab.evals.schema import Validator

SCHEMA_VERSION = "run-record.v1"
SCHEMA_PATH = "schemas/run-record.v1.json"
MANIFEST = "manifest.json"
CASES = "cases.jsonl"
REPORT = "report.md"

type Json = dict[str, object]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def as_json(value: object) -> Json:
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object, got {type(value).__name__}")
    return {str(k): v for k, v in cast(dict[object, object], value).items()}


def as_list(value: object) -> list[object]:
    if not isinstance(value, list):
        raise ValueError(f"expected a JSON array, got {type(value).__name__}")
    return list(cast(list[object], value))


def metric_names(k: int) -> dict[str, str]:
    """The manifest's metric names, keyed by the case field each is the mean of."""
    return {"hit": f"hit@{k}", "reciprocal_rank": f"mrr@{k}", "recall": f"recall@{k}"}


def results_from_cases(cases: Sequence[Json], k: int, bootstrap: Json) -> Json:
    """Each metric's mean over the cases with its bootstrap interval, as the manifest holds it."""
    seed = cast(int, bootstrap["seed"])
    resamples = cast(int, bootstrap["resamples"])
    level = cast(float, bootstrap["level"])
    out: Json = {}
    for field, name in metric_names(k).items():
        values = [float(cast(float, c[field])) for c in cases]
        out[name] = metrics.bootstrap_interval(values, seed, resamples, level).as_json()
    return {"metrics": out}


def _fmt(value: object) -> str:
    return f"{cast(float, value):.3f}"


def render_report(manifest: Json, cases: Sequence[Json]) -> str:
    """report.md, generated from the manifest (without its files block) and the cases."""
    config, chunker = as_json(manifest["config"]), as_json(manifest["chunker"])
    embedder, retriever = as_json(manifest["embedder"]), as_json(manifest["retriever"])
    dataset, corpus = as_json(manifest["dataset"]), as_json(manifest["corpus"])
    boot = as_json(manifest["bootstrap"])
    results = as_json(as_json(manifest["results"])["metrics"])
    k = cast(int, retriever["k"])
    retriever_text = f"{retriever['kind']}, k = {k}"
    if retriever["kind"] == "hybrid":
        retriever_text += (
            f" (dense and BM25, {retriever['candidates']} candidates each, "
            f"reciprocal rank fusion with k = {retriever['rrf_k']})"
        )
    level = round(cast(float, boot["level"]) * 100)
    lines = [
        f"# Run {manifest['run_id']}",
        "",
        "Generated from manifest.json and cases.jsonl by raglab; never edited by hand.",
        "",
        "| | |",
        "|---|---|",
        f"| Suite | {manifest['suite']}, split {manifest['split']}, "
        f"{manifest['trials']} trial(s), gate {manifest['gate']} |",
        f"| Provenance | {manifest['provenance']} |",
        f"| Created | {manifest['created_at']} |",
        f"| Git | {manifest['git_sha']} ({'dirty' if manifest['git_dirty'] else 'clean'}) |",
        f"| Config | {config['name']} (`{config['path']}`, sha256 {str(config['sha256'])[:12]}) |",
        f"| Embedder | {embedder['model']} at revision {str(embedder['revision'])[:12]} "
        f"({embedder['provider']}, dimension {embedder['dimension']}) |",
        f"| Retriever | {retriever_text} |",
        f"| Chunker | {chunker['chunk_size']} characters, overlap {chunker['overlap']} |",
        f"| Corpus | {corpus['documents']} documents, {corpus['chunks']} chunks, "
        f"sha256 {str(corpus['sha256'])[:12]} |",
        f"| Dataset | `{dataset['path']}`, sha256 {str(dataset['sha256'])[:12]}, "
        f"{dataset['questions']} questions in this run |",
        f"| Bootstrap | {boot['resamples']} resamples, seed {boot['seed']}, "
        f"{level}% percentile interval |",
        "",
        "## Metrics",
        "",
        f"Labels are sections; a section is found when any of its chunks is in the top {k}.",
        "",
        f"| Metric | Value | {level}% interval | n |",
        "|---|---|---|---|",
    ]
    for name, raw in results.items():
        item = as_json(raw)
        lines.append(
            f"| {name} | {_fmt(item['value'])} | {_fmt(item['ci_low'])} to "
            f"{_fmt(item['ci_high'])} | {item['n']} |"
        )
    lines += [
        "",
        "## Questions",
        "",
        f"Top {k} chunk ids, best first; a labelled section's chunks are marked `*`.",
        "",
        "| Case | Split | Tenant | Kind | Hit | RR | Recall | Retrieved |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for case in cases:
        retrieved = ", ".join(
            f"{r['chunk_id']}{'*' if r['relevant'] else ''}"
            for r in (as_json(x) for x in as_list(case["retrieved"]))
        )
        lines.append(
            f"| {case['case_id']} | {case['split']} | {case['tenant']} | "
            f"{case.get('question_kind', '')} | {case['hit']} | {_fmt(case['reciprocal_rank'])} | "
            f"{_fmt(case['recall'])} | {retrieved} |"
        )
    return "\n".join(lines) + "\n"


def cases_text(cases: Sequence[Json]) -> str:
    return "".join(json.dumps(c, sort_keys=True, ensure_ascii=False) + "\n" for c in cases)


def write(parent: Path, manifest: Json, cases: Sequence[Json]) -> Path:
    """Write the run under parent/<run_id>/ and return that directory. The manifest's files
    block is filled here."""
    run_dir = parent / str(manifest["run_id"])
    if run_dir.exists():
        raise FileExistsError(f"{run_dir} already exists")
    run_dir.mkdir(parents=True)
    body = {k: v for k, v in manifest.items() if k != "files"}
    cases_bytes = cases_text(cases).encode("utf-8")
    report_bytes = render_report(body, cases).encode("utf-8")
    (run_dir / CASES).write_bytes(cases_bytes)
    (run_dir / REPORT).write_bytes(report_bytes)
    full = {
        **body,
        "files": {CASES: sha256_bytes(cases_bytes), REPORT: sha256_bytes(report_bytes)},
    }
    (run_dir / MANIFEST).write_text(
        json.dumps(full, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return run_dir


def read(run_dir: Path) -> tuple[Json, list[Json]]:
    manifest = as_json(json.loads((run_dir / MANIFEST).read_text(encoding="utf-8")))
    lines = (run_dir / CASES).read_text(encoding="utf-8").splitlines()
    return manifest, [as_json(json.loads(line)) for line in lines if line.strip()]


def schema_validator(root: Path) -> Validator:
    return Validator(as_json(json.loads((root / SCHEMA_PATH).read_text(encoding="utf-8"))))


def case_scores(retrieved: Sequence[str], labels: Sequence[frozenset[str]], k: int) -> Json:
    """A case's metric fields, from its retrieved ids and its labels' chunk ids (rounded to six
    places, the precision the record keeps and the results are computed from)."""
    return {
        "hit": metrics.hit_at_k(retrieved, labels, k),
        "reciprocal_rank": round(metrics.reciprocal_rank(retrieved, labels, k), 6),
        "recall": round(metrics.recall_at_k(retrieved, labels, k), 6),
    }


def case_problems(case: Json, k: int) -> list[str]:
    """A case whose scores, ranks or flags do not follow from its retrieved ids and labels."""
    labels = [as_json(x) for x in as_list(case["labels"])]
    sets = [frozenset(str(i) for i in as_list(label["chunk_ids"])) for label in labels]
    rows = [as_json(x) for x in as_list(case["retrieved"])]
    ids = [str(r["chunk_id"]) for r in rows]
    problems: list[str] = []
    where = f"case {case['case_id']}"
    if len(ids) > k or [r["rank"] for r in rows] != list(range(1, len(rows) + 1)):
        problems.append(f"{where}: retrieved must be ranks 1 to n, at most k = {k}")
    relevant = frozenset[str]().union(*sets)
    if [r["relevant"] for r in rows] != [i in relevant for i in ids]:
        problems.append(f"{where}: a retrieved chunk's relevant flag is wrong")
    if [label["found"] for label in labels] != [bool(set(ids) & s) for s in sets]:
        problems.append(f"{where}: a label's found flag is wrong")
    expected = case_scores(ids, sets, k)
    actual = {name: case[name] for name in expected}
    if actual != expected:
        problems.append(f"{where}: scores {actual} do not follow from the ranks ({expected})")
    return problems


def validate(run_dir: Path, root: Path) -> list[str]:
    """Every problem with the run at run_dir; [] when it is a valid run record v1."""
    for name in (MANIFEST, CASES, REPORT):
        if not (run_dir / name).is_file():
            return [f"{run_dir.name}: {name} is missing"]
    try:
        manifest, cases = read(run_dir)
    except (ValueError, UnicodeDecodeError) as error:
        return [f"{run_dir.name}: unreadable ({error})"]
    problems = schema_validator(root).errors({"manifest": manifest, "cases": cases})
    if problems:
        return problems  # the checks below assume the shape the schema guarantees
    if manifest["run_id"] != run_dir.name:
        problems.append(f"run_id {manifest['run_id']} is not the directory name {run_dir.name}")
    files = as_json(manifest["files"])
    for name in (CASES, REPORT):
        actual = sha256_bytes((run_dir / name).read_bytes())
        if files[name] != actual:
            problems.append(f"{name}: sha256 {actual} is not the manifest's {files[name]}")
    totals = as_json(manifest["totals"])
    if totals["cases"] != len(cases):
        problems.append(f"totals.cases {totals['cases']} but cases.jsonl has {len(cases)} lines")
    ids = [str(c["case_id"]) for c in cases]
    if len(set(ids)) != len(ids):
        problems.append("a case id appears twice in cases.jsonl")
    k = cast(int, as_json(manifest["retriever"])["k"])
    problems.extend(problem for case in cases for problem in case_problems(case, k))
    expected = results_from_cases(cases, k, as_json(manifest["bootstrap"]))
    if manifest["results"] != expected:
        problems.append(
            f"results do not match the cases: manifest {manifest['results']}, recomputed {expected}"
        )
    body = {k2: v for k2, v in manifest.items() if k2 != "files"}
    if (run_dir / REPORT).read_text(encoding="utf-8") != render_report(body, cases):
        problems.append("report.md is not the report generated from the manifest and the cases")
    return problems
