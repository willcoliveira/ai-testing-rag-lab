"""Small pipelines, apps and generation runs for the S3 tests: the PACK chunks of
tests/retrieval_support with the fake embedder, FakeChat, and a spy that counts retrievals."""

import json
import shutil
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path

import httpx

from raglab.adapters import factory
from raglab.adapters.fake import FakeChat, HashingEmbedder, echo
from raglab.chunk.sections import ChunkSettings
from raglab.core.ports import ChatModel, Guardrail, Retriever
from raglab.core.types import ChatMessage, ChatRequest, Chunk, ScoredChunk
from raglab.evals import config as eval_config
from raglab.evals import generation, record
from raglab.generate.assemble import Assembled, assemble
from raglab.generate.pipeline import Pipeline
from raglab.guard import default_guards
from raglab.ingest.pipeline import Inventory, section_chunks
from tests.conftest import ROOT
from tests.retrieval_support import (
    GIT,
    PACK,
    QUESTIONS,
    dense,
    lab_root,
    local_embedder,
    make_chunk,
    write_register,
)

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


def generation_config_text(
    name: str = "generation-fake",
    trials: int = 2,
    cap: int = 600,
    probes: bool = True,
    split: str = "dev",
) -> str:
    return (
        f'name = "{name}"\nsuite = "generation"\n\n[dataset]\npath = "golden.jsonl"\n'
        f'split = "{split}"\n\n[chunker]\nchunk_size = 1200\noverlap = 1\n\n[embedder]\n'
        'provider = "fake"\nmodel = "hashing-256"\nrevision = "fake"\n\n'
        '[retriever]\nkind = "dense"\nk = 2\n\n[generator]\nprovider = "fake"\n'
        f'model = "fake-echo"\n\n[generation]\ntrials = {trials}\nseed = 7\nlevel = 0.95\n'
        + ('probes = "probes.jsonl"\n' if probes else "")
        + f"run_timeout_s = {cap}\n\n"
        '[api]\ntokens = { demo = ["tenant-a", "tenant-b"], tenant-a-only = ["tenant-a"] }\n'
    )


def generation_root(
    tmp_path: Path, probes: list[dict] | None = None, questions: list[dict] | None = None
) -> Path:
    """lab_root (schema, register, the real answer key) with a small golden file, by default the
    retrieval questions of QUESTIONS (its Q6 is a behaviour line without a case's fields, which
    the generation suite refuses since S4), and a probes file."""
    retrieval_only = [q for q in QUESTIONS if q["kind"] == "retrieval"]
    root = lab_root(tmp_path, retrieval_only if questions is None else questions)
    lines = [json.dumps(p) for p in (PROBES if probes is None else probes)]
    (root / "probes.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return root


def echo_server(request: httpx.Request) -> httpx.Response:
    """The stub server's chat endpoint answering as FakeChat's echo would."""
    body = json.loads(request.content)
    user = ChatRequest((ChatMessage("user", body["messages"][-1]["content"]),), "s", {}, 0)
    return completion(echo(user))


def small_assembled(
    root: Path,
    chat: ChatModel | None = None,
    config_text: str | None = None,
    local: bool = False,
    handler=None,
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
            client=stub_client(stub_ollama(handler or echo_server)),
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
    handler=None,
    gate: str = "manual",
) -> Path:
    """A generation run record written under root/runs/tmp with the fake embedder and chat, or
    (local=True) a local run publish may accept. A given provenance overrides the label, so a
    test can forge a fake run's."""
    config, built = small_assembled(root, chat, config_text, local, handler)
    if provenance is not None:
        built = Assembled(
            built.pipeline,
            built.inventory,
            built.embedder_description,
            built.chat_description,
            provenance,
        )
    kwargs = {"monotonic": monotonic} if monotonic else {}
    manifest, cases = generation.run(
        config, root, built, gate=gate, git=GIT, clock=lambda: when, **kwargs
    )
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


# ---------------------------------------------------------------- S4: behaviour cases
#
# A small pack whose chunks carry the real document and section ids the answer key names, so the
# real answer key's conflict sides apply (F-04: A-PWD-V2 4.4 new, A-PWD-V1 4.3 old; F-53's FAQ Q2
# restates 4.4). The texts are short stand-ins, and the retriever returns, for each question, the
# chunks a test chose, so a conflict side can be retrieved or not on purpose.

V2_41 = make_chunk("A-PWD-V2@2.0/4.1/1", "tenant-a", "Passwords are 15 characters long.", "4.1")
V2_44 = make_chunk("A-PWD-V2@2.0/4.4/1", "tenant-a", "User passwords expire every 60 days.", "4.4")
V2_46 = make_chunk("A-PWD-V2@2.0/4.6/1", "tenant-a", "Never share your password.", "4.6")
V2_5 = make_chunk("A-PWD-V2@2.0/5/1", "tenant-a", "Accounts lock after 10 failures.", "5")
V1_43 = make_chunk("A-PWD-V1@1.0/4.3/1", "tenant-a", "Passwords expire every 90 days.", "4.3")
V1_44 = make_chunk(
    "A-PWD-V1@1.0/4.4/1", "tenant-a", "Accounts stay locked until the desk unlocks them.", "4.4"
)
FAQ_Q2 = make_chunk("A-FAQ@1.0/Q2/1", "tenant-a", "Q2 Passwords expire every 60 days.", "Q2")
# the real excerpt's section 3.1.1.2, two chunks at the default settings: a may_quote section is
# derived again from the corpus when a record's golden file is current (raglab.evals.record), so
# the fixture's root carries the real document and these are its real chunks
NIST_PATH = "corpus/external/nist-sp-800-63b-4-excerpt.md"
NIST_CHUNKS = section_chunks(ROOT, "X-NIST", "3.1.1.2")
NIST = NIST_CHUNKS[0]  # the maximum-length sentence (at least 64 characters) is in the first
B_33 = make_chunk(
    "B-PWD@1.0/3.3/1", "tenant-b", "Passwords do not expire; a reset link lasts 30 minutes.", "3.3"
)
BEHAVIOUR_CHUNKS = [V2_41, V2_44, V2_46, V2_5, V1_43, V1_44, FAQ_Q2, *NIST_CHUNKS, B_33]

Q_ANS = "How long must a password be?"
Q_FC = "Has the expiry period changed?"
Q_FC2 = "What did the old standard say about expiry?"
Q_ABS = "How many reset attempts a day?"
Q_ABQ = "What is the longest password allowed?"
Q_RH = "Can my colleague use my password?"
Q_TB = "Do our passwords expire?"
Q_CUR = "How long does my locked account stay locked?"  # a current value, like G-04


def behaviour_cases() -> list[dict]:
    from tests.dataset_support import case, group, sec

    return [
        case("B-ANS", "single-chunk", "answer", "dev", ["F-01", "F-47"],
             [sec("A-PWD-V2", "4.1")], question=Q_ANS),
        case("B-FC", "version-conflict", "flag-conflict", "dev", ["F-04", "F-53"],
             [group(sec("A-PWD-V2", "4.4"), sec("A-FAQ", "Q2")), sec("A-PWD-V1", "4.3")],
             question=Q_FC),
        case("B-FC2", "version-conflict", "flag-conflict", "dev", ["F-04"],
             [sec("A-PWD-V2", "4.4"), sec("A-PWD-V1", "4.3")], question=Q_FC2),
        case("B-ABS", "unanswerable", "abstain", "dev", ["F-32"], question=Q_ABS),
        case("B-ABQ", "unanswerable", "abstain", "dev", ["F-40"], tenant="tenant-b",
             may_quote=sec("X-NIST", "3.1.1.2"), question=Q_ABQ),
        case("B-RH", "single-chunk", "refuse-and-help", "dev", ["F-42"],
             [sec("A-PWD-V2", "4.6")], question=Q_RH),
        case("B-TB", "single-chunk", "answer", "dev", ["F-35"], [sec("B-PWD", "3.3")],
             tenant="tenant-b", question=Q_TB),
    ]  # fmt: skip


RETRIEVED = {
    Q_ANS: [V2_41, V2_5],
    Q_FC: [FAQ_Q2, V1_43],  # the conflict side retrieved; the governing side by its FAQ member
    Q_FC2: [V2_44, V2_41],  # the conflict side not retrieved
    Q_ABS: [V2_5],
    Q_ABQ: [NIST, B_33],
    Q_RH: [V2_46],
    Q_TB: [B_33],
    Q_CUR: [V2_5, V1_44],  # the superseded 1.0 section retrieved outside the labels
}
# replies that pass every check that applies
GOOD = {
    Q_ANS: reply("answer", "Passwords are 15 characters long.", [V2_41.chunk_id]),
    Q_FC: reply(
        "flag-conflict",
        "They expire every 60 days now; version 1.0 said every 90 days.",
        [FAQ_Q2.chunk_id, V1_43.chunk_id],
        [FAQ_Q2.chunk_id, V1_43.chunk_id],
        "version 1.0 is superseded",
    ),
    Q_FC2: reply("answer", "They expire every 60 days.", [V2_44.chunk_id]),
    Q_ABS: reply("abstain", "The documents do not say how many reset attempts are allowed."),
    Q_ABQ: reply(
        "abstain",
        "Our documents do not say; NIST SP 800-63B-4 says at least 64 characters.",
        [NIST.chunk_id],
    ),
    Q_RH: reply("refuse-and-help", "Do not share it; ask the owner for access.", [V2_46.chunk_id]),
    Q_TB: reply("answer", "Passwords do not expire.", [B_33.chunk_id]),
}


def write_behaviour_register(root: Path) -> None:
    """The behaviour pack's register: a placeholder file for each tenant document (as
    write_register writes them) and the real NIST excerpt, from which a may_quote section is
    read again when a record is validated."""
    write_register(root, {c.doc_id: c.tenant for c in BEHAVIOUR_CHUNKS if c.doc_id != "X-NIST"})
    (root / NIST_PATH).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / NIST_PATH, root / NIST_PATH)
    with (root / "corpus" / "register.yaml").open("a", encoding="utf-8") as entries:
        entries.write(
            "- id: X-NIST\n  status: reference\n  supersedes: null\n  tenant: shared\n"
            f"  path: {NIST_PATH}\n"
        )


class ScriptedRetriever:
    """A retriever that returns the chunks a test chose for each question, best first."""

    def __init__(self, by_question: dict[str, list[Chunk]]) -> None:
        self.by_question = by_question

    @property
    def name(self) -> str:
        return "scripted"

    def retrieve(self, query: str, tenant: str, k: int) -> list[ScoredChunk]:
        chosen = self.by_question.get(query, [])[:k]
        return [ScoredChunk(chunk, round(1.0 - n / 10, 6)) for n, chunk in enumerate(chosen)]


def per_question(replies: dict[str, str]) -> Callable[[ChatRequest], str]:
    """A FakeChat script: the reply chosen for the question the request frames."""

    def answer(request: ChatRequest) -> str:
        user = request.messages[-1].content
        for question, text in replies.items():
            if f"<question>\n{question}\n</question>" in user:
                return text
        raise AssertionError(f"no scripted reply for {user[:80]!r}")

    return answer


def behaviour_run(
    tmp_path: Path,
    replies: dict[str, str] | None = None,
    cases: list[dict] | None = None,
    retrieved: dict[str, list[Chunk]] | None = None,
    trials: int = 2,
    split: str = "dev",
    gate: str = "manual",
    local: bool = False,
    root: Path | None = None,
    when: datetime = datetime(2026, 10, 19, 12, 0, 0, tzinfo=UTC),
) -> tuple[Path, Path]:
    """(root, run directory) of a generation run of the behaviour cases: the small pack above,
    the scripted retriever, and the given replies (GOOD by default) from FakeChat, or (local=True)
    from the OpenAI-compatible adapter against the in-process stub server, described with the real
    local embedder, so the record is not fake and publish and the gates may read it. No probes
    file. The record is written and left for the test to validate. A given root is reused."""
    if root is None:
        root = lab_root(tmp_path, cases if cases is not None else behaviour_cases())
        write_behaviour_register(root)
    path = root / "config" / "generation.toml"
    path.parent.mkdir(exist_ok=True)
    path.write_text(
        generation_config_text(trials=trials, probes=False, split=split), encoding="utf-8"
    )
    config = eval_config.load_generation(path, root)
    script = per_question({**GOOD, **(replies or {})})
    retriever = ScriptedRetriever(RETRIEVED | (retrieved or {}))
    inventory = Inventory(ChunkSettings(), {"pypdf": "x"}, (), tuple(BEHAVIOUR_CHUNKS))
    if local:

        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            user = ChatRequest((ChatMessage("user", body["messages"][-1]["content"]),), "s", {}, 0)
            return completion(script(user))

        _, description = local_embedder()
        model, chat_description, provenance = factory.chat(
            "openai-compat",
            "stub-model:1b",
            digest=DIGEST,
            base_url="http://127.0.0.1:11434",
            temperature=1.0,
            max_tokens=256,
            timeout_s=5,
            client=stub_client(stub_ollama(handler)),
        )
        pipeline = Pipeline(retriever, model, default_guards(), 2)
        built = Assembled(pipeline, inventory, description, chat_description, provenance)
    else:
        chat = FakeChat(script)
        hashing = HashingEmbedder()
        description = {
            "provider": "fake",
            "model": hashing.model,
            "revision": hashing.revision,
            "dimension": hashing.dimension,
        }
        pipeline = Pipeline(retriever, chat, default_guards(), 2)
        built = Assembled(pipeline, inventory, description, chat.describe(), "fake")
    manifest, rows = generation.run(config, root, built, gate=gate, git=GIT, clock=lambda: when)
    return root, record.write(root / "runs" / "tmp", manifest, rows)
