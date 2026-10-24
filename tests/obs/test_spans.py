"""S9 OB3 (and OB2's no-provider half): one /ask makes one trace, FastAPI's request span as its
root, raglab's pipeline span under it, and the retrieval, embeddings and chat spans, each named
and attributed as the GenAI conventions say at the pinned commit (raglab.obs.names). Tokens are
recorded only as the server reported them; error.type is a fixed value. Through the API in process
(TestClient), with FakeChat and with the local adapter against its in-process stub server; spans
leave through the allowlist into an in-memory exporter."""

import json
from types import SimpleNamespace

import httpx
import pytest
from opentelemetry.sdk import trace as sdk_trace
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import SpanKind, StatusCode

from raglab.adapters import factory
from raglab.adapters.fake import FakeChat
from raglab.api import server
from raglab.core.ports import NoopTracer
from raglab.core.types import ChatTimeout, ChatUnavailable
from raglab.generate.assemble import Assembled
from raglab.generate.pipeline import PROMPT_VERSION
from raglab.ingest.pipeline import Inventory
from raglab.obs import names, otel
from tests.conftest import ROOT
from tests.generation_support import (
    DIGEST,
    completion,
    echo_server,
    fake_generation_run,
    generation_root,
    small_assembled,
    small_pipeline,
    stub_client,
    stub_ollama,
)
from tests.obs_support import DEMO, traced_app

pytestmark = pytest.mark.unit
QUESTION = "How many characters must passwords have?"
ASK = {"tenant": "tenant-a", "question": QUESTION}
EXPECTED = {
    "POST /ask",
    names.PIPELINE_SPAN,
    "retrieval policy-pack",
    "embeddings hashing-256",
    "chat fake-echo",
}


def local_chat(handler):
    model, _, _ = factory.chat(
        "openai-compat",
        "stub-model:1b",
        digest=DIGEST,
        base_url="http://127.0.0.1:11434",
        temperature=1.0,
        top_p=0.95,
        max_tokens=256,
        timeout_s=5,
        extra={"reasoning_effort": "none"},
        client=stub_client(stub_ollama(handler)),
    )
    return model


def test_one_ask_is_one_trace_with_the_request_span_as_its_root():
    traced = traced_app()
    assert traced.client.post("/ask", json=ASK, headers=DEMO).status_code == 200
    spans = traced.by_name()
    assert set(spans) == EXPECTED
    contexts = {name: span.get_span_context() for name, span in spans.items()}
    assert all(context is not None for context in contexts.values())
    assert len({context.trace_id for context in contexts.values() if context}) == 1
    root = spans["POST /ask"]
    assert root.parent is None
    assert root.kind is SpanKind.SERVER
    parent = {name: span.parent.span_id for name, span in spans.items() if span.parent}
    ids = {name: context.span_id for name, context in contexts.items() if context}
    assert parent[names.PIPELINE_SPAN] == ids["POST /ask"]
    assert parent["retrieval policy-pack"] == ids[names.PIPELINE_SPAN]
    assert parent["embeddings hashing-256"] == ids["retrieval policy-pack"]
    assert parent["chat fake-echo"] == ids[names.PIPELINE_SPAN]


def test_the_request_span_keeps_method_route_and_status_only():
    traced = traced_app()
    traced.client.post("/ask?q=a-query", json=ASK, headers={**DEMO, "User-Agent": "an-agent"})
    root = traced.by_name()["POST /ask"]
    assert dict(root.attributes or {}) == {
        "http.request.method": "POST",
        "http.route": "/ask",
        "http.response.status_code": 200,
    }


def test_health_checks_and_the_page_make_no_span():
    traced = traced_app()
    for path in ("/healthz", "/version", "/", "/app.js", "/nowhere"):
        traced.client.get(path)
    assert traced.spans() == []


def test_the_spans_are_named_and_attributed_by_the_pinned_spec():
    traced = traced_app()
    traced.client.post("/ask", json=ASK, headers=DEMO)
    spans = traced.by_name()
    pipeline = dict(spans[names.PIPELINE_SPAN].attributes or {})
    assert spans[names.PIPELINE_SPAN].kind is SpanKind.INTERNAL
    assert pipeline[names.PROMPT_VERSION] == PROMPT_VERSION
    assert (pipeline[names.STATUS], pipeline[names.LABEL]) == ("ok", "answer")
    assert pipeline[names.TENANT] == "tenant-a"
    assert pipeline[names.CITED_IDS] == pipeline[names.RETRIEVED_IDS]
    retrieval = spans["retrieval policy-pack"]
    assert retrieval.kind is SpanKind.CLIENT
    assert dict(retrieval.attributes or {}) == {
        "gen_ai.operation.name": "retrieval",
        "gen_ai.data_source.id": "policy-pack",
        "gen_ai.retrieval.top_k": 3,
        "raglab.retrieved.count": 3,
    }
    embeddings = spans["embeddings hashing-256"]
    assert embeddings.kind is SpanKind.CLIENT
    assert dict(embeddings.attributes or {}) == {
        "gen_ai.operation.name": "embeddings",
        "gen_ai.provider.name": "fake",
        "gen_ai.request.model": "hashing-256",
        "gen_ai.embeddings.dimension.count": 256,
        "raglab.embedder.revision": "fake",
    }
    chat = spans["chat fake-echo"]
    assert chat.kind is SpanKind.CLIENT
    assert dict(chat.attributes or {}) == {
        "gen_ai.operation.name": "chat",
        "gen_ai.provider.name": "fake",
        "gen_ai.request.model": "fake-echo",
        "gen_ai.request.seed": 0,
        "gen_ai.prompt.name": PROMPT_VERSION,
        "raglab.model.digest": "fake",
    }  # FakeChat reports no tokens: no usage key at all, never a 0


def test_the_local_adapters_span_has_its_settings_and_the_tokens_the_server_reported():
    traced = traced_app(local_chat(echo_server))  # the stub reports usage 100 and 20
    traced.client.post("/ask", json=ASK, headers=DEMO)
    chat = dict(traced.by_name()["chat stub-model:1b"].attributes or {})
    assert chat == {
        "gen_ai.operation.name": "chat",
        "gen_ai.provider.name": "openai-compat",
        "gen_ai.request.model": "stub-model:1b",
        "gen_ai.request.seed": 0,
        "gen_ai.prompt.name": PROMPT_VERSION,
        "gen_ai.request.temperature": 1.0,
        "gen_ai.request.top_p": 0.95,
        "gen_ai.request.max_tokens": 256,
        "gen_ai.request.reasoning.level": "none",
        "gen_ai.output.type": "json",
        "gen_ai.usage.input_tokens": 100,
        "gen_ai.usage.output_tokens": 20,
        "server.address": "127.0.0.1",
        "server.port": 11434,
        "raglab.model.digest": DIGEST,
    }


def test_tokens_the_server_did_not_report_stay_unreported():
    def no_usage(request: httpx.Request) -> httpx.Response:
        body = json.loads(echo_server(request).content)
        body.pop("usage")
        return httpx.Response(200, json=body)

    traced = traced_app(local_chat(no_usage))
    assert traced.client.post("/ask", json=ASK, headers=DEMO).json()["status"] == "ok"
    chat = dict(traced.by_name()["chat stub-model:1b"].attributes or {})
    assert names.USAGE_INPUT_TOKENS not in chat
    assert names.USAGE_OUTPUT_TOKENS not in chat


def test_only_the_count_the_server_reported_is_recorded():
    def prompt_only(request: httpx.Request) -> httpx.Response:
        body = json.loads(completion("x", 7, 0).content)
        body["usage"] = {"prompt_tokens": 7}
        body["choices"] = json.loads(echo_server(request).content)["choices"]
        return httpx.Response(200, json=body)

    traced = traced_app(local_chat(prompt_only))
    traced.client.post("/ask", json=ASK, headers=DEMO)
    chat = dict(traced.by_name()["chat stub-model:1b"].attributes or {})
    assert chat[names.USAGE_INPUT_TOKENS] == 7
    assert names.USAGE_OUTPUT_TOKENS not in chat


@pytest.mark.parametrize(
    ("script", "error_type", "code"),
    [
        ([ChatUnavailable("HTTP 503 from the server")], "unavailable", 503),
        ([ChatTimeout("timeout after 5 s")], "timeout", 503),
        (["not json"], "invalid_output", 502),
    ],
    ids=["unavailable", "timeout", "invalid_output"],
)
def test_a_failed_call_has_a_fixed_error_type(script, error_type, code):
    traced = traced_app(FakeChat(script))
    assert traced.client.post("/ask", json=ASK, headers=DEMO).status_code == code
    spans = traced.by_name()
    for name in ("chat fake-echo", names.PIPELINE_SPAN):
        span = spans[name]
        assert (span.attributes or {})[names.ERROR_TYPE] == error_type, name
        assert span.status.status_code is StatusCode.ERROR
        assert span.status.description is None
    assert error_type in names.ERROR_TYPES


def test_a_timeout_from_the_local_adapter_is_error_type_timeout():
    def slow(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("no reply", request=request)

    traced = traced_app(local_chat(slow))
    assert traced.client.post("/ask", json=ASK, headers=DEMO).status_code == 503
    chat = dict(traced.by_name()["chat stub-model:1b"].attributes or {})
    assert chat[names.ERROR_TYPE] == "timeout"


def test_an_error_type_outside_the_fixed_list_is_refused():
    tracer = otel.OtelTracer(otel.provider_with(InMemorySpanExporter(), batch=False))
    with tracer.span("x") as span, pytest.raises(ValueError, match="not one of"):
        span.fail("RuntimeError: a message")


def test_an_eval_run_builds_no_provider_and_makes_no_span(tmp_path, monkeypatch):
    """OB2: only `raglab serve` builds a tracer provider; a generation run with the fake model uses
    the no-op tracer and never constructs one."""
    built: list[object] = []
    original = sdk_trace.TracerProvider.__init__

    def spy(self, *args, **kwargs):
        built.append(self)
        original(self, *args, **kwargs)

    monkeypatch.setattr(sdk_trace.TracerProvider, "__init__", spy)
    root = generation_root(tmp_path)
    _, assembled = small_assembled(root)
    assert isinstance(assembled.pipeline.tracer, NoopTracer)
    fake_generation_run(root)
    assert built == []


def test_serve_builds_a_provider_only_with_an_endpoint(monkeypatch):
    """OB2: `raglab serve` asks for tracing only when RAGLAB_OTLP_ENDPOINT is set, and gives the
    pipeline and the app what it built."""
    asked: list[tuple[str, bool]] = []
    tracing = SimpleNamespace(tracer=NoopTracer(), provider=None, shutdown=lambda: None)
    given: list[object] = []

    def tiny_assemble(config, root, tracer=None):
        given.append(tracer)
        pipeline, _ = small_pipeline()
        chat: dict[str, object] = {"provider": "fake", "model": "fake-echo", "digest": "fake"}
        return Assembled(pipeline, Inventory(config.chunker, {}, (), ()), {}, chat, "fake")

    def for_endpoint(url: str, capture: bool):
        asked.append((url, capture))
        return tracing

    monkeypatch.setattr(server.assemble, "assemble", tiny_assemble)
    monkeypatch.setattr(server.otel, "for_endpoint", for_endpoint)
    config = ROOT / "config" / "fake.toml"
    server.build_app(config, ROOT, environ={})
    assert (asked, given) == ([], [None])
    server.build_app(config, ROOT, environ={"RAGLAB_OTLP_ENDPOINT": "http://127.0.0.1:4391"})
    assert asked == [("http://127.0.0.1:4391", False)]
    assert given[-1] is tracing.tracer


@pytest.mark.parametrize(
    "value",
    [
        "http://192.0.2.1:4318",
        "https://127.0.0.1:4318",
        "http://127.0.0.1",
        "http://127.0.0.1:4318/v1/traces",
        "http://user:pw@127.0.0.1:4318",
        "http://collector.example.com:4318",
        "127.0.0.1:4318",
        "http://localhost:4318",  # a name, resolved by the machine (S9-J6): refused
    ],
)
def test_the_endpoint_is_a_loopback_collector_only(value):
    with pytest.raises(otel.TracingError, match="loopback"):
        otel.endpoint({"RAGLAB_OTLP_ENDPOINT": value})


def test_an_unset_endpoint_is_tracing_off_and_a_loopback_one_is_kept():
    assert otel.endpoint({}) is None
    assert otel.endpoint({"RAGLAB_OTLP_ENDPOINT": ""}) is None
    assert otel.endpoint({"RAGLAB_OTLP_ENDPOINT": "http://127.0.0.1:4391/"}) == (
        "http://127.0.0.1:4391"
    )
    assert otel.endpoint({"RAGLAB_OTLP_ENDPOINT": "http://127.0.0.2:4391"}) == (
        "http://127.0.0.2:4391"
    )
    assert otel.endpoint({"RAGLAB_OTLP_ENDPOINT": "http://[::1]:4391"}) == "http://[::1]:4391"
