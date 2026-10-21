"""S5 AC8, offline: the checks on the judge. The order check asks grounded again on trial 1 of
every case with the passages in reverse order (the pointwise form of how-to 04 step 5's position
bias), and the repeatability check judges trial 1 of every behaviour case a second time; both run
after every answer is judged, and both agreements are counted in the record. A reversed call shown
the passages in their original order is refused."""

import pytest

from raglab.core.types import ChatRequest
from raglab.evals import record
from tests.judge_support import (
    answer_of,
    criterion_of,
    fake_judge,
    judged_root,
    passage_ids_of,
    reseal,
    run_judged,
    script,
    verdict,
)
from tests.retrieval_support import read_run

pytestmark = pytest.mark.unit


def test_the_order_check_shows_the_passages_in_reverse_order(tmp_path):
    root, source = judged_root(tmp_path)
    judge, chat = fake_judge()
    run_dir = run_judged(root, source, judge, chat.describe())
    manifest, lines = read_run(run_dir)
    grounded = [r for r in chat.requests if criterion_of(r) == "grounded"]
    differs = 0
    for line in lines:
        if line["trial"] != 1 or "reversed" not in line:
            continue
        forward = line["verdicts"]["grounded"]["shown_ids"]
        backward = line["reversed"]["grounded"]["shown_ids"]
        assert backward == forward[::-1], line["case_id"]
        differs += backward != forward
    assert differs == 4  # B-ANS, B-FC, B-FC2 and B-ABQ retrieved two passages each
    # in the requests themselves: every reversed request mirrors an earlier forward one
    orders = [passage_ids_of(r) for r in grounded]
    reversed_requests = orders[-manifest["results"]["judged"]["order"]["pairs"] :]
    for ids in reversed_requests:
        assert ids[::-1] in orders[: -len(reversed_requests)]


def test_the_checks_run_after_every_answer_is_judged(tmp_path):
    """The repeat pass and then the order pass come after the last answer's verdicts, so a repeat
    is not the request just before it."""
    root, source = judged_root(tmp_path)
    judge, chat = fake_judge()
    run_dir = run_judged(root, source, judge, chat.describe())
    manifest, lines = read_run(run_dir)
    main = sum(len(c["verdicts"]) for c in lines)
    repeats = sum(len(c.get("repeat", {})) for c in lines)
    order = sum(len(c.get("reversed", {})) for c in lines)
    canaries = len(manifest["canaries"]["results"])
    assert len(chat.requests) == canaries + main + repeats + order
    tail = chat.requests[canaries + main + repeats :]
    assert {criterion_of(r) for r in tail} == {"grounded"}
    behaviour_trial_one = [c for c in lines if c["kind"] == "behaviour" and c["trial"] == 1]
    assert repeats == sum(
        len([k for k in c["verdicts"] if k != "context_sufficient"]) for c in behaviour_trial_one
    )


def test_the_agreements_are_counted_from_the_verdicts(tmp_path):
    """A judge that fails relevant on its third sight of the same request: the fixture's two
    trials give the same answer, so the third sight is trial 1's repeat, and every repeat of
    relevant disagrees; the record counts it, and grounded's repeats and reversals agree."""
    root, source = judged_root(tmp_path)
    seen: dict[tuple[str, str], int] = {}

    def fickle(request: ChatRequest) -> str:
        key = (criterion_of(request), request.messages[-1].content)
        seen[key] = seen.get(key, 0) + 1
        answer = answer_of(request) or ""
        if key[0] == "relevant" and seen[key] == 3:
            return verdict("fail", answer[:8])
        return script(request)

    judge, chat = fake_judge(fickle)
    run_dir = run_judged(root, source, judge, chat.describe())
    manifest, _ = read_run(run_dir)
    block = manifest["results"]["judged"]
    relevant = block["repeatability"]["relevant"]
    assert relevant["pairs"] == 5  # the answer, flag-conflict and refuse-and-help cases
    assert relevant["agree"] == 0  # every repeat of relevant disagreed
    assert (
        block["repeatability"]["grounded"]["agree"] == block["repeatability"]["grounded"]["pairs"]
    )
    assert block["order"]["agree"] == block["order"]["pairs"]
    assert record.validate(run_dir, root) == []


def test_a_reversed_verdict_shown_the_original_order_is_refused(tmp_path):
    """AC8's break, as a record: the order check given the passages in their original order."""
    root, source = judged_root(tmp_path)
    run_dir = run_judged(root, source)
    manifest, lines = read_run(run_dir)
    line = next(c for c in lines if "reversed" in c)
    line["reversed"]["grounded"]["shown_ids"] = line["verdicts"]["grounded"]["shown_ids"]
    reseal(run_dir, manifest, lines)  # type: ignore[arg-type]
    problems = record.validate(run_dir, root)
    assert any("(reversed) grounded: shown" in p for p in problems), problems
