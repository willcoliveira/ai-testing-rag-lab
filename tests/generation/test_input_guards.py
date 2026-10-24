"""S3 AC6 (TEST-PLAN R1, tenant-required; R-21): a question that is empty, over 500 characters or
holds control characters, and a request without a tenant, with an unknown one, with "shared" or
with a tenant the caller may not use, is refused before retrieval: the retriever is never called.
After retrieval, a chunk of another tenant blocks the answer before the model sees it."""

import pytest

from raglab.adapters.fake import FakeChat
from raglab.core.types import ScoredChunk, Status
from raglab.generate.pipeline import Pipeline
from raglab.guard import default_guards
from raglab.guard.limits import MAX_CHARS, InputLimits
from raglab.guard.tenant import TenantGuard
from tests.conftest import ROOT
from tests.generation_support import small_pipeline
from tests.retrieval_support import PACK

pytestmark = [pytest.mark.unit, pytest.mark.security]
OK_QUESTION = "How many characters must passwords have?"


@pytest.mark.parametrize(
    ("question", "reason"),
    [
        ("", "empty"),
        ("   \n\t ", "empty"),
        ("x" * (MAX_CHARS + 1), "501 characters; the limit is 500"),
        ("password\x00length", "U+0000"),
        ("password \x1b[31m length", "U+001B"),
        ("password ‮ length", "U+202E"),  # right-to-left override (Cf)
        ("pass​word length", "U+200B"),  # zero-width space (Cf)
        ("password  length", "U+E000"),  # private use (Co)
        ("password\r\nlength", "U+000D"),
        ("password \x7f length", "U+007F"),
    ],
)
def test_a_question_over_the_limits_is_refused_before_retrieval(question, reason):
    pipeline, spy = small_pipeline()
    outcome = pipeline.ask(question, "tenant-a")
    assert outcome.answer.status is Status.REFUSED
    assert outcome.refused_by() == "input-limits"
    assert reason in outcome.events[0].reason
    assert spy.calls == 0
    assert outcome.retrieved == ()


@pytest.mark.parametrize(
    "question",
    ["x" * MAX_CHARS, "Line one\nline two\twith a tab", "Mot de passe: combien de caractères ?"],
)
def test_a_question_within_the_limits_is_answered(question):
    pipeline, spy = small_pipeline()
    assert pipeline.ask(question, "tenant-a").answer.status is Status.OK
    assert spy.calls == 1


@pytest.mark.parametrize(
    ("tenant", "caller", "reason"),
    [
        (None, None, "got None"),
        ("", None, "got ''"),
        ("shared", None, "got 'shared'"),
        ("tenant-c", None, "got 'tenant-c'"),
        ("TENANT-A", None, "got 'TENANT-A'"),
        ("tenant-b", frozenset({"tenant-a"}), "the caller may not use tenant-b"),
        ("tenant-a", frozenset[str](), "the caller may not use tenant-a"),
    ],
)
def test_a_request_without_a_tenant_the_caller_may_use_is_refused_before_retrieval(
    tenant, caller, reason
):
    pipeline, spy = small_pipeline()
    outcome = pipeline.ask(OK_QUESTION, tenant, caller)
    assert outcome.answer.status is Status.REFUSED
    assert outcome.refused_by() == "tenant"
    assert reason in outcome.events[0].reason
    assert spy.calls == 0


def test_the_tenant_is_checked_before_the_question():
    pipeline, _ = small_pipeline()
    assert pipeline.ask("", "shared").refused_by() == "tenant"
    assert [g.name for g in default_guards(ROOT, PACK)] == [
        "tenant",
        "input-limits",
        "injection",
        "register",
        "citations",
        "links",
        "secrets-pii",
        "prompt-leak",
    ]


def test_without_any_guard_a_request_with_no_tenant_still_fails_closed():
    pipeline, spy = small_pipeline(guards=[])
    outcome = pipeline.ask(OK_QUESTION, None)
    assert (outcome.answer.status, outcome.refused_by(), spy.calls) == (
        Status.REFUSED,
        "pipeline",
        0,
    )


def test_a_caller_may_use_the_tenants_of_its_token():
    pipeline, spy = small_pipeline()
    outcome = pipeline.ask(OK_QUESTION, "tenant-a", frozenset({"tenant-a"}))
    assert outcome.answer.status is Status.OK
    assert spy.calls == 1


class LeakyRetriever:
    """A broken retriever that returns another tenant's chunk."""

    name = "leaky"

    def retrieve(self, query: str, tenant: str, k: int) -> list[ScoredChunk]:
        return [ScoredChunk(c, 1.0) for c in PACK if c.tenant == "tenant-b"]


def test_another_tenants_chunk_after_retrieval_blocks_the_answer_before_the_model():
    chat = FakeChat()
    pipeline = Pipeline(LeakyRetriever(), chat, default_guards(ROOT, PACK), 3)
    outcome = pipeline.ask(OK_QUESTION, "tenant-a")
    assert outcome.answer.status is Status.BLOCKED
    assert (outcome.events[0].guard, outcome.events[0].stage) == ("tenant", "retrieved")
    assert chat.requests == []


def test_the_guards_refuse_bad_settings():
    with pytest.raises(ValueError, match="max_chars"):
        InputLimits(0)
    assert TenantGuard().check_retrieved("tenant-a", []) is None
