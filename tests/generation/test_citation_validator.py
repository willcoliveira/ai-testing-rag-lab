"""S3 AC3 (TEST-PLAN R7, citations-subset-of-retrieved; R-02): every id an answer cites, or names
in its conflict field, was retrieved for that answer. An answer that points at any other id is
blocked: withheld as abstain with status blocked, and the event names the ids."""

import random

import pytest

from raglab.adapters.fake import FakeChat
from raglab.core.types import ChatRequest, Status
from raglab.guard.citations import CitationValidator
from raglab.guard.limits import InputLimits
from raglab.guard.tenant import TenantGuard
from tests.generation_support import reply, small_pipeline
from tests.retrieval_support import PACK, QUESTIONS

pytestmark = pytest.mark.unit
UNRETRIEVED = "B-PWD@1.0/3/1"  # tenant B's chunk: never retrieved for a tenant A question


def test_an_answer_citing_an_unretrieved_id_is_blocked_and_recorded():
    chat = FakeChat([reply("answer", "16 characters.", cited=[UNRETRIEVED])])
    pipeline, _ = small_pipeline(chat)
    outcome = pipeline.ask("How many characters must passwords have?", "tenant-a")
    assert UNRETRIEVED not in {r.chunk.chunk_id for r in outcome.retrieved}
    answer = outcome.answer
    assert (answer.status, answer.label, answer.text, answer.cited_ids) == (
        Status.BLOCKED,
        "abstain",
        "",
        (),
    )
    [event] = outcome.events
    assert (event.guard, event.stage) == ("citations", "output")
    assert UNRETRIEVED in event.reason


def test_a_conflict_naming_an_unretrieved_id_is_blocked():
    def script(request: ChatRequest) -> str:
        first = request.messages[-1].content.split('<chunk id="', 1)[1].split('"', 1)[0]
        return reply("flag-conflict", "15.", cited=[first], conflict=[first, "X-OTHER@1/1/1"])

    pipeline, _ = small_pipeline(FakeChat(script))
    outcome = pipeline.ask("How many characters must passwords have?", "tenant-a")
    assert outcome.answer.status is Status.BLOCKED
    assert "X-OTHER@1/1/1" in outcome.events[0].reason


def test_an_answer_citing_only_retrieved_ids_passes():
    pipeline, _ = small_pipeline(FakeChat())
    outcome = pipeline.ask("How many characters must passwords have?", "tenant-a")
    assert outcome.answer.status is Status.OK
    assert outcome.answer.cited_ids
    assert set(outcome.answer.cited_ids) == {r.chunk.chunk_id for r in outcome.retrieved}


def test_cited_ids_are_a_subset_of_retrieved_on_every_answer():
    """Over every small question as each tenant, with a model that cites a random mix of the
    pack's ids (retrieved or not): every answer that gets through cites retrieved ids only, and
    every answer that cites another id is blocked."""
    rng = random.Random(20261018)  # noqa: S311  # a seeded sample, not a secret
    all_ids = [c.chunk_id for c in PACK] + ["Z-NONE@1/1/1"]
    ok = blocked = 0
    for question in QUESTIONS:
        for tenant in ("tenant-a", "tenant-b"):
            for _ in range(10):
                cited = rng.sample(all_ids, rng.randint(1, 3))
                pipeline, _ = small_pipeline(FakeChat([reply("answer", "x", cited=cited)]))
                outcome = pipeline.ask(str(question["question"]), tenant)
                retrieved = {r.chunk.chunk_id for r in outcome.retrieved}
                if set(cited) <= retrieved:
                    assert outcome.answer.status is Status.OK
                    ok += 1
                else:
                    assert outcome.answer.status is Status.BLOCKED
                    blocked += 1
                assert set(outcome.answer.cited_ids) <= retrieved
    assert ok > 0  # both paths ran
    assert blocked > 0


def test_without_the_validator_an_unretrieved_citation_would_get_through():
    """The control for the tests above: the same scripted model with every guard but the
    citation validator answers with the unretrieved citation."""
    chat = FakeChat([reply("answer", "16 characters.", cited=[UNRETRIEVED])])
    pipeline, _ = small_pipeline(chat, guards=[TenantGuard(), InputLimits()])
    outcome = pipeline.ask("How many characters must passwords have?", "tenant-a")
    assert outcome.answer.status is Status.OK
    assert outcome.answer.cited_ids == (UNRETRIEVED,)
    assert CitationValidator().check_output(outcome.answer, frozenset()) is not None


def test_the_record_counts_the_models_unretrieved_citations(tmp_path):
    """Judge S3-J1: the run's citation metric measures the model's reply. A FakeChat that cites a
    tenant B chunk for every question: every such trial is blocked, the blocked count says so,
    and model_citations_retrieved falls below 1.0 (it was 1.000 by construction before)."""
    from raglab.evals import record
    from tests.generation_support import fake_generation_run, generation_root
    from tests.retrieval_support import read_run

    root = generation_root(tmp_path)
    chat = FakeChat(lambda request: reply("answer", "16 characters.", cited=[UNRETRIEVED]))
    run_dir = fake_generation_run(root, chat)
    assert record.validate(run_dir, root) == []
    manifest, cases = read_run(run_dir)
    metric = manifest["results"]["metrics"]["model_citations_retrieved"]
    blocked = manifest["results"]["generation"]["status_counts"]["blocked"]
    assert blocked > 0
    assert metric["value"] < 1.0
    for case in cases:
        fired = any(e["guard"] == "citations" for e in case["guard_events"])
        assert case["checks"]["model_citations_retrieved"] is (not fired)
