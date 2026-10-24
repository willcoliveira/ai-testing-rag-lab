"""The OpenTelemetry side of tracing (S9): the Tracer port over the SDK, the allowlist every span
passes on its way out, and the provider `raglab serve` builds.

- **Off unless configured.** Only `raglab serve` builds a provider, and only when
  RAGLAB_OTLP_ENDPOINT names a collector on the loopback interface (S9; S10 widens it with an
  allowlist). The endpoint is passed to the exporter explicitly: OTEL_EXPORTER_OTLP_ENDPOINT never
  decides where spans go, and FastAPI's own auto-configuration is switched off in code
  (raglab.api.app).
- **One filter on the way out** (the main plan's "redaction span processor"): AllowlistExporter
  wraps the exporter, so a span leaves with only the reviewed keys of raglab.obs.names, no events
  (an exception's message and stack never leave), no links, a status without its description, and
  a resource of the service's name and version only. The content keys leave only while the
  opt-in is on (D4); otherwise they are dropped twice, when set and when exported.
- **No exception is recorded**: spans are started with record_exception and
  set_status_on_exception off; a failure is marked with a fixed error.type (Span.fail).

The provider is handed to raglab.api as an opaque object, so the web layer never imports
opentelemetry (scripts/check_architecture.py, rule 7).
"""

import ipaddress
from collections.abc import Generator, Mapping, Sequence
from contextlib import contextmanager
from urllib.parse import urlsplit

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SimpleSpanProcessor,
    SpanExporter,
    SpanExportResult,
)
from opentelemetry.trace import Status, StatusCode

from raglab import __version__
from raglab.core.ports import AttributeValue, Span, SpanKind
from raglab.obs import names

ENDPOINT_ENV = "RAGLAB_OTLP_ENDPOINT"
SERVICE = "raglab"
KINDS = {"internal": trace.SpanKind.INTERNAL, "client": trace.SpanKind.CLIENT}
EXPORT_TIMEOUT_S = 5.0


class TracingError(ValueError):
    """Tracing refuses to start: the endpoint is not a loopback collector."""


def _loopback(host: str | None) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host or "").is_loopback
    except ValueError:
        return False


def endpoint(environ: Mapping[str, str]) -> str | None:
    """The collector's OTLP/HTTP base URL from RAGLAB_OTLP_ENDPOINT (http://127.0.0.1:<port>), or
    None when it is unset or empty (tracing off). Anything but plain http to a loopback host and
    port, with no path, query, fragment or credentials, is refused."""
    raw = environ.get(ENDPOINT_ENV, "")
    if not raw:
        return None
    parts = urlsplit(raw)
    try:
        port = parts.port
    except ValueError:
        port = None
    if (
        parts.scheme != "http"
        or not _loopback(parts.hostname)
        or port is None
        or parts.path not in ("", "/")
        or parts.query
        or parts.fragment
        or parts.username is not None
        or parts.password is not None
    ):
        raise TracingError(
            f"{ENDPOINT_ENV}={raw!r}: in S9 traces go only to a collector on the loopback "
            "interface, as http://127.0.0.1:<port>"
        )
    return f"http://{parts.hostname}:{port}"


def redact(span: ReadableSpan, allowed: frozenset[str]) -> ReadableSpan:
    """The span as it may leave the process: only allowed attribute keys, no events, no links, a
    status code without its description, and the resource's allowed keys only."""
    resource = Resource(
        {k: v for k, v in span.resource.attributes.items() if k in names.RESOURCE_KEYS}
    )
    return ReadableSpan(
        name=span.name,
        context=span.context,
        parent=span.parent,
        resource=resource,
        attributes={k: v for k, v in (span.attributes or {}).items() if k in allowed},
        events=(),
        links=(),
        kind=span.kind,
        status=Status(span.status.status_code),
        start_time=span.start_time,
        end_time=span.end_time,
        instrumentation_scope=span.instrumentation_scope,
    )


class AllowlistExporter(SpanExporter):
    """Exports every span through redact(), with the keys its scope may keep: raglab's spans the
    keys of names.SPAN_KEYS (and the content keys only when capture_content is on), FastAPI's
    request span names.HTTP_KEYS, any other scope none."""

    def __init__(self, inner: SpanExporter, capture_content: bool = False) -> None:
        self.inner = inner
        self.by_scope = {
            names.RAGLAB_SCOPE: names.SPAN_KEYS
            | (frozenset(names.CONTENT_KEYS) if capture_content else frozenset[str]()),
            names.FASTAPI_SCOPE: names.HTTP_KEYS,
        }

    def allowed(self, span: ReadableSpan) -> frozenset[str]:
        scope = span.instrumentation_scope
        return self.by_scope.get("" if scope is None else scope.name, frozenset[str]())

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        return self.inner.export([redact(span, self.allowed(span)) for span in spans])

    def shutdown(self) -> None:
        self.inner.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return self.inner.force_flush(timeout_millis)


class _OtelSpan:
    def __init__(self, span: trace.Span, capture_content: bool) -> None:
        self._span = span
        self._capture = capture_content

    def set(self, key: str, value: AttributeValue) -> None:
        if key in names.CONTENT_KEYS and not self._capture:
            return
        self._span.set_attribute(key, value)

    def fail(self, error_type: str) -> None:
        if error_type not in names.ERROR_TYPES:
            raise ValueError(f"error type {error_type!r} is not one of {names.ERROR_TYPES}")
        self._span.set_attribute(names.ERROR_TYPE, error_type)
        self._span.set_status(Status(StatusCode.ERROR))


class OtelTracer:
    """The Tracer port over an SDK provider."""

    def __init__(self, provider: TracerProvider, capture_content: bool = False) -> None:
        self._tracer = provider.get_tracer(SERVICE, __version__)
        self._capture = capture_content

    @property
    def capture_content(self) -> bool:
        return self._capture

    @contextmanager
    def span(self, name: str, kind: SpanKind = "internal") -> Generator[Span]:
        with self._tracer.start_as_current_span(
            name, kind=KINDS[kind], record_exception=False, set_status_on_exception=False
        ) as span:
            yield _OtelSpan(span, self._capture)


def provider_with(
    exporter: SpanExporter, capture_content: bool = False, *, batch: bool = True
) -> TracerProvider:
    """A provider whose spans leave through AllowlistExporter(exporter): batched for serving,
    synchronous (batch=False) for the tests' in-memory exporter. Its resource is built from the
    service's name and version alone, never merged with OTEL_RESOURCE_ATTRIBUTES."""
    provider = TracerProvider(
        resource=Resource({"service.name": SERVICE, "service.version": __version__})
    )
    allowed = AllowlistExporter(exporter, capture_content)
    provider.add_span_processor(
        BatchSpanProcessor(allowed) if batch else SimpleSpanProcessor(allowed)
    )
    return provider


class Tracing:
    """What `raglab serve` builds when an endpoint is set: the provider FastAPI's request span uses
    (opaque to raglab.api), the Tracer the pipeline writes to, and the shutdown that flushes the
    batch on a graceful stop."""

    def __init__(self, provider: TracerProvider, capture_content: bool) -> None:
        self._provider = provider
        self.tracer = OtelTracer(provider, capture_content)

    @property
    def provider(self) -> object:
        return self._provider

    def shutdown(self) -> None:
        self._provider.shutdown()


def for_endpoint(base_url: str, capture_content: bool) -> Tracing:
    """Tracing to the collector at base_url (endpoint()'s value), over OTLP/HTTP."""
    exporter = OTLPSpanExporter(endpoint=f"{base_url}/v1/traces", timeout=EXPORT_TIMEOUT_S)
    return Tracing(provider_with(exporter, capture_content), capture_content)
