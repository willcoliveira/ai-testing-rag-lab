"""S3 AC15: the local model server runs for one session only, under usage guards. Every OS read
and the process start are replaced by a fake host, so this runs offline and starts nothing. The
live part (a real server) is `make eval-local`."""

import json
import re
import signal
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from raglab.evals import config as eval_config
from raglab.runtime import ollama
from raglab.runtime.ollama import GIB, Host, Session, SessionError
from tests.conftest import ROOT

pytestmark = pytest.mark.unit
MODEL = "nemotron-3.5-lightning:30b-a3b-mlx"
MODEL_BYTES = 19 * GIB


@dataclass
class FakeHost(Host):
    tmp: Path = Path()
    binary: str | None = "/opt/homebrew/bin/ollama"
    memory: int = 40 * GIB
    services: list[str] = field(default_factory=list[str])
    foreign_port: bool = False  # the port held by a process this project did not start
    version: str = "0.40.6"
    loaded: list[str] = field(default_factory=list[str])
    stubborn: bool = False  # ignores SIGTERM and SIGKILL
    leftover: list[str] = field(default_factory=list[str])
    running: bool = False
    started: list[tuple[list[str], dict[str, str]]] = field(default_factory=list)
    signals: list[int] = field(default_factory=list[int])
    unloaded: list[str] = field(default_factory=list[str])

    def which_ollama(self):
        return self.binary

    def available_memory_bytes(self):
        return self.memory

    def registered_services(self):
        return self.services

    def port_open(self, host, port):
        return self.running or self.foreign_port

    def ollama_processes(self):
        return ["4242 ollama serve"] if self.running else list(self.leftover)

    def pid_alive(self, pid):
        return self.running and pid == 4242

    def start(self, command, env, log):
        self.started.append((command, env))
        self.running = True
        return 4242

    def signal_group(self, pid, sig):
        self.signals.append(sig)
        if not self.stubborn:
            self.running = False

    def http(self, method, url, body=None):
        if not self.running:
            raise OSError("connection refused")
        path = url.split(":11434", 1)[1]
        if path == "/api/version":
            return {"version": self.version}
        if path == "/api/ps":
            return {"models": [{"name": m} for m in self.loaded]}
        if path == "/api/generate":
            assert body is not None
            assert body["keep_alive"] == 0
            self.unloaded.append(str(body["model"]))
            self.loaded.remove(str(body["model"]))
            return {}
        raise AssertionError(path)

    def sleep(self, seconds):
        pass

    def models_dir(self):
        return self.tmp / "models"


def pulled(tmp: Path, size: int = MODEL_BYTES) -> None:
    manifest = (
        tmp / "models/manifests/registry.ollama.ai/library/nemotron-3.5-lightning/30b-a3b-mlx"
    )
    manifest.parent.mkdir(parents=True)
    layers = [{"size": size - 1000}, {"size": 600}]
    manifest.write_text(json.dumps({"config": {"size": 400}, "layers": layers}), encoding="utf-8")


def local_config() -> eval_config.GenerationConfig:
    return eval_config.load_generation(
        ROOT / "config" / "local-ollama.toml", ROOT, require_digest=False
    )


def session(tmp_path: Path, **host) -> tuple[Session, FakeHost, list[str]]:
    fake = FakeHost(tmp=tmp_path, **host)
    said: list[str] = []
    return ollama.session_for(local_config(), tmp_path, fake), fake, said


def test_the_server_gets_the_session_settings_as_its_environment(tmp_path, monkeypatch):
    monkeypatch.delenv("OLLAMA_MODELS", raising=False)
    pulled(tmp_path)
    s, fake, _ = session(tmp_path)
    s.say = lambda text: None
    assert s.up() == 4242
    [(command, env)] = fake.started
    assert command == ["/opt/homebrew/bin/ollama", "serve"]
    assert {k: v for k, v in env.items() if k.startswith("OLLAMA_")} == {
        "OLLAMA_HOST": "127.0.0.1:11434",
        "OLLAMA_KEEP_ALIVE": "2m",
        "OLLAMA_MAX_LOADED_MODELS": "1",
        "OLLAMA_NUM_PARALLEL": "1",
        "OLLAMA_CONTEXT_LENGTH": "8192",
    }
    assert set(env) == {"PATH", "HOME", *(k for k in env if k.startswith("OLLAMA_"))}
    assert (tmp_path / "runs/tmp/ollama/serve.pid").read_text() == "4242\n"
    assert s.down() == []
    assert not (tmp_path / "runs/tmp/ollama/serve.pid").exists()


def test_the_model_size_is_read_from_its_manifest(tmp_path):
    pulled(tmp_path)
    s, _, _ = session(tmp_path)
    assert s.model_size_bytes() == MODEL_BYTES


@pytest.mark.parametrize(
    ("host", "reason"),
    [
        ({"memory": 20 * GIB}, "not enough memory: 20.0 GiB available, 23.0 GiB needed"),
        ({"services": ["homebrew.mxcl.ollama"]}, "an Ollama service is registered"),
        ({"foreign_port": True}, "127.0.0.1:11434 is already held by a process this project"),
        ({"binary": None}, "the ollama binary is not on PATH"),
    ],
    ids=["low-memory", "service", "port-held", "no-binary"],
)
def test_the_preflight_refuses_and_nothing_starts(tmp_path, host, reason):
    pulled(tmp_path)
    s, fake, _ = session(tmp_path, **host)
    s.say = lambda text: None
    with pytest.raises(SessionError, match=re.escape(reason)):
        s.up()
    assert fake.started == []


def test_a_model_that_is_not_pulled_is_refused(tmp_path):
    s, fake, _ = session(tmp_path)
    with pytest.raises(SessionError, match="is not pulled"):
        s.up()
    assert fake.started == []


def test_the_memory_guard_is_the_model_size_plus_the_stated_margin(tmp_path):
    pulled(tmp_path)
    margin = local_config().ollama.memory_margin_gb  # pyright: ignore[reportOptionalMemberAccess]
    needed = MODEL_BYTES + int(margin * GIB)
    ok, _, _ = session(tmp_path, memory=needed)
    ok.say = lambda text: None
    assert ok.preflight() == []
    short, _, _ = session(tmp_path, memory=needed - 1)
    short.say = lambda text: None
    assert any("not enough memory" in p for p in short.preflight())


def test_an_old_server_is_refused_and_stopped(tmp_path):
    pulled(tmp_path)
    s, fake, _ = session(tmp_path, version="0.40.4")
    s.say = lambda text: None
    with pytest.raises(SessionError, match=r"0\.40\.4 is older than 0\.40\.6"):
        s.up()
    assert fake.running is False
    assert signal.SIGTERM in fake.signals


def test_down_unloads_the_model_and_the_postcheck_passes(tmp_path):
    pulled(tmp_path)
    s, fake, _ = session(tmp_path)
    s.say = lambda text: None
    s.up()
    fake.loaded.append(MODEL)
    assert s.down() == []
    assert fake.unloaded == [MODEL]
    assert fake.signals == [signal.SIGTERM]


def test_a_server_that_will_not_stop_fails_the_postcheck_loudly(tmp_path):
    pulled(tmp_path)
    s, fake, _ = session(tmp_path, stubborn=True)
    s.say = lambda text: None
    s.up()
    problems = s.down()
    assert fake.signals == [signal.SIGTERM, signal.SIGKILL]
    assert "127.0.0.1:11434 is still open" in problems
    assert any("ollama processes still run" in p for p in problems)


def test_a_leftover_ollama_process_fails_the_postcheck(tmp_path):
    s, _, _ = session(tmp_path, leftover=["777 ollama runner --model x"])
    assert s.postcheck() == ["ollama processes still run: ['777 ollama runner --model x']"]


@pytest.mark.parametrize("outcome", ["ok", "fails", "interrupted"])
def test_the_session_always_stops_the_server(tmp_path, outcome):
    pulled(tmp_path)
    s, fake, _ = session(tmp_path)
    said: list[str] = []
    s.say = said.append
    ran: list[str] = []

    def runner(command):
        ran.append(command[0])
        if outcome == "interrupted":
            raise KeyboardInterrupt
        return 3 if outcome == "fails" and command[0] == "first" else 0

    if outcome == "interrupted":
        with pytest.raises(KeyboardInterrupt):
            s.run([["first"], ["second"]], runner)
    else:
        code = s.run([["first"], ["second"]], runner)
        assert code == (3 if outcome == "fails" else 0)
    assert ran == (["first", "second"] if outcome == "ok" else ["first"])
    assert fake.running is False
    assert "postcheck passed: port closed, no ollama process, no model loaded" in said


def test_a_failed_postcheck_fails_the_session(tmp_path):
    pulled(tmp_path)
    s, _, _ = session(tmp_path, stubborn=True)
    said: list[str] = []
    s.say = said.append
    assert s.run([["ok"]], lambda command: 0) == 1
    assert any(line.startswith("POSTCHECK FAILED") for line in said)


def test_the_real_host_reads_vm_stat(monkeypatch):
    canned = (
        "Mach Virtual Memory Statistics: (page size of 16384 bytes)\n"
        "Pages free:                                   100.\n"
        "Pages active:                                5000.\n"
        "Pages inactive:                               200.\n"
        "Pages speculative:                             10.\n"
        "Pages purgeable:                               70.\n"
    )
    monkeypatch.setattr(ollama.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(ollama, "_run", lambda command: canned)
    assert Host().available_memory_bytes() == 16384 * (100 + 200 + 10)


def test_the_session_only_talks_to_loopback():
    with pytest.raises(SessionError, match="loopback"):
        Host().http("GET", "http://192.0.2.1:11434/api/ps")


def test_a_config_without_an_ollama_table_has_no_session():
    fake = eval_config.load_generation(ROOT / "config" / "fake.toml", ROOT)
    with pytest.raises(SessionError, match="no \\[ollama\\] table"):
        ollama.session_for(fake, ROOT)


def test_the_manifest_records_the_session_settings(tmp_path):
    """A run of the local config records its [ollama] settings (here with fake components, so
    nothing starts)."""
    from raglab.adapters.fake import FakeChat, HashingEmbedder
    from raglab.chunk.sections import ChunkSettings
    from raglab.evals import generation
    from raglab.generate.assemble import assemble
    from raglab.ingest.pipeline import Inventory
    from tests.generation_support import generation_root
    from tests.retrieval_support import GIT, PACK

    root = generation_root(tmp_path)
    text = (ROOT / "config" / "local-ollama.toml").read_text(encoding="utf-8")
    text = text.replace("datasets/golden.v1.jsonl", "golden.jsonl").replace(
        "datasets/probes.s3.jsonl", "probes.jsonl"
    )
    path = root / "config" / "local.toml"
    path.parent.mkdir(exist_ok=True)
    path.write_text(text, encoding="utf-8")
    config = eval_config.load_generation(path, root, require_digest=False)
    embedder, chat = HashingEmbedder(), FakeChat()
    built = assemble(
        config,
        root,
        embedder=(
            embedder,
            {"provider": "fake", "model": "h", "revision": "f", "dimension": 256},
            "fake",
        ),
        chat=(chat, chat.describe(), "fake"),
        inventory=Inventory(ChunkSettings(), {}, (), tuple(PACK)),
    )
    manifest, _ = generation.run(config, root, built, git=GIT)
    assert manifest["ollama"] == {
        "host": "127.0.0.1:11434",
        "keep_alive": "2m",
        "max_loaded_models": 1,
        "num_parallel": 1,
        "context_length": 8192,
    }


def test_the_makefile_has_the_session_targets():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    for target in ("ollama-up", "ollama-down", "ollama-status", "eval-local"):
        assert re.search(rf"^{target}:", makefile, flags=re.M), target
    eval_local = makefile.split("\neval-local:", 1)[1].split("\n\n", 1)[0].replace("\\\n", "")
    assert "raglab ollama session --config config/local-ollama.toml" in eval_local
    assert "-m live" in eval_local
    assert "raglab eval --suite generation --config config/local-ollama.toml" in eval_local


def test_a_refused_group_signal_falls_back_to_the_server_itself(monkeypatch):
    sent: list[tuple[str, int, int]] = []

    def killpg(pid, sig):
        raise PermissionError(1, "Operation not permitted")

    monkeypatch.setattr(ollama.os, "killpg", killpg)
    monkeypatch.setattr(ollama.os, "kill", lambda pid, sig: sent.append(("kill", pid, sig)))
    Host().signal_group(4242, signal.SIGTERM)
    assert sent == [("kill", 4242, signal.SIGTERM)]
