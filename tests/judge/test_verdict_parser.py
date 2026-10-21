"""S5 AC2: the strict verdict parser and the judge over the ChatModel port. A reply off the verdict
schema is recorded as unable_to_verify with status invalid_output and the reply kept, never
repaired; no reply is unable_to_verify with status unavailable; the quote is checked against the
answer and the passage ids against the passages shown, and both are reported beside the verdict.
The judge's replies are scripted with FakeChat (raglab.adapters.fake, imported by the tests only).
"""

import json

import pytest

from raglab.adapters.fake import FakeChat
from raglab.core.types import ChatTimeout, ChatUnavailable, JudgeItem, Passage, Status
from raglab.judge.llm import LLMJudge
from raglab.judge.prompts import judge_v2 as prompt
from tests.retrieval_support import PACK

pytestmark = pytest.mark.unit

PASSAGES = tuple(Passage.of(c) for c in PACK[:2])
ANSWER = "Passwords must be at least 15 characters.\nPassphrases are allowed."


def verdict_reply(
    verdict: str = "pass",
    quote: str = "at least 15 characters",
    ids: list[str] | None = None,
    reason: str = "The first passage states the minimum length.",
    **extra: object,
) -> str:
    body: dict[str, object] = {
        "answer_quote": quote,
        "passage_ids": [PACK[0].chunk_id] if ids is None else ids,
        "reason": reason,
        "verdict": verdict,
        **extra,
    }
    return json.dumps(body)


def grounded(answer: str = ANSWER) -> JudgeItem:
    return JudgeItem("grounded", "How long must a password be?", PASSAGES, None, answer, 20261020)


def test_a_reply_in_the_schema_parses():
    parsed = prompt.parse(verdict_reply(ids=[PACK[0].chunk_id, PACK[0].chunk_id]))
    assert (parsed.verdict, parsed.answer_quote, parsed.passage_ids) == (
        "pass",
        "at least 15 characters",
        (PACK[0].chunk_id,),  # a repeated id is named once
    )
    for verdict in ("fail", "unable_to_verify"):
        assert prompt.parse(verdict_reply(verdict)).verdict == verdict


@pytest.mark.parametrize(
    ("text", "match"),
    [
        (verdict_reply(confidence=0.9), "not the schema's"),  # AC2's break: an extra field
        (json.dumps({"verdict": "pass", "answer_quote": "", "reason": "r"}), "not the schema's"),
        (verdict_reply("PASS"), "verdict 'PASS' is not one of"),
        (verdict_reply("partial"), "is not one of"),
        (verdict_reply(reason=" "), "reason is not a non-empty string"),
        (verdict_reply(ids="A-PWD@1.0/4.1/1"), "passage_ids is not a list of strings"),  # type: ignore[arg-type]
        (verdict_reply(ids=[1]), "passage_ids is not a list of strings"),  # type: ignore[list-item]
        (verdict_reply(quote=None), "answer_quote is not a string"),  # type: ignore[arg-type]
        ("```json\n" + verdict_reply() + "\n```", "not JSON"),  # no fence is stripped
        ("Verdict: pass", "not JSON"),
        ("[" + verdict_reply() + "]", "not a JSON object"),
        (
            '{"answer_quote": "", "passage_ids": [], "reason": "r", "verdict": "fail", '
            '"verdict": "pass"}',
            "repeats a field",
        ),
        (verdict_reply() + "\nThe answer is supported.", "not JSON"),
    ],
)
def test_a_reply_off_the_schema_is_refused_never_repaired(text, match):
    with pytest.raises(prompt.InvalidVerdict, match=match):
        prompt.parse(text)


def test_the_judge_records_an_off_schema_reply_as_unable_to_verify_with_the_reply_kept():
    text = verdict_reply(confidence=0.9)
    verdict = LLMJudge(FakeChat([text])).judge(grounded())
    assert (verdict.verdict, verdict.status) == ("unable_to_verify", Status.INVALID_OUTPUT)
    assert verdict.reply == text
    assert verdict.error is not None
    assert "not the schema's" in verdict.error
    assert (verdict.answer_quote, verdict.passage_ids, verdict.reason) == ("", (), "")


def test_no_reply_is_unable_to_verify_with_status_unavailable():
    verdict = LLMJudge(FakeChat([ChatTimeout("timeout after 180 s")])).judge(grounded())
    assert (verdict.verdict, verdict.status, verdict.reply) == (
        "unable_to_verify",
        Status.UNAVAILABLE,
        None,
    )
    assert verdict.timed_out is True
    other = LLMJudge(FakeChat([ChatUnavailable("HTTP 501")])).judge(grounded())
    assert (other.status, other.timed_out, other.error) == (Status.UNAVAILABLE, False, "HTTP 501")


def test_the_quote_is_checked_against_the_answer_and_reported():
    judge = LLMJudge(
        FakeChat(
            [
                verdict_reply(quote="at least   15\ncharacters"),  # whitespace runs read as one
                verdict_reply(quote="at least 12 characters"),  # not in the answer
                verdict_reply(quote=""),  # an empty quote is not found
            ]
        )
    )
    found = [judge.judge(grounded()).quote_found for _ in range(3)]
    assert found == [True, False, False]


def test_the_quote_of_a_criterion_that_sees_no_answer_is_not_checked():
    item = JudgeItem("context_sufficient", None, PASSAGES, "At least 15 characters.", None, 1)
    verdict = LLMJudge(FakeChat([verdict_reply(quote="")])).judge(item)
    assert verdict.quote_found is None
    assert verdict.verdict == "pass"


def test_passage_ids_that_were_not_shown_are_reported():
    judge = LLMJudge(
        FakeChat([verdict_reply(ids=[PACK[1].chunk_id]), verdict_reply(ids=["A-OTHER@1/1/1"])])
    )
    assert judge.judge(grounded()).passages_given is True
    assert judge.judge(grounded()).passages_given is False


def test_a_verdict_keeps_what_it_was_shown_and_what_it_cost():
    chat = FakeChat([verdict_reply("fail")])
    verdict = LLMJudge(chat).judge(grounded())
    assert verdict.shown_ids == (PACK[0].chunk_id, PACK[1].chunk_id)
    assert verdict.criterion == "grounded"
    assert verdict.latency_ms >= 0
    # FakeChat reports no token counts: unreported, never estimated
    assert (verdict.prompt_tokens, verdict.completion_tokens) == (None, None)
    [request] = chat.requests
    assert request.seed == 20261020
    assert request.schema_name == prompt.SCHEMA_NAME
    assert request.schema == prompt.VERDICT_SCHEMA
    assert [m.role for m in request.messages] == ["system", "user"]
    assert request.messages[0].content == prompt.SYSTEM


def test_the_judge_describes_its_model_and_its_prompt():
    judge = LLMJudge(FakeChat(name="fake-judge"))
    assert judge.describe() == {"provider": "fake", "model": "fake-judge", "digest": "fake"}
    assert (judge.version, judge.fingerprint()) == ("judge-v2", prompt.fingerprint())


def test_a_verdict_off_the_schema_or_without_a_reply_is_never_a_pass():
    from raglab.core.types import Verdict

    with pytest.raises(ValueError, match="is unable_to_verify"):
        Verdict("grounded", "pass", Status.INVALID_OUTPUT, "", (), "", None, True, (), "x")
    with pytest.raises(ValueError, match="status is ok, invalid_output or unavailable"):
        Verdict("grounded", "fail", Status.BLOCKED, "", (), "", None, True, (), "x")
