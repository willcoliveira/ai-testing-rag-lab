"""S9 OB4, the redaction test: with default settings no exported span, event, status, link or
resource (FastAPI's request span included) holds the question, the answer, a chunk's text, the
system text, the bearer token or another tenant's canary; only allowlisted keys leave the process;
no exception's message or stack is recorded. With D4's opt-in, where RAGLAB_ENV is ci or local,
the question and an ok answer appear on raglab's pipeline span only.

Distinctive markers are planted in the question, a chunk, the answer, an invalid reply, an
unavailable error's text, an escaped exception and a test-only token; tenant B's canaries come from
the answer key. Each test checks what leaves (the exporter behind the allowlist) and what raglab's
code recorded before the filter (a second, unfiltered processor), so a leak is caught at its source
too."""

import json
from collections.abc import Callable

import pytest
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from raglab.adapters.fake import CHUNK_FRAME, FakeChat
from raglab.core.types import ChatRequest, ChatUnavailable
from raglab.generate.prompts import CURRENT
from raglab.ingest import answer_key
from raglab.obs import names, otel
from tests.conftest import ROOT
from tests.obs_support import LOCAL, Traced, leaks, traced_app
from tests.retrieval_support import PACK, make_chunk

pytestmark = [pytest.mark.unit, pytest.mark.security]
QUESTION_MARK = "zebra-question-7731"
CHUNK_MARK = "zebra-chunk-5519"
ANSWER_MARK = "zebra-answer-2290"
INVALID_MARK = "zebra-invalid-8812"
UNAVAILABLE_MARK = "zebra-unavailable-4410"
EXCEPTION_MARK = "zebra-exception-6620"
TOKEN = "zebra-token-3307"  # noqa: S105  # a test-only bearer token, planted as a marker
QUESTION = f"How many characters must passwords have? {QUESTION_MARK}"
CHUNKS = [
    make_chunk(
        "A-PWD@1.0/4.1/1",
        "tenant-a",
        f"Passwords must be at least 15 characters. {CHUNK_MARK}",
        "4.1",
    ),
    *PACK[1:],
]
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
TOKENS = {TOKEN: frozenset({"tenant-a", "tenant-b"})}
SYSTEM = CURRENT.SYSTEM.split(". ")[0]  # the system text's first sentence
TENANT_B = answer_key.canaries(ROOT)["tenant-b"]
MARKERS = [
    QUESTION_MARK,
    CHUNK_MARK,
    ANSWER_MARK,
    INVALID_MARK,
    UNAVAILABLE_MARK,
    EXCEPTION_MARK,
    TOKEN,
    SYSTEM,
    *TENANT_B,
]


def cite_first(text: str) -> Callable[[ChatRequest], str]:
    """A FakeChat script: an ok answer with this text, citing the first chunk it was given."""

    def reply(request: ChatRequest) -> str:
        first = CHUNK_FRAME.findall(request.messages[-1].content)[0][0]
        return json.dumps(
            {
                "label": "answer",
                "answer": text,
                "cited_ids": [first],
                "conflict_ids": [],
                "conflict_note": "",
            }
        )

    return reply


def explode(request: ChatRequest) -> str:
    raise RuntimeError(f"an unexpected failure {EXCEPTION_MARK}")


CASES = ("ok", "echo", "invalid", "unavailable", "exception")


def scripted(case: str) -> tuple[FakeChat, int]:
    """A fresh FakeChat for the case (a list script is used up by one request) and the status
    code the API answers with."""
    return {
        "ok": lambda: (FakeChat(cite_first(f"Fifteen characters. {ANSWER_MARK}")), 200),
        "echo": lambda: (FakeChat(), 200),
        "invalid": lambda: (FakeChat([f"not json {INVALID_MARK}"]), 502),
        "unavailable": lambda: (FakeChat([ChatUnavailable(f"HTTP 503 {UNAVAILABLE_MARK}")]), 503),
        "exception": lambda: (FakeChat(explode), 500),
    }[case]()


def ask(traced: Traced, code: int, tenant: str = "tenant-a") -> None:
    response = traced.client.post(
        "/ask", json={"tenant": tenant, "question": QUESTION}, headers=HEADERS
    )
    assert response.status_code == code


def keys_beyond_the_allowlist(traced: Traced, content: bool = False) -> list[str]:
    allowed = {
        "raglab": names.SPAN_KEYS | (set(names.CONTENT_KEYS) if content else set()),
        "fastapi": names.HTTP_KEYS,
    }
    out: list[str] = []
    for span in traced.spans():
        scope = span.instrumentation_scope.name if span.instrumentation_scope else ""
        out += [f"{span.name}: {k}" for k in span.attributes or {} if k not in allowed[scope]]
    return out


@pytest.mark.parametrize("case", CASES)
def test_by_default_no_content_leaves_in_any_span(case):
    chat, code = scripted(case)
    traced = traced_app(chat, chunks=CHUNKS, tokens=TOKENS)
    ask(traced, code)
    spans = traced.spans()
    assert {span.name for span in spans} >= {"POST /ask", names.PIPELINE_SPAN}
    assert leaks(spans, MARKERS) == []
    assert keys_beyond_the_allowlist(traced) == []
    for span in spans:
        assert span.events == ()
        assert span.links == ()
        assert span.status.description is None
        assert dict(span.resource.attributes) == {
            "service.name": "raglab",
            "service.version": "0.1.0",
        }


@pytest.mark.parametrize("case", CASES)
def test_by_default_raglabs_code_records_no_content_and_no_exception(case):
    """The source, before the allowlist: raglab's spans hold only reviewed keys, no event (no
    recorded exception) and no marker."""
    chat, code = scripted(case)
    traced = traced_app(chat, chunks=CHUNKS, tokens=TOKENS)
    ask(traced, code)
    raw = traced.raw_spans()
    assert raw
    assert leaks(raw, MARKERS) == []
    for span in raw:
        assert span.events == ()
        assert set(span.attributes or {}) <= names.SPAN_KEYS, span.name
        assert span.status.description is None


def test_the_request_span_never_keeps_a_query_a_header_or_an_address():
    traced = traced_app(chunks=CHUNKS, tokens=TOKENS)
    response = traced.client.post(
        f"/ask?q={QUESTION_MARK}",
        json={"tenant": "tenant-a", "question": QUESTION},
        headers={**HEADERS, "User-Agent": CHUNK_MARK, "X-Forwarded-For": ANSWER_MARK},
    )
    assert response.status_code == 200
    raw_request = traced.raw_spans("fastapi")
    assert any(QUESTION_MARK in text for _, text in _values(raw_request))  # FastAPI recorded it
    assert leaks(traced.spans(), MARKERS) == []  # and the allowlist kept it in


def _values(spans):
    from tests.obs_support import every_value

    return [pair for span in spans for pair in every_value(span)]


def test_with_the_opt_in_the_question_and_an_ok_answer_appear_on_the_pipeline_span_only():
    chat = FakeChat(cite_first(f"Fifteen characters. {ANSWER_MARK}"))
    traced = traced_app(chat, chunks=CHUNKS, tokens=TOKENS, environ=LOCAL)
    ask(traced, 200)
    spans = traced.by_name()
    pipeline = dict(spans[names.PIPELINE_SPAN].attributes or {})
    assert pipeline[names.QUESTION] == QUESTION
    assert pipeline[names.ANSWER] == f"Fifteen characters. {ANSWER_MARK}"
    others = [span for name, span in spans.items() if name != names.PIPELINE_SPAN]
    assert leaks(others, [QUESTION_MARK, ANSWER_MARK]) == []
    assert leaks(list(spans.values()), [CHUNK_MARK, TOKEN, SYSTEM, *TENANT_B]) == []
    assert keys_beyond_the_allowlist(traced, content=True) == []
    for key in names.NEVER_SET:
        assert all(key not in (span.attributes or {}) for span in spans.values()), key


@pytest.mark.parametrize("case", ["invalid", "unavailable", "exception"])
def test_with_the_opt_in_a_failed_request_keeps_no_content(case):
    chat, code = scripted(case)
    traced = traced_app(chat, chunks=CHUNKS, tokens=TOKENS, environ=LOCAL)
    ask(traced, code)
    assert leaks(traced.spans(), MARKERS) == []
    assert leaks(traced.raw_spans(), MARKERS) == []


def test_a_key_outside_the_allowlist_never_reaches_the_exporter():
    """The allowlist's own test: a key nobody reviewed, set on a raglab span, is recorded at the
    source and dropped on the way out; so is a content key while the opt-in is off, and every
    attribute of a span from an unknown instrumentation scope."""
    exporter = InMemorySpanExporter()
    provider = otel.provider_with(exporter, batch=False)
    tracer = otel.OtelTracer(provider)
    with tracer.span(names.PIPELINE_SPAN) as span:
        span.set("raglab.unreviewed", TOKEN)
        span.set(names.STATUS, "ok")
    other = provider.get_tracer("someone-else")
    with other.start_as_current_span("theirs") as theirs:
        theirs.set_attribute(names.STATUS, "ok")
        theirs.set_attribute("http.route", "/ask")
    ours, foreign = exporter.get_finished_spans()
    assert dict(ours.attributes or {}) == {names.STATUS: "ok"}
    assert dict(foreign.attributes or {}) == {}


def test_content_keys_are_dropped_when_set_and_when_exported_while_the_opt_in_is_off():
    exporter = InMemorySpanExporter()
    tracer = otel.OtelTracer(otel.provider_with(exporter, batch=False), capture_content=False)
    with tracer.span(names.PIPELINE_SPAN) as span:
        span.set(names.QUESTION, QUESTION)
    assert dict(exporter.get_finished_spans()[0].attributes or {}) == {}
    # a tracer that captures, behind an exporter built without the opt-in: still dropped
    exporter = InMemorySpanExporter()
    provider = otel.provider_with(exporter, capture_content=False, batch=False)
    with otel.OtelTracer(provider, capture_content=True).span(names.PIPELINE_SPAN) as span:
        span.set(names.ANSWER, ANSWER_MARK)
    assert dict(exporter.get_finished_spans()[0].attributes or {}) == {}


def test_the_resource_is_built_without_the_environment(monkeypatch):
    monkeypatch.setenv("OTEL_RESOURCE_ATTRIBUTES", f"host.name={TOKEN},owner={CHUNK_MARK}")
    monkeypatch.setenv("OTEL_SERVICE_NAME", ANSWER_MARK)
    traced = traced_app(chunks=CHUNKS, tokens=TOKENS)
    ask(traced, 200)
    assert leaks(traced.spans(), MARKERS) == []
    assert leaks(traced.raw_spans(), [TOKEN, CHUNK_MARK, ANSWER_MARK]) == []
