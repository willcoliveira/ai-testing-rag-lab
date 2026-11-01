"""Failure causes (S8, GA4 and GA5): one cause per failed case-trial of a generation or retrieval
run, chosen by the first rule that applies, in this order, from fields the case line already
holds, so `raglab.evals.record.validate` recomputes it and a published record can be read without
change (`raglab causes <run>`).

1. **ingestion**: a labelled section's chunk ids are not all in the inventory the run searched
   (quarantined by the instruction scan, or absent at the run's chunk settings), or one of the
   case's features is split at those settings (raglab.ingest.chunk_fit: the cited values cannot
   sit in one chunk);
2. **retrieval**: a labelled section was not retrieved (`labels[].found` false, which covers a
   flag-conflict case's conflict side not retrieved), or a retrieval question's recall is under 1;
3. **abstention**: an abstain case not abstained, or abstained and still stating a value
   (`no_value` false); or an answerable case with every label retrieved whose given label is
   abstain (over-abstention);
4. **generation**: everything else that failed with its labels retrieved: a wrong decision label,
   a missing citation of a labelled section, a wrong or missing conflict field, a canary, a
   must-not-contain string, an answer withheld by a guard.

Rule 1 reads the corpus, so a tag is not a pure function of the record: it is computed when the
run is made, from the chunks the run searched (`Context.of`), and stored; `validate` recomputes it
only while the record's corpus sha256 is that of the corpus rebuilt at the record's chunk settings
(`Context.for_record`); otherwise the stored tags stand as history and only the counts are
recomputed. A trial whose status is unavailable or invalid_output has no cause (null): it is the
fallback contract, and a run with an unavailable trial is partial and never published. A passed
trial's cause is null. Attack records keep their per-check failures, where the layer is the cause,
and get the reported `other_tenant_claim` count (raglab.evals.attack_record); a judged record's
failed verdicts split into retrieval (the case's `context_sufficient` verdict is a fail) and
generation (the rest), reported by `raglab causes` only, since that split rests on an uncalibrated
criterion (docs/THRESHOLDS.md).

What the rule cannot separate (docs/THRESHOLDS.md says so too): a model that abstains because the
passage it was given is ambiguous from one that abstains out of habit (both `abstention`); a wrong
value with the right chunk retrieved, whether the chunk's text or the model misled it
(`generation`); an ingestion split and a retrieval miss on the same section (`ingestion`, because
the order decides). The counts are a triage, not a diagnosis.

The counts: `results.causes` holds, per cause, the case-trials and the cases (a case takes the
**earliest cause in the rule order** above among its failed trials, whatever the trial order: the
maintainer's answer of 2026-10-31 on choice 2, "Keep the rule order (Recommended)"; the plan's
"the cause of the first of its failed trials in the order above" reads that way), plus the passed
ones and those with no cause; the per-trial counts are the honest ones and the report shows both.
"""

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from raglab.chunk.sections import ChunkSettings
from raglab.core.types import Chunk, Status
from raglab.evals import retrieval
from raglab.evals.record import Json, as_json, as_list
from raglab.ingest import chunk_fit, pipeline, scan

CAUSES = ("ingestion", "retrieval", "abstention", "generation")
PASSED, NO_CAUSE = "passed", "no_cause"
COUNTED = (*CAUSES, PASSED, NO_CAUSE)
NO_CAUSE_STATUSES = frozenset({Status.UNAVAILABLE.value, Status.INVALID_OUTPUT.value})
CAUSED_SUITES = frozenset({"retrieval", "generation"})
SCHEMA_VERSION = "causes.v1"
OUT = "runs/causes"
CONTEXT = "context_sufficient"


@dataclass(frozen=True)
class Context:
    """What rule 1 reads: the chunk ids the run searched and the features split at its settings."""

    searched: frozenset[str]
    split_features: frozenset[str]

    @classmethod
    def of(cls, chunks: Sequence[Chunk], root: Path) -> "Context":
        """The context of a run being made, from the chunks its retriever searches."""
        return cls(
            frozenset(str(c.chunk_id) for c in chunks), chunk_fit.split_features(chunks, root)
        )

    @classmethod
    def for_record(cls, manifest: Json, root: Path) -> "Context | None":
        """The context of a finished record: the corpus rebuilt at its chunk settings (through
        the instruction scan for a generation run, as the index is built), when its sha256 is the
        record's; None when it is not (the stored tags are history) or the suite has no causes."""
        if manifest["suite"] not in CAUSED_SUITES:
            return None
        chunker = as_json(manifest["chunker"])
        settings = ChunkSettings(cast(int, chunker["chunk_size"]), cast(int, chunker["overlap"]))
        try:
            chunks: Sequence[Chunk] = pipeline.ingest(root, settings).chunks
        except (pipeline.IngestError, OSError, ValueError):
            return None
        if manifest["suite"] == "generation":
            chunks = scan.scan(chunks).kept
        if retrieval.corpus_sha256(list(chunks)) != as_json(manifest["corpus"])["sha256"]:
            return None
        return cls.of(chunks, root)


def _labels(case: Json) -> list[Json]:
    return [as_json(x) for x in as_list(case.get("labels", []))]


def labelled_ids(case: Json) -> set[str]:
    """Every chunk id a case's labels name, the members of a group included."""
    ids: set[str] = set()
    for label in _labels(case):
        ids |= {str(i) for i in as_list(label["chunk_ids"])}
        for member in as_list(label.get("any_of", [])):
            ids |= {str(i) for i in as_list(as_json(member)["chunk_ids"])}
    return ids


def failed(case: Json) -> bool:
    """A generation trial failed when its checks did not all pass; a retrieval question failed
    when its recall is under 1."""
    if "checks" in case:
        return not bool(as_json(case["checks"]).get("passed"))
    recall = case.get("recall")  # a retrieval case without its scores (refused elsewhere) fails
    return isinstance(recall, bool) or not isinstance(recall, int | float) or recall < 1


def cause_of(case: Json, context: Context | None) -> str | None:
    """The cause of a failed trial by the first rule that applies (the module docstring); None
    for a passed trial or one with no cause (status unavailable or invalid_output). Without a
    context rule 1 is not read."""
    if case.get("status") in NO_CAUSE_STATUSES or not failed(case):
        return None
    labels = _labels(case)
    if context is not None:
        if labelled_ids(case) - context.searched:
            return "ingestion"
        if any(str(f) in context.split_features for f in as_list(case.get("feature_ids", []))):
            return "ingestion"
    if any(not label["found"] for label in labels):
        return "retrieval"
    if "checks" not in case:  # a retrieval question failed on its recall alone
        return "retrieval"
    checks = as_json(case["checks"])
    if case.get("expected") == "abstain":
        if not checks.get("abstained") or not checks.get("no_value"):
            return "abstention"
    elif labels and case["status"] == Status.OK.value and case["label"] == "abstain":
        return "abstention"
    return "generation"


def tag(cases: Sequence[Json], context: Context | None) -> list[str | None]:
    return [cause_of(case, context) for case in cases]


def counts(cases: Sequence[Json]) -> Json:
    """`results.causes` from the lines' `cause` fields: per cause the case-trials and the cases
    (a case takes the earliest cause in CAUSES' order among its failed trials; passed when every
    trial passed; no_cause when every failed trial has none)."""
    trials: dict[str, int] = dict.fromkeys(COUNTED, 0)
    by_case: dict[str, list[tuple[bool, str | None]]] = {}
    for case in cases:
        cause = cast(str | None, case.get("cause"))
        passed = cause is None and not failed(case)
        trials[PASSED if passed else cause or NO_CAUSE] += 1
        by_case.setdefault(str(case["case_id"]), []).append((passed, cause))
    per_case: dict[str, int] = dict.fromkeys(COUNTED, 0)
    for rows in by_case.values():
        found = [cause for passed, cause in rows if not passed and cause is not None]
        if found:
            per_case[min(found, key=CAUSES.index)] += 1
        elif all(passed for passed, _ in rows):
            per_case[PASSED] += 1
        else:
            per_case[NO_CAUSE] += 1
    return {"case_trials": trials, "cases": per_case}


def problems(manifest: Json, cases: Sequence[Json], root: Path) -> list[str]:
    """A record whose causes do not follow from its lines: a line with a cause while others have
    none, a cause on a passed trial or on a trial with no cause, results.causes not the counts of
    the lines, or (while the corpus is the record's) a tag that is not the rule's."""
    if manifest["suite"] not in CAUSED_SUITES:
        return []
    with_cause = [c for c in cases if "cause" in c]
    results = as_json(manifest["results"])
    if not with_cause:
        return ["results.causes needs a cause on every line"] if "causes" in results else []
    out: list[str] = []
    if len(with_cause) != len(cases):
        out.append(f"{len(cases) - len(with_cause)} line(s) have no cause while others do")
        return out
    if "causes" not in results:
        out.append("the lines carry causes, so the manifest needs results.causes")
    elif results["causes"] != counts(cases):
        out.append(f"results.causes {results['causes']} are not the counts of the lines")
    context = Context.for_record(manifest, root)
    for case in cases:
        where = f"case {case['case_id']} trial {case.get('trial', 1)}"
        stored = case["cause"]
        try:
            out.extend(_case_problems(case, stored, context, where))
        except (KeyError, TypeError, ValueError) as error:  # a field the rule reads is missing
            out.append(f"{where}: its cause cannot be read ({error!r})")
    return out


def _case_problems(case: Json, stored: object, context: Context | None, where: str) -> list[str]:
    if stored is not None and stored not in CAUSES:
        return [f"{where}: cause {stored!r} is not one of {CAUSES}"]
    if stored is not None and (case.get("status") in NO_CAUSE_STATUSES or not failed(case)):
        return [f"{where}: a passed trial, or one with no cause, has cause {stored!r}"]
    if stored is None and failed(case) and case.get("status") not in NO_CAUSE_STATUSES:
        return [f"{where}: a failed trial has no cause"]
    if context is not None and stored != (expected := cause_of(case, context)):
        return [f"{where}: cause {stored!r}, but the rule gives {expected!r}"]
    return []


# ---------------------------------------------------------------- the report lines

RULE_NOTE = (
    "One cause per failed case-trial, the first rule that applies: ingestion (a labelled chunk "
    "the run did not search, or a feature split at the chunk settings), retrieval (a labelled "
    "section not retrieved), abstention (an abstain case answered or stating a value, or an "
    "answerable case abstaining with its labels retrieved), generation (the rest). A case takes "
    "the earliest cause in that order among its failed trials. The rule reads the record's "
    "fields and the corpus, never the model's reasons: an ambiguous passage and a habit both "
    "read as abstention, a chunk's text and the model both read as generation (a triage, not a "
    "diagnosis)."
)


def report_lines(block: Json) -> list[str]:
    trials, per_case = as_json(block["case_trials"]), as_json(block["cases"])
    lines = [
        "",
        "## Causes (no judge)",
        "",
        RULE_NOTE,
        "",
        "| Cause | Case-trials | Cases |",
        "|---|---|---|",
    ]
    lines += [f"| {name} | {trials[name]} | {per_case[name]} |" for name in COUNTED]
    return lines


# ---------------------------------------------------------------- derived files (raglab causes)


def seal(data: Json) -> str:
    body = {k: v for k, v in data.items() if k != "sha256"}
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def judged_counts(cases: Sequence[Json]) -> Json:
    """A judged record's failed verdicts per criterion, split into retrieval (the line's, or its
    case's trial-1, context_sufficient verdict is a fail) and generation; reported only."""
    context_fail: dict[str, bool] = {}
    for case in cases:
        verdicts = as_json(case.get("verdicts") or {})
        if CONTEXT in verdicts:
            context_fail[str(case["case_id"])] = as_json(verdicts[CONTEXT])["verdict"] == "fail"
    found: dict[str, dict[str, int]] = {}
    for case in cases:
        for criterion, raw in as_json(case.get("verdicts") or {}).items():
            if criterion == CONTEXT or as_json(raw)["verdict"] != "fail":
                continue
            which = "retrieval" if context_fail.get(str(case["case_id"])) else "generation"
            found.setdefault(criterion, {"retrieval": 0, "generation": 0})[which] += 1
    return {"failed_verdicts": found, "rests_on": f"{CONTEXT}, uncalibrated (docs/THRESHOLDS.md)"}


def derive(manifest: Json, cases: Sequence[Json], manifest_bytes: bytes, root: Path) -> Json:
    """The causes of a run read without change: for a generation or retrieval run every line's
    cause by the rule (recomputed when the corpus is the record's, else the stored tags, which
    the file then says are historical; a record without tags is tagged now only when the corpus
    is the record's) and the counts; for an attack run the reported other_tenant_claim count; for
    a judged run the failed verdicts split by context_sufficient. Sealed with its own sha256."""
    suite = str(manifest["suite"])
    data: Json = {
        "schema_version": SCHEMA_VERSION,
        "run_id": manifest["run_id"],
        "suite": suite,
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
    }
    if suite in CAUSED_SUITES:
        context = Context.for_record(manifest, root)
        if context is not None:
            tags = tag(cases, context)
            data["recomputed"] = True
        elif all("cause" in c for c in cases):
            tags = [cast(str | None, c["cause"]) for c in cases]
            data["recomputed"] = False
        else:
            raise ValueError(
                f"{manifest['run_id']} carries no causes and its corpus (sha256 "
                f"{str(as_json(manifest['corpus'])['sha256'])[:12]}) is not the one here, so the "
                "rule cannot read it"
            )
        tagged = [{**c, "cause": t} for c, t in zip(cases, tags, strict=True)]
        data["counts"] = counts(tagged)
        data["cases"] = [
            {"case_id": c["case_id"], "trial": c.get("trial", 1), "cause": t}
            for c, t in zip(cases, tags, strict=True)
        ]
    elif suite == "attack":
        from raglab.evals import attack_record

        claims = attack_record.other_tenant_claims(cases, root)
        data["counts"] = {"other_tenant_claim": attack_record.claim_counts(claims, cases)}
        data["cases"] = [
            {"case_id": c["case_id"], "trial": c["trial"], "other_tenant_claim": claim}
            for c, claim in zip(cases, claims, strict=True)
        ]
        data["cause"] = "generation"
    else:
        data["counts"] = judged_counts(cases)
    data["sha256"] = seal(data)
    return data


def check_file(path: Path) -> list[str]:
    """Why a derived file is not what `raglab causes` wrote: its seal is not its content's."""
    try:
        data = as_json(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError) as error:
        return [f"{path.name}: unreadable ({error})"]
    if data.get("schema_version") != SCHEMA_VERSION:
        return [f"{path.name}: schema_version is not {SCHEMA_VERSION}"]
    if data.get("sha256") != seal(data):
        return [f"{path.name}: its sha256 is not its content's: the file was edited"]
    return []


def write(root: Path, data: Json, out: Path | None = None) -> Path:
    out = out if out is not None else root / OUT
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{data['run_id']}.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def summary(data: Json) -> list[str]:
    """One line per count, for the terminal and the ledger."""
    lines = [f"{data['run_id']} ({data['suite']})"]
    found = as_json(data["counts"])
    if data["suite"] in CAUSED_SUITES:
        state = "recomputed from the corpus" if data["recomputed"] else "as recorded (historical)"
        trials, per_case = as_json(found["case_trials"]), as_json(found["cases"])
        lines.append(f"  causes {state}:")
        lines += [
            f"  {name}: {trials[name]} case-trial(s), {per_case[name]} case(s)" for name in COUNTED
        ]
    elif data["suite"] == "attack":
        claim = as_json(found["other_tenant_claim"])
        lines.append(
            f"  other_tenant_claim (reported, never gated; cause generation): "
            f"{claim['case_trials']} case-trial(s) in cases {claim['cases'] or 'none'}"
        )
    else:
        for criterion, raw in as_json(found["failed_verdicts"]).items():
            split = as_json(raw)
            lines.append(
                f"  {criterion}: {split['retrieval']} failed verdict(s) retrieval, "
                f"{split['generation']} generation"
            )
        lines.append(f"  rests on {found['rests_on']}")
    return lines
