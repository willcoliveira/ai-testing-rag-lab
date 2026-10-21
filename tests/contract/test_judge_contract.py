"""S5 AC3: the judge's contract, against a stub server (in-process, no socket; pr-fast) and against
the local Ollama server in a judge session (marker `live`: `make judge-contract`, never `make
check`). The judge is built from config/judge-local.toml as a judged run builds it.

The contract: the adapter describes the pinned judge model; each request carries the config's
temperature, its cap on output tokens, the call's seed, and the verdict schema as a JSON schema
response format when the config asks for it; a reply to a judge prompt parses into a verdict
(status ok), carries no reasoning text, and reports its token counts.

The live test judges hand-written contract items only, never a golden answer. It also probes the
format the config does not name, so one session says which response format the judge's runner
accepts, and it writes every call's format, seconds and tokens to runs/tmp/judge-contract/.
"""

import json
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from raglab.adapters import factory
from raglab.core.types import JudgeItem, Passage, Status
from raglab.evals import config as eval_config
from raglab.judge.build import judge_from_config
from raglab.judge.llm import LLMJudge
from raglab.judge.prompts import judge_v2 as prompt
from tests.conftest import ROOT
from tests.generation_support import completion, stub_client, stub_ollama

pytestmark = pytest.mark.contract
JUDGE_CONFIG = ROOT / "config" / "judge-local.toml"
LOG_DIR = ROOT / "runs" / "tmp" / "judge-contract"

# Hand-written items of a fictional document, never a golden answer.
LOCKOUT = Passage(
    "C-PWD@1.0/5/1",
    "Contract Test Standard",
    "1.0",
    "5",
    "approved",
    "Accounts lock after 10 failed sign-ins within 15 minutes. The service desk unlocks them.",
)
LENGTH = Passage(
    "C-PWD@1.0/4.1/1",
    "Contract Test Standard",
    "1.0",
    "4.1",
    "approved",
    "Passwords must be at least 15 characters long.",
)
QUESTION = "How many failed sign-ins lock an account?"
SEED = 20261020
ITEMS = {
    "supported": JudgeItem(
        "grounded",
        QUESTION,
        (LOCKOUT, LENGTH),
        None,
        "An account locks after 10 failed sign-ins within 15 minutes.",
        SEED,
    ),
    "invented": JudgeItem(
        "grounded",
        QUESTION,
        (LOCKOUT, LENGTH),
        None,
        "An account locks after 5 failed sign-ins, and the lock lasts 2 hours.",
        SEED,
    ),
    "off-topic": JudgeItem(
        "relevant", QUESTION, None, None, "Passwords must be at least 15 characters long.", SEED
    ),
}


def judge_config() -> eval_config.JudgeConfig:
    return eval_config.load_judge(JUDGE_CONFIG, ROOT)


def check_contract(judge: LLMJudge, digest: str, item: JudgeItem) -> None:
    described = judge.describe()
    assert described["provider"] == "openai-compat"
    assert described["digest"] == digest
    verdict = judge.judge(item)
    assert verdict.status is Status.OK, f"{verdict.status}: {verdict.error}: {verdict.reply!r}"
    assert verdict.verdict in ("pass", "fail", "unable_to_verify")
    assert verdict.reasoning is False, "the reply carried reasoning text"
    assert verdict.prompt_tokens is not None
    assert verdict.completion_tokens is not None


# ---------------------------------------------------------------- the stub server (pr-fast)


def stub_judge(seen: list[dict], reply: str | None = None) -> LLMJudge:
    """The judge as config/judge-local.toml configures it, against a stub serving its tag."""
    spec = judge_config().judge

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return completion(
            reply
            or json.dumps(
                {
                    "answer_quote": "10 failed sign-ins",
                    "passage_ids": [LOCKOUT.chunk_id],
                    "reason": "The passage states the count.",
                    "verdict": "pass",
                }
            ),
            prompt_tokens=420,
            completion_tokens=48,
        )

    chat, _, provenance = factory.chat(
        spec.provider,
        spec.model,
        digest=spec.digest,
        base_url=spec.base_url,
        temperature=spec.temperature,
        top_p=spec.top_p,
        max_tokens=spec.max_tokens,
        timeout_s=spec.timeout_s,
        extra=spec.extra(),
        response_format=spec.response_format or "json_schema",
        client=stub_client(stub_ollama(handler, digest=str(spec.digest), model=spec.model)),
    )
    assert provenance == "local"
    return LLMJudge(chat)


@pytest.mark.unit
def test_the_judge_passes_the_contract_against_the_stub():
    seen: list[dict] = []
    spec = judge_config().judge
    judge = stub_judge(seen)
    check_contract(judge, str(spec.digest), ITEMS["supported"])
    [body] = seen
    assert body["model"] == "ministral-3:14b-instruct-2512-q4_K_M"
    assert (body["temperature"], body["max_tokens"], body["seed"], body["stream"]) == (
        0.0,
        spec.max_tokens,
        SEED,
        False,
    )
    if spec.response_format == "json_schema":
        assert body["response_format"] == {
            "type": "json_schema",
            "json_schema": {
                "name": "raglab_verdict",
                "schema": prompt.VERDICT_SCHEMA,
                "strict": True,
            },
        }
    else:
        assert "response_format" not in body
    assert "top_p" not in body
    assert "reasoning_effort" not in body
    assert [m["role"] for m in body["messages"]] == ["system", "user"]
    assert body["messages"][0]["content"] == prompt.SYSTEM


@pytest.mark.unit
def test_an_off_schema_reply_from_the_server_is_invalid_output_never_a_verdict():
    seen: list[dict] = []
    judge = stub_judge(seen, reply='{"verdict": "pass"}')
    verdict = judge.judge(ITEMS["supported"])
    assert (verdict.verdict, verdict.status) == ("unable_to_verify", Status.INVALID_OUTPUT)
    assert (verdict.prompt_tokens, verdict.completion_tokens) == (420, 48)


@pytest.mark.unit
def test_an_http_error_is_unavailable_never_a_verdict():
    spec = judge_config().judge

    def refuse(request: httpx.Request) -> httpx.Response:
        return httpx.Response(501, json={"error": "structured output is unavailable"})

    chat, _, _ = factory.chat(
        spec.provider,
        spec.model,
        digest=spec.digest,
        base_url=spec.base_url,
        temperature=spec.temperature,
        max_tokens=spec.max_tokens,
        timeout_s=spec.timeout_s,
        response_format="json_schema",
        client=stub_client(stub_ollama(refuse, digest=str(spec.digest), model=spec.model)),
    )
    verdict = LLMJudge(chat).judge(ITEMS["supported"])
    assert (verdict.verdict, verdict.status) == ("unable_to_verify", Status.UNAVAILABLE)
    assert verdict.error == "HTTP 501 from /v1/chat/completions"


@pytest.mark.unit
def test_the_judge_refuses_a_server_whose_tag_has_another_digest():
    spec = judge_config().judge
    with pytest.raises(factory.AdapterError, match="not the pinned"):
        factory.chat(
            spec.provider,
            spec.model,
            digest=spec.digest,
            base_url=spec.base_url,
            temperature=spec.temperature,
            max_tokens=spec.max_tokens,
            timeout_s=spec.timeout_s,
            client=stub_client(stub_ollama(digest="b" * 64, model=spec.model)),
        )


# ---------------------------------------------------------------- the live server (judge-contract)


def _record(log: Path, row: dict[str, object]) -> None:
    with log.open("a", encoding="utf-8") as out:
        out.write(json.dumps(row, sort_keys=True) + "\n")
    print(json.dumps(row, sort_keys=True), flush=True)


def _call(judge: LLMJudge, fmt: str, name: str, call: int, log: Path) -> Status:
    started = time.perf_counter()
    verdict = judge.judge(ITEMS[name])
    _record(
        log,
        {
            "format": fmt,
            "item": name,
            "call": call,
            "seconds": round(time.perf_counter() - started, 3),
            "status": verdict.status.value,
            "verdict": verdict.verdict,
            "quote_found": verdict.quote_found,
            "passages_given": verdict.passages_given,
            "reasoning": verdict.reasoning,
            "prompt_tokens": verdict.prompt_tokens,
            "completion_tokens": verdict.completion_tokens,
            "error": verdict.error,
        },
    )
    return verdict.status


@pytest.mark.live
def test_the_judge_passes_the_contract_against_the_local_server():
    config = judge_config()
    configured = config.judge.response_format or "json_schema"
    other = "none" if configured == "json_schema" else "json_schema"
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log = LOG_DIR / f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}.jsonl"
    judge, described, provenance = judge_from_config(config)
    assert provenance == "local"
    assert (described["model"], described["digest"]) == (config.judge.model, config.judge.digest)
    _record(log, {"described": described, "configured_format": configured})
    # call 1 loads the model; calls 2 to 4 are warm
    for call, name in enumerate(["supported", "supported", "invented", "off-topic"], start=1):
        _call(judge, configured, name, call, log)
    check_contract(judge, str(config.judge.digest), ITEMS["supported"])
    # the other format, recorded and never asserted: does this runner accept it?
    probe, _, _ = judge_from_config(config, response_format=other)
    for call, name in enumerate(["supported", "invented", "off-topic"], start=1):
        _call(probe, other, name, call, log)
    print(f"judge contract log: {log}", flush=True)
