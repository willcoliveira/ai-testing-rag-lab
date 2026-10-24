"""Calibrations for the S6 tests: a published judged record of the behaviour run
(tests.judge_support) made by a scripted local judge through the stub server, so it is not fake and
publishes; a recording judge that keeps every JudgeItem the judged run built; a small bar; and
scripted answers for the label CLI. The judge's reasons and quotes are marked (JUDGE-REASON,
JUDGE-QUOTE) so a test can tell whether any of them reached the label CLI's screen."""

import json
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from raglab.core.types import ChatRequest, JudgeItem, Verdict
from raglab.evals import calibration, publish, record
from raglab.evals.label import Shown
from raglab.judge.llm import LLMJudge
from tests.generation_support import Q_ABQ, Q_FC, Q_RH
from tests.judge_support import (
    INVENTED,
    answer_of,
    criterion_of,
    judged_root,
    local_judge,
    run_judged,
    small_inventory,
)

FOLDER = "datasets/calibration/test-c1"
REASON = "JUDGE-REASON"
QUOTE = "JUDGE-QUOTE"
SEALED = datetime(2026, 10, 24, 9, 0, 0, tzinfo=UTC)
# grounded fails these questions' answers; abstains fails the second abstain case
GROUNDED_FAILS = (Q_FC, Q_RH, Q_ABQ)
ABSTAINS_FAILS = (Q_ABQ,)

BAR_TEXT = """name = "test-c1"
judge_prompt = "judge-v2"
reads = "kappa"
undefined = "reported only"

[sample]
rule = "s6-1"
seed = 20261023

[agreement]
resamples = 200
level = 0.95
seed = 20261023

[relabel]
per_criterion = 1
min_gap_hours = 24

[criteria.grounded]
judge_pass = 3
judge_fail = 3
trusted = 0.80
stop = 0.60

[criteria.abstains]
judge_pass = 1
judge_fail = 1
trusted = 0.80
stop = 0.60
"""


class Recording:
    """A judge that keeps every item it is asked about, then asks the real one."""

    def __init__(self, judge: LLMJudge) -> None:
        self.inner = judge
        self.items: list[JudgeItem] = []

    @property
    def version(self) -> str:
        return self.inner.version

    def fingerprint(self) -> str:
        return self.inner.fingerprint()

    def describe(self) -> dict[str, object]:
        return self.inner.describe()

    def judge(self, item: JudgeItem) -> Verdict:
        self.items.append(item)
        return self.inner.judge(item)


def marked_script() -> Any:
    """Verdicts by criterion and question, each with a marked reason and a marked quote (never a
    span of the answer); the canaries on their side."""
    count = iter(range(1, 10_000))

    def reply(request: ChatRequest) -> str:
        criterion = criterion_of(request)
        answer = answer_of(request) or ""
        user = request.messages[-1].content
        fails = {"grounded": GROUNDED_FAILS, "abstains": ABSTAINS_FAILS}.get(criterion, ())
        failed = INVENTED in answer or any(f"<question>\n{q}\n</question>" in user for q in fails)
        return json.dumps(
            {
                "answer_quote": QUOTE,
                "passage_ids": [],
                "reason": f"{REASON}-{criterion}-{next(count)}.",
                "verdict": "fail" if failed else "pass",
            }
        )

    return reply


def published_root(tmp_path: Path) -> tuple[Path, str, str, Recording]:
    """(root, judged run id, source run id, the recording judge) with the source run and its
    judged record published, and the test bar written in the calibration folder."""
    root, source = judged_root(tmp_path, local=True)
    judge, description, provenance = local_judge(marked_script())
    recording = Recording(judge)
    run_dir = run_judged(root, source, recording, description, provenance)  # type: ignore[arg-type]
    assert record.validate(run_dir, root) == []
    publish.publish(source, root, privacy=lambda *_: [])
    publish.publish(run_dir, root, privacy=lambda *_: [])
    folder = root / FOLDER
    folder.mkdir(parents=True)
    (folder / calibration.BAR).write_text(BAR_TEXT, encoding="utf-8")
    return root, run_dir.name, source.name, recording


def sampled_root(tmp_path: Path) -> tuple[Path, Path, str, Recording]:
    """published_root with the sample drawn: (root, folder, judged run id, recording judge)."""
    root, run_id, _, recording = published_root(tmp_path)
    folder = root / FOLDER
    calibration.draw_sample(root, folder, run_id, clock=lambda: SEALED - timedelta(hours=1))
    return root, folder, run_id, recording


def answers_for(shown: list[Shown], verdicts: dict[int, str] | None = None) -> list[str]:
    """Scripted CLI answers for each item: its verdict (pass unless given), a quote of the
    answer's first word, the first passage shown, a reason, not ambiguous."""
    out: list[str] = []
    for s in shown:
        verdict = (verdicts or {}).get(s.item.order, "pass")
        out += [verdict[0], s.answer.split()[0], "1" if s.ids else "", f"Labelled {verdict}.", "n"]
    return out


def asker(answers: list[str]) -> Any:
    feed: Iterator[str] = iter(answers)

    def ask(question: str) -> str:
        try:
            return next(feed)
        except StopIteration:
            raise EOFError from None

    return ask


def ticking(start: datetime = SEALED) -> Any:
    """A clock that moves one second a call."""
    moments = (start + timedelta(seconds=n) for n in range(1_000_000))
    return lambda: next(moments)


def inventory() -> Any:
    return small_inventory()
