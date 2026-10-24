"""S6 JC2: the judged run's wall-clock cap is the plan's rule on the judged baseline on golden set
v2's exact call count (docs/plans/2026-10-23-s6-judge-calibration.md, "The cap"): the count x the
slower measured mean per call x 1.5, up to the next half hour.

The count is the dry run's of 2026-10-24 (the S6 ledger: judged.run on S4b's run 1 with a scripted
fake judge, no model). Here it is counted again from the source record with the same rules the
judged run applies (the canaries; each answer on its criteria and context_sufficient once per case;
trial 1 of every behaviour case judged again; grounded on trial 1 with the passages reversed), so
the check needs neither the corpus's OCR text nor a judge, and runs in CI. The means are read from
the two judged records the plan names: each run's duration over its judge calls.
"""

import json
import math
from collections import defaultdict

import pytest

from raglab.core.types import Status
from raglab.evals import judged_record, publish, record
from raglab.evals.config import load_judge
from raglab.judge import canaries
from tests.conftest import ROOT

pytestmark = pytest.mark.unit
SOURCE = "20261024T090351Z-generation-local-ollama-dev-ade9397"  # S4b's run 1, the source
MEASURED = ("20261021T081852Z-judge-local-dev-5aa0ec5", "20261023T090413Z-judge-local-dev-c14acb0")
DRY_RUN_CALLS = 1400  # the dry run's count (the S6 ledger)
JUDGE_CONFIG = ROOT / "config" / "judge-local.toml"


def judge_calls(lines: list[dict], canary_items: int) -> dict[str, int]:
    """The judge calls a judged run of these source lines makes, by kind."""
    rows = [{**s, "source_status": s["status"]} for s in lines]
    by_case: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_case[str(row["case_id"])].append(row)
    context = sum(len(judged_record.context_trials(case)) for case in by_case.values())
    verdicts = sum(len(judged_record.trial_criteria(row)) for row in rows) + context
    first = [r for r in rows if r["trial"] == 1 and r["source_status"] == Status.OK.value]
    repeat = sum(len(judged_record.trial_criteria(r)) for r in first if r["kind"] == "behaviour")
    reverse = sum(judged_record.GROUNDED in judged_record.trial_criteria(r) for r in first)
    return {
        "canaries": canary_items,
        "verdicts": verdicts,
        "repeat": repeat,
        "reversed": reverse,
    }


def mean_per_call(run_id: str) -> float:
    manifest = json.loads((ROOT / publish.PUBLISHED / run_id / record.MANIFEST).read_text("utf-8"))
    tokens = manifest["results"]["judged"]["tokens"]
    calls = sum(tokens[role]["calls"] for role in ("judge", "judge_checks", "canaries"))
    return manifest["totals"]["duration_s"] / calls


def test_the_judged_runs_calls_on_s4bs_run_1_are_the_dry_runs_count():
    _, lines = record.read(ROOT / publish.PUBLISHED / SOURCE)
    config = load_judge(JUDGE_CONFIG, ROOT)
    items = len(canaries.load(ROOT / config.judging.canaries))
    calls = judge_calls(lines, items)
    assert calls == {"canaries": 19, "verdicts": 1015, "repeat": 268, "reversed": 98}
    assert sum(calls.values()) == DRY_RUN_CALLS


def test_the_cap_is_the_rule_on_the_dry_runs_count():
    means = [round(mean_per_call(run_id), 3) for run_id in MEASURED]
    assert means == [5.710, 5.384]
    rule = math.ceil(DRY_RUN_CALLS * max(means) * 1.5 / 1800) * 1800
    assert rule == 12600
    config = load_judge(JUDGE_CONFIG, ROOT)
    assert config.judging.run_timeout_s == rule
    text = JUDGE_CONFIG.read_text(encoding="utf-8")
    for stated in ("1,400 judge calls", "5.710 s", "5.384 s", "x 1.5", "12,600 s"):
        assert stated in text, f"the cap's comment states {stated!r}"
