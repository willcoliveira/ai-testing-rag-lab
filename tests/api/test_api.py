"""S3 AC6 and AC10 through the API (TEST-PLAN R1, R-21): /healthz, /version and /ask; a request
without a token is 401; one without a tenant the caller's token may use is 403 and never reaches
the retriever; a question over the input limits is 400; the model's failures are 502 and 503;
every response carries the security headers. The app runs in process (TestClient, no socket),
over the small pack with the fake embedder, a spy retriever and FakeChat."""

import pytest
from fastapi.testclient import TestClient

from raglab.adapters.fake import FakeChat
from raglab.api.app import CSP, MAX_BODY_BYTES, SECURITY_HEADERS, VersionInfo, create_app
from raglab.core.types import ChatUnavailable
from raglab.generate.pipeline import PROMPT_VERSION
from tests.generation_support import TOKENS, SpyRetriever, small_pipeline

pytestmark = [pytest.mark.unit, pytest.mark.security]
INFO = VersionInfo("0.0.1", "0" * 40, PROMPT_VERSION, "fake", "fake-echo", "fake", "fake")
DEMO = {"Authorization": "Bearer demo"}
A_ONLY = {"Authorization": "Bearer tenant-a-only"}
QUESTION = "How many characters must passwords have?"


def client(chat=None) -> tuple[TestClient, SpyRetriever]:
    pipeline, spy = small_pipeline(chat)
    return TestClient(create_app(pipeline, INFO, TOKENS)), spy


def test_healthz_and_version():
    api, _ = client()
    assert api.get("/healthz").json() == {"status": "ok"}
    assert api.get("/version").json() == {
        "raglab": "0.0.1",
        "git_sha": "0" * 40,
        "prompt_version": "answer-v2",
        "provider": "fake",
        "model": "fake-echo",
        "digest": "fake",
        "provenance": "fake",
    }


def test_an_answer_with_its_citations():
    api, spy = client()
    response = api.post("/ask", json={"tenant": "tenant-a", "question": QUESTION}, headers=DEMO)
    assert response.status_code == 200
    body = response.json()
    assert (body["status"], body["label"], body["prompt_version"]) == ("ok", "answer", "answer-v2")
    assert body["answer"]
    assert body["citations"]
    assert {"chunk_id", "document", "version", "section", "page"} == set(body["citations"][0])
    assert all(c["chunk_id"].startswith(("A-", "X-")) for c in body["citations"])
    assert spy.calls == 1


@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Bearer nope"}, {"Authorization": "demo"}, {"Authorization": "Bearer "}],
)
def test_no_known_token_is_401_before_anything_else(headers):
    api, spy = client()
    response = api.post("/ask", json={"tenant": "tenant-a", "question": QUESTION}, headers=headers)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert spy.calls == 0


@pytest.mark.parametrize(
    ("body", "headers"),
    [
        ({"question": QUESTION}, DEMO),
        ({"tenant": None, "question": QUESTION}, DEMO),
        ({"tenant": "", "question": QUESTION}, DEMO),
        ({"tenant": "shared", "question": QUESTION}, DEMO),
        ({"tenant": "tenant-c", "question": QUESTION}, DEMO),
        ({"tenant": ["tenant-a"], "question": QUESTION}, DEMO),
        ({"tenant": "tenant-b", "question": QUESTION}, A_ONLY),  # the spoof
    ],
    ids=["missing", "null", "empty", "shared", "unknown", "list", "spoofed"],
)
def test_a_tenant_the_caller_may_not_use_is_403_and_never_retrieved(body, headers):
    api, spy = client()
    response = api.post("/ask", json=body, headers=headers)
    assert response.status_code == 403
    reply = response.json()
    assert (reply["status"], reply["label"], reply["answer"], reply["citations"]) == (
        "refused",
        "abstain",
        "",
        [],
    )
    assert spy.calls == 0


def test_the_spoof_message_names_the_tenant():
    api, _ = client()
    response = api.post("/ask", json={"tenant": "tenant-b", "question": QUESTION}, headers=A_ONLY)
    from raglab.api.app import REASONS

    assert response.json()["reason"] == REASONS["tenant"]
    ok = api.post("/ask", json={"tenant": "tenant-a", "question": QUESTION}, headers=A_ONLY)
    assert ok.status_code == 200


@pytest.mark.parametrize(
    ("body", "code"),
    [
        ({"tenant": "tenant-a", "question": "x" * 501}, 400),
        ({"tenant": "tenant-a", "question": ""}, 400),
        ({"tenant": "tenant-a", "question": "password\x00"}, 400),
        ({"tenant": "tenant-a", "question": 15}, 400),
        ({"tenant": "tenant-a"}, 400),
        (["tenant-a", QUESTION], 400),
    ],
)
def test_a_question_over_the_input_limits_is_400_and_never_retrieved(body, code):
    api, spy = client()
    assert api.post("/ask", json=body, headers=DEMO).status_code == code
    assert spy.calls == 0


def test_a_body_that_is_not_json_or_too_large_is_refused():
    api, spy = client()
    bad = api.post("/ask", content=b"{not json", headers=DEMO)
    assert bad.status_code == 400
    big = api.post("/ask", content=b"x" * (MAX_BODY_BYTES + 1), headers=DEMO)
    assert big.status_code == 413
    assert spy.calls == 0


@pytest.mark.parametrize(
    ("script", "code", "status"),
    [
        ([ChatUnavailable("HTTP 503")], 503, "unavailable"),
        (["not json"], 502, "invalid_output"),
        (['{"label": "answer"}'], 502, "invalid_output"),
    ],
)
def test_a_model_failure_is_never_an_answer(script, code, status):
    api, _ = client(FakeChat(script))
    response = api.post("/ask", json={"tenant": "tenant-a", "question": QUESTION}, headers=DEMO)
    assert response.status_code == code
    body = response.json()
    assert (body["status"], body["answer"], body["citations"]) == (status, "", [])


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/"),
        ("GET", "/app.js"),
        ("GET", "/app.css"),
        ("GET", "/healthz"),
        ("GET", "/version"),
        ("POST", "/ask"),
        ("GET", "/nope"),
        ("GET", "/ask"),
        ("GET", "/docs"),
        ("GET", "/openapi.json"),
    ],
)
def test_every_response_carries_the_security_headers(method, path):
    api, _ = client()
    response = api.request(method, path, headers=DEMO, json={"tenant": "tenant-a", "question": "q"})
    for name, value in SECURITY_HEADERS.items():
        assert response.headers.get(name) == value, (path, name)
    assert "server" not in response.headers
    assert "'unsafe-inline'" not in CSP
    assert "frame-ancestors 'none'" in CSP
    assert "script-src 'self'" in CSP


def test_the_openapi_pages_are_off_and_other_methods_are_refused():
    api, _ = client()
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert api.get(path).status_code == 404
    assert api.get("/ask").status_code == 405
    assert api.delete("/healthz").status_code == 405


# ---------------------------------------------------------------- S3 fix round 1


def test_a_server_error_carries_the_security_headers():
    """Judge S3-S1: an exception that escapes the route is answered with every security header."""

    def boom(request):
        raise RuntimeError("an unexpected failure at /Users/someone/secret/path")

    pipeline, _ = small_pipeline(FakeChat(boom))
    api = TestClient(create_app(pipeline, INFO, TOKENS), raise_server_exceptions=False)
    response = api.post("/ask", json={"tenant": "tenant-a", "question": QUESTION}, headers=DEMO)
    assert response.status_code == 500
    for name, value in SECURITY_HEADERS.items():
        assert response.headers.get(name) == value, name
    assert "secret" not in response.text


@pytest.mark.parametrize(
    ("script", "code"),
    [
        ([ChatUnavailable("connection error (ConnectError: /Users/someone/secret/path)")], 503),
        (['{"label": "answer", "secret_field": "/Users/someone/secret/path"}'], 502),
    ],
)
def test_an_error_reason_comes_from_a_fixed_vocabulary(script, code):
    """Judge S3-S3: the reason a client sees is one of REASONS, never the adapter's or the
    parser's text (that stays in the server log and the run record's guard events)."""
    from raglab.api.app import REASONS

    api, _ = client(FakeChat(script))
    response = api.post("/ask", json={"tenant": "tenant-a", "question": QUESTION}, headers=DEMO)
    assert response.status_code == code
    assert response.json()["reason"] in REASONS.values()
    assert "secret" not in response.text
