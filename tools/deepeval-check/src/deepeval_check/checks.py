"""DeepEval 4.3.1's checks (S5, AC11), every metric in eval mode `llm` and every call through
raglab's judge (deepeval_check.llm). Import deepeval_check.guard and call `opt_out` first.

1. **The custom-LLM API**: the subclass called with a schema returns its instance.
2. **The metric canary**: FaithfulnessMetric on P-01's honest answer (the canary set's C-03) and
   on its invented "five attempts" (C-01), with penalize_ambiguous_claims off and on: four scores,
   the side of the default threshold each lands on, and which of the page's two readings the run
   supports ("a claim is considered truthful if it does not contradict any facts presented in the
   retrieval_context", or "Faithfulness only rewards claims supported by the retrieval_context").
3. **The hallucination direction**: HallucinationMetric with G-01's labelled passage as its one
   context, an output consistent with it and one that contradicts it: both scores, which is
   higher, and is_successful() at the default threshold, beside the page's sentence and its read
   date. The check measures the direction; it asserts neither.
4. **The cross-check**: FaithfulnessMetric on trial 1 of the dev answer cases of a judged record's
   source, against the own judge's grounded verdict on the same answer (a two-by-two table), with
   DeepEval's calls and tokens per metric.
"""

import json
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from deepeval.metrics import FaithfulnessMetric, HallucinationMetric
from deepeval.test_case import LLMTestCase
from pydantic import BaseModel

from deepeval_check.llm import RaglabJudgeLLM
from raglab.ingest import pipeline
from raglab.judge import canaries

type Json = dict[str, object]

MODE = "llm"  # every metric's eval mode: hybrid and system_one send the judging to a hosted service
P01 = "How many password reset attempts are allowed per day?"
HALLUCINATION_PAGE = (
    "Higher is better. ... the fraction of context documents the actual_output stays consistent "
    "with, so 1 is perfect ... threshold is therefore a minimum — output passes at or above it"
)
HALLUCINATION_PAGE_READ = "2026-10-20"
G01_QUESTION = (
    "My password manager makes 50-character passwords. Do Halvenroot systems have to accept one "
    "that long?"
)
CONSISTENT = "Yes: systems must accept passwords of at least 64 characters, so 50 is accepted."
CONTRADICTING = "No: systems may cut passwords off at 20 characters, so 50 is not accepted."


class Probe(BaseModel):
    """The custom-LLM API check's schema: a verdict and a reason."""

    verdict: str
    reason: str


def custom_llm_api(llm: RaglabJudgeLLM) -> Json:
    """The subclass called with a schema returns an instance of that schema."""
    out = llm.generate(
        'Reply with a JSON object with the fields verdict ("yes" or "no") and reason (one '
        "sentence): is 64 greater than 20?",
        schema=Probe,
    )
    return {"returned": type(out).__name__, "is_instance": isinstance(out, Probe)}


def _plain(value: object) -> object:
    """A metric's intermediate output as JSON data: a pydantic model as its fields, a list item by
    item, anything else as it is."""
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, list):
        return [_plain(item) for item in cast(list[object], value)]
    return value


def _steps(metric: object, names: Sequence[str]) -> Json:
    """What a metric worked from after measure, read from its public attributes (DeepEval 4.3.1:
    a FaithfulnessMetric's truths, claims, verdicts and reason; a HallucinationMetric's verdicts
    and reason), so a score can be read from its steps."""
    return {name: _plain(getattr(metric, name, None)) for name in names}


def faithfulness(
    llm: RaglabJudgeLLM, question: str, answer: str, passages: Sequence[str], penalize: bool
) -> Json:
    metric = FaithfulnessMetric(
        model=llm, eval_mode=MODE, async_mode=False, penalize_ambiguous_claims=penalize
    )
    before = len(llm.calls)
    score = metric.measure(
        LLMTestCase(input=question, actual_output=answer, retrieval_context=list(passages))
    )
    return {
        "score": score,
        "passes": metric.is_successful(),
        "threshold": metric.threshold,
        "calls": len(llm.calls) - before,
        **_steps(metric, ("truths", "claims", "verdicts", "reason")),
    }


def hallucination(llm: RaglabJudgeLLM, question: str, output: str, context: Sequence[str]) -> Json:
    metric = HallucinationMetric(model=llm, eval_mode=MODE, async_mode=False)
    before = len(llm.calls)
    score = metric.measure(LLMTestCase(input=question, actual_output=output, context=list(context)))
    return {
        "score": score,
        "passes": metric.is_successful(),
        "threshold": metric.threshold,
        "calls": len(llm.calls) - before,
        **_steps(metric, ("verdicts", "reason")),
    }


def canary_reading(honest: Json, invented: Json) -> str:
    """Which of the faithfulness page's readings a run supports, from the honest twin's and the
    invented answer's scores with penalize_ambiguous_claims off. The canary separates them only
    when they score differently and the honest twin passes: then the invented answer passing means
    an unsupported claim that nothing contradicts counted as truthful, and failing means only
    supported claims counted. Otherwise the run supports no reading, and says so."""
    h, i = float(cast(float, honest["score"])), float(cast(float, invented["score"]))
    if h == i:
        return (
            f"not separated: the honest twin and the invented answer both scored {h:g}, so the "
            "run supports no reading"
        )
    if not honest["passes"]:
        return (
            f"not separated: the honest twin failed too ({h:g}, the invented answer {i:g}), so "
            "the run supports no reading"
        )
    if invented["passes"]:
        return (
            "not contradicted counts as truthful: the invented value passed beside the honest twin"
        )
    return "only supported claims count: the invented value failed and the honest twin passed"


def _scored(found: Json, score: float) -> Json:
    """One output's side of the direction report: its score and pass, and the metric's steps
    (verdicts and reason) when it recorded them. The session of 2026-10-21 kept only the score and
    the pass, so its steps were lost (S5 ledger); they are carried since."""
    return {
        "score": score,
        "passes": found["passes"],
        **{k: found[k] for k in ("verdicts", "reason") if k in found},
    }


def direction_report(consistent: Json, contradicting: Json) -> Json:
    """The hallucination direction, measured: which output scored higher, and the reading that
    follows (the consistent output higher means higher is better, as the page says)."""
    c, x = float(cast(float, consistent["score"])), float(cast(float, contradicting["score"]))
    higher = "consistent" if c > x else "contradicting" if x > c else "neither"
    reading = {
        "consistent": "higher is better: the consistent output scored higher",
        "contradicting": "higher is worse: the contradicting output scored higher",
        "neither": "undecided: both outputs scored the same",
    }[higher]
    return {
        "consistent": _scored(consistent, c),
        "contradicting": _scored(contradicting, x),
        "higher": higher,
        "reading": reading,
        "page": HALLUCINATION_PAGE,
        "page_read": HALLUCINATION_PAGE_READ,
    }


def metric_canary(llm: RaglabJudgeLLM, root: Path) -> Json:
    """FaithfulnessMetric on the canary set's honest twin (C-03) and invented answer (C-01), each
    with penalize_ambiguous_claims off and on."""
    items = {c.id: c for c in canaries.load(root / "datasets" / "canaries.judge.jsonl")}
    invented, honest = items["C-01"], items["C-03"]
    passages = canaries.corpus_passages(root, [invented])
    texts = [passages[i].text for i in invented.corpus_ids()]
    scores: Json = {}
    for name, item in (("honest", honest), ("invented", invented)):
        for penalize in (False, True):
            key = f"{name}, penalize {'on' if penalize else 'off'}"
            scores[key] = faithfulness(llm, P01, str(item.answer), texts, penalize)
    return {
        "scores": scores,
        "reading": canary_reading(
            cast(Json, scores["honest, penalize off"]), cast(Json, scores["invented, penalize off"])
        ),
    }


def hallucination_direction(llm: RaglabJudgeLLM, root: Path) -> Json:
    """HallucinationMetric on G-01's labelled passage, with a consistent and a contradicting
    output."""
    [chunk] = pipeline.section_chunks(root, "A-PWD-V2", "4.2")
    consistent = hallucination(llm, G01_QUESTION, CONSISTENT, [chunk.text])
    contradicting = hallucination(llm, G01_QUESTION, CONTRADICTING, [chunk.text])
    return direction_report(consistent, contradicting)


def _lines(run: Path) -> list[Json]:
    text = (run / "cases.jsonl").read_text(encoding="utf-8")
    return [cast(Json, json.loads(line)) for line in text.splitlines() if line.strip()]


def cross_check(llm: RaglabJudgeLLM, root: Path, judged: Path) -> Json:
    """FaithfulnessMetric (penalize off, the default) on trial 1 of every dev answer case of a
    judged record's source, against the own judge's grounded verdict on the same answer."""
    manifest = cast(Json, json.loads((judged / "manifest.json").read_text(encoding="utf-8")))
    source_id = str(cast(Json, manifest["source"])["run_id"])
    source = judged.parent / source_id
    if not (source / "manifest.json").is_file():
        source = root / "runs" / "published" / source_id
    by_key = {(c["case_id"], c["trial"]): c for c in _lines(source)}
    chunks = {c.chunk_id: c.text for c in pipeline.ingest(root).chunks}
    table = {
        "both pass": 0,
        "both fail": 0,
        "own pass, deepeval fail": 0,
        "own fail, deepeval pass": 0,
    }
    rows: list[Json] = []
    before = len(llm.calls)
    for line in _lines(judged):
        if (
            line.get("kind") != "behaviour"
            or line.get("expected") != "answer"
            or line["trial"] != 1
        ):
            continue
        own = cast(Json, cast(Json, line["verdicts"]).get("grounded") or {}).get("verdict")
        if own is None:
            continue  # a withheld answer: not judged
        src = by_key[(line["case_id"], line["trial"])]
        texts = [
            chunks[str(cast(Json, r)["chunk_id"])] for r in cast(list[object], src["retrieved"])
        ]
        found = faithfulness(llm, str(src["question"]), str(src["answer"]), texts, False)
        own_pass, theirs = own == "pass", bool(found["passes"])
        cell = (
            "both pass"
            if own_pass and theirs
            else "both fail"
            if not own_pass and not theirs
            else "own pass, deepeval fail"
            if own_pass
            else "own fail, deepeval pass"
        )
        table[cell] += 1
        rows.append({"case_id": line["case_id"], "own": own, "deepeval": found})
    return {
        "judged": judged.name,
        "cases": len(rows),
        "table": table,
        "rows": rows,
        "deepeval_calls": len(llm.calls) - before,
    }
