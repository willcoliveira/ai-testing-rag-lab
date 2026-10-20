"""The judge over the ChatModel port (S5): one criterion per call, the judge-v1 prompt, the verdict
schema as the request's response format (when the model's config asks for it), and the strict
parser. The judge model is one more configuration of a chat adapter (raglab.adapters: the local
OpenAI-compatible server in S5, a hosted provider after the sign-up), and FakeChat scripts its
replies in the tests.

A call never raises for the model's sake: no reply (ChatUnavailable) gives a verdict of
unable_to_verify with status unavailable, and a reply off the schema gives unable_to_verify with
status invalid_output, the reply kept as it came. Code then checks what code can: whether the
quote is a span of the answer, and whether every passage id the verdict names was shown. Both are
reported beside the verdict; neither changes it.
"""

import time

from raglab.core.ports import ChatModel
from raglab.core.types import (
    ChatMessage,
    ChatRequest,
    ChatTimeout,
    ChatUnavailable,
    JudgeItem,
    Status,
    Verdict,
)
from raglab.judge.prompts import judge_v1 as prompt


class LLMJudge:
    def __init__(self, chat: ChatModel) -> None:
        self.chat = chat

    @property
    def version(self) -> str:
        return prompt.VERSION

    def fingerprint(self) -> str:
        return prompt.fingerprint()

    def describe(self) -> dict[str, object]:
        return self.chat.describe()

    def request(self, item: JudgeItem) -> ChatRequest:
        """The chat request of one judge call."""
        system, user = prompt.build(item)
        return ChatRequest(
            (ChatMessage("system", system), ChatMessage("user", user)),
            prompt.SCHEMA_NAME,
            prompt.VERDICT_SCHEMA,
            item.seed,
        )

    def judge(self, item: JudgeItem) -> Verdict:
        request = self.request(item)
        shown = item.shown_ids()
        started = time.perf_counter()
        try:
            reply = self.chat.complete(request)
        except ChatUnavailable as error:
            return Verdict(
                item.criterion,
                "unable_to_verify",
                Status.UNAVAILABLE,
                "",
                (),
                "",
                None,
                True,
                shown,
                None,
                latency_ms=round((time.perf_counter() - started) * 1000, 3),
                error=str(error),
                timed_out=isinstance(error, ChatTimeout),
            )
        latency = round((time.perf_counter() - started) * 1000, 3)
        try:
            parsed = prompt.parse(reply.text)
        except prompt.InvalidVerdict as error:
            return Verdict(
                item.criterion,
                "unable_to_verify",
                Status.INVALID_OUTPUT,
                "",
                (),
                "",
                None,
                True,
                shown,
                reply.text,
                reply.prompt_tokens,
                reply.completion_tokens,
                reply.reasoning,
                latency,
                str(error),
            )
        return Verdict(
            item.criterion,
            parsed.verdict,
            Status.OK,
            parsed.answer_quote,
            parsed.passage_ids,
            parsed.reason,
            prompt.quote_found(parsed.answer_quote, item.answer),
            set(parsed.passage_ids) <= set(shown),
            shown,
            reply.text,
            reply.prompt_tokens,
            reply.completion_tokens,
            reply.reasoning,
            latency,
        )
