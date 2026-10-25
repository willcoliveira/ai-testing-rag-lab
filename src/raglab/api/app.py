"""The API: /healthz, /version, /ask, and the page (/, /app.js, /app.css).

/ask takes `{"tenant": ..., "question": ...}` with `Authorization: Bearer <token>`. The token names
the tenants the caller may use (config [api] tokens; lab practice: production takes the tenant
from the identity provider's claims). The request goes through the pipeline's guards, which own
every refusal, and the status code says what happened:

| Outcome | Code |
|---|---|
| no token, or an unknown one | 401 |
| body over 4 KiB, not JSON, not an object, or a question that is not a string | 413 or 400 |
| refused by the tenant guard: no tenant, "shared", unknown, or one the caller may not use | 403 |
| refused by the input limits: empty, over 500 characters, control characters | 400 |
| refused by the injection detector (S7): an instruction, a system message, a prompt request | 400 |
| answered (ok) or withheld by a guard after retrieval (blocked) | 200 |
| the model's reply is outside the answer schema (invalid_output) | 502 |
| the model gave no reply (unavailable) | 503 |

Every response carries the security headers: a CSP without inline script, frame-ancestors none,
nosniff, no referrer, and no caching. The middleware adds them to every response the app makes;
an exception that escapes a route is answered by a catch-all handler, outside the middleware, so
that handler sets them itself (judge S3-S1). The OpenAPI pages are off (they load script from a
CDN). One request runs at a time (a lock; lab scale).

A response's `reason` is one of REASONS, a fixed vocabulary: never the adapter's, the parser's or
a guard's own text (judge S3-S3). The key of a guard's decision comes from raglab.core.reasons,
the rule the trace uses too (S9): a refused request answers with its guard's input key, and a
withheld answer with "blocked" whichever guard withheld it; a drop step's decision (S7, the
register filter) is keyed "dropped" and the answer goes on. The server log (logger `raglab.api`)
records a guard's decision as the guard's name, its stage and that key, never the guard's own text
(S7; the drop steps' events too); the adapter's or the parser's error text goes to the log, and, in
a run, to the record's error field.

S9: FastAPI's own telemetry is set explicitly (docs/OBSERVABILITY.md). With a tracer provider
(`raglab serve` with an OTLP endpoint) its request span for POST /ask is the root of the trace and
every other path is left out; operation spans, OpenTelemetry logs (exception messages and stack
traces) and metrics are off; auto-configuration is off in code, so FASTAPI_OTEL_AUTO_CONFIGURE in
the environment cannot add an exporter. Without a provider, tracing is off too. create_app refuses
an environment that may not serve this model (raglab.api.environment).
"""

import hmac
import json
import logging
import os
import threading
from collections.abc import AsyncGenerator, Callable, Mapping, MutableMapping
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from starlette.concurrency import run_in_threadpool
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from raglab.api import environment
from raglab.core.reasons import drop_key, reason_key
from raglab.core.types import ScoredChunk, Status
from raglab.generate.pipeline import Outcome, Pipeline

WEB = Path(__file__).resolve().parent.parent / "web"
MAX_BODY_BYTES = 4096
CSP = (
    "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
    "img-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
)
SECURITY_HEADERS = {
    "content-security-policy": CSP,
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "no-referrer",
    "permissions-policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
    "cross-origin-opener-policy": "same-origin",
    "cross-origin-resource-policy": "same-origin",
    "cross-origin-embedder-policy": "require-corp",
    "cache-control": "no-store",
}
PAGES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/app.css": ("app.css", "text/css; charset=utf-8"),
}
LOG = logging.getLogger("raglab.api")
REASONS = {
    "unauthorized": "a known bearer token is required",
    "too_large": f"the request body is over {MAX_BODY_BYTES} bytes",
    "bad_body": "the body must be a JSON object with a string question",
    "tenant": "the request names no tenant the caller may use",
    "input": "the question is empty, over 500 characters, or holds control characters",
    "injection": "the question reads as an instruction to the assistant or asks for its prompt",
    "blocked": "a guard withheld the answer",
    "dropped": "passages from outside the register were left out and the answer went on",
    "unavailable": "the model is unavailable",
    "invalid_output": "the model's reply did not fit the answer schema",
    "error": "internal error",
}
STATUS_REASONS = {
    Status.BLOCKED: "blocked",
    Status.UNAVAILABLE: "unavailable",
    Status.INVALID_OUTPUT: "invalid_output",
}
CODES = {
    Status.OK: 200,
    Status.BLOCKED: 200,
    Status.INVALID_OUTPUT: 502,
    Status.UNAVAILABLE: 503,
}


@dataclass(frozen=True)
class VersionInfo:
    """What /version says: the code, the prompt and the model the answers come from."""

    raglab: str
    git_sha: str
    prompt_version: str
    provider: str
    model: str
    digest: str
    provenance: str


class SecurityHeaders:
    """Adds SECURITY_HEADERS to every HTTP response (an ASGI middleware, so error pages get them
    too)."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = [
                    (k, v)
                    for k, v in cast(list[tuple[bytes, bytes]], message.get("headers", []))
                    if k.decode("latin-1").lower() not in SECURITY_HEADERS
                ]
                headers += [(k.encode(), v.encode()) for k, v in SECURITY_HEADERS.items()]
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, with_headers)


def _caller(header: str | None, tokens: Mapping[str, frozenset[str]]) -> frozenset[str] | None:
    """The tenants of the bearer token, or None when there is no known token. Every token is
    compared in constant time."""
    if not header or not header.startswith("Bearer "):
        return None
    given = header.removeprefix("Bearer ").encode()
    found: frozenset[str] | None = None
    for token, tenants in tokens.items():
        if hmac.compare_digest(given, token.encode()):
            found = tenants
    return found


async def _body(request: Request) -> bytes | None:
    """The request body, or None when it is over MAX_BODY_BYTES (read no further)."""
    data = bytearray()
    async for chunk in request.stream():
        data += chunk
        if len(data) > MAX_BODY_BYTES:
            return None
    return bytes(data)


def _citation(result: ScoredChunk) -> dict[str, object]:
    chunk = result.chunk
    return {
        "chunk_id": chunk.chunk_id,
        "document": chunk.title,
        "version": chunk.version,
        "section": chunk.section_id,
        "page": chunk.page,
    }


def _reason(outcome: Outcome) -> str | None:
    """The fixed reason for a refused or withheld answer (None for an answer). Every guard event
    is logged as its guard, stage and key, never its text; an adapter's or a parser's error is
    logged as it came."""
    for event in outcome.dropped:
        LOG.info("ask %s: guard %s at %s", drop_key(event), event.guard, event.stage)
    refused = outcome.refused_by()
    key = (
        reason_key(outcome.events[0])
        if refused is not None
        else STATUS_REASONS.get(outcome.answer.status)
    )
    if key is None:
        return None
    if outcome.events:
        event = outcome.events[0]
        LOG.info("ask %s: guard %s at %s", reason_key(event), event.guard, event.stage)
    else:
        LOG.info("ask %s: %s", key, outcome.error)
    return REASONS[key]


def _payload(outcome: Outcome, prompt_version: str) -> dict[str, object]:
    answer = outcome.answer
    by_id: dict[str, ScoredChunk] = {r.chunk.chunk_id: r for r in outcome.retrieved}
    return {
        "status": answer.status.value,
        "label": answer.label,
        "answer": answer.text,
        "citations": [_citation(by_id[i]) for i in answer.cited_ids if i in by_id],
        "conflict": None
        if answer.conflict is None
        else {"chunk_ids": list(answer.conflict.chunk_ids), "note": answer.conflict.note},
        "reason": _reason(outcome),
        "prompt_version": prompt_version,
    }


def _refusal(code: int, status: str, reason: str) -> JSONResponse:
    headers = {"www-authenticate": "Bearer"} if code == 401 else None
    return JSONResponse(
        {"status": status, "reason": REASONS[reason]}, status_code=code, headers=headers
    )


async def _server_error(request: Request, error: Exception) -> JSONResponse:
    """The answer to an exception that escaped a route: a fixed body with every security header
    (this handler runs outside the middleware); the exception goes to the log."""
    LOG.error("unhandled error on %s %s: %r", request.method, request.url.path, error)
    return JSONResponse(
        {"status": "error", "reason": REASONS["error"]},
        status_code=500,
        headers=SECURITY_HEADERS,
    )


TRACED_PATH = "/ask"


def _not_traced(scope: MutableMapping[str, Any]) -> bool:
    """FastAPI's request spans cover POST /ask only; health checks and pages make none."""
    return scope.get("path") != TRACED_PATH


def telemetry(tracer_provider: object | None) -> dict[str, object]:
    """FastAPI's telemetry settings, each one explicit (FastAPI 0.144.0's `telemetry` dict)."""
    settings: dict[str, object] = {
        "tracing": tracer_provider is not None,
        "operation_spans": False,
        "logs": False,
        "metrics": False,
        "auto_configure": False,
        "exclude": _not_traced,
    }
    if tracer_provider is not None:
        settings["tracer_provider"] = tracer_provider
    return settings


def create_app(
    pipeline: Pipeline,
    info: VersionInfo,
    tokens: Mapping[str, frozenset[str]],
    seed: int = 0,
    *,
    tracer_provider: object | None = None,
    on_shutdown: Callable[[], None] | None = None,
    environ: Mapping[str, str] | None = None,
) -> FastAPI:
    """The app. tracer_provider (raglab.obs.otel.Tracing.provider, opaque here) turns FastAPI's
    request span on; on_shutdown runs when the server stops gracefully (it flushes the spans)."""
    environment.switches(os.environ if environ is None else environ, info.provider)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
        yield
        if on_shutdown is not None:
            on_shutdown()

    app = FastAPI(
        title="raglab",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
        telemetry=cast(Any, telemetry(tracer_provider)),
    )
    app.add_middleware(SecurityHeaders)
    app.add_exception_handler(Exception, _server_error)
    lock = threading.Lock()
    pages = {path: ((WEB / name).read_bytes(), kind) for path, (name, kind) in PAGES.items()}

    def ask_locked(question: str, tenant: str | None, caller: frozenset[str]) -> Outcome:
        with lock:
            return pipeline.ask(question, tenant, caller, seed)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:  # pyright: ignore[reportUnusedFunction]
        return {"status": "ok"}

    @app.get("/version")
    def version() -> dict[str, str]:  # pyright: ignore[reportUnusedFunction]
        return asdict(info)

    @app.get("/")
    @app.get("/app.js")
    @app.get("/app.css")
    def page(request: Request) -> Response:  # pyright: ignore[reportUnusedFunction]
        content, kind = pages[request.url.path]
        return Response(content, media_type=kind)

    @app.post("/ask")
    async def ask(request: Request) -> JSONResponse:  # pyright: ignore[reportUnusedFunction]
        caller = _caller(request.headers.get("authorization"), tokens)
        if caller is None:
            return _refusal(401, "unauthorized", "unauthorized")
        raw = await _body(request)
        if raw is None:
            return _refusal(413, "refused", "too_large")
        try:
            body: object = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return _refusal(400, "refused", "bad_body")
        if not isinstance(body, dict):
            return _refusal(400, "refused", "bad_body")
        fields = {str(k): v for k, v in cast(dict[object, object], body).items()}
        question, tenant = fields.get("question"), fields.get("tenant")
        if not isinstance(question, str):
            return _refusal(400, "refused", "bad_body")
        outcome = await run_in_threadpool(
            ask_locked, question, tenant if isinstance(tenant, str) else None, caller
        )
        refused = outcome.refused_by()
        if refused is not None:
            code = 403 if reason_key(outcome.events[0]) == "tenant" else 400
            return JSONResponse(_payload(outcome, info.prompt_version), status_code=code)
        code = CODES[outcome.answer.status]
        return JSONResponse(_payload(outcome, info.prompt_version), status_code=code)

    return app
