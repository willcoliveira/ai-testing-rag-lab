"""S9 OB5, nothing a guard removed is kept in a trace (the main plan's guardrails table: "traces
never keep what a guard removed"). With the content opt-in on, where it is honoured: a refused
question (over 500 characters, a control character, an unknown tenant) leaves no text in any span;
an answer the citation guard withheld leaves none; a request blocked after retrieval (a tenant-B
chunk returned for tenant A) records no retrieved id and no tenant-B canary. Each decision is
recorded as the guard's name, its stage and the API's fixed reason key, never the event's own text.
The scripted retriever and FakeChat of the existing guard tests stand in for the real ones."""

import json

import pytest

from raglab.adapters.fake import FakeChat
from raglab.api.app import REASONS
from raglab.core.reasons import reason_key
from raglab.core.types import GuardEvent, ScoredChunk
from raglab.guard import default_guards
from raglab.ingest import answer_key
from raglab.obs import names
from tests.conftest import ROOT
from tests.obs_support import DEMO, LOCAL, Traced, leaks, traced_app
from tests.retrieval_support import PACK

pytestmark = [pytest.mark.unit, pytest.mark.security]
MARK = "zebra-refused-9104"
WITHHELD_MARK = "zebra-withheld-3382"
TENANT_B = answer_key.canaries(ROOT)["tenant-b"]
B_CHUNK = next(c for c in PACK if c.tenant == "tenant-b")


def pipeline_span(traced: Traced) -> dict[str, object]:
    return dict(traced.by_name()[names.PIPELINE_SPAN].attributes or {})


def everywhere(traced: Traced) -> list:
    """What left the process and what raglab's code recorded before the filter."""
    return [*traced.spans(), *traced.raw_spans()]


@pytest.mark.parametrize(
    ("body", "guard", "event_text"),
    [
        ({"tenant": "tenant-a", "question": f"{MARK} " + "x" * 500}, "input-limits", "501"),
        (
            {"tenant": "tenant-a", "question": f"{MARK} password\x00length"},
            "input-limits",
            "U+0000",
        ),
        ({"tenant": f"tenant-{MARK}", "question": "How long are passwords?"}, "tenant", "got"),
        ({"question": f"{MARK} How long are passwords?"}, "tenant", "got None"),
    ],
    ids=["over-500", "control-character", "unknown-tenant", "no-tenant"],
)
def test_a_refused_question_leaves_no_text_in_any_span(body, guard, event_text):
    traced = traced_app(environ=LOCAL)
    response = traced.client.post("/ask", json=body, headers=DEMO)
    assert response.json()["status"] == "refused"
    assert leaks(everywhere(traced), [MARK, event_text]) == []
    span = pipeline_span(traced)
    assert span[names.GUARD] == guard
    assert span[names.GUARD_STAGE] == "input"
    assert span[names.GUARD_REASON] in REASONS
    for key in (names.TENANT, names.RETRIEVED_IDS, names.CITED_IDS, *names.CONTENT_KEYS):
        assert key not in span, key
    assert set(traced.by_name()) == {"POST /ask", names.PIPELINE_SPAN}  # never retrieved


def test_an_answer_the_citation_guard_withheld_leaves_no_text():
    reply = json.dumps(
        {
            "label": "answer",
            "answer": f"Passwords are 12 characters. {WITHHELD_MARK}",
            "cited_ids": [B_CHUNK.chunk_id],  # never retrieved for tenant A
            "conflict_ids": [],
            "conflict_note": "",
        }
    )
    traced = traced_app(FakeChat([reply]), environ=LOCAL)
    body = {"tenant": "tenant-a", "question": "How many characters must passwords have?"}
    assert traced.client.post("/ask", json=body, headers=DEMO).json()["status"] == "blocked"
    assert leaks(everywhere(traced), [WITHHELD_MARK, *TENANT_B]) == []
    span = pipeline_span(traced)
    assert (span[names.GUARD], span[names.GUARD_STAGE], span[names.GUARD_REASON]) == (
        "citations",
        "output",
        "blocked",
    )
    assert span[names.CITED_IDS] == ()
    assert names.ANSWER not in span
    assert names.QUESTION not in span


class LeakyRetriever:
    """A broken retriever that returns another tenant's chunk (tests/generation/
    test_input_guards.py's)."""

    name = "leaky"

    def retrieve(self, query: str, tenant: str, k: int) -> list[ScoredChunk]:
        return [ScoredChunk(B_CHUNK, 1.0)]


def test_a_request_blocked_after_retrieval_records_no_id_and_no_canary():
    traced = traced_app(retriever=LeakyRetriever(), environ=LOCAL)
    body = {"tenant": "tenant-a", "question": "How many characters must passwords have?"}
    assert traced.client.post("/ask", json=body, headers=DEMO).json()["status"] == "blocked"
    assert B_CHUNK.chunk_id.startswith(tuple(TENANT_B))  # its id is a tenant-B canary
    assert leaks(everywhere(traced), [B_CHUNK.chunk_id, B_CHUNK.text, *TENANT_B]) == []
    span = pipeline_span(traced)
    assert (span[names.GUARD], span[names.GUARD_STAGE], span[names.GUARD_REASON]) == (
        "tenant",
        "retrieved",
        "blocked",
    )
    assert span[names.TENANT] == "tenant-a"  # the input guards had passed
    for key in (names.RETRIEVED_IDS, names.CITED_IDS, *names.CONTENT_KEYS):
        assert key not in span, key
    retrieval = dict(traced.by_name()["retrieval policy-pack"].attributes or {})
    assert retrieval[names.RETRIEVED_COUNT] == 1  # a count, never the ids
    assert "chat fake-echo" not in traced.by_name()  # the model never saw it


def test_every_default_guards_decision_has_a_key_the_api_knows():
    """S7 adds its guards here: a guard whose decision has no key in REASONS fails this test."""
    for guard in default_guards():
        for stage in ("input", "retrieved", "output"):
            key = reason_key(GuardEvent(guard.name, stage, "any text"))
            assert key in REASONS, (guard.name, stage, key)
    assert reason_key(GuardEvent("pipeline", "input", "x")) == "tenant"


def test_the_decision_key_never_carries_the_events_text():
    for text in ("the question contains character U+0000", "chunk B-PWD@1.0/3/1 of tenant-b"):
        for stage in ("input", "retrieved", "output"):
            assert reason_key(GuardEvent("tenant", stage, text)) in REASONS
            assert text not in reason_key(GuardEvent("tenant", stage, text))
