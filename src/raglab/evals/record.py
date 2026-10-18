"""Run record v1: a directory per run with manifest.json, cases.jsonl and report.md.

- `write` puts the cases and the generated report in place, then the manifest with the sha256 of
  both files.
- `validate` reads a run directory back and lists every problem: the schema
  (schemas/run-record.v1.json, both files read as one object), the run id against the directory
  name, the file hashes, the case count, the results recomputed from the cases (the same seeded
  bootstrap gives the same intervals), report.md against a fresh render, so the report is never
  edited by hand, and the tenants: every retrieved and labelled chunk id names a document of the
  register (corpus/register.yaml) that the case's tenant may see, so a record that shows another
  tenant's chunk is refused even when its flags, scores, hashes and report agree (S2 judge D3).
- The provenance against the models (S3 judge S3-S2): a run whose embedder or generator is a
  fake (provider fake, or a fake revision or digest) has provenance fake, whatever else its label
  says, so a fake run relabelled local is refused even when its hashes and report agree.
- The suite (S3): a retrieval run has bootstrap intervals and every case its labels and scores; a
  generation run (raglab.evals.generation_record) has the generator, the prompt, the guards, the
  probes and Wilson intervals, one line per case and trial, and every case its answer fields, its
  checks recomputed, and no cited id that was not retrieved for it. Fields of one suite are
  refused in the other.

The report and the cases carry chunk ids and scores, never chunk text.
"""

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

from raglab.core.types import visible_tenants
from raglab.evals import generation_record, metrics
from raglab.evals.schema import Validator
from raglab.ingest import answer_key, register

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
    report_bytes = render(body, cases).encode("utf-8")
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


def doc_tenants(root: Path) -> dict[str, str]:
    """Each registered document's tenant, from corpus/register.yaml under root."""
    return {entry.doc_id: entry.tenant for entry in register.read(root)}


def tenant_problems(case: Json, tenants: Mapping[str, str]) -> list[str]:
    """A retrieved or labelled chunk whose document is not in the register, or belongs to a
    tenant the case's tenant may not see. A chunk id is `<doc id>@<version>/<section>/<n>`."""
    where = f"case {case['case_id']} ({case['tenant']})"
    visible = visible_tenants(case["tenant"])
    ids = [str(as_json(r)["chunk_id"]) for r in as_list(case["retrieved"])]
    ids += [
        str(i)
        for label in as_list(case.get("labels", []))
        for i in as_list(as_json(label)["chunk_ids"])
    ]
    if "cited_ids" in case:  # a generation case: what it cites is checked too
        ids += sorted(generation_record.referenced(case))
    problems: list[str] = []
    for chunk_id in ids:
        doc = chunk_id.split("@", 1)[0]
        tenant = tenants.get(doc)
        if tenant is None:
            problems.append(f"{where}: chunk {chunk_id} names {doc}, which is not in the register")
        elif tenant not in visible:
            problems.append(f"{where}: chunk {chunk_id} is {tenant}, which it cannot see")
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
    problems.extend(provenance_problems(manifest))
    keys = [(str(c["case_id"]), c["trial"]) for c in cases]
    if len(set(keys)) != len(keys):
        problems.append("a case id and trial appear twice in cases.jsonl")
    k = cast(int, as_json(manifest["retriever"])["k"])
    if manifest["suite"] == "generation":
        problems.extend(generation_problems(manifest, cases, k, root))
    else:
        problems.extend(retrieval_problems(manifest, cases, k))
    try:
        tenants = doc_tenants(root)
    except (OSError, ValueError) as error:  # the register fails closed: no check, no valid run
        problems.append(f"the register cannot be read, so the tenants are unchecked ({error})")
    else:
        problems.extend(problem for case in cases for problem in tenant_problems(case, tenants))
    body = {k2: v for k2, v in manifest.items() if k2 != "files"}
    try:
        expected = expected_results(manifest, cases)
        report = render(body, cases)
    except (KeyError, ValueError, TypeError) as error:  # a field the suite needs is missing
        problems.append(f"the results and report cannot be recomputed ({error!r})")
        return problems
    if manifest["results"] != expected:
        problems.append(
            f"results do not match the cases: manifest {manifest['results']}, recomputed {expected}"
        )
    if (run_dir / REPORT).read_text(encoding="utf-8") != report:
        problems.append("report.md is not the report generated from the manifest and the cases")
    return problems


# ---------------------------------------------------------------- the suites (S3)


def fake_models(manifest: Json) -> list[str]:
    """The model fields that say a fake made this run: a fake provider, revision or digest."""
    found: list[str] = []
    for part, fields in (
        ("embedder", ("provider", "revision")),
        ("generator", ("provider", "digest")),
    ):
        if part not in manifest:
            continue
        described = as_json(manifest[part])
        found += [f"{part}.{field} fake" for field in fields if described.get(field) == "fake"]
    return found


def provenance_problems(manifest: Json) -> list[str]:
    """A run made with a fake model whose provenance is not fake."""
    fake = fake_models(manifest)
    if fake and manifest["provenance"] != "fake":
        return [
            f"provenance {manifest['provenance']} but {', '.join(fake)}: a run made with a fake "
            "model has provenance fake"
        ]
    return []


GENERATION_MANIFEST = ("generator", "prompt", "guards", "intervals", "probes")


def render(manifest: Json, cases: Sequence[Json]) -> str:
    """report.md for the run's suite."""
    if manifest["suite"] == "generation":
        return generation_record.render_report(manifest, cases)
    return render_report(manifest, cases)


def expected_results(manifest: Json, cases: Sequence[Json]) -> Json:
    """The results block recomputed from the cases, for the run's suite."""
    if manifest["suite"] == "generation":
        level = cast(float, as_json(manifest["intervals"])["level"])
        return generation_record.results(cases, cast(int, manifest["trials"]), level)
    k = cast(int, as_json(manifest["retriever"])["k"])
    return results_from_cases(cases, k, as_json(manifest["bootstrap"]))


def retrieval_problems(manifest: Json, cases: Sequence[Json], k: int) -> list[str]:
    """A retrieval run: bootstrap intervals, one trial, every case its labels and scores, and no
    field of a generation run."""
    problems: list[str] = []
    if "bootstrap" not in manifest:
        problems.append("a retrieval run has bootstrap intervals: missing 'bootstrap'")
    extra = [f for f in (*GENERATION_MANIFEST, "ollama") if f in manifest]
    if extra or "generation" in as_json(manifest["results"]):
        problems.append(
            f"a retrieval run has no generation fields: {extra or ['results.generation']}"
        )
    for case in cases:
        where = f"case {case['case_id']}"
        if missing := [f for f in generation_record.RETRIEVAL_FIELDS if f not in case]:
            problems.append(f"{where}: a retrieval case needs {missing}")
            continue
        if extra := [f for f in generation_record.ANSWER_FIELDS if f in case]:
            problems.append(f"{where}: a retrieval case has no answer fields: {extra}")
        problems.extend(case_problems(case, k))
    return problems


def generation_problems(manifest: Json, cases: Sequence[Json], k: int, root: Path) -> list[str]:
    """A generation run: its manifest fields, N trials of every case (fewer only in a partial
    run), every case's answer fields, a withheld answer for every status but ok, no cited id that
    was not retrieved, retrieval scores on the questions and none on the probes, and the checks
    as the fields give them."""
    problems: list[str] = []
    if missing := [f for f in GENERATION_MANIFEST if f not in manifest]:
        problems.append(f"a generation run needs {missing}")
    if "bootstrap" in manifest:
        problems.append("a generation run has Wilson intervals, not bootstrap ones")
    if "generation" not in as_json(manifest["results"]):
        problems.append("a generation run needs results.generation")
    if problems:
        return problems
    trials = cast(int, manifest["trials"])
    try:
        canaries = answer_key.canaries(root)
    except (OSError, ValueError) as error:  # fails closed, as the register does
        return [f"the answer key's canaries cannot be read, so the probes are unchecked ({error})"]
    seen: dict[str, list[int]] = {}
    for case in cases:
        where = f"case {case['case_id']} trial {case['trial']}"
        seen.setdefault(str(case["case_id"]), []).append(cast(int, case["trial"]))
        if missing := [f for f in generation_record.ANSWER_FIELDS if f not in case]:
            problems.append(f"{where}: a generation case needs {missing}")
            continue
        kind_fields = (
            generation_record.PROBE_FIELDS
            if case["kind"] == generation_record.PROBE
            else generation_record.RETRIEVAL_FIELDS
        )
        other_fields = (
            generation_record.RETRIEVAL_FIELDS
            if case["kind"] == generation_record.PROBE
            else generation_record.PROBE_FIELDS
        )
        if missing := [f for f in kind_fields if f not in case]:
            problems.append(f"{where}: a {case['kind']} case needs {missing}")
            continue
        if extra := [f for f in other_fields if f in case]:
            problems.append(f"{where}: a {case['kind']} case has no {extra}")
            continue
        if case["status"] != "ok" and (
            case["answer"] or case["cited_ids"] or case["conflict"] or case["label"] != "abstain"
        ):
            problems.append(f"{where}: a {case['status']} answer is withheld (abstain, no text)")
        retrieved = {str(as_json(r)["chunk_id"]) for r in as_list(case["retrieved"])}
        guards = [str(as_json(e)["guard"]) for e in as_list(case["guard_events"])]
        if generation_record.CITATIONS_GUARD in guards and case["status"] != "blocked":
            problems.append(f"{where}: the citation validator fired, so the answer is blocked")
        if unretrieved := sorted(generation_record.referenced(case) - retrieved):
            problems.append(f"{where}: cites ids that were not retrieved: {unretrieved}")
        if case["kind"] == generation_record.RETRIEVAL:
            problems.extend(case_problems(case, k))
        elif any(as_json(r)["relevant"] for r in as_list(case["retrieved"])):
            problems.append(f"{where}: a probe has no labels, so no retrieved chunk is relevant")
        if case["checks"] != generation_record.case_checks(case, canaries):
            problems.append(f"{where}: checks {case['checks']} do not follow from the fields")
    for case_id, numbers in seen.items():
        full = list(range(1, trials + 1))
        if sorted(numbers) != full and not (
            manifest["partial"] and sorted(numbers) == full[: len(numbers)]
        ):
            problems.append(f"case {case_id}: trials {sorted(numbers)}, not 1 to {trials}")
    return problems
