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

S9: the pipeline writes spans to its tracer (the no-op tracer unless `raglab serve` gives it one;
docs/OBSERVABILITY.md): raglab's pipeline span, and inside it the retrieval span and the chat span
(`chat <model>`, open through the parse, so an invalid reply is its error). What the pipeline span
keeps follows the guards: a guard's decision as its name, stage and the API's fixed reason key
(raglab.core.reasons), never the event's text; the tenant only once the input guards have passed;
the retrieved and cited ids only once the retrieved-chunk guards have passed; and, with the
content opt-in, the question and the answer of an ok answer only. Nothing of a refused or withheld
request, and no exception's message, is ever set on a span.

S7 (with S9's attributes as they are): the decision the span keeps is the one that stopped the
request; when nothing stopped it, a drop step's (the register filter: its name, "retrieved" and
"dropped"), and the status, ok, tells the two apart. The retrieved ids are the chunks kept, so a
chunk a drop step left out never reaches a span. A request dropped from and then withheld shows
only the stop in its trace; the drop stays in the run record and the server log.
"""

import time
from collections.abc import Sequence
from dataclasses import dataclass

from raglab.core.ports import ChatModel, Guardrail, NoopTracer, Retriever, Span, Tracer
from raglab.core.reasons import drop_key, reason_key
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
from raglab.obs import names, traced

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
        *,
        tracer: Tracer | None = None,
    ) -> None:
        if k < 1:
            raise ValueError(f"k must be at least 1, not {k}")
        self.retriever = retriever
        self.chat = chat
        self.guards = list(guards)
        self.k = k
        self.tracer: Tracer = NoopTracer() if tracer is None else tracer

    def ask(
        self,
        question: str,
        tenant: str | None,
        caller_tenants: frozenset[str] | None = None,
        seed: int = 0,
    ) -> Outcome:
        with self.tracer.span(names.PIPELINE_SPAN) as span:
            outcome = self._ask(question, tenant, caller_tenants, seed)
            self._record(span, outcome, question, tenant)
            return outcome

    def _record(self, span: Span, outcome: Outcome, question: str, tenant: str | None) -> None:
        """What the pipeline span keeps of an outcome, after every guard has decided."""
        status = outcome.answer.status
        span.set(names.PROMPT_VERSION, PROMPT_VERSION)
        span.set(names.STATUS, status.value)
        span.set(names.LABEL, outcome.answer.label)
        decisions = [(e, reason_key(e)) for e in outcome.events] or [
            (e, drop_key(e)) for e in outcome.dropped
        ]
        for event, key in decisions:  # the stop, or else the drops (status ok tells them apart)
            span.set(names.GUARD, event.guard)
            span.set(names.GUARD_STAGE, event.stage)
            span.set(names.GUARD_REASON, key)
        if status is Status.REFUSED or tenant is None:
            return
        span.set(names.TENANT, tenant)
        if any(event.stage == "retrieved" for event in outcome.events):
            return
        span.set(names.RETRIEVED_IDS, tuple(r.chunk.chunk_id for r in outcome.retrieved))
        span.set(names.CITED_IDS, outcome.answer.cited_ids)
        if status is Status.UNAVAILABLE:
            span.fail("timeout" if outcome.timed_out else "unavailable")
        elif status is Status.INVALID_OUTPUT:
            span.fail("invalid_output")
        elif status is Status.OK and self.tracer.capture_content:
            span.set(names.QUESTION, question)
            span.set(names.ANSWER, outcome.answer.text)

    def _retrieve(self, question: str, tenant: str) -> tuple[ScoredChunk, ...]:
        with self.tracer.span(f"{names.RETRIEVAL} {names.DATA_SOURCE}", "client") as span:
            span.set(names.OPERATION, names.RETRIEVAL)
            span.set(names.DATA_SOURCE_ID, names.DATA_SOURCE)
            span.set(names.RETRIEVAL_TOP_K, self.k)
            retrieved = tuple(self.retriever.retrieve(question, tenant, self.k))
            span.set(names.RETRIEVED_COUNT, len(retrieved))
            return retrieved

    def _ask(
        self,
        question: str,
        tenant: str | None,
        caller_tenants: frozenset[str] | None,
        seed: int,
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
        retrieved = self._retrieve(question, tenant)
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
        with self.tracer.span(f"{names.CHAT} {self.chat.model}", "client") as span:
            for key, value in traced.chat_attributes(
                self.chat.model, self.chat.describe(), seed, PROMPT_VERSION
            ):
                span.set(key, value)
            try:
                reply = self.chat.complete(request)
            except ChatUnavailable as error:
                timed_out = isinstance(error, ChatTimeout)
                span.fail("timeout" if timed_out else "unavailable")
                return done(
                    Answer.withheld(Status.UNAVAILABLE),
                    retrieved,
                    error=str(error),
                    timed_out=timed_out,
                )
            tokens = (reply.prompt_tokens, reply.completion_tokens)
            for key, count in zip(
                (names.USAGE_INPUT_TOKENS, names.USAGE_OUTPUT_TOKENS), tokens, strict=True
            ):
                if count is not None:  # as the server reported it; unreported stays unset
                    span.set(key, count)
            try:
                answer = prompt.parse(reply.text)
            except prompt.InvalidOutput as error:
                span.fail("invalid_output")
                return done(
                    Answer.withheld(Status.INVALID_OUTPUT), retrieved, None, str(error), *tokens
                )
        for guard in self.guards:
            if event := guard.check_output(answer, retrieved):
                return done(Answer.withheld(Status.BLOCKED), retrieved, event, None, *tokens)
        return done(answer, retrieved, None, None, *tokens)
