"""Small pipelines, apps and generation runs for the S3 tests: the PACK chunks of
tests/retrieval_support with the fake embedder, FakeChat, and a spy that counts retrievals."""

import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import httpx

from raglab.adapters import factory
from raglab.adapters.fake import FakeChat, HashingEmbedder, echo
from raglab.chunk.sections import ChunkSettings
from raglab.core.ports import ChatModel, Guardrail, Retriever
from raglab.core.types import ChatMessage, ChatRequest, ScoredChunk
from raglab.evals import config as eval_config
from raglab.evals import generation, record
from raglab.generate.assemble import Assembled, assemble
from raglab.generate.pipeline import Pipeline
from raglab.guard import default_guards
from raglab.ingest.pipeline import Inventory
from tests.retrieval_support import GIT, PACK, dense, lab_root, local_embedder

TOKENS = {"demo": frozenset({"tenant-a", "tenant-b"}), "tenant-a-only": frozenset({"tenant-a"})}
DIGEST = "a" * 64
PROBES = [
    {
        "id": "P-01",
        "kind": "behaviour",
        "split": "dev",
        "tenant": "tenant-a",
        "question": "How many password reset attempts are allowed per day?",
        "question_kind": "abstention-probe",
        "feature_ids": ["F-32"],
        "expected": "abstain",
        "canaries_of": None,
    }
]


class SpyRetriever:
    """A retriever that counts its calls (AC6: a refused request never reaches retrieval)."""

    def __init__(self, inner: Retriever) -> None:
        self.inner = inner
        self.calls = 0

    @property
    def name(self) -> str:
        return self.inner.name

    def retrieve(self, query: str, tenant: str, k: int) -> list[ScoredChunk]:
        self.calls += 1
        return self.inner.retrieve(query, tenant, k)


def small_pipeline(
    chat: ChatModel | None = None, guards: Sequence[Guardrail] | None = None, k: int = 3
) -> tuple[Pipeline, SpyRetriever]:
    spy = SpyRetriever(dense(PACK))
    pipeline = Pipeline(spy, chat or FakeChat(), default_guards() if guards is None else guards, k)
    return pipeline, spy


def reply(label: str = "answer", answer: str = "x", cited=(), conflict=(), note: str = "") -> str:
    """A reply in the answer schema."""
    return json.dumps(
        {
            "label": label,
            "answer": answer,
            "cited_ids": list(cited),
            "conflict_ids": list(conflict),
            "conflict_note": note,
        }
    )


def generation_config_text(name: str = "generation-fake", trials: int = 2, cap: int = 600) -> str:
    return (
        f'name = "{name}"\nsuite = "generation"\n\n[dataset]\npath = "golden.jsonl"\n'
        'split = "dev"\n\n[chunker]\nchunk_size = 1200\noverlap = 1\n\n[embedder]\n'
        'provider = "fake"\nmodel = "hashing-256"\nrevision = "fake"\n\n'
        '[retriever]\nkind = "dense"\nk = 2\n\n[generator]\nprovider = "fake"\n'
        f'model = "fake-echo"\n\n[generation]\ntrials = {trials}\nseed = 7\nlevel = 0.95\n'
        f'probes = "probes.jsonl"\nrun_timeout_s = {cap}\n\n'
        '[api]\ntokens = { demo = ["tenant-a", "tenant-b"], tenant-a-only = ["tenant-a"] }\n'
    )


def generation_root(tmp_path: Path, probes: list[dict] | None = None) -> Path:
    """lab_root (schema, register, small golden file) with a probes file."""
    root = lab_root(tmp_path)
    lines = [json.dumps(p) for p in (PROBES if probes is None else probes)]
    (root / "probes.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return root


def echo_server(request: httpx.Request) -> httpx.Response:
    """The stub server's chat endpoint answering as FakeChat's echo would."""
    body = json.loads(request.content)
    user = ChatRequest((ChatMessage("user", body["messages"][-1]["content"]),), "s", {}, 0)
    return completion(echo(user))


def small_assembled(
    root: Path, chat: ChatModel | None = None, config_text: str | None = None, local: bool = False
) -> tuple[eval_config.GenerationConfig, Assembled]:
    """The small pack's pipeline with the fake embedder and FakeChat, or (local=True) with the
    real local embedder and the OpenAI-compatible adapter against the in-process stub server: a
    run publish may accept (its provenance is local, and no model field is fake)."""
    path = root / "config" / "generation.toml"
    path.parent.mkdir(exist_ok=True)
    path.write_text(config_text or generation_config_text(), encoding="utf-8")
    config = eval_config.load_generation(path, root)
    inventory = Inventory(ChunkSettings(), {"pypdf": "x"}, (), tuple(PACK))
    if local:
        embedder, description = local_embedder()
        model, chat_description, provenance = factory.chat(
            "openai-compat",
            "stub-model:1b",
            digest=DIGEST,
            base_url="http://127.0.0.1:11434",
            temperature=1.0,
            max_tokens=256,
            timeout_s=5,
            client=stub_client(stub_ollama(echo_server)),
        )
        built = assemble(
            config,
            root,
            embedder=(embedder, description, "local"),
            chat=(model, chat_description, provenance),
            inventory=inventory,
        )
        return config, built
    hashing = HashingEmbedder()
    fake_description = {
        "provider": "fake",
        "model": hashing.model,
        "revision": hashing.revision,
        "dimension": hashing.dimension,
    }
    fake_model = chat or FakeChat()
    built = assemble(
        config,
        root,
        embedder=(hashing, fake_description, "fake"),
        chat=(fake_model, fake_model.describe(), "fake"),
        inventory=inventory,
    )
    return config, built


def fake_generation_run(
    root: Path,
    chat: ChatModel | None = None,
    config_text: str | None = None,
    provenance: str | None = None,
    when: datetime = datetime(2026, 10, 18, 12, 0, 0, tzinfo=UTC),
    monotonic=None,
    local: bool = False,
) -> Path:
    """A generation run record written under root/runs/tmp with the fake embedder and chat, or
    (local=True) a local run publish may accept. A given provenance overrides the label, so a
    test can forge a fake run's."""
    config, built = small_assembled(root, chat, config_text, local)
    if provenance is not None:
        built = Assembled(
            built.pipeline,
            built.inventory,
            built.embedder_description,
            built.chat_description,
            provenance,
        )
    kwargs = {"monotonic": monotonic} if monotonic else {}
    manifest, cases = generation.run(config, root, built, git=GIT, clock=lambda: when, **kwargs)
    return record.write(root / "runs" / "tmp", manifest, cases)


def stub_ollama(
    chat_handler=None, digest: str = DIGEST, model: str = "stub-model:1b"
) -> httpx.MockTransport:
    """An in-process stand-in for an Ollama server (no socket): /api/tags lists the model with its
    digest, /api/version answers, and /v1/chat/completions is chat_handler (by default a reply
    that cites nothing and abstains)."""

    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(
                200, json={"models": [{"name": model, "model": model, "digest": digest}]}
            )
        if request.url.path == "/api/version":
            return httpx.Response(200, json={"version": "0.0.0-stub"})
        if request.url.path == "/v1/chat/completions":
            if chat_handler is not None:
                return chat_handler(request)
            return completion(reply("abstain", "The documents do not say."))
        return httpx.Response(404)

    return httpx.MockTransport(handle)


def completion(
    content: str, prompt_tokens: int = 100, completion_tokens: int = 20
) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [{"index": 0, "message": {"role": "assistant", "content": content}}],
            "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens},
        },
    )


def stub_client(transport: httpx.MockTransport) -> httpx.Client:
    return httpx.Client(base_url="http://127.0.0.1:11434", transport=transport)
