"""From a question and a tenant to a structured answer:

input guards -> retrieve top k -> retrieved guards -> drop steps -> prompt -> model -> parse ->
output guards.

Each step but the drop steps can end the request, and none of them guesses an answer:
- an input guard's event refuses it before retrieval (status refused; the retriever is never
  called);
- a retrieved guard's event withholds it before the model is called (status blocked);
- a drop step (S7, the register filter) leaves chunks out of the prompt, with an event per
  document, and the request goes on from the chunks that remain: the model, the output guards,
  the answer's citations and the outcome's retrieved chunks are those kept;
- a model that gives no reply (ChatUnavailable) gives status unavailable;
- a reply outside the answer schema gives status invalid_output (counted, never repaired);
- an output guard's event withholds the parsed answer (status blocked; the citation validator).

The Outcome keeps what a run record and the API need: the answer, the retrieved chunks (those the
prompt was built from), the event that ended the request, the drop events, the error text of an
unavailable or invalid reply, the tokens and the latency.
"""

import time
from collections.abc import Sequence
from dataclasses import dataclass

from raglab.core.ports import ChatModel, Guardrail, Retriever
from raglab.core.types import (
    Answer,
    ChatMessage,
    ChatRequest,
    ChatTimeout,
    ChatUnavailable,
    GuardEvent,
    ScoredChunk,
    Status,
)
from raglab.generate.prompts import CURRENT as prompt

PROMPT_VERSION = prompt.VERSION


@dataclass(frozen=True)
class Outcome:
    answer: Answer
    retrieved: tuple[ScoredChunk, ...] = ()
    events: tuple[GuardEvent, ...] = ()
    error: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    latency_ms: float = 0.0
    timed_out: bool = False
    dropped: tuple[GuardEvent, ...] = ()  # S7: the drop steps' events; the request went on

    def refused_by(self) -> str | None:
        """The guard that refused the request at input, if one did."""
        if self.answer.status is Status.REFUSED and self.events:
            return self.events[0].guard
        return None


class Pipeline:
    def __init__(
        self,
        retriever: Retriever,
        chat: ChatModel,
        guards: Sequence[Guardrail],
        k: int,
    ) -> None:
        if k < 1:
            raise ValueError(f"k must be at least 1, not {k}")
        self.retriever = retriever
        self.chat = chat
        self.guards = list(guards)
        self.k = k

    def ask(
        self,
        question: str,
        tenant: str | None,
        caller_tenants: frozenset[str] | None = None,
        seed: int = 0,
    ) -> Outcome:
        started = time.perf_counter()

        dropped: list[GuardEvent] = []

        def done(
            answer: Answer,
            retrieved: tuple[ScoredChunk, ...] = (),
            event: GuardEvent | None = None,
            error: str | None = None,
            prompt_tokens: int | None = None,
            completion_tokens: int | None = None,
            timed_out: bool = False,
        ) -> Outcome:
            return Outcome(
                answer,
                retrieved,
                (event,) if event else (),
                error,
                prompt_tokens,
                completion_tokens,
                round((time.perf_counter() - started) * 1000, 3),
                timed_out,
                tuple(dropped),
            )

        for guard in self.guards:
            if event := guard.check_input(question, tenant, caller_tenants):
                return done(Answer.withheld(Status.REFUSED), event=event)
        if tenant is None:  # without the tenant guard the request still fails closed
            return done(
                Answer.withheld(Status.REFUSED),
                event=GuardEvent("pipeline", "input", "the request names no tenant"),
            )
        retrieved = tuple(self.retriever.retrieve(question, tenant, self.k))
        for guard in self.guards:
            if event := guard.check_retrieved(tenant, retrieved):
                return done(Answer.withheld(Status.BLOCKED), retrieved, event)
        for guard in self.guards:  # the kept chunks are handed on, explicitly, to every step after
            retrieved, events = guard.drop_retrieved(tenant, retrieved)
            dropped.extend(events)
        system, user = prompt.build(question, tenant, retrieved)
        request = ChatRequest(
            (ChatMessage("system", system), ChatMessage("user", user)),
            prompt.SCHEMA_NAME,
            prompt.ANSWER_SCHEMA,
            seed,
        )
        try:
            reply = self.chat.complete(request)
        except ChatUnavailable as error:
            return done(
                Answer.withheld(Status.UNAVAILABLE),
                retrieved,
                error=str(error),
                timed_out=isinstance(error, ChatTimeout),
            )
        tokens = (reply.prompt_tokens, reply.completion_tokens)
        try:
            answer = prompt.parse(reply.text)
        except prompt.InvalidOutput as error:
            return done(
                Answer.withheld(Status.INVALID_OUTPUT), retrieved, None, str(error), *tokens
            )
        for guard in self.guards:
            if event := guard.check_output(answer, retrieved):
                return done(Answer.withheld(Status.BLOCKED), retrieved, event, None, *tokens)
        return done(answer, retrieved, None, None, *tokens)
