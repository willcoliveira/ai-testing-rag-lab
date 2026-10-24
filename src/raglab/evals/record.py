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
  generation run (raglab.evals.generation_record) has the generator, the prompt, the guards and
  Wilson intervals (and the probes block when it has probe cases: S4 made it optional), one line
  per case and trial, and every case its answer fields and those of its kind, its checks
  recomputed, and no cited id that was not retrieved for it. Fields of one suite are refused in
  the other.
- S4: label groups (`any_of`: the primary's ids, every member's chunks together) and the behaviour
  case kind (raglab.evals.behaviour), whose checks are recomputed from its fields and the answer
  key's canaries and answer_must_not_contain strings, read live.
- S4, the fields a behaviour case's checks rest on (the orchestrator's decision; the same class of
  gap as S3-S2, publish trusting a label): when a generation record's dataset sha256 is that of the
  golden file at its dataset path under root, each behaviour case's expected label, mix and
  features, its labels with their groups and conflict sides, and its may_quote section with its
  chunks and their values are derived again from the golden file, the answer key and the corpus
  (the may_quote document chunked at the record's settings), and a difference is refused. A record
  of another dataset version keeps its recorded fields, as history (the S2 and S3 runs).

The report and the cases carry chunk ids and scores, never chunk text.
"""

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

from raglab.chunk.sections import ChunkSettings
from raglab.core.types import visible_tenants
from raglab.evals import (
    behaviour,
    generation_record,
    golden,
    judged_record,
    metrics,
    position_record,
)
from raglab.evals.schema import Validator
from raglab.ingest import answer_key, pipeline, register

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


def group_note(cases: Sequence[Json]) -> str:
    """The sentence a report adds when a case has a label group (S4); none otherwise, so the
    reports of earlier runs render as they did."""
    grouped = any(
        "any_of" in as_json(label) for case in cases for label in as_list(case.get("labels", []))
    )
    if not grouped:
        return ""
    return (
        " A group of sections that state the same rule (any_of) is one thing to find: found, and"
        " ranked, by the first chunk of any member."
    )


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
        f"Labels are sections; a section is found when any of its chunks is in the top {k}."
        + group_note(cases),
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


def group_problems(label: Json, where: str) -> list[str]:
    """A label group (S4, `any_of`) is one thing to find: its ids are its primary (first)
    member's, and its chunk ids are every member's chunks together, in member order, each once."""
    if "any_of" not in label:
        return []
    group = [as_json(m) for m in as_list(label["any_of"])]
    problems: list[str] = []
    if (label["doc_id"], label["section_id"]) != (group[0]["doc_id"], group[0]["section_id"]):
        problems.append(f"{where}: a group's doc_id and section_id are its first member's")
    union = list(dict.fromkeys(str(i) for m in group for i in as_list(m["chunk_ids"])))
    if [str(i) for i in as_list(label["chunk_ids"])] != union:
        problems.append(f"{where}: a group's chunk_ids are not its members' chunks together")
    return problems


def case_problems(case: Json, k: int) -> list[str]:
    """A case whose scores, ranks or flags do not follow from its retrieved ids and labels."""
    labels = [as_json(x) for x in as_list(case["labels"])]
    sets = [frozenset(str(i) for i in as_list(label["chunk_ids"])) for label in labels]
    rows = [as_json(x) for x in as_list(case["retrieved"])]
    ids = [str(r["chunk_id"]) for r in rows]
    problems: list[str] = []
    where = f"case {case['case_id']}"
    for label in labels:
        problems.extend(group_problems(label, where))
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
    labels = [as_json(label) for label in as_list(case.get("labels", []))]
    ids += [str(i) for label in labels for i in as_list(label["chunk_ids"])]
    ids += [  # a group's members, in case its chunk_ids were edited apart from them
        str(i)
        for label in labels
        for member in as_list(label.get("any_of", []))
        for i in as_list(as_json(member)["chunk_ids"])
    ]
    if "cited_ids" in case:  # a generation case: what it cites is checked too
        ids += sorted(generation_record.referenced(case))
    if "may_quote" in case:  # a behaviour case's quotable section (S4)
        quote = as_json(case["may_quote"])
        ids += [str(as_json(c)["chunk_id"]) for c in as_list(quote["chunks"])]
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
    problems.extend(label_chunk_problems(manifest, cases, root))
    keys = [(str(c["case_id"]), c["trial"]) for c in cases]
    if len(set(keys)) != len(keys):
        problems.append("a case id and trial appear twice in cases.jsonl")
    k = cast(int, as_json(manifest["retriever"])["k"])
    if manifest["suite"] == "generation":
        problems.extend(generation_problems(manifest, cases, k, root))
    elif manifest["suite"] == judged_record.JUDGED:  # S5
        problems.extend(judged_record.judged_problems(manifest, cases, run_dir, root))
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
        ("judge", ("provider", "digest")),  # S5: a judged run's judge model
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


# the probes block is S3's: a run without probe cases has none (S4), one with them needs it
GENERATION_MANIFEST = ("generator", "prompt", "guards", "intervals")
BEHAVIOUR_ONLY = ("mix", "may_quote")


def kind_fields(case: Json) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """(required, refused) fields of a generation case of its kind: a retrieval question has its
    labels and scores; a probe (S3) its expected label, features and canaries_of; a behaviour case
    (S4) its expected label, features and mix, with labels and scores unless it abstains, and a
    may_quote section only if it abstains."""
    kind = case["kind"]
    if kind == position_record.POSITION:  # S5: the position test
        return position_record.POSITION_FIELDS, (
            "canaries_of",
            *BEHAVIOUR_ONLY,
            *generation_record.RETRIEVAL_FIELDS,
        )
    if kind == generation_record.PROBE:
        return generation_record.PROBE_FIELDS, (
            *generation_record.RETRIEVAL_FIELDS,
            *BEHAVIOUR_ONLY,
        )
    if kind == generation_record.BEHAVIOUR:
        if case.get("expected") == "abstain":
            return behaviour.BEHAVIOUR_FIELDS, ("canaries_of", *generation_record.RETRIEVAL_FIELDS)
        return (
            (*behaviour.BEHAVIOUR_FIELDS, *generation_record.RETRIEVAL_FIELDS),
            ("canaries_of", "may_quote"),
        )
    return generation_record.RETRIEVAL_FIELDS, (*generation_record.PROBE_FIELDS, *BEHAVIOUR_ONLY)


def render(manifest: Json, cases: Sequence[Json]) -> str:
    """report.md for the run's suite."""
    if manifest["suite"] == "generation":
        return generation_record.render_report(manifest, cases)
    if manifest["suite"] == judged_record.JUDGED:
        return judged_record.render_report(manifest, cases)
    return render_report(manifest, cases)


def expected_results(manifest: Json, cases: Sequence[Json]) -> Json:
    """The results block recomputed from the cases, for the run's suite."""
    if manifest["suite"] == "generation":
        level = cast(float, as_json(manifest["intervals"])["level"])
        position = as_json(manifest["position"]) if "position" in manifest else None
        return generation_record.results(cases, cast(int, manifest["trials"]), level, position)
    if manifest["suite"] == judged_record.JUDGED:
        level = cast(float, as_json(manifest["intervals"])["level"])
        canary_rows = [as_json(r) for r in as_list(as_json(manifest["canaries"])["results"])]
        return judged_record.results(cases, cast(int, manifest["trials"]), level, canary_rows)
    k = cast(int, as_json(manifest["retriever"])["k"])
    return results_from_cases(cases, k, as_json(manifest["bootstrap"]))


def retrieval_problems(manifest: Json, cases: Sequence[Json], k: int) -> list[str]:
    """A retrieval run: bootstrap intervals, one trial, every case its labels and scores, and no
    field of a generation run."""
    problems: list[str] = []
    if "bootstrap" not in manifest:
        problems.append("a retrieval run has bootstrap intervals: missing 'bootstrap'")
    extra = [
        f
        for f in (*GENERATION_MANIFEST, "guard_set", "probes", "ollama", "position")
        if f in manifest
    ]
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
    run), every case's answer fields and the fields of its kind, a withheld answer for every
    status but ok, no cited id that was not retrieved, retrieval scores on the labelled cases and
    none on the others, and the checks as the fields give them (S4: the behaviour cases' too)."""
    problems: list[str] = []
    if missing := [f for f in GENERATION_MANIFEST if f not in manifest]:
        problems.append(f"a generation run needs {missing}")
    if "bootstrap" in manifest:
        problems.append("a generation run has Wilson intervals, not bootstrap ones")
    if "generation" not in as_json(manifest["results"]):
        problems.append("a generation run needs results.generation")
    if "probes" not in manifest and any(c.get("kind") == generation_record.PROBE for c in cases):
        problems.append("a generation run with probe cases needs its probes block")
    if problems:
        return problems
    trials = cast(int, manifest["trials"])
    unavailable = sum(1 for case in cases if case.get("status") == "unavailable")
    if unavailable and not manifest["partial"]:  # judge S3-J10
        problems.append(
            f"{unavailable} trial(s) unavailable but partial is false: a run with unanswered "
            "trials is never complete"
        )
    try:
        canaries = answer_key.canaries(root)
        banned = answer_key.must_not_contain(root)
        features = answer_key.features(root)
    except (OSError, ValueError) as error:  # fails closed, as the register does
        return [f"the answer key's canaries cannot be read, so the probes are unchecked ({error})"]
    positioned = [c for c in cases if c.get("kind") == position_record.POSITION]
    if positioned:  # S5: the position test's lines
        problems.extend(position_record.problems(manifest, positioned, root))
    elif "position" in manifest:
        problems.append("a generation run without position cases has no position block")
    seen: dict[str, list[int]] = {}
    for case in cases:
        where = f"case {case['case_id']} trial {case['trial']}"
        seen.setdefault(str(case["case_id"]), []).append(cast(int, case["trial"]))
        if missing := [f for f in generation_record.ANSWER_FIELDS if f not in case]:
            problems.append(f"{where}: a generation case needs {missing}")
            continue
        required, refused = kind_fields(case)
        if missing := [f for f in required if f not in case]:
            problems.append(f"{where}: a {case['kind']} case needs {missing}")
            continue
        if extra := [f for f in refused if f in case]:
            problems.append(f"{where}: a {case['kind']} case has no {extra}")
            continue
        sided = case["kind"] == generation_record.BEHAVIOUR and case["expected"] == "flag-conflict"
        if not sided and any("side" in as_json(x) for x in as_list(case.get("labels", []))):
            problems.append(f"{where}: only a flag-conflict case's labels take a side")
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
        if "labels" in case:
            problems.extend(case_problems(case, k))
        elif case["kind"] == position_record.POSITION:
            pass  # its context and relevant flag: position_record.problems, above
        elif any(as_json(r)["relevant"] for r in as_list(case["retrieved"])):
            problems.append(
                f"{where}: a {case['kind']} case has no labels, so no retrieved chunk is relevant"
            )
        if case["checks"] != generation_record.case_checks(case, canaries, banned, features):
            problems.append(f"{where}: checks {case['checks']} do not follow from the fields")
    for case_id, numbers in seen.items():
        full = list(range(1, trials + 1))
        if sorted(numbers) != full and not (
            manifest["partial"] and sorted(numbers) == full[: len(numbers)]
        ):
            problems.append(f"case {case_id}: trials {sorted(numbers)}, not 1 to {trials}")
    problems.extend(behaviour_field_problems(manifest, cases, root))
    return problems


# ---------------------------------------------------------------- the behaviour fields (S4)


SNAPSHOT = "corpus/inventory.snapshot.json"
# each register document's chunk ids by section, per (root, document, chunk size, overlap and the
# document's bytes): ingestion parses a whole document, the scanned page through OCR, so a
# document is chunked once per process however many records and labels read it
_SECTIONS: dict[tuple[str, str, int, int, str], dict[str, tuple[str, ...]]] = {}


class SectionIds:
    """The chunk ids of a labelled section at a record's chunker settings: from the committed
    inventory snapshot when the settings are the snapshot's, so the record validates alike on a
    Mac and on CI, whose Tesseract reads the scanned page with other character errors; otherwise
    from the corpus, each document chunked once (S4, fix round 1)."""

    def __init__(self, root: Path, settings: ChunkSettings) -> None:
        self.root, self.settings = root, settings
        self.snapshot: dict[tuple[str, str], tuple[str, ...]] | None = None
        path = root / SNAPSHOT
        if path.is_file():
            data = as_json(json.loads(path.read_text(encoding="utf-8")))
            kept = as_json(data["settings"])
            if (kept["chunk_size"], kept["overlap"]) == (settings.chunk_size, settings.overlap):
                found: dict[tuple[str, str], list[str]] = {}
                for row in (as_json(r) for r in as_list(data["chunks"])):
                    found.setdefault((str(row["doc"]), str(row["section"])), []).append(
                        str(row["id"])
                    )
                self.snapshot = {key: tuple(ids) for key, ids in found.items()}
        self.paths: dict[str, str] | None = None  # the register, read only to chunk again

    def of(self, doc_id: str, section_id: str) -> tuple[str, ...]:
        if self.snapshot is not None:
            return self.snapshot.get((doc_id, section_id), ())
        return self._document(doc_id).get(section_id, ())

    def _document(self, doc_id: str) -> dict[str, tuple[str, ...]]:
        if self.paths is None:
            self.paths = {e.doc_id: e.path for e in register.read(self.root)}
        if doc_id not in self.paths:
            return {}
        source = self.root / self.paths[doc_id]
        digest = hashlib.sha256(source.read_bytes())
        canonical = source.with_suffix(".md")  # a rendered document's front matter (its version)
        if canonical != source and canonical.is_file():
            digest.update(canonical.read_bytes())
        size, overlap = self.settings.chunk_size, self.settings.overlap
        key = (str(self.root.resolve()), doc_id, size, overlap, digest.hexdigest())
        if key not in _SECTIONS:
            found: dict[str, list[str]] = {}
            for chunk in pipeline.document_chunks(self.root, doc_id, self.settings):
                found.setdefault(chunk.section_id, []).append(chunk.chunk_id)
            _SECTIONS[key] = {section: tuple(ids) for section, ids in found.items()}
        return _SECTIONS[key]


def label_chunk_problems(manifest: Json, cases: Sequence[Json], root: Path) -> list[str]:
    """For a record of the golden file's current bytes (any suite), every label whose chunk ids,
    or a group member's, are not the labelled section's chunks at the record's settings (the
    criteria judge's S4-J2; the user's answer on it, "Fix it now (Recommended)"). A record of
    another dataset version keeps its labels as recorded, as history (the S2 and S3 runs)."""
    if current_golden(manifest, root) is None:
        return []
    chunker = as_json(manifest["chunker"])
    settings = ChunkSettings(cast(int, chunker["chunk_size"]), cast(int, chunker["overlap"]))
    try:
        ids = SectionIds(root, settings)
    except (OSError, ValueError, KeyError, TypeError, register.RegisterError) as error:
        return [f"the labelled sections cannot be read, so the labels are unchecked ({error})"]
    problems: list[str] = []
    for case in cases:
        for label in (as_json(x) for x in as_list(case.get("labels", []))):
            members = [as_json(m) for m in as_list(label.get("any_of", []))] or [label]
            union: list[str] = []
            for member in members:
                doc, section = str(member["doc_id"]), str(member["section_id"])
                try:
                    derived = list(ids.of(doc, section))
                except (pipeline.IngestError, register.RegisterError, OSError) as error:
                    problems.append(f"{doc} {section} cannot be chunked again ({error})")
                    continue
                recorded = [str(i) for i in as_list(member["chunk_ids"])]
                if recorded != derived:
                    problems.append(
                        f"case {case['case_id']} trial {case['trial']}: label {doc} {section} has "
                        f"chunk ids {recorded}, not the section's chunks at "
                        f"{settings.chunk_size}/{settings.overlap} {derived}"
                    )
                union += [i for i in derived if i not in union]
            if len(members) > 1 and [str(i) for i in as_list(label["chunk_ids"])] != union:
                problems.append(
                    f"case {case['case_id']} trial {case['trial']}: label group {label['doc_id']} "
                    f"{label['section_id']} has chunk ids that are not its members' sections' "
                    "chunks together"
                )
    return problems


def current_golden(manifest: Json, root: Path) -> Path | None:
    """The golden file a record names, when its bytes are still those the record was made from."""
    dataset = as_json(manifest["dataset"])
    path = root / str(dataset["path"])
    try:
        data = path.read_bytes()
    except OSError:
        return None
    return path if sha256_bytes(data) == dataset["sha256"] else None


def _recorded_label(label: Json) -> tuple[object, ...]:
    group = tuple(
        (as_json(m)["doc_id"], as_json(m)["section_id"]) for m in as_list(label.get("any_of", []))
    )
    return (label["doc_id"], label["section_id"], group, label.get("side"))


def behaviour_field_problems(manifest: Json, cases: Sequence[Json], root: Path) -> list[str]:
    """For a record of the current golden file, every behaviour case whose expected label, mix,
    features, labels, groups, conflict sides or may_quote chunks and values differ from those the
    golden file, the answer key and the corpus give (see the module docstring)."""
    path = current_golden(manifest, root)
    if path is None or not any(c.get("kind") == behaviour.BEHAVIOUR for c in cases):
        return []
    try:
        questions = {q.case_id: q for q in golden.load(path) if q.kind == "behaviour"}
        features = answer_key.features(root)
    except (OSError, ValueError) as error:  # fails closed, as the register does
        return [f"the golden file or the answer key cannot be read, so it is unchecked ({error})"]
    chunker = as_json(manifest["chunker"])
    settings = ChunkSettings(cast(int, chunker["chunk_size"]), cast(int, chunker["overlap"]))
    quotes: dict[tuple[str, str], Json] = {}
    problems: list[str] = []
    for case in cases:
        if case.get("kind") != behaviour.BEHAVIOUR:
            continue
        where = f"case {case['case_id']} trial {case['trial']}"
        question = questions.get(str(case["case_id"]))
        if question is None:
            problems.append(f"{where}: {path.name} has no behaviour case with this id")
            continue
        try:
            shape = golden.behaviour(question)
        except golden.DatasetError as error:
            problems.append(f"{where}: {error}")
            continue
        listed = [str(f) for f in as_list(case.get("feature_ids", []))]
        fields = (case.get("expected"), case.get("mix"), listed)  # a missing one: reported above
        if fields != (shape.expected, shape.mix, list(shape.feature_ids)):
            problems.append(f"{where}: its expected label, mix or features are not {path.name}'s")
        own = [features[f] for f in shape.feature_ids if f in features]
        derived: list[tuple[object, ...]] = []
        for entry in question.labels:
            members = golden.members(entry)
            places = {(s.doc_id, s.section_id) for s in members}
            group = (
                tuple((s.doc_id, s.section_id) for s in members)
                if isinstance(entry, golden.Group)
                else ()
            )
            side = behaviour.side(places, own) if shape.expected == "flag-conflict" else None
            derived.append((members[0].doc_id, members[0].section_id, group, side))
        recorded = [_recorded_label(as_json(x)) for x in as_list(case.get("labels", []))]
        if recorded != derived:
            problems.append(
                f"{where}: its labels or their conflict sides are not those of {path.name} and "
                "the answer key"
            )
        quote: Json | None = None
        if shape.may_quote is not None:
            key = (shape.may_quote.doc_id, shape.may_quote.section_id)
            if key not in quotes:
                try:
                    chunks = pipeline.section_chunks(root, key[0], key[1], settings)
                except (pipeline.IngestError, OSError) as error:
                    problems.append(f"{where}: its may_quote section cannot be read ({error})")
                    continue
                quotes[key] = behaviour.quote_json(*key, [(c.chunk_id, c.text) for c in chunks])
            quote = quotes[key]
        if case.get("may_quote") != quote:
            problems.append(f"{where}: its may_quote chunks or values are not the corpus's")
    return problems
