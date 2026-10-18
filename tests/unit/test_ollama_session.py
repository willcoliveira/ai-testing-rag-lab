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
    asked: list[tuple[str, int]] = field(default_factory=list)  # every (host, port) checked
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
        self.asked.append((host, port))
        return self.running or self.foreign_port

    def ollama_processes(self):
        return ["4242 ollama serve"] if self.running else list(self.leftover)

    def pid_alive(self, pid):
        return self.running and pid == 4242

    def exited(self, pid):
        return not self.pid_alive(pid)

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


MANIFEST_RUN = """
import json, sys
from pathlib import Path
sys.path.insert(0, {root!r})
from raglab.adapters.fake import FakeChat, HashingEmbedder
from raglab.chunk.sections import ChunkSettings
from raglab.evals import config as eval_config
from raglab.evals import generation
from raglab.generate.assemble import assemble
from raglab.ingest.pipeline import Inventory
from tests.generation_support import generation_root
from tests.retrieval_support import GIT, PACK

repo = Path({root!r})
root = generation_root(Path({tmp!r}))
text = (repo / "config" / "local-ollama.toml").read_text(encoding="utf-8")
text = text.replace("datasets/golden.v1.jsonl", "golden.jsonl")
text = text.replace("datasets/probes.s3.jsonl", "probes.jsonl")
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
        {{"provider": "fake", "model": "h", "revision": "f", "dimension": 256}},
        "fake",
    ),
    chat=(chat, chat.describe(), "fake"),
    inventory=Inventory(ChunkSettings(), {{}}, (), tuple(PACK)),
)
manifest, _ = generation.run(config, root, built, git=GIT)
print(json.dumps(manifest["ollama"]))
"""


def test_the_manifest_records_the_session_settings(tmp_path):
    """A run of the local config records its [ollama] settings (here with fake components, so
    nothing starts). The run happens in a short subprocess, which keeps onnxruntime (imported
    through the adapters' factory) out of this file's pytest process: onnxruntime 1.30.0 on macOS
    aborts the process at exit (libc++ "recursive_mutex lock failed") when it lives about 10 s
    after the import, and this file's signal tests take that long (S3 ledger, fix round 3)."""
    import subprocess
    import sys

    script = MANIFEST_RUN.format(root=str(ROOT), tmp=str(tmp_path))
    done = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, timeout=120, check=False
    )
    assert done.returncode == 0, done.stderr[-2000:]
    assert json.loads(done.stdout.strip().splitlines()[-1]) == {
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


def test_only_the_ollama_executable_counts_as_an_ollama_process(monkeypatch):
    """Judge S3-J5: the postcheck matches the executable, not any command line that names ollama
    (an editor on the config, a tail of the log, the session's own raglab command)."""
    listing = (
        "4593 /opt/homebrew/bin/ollama serve\n"
        "4601 /opt/homebrew/Cellar/ollama/0.40.6/bin/ollama runner --mlx --model x\n"
        "777 vim config/local-ollama.toml\n"
        "778 tail -f runs/tmp/ollama/serve.log\n"
        "779 /repo/.venv/bin/python /repo/.venv/bin/raglab ollama session --config x\n"
    )
    monkeypatch.setattr(ollama, "_run", lambda command: listing)
    assert Host().ollama_processes() == [
        "4593 /opt/homebrew/bin/ollama serve",
        "4601 /opt/homebrew/Cellar/ollama/0.40.6/bin/ollama runner --mlx --model x",
    ]
    monkeypatch.setattr(ollama, "_run", lambda command: "777 vim config/local-ollama.toml\n")
    assert Host().ollama_processes() == []


def test_the_preflight_and_the_postcheck_ask_about_the_configured_port(tmp_path):
    """Judge S3-J3: the fake host records which port is checked, so a guard that looks at another
    port fails here."""
    pulled(tmp_path)
    s, fake, _ = session(tmp_path)
    s.say = lambda text: None
    assert s.preflight() == []
    assert fake.asked == [("127.0.0.1", 11434)]
    fake.asked.clear()
    assert s.postcheck() == []
    assert fake.asked == [("127.0.0.1", 11434)]


SIGNALLED_SESSION = """
import json, os, signal, sys
from pathlib import Path
sys.path.insert(0, {root!r})
from tests.unit.test_ollama_session import FakeHost, local_config, pulled
from raglab.runtime import ollama
tmp = Path({tmp!r})
pulled(tmp)
host = FakeHost(tmp=tmp)
said = []
session = ollama.session_for(local_config(), tmp, host)
session.say = said.append
def runner(command):
    os.kill(os.getpid(), signal.{sig})
    return 0
try:
    session.run([["first"]], runner)
finally:
    out = {{"signals": host.signals, "said": said, "running": host.running}}
    print(json.dumps(out), flush=True)
"""


@pytest.mark.parametrize("sig", ["SIGTERM", "SIGHUP"])
def test_a_terminated_session_still_stops_the_server_and_runs_the_postcheck(tmp_path, sig):
    """Judge S3-J2: `kill` (SIGTERM) or a closed terminal (SIGHUP) of the session process ends it
    through its finally block: the server gets SIGTERM and the postcheck runs. SIGKILL cannot be
    trapped (docs/LOCAL-MODEL.md: the pid-file guard then makes the next up refuse)."""
    import subprocess
    import sys

    script = SIGNALLED_SESSION.format(root=str(ROOT), tmp=str(tmp_path), sig=sig)
    done = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, timeout=60, check=False
    )
    lines = [line for line in done.stdout.splitlines() if line.startswith("{")]
    assert lines, (done.returncode, done.stdout, done.stderr[-500:])
    out = json.loads(lines[-1])
    assert signal.SIGTERM.value in out["signals"]
    assert out["running"] is False
    assert "postcheck passed: port closed, no ollama process, no model loaded" in out["said"]
    assert done.returncode != 0  # the session still ends as signalled


PIPED_SESSION = """
import sys, time
from pathlib import Path
sys.path.insert(0, {root!r})
from tests.unit.test_ollama_session import FakeHost, local_config, pulled
from raglab.runtime import ollama
lab = Path({lab!r})
pulled(lab)
session = ollama.session_for(local_config(), lab, FakeHost(tmp=lab))
marker = Path({marker!r})
def runner(command):
    marker.write_text("sleeping", encoding="utf-8")
    time.sleep(2)
    return 0
sys.exit(session.run([["first"]], runner))
"""


def test_the_sessions_lines_reach_a_pipe_as_they_happen(tmp_path):
    """Judge S3-J7: with stdout piped (a log file, CI), the session's own lines are flushed as
    they are printed, not when the process exits. The session runs in a subprocess with the fake
    host and the default say; its runner marks a file and sleeps 2 s; the "up" line must be
    readable within 1 s of that mark, while the session still runs. PYTHONUNBUFFERED is removed
    from the child's environment, so only the code's own flush can pass this."""
    import os
    import select
    import subprocess
    import sys
    import time

    marker = tmp_path / "sleeping"
    script = PIPED_SESSION.format(root=str(ROOT), lab=str(tmp_path / "lab"), marker=str(marker))
    env = {k: v for k, v in os.environ.items() if k != "PYTHONUNBUFFERED"}
    proc = subprocess.Popen(
        [sys.executable, "-c", script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env
    )
    assert proc.stdout is not None
    assert proc.stderr is not None
    try:
        deadline = time.monotonic() + 60
        while not marker.exists():
            assert proc.poll() is None, proc.stderr.read()
            assert time.monotonic() < deadline, "the runner never started"
            time.sleep(0.05)
        seen = b""
        until = time.monotonic() + 1.0
        while b"ollama 0.40.6 up on http://127.0.0.1:11434" not in seen:
            left = until - time.monotonic()
            assert left > 0, f"no 'up' line within 1 s of the runner starting: {seen!r}"
            ready, _, _ = select.select([proc.stdout], [], [], left)
            if ready:
                chunk = os.read(proc.stdout.fileno(), 65536)
                assert chunk, f"the pipe closed before the 'up' line: {seen!r}"
                seen += chunk
        assert proc.poll() is None, "the line came only when the session ended"
        assert b"memory: " in seen
    finally:
        proc.wait(timeout=60)
    assert proc.returncode == 0


def test_the_makefile_session_targets_run_unbuffered():
    """Judge S3-J7: the session targets also set PYTHONUNBUFFERED=1, so the child commands'
    output (the live test, the eval) interleaves with the session's lines in a log."""
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    for target in ("ollama-up", "ollama-down", "ollama-status", "eval-local"):
        body = makefile.split(f"\n{target}:", 1)[1].split("\n\n", 1)[0]
        assert "PYTHONUNBUFFERED=1 " in body, target


# ---------------------------------------------------------------- fix round 3 (judge S3-J8 to J11)

DOUBLE_SIGNAL_SESSION = """
import json, signal, sys, time
from pathlib import Path
sys.path.insert(0, {root!r})
from tests.unit.test_ollama_session import FakeHost, local_config, pulled
from raglab.runtime import ollama
signal.signal(signal.SIGINT, signal.default_int_handler)  # as in a terminal
lab = Path({lab!r})
pulled(lab)


class SlowUnloadHost(FakeHost):
    def http(self, method, url, body=None):
        if self.running and url.endswith("/api/ps"):
            return {{"models": [{{"name": "nemotron-3.5-lightning:30b-a3b-mlx"}}]}}
        if self.running and url.endswith("/api/generate"):
            time.sleep(2)  # the model unloading
            return {{}}
        return super().http(method, url, body)


host = SlowUnloadHost(tmp=lab)
said = []
session = ollama.session_for(local_config(), lab, host)
session.say = said.append
marker = Path({marker!r})
def runner(command):
    marker.write_text("running", encoding="utf-8")
    time.sleep(60)
    return 0
try:
    session.run([["first"]], runner)
finally:
    out = {{
        "signals": host.signals,
        "running": host.running,
        "said": said,
        "pid_file": (lab / "runs/tmp/ollama/serve.pid").exists(),
    }}
    Path({result!r}).write_text(json.dumps(out), encoding="utf-8")
"""


def _wait_for(path: Path, proc, seconds: float = 60) -> None:
    import time

    deadline = time.monotonic() + seconds
    while not path.exists() or not path.read_text(encoding="utf-8").strip():
        assert proc.poll() is None, f"the session ended early ({proc.returncode})"
        assert time.monotonic() < deadline, f"{path.name} never appeared"
        time.sleep(0.05)


@pytest.mark.parametrize(
    ("first", "second"),
    [("SIGTERM", "SIGTERM"), ("SIGINT", "SIGINT"), ("SIGHUP", "SIGHUP")],
)
def test_a_second_signal_during_the_stop_does_not_abort_it(tmp_path, first, second):
    """Judge S3-J8: a session subprocess (the fake host, an unload that takes 2 s) gets a signal
    while its runner sleeps, then a second one 1 s later, inside the stop. The stop runs to the
    postcheck: the server got SIGTERM and is not running, the pid file is gone, and the second
    signal was only said."""
    import os
    import subprocess
    import sys
    import time

    marker, result = tmp_path / "running", tmp_path / "result.json"
    script = DOUBLE_SIGNAL_SESSION.format(
        root=str(ROOT), lab=str(tmp_path / "lab"), marker=str(marker), result=str(result)
    )
    proc = subprocess.Popen(
        [sys.executable, "-c", script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    try:
        _wait_for(marker, proc)
        time.sleep(0.3)
        os.kill(proc.pid, getattr(signal, first))
        time.sleep(1.0)
        os.kill(proc.pid, getattr(signal, second))
    finally:
        proc.wait(timeout=60)
    out = json.loads(result.read_text(encoding="utf-8"))
    assert signal.SIGTERM.value in out["signals"], out
    assert out["running"] is False, out
    assert "postcheck passed: port closed, no ollama process, no model loaded" in out["said"]
    assert out["pid_file"] is False
    assert any("the stop continues" in line for line in out["said"]), out["said"]


GRANDCHILD = (
    "import subprocess, sys\n"
    "child = subprocess.Popen(['sleep', '30'])\n"
    "open(sys.argv[1], 'w').write(str(child.pid))\n"
    "child.wait()\n"
)
TREE_SESSION = """
import signal, sys
from pathlib import Path
sys.path.insert(0, {root!r})
from tests.unit.test_ollama_session import FakeHost, local_config, pulled
from raglab.runtime import ollama
signal.signal(signal.SIGINT, signal.default_int_handler)  # as in a terminal
lab = Path({lab!r})
pulled(lab)
session = ollama.session_for(local_config(), lab, FakeHost(tmp=lab))
command = [sys.executable, "-c", {grandchild!r}, {pids!r}]
sys.exit(session.run([command], ollama.run_command))
"""


@pytest.mark.parametrize("sig", ["SIGTERM", "SIGINT"])
def test_a_signal_to_the_session_ends_the_commands_whole_process_tree(tmp_path, sig):
    """Judge S3-J11: a session command that starts a grandchild (`sleep 30`); a SIGTERM (a kill
    of the session alone) or a SIGINT (Ctrl-C reaches the session, not the command, which runs
    in its own process group) to the session ends the command's whole group: no sleep
    survives."""
    import contextlib
    import os
    import subprocess
    import sys
    import time

    pids = tmp_path / "sleep.pid"
    script = TREE_SESSION.format(
        root=str(ROOT), lab=str(tmp_path / "lab"), grandchild=GRANDCHILD, pids=str(pids)
    )
    proc = subprocess.Popen(
        [sys.executable, "-c", script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    sleep_pid = None
    try:
        _wait_for(pids, proc)
        sleep_pid = int(pids.read_text(encoding="utf-8"))
        os.kill(proc.pid, getattr(signal, sig))
        proc.wait(timeout=60)
        deadline = time.monotonic() + 5
        alive = True
        while alive and time.monotonic() < deadline:
            try:
                os.kill(sleep_pid, 0)
            except ProcessLookupError:
                alive = False
            else:
                time.sleep(0.1)
        assert not alive, f"the command's grandchild sleep {sleep_pid} survived the session"
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        if sleep_pid is not None:
            with contextlib.suppress(ProcessLookupError):
                os.kill(sleep_pid, signal.SIGKILL)
