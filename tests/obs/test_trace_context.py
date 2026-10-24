"""S9-J2 (the criteria judge's round 0, fix round 1): a caller's W3C trace context is never
adopted. A `traceparent` with flags 00 must not suppress the request's spans; one with flags 01
must not choose the trace id or parent `POST /ask`; and no `tracestate` or `baggage` text may ride
out on a span, a field the attribute allowlist does not cover. Each request is answered and
exported as a trace of raglab's own, rooted at its request span, whatever headers it carries."""

import pytest
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import SpanContext, TraceFlags, TraceState

from raglab.obs import names, otel
from tests.obs_support import DEMO, Traced, leaks, traced_app

pytestmark = [pytest.mark.unit, pytest.mark.security]
CLIENT_TRACE = "4bf92f3577b34da6a3ce929d0e0e4736"
CLIENT_SPAN = "00f067aa0ba902b7"
MARK = "zebra-tracestate-5150"
BAGGAGE_MARK = "zebra-baggage-7342"
ASK = {"tenant": "tenant-a", "question": "How many characters must passwords have?"}
SPANS = {
    "POST /ask",
    names.PIPELINE_SPAN,
    "retrieval policy-pack",
    "embeddings hashing-256",
    "chat fake-echo",
}


def ask_with(flags: str) -> Traced:
    traced = traced_app()
    headers = {
        **DEMO,
        "traceparent": f"00-{CLIENT_TRACE}-{CLIENT_SPAN}-{flags}",
        "tracestate": f"vendor={MARK},other=x",
        "baggage": f"user={BAGGAGE_MARK}",
    }
    assert traced.client.post("/ask", json=ASK, headers=headers).status_code == 200
    return traced


def own_trace(spans: list[ReadableSpan]) -> None:
    """One trace of raglab's own: rooted at the request span, under no remote parent, with no
    trace state, and no client id or text anywhere."""
    named = {span.name: span for span in spans}
    assert set(named) == SPANS, sorted(named)
    root = named["POST /ask"]
    assert root.parent is None, root.parent
    contexts = [span.get_span_context() for span in spans]
    trace_ids = {f"{context.trace_id:032x}" for context in contexts if context}
    assert len(trace_ids) == 1, trace_ids
    assert trace_ids != {CLIENT_TRACE}
    for span in spans:
        assert span.parent is None or not span.parent.is_remote, span.name
        assert span.parent is None or f"{span.parent.span_id:016x}" != CLIENT_SPAN, span.name
        context = span.get_span_context()
        assert context is not None
        assert len(context.trace_state) == 0, (span.name, context.trace_state)
    assert leaks(spans, [MARK, BAGGAGE_MARK, CLIENT_TRACE, CLIENT_SPAN]) == []


@pytest.mark.parametrize("flags", ["00", "01"], ids=["not-sampled", "sampled"])
def test_a_callers_trace_context_is_never_adopted(flags):
    traced = ask_with(flags)
    own_trace(traced.spans())  # what leaves the process
    raw = traced.raw_spans() + traced.raw_spans("fastapi")
    own_trace(raw)  # and what was recorded before the allowlist


def test_redact_keeps_the_ids_and_drops_the_trace_state():
    """The exporter's own line of defence: whatever context a span carries, it leaves with its
    ids and flags and an empty trace state, its parent's too."""
    state = TraceState([("vendor", MARK)])
    context = SpanContext(int(CLIENT_TRACE, 16), 0x1111, False, TraceFlags(1), state)
    parent = SpanContext(int(CLIENT_TRACE, 16), int(CLIENT_SPAN, 16), True, TraceFlags(1), state)
    exporter = InMemorySpanExporter()
    span = ReadableSpan(
        name=names.PIPELINE_SPAN, context=context, parent=parent, resource=Resource({})
    )
    otel.AllowlistExporter(exporter).export([span])
    [out] = exporter.get_finished_spans()
    for before, after in ((context, out.context), (parent, out.parent)):
        assert after is not None
        assert (after.trace_id, after.span_id, after.trace_flags, after.is_remote) == (
            before.trace_id,
            before.span_id,
            before.trace_flags,
            before.is_remote,
        )
        assert len(after.trace_state) == 0
