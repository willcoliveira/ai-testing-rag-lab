"""S3 AC5: the OpenAI-compatible adapter passes the shared chat contract against a stub server
(in-process, no socket; pr-fast) and against the local Ollama server (marker `live`: run by
`make eval-local`, never by `make check`); and it refuses to start when the server's copy of the
tag has another digest, when the tag is not pulled, or when the server is not local.

The contract: the adapter describes the pinned model, sends the answer schema as a JSON schema
response format with the config's settings, and a reply to the answer prompt parses into an
Answer (status ok) whose citations are ids of the passages it was given, with no reasoning text
(thinking off) and token counts reported.
"""

import json
import os
from pathlib import Path

import httpx
import pytest

from raglab.adapters import factory
from raglab.adapters.openai_compat import ChatConfigError, OpenAICompatChat
from raglab.core.ports import ChatModel
from raglab.core.types import ChatMessage, ChatRequest, ScoredChunk
from raglab.evals import config as eval_config
from raglab.generate.prompts import answer_v1 as prompt
from tests.conftest import ROOT
from tests.generation_support import DIGEST, completion, reply, stub_client, stub_ollama
from tests.retrieval_support import PACK

pytestmark = pytest.mark.contract
LOCAL_CONFIG = ROOT / "config" / "local-ollama.toml"
# the live test's config; another one (a copy with response_format = "json_schema", to re-test
# schema mode after an Ollama upgrade) by RAGLAB_LIVE_CONFIG (docs/COMPATIBILITY.md)
LIVE_CONFIG = Path(os.environ.get("RAGLAB_LIVE_CONFIG", str(LOCAL_CONFIG)))
PASSAGES = [ScoredChunk(c, 0.9) for c in PACK[:3]]


def contract_request() -> ChatRequest:
    system, user = prompt.build("How many characters must passwords have?", "tenant-a", PASSAGES)
    return ChatRequest(
        (ChatMessage("system", system), ChatMessage("user", user)),
        prompt.SCHEMA_NAME,
        prompt.ANSWER_SCHEMA,
        20261018,
    )


def check_contract(chat: ChatModel, digest: str) -> None:
    described = chat.describe()
    assert described["provider"] == "openai-compat"
    assert described["model"] == chat.model
    assert described["digest"] == digest
    reply_ = chat.complete(contract_request())
    answer = prompt.parse(reply_.text)  # raises InvalidOutput when the reply is off-schema
    assert answer.label in ("answer", "abstain")
    assert set(answer.cited_ids) <= {r.chunk.chunk_id for r in PASSAGES}
    assert reply_.reasoning is False, "the reply carried reasoning text: thinking is not off"
    assert reply_.prompt_tokens is not None
    assert reply_.completion_tokens is not None


# ---------------------------------------------------------------- the stub server (pr-fast)


def echoing_stub(seen: list[dict]):
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append(body)
        return completion(reply("answer", "At least 15 characters.", cited=[PACK[0].chunk_id]))

    return handler


def stub_adapter(handler=None, extra=None, model: str = "stub-model:1b") -> OpenAICompatChat:
    """The adapter, configured for stub-model:1b, against a stub serving `model`."""
    return OpenAICompatChat(
        "http://127.0.0.1:11434",
        "stub-model:1b",
        DIGEST,
        temperature=0.2,
        max_tokens=256,
        timeout_s=5,
        extra=extra,
        client=stub_client(stub_ollama(handler, model=model)),
    )


@pytest.mark.unit
def test_the_adapter_passes_the_contract_against_the_stub():
    seen: list[dict] = []
    chat = stub_adapter(echoing_stub(seen), extra={"reasoning_effort": "none"})
    check_contract(chat, DIGEST)
    [body] = seen
    assert body["model"] == "stub-model:1b"
    assert (body["temperature"], body["max_tokens"], body["seed"], body["stream"]) == (
        0.2,
        256,
        20261018,
        False,
    )
    assert body["response_format"] == {
        "type": "json_schema",
        "json_schema": {"name": "raglab_answer", "schema": prompt.ANSWER_SCHEMA, "strict": True},
    }
    assert body["reasoning_effort"] == "none"
    assert [m["role"] for m in body["messages"]] == ["system", "user"]
    assert chat.describe()["server_version"] == "0.0.0-stub"
    assert chat.describe()["extra"] == {"reasoning_effort": "none"}


@pytest.mark.unit
def test_no_extra_field_is_sent_unless_the_config_names_it():
    seen: list[dict] = []
    stub_adapter(echoing_stub(seen)).complete(contract_request())
    assert "reasoning_effort" not in seen[0]
    assert "top_p" not in seen[0]


@pytest.mark.unit
def test_top_p_is_sent_and_described_when_configured():
    seen: list[dict] = []
    chat = OpenAICompatChat(
        "http://127.0.0.1:11434",
        "stub-model:1b",
        DIGEST,
        temperature=1.0,
        top_p=0.95,
        max_tokens=256,
        timeout_s=5,
        client=stub_client(stub_ollama(echoing_stub(seen))),
    )
    chat.complete(contract_request())
    assert (seen[0]["temperature"], seen[0]["top_p"]) == (1.0, 0.95)
    assert chat.describe()["top_p"] == 0.95


@pytest.mark.unit
def test_response_format_none_sends_no_response_format_and_still_parses():
    """The local config's setting (Ollama 0.40.6's MLX runner refuses any response format with
    HTTP 501): the schema is asked for by the prompt alone, and the reply is still parsed
    strictly."""
    seen: list[dict] = []
    chat = OpenAICompatChat(
        "http://127.0.0.1:11434",
        "stub-model:1b",
        DIGEST,
        temperature=0.2,
        max_tokens=256,
        timeout_s=5,
        response_format="none",
        client=stub_client(stub_ollama(echoing_stub(seen))),
    )
    check_contract(chat, DIGEST)
    assert "response_format" not in seen[0]
    assert chat.describe()["response_format"] == "none"
    with pytest.raises(ChatConfigError, match="response_format 'json_object'"):
        OpenAICompatChat(
            "http://127.0.0.1:11434",
            "m",
            DIGEST,
            temperature=0,
            max_tokens=1,
            timeout_s=1,
            response_format="json_object",
        )


@pytest.mark.unit
def test_a_reply_with_reasoning_text_is_reported():
    def thinking(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": reply("abstain", "No."), "reasoning": "Let me think"}}
                ]
            },
        )

    assert stub_adapter(thinking).complete(contract_request()).reasoning is True


@pytest.mark.unit
def test_a_digest_mismatch_refuses_to_start():
    with pytest.raises(ChatConfigError, match=r"has digest b{64}, not the pinned a{64}"):
        OpenAICompatChat(
            "http://127.0.0.1:11434",
            "stub-model:1b",
            "a" * 64,
            temperature=0.2,
            max_tokens=256,
            timeout_s=5,
            client=stub_client(stub_ollama(digest="b" * 64)),
        )


@pytest.mark.unit
def test_a_model_that_is_not_pulled_refuses_to_start():
    with pytest.raises(
        ChatConfigError, match=r"stub-model:1b is not on http://127\.0\.0\.1:11434: pull it"
    ):
        stub_adapter(model="another:1b")


@pytest.mark.unit
def test_a_server_that_is_down_refuses_to_start():
    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    client = httpx.Client(base_url="http://127.0.0.1:11434", transport=httpx.MockTransport(down))
    with pytest.raises(ChatConfigError, match="is the server up"):
        OpenAICompatChat(
            "http://127.0.0.1:11434",
            "stub-model:1b",
            DIGEST,
            temperature=0.2,
            max_tokens=256,
            timeout_s=5,
            client=client,
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    "url", ["https://api.example.com", "http://192.0.2.10:11434", "http://model-server:11434"]
)
def test_a_server_that_is_not_local_is_refused(url):
    with pytest.raises(ChatConfigError, match="local model only"):
        OpenAICompatChat(url, "m", DIGEST, temperature=0, max_tokens=1, timeout_s=1)


@pytest.mark.unit
def test_the_factory_wraps_a_refusal_and_builds_fake_only_on_provider_fake():
    with pytest.raises(factory.AdapterError, match="m:1b is not on"):
        factory.chat(
            "openai-compat",
            "m:1b",
            digest=DIGEST,
            base_url="http://127.0.0.1:11434",
            temperature=0,
            max_tokens=1,
            timeout_s=1,
            client=stub_client(stub_ollama()),
        )
    with pytest.raises(factory.AdapterError, match="only fake and openai-compat"):
        factory.chat("anthropic", "x")
    model, described, provenance = factory.chat("fake", "fake-echo")
    assert (type(model).__name__, described["provider"], provenance) == ("FakeChat", "fake", "fake")


# ---------------------------------------------------------------- the committed live config


@pytest.mark.unit
def test_the_live_config_refuses_to_run_until_its_digest_is_pinned(tmp_path):
    text = LOCAL_CONFIG.read_text(encoding="utf-8")
    placeholder = tmp_path / "local-ollama.toml"
    lines = [
        'digest = "fill in from /api/tags after ollama pull"'
        if line.startswith("digest = ")
        else line
        for line in text.splitlines()
    ]
    placeholder.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(eval_config.ConfigError, match="refuses to start until the tag's digest"):
        eval_config.load_generation(placeholder, ROOT)
    loose = eval_config.load_generation(placeholder, ROOT, require_digest=False)
    assert loose.generator.model == "nemotron-3.5-lightning:30b-a3b-mlx"
    from raglab.__main__ import main

    assert main(["eval", "--suite", "generation", "--config", str(placeholder)]) == 1


# ---------------------------------------------------------------- the live server (make eval-local)


@pytest.mark.live
def test_the_adapter_passes_the_contract_against_the_local_server():
    config = eval_config.load_generation(LIVE_CONFIG, ROOT)
    spec = config.generator
    chat, described, provenance = factory.chat(
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
    )
    assert provenance == "local"
    assert described["extra"] == spec.extra()
    check_contract(chat, str(spec.digest))
