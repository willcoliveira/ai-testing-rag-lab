"""S3 AC4, the fallback contract: a provider timeout, a connection error, an HTTP error status or
a reply outside the answer schema gives status unavailable or invalid_output, never answer text;
and the run record counts each status. The provider is the real OpenAI-compatible adapter talking
to an in-process stub of an Ollama server (httpx.MockTransport: no socket, no network)."""

import json

import httpx
import pytest

from raglab.adapters.fake import FakeChat
from raglab.adapters.openai_compat import OpenAICompatChat
from raglab.core.types import ChatTimeout, ChatUnavailable, Status
from raglab.evals import record
from tests.generation_support import (
    DIGEST,
    completion,
    fake_generation_run,
    generation_config_text,
    generation_root,
    reply,
    small_pipeline,
    stub_client,
    stub_ollama,
)
from tests.retrieval_support import read_run

pytestmark = [pytest.mark.unit, pytest.mark.contract]
QUESTION = "How many characters must passwords have?"


def adapter(handler) -> OpenAICompatChat:
    return OpenAICompatChat(
        "http://127.0.0.1:11434",
        "stub-model:1b",
        DIGEST,
        temperature=0.2,
        max_tokens=256,
        timeout_s=5,
        client=stub_client(stub_ollama(handler)),
    )


def raises(error: Exception):
    def handler(request: httpx.Request) -> httpx.Response:
        raise error

    return handler


def answers_with(response: httpx.Response):
    return lambda request: response


@pytest.mark.parametrize(
    ("handler", "status", "error"),
    [
        (raises(httpx.ReadTimeout("slow")), Status.UNAVAILABLE, "timeout after 5 s"),
        (raises(httpx.ConnectTimeout("slow")), Status.UNAVAILABLE, "timeout after 5 s"),
        (raises(httpx.ConnectError("refused")), Status.UNAVAILABLE, "connection error"),
        (raises(httpx.RemoteProtocolError("cut")), Status.UNAVAILABLE, "connection error"),
        (answers_with(httpx.Response(500)), Status.UNAVAILABLE, "HTTP 500"),
        (answers_with(httpx.Response(503)), Status.UNAVAILABLE, "HTTP 503"),
        (answers_with(httpx.Response(404)), Status.UNAVAILABLE, "HTTP 404"),
        (
            answers_with(httpx.Response(200, text="<html>busy</html>")),
            Status.INVALID_OUTPUT,
            "not JSON",
        ),
        (
            answers_with(httpx.Response(200, json={"choices": []})),
            Status.INVALID_OUTPUT,
            "not JSON",
        ),
        (answers_with(completion("The answer is 15.")), Status.INVALID_OUTPUT, "not JSON"),
        (
            answers_with(completion("```json\n" + reply() + "\n```")),
            Status.INVALID_OUTPUT,
            "not JSON",
        ),
        (answers_with(completion(reply(label="maybe"))), Status.INVALID_OUTPUT, "label 'maybe'"),
        (answers_with(completion(reply(answer=""))), Status.INVALID_OUTPUT, "answer is not"),
        (
            answers_with(completion(json.dumps({"label": "answer", "answer": "15"}))),
            Status.INVALID_OUTPUT,
            "fields",
        ),
        (answers_with(completion(reply())), Status.OK, None),
    ],
)
def test_a_provider_failure_never_gives_answer_text(handler, status, error):
    pipeline, _ = small_pipeline(adapter(handler))
    outcome = pipeline.ask(QUESTION, "tenant-a")
    assert outcome.answer.status is status
    if status is Status.OK:
        return
    assert (outcome.answer.text, outcome.answer.cited_ids, outcome.answer.label) == (
        "",
        (),
        "abstain",
    )
    assert outcome.error is not None
    assert error in outcome.error
    assert outcome.timed_out == ("timeout" in error)


def test_the_adapter_raises_typed_errors():
    with pytest.raises(ChatTimeout):
        adapter(raises(httpx.ReadTimeout("slow"))).complete(_request())
    with pytest.raises(ChatUnavailable):
        adapter(answers_with(httpx.Response(502))).complete(_request())


def _request():
    from raglab.core.types import ChatMessage, ChatRequest

    return ChatRequest((ChatMessage("user", "q"),), "s", {}, 1)


def test_the_run_record_counts_every_status(tmp_path):
    """A generation run whose model fails in different ways: each case-trial is recorded with its
    status and no answer text, and status_counts holds the counts."""
    root = generation_root(tmp_path)
    script = [
        ChatUnavailable("HTTP 503 from /v1/chat/completions"),
        "not json",
        reply("maybe"),
    ]
    chat = FakeChat(script * 10)
    run_dir = fake_generation_run(root, chat, generation_config_text(trials=1))
    assert record.validate(run_dir, root) == []
    manifest, cases = read_run(run_dir)
    counts = manifest["results"]["generation"]["status_counts"]
    assert counts == {"ok": 0, "refused": 0, "blocked": 0, "unavailable": 2, "invalid_output": 3}
    for case in cases:
        assert case["answer"] == ""
        assert case["label"] == "abstain"
        assert case["error"]
    assert manifest["partial"] is False  # an HTTP error is not a timeout


def test_a_timeout_marks_the_run_partial(tmp_path):
    root = generation_root(tmp_path)
    chat = FakeChat([ChatTimeout("timeout after 5 s")] * 10)
    run_dir = fake_generation_run(root, chat, generation_config_text(trials=1))
    assert record.validate(run_dir, root) == []
    manifest, _ = read_run(run_dir)
    assert manifest["partial"] is True
    assert "timed out" in manifest["totals"]["stopped"]


def test_the_wall_clock_cap_stops_the_run_and_marks_it_partial(tmp_path):
    """A clock that moves 100 s per reading: with a cap of 250 s the run stops after its second
    case-trial and says why."""
    root = generation_root(tmp_path)
    ticks = iter(range(0, 10_000, 100))
    run_dir = fake_generation_run(
        root, config_text=generation_config_text(trials=2, cap=250), monotonic=lambda: next(ticks)
    )
    assert record.validate(run_dir, root) == []
    manifest, cases = read_run(run_dir)
    assert manifest["partial"] is True
    assert manifest["totals"]["stopped"] == "the run hit its wall-clock cap of 250 s"
    assert [(c["case_id"], c["trial"]) for c in cases] == [("Q1", 1), ("Q1", 2)]
