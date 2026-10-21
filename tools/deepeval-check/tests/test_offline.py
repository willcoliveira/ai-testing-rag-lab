"""S5 AC10 and AC11, offline (`make deepeval-test`, in this project's own environment; never in
`make test`). DeepEval's telemetry is off before it is imported; the socket guard lets nothing but
the loopback Ollama port through; the custom judge model, over raglab's OpenAI-compatible adapter
against an in-process stub server, returns an instance of the schema DeepEval asks for and records
every call's tokens; a whole FaithfulnessMetric runs in eval mode llm through it with no
connection attempted; and the direction report names the output that scored higher."""

import json
import os
import socket
import subprocess
import sys
from collections.abc import Callable
from typing import Any

import httpx
import pytest
from deepeval_check import guard

DIGEST = "a" * 64
MODEL = "stub-judge:1b"


def stub(reply: Callable[[dict[str, Any]], str], seen: list[dict[str, Any]]) -> httpx.Client:
    """An in-process stand-in for the judge's Ollama server: /api/tags lists the pinned model,
    /api/version answers, /v1/chat/completions answers with reply(body)."""

    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(
                200, json={"models": [{"name": MODEL, "model": MODEL, "digest": DIGEST}]}
            )
        if request.url.path == "/api/version":
            return httpx.Response(200, json={"version": "0.0.0-stub"})
        body = json.loads(request.content)
        seen.append(body)
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"role": "assistant", "content": reply(body)}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 20},
            },
        )

    return httpx.Client(base_url="http://127.0.0.1:11434", transport=httpx.MockTransport(handle))


def judge_llm(reply: Callable[[dict[str, Any]], str], seen: list[dict[str, Any]]):
    guard.opt_out()
    from deepeval_check.llm import RaglabJudgeLLM

    from raglab.adapters.openai_compat import OpenAICompatChat

    def chat(fmt: str) -> OpenAICompatChat:
        return OpenAICompatChat(
            "http://127.0.0.1:11434",
            MODEL,
            DIGEST,
            temperature=0.0,
            max_tokens=512,
            timeout_s=5,
            response_format=fmt,
            client=stub(reply, seen),
        )

    return RaglabJudgeLLM(chat("json_schema"), chat("none"), seed=11)


def minimal(schema: dict[str, Any], defs: dict[str, Any] | None = None) -> Any:
    """The smallest value a JSON schema accepts: an object with its required properties, an
    empty list, the first enum value, a short string."""
    defs = schema.get("$defs", defs or {})
    if "$ref" in schema:
        return minimal(defs[schema["$ref"].split("/")[-1]], defs)
    if "anyOf" in schema:
        return minimal(schema["anyOf"][0], defs)
    if "enum" in schema:
        return schema["enum"][0]
    kind = schema.get("type")
    if kind == "object":
        props = schema.get("properties", {})
        return {k: minimal(props[k], defs) for k in schema.get("required", [])}
    if kind == "array":
        return []
    return {"string": "yes", "number": 1.0, "integer": 1, "boolean": True, "null": None}.get(
        str(kind), "yes"
    )


def schema_reply(body: dict[str, Any]) -> str:
    """A reply that fits the schema the request asks for, or a short text without one."""
    response = body.get("response_format")
    if not response:
        return "A short reason."
    return json.dumps(minimal(response["json_schema"]["schema"]))


def test_telemetry_is_off_before_deepeval_is_imported():
    """The entry point sets DEEPEVAL_TELEMETRY_OPT_OUT=1 before its first DeepEval import: an
    import hook records the variable at the moment DeepEval is first imported."""
    script = (
        "import os, sys\n"
        "seen = []\n"
        "class Watch:\n"
        "    def find_spec(self, name, path=None, target=None):\n"
        "        if name == 'deepeval' and not seen:\n"
        "            seen.append(os.environ.get('DEEPEVAL_TELEMETRY_OPT_OUT'))\n"
        "        return None\n"
        "sys.meta_path.insert(0, Watch())\n"
        "from deepeval_check import __main__ as entry\n"
        "assert 'deepeval' not in sys.modules\n"
        "try:\n"
        "    entry.main(['--help'])\n"
        "except SystemExit:\n"
        "    pass\n"
        "print(seen)\n"
    )
    env = {k: v for k, v in os.environ.items() if k != guard.OPT_OUT}
    done = subprocess.run(
        [sys.executable, "-c", script], env=env, capture_output=True, text=True, check=False
    )
    assert done.returncode == 0, done.stderr[-2000:]
    assert done.stdout.strip().splitlines()[-1] == "['1']"


def test_the_guard_lets_nothing_but_the_loopback_ollama_port_through():
    with guard.SocketGuard() as sockets:
        with pytest.raises(OSError, match="blocked by the loopback-only socket guard"):
            socket.getaddrinfo("us.i.posthog.com", 443)
        with pytest.raises(OSError, match="blocked by the loopback-only socket guard"):
            socket.create_connection(("192.0.2.1", 443), timeout=1)
        raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        with pytest.raises(OSError, match="blocked"):
            raw.connect(("127.0.0.1", 8080))  # loopback, but not the Ollama port
        raw.close()
        assert socket.getaddrinfo("127.0.0.1", 11434)  # allowed: no attempt recorded
        assert sockets.attempts == [
            "lookup us.i.posthog.com:443",
            "lookup 192.0.2.1:443",
            "connect 127.0.0.1:8080",
        ]
    assert socket.getaddrinfo is not None  # restored
    assert "connect" not in vars(socket.socket) or socket.socket.connect.__name__ == "connect"


def test_the_custom_llm_returns_an_instance_of_the_schema_and_records_its_tokens():
    """AC10's custom-LLM API, offline: called with a schema, it returns that schema's instance; the
    request carries the schema as a JSON schema response format; a reply off the schema raises
    and is counted, never repaired."""
    from deepeval_check.checks import Probe, custom_llm_api
    from pydantic import ValidationError

    seen: list[dict[str, Any]] = []
    llm = judge_llm(lambda body: '{"verdict": "yes", "reason": "64 is more than 20."}', seen)
    assert custom_llm_api(llm) == {"returned": "Probe", "is_instance": True}
    [body] = seen
    assert body["response_format"]["json_schema"]["schema"] == Probe.model_json_schema()
    assert (body["temperature"], body["seed"]) == (0.0, 11)
    assert llm.tokens() == {
        "calls": 1,
        "prompt": 100,
        "completion": 20,
        "unreported": 0,
        "off_schema": 0,
    }
    off = judge_llm(lambda body: '{"verdict": "yes"}', [])
    with pytest.raises(ValidationError):
        off.generate("Is 64 greater than 20?", schema=Probe)
    assert off.tokens()["off_schema"] == 1
    plain = judge_llm(lambda body: "Plain text.", [])
    assert plain.generate("Say something.") == "Plain text."


def test_a_whole_faithfulness_metric_runs_in_mode_llm_through_the_judge_with_no_attempt():
    """Every DeepEval call goes through raglab's adapter (the stub here), every call asks for a
    schema and gets an instance, and the guard records no connection attempt."""
    from deepeval_check import checks

    seen: list[dict[str, Any]] = []
    llm = judge_llm(schema_reply, seen)
    with guard.SocketGuard() as sockets:
        found = checks.faithfulness(
            llm,
            "How long must a password be?",
            "At least 15 characters.",
            ["Passwords must be at least 15 characters long."],
            penalize=False,
        )
    assert found["calls"] == len(seen) > 0
    assert all("response_format" in body for body in seen)  # every step asks for its schema
    assert isinstance(found["score"], int | float)  # 1 when no claim is extracted
    assert found["threshold"] == 0.5
    assert sockets.attempts == []
    assert checks.MODE == "llm"


@pytest.mark.parametrize(
    ("consistent", "contradicting", "higher", "reading"),
    [
        (0.9, 0.1, "consistent", "higher is better"),
        (0.1, 0.9, "contradicting", "higher is worse"),
        (0.5, 0.5, "neither", "undecided"),
    ],
)
def test_the_direction_report_names_the_output_that_scored_higher(
    consistent, contradicting, higher, reading
):
    """AC11's break: the report fed scripted scores with the outputs' names swapped fails here."""
    from deepeval_check.checks import HALLUCINATION_PAGE_READ, direction_report

    report = direction_report(
        {"score": consistent, "passes": consistent >= 0.5},
        {"score": contradicting, "passes": contradicting >= 0.5},
    )
    assert report["higher"] == higher
    assert str(report["reading"]).startswith(reading)
    assert report["consistent"] == {"score": consistent, "passes": consistent >= 0.5}
    assert report["contradicting"] == {"score": contradicting, "passes": contradicting >= 0.5}
    assert report["page_read"] == HALLUCINATION_PAGE_READ


@pytest.mark.parametrize(
    ("honest", "invented", "reading"),
    [
        ((0.0, False), (0.0, False), "not separated: the honest twin and the invented answer both"),
        ((1.0, True), (1.0, True), "not separated: the honest twin and the invented answer both"),
        ((0.3, False), (0.0, False), "not separated: the honest twin failed too"),
        ((1.0, True), (0.6, True), "not contradicted counts as truthful"),
        ((1.0, True), (0.0, False), "only supported claims count"),
    ],
)
def test_the_canary_reading_says_when_the_canary_separates_nothing(honest, invented, reading):
    """Fixed on 2026-10-21: the live run of that day read "only supported claims count: the
    invented value failed" from the invented answer alone, when the honest twin had scored 0.0 as
    well. Two answers that score the same are not separated, and the reading says so."""
    from deepeval_check.checks import canary_reading

    found = canary_reading(
        {"score": honest[0], "passes": honest[1]}, {"score": invented[0], "passes": invented[1]}
    )
    assert found.startswith(reading), found
    if honest[0] == invented[0] or not honest[1]:
        assert "only supported claims count" not in found
        assert "counts as truthful" not in found


def test_each_metric_records_the_steps_its_score_comes_from():
    """After measure, a FaithfulnessMetric's truths, claims, verdicts and reason, and a
    HallucinationMetric's verdicts and reason, are recorded beside the score."""
    from deepeval_check import checks

    llm = judge_llm(schema_reply, [])
    with guard.SocketGuard() as sockets:
        found = checks.faithfulness(llm, "q?", "a.", ["p."], penalize=False)
        seen = checks.hallucination(llm, "q?", "a.", ["p."])
    assert {"truths", "claims", "verdicts", "reason"} <= set(found)
    assert isinstance(found["claims"], list)
    assert isinstance(found["reason"], str)
    assert {"verdicts", "reason"} <= set(seen)
    assert sockets.attempts == []
    json.dumps(found)  # plain data: the results file holds it


def test_the_direction_report_keeps_each_outputs_steps():
    """The session of 2026-10-21 recorded the hallucination metric's verdicts and reason, but the
    direction report kept only each output's score and pass, so they were lost; it keeps them."""
    from deepeval_check.checks import direction_report

    steps = {"verdicts": [{"verdict": "no", "reason": "r"}], "reason": "why"}
    report = direction_report(
        {"score": 0.0, "passes": False, **steps}, {"score": 1.0, "passes": True, **steps}
    )
    assert report["consistent"] == {"score": 0.0, "passes": False, **steps}
    assert report["contradicting"]["verdicts"] == steps["verdicts"]


def test_deepevals_requests_get_their_own_output_cap_and_the_judge_config_is_unchanged():
    """DeepEval's requests ask for up to DEEPEVAL_MAX_TOKENS (its Truths list was cut off at the
    own judge's 512 on 2026-10-21); the committed judge config keeps 512, and nothing else of the
    judge changes."""
    from dataclasses import replace
    from pathlib import Path

    from deepeval_check.__main__ import DEEPEVAL_MAX_TOKENS, deepeval_config

    from raglab.evals import config as eval_config

    root = Path(__file__).resolve().parents[3]
    config = eval_config.load_judge(root / "config" / "judge-local.toml", root)
    raised = deepeval_config(config)
    assert DEEPEVAL_MAX_TOKENS == 2048
    assert (config.judge.max_tokens, raised.judge.max_tokens) == (512, 2048)
    assert replace(raised.judge, max_tokens=config.judge.max_tokens) == config.judge
    assert (raised.judging, raised.ollama) == (config.judging, config.ollama)
