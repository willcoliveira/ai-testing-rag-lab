"""Run record v1 for the generation suite (S3): the per-trial checks, the results and the report,
computed from the cases alone, so `raglab.evals.record.validate` recomputes every one of them.

A generation run has one line per case and trial. A case is a retrieval question of the golden
set (kind "retrieval", with its labels and retrieval scores) or an abstention probe (kind
"probe", with its expected label and the strings that must not appear). The checks need no judge:

1. status_ok: the status is ok;
2. model_citations_retrieved: the model's reply cited, and named in its conflict field, only ids
   retrieved for it (R-02). It reads the citation validator's event: a reply that cited another
   id fails here, and its answer is withheld (status blocked), so the recorded answer never holds
   such an id (judge S3-J1: measured on the recorded answer, the check could not fail);
3. a probe, by the abstention oracle (`abstention_oracle`): abstained (status ok, label
   abstain), no_value (the answer states no policy value: R-18's acceptance, "omission questions
   produce no number") and no_canary (for a tenant-isolation probe, no canary of the other tenant
   from corpus/answer-key.yaml appears: R-16);
4. a retrieval question: answered (status ok, label not abstain) and cites_label (it cites at
   least one chunk of a labelled section: a citation hit, which is not correctness: S5 judges
   that).

A trial passes when every check that applies to its case passes. The results: each check's rate
over the trials, with a Wilson interval at n = the number of cases (raglab.evals.metrics); pass^N,
the share of cases whose N trials all pass; the count of each status; how many cases got the same
label in every trial; each probe's abstentions out of its trials; p50 and p95 latency (type 7
quantiles); and the token totals the server reported.

S4 adds a third kind, the golden set's behaviour cases (kind "behaviour"): their checks, results
and report section are raglab.evals.behaviour's, added only when a run has such cases, so an S3
record computes and renders exactly as it did. The probes' oracle is raglab.evals.oracle's,
unchanged.
"""

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import cast

from raglab.core.types import Status
from raglab.evals import behaviour, metrics
from raglab.evals.oracle import abstention_oracle

type Json = dict[str, object]

STATUSES = tuple(s.value for s in Status)
PROBE = "probe"
CITATIONS_GUARD = "citations"  # raglab.guard.citations.CitationValidator's name
RETRIEVAL = "retrieval"
BEHAVIOUR = behaviour.BEHAVIOUR
# the fields every generation case has (record.validate checks them; the schema cannot say "for
# this suite")
ANSWER_FIELDS = (
    "kind",
    "status",
    "label",
    "answer",
    "cited_ids",
    "conflict",
    "guard_events",
    "error",
    "prompt_tokens",
    "completion_tokens",
    "checks",
)
RETRIEVAL_FIELDS = ("labels", "hit", "reciprocal_rank", "recall")
PROBE_FIELDS = ("expected", "canaries_of", "feature_ids")


def _obj(value: object) -> Json:
    return {str(k): v for k, v in cast(dict[object, object], value).items()}


def _strings(value: object) -> list[str]:
    return [str(x) for x in cast(list[object], value)]


def referenced(case: Json) -> set[str]:
    """The ids an answer points at: its citations and its conflict's chunks."""
    ids = set(_strings(case["cited_ids"]))
    if case["conflict"] is not None:
        ids |= set(_strings(_obj(case["conflict"])["chunk_ids"]))
    return ids


def case_checks(
    case: Json,
    canaries: Mapping[str, Sequence[str]],
    banned: Mapping[str, Sequence[str]] | None = None,
) -> Json:
    """The checks of one trial, from its fields and the answer key's canaries by tenant (and, for
    a behaviour case, its answer_must_not_contain strings by feature, which it needs)."""
    ok = case["status"] == Status.OK.value
    retrieved = {str(_obj(r)["chunk_id"]) for r in cast(list[object], case["retrieved"])}
    events = cast(list[object], case["guard_events"])
    cited_unretrieved = any(_obj(e)["guard"] == CITATIONS_GUARD for e in events)
    checks: Json = {
        "status_ok": ok,
        "model_citations_retrieved": not cited_unretrieved and referenced(case) <= retrieved,
    }
    if case["kind"] == BEHAVIOUR:
        if banned is None:
            raise ValueError("a behaviour case's checks need the answer_must_not_contain strings")
        checks |= behaviour.checks(case, canaries, banned)
    elif case["kind"] == PROBE:
        of = case["canaries_of"]
        oracle = abstention_oracle(
            str(case["status"]),
            str(case["label"]),
            str(case["answer"]),
            canaries[str(of)] if of is not None else (),
        )
        checks |= oracle
    else:
        labelled = {
            i
            for label in cast(list[object], case["labels"])
            for i in _strings(_obj(label)["chunk_ids"])
        }
        checks["answered"] = ok and case["label"] != "abstain"
        checks["cites_label"] = bool(set(_strings(case["cited_ids"])) & labelled)
    checks["passed"] = all(bool(v) for v in checks.values())
    return checks


def _by_case(cases: Sequence[Json]) -> dict[str, list[Json]]:
    grouped: dict[str, list[Json]] = {}
    for case in cases:
        grouped.setdefault(str(case["case_id"]), []).append(case)
    return grouped


def _rate(cases: Sequence[Json], passes: list[bool], level: float) -> Json:
    n_cases = len({str(c["case_id"]) for c in cases})
    rate = sum(passes) / len(passes)
    return dict(metrics.wilson_interval(rate, n_cases, level).as_json())


def results(cases: Sequence[Json], trials: int, level: float) -> Json:
    """The manifest's results block of a generation run."""
    checks = [_obj(c["checks"]) for c in cases]
    probes = [(c, k) for c, k in zip(cases, checks, strict=True) if c["kind"] == PROBE]
    questions = [(c, k) for c, k in zip(cases, checks, strict=True) if c["kind"] == RETRIEVAL]
    out: Json = {
        "status_ok": _rate(cases, [bool(k["status_ok"]) for k in checks], level),
        "model_citations_retrieved": _rate(
            cases, [bool(k["model_citations_retrieved"]) for k in checks], level
        ),
    }
    if probes:
        out["probe_abstention"] = _rate(
            [c for c, _ in probes],
            [
                bool(k["abstained"]) and bool(k["no_value"]) and bool(k["no_canary"])
                for _, k in probes
            ],
            level,
        )
    if questions:
        out["citation_hit"] = _rate(
            [c for c, _ in questions],
            [bool(k["answered"]) and bool(k["cites_label"]) for _, k in questions],
            level,
        )
    grouped = _by_case(cases)
    complete = {i: rows for i, rows in grouped.items() if len(rows) == trials}
    if complete:
        passed = sum(
            all(bool(_obj(r["checks"])["passed"]) for r in rows) for rows in complete.values()
        )
        out[f"pass^{trials}"] = dict(
            metrics.wilson_interval(passed / len(complete), len(complete), level).as_json()
        )
    statuses = Counter(str(c["status"]) for c in cases)
    unanimous = sum(len({str(r["label"]) for r in rows}) == 1 for rows in complete.values())
    latencies = [float(cast(float, c["latency_ms"])) for c in cases]
    prompt = [c["prompt_tokens"] for c in cases]
    completion = [c["completion_tokens"] for c in cases]
    reported = [
        (cast(int, p), cast(int, q))
        for p, q in zip(prompt, completion, strict=True)
        if p is not None and q is not None
    ]
    generation: Json = {
        "trials": trials,
        "cases": len(grouped),
        "case_trials": len(cases),
        "status_counts": {s: statuses.get(s, 0) for s in STATUSES},
        "label_agreement": {"cases": len(complete), "unanimous": unanimous},
        "probes": [
            {
                "case_id": case_id,
                "feature_ids": _strings(rows[0]["feature_ids"]),
                "tenant": rows[0]["tenant"],
                "abstained": sum(bool(_obj(r["checks"])["abstained"]) for r in rows),
                "trials": len(rows),
            }
            for case_id, rows in grouped.items()
            if rows[0]["kind"] == PROBE
        ],
        "latency_ms": {
            "p50": round(metrics.quantile(latencies, 0.5), 3),
            "p95": round(metrics.quantile(latencies, 0.95), 3),
            "n": len(latencies),
        },
        "tokens": {
            "reported": len(reported),
            "prompt": sum(p for p, _ in reported),
            "completion": sum(q for _, q in reported),
        },
    }
    added, block = behaviour.results(cases, trials, level)  # S4: nothing for a run without
    out |= added
    if block is not None:
        generation["behaviour"] = block
    return {"metrics": out, "generation": generation}


def _pass_k_note(manifest: Json, generator: Json) -> str:
    """What pass^N measures under the run's sampling settings."""
    trials, seed = manifest["trials"], manifest["seed"]
    head = (
        f"pass^{trials}: a case passes only when all {trials} trials pass every check that "
        f"applies; trial t uses seed {seed} + t - 1"
    )
    if "temperature" in generator:
        return (
            f"{head} at temperature {generator['temperature']}, so it measures whether the model "
            "passes consistently while it samples at that temperature, not whether it is correct."
        )
    return (
        f"{head}, but the {generator['provider']} model does not sample: its trials are "
        f"identical, so pass^{trials} equals the single-trial pass rate."
    )


def _fmt(value: object) -> str:
    return f"{cast(float, value):.3f}"


def render_report(manifest: Json, cases: Sequence[Json]) -> str:
    """report.md of a generation run, generated from the manifest (without its files block) and
    the cases. It carries ids, labels and checks, never answer text (that is in cases.jsonl)."""
    config, chunker = _obj(manifest["config"]), _obj(manifest["chunker"])
    embedder, retriever = _obj(manifest["embedder"]), _obj(manifest["retriever"])
    generator, prompt = _obj(manifest["generator"]), _obj(manifest["prompt"])
    dataset, corpus = _obj(manifest["dataset"]), _obj(manifest["corpus"])
    dataset_line = f"| Dataset | `{dataset['path']}`, sha256 {str(dataset['sha256'])[:12]}"
    if "probes" in manifest:  # S3's probes file; S4 folds the probes into the golden set
        probes = _obj(manifest["probes"])
        dataset_line += f"; probes `{probes['path']}`, sha256 {str(probes['sha256'])[:12]}"
    intervals, totals = _obj(manifest["intervals"]), _obj(manifest["totals"])
    results_ = _obj(manifest["results"])
    found, gen = _obj(results_["metrics"]), _obj(results_["generation"])
    level = round(cast(float, intervals["level"]) * 100)
    gated = (
        " Nothing here is gated."
        if "behaviour" not in gen
        else f" Only behaviour pass^{manifest['trials']} on the dev split is gated, by the "
        "consistency gate (Q-05; docs/THRESHOLDS.md), and locally until keys exist; the rest is "
        "reported."
    )
    model = f"{generator['model']} ({generator['provider']}, digest {str(generator['digest'])[:12]}"
    if "server_version" in generator:
        model += f", server {generator['server_version']}"
    model += ")"
    settings = ", ".join(
        f"{key} {generator[key]}"
        for key in ("temperature", "top_p", "max_tokens", "timeout_s", "response_format")
        if key in generator
    )
    extra = _obj(generator.get("extra") or {})
    if extra:
        settings += ", " + ", ".join(f"{k} {v}" for k, v in extra.items())
    lines = [
        f"# Run {manifest['run_id']}",
        "",
        "Generated from manifest.json and cases.jsonl by raglab; never edited by hand.",
        "",
        "| | |",
        "|---|---|",
        f"| Suite | {manifest['suite']}, split {manifest['split']}, "
        f"{manifest['trials']} trial(s), seed {manifest['seed']}, gate {manifest['gate']} |",
        f"| Provenance | {manifest['provenance']}"
        f"{' (partial: ' + str(totals.get('stopped', '')) + ')' if manifest['partial'] else ''} |",
        f"| Created | {manifest['created_at']} |",
        f"| Git | {manifest['git_sha']} ({'dirty' if manifest['git_dirty'] else 'clean'}) |",
        f"| Config | {config['name']} (`{config['path']}`, sha256 {str(config['sha256'])[:12]}) |",
        f"| Generator | {model} |",
        f"| Settings | {settings or 'none'} |",
        f"| Prompt | {prompt['version']} (sha256 {str(prompt['sha256'])[:12]}) |",
        f"| Guards | {', '.join(_strings(manifest['guards']))} |",
        f"| Embedder | {embedder['model']} at revision {str(embedder['revision'])[:12]} |",
        f"| Retriever | {retriever['kind']}, k = {retriever['k']} |",
        f"| Chunker | {chunker['chunk_size']} characters, overlap {chunker['overlap']} |",
        f"| Corpus | {corpus['documents']} documents, {corpus['chunks']} chunks, "
        f"sha256 {str(corpus['sha256'])[:12]} |",
        f"{dataset_line} |",
        f"| Cases | {gen['cases']} ({gen['case_trials']} case-trials) |",
        "",
        "## Checks (no judge)",
        "",
        f"Rates over every trial, with a {level}% Wilson interval at n = the number of cases. "
        "A citation hit means the answer cites a labelled chunk; it is not correctness (S5 "
        f"judges that).{gated}",
        "",
        _pass_k_note(manifest, generator),
        "",
        f"| Check | Rate | {level}% interval | n (cases) |",
        "|---|---|---|---|",
    ]
    for name, raw in found.items():
        item = _obj(raw)
        lines.append(
            f"| {name} | {_fmt(item['value'])} | {_fmt(item['ci_low'])} to "
            f"{_fmt(item['ci_high'])} | {item['n']} |"
        )
    statuses = _obj(gen["status_counts"])
    agreement = _obj(gen["label_agreement"])
    latency, tokens = _obj(gen["latency_ms"]), _obj(gen["tokens"])
    lines += [
        "",
        "## Run",
        "",
        "- Status counts: " + ", ".join(f"{k} {v}" for k, v in statuses.items()),
        f"- Label agreement: {agreement['unanimous']} of {agreement['cases']} cases gave the same "
        "label in every trial",
        f"- Latency: p50 {_fmt(latency['p50'])} ms, p95 {_fmt(latency['p95'])} ms "
        f"(n {latency['n']})",
        f"- Tokens: {tokens['prompt']} prompt and {tokens['completion']} completion, from the "
        f"{tokens['reported']} case-trials whose server reported them",
    ]
    probes_ = cast(list[object], gen["probes"])
    if probes_ or "behaviour" not in gen:  # an S3 record renders as it did
        lines += [
            "",
            "## Abstention probes",
            "",
            "| Probe | Features | Tenant | Abstained |",
            "|---|---|---|---|",
        ]
    for raw in probes_:
        probe = _obj(raw)
        lines.append(
            f"| {probe['case_id']} | {', '.join(_strings(probe['feature_ids']))} | "
            f"{probe['tenant']} | {probe['abstained']} of {probe['trials']} |"
        )
    if "behaviour" in gen:
        lines += behaviour.report_lines(
            _obj(gen["behaviour"]), cases, cast(int, manifest["trials"])
        )
    lines += [
        "",
        "## Case-trials",
        "",
        "| Case | Trial | Tenant | Kind | Status | Label | Cited | Passed |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for case in cases:
        lines.append(
            f"| {case['case_id']} | {case['trial']} | {case['tenant']} | {case['kind']} | "
            f"{case['status']} | {case['label']} | {', '.join(_strings(case['cited_ids'])) or '-'} "
            f"| {'yes' if _obj(case['checks'])['passed'] else 'no'} |"
        )
    return "\n".join(lines) + "\n"
