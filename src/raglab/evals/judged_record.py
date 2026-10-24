"""Run record v1 for the judged suite (S5): the judge's verdicts on a finished generation run (its
source), the results and the report, computed from the lines alone, and the checks that tie every
line to its source, so `raglab.evals.record.validate` recomputes and checks all of it.

A judged record has one line per case and trial of its source, in the source's order, with the
source's case id, trial, split, tenant, question and retrieved chunks, and:

- `source_status`, `answer_sha256` (of the source's answer text), `source_called` (whether the
  source's request reached the generator) and `source_tokens` (its prompt and completion tokens as
  the server reported them), all checked against the source line;
- `reference_sha256`: the sha256 of the reference answer the judge saw (the golden case's, with a
  contact feature's reference from the answer key: docs/CRITERIA.md), null for a case without one;
- `verdicts`: one per criterion the answer takes (docs/CRITERIA.md, "What each answer is judged
  on"), each with its verdict, status, quote, passage ids, reason, the reply as it came, the ids
  it was shown, its tokens and its latency; a withheld answer takes none but `context_sufficient`;
- `repeat` (trial 1 of a behaviour case: every criterion judged a second time, the repeatability
  check) and `reversed` (trial 1 of every case: `grounded` with the passages in reverse order, the
  order check).

The checks against the source: the source's manifest and cases are the ones the record names
(their sha256), every source case-trial has its line (a partial record a prefix of them), every
line's fields equal its source line's, each line takes exactly its criteria, and each verdict was
shown exactly the passages its criterion sees. Each verdict is read again from its reply with the
parser of the record's judge prompt, so a verdict edited apart from its reply is refused; the quote
and passage-id checks are recomputed from the source's answer. When the golden file is still the
one the record names, each reference answer's sha256 is derived again.

The results: per criterion, the pass rate over judged verdicts with a Wilson interval at n =
cases, per expected label, and pass^N (the cases whose N trials all pass; a withheld trial does
not); the counts of each verdict and status, the unable_to_verify rate and the quote checks; the
repeatability and order agreements; the canaries; the tokens of every call by role (generator, from
the source lines; judge; judge checks; canaries); and the judge calls' latency. Nothing judged is
gated in S5: S6 calibrates the judge.
"""

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

from raglab.core.types import CRITERIA, VERDICTS, Status
from raglab.evals import golden, metrics
from raglab.ingest import answer_key
from raglab.judge import canaries as canary_set
from raglab.judge.prompts import judge_v1, judge_v2

type Json = dict[str, object]

JUDGED = "judged"
CONTEXT = "context_sufficient"
GROUNDED = "grounded"
BY_LABEL: dict[str, tuple[str, ...]] = {
    "answer": ("grounded", "cites_support", "correct", "relevant"),
    "flag-conflict": ("grounded", "cites_support", "correct", "relevant"),
    "refuse-and-help": ("grounded", "correct", "refuses_and_helps", "relevant"),
    "abstain": ("grounded", "abstains"),
}
RETRIEVAL_CRITERIA = ("grounded", "relevant")
POSITION_CRITERIA = ("correct",)
REFERENCE_LABELS = ("answer", "flag-conflict", "refuse-and-help")
GROUPS = ("answer", "flag-conflict", "refuse-and-help", "abstain", "retrieval", "position")
# the parser of each judge prompt version a record may name
PROMPTS = {judge_v1.VERSION: judge_v1, judge_v2.VERSION: judge_v2}
# the version a new judged run uses (raglab.judge.llm), since the second sign-off (2026-10-21)
CURRENT = judge_v2.VERSION
STATUSES = (Status.OK.value, Status.INVALID_OUTPUT.value, Status.UNAVAILABLE.value)
PUBLISHED = "runs/published"
# the manifest fields of a judged run, and those of a generation run it has none of
JUDGED_MANIFEST = ("judge", "judge_prompt", "source", "criteria", "canaries", "intervals")
NOT_JUDGED = ("generator", "prompt", "guards", "guard_set", "probes", "bootstrap", "position")
LINE_FIELDS = (
    "kind",
    "source_status",
    "answer_sha256",
    "source_called",
    "source_tokens",
    "reference_sha256",
    "verdicts",
)


def _obj(value: object) -> Json:
    return {str(k): v for k, v in cast(dict[object, object], value).items()}


def _list(value: object) -> list[object]:
    return list(cast(list[object], value)) if isinstance(value, list) else []


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- what each answer is judged on


def group(case: Json) -> str:
    """retrieval, position, or a behaviour case's expected label."""
    kind = str(case["kind"])
    return str(case["expected"]) if kind == "behaviour" else kind


def applies(case: Json) -> tuple[str, ...]:
    """The per-trial criteria a case's answers take, whatever a trial's status."""
    kind = case["kind"]
    if kind == "retrieval":
        return RETRIEVAL_CRITERIA
    if kind == "position":
        return POSITION_CRITERIA
    return BY_LABEL[str(case["expected"])]


def trial_criteria(case: Json) -> tuple[str, ...]:
    """The criteria one trial's answer is judged on: none when it was withheld (no text)."""
    return applies(case) if case["source_status"] == Status.OK.value else ()


def has_reference(case: Json) -> bool:
    """A behaviour case with a reference answer, or a position case (its golden case's)."""
    if case["kind"] == "position":
        return True
    return case["kind"] == "behaviour" and case["expected"] in REFERENCE_LABELS


def context_trials(lines: Sequence[Json]) -> list[int]:
    """The trials of one case that carry context_sufficient: the first, when every trial retrieved
    the same chunks in the same order (retrieval is deterministic); otherwise every trial."""
    if not lines or lines[0]["kind"] != "behaviour" or not has_reference(lines[0]):
        return []
    ranked = [retrieved_ids(line) for line in lines]
    trials = [cast(int, line["trial"]) for line in lines]
    return trials[:1] if all(r == ranked[0] for r in ranked) else trials


def retrieved_ids(case: Json) -> list[str]:
    return [str(_obj(r)["chunk_id"]) for r in _list(case["retrieved"])]


def cited_ids(case: Json) -> list[str]:
    """The passages an answer cites: its citations, then its conflict field's chunks, each once,
    in that order; only retrieved ones (an ok answer cites no other)."""
    retrieved = set(retrieved_ids(case))
    conflict: object = case.get("conflict")
    ids = [str(i) for i in _list(case.get("cited_ids", []))]
    if conflict is not None:
        ids += [str(i) for i in _list(_obj(conflict).get("chunk_ids"))]
    return [i for i in dict.fromkeys(ids) if i in retrieved]


def shown_ids(
    criterion: str, source_case: Json, reverse: bool = False, version: str = CURRENT
) -> list[str]:
    """The passage ids a criterion's call is shown for a source case: the retrieved passages in
    rank order (reversed for the order check), the cited ones for cites_support, none for a
    criterion that sees no passages."""
    sees = PROMPTS[version].RULES[criterion].sees
    if "passages" not in sees:
        return []
    ids = cited_ids(source_case) if criterion == "cites_support" else retrieved_ids(source_case)
    return ids[::-1] if reverse else ids


def source_called(case: Json) -> bool:
    """Whether a generation trial's request reached the model: refused at input or blocked
    before the model (stage retrieved) did not."""
    status = case["status"]
    if status == Status.REFUSED.value:
        return False
    if status == Status.BLOCKED.value:
        stages = [str(_obj(e)["stage"]) for e in _list(case["guard_events"])]
        return "output" in stages
    return True


def references(root: Path, dataset: Path) -> dict[str, str]:
    """The reference answer the judge sees for each behaviour case that has one (docs/CRITERIA.md):
    the golden case's reference_answer, and for a case whose features include a contact feature,
    that feature's reference from the answer key."""
    features = answer_key.features(root)
    found: dict[str, str] = {}
    for question in golden.load(dataset):
        reference = question.extra.get("reference_answer")
        if question.kind != "behaviour" or not isinstance(reference, str):
            continue
        extra = [
            f"The answer key gives the contact in full: {features[f].reference_answer}"
            for f in (str(i) for i in _list(question.extra.get("feature_ids")))
            if f in features
            and features[f].kind.startswith("contact")
            and features[f].reference_answer
        ]
        found[question.case_id] = " ".join([reference, *extra])
    return found


def reference_of(case: Json, refs: Mapping[str, str]) -> str | None:
    """A case's reference answer: its golden case's (a position case names it as golden_id)."""
    if not has_reference(case):
        return None
    key = str(case["golden_id"]) if case["kind"] == "position" else str(case["case_id"])
    return refs.get(key)


# ---------------------------------------------------------------- results


def _verdicts(case: Json, field: str = "verdicts") -> dict[str, Json]:
    return {str(k): _obj(v) for k, v in _obj(case.get(field) or {}).items()}


def _rate(rows: Sequence[tuple[Json, Json]], level: float) -> Json:
    passes = [v["verdict"] == "pass" for _, v in rows]
    n_cases = len({str(c["case_id"]) for c, _ in rows})
    return dict(metrics.wilson_interval(sum(passes) / len(passes), n_cases, level).as_json())


def _by_case(cases: Sequence[Json]) -> dict[str, list[Json]]:
    grouped: dict[str, list[Json]] = {}
    for case in cases:
        grouped.setdefault(str(case["case_id"]), []).append(case)
    return grouped


def _counts(rows: Sequence[Json]) -> Json:
    statuses = [str(v["status"]) for v in rows]
    verdicts = [str(v["verdict"]) for v in rows]
    return {
        "judged": len(rows),
        **{v: verdicts.count(v) for v in VERDICTS},
        "invalid_output": statuses.count(Status.INVALID_OUTPUT.value),
        "unavailable": statuses.count(Status.UNAVAILABLE.value),
        "quote_found": sum(v["quote_found"] is True for v in rows),
        "quote_missing": sum(v["quote_found"] is False for v in rows),
        "passages_not_given": sum(v["passages_given"] is False for v in rows),
    }


def _role(rows: Sequence[Json]) -> Json:
    """Calls, and the tokens their server reported; a call with either count missing is
    unreported, never estimated."""
    reported = [
        (cast(int, r["prompt_tokens"]), cast(int, r["completion_tokens"]))
        for r in rows
        if r["prompt_tokens"] is not None and r["completion_tokens"] is not None
    ]
    return {
        "calls": len(rows),
        "prompt": sum(p for p, _ in reported),
        "completion": sum(c for _, c in reported),
        "unreported": len(rows) - len(reported),
    }


def results(cases: Sequence[Json], trials: int, level: float, canaries: Sequence[Json]) -> Json:
    """The manifest's results block of a judged run, from its lines and its canary results."""
    found: Json = {}
    criteria: Json = {}
    grouped = _by_case(cases)
    for criterion in CRITERIA:
        rows = [(c, v) for c in cases for name, v in _verdicts(c).items() if name == criterion]
        takers = [i for i, lines in grouped.items() if criterion in applies(lines[0])]
        if criterion == CONTEXT:
            takers = [i for i, lines in grouped.items() if context_trials(lines)]
        if not rows and not takers:
            continue
        if rows:
            found[criterion] = _rate(rows, level)
            for name in GROUPS:
                subset = [(c, v) for c, v in rows if group(c) == name]
                if subset:
                    found[f"{criterion}[{name}]"] = _rate(subset, level)
        block: Json = {"cases": len(takers), **_counts([v for _, v in rows])}
        judged = cast(int, block["judged"])
        block["unable_to_verify_rate"] = (
            round(cast(int, block["unable_to_verify"]) / judged, 6) if judged else None
        )
        if criterion != CONTEXT and takers:
            passed = sum(
                len(grouped[i]) == trials
                and all(
                    _verdicts(c).get(criterion, {}).get("verdict") == "pass" for c in grouped[i]
                )
                for i in takers
            )
            found[f"{criterion}_pass^{trials}"] = dict(
                metrics.wilson_interval(passed / len(takers), len(takers), level).as_json()
            )
            block[f"pass^{trials}"] = passed
        criteria[criterion] = block
    repeatability: Json = {}
    for criterion in CRITERIA:
        pairs = [
            (_verdicts(c)[criterion], v)
            for c in cases
            for name, v in _verdicts(c, "repeat").items()
            if name == criterion
        ]
        if pairs:
            repeatability[criterion] = {
                "pairs": len(pairs),
                "agree": sum(a["verdict"] == b["verdict"] for a, b in pairs),
            }
    order_pairs = [
        (_verdicts(c)[GROUNDED], _verdicts(c, "reversed")[GROUNDED])
        for c in cases
        if GROUNDED in _verdicts(c, "reversed")
    ]
    main = [v for c in cases for v in _verdicts(c).values()]
    checks = [v for c in cases for f in ("repeat", "reversed") for v in _verdicts(c, f).values()]
    canary_rows = [_obj(r) for r in canaries]
    generator = [
        {
            "prompt_tokens": _obj(c["source_tokens"])["prompt"],
            "completion_tokens": _obj(c["source_tokens"])["completion"],
        }
        for c in cases
        if c["source_called"]
    ]
    latencies = [float(cast(float, v["latency_ms"])) for v in [*main, *checks, *canary_rows]]
    judged_block: Json = {
        "cases": len(grouped),
        "case_trials": len(cases),
        "criteria": criteria,
        "repeatability": repeatability,
        "order": {
            "pairs": len(order_pairs),
            "agree": sum(a["verdict"] == b["verdict"] for a, b in order_pairs),
        },
        "canaries": {
            "items": len(canary_rows),
            "on_side": sum(r["on_side"] is True for r in canary_rows),
        },
        "tokens": {
            "generator": _role(generator),
            "judge": _role(main),
            "judge_checks": _role(checks),
            "canaries": _role(canary_rows),
        },
        "latency_ms": {
            "p50": round(metrics.quantile(latencies, 0.5), 3) if latencies else 0.0,
            "p95": round(metrics.quantile(latencies, 0.95), 3) if latencies else 0.0,
            "n": len(latencies),
        },
    }
    return {"metrics": found, "judged": judged_block}


# ---------------------------------------------------------------- the report


def _fmt(value: object) -> str:
    return f"{cast(float, value):.3f}"


def render_report(manifest: Json, cases: Sequence[Json]) -> str:
    """report.md of a judged run, generated from the manifest (without its files block) and the
    lines. Ids, verdicts and counts only: never answer, passage or reference text."""
    config, judge = _obj(manifest["config"]), _obj(manifest["judge"])
    prompt, source = _obj(manifest["judge_prompt"]), _obj(manifest["source"])
    criteria_file, canaries = _obj(manifest["criteria"]), _obj(manifest["canaries"])
    dataset, corpus = _obj(manifest["dataset"]), _obj(manifest["corpus"])
    intervals, totals = _obj(manifest["intervals"]), _obj(manifest["totals"])
    results_ = _obj(manifest["results"])
    found, block = _obj(results_["metrics"]), _obj(results_["judged"])
    level = round(cast(float, intervals["level"]) * 100)
    trials = cast(int, manifest["trials"])
    model = f"{judge['model']} ({judge['provider']}, digest {str(judge['digest'])[:12]}"
    if "server_version" in judge:
        model += f", server {judge['server_version']}"
    model += ")"
    settings = ", ".join(
        f"{key} {judge[key]}"
        for key in ("temperature", "max_tokens", "timeout_s", "response_format")
        if key in judge
    )
    partial = f" (partial: {totals.get('stopped', '')})" if manifest["partial"] else ""
    lines = [
        f"# Run {manifest['run_id']}",
        "",
        "Generated from manifest.json and cases.jsonl by raglab; never edited by hand.",
        "",
        "| | |",
        "|---|---|",
        f"| Suite | {manifest['suite']}, split {manifest['split']}, {trials} trial(s) of the "
        f"source, judge seed {manifest['seed']}, gate {manifest['gate']} |",
        f"| Provenance | {manifest['provenance']}{partial} |",
        f"| Created | {manifest['created_at']} |",
        f"| Git | {manifest['git_sha']} ({'dirty' if manifest['git_dirty'] else 'clean'}) |",
        f"| Config | {config['name']} (`{config['path']}`, sha256 {str(config['sha256'])[:12]}) |",
        f"| Source | {source['run_id']} ({source['suite']}, manifest sha256 "
        f"{str(source['manifest_sha256'])[:12]}) |",
        f"| Judge | {model} |",
        f"| Settings | {settings or 'none'} |",
        f"| Judge prompt | {prompt['version']} (sha256 {str(prompt['sha256'])[:12]}) |",
        f"| Criteria | `{criteria_file['path']}`, sha256 {str(criteria_file['sha256'])[:12]} |",
        f"| Canaries | `{canaries['path']}`, sha256 {str(canaries['sha256'])[:12]} |",
        f"| Corpus | {corpus['documents']} documents, {corpus['chunks']} chunks, "
        f"sha256 {str(corpus['sha256'])[:12]} |",
        f"| Dataset | `{dataset['path']}`, sha256 {str(dataset['sha256'])[:12]} |",
        f"| Cases | {block['cases']} ({block['case_trials']} case-trials) |",
        "",
        "## Judged criteria (reported, not gated)",
        "",
        f"Rates over judged verdicts, with a {level}% Wilson interval at n = the number of cases; "
        f"pass^{trials} counts the cases whose {trials} trials all pass (a withheld trial does "
        "not). unable_to_verify is never a pass. Nothing judged is gated before S6 calibrates the "
        "judge (docs/CRITERIA.md).",
        "",
        f"| Metric | Rate | {level}% interval | n (cases) |",
        "|---|---|---|---|",
    ]
    for name, raw in found.items():
        item = _obj(raw)
        lines.append(
            f"| {name} | {_fmt(item['value'])} | {_fmt(item['ci_low'])} to "
            f"{_fmt(item['ci_high'])} | {item['n']} |"
        )
    lines += [
        "",
        "| Criterion | Cases | Judged | pass | fail | unable_to_verify | invalid_output | "
        "unavailable | Quote found | Quote missing | Passages not shown |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for name, raw in _obj(block["criteria"]).items():
        c = _obj(raw)
        lines.append(
            f"| {name} | {c['cases']} | {c['judged']} | {c['pass']} | {c['fail']} | "
            f"{c['unable_to_verify']} | {c['invalid_output']} | {c['unavailable']} | "
            f"{c['quote_found']} | {c['quote_missing']} | {c['passages_not_given']} |"
        )
    order = _obj(block["order"])
    lines += [
        "",
        "## Checks on the judge (reported)",
        "",
        "Repeatability: trial 1 of every behaviour case judged a second time in the same "
        "session. Order: grounded asked again on trial 1 of every case with the passages in "
        "reverse order.",
        "",
        "| Check | Pairs | Agree |",
        "|---|---|---|",
    ]
    for name, raw in _obj(block["repeatability"]).items():
        pair = _obj(raw)
        lines.append(f"| repeat: {name} | {pair['pairs']} | {pair['agree']} |")
    lines.append(f"| order: grounded reversed | {order['pairs']} | {order['agree']} |")
    lines += [
        "",
        "## Canaries (a hard stop on the judge)",
        "",
        "| Item | Criterion | Side | Verdict | Status | On side |",
        "|---|---|---|---|---|---|",
    ]
    for raw in _list(canaries["results"]):
        row = _obj(raw)
        lines.append(
            f"| {row['id']} | {row['criterion']} | {row['side']} | {row['verdict']} | "
            f"{row['status']} | {'yes' if row['on_side'] else 'no'} |"
        )
    tokens, latency = _obj(block["tokens"]), _obj(block["latency_ms"])
    lines += [
        "",
        "## Tokens and time",
        "",
        "Every call's tokens as its server reported them; a call that reported none is "
        "unreported, never estimated. The generator's are the source run's.",
        "",
        "| Role | Calls | Prompt | Completion | Unreported |",
        "|---|---|---|---|---|",
    ]
    for role, raw in tokens.items():
        t = _obj(raw)
        lines.append(
            f"| {role} | {t['calls']} | {t['prompt']} | {t['completion']} | {t['unreported']} |"
        )
    lines += [
        "",
        f"- Judge calls' latency: p50 {_fmt(latency['p50'])} ms, p95 {_fmt(latency['p95'])} ms "
        f"(n {latency['n']}); the run took {totals['duration_s']} s",
        "",
        "## Cases",
        "",
        "Passes out of judged trials, per criterion.",
        "",
        "| Case | Group | Status by trial | " + " | ".join(CRITERIA) + " |",
        "|---|---|---|" + "---|" * len(CRITERIA),
    ]
    for case_id, rows in _by_case(cases).items():
        cells: list[str] = []
        for criterion in CRITERIA:
            judged = [_verdicts(r)[criterion] for r in rows if criterion in _verdicts(r)]
            passed = sum(v["verdict"] == "pass" for v in judged)
            cells.append(f"{passed} of {len(judged)}" if judged else "-")
        statuses = ", ".join(str(r["source_status"]) for r in rows)
        lines.append(f"| {case_id} | {group(rows[0])} | {statuses} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- the checks against the source


def find_source(run_dir: Path, root: Path, run_id: str) -> Path | None:
    """The source run: beside the judged record (runs/tmp or runs/published), else published."""
    for candidate in (run_dir.parent / run_id, root / PUBLISHED / run_id):
        if (candidate / "manifest.json").is_file():
            return candidate
    return None


def read_source(source: Path) -> tuple[bytes, Json, list[Json]]:
    raw = (source / "manifest.json").read_bytes()
    manifest = _obj(json.loads(raw.decode("utf-8")))
    text = (source / "cases.jsonl").read_text(encoding="utf-8")
    return raw, manifest, [_obj(json.loads(line)) for line in text.splitlines() if line.strip()]


def verdict_problems(
    verdict: Json,
    criterion: str,
    version: str,
    shown: list[str],
    answer: str | None,
    where: str,
    answer_known: bool = True,
) -> list[str]:
    """A verdict whose fields do not follow from its reply, or whose checks do not follow from
    the answer and the passages it was shown (answer_known=False: the quote check is not
    recomputed, for a canary of another version of the set)."""
    where = f"{where} {criterion}"
    problems: list[str] = []
    if [str(i) for i in _list(verdict["shown_ids"])] != shown:
        problems.append(f"{where}: shown {verdict['shown_ids']}, not the passages it sees {shown}")
    status, reply = verdict["status"], verdict["reply"]
    prompt = PROMPTS.get(version)
    if prompt is None:
        return [*problems, f"{where}: no parser for judge prompt {version}"]
    if status == Status.UNAVAILABLE.value:
        if reply is not None or verdict["verdict"] != "unable_to_verify":
            problems.append(f"{where}: an unavailable verdict has no reply and is unable_to_verify")
        return problems
    if not isinstance(reply, str):
        return [*problems, f"{where}: a {status} verdict keeps its reply"]
    try:
        parsed = prompt.parse(reply)
    except prompt.InvalidVerdict:
        if status != Status.INVALID_OUTPUT.value or verdict["verdict"] != "unable_to_verify":
            problems.append(f"{where}: its reply is off the schema, so it is invalid_output")
        return problems
    if status != Status.OK.value:
        return [*problems, f"{where}: its reply parses, so its status is ok, not {status}"]
    fields = (
        verdict["verdict"],
        verdict["answer_quote"],
        [str(i) for i in _list(verdict["passage_ids"])],
        verdict["reason"],
    )
    if fields != (parsed.verdict, parsed.answer_quote, list(parsed.passage_ids), parsed.reason):
        problems.append(f"{where}: its verdict, quote, passage ids or reason are not its reply's")
    if answer_known and verdict["quote_found"] != prompt.quote_found(parsed.answer_quote, answer):
        problems.append(f"{where}: quote_found does not follow from the answer")
    if verdict["passages_given"] != (set(parsed.passage_ids) <= set(shown)):
        problems.append(f"{where}: passages_given does not follow from the passages shown")
    return problems


def _source_fields(source: Json) -> Json:
    """What a judged line copies from its source line."""
    tokens = {"prompt": source["prompt_tokens"], "completion": source["completion_tokens"]}
    return {
        "split": source["split"],
        "tenant": source["tenant"],
        "question": source["question"],
        "retrieved": source["retrieved"],
        "kind": source["kind"],
        "source_status": source["status"],
        "answer_sha256": sha256_text(str(source["answer"])),
        "source_called": source_called(source),
        "source_tokens": tokens,
    }


def line_problems(
    line: Json, source: Json, version: str, context: bool, where: str, partial: bool = False
) -> list[str]:
    """A judged line whose copied fields, criteria or verdicts do not follow from its source. In a
    partial record (its cap hit) a check on the judge may hold fewer calls than it would."""
    problems: list[str] = []
    expected = _source_fields(source)
    for name in ("expected", "golden_id", "position"):
        if name in source:
            expected[name] = source[name]
    for name, value in expected.items():
        if line.get(name) != value:
            problems.append(f"{where}: {name} is not its source line's")
    if problems:
        return problems
    wanted = [*trial_criteria(line), *([CONTEXT] if context else [])]
    verdicts = _verdicts(line)
    if sorted(verdicts) != sorted(wanted):
        return [f"{where}: judged on {sorted(verdicts)}, not its criteria {sorted(wanted)}"]
    answer = str(source["answer"])
    for criterion, verdict in verdicts.items():
        sees_answer = "answer" in PROMPTS[version].RULES[criterion].sees
        shown = shown_ids(criterion, source, version=version)
        problems += verdict_problems(
            verdict, criterion, version, shown, answer if sees_answer else None, where
        )
    trial_one = line["trial"] == 1 and line["source_status"] == Status.OK.value
    repeat = _verdicts(line, "repeat")
    wanted_repeat = list(trial_criteria(line)) if trial_one and line["kind"] == "behaviour" else []
    allowed = (
        set(repeat) <= set(wanted_repeat) if partial else sorted(repeat) == sorted(wanted_repeat)
    )
    if not allowed:
        problems.append(f"{where}: repeated {sorted(repeat)}, not {sorted(wanted_repeat)}")
    else:
        for criterion, verdict in repeat.items():
            sees_answer = "answer" in PROMPTS[version].RULES[criterion].sees
            problems += verdict_problems(
                verdict,
                criterion,
                version,
                shown_ids(criterion, source, version=version),
                answer if sees_answer else None,
                f"{where} (repeat)",
            )
    reversed_ = _verdicts(line, "reversed")
    wanted_order = [GROUNDED] if trial_one and GROUNDED in trial_criteria(line) else []
    order_ok = set(reversed_) <= set(wanted_order) if partial else sorted(reversed_) == wanted_order
    if not order_ok:
        problems.append(f"{where}: order check on {sorted(reversed_)}, not {wanted_order}")
    elif reversed_:
        problems += verdict_problems(
            reversed_[GROUNDED],
            GROUNDED,
            version,
            shown_ids(GROUNDED, source, reverse=True, version=version),
            answer,
            f"{where} (reversed)",
        )
    latencies = [
        cast(float, v["latency_ms"])
        for f in ("verdicts", "repeat", "reversed")
        for v in _verdicts(line, f).values()
    ]
    if line["latency_ms"] != round(sum(latencies), 3):
        problems.append(f"{where}: latency_ms is not the sum of its calls'")
    return problems


def canary_problems(manifest: Json, root: Path) -> list[str]:
    """The canary results: every item on its side (a stop writes no record), each verdict as its
    reply gives it, and, while the canary file is the one the record names, its items, criteria
    and sides in order."""
    block = _obj(manifest["canaries"])
    version = str(_obj(manifest["judge_prompt"])["version"])
    rows = [_obj(r) for r in _list(block["results"])]
    problems: list[str] = []
    if not rows:
        problems.append("a judged run carries its canary results")
    for row in rows:
        where = f"canary {row['id']}"
        expected_on_side = row["status"] == Status.OK.value and row["verdict"] == row["side"]
        if row["on_side"] is not expected_on_side:
            problems.append(f"{where}: on_side does not follow from its verdict")
        if not row["on_side"]:
            problems.append(f"{where} is off its side: a judged run stops before any judged call")
    path = root / str(block["path"])
    try:
        current = path.read_bytes()
    except OSError:
        current = b""
    if hashlib.sha256(current).hexdigest() != block["sha256"]:
        # another version of the set: the items are kept as recorded, each verdict still read
        # again from its reply
        for row in rows:
            problems += verdict_problems(
                row,
                str(row["criterion"]),
                version,
                [str(i) for i in _list(row["shown_ids"])],
                None,
                f"canary {row['id']}",
                answer_known=False,
            )
        return problems
    try:
        items = canary_set.load(path)
    except canary_set.CanaryError as error:
        return [*problems, f"the canary file cannot be read ({error})"]
    if [(r["id"], r["criterion"], r["side"]) for r in rows] != [
        (c.id, c.criterion, c.side) for c in items
    ]:
        problems.append("the canary results are not the canary file's items, criteria and sides")
    by_id = {c.id: c for c in items}
    for row in rows:
        canary = by_id.get(str(row["id"]))
        if canary is None:
            continue
        shown = [p if isinstance(p, str) else p.chunk_id for p in canary.passages or ()]
        sees_answer = "answer" in PROMPTS[version].RULES[canary.criterion].sees
        problems += verdict_problems(
            row,
            canary.criterion,
            version,
            shown,
            canary.answer if sees_answer else None,
            f"canary {canary.id}",
        )
    return problems


def judged_problems(manifest: Json, cases: Sequence[Json], run_dir: Path, root: Path) -> list[str]:
    """A judged run: its manifest fields, its source found and unchanged, every line tied to its
    source line, each line's criteria and verdicts as its source and replies give them, the
    reference answers (while the golden file is current) and the canaries."""
    problems: list[str] = []
    if missing := [f for f in JUDGED_MANIFEST if f not in manifest]:
        return [f"a judged run needs {missing}"]
    if extra := [f for f in NOT_JUDGED if f in manifest]:
        problems.append(f"a judged run has no {extra}")
    if "judged" not in _obj(manifest["results"]):
        problems.append("a judged run needs results.judged")
    for case in cases:
        if missing := [f for f in LINE_FIELDS if f not in case]:
            problems.append(f"case {case['case_id']} trial {case['trial']}: needs {missing}")
    if problems:
        return problems
    source_block = _obj(manifest["source"])
    source_dir = find_source(run_dir, root, str(source_block["run_id"]))
    if source_dir is None:
        return [f"the source run {source_block['run_id']} is not found beside it or published"]
    try:
        raw, source_manifest, source_cases = read_source(source_dir)
    except (OSError, ValueError) as error:
        return [f"the source run cannot be read ({error})"]
    if hashlib.sha256(raw).hexdigest() != source_block["manifest_sha256"]:
        problems.append(f"the source run {source_block['run_id']} has another manifest sha256")
    cases_bytes = (source_dir / "cases.jsonl").read_bytes()
    files = _obj(source_manifest.get("files") or {})
    if hashlib.sha256(cases_bytes).hexdigest() != files.get("cases.jsonl"):
        problems.append("the source run's cases.jsonl is not the one its manifest seals")
    if source_manifest.get("suite") != source_block["suite"] or source_block["suite"] != (
        "generation"
    ):
        problems.append("the source of a judged run is a generation run")
    for name in ("split", "trials"):
        if manifest[name] != source_manifest.get(name):
            problems.append(f"{name} is not the source run's")
    for name in ("chunker", "embedder", "retriever", "corpus"):
        if manifest[name] != source_manifest.get(name):
            problems.append(f"{name} is not the source run's")
    dataset, source_dataset = _obj(manifest["dataset"]), _obj(source_manifest["dataset"])
    if (dataset["path"], dataset["sha256"]) != (source_dataset["path"], source_dataset["sha256"]):
        problems.append("the dataset is not the source run's")
    if problems:
        return problems
    by_key = {(str(c["case_id"]), cast(int, c["trial"])): c for c in source_cases}
    keys = [(str(c["case_id"]), cast(int, c["trial"])) for c in cases]
    source_keys = list(by_key)
    if keys != source_keys and not (manifest["partial"] and keys == source_keys[: len(keys)]):
        problems.append("the lines are not the source run's case-trials, in its order")
        return problems
    version = str(_obj(manifest["judge_prompt"])["version"])
    if version not in PROMPTS:
        return [f"no parser for judge prompt {version}"]
    if _obj(manifest["judge_prompt"])["sha256"] != PROMPTS[version].fingerprint():
        problems.append(f"the judge prompt's sha256 is not {version}'s fingerprint")
    grouped = _by_case([by_key[k] for k in keys])
    lines = _by_case(cases)
    for case_id, rows in lines.items():
        sources = grouped[case_id]
        source_lines = [{**s, "source_status": s["status"]} for s in sources]
        context = set(context_trials(source_lines)) if not manifest["partial"] else None
        for line, source in zip(rows, sources, strict=True):
            where = f"case {case_id} trial {line['trial']}"
            if context is None:  # a partial record: its last case may lack trials
                carries = CONTEXT in _verdicts(line)
            else:
                carries = cast(int, line["trial"]) in context
            problems += line_problems(
                line, source, version, carries, where, bool(manifest["partial"])
            )
    unavailable = sum(
        v["status"] == Status.UNAVAILABLE.value
        for c in cases
        for f in ("verdicts", "repeat", "reversed")
        for v in _verdicts(c, f).values()
    )
    if unavailable and not manifest["partial"]:
        problems.append(f"{unavailable} judge call(s) unavailable but partial is false")
    problems += reference_problems(manifest, cases, root)
    problems += canary_problems(manifest, root)
    return problems


def reference_problems(manifest: Json, cases: Sequence[Json], root: Path) -> list[str]:
    """While the golden file is the one the record names, each line's reference_sha256 is the
    sha256 of the reference answer docs/CRITERIA.md gives its case (null for a case without)."""
    dataset = _obj(manifest["dataset"])
    path = root / str(dataset["path"])
    try:
        current = path.read_bytes()
    except OSError:
        return []
    if hashlib.sha256(current).hexdigest() != dataset["sha256"]:
        return []
    try:
        refs = references(root, path)
    except (OSError, ValueError) as error:
        return [f"the reference answers cannot be read ({error})"]
    problems: list[str] = []
    for case in cases:
        reference = reference_of(case, refs)
        expected = None if reference is None else sha256_text(reference)
        if case["reference_sha256"] != expected:
            problems.append(
                f"case {case['case_id']} trial {case['trial']}: reference_sha256 is not its "
                "reference answer's"
            )
    return problems
