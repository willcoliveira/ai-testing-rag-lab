"""Traced apps for the S9 tests: the small pack (tests/retrieval_support) behind the hashing
embedder wrapped by the traced embedder, a pipeline that writes to an OpenTelemetry tracer, and the
app built with the same provider, whose spans leave through raglab.obs.otel's allowlist into an
in-memory exporter. Each app has its own provider: none is ever set as the global one, so nothing
leaks between tests and an untraced run builds none (raglab.obs.otel)."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from fastapi.testclient import TestClient
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from raglab.adapters.fake import FakeChat, HashingEmbedder
from raglab.api.app import VersionInfo, create_app
from raglab.core.ports import ChatModel, Guardrail, Retriever
from raglab.core.types import Chunk
from raglab.generate.pipeline import PROMPT_VERSION, Pipeline
from raglab.guard import default_guards
from raglab.index.memory import InMemoryStore
from raglab.obs import otel
from raglab.obs.traced import TracedEmbedder
from raglab.retrieve.dense import DenseRetriever, index_chunks
from tests.generation_support import TOKENS
from tests.retrieval_support import PACK

INFO = VersionInfo("0.0.1", "0" * 40, PROMPT_VERSION, "fake", "fake-echo", "fake", "fake")
DEMO = {"Authorization": "Bearer demo"}
LOCAL = {"RAGLAB_ENV": "local", "RAGLAB_TRACE_CONTENT": "1"}  # D4's opt-in, where it is honoured


@dataclass
class Traced:
    """A traced app: `exporter` receives what leaves the process (after the allowlist), `raw` what
    the code recorded before it (a second processor, for the tests that check the source too)."""

    client: TestClient
    exporter: InMemorySpanExporter
    raw: InMemorySpanExporter
    chat: ChatModel

    def spans(self) -> list[ReadableSpan]:
        return list(self.exporter.get_finished_spans())

    def raw_spans(self, scope: str = "raglab") -> list[ReadableSpan]:
        return [
            span
            for span in self.raw.get_finished_spans()
            if span.instrumentation_scope is not None and span.instrumentation_scope.name == scope
        ]

    def by_name(self) -> dict[str, ReadableSpan]:
        spans = self.spans()
        named = {span.name: span for span in spans}
        assert len(named) == len(spans), [s.name for s in spans]
        return named


def traced_retriever(tracer: otel.OtelTracer, chunks: Sequence[Chunk] = PACK) -> DenseRetriever:
    embedder = TracedEmbedder(HashingEmbedder(), tracer, "fake")
    store = InMemoryStore(embedder.dimension)
    index_chunks(embedder, store, list(chunks))
    return DenseRetriever(embedder, store)


def traced_app(
    chat: ChatModel | None = None,
    *,
    chunks: Sequence[Chunk] = PACK,
    retriever: Retriever | None = None,
    guards: Sequence[Guardrail] | None = None,
    capture_content: bool = False,
    environ: Mapping[str, str] | None = None,
    info: VersionInfo = INFO,
    tokens: Mapping[str, frozenset[str]] = TOKENS,
) -> Traced:
    exporter, raw = InMemorySpanExporter(), InMemorySpanExporter()
    provider = otel.provider_with(exporter, capture_content, batch=False)
    provider.add_span_processor(SimpleSpanProcessor(raw))
    tracer = otel.OtelTracer(provider, capture_content)
    model = chat or FakeChat()
    pipeline = Pipeline(
        retriever or traced_retriever(tracer, chunks),
        model,
        default_guards() if guards is None else guards,
        3,
        tracer=tracer,
    )
    environment = (LOCAL if capture_content else {}) if environ is None else environ
    app = create_app(pipeline, info, tokens, tracer_provider=provider, environ=environment)
    return Traced(TestClient(app, raise_server_exceptions=False), exporter, raw, model)


def every_value(span: ReadableSpan) -> list[tuple[str, str]]:
    """Everything the span would export, as (where, text): its name, each attribute, the status
    description, each event and its attributes, each link's attributes, the resource and the
    scope."""
    out = [("name", span.name), ("status", str(span.status.description or ""))]
    out += [(f"attribute {k}", f"{k}={v}") for k, v in (span.attributes or {}).items()]
    for event in span.events:
        out.append((f"event {event.name}", event.name))
        out += [
            (f"event {event.name} {k}", f"{k}={v}") for k, v in (event.attributes or {}).items()
        ]
    for link in span.links:
        out += [(f"link {k}", f"{k}={v}") for k, v in (link.attributes or {}).items()]
    out += [(f"resource {k}", f"{k}={v}") for k, v in span.resource.attributes.items()]
    scope: Any = span.instrumentation_scope
    if scope is not None:
        out.append(("scope", f"{scope.name} {scope.version}"))
    return out


def leaks(spans: Sequence[ReadableSpan], markers: Sequence[str]) -> list[str]:
    """Each place a marker appears, as 'span name, where: marker' (empty when none does)."""
    return [
        f"{span.name}, {where}: {marker}"
        for span in spans
        for where, text in every_value(span)
        for marker in markers
        if marker in text
    ]
