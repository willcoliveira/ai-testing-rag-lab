"""A local Ollama server for one session, never a resident service (S3, AC15; docs/LOCAL-MODEL.md).

`up` runs `ollama serve` as a child process of this project, in its own process group, with its
pid and log in runs/tmp/ollama/ (gitignored) and the session settings of the config's [ollama]
table as its environment: loopback only, one model loaded at a time, one request at a time, a
short keep-alive and a context window far below the model's default. `down` unloads every loaded
model, stops the server (SIGTERM to its group, SIGKILL after a grace period), and runs the
postcheck. `session` is up, the given commands, then down and the postcheck, in a finally block:
on success, on failure, on Ctrl-C, and on SIGTERM and SIGHUP, which the session turns into
SystemExit. A SIGKILL cannot be caught: the pid file then makes the next `up` refuse until
`make ollama-down` stops the server.

Usage guards (each refusal names its reason, and nothing is started):
- the ollama binary is on PATH;
- no launchd job or brew service for Ollama is registered (a resident server would outlive the
  session);
- the server's port is free, unless this project's own pid file names the process holding it;
- the pinned model is pulled, and the memory the OS reports available is at least the model's
  size on disk plus the config's memory_margin_gb;
- once up, the server's version is at least MIN_VERSION (0.40.6: the first that runs the pinned
  model; 0.40.4 refused it with "requires a newer version of Ollama").

The postcheck fails loudly unless the port is closed and no ollama executable is running (a
loaded model lives in a runner process, so none means no model is resident). The per-request
timeout, the max-tokens cap and the run's wall-clock cap are the generator's and the generation
suite's (raglab.adapters.openai_compat, raglab.evals.generation).

The OS reads go through `Host`, so the tests replace them with fakes.
"""

import contextlib
import json
import os
import platform
import re
import shutil
import signal
import socket
import subprocess  # nosec B404
import time
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

from raglab.evals.config import GenerationConfig, OllamaSettings

MIN_VERSION = (0, 40, 6)
STATE_DIR = "runs/tmp/ollama"
GIB = 1 << 30


class SessionError(RuntimeError):
    """A guard refused the session, or the server did not start or stop as it must."""


def _run(command: Sequence[str]) -> str:
    """The stdout of a fixed system command (no shell); empty when it is missing or fails."""
    executable = shutil.which(command[0])
    if executable is None:
        return ""
    # fixed arguments chosen in this module, no shell, no user input
    done = subprocess.run(  # noqa: S603  # nosec B603
        [executable, *command[1:]], capture_output=True, text=True, check=False, timeout=30
    )
    return done.stdout if done.returncode == 0 else ""


@dataclass
class Host:
    """The OS reads and the process start of a session. Every method is replaced in the tests."""

    def which_ollama(self) -> str | None:
        return shutil.which("ollama")

    def available_memory_bytes(self) -> int:
        """Memory the OS can hand to a new process now. macOS: free, inactive and speculative
        pages from vm_stat (purgeable pages are left out: they can be counted in the others too,
        so the guard errs low); Linux: MemAvailable from /proc/meminfo."""
        if platform.system() == "Darwin":
            text = _run(["vm_stat"])
            size = re.search(r"page size of (\d+) bytes", text)
            pages = {
                name: int(value)
                for name, value in re.findall(r"^Pages (\w+):\s+(\d+)\.", text, flags=re.M)
            }
            if not size or "free" not in pages:
                raise SessionError("cannot read the available memory from vm_stat")
            keep = ("free", "inactive", "speculative")
            return int(size.group(1)) * sum(pages.get(name, 0) for name in keep)
        meminfo = Path("/proc/meminfo").read_text(encoding="utf-8")
        found = re.search(r"^MemAvailable:\s+(\d+) kB", meminfo, flags=re.M)
        if not found:
            raise SessionError("cannot read MemAvailable from /proc/meminfo")
        return int(found.group(1)) * 1024

    def registered_services(self) -> list[str]:
        """launchd jobs and LaunchAgent or LaunchDaemon plists for Ollama (brew services writes
        homebrew.mxcl.ollama.plist)."""
        found = [
            line.split()[-1]
            for line in _run(["launchctl", "list"]).splitlines()
            if "ollama" in line.lower()
        ]
        for directory in (
            Path.home() / "Library" / "LaunchAgents",
            Path("/Library/LaunchAgents"),
            Path("/Library/LaunchDaemons"),
        ):
            if directory.is_dir():
                found += [str(p) for p in directory.glob("*ollama*")]
        return sorted(set(found))

    def port_open(self, host: str, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            return sock.connect_ex((host, port)) == 0

    def ollama_processes(self) -> list[str]:
        """Every running ollama executable (the server and its runners), as 'pid command'. A
        process is matched by its executable's name, not by any argument that names ollama (an
        editor on the config, a tail of the log, this session's own raglab command: judge S3-J5),
        so the check does not rely on BSD pgrep leaving out the caller's ancestors."""
        found: list[str] = []
        for line in _run(["pgrep", "-fl", "ollama"]).splitlines():
            parts = line.split()
            if len(parts) >= 2 and Path(parts[1]).name == "ollama":
                found.append(line.strip())
        return found

    def pid_alive(self, pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def start(self, command: list[str], env: dict[str, str], log: Path) -> int:
        """Start the server in its own process group, its output to log; its pid."""
        with log.open("ab") as out:
            # the ollama binary found on PATH, fixed arguments, no shell
            process = subprocess.Popen(  # noqa: S603  # nosec B603
                command, env=env, stdout=out, stderr=subprocess.STDOUT, start_new_session=True
            )
        return process.pid

    def signal_group(self, pid: int, sig: int) -> None:
        """Signal the server's process group; where macOS refuses that (EPERM, seen with the MLX
        runner on Ollama 0.40.6), signal the server itself, which stops its runner."""
        try:
            os.killpg(pid, sig)
        except ProcessLookupError:
            return
        except PermissionError:
            with contextlib.suppress(ProcessLookupError):
                os.kill(pid, sig)

    def http(self, method: str, url: str, body: dict[str, object] | None = None) -> object:
        if not url.startswith("http://127.0.0.1:"):
            raise SessionError(f"the session only talks to its loopback server, not {url}")
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(  # noqa: S310  # loopback only, checked above
            url, data=data, method=method, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310  # nosec B310
            return json.loads(response.read() or b"null")

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)

    def models_dir(self) -> Path:
        configured = os.environ.get("OLLAMA_MODELS")
        return Path(configured) if configured else Path.home() / ".ollama" / "models"


@dataclass
class Session:
    """One config's server: its settings, the model and where its pid and log live."""

    settings: OllamaSettings
    model: str
    root: Path
    host: Host = field(default_factory=Host)
    say: Callable[[str], None] = print

    @property
    def address(self) -> tuple[str, int]:
        name, _, port = self.settings.host.partition(":")
        return ("127.0.0.1" if name == "localhost" else name), int(port)

    @property
    def base_url(self) -> str:
        name, port = self.address
        return f"http://{name}:{port}"

    @property
    def state(self) -> Path:
        return self.root / STATE_DIR

    @property
    def pid_file(self) -> Path:
        return self.state / "serve.pid"

    def environment(self) -> dict[str, str]:
        """The server's environment: the session settings and nothing else of this shell but
        PATH and HOME (and OLLAMA_MODELS when it is set)."""
        env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": os.environ.get("HOME", str(Path.home())),
            "OLLAMA_HOST": self.settings.host,
            "OLLAMA_KEEP_ALIVE": self.settings.keep_alive,
            "OLLAMA_MAX_LOADED_MODELS": str(self.settings.max_loaded_models),
            "OLLAMA_NUM_PARALLEL": str(self.settings.num_parallel),
            "OLLAMA_CONTEXT_LENGTH": str(self.settings.context_length),
        }
        if "OLLAMA_MODELS" in os.environ:
            env["OLLAMA_MODELS"] = os.environ["OLLAMA_MODELS"]
        return env

    def our_pid(self) -> int | None:
        if not self.pid_file.is_file():
            return None
        try:
            pid = int(self.pid_file.read_text(encoding="utf-8").strip())
        except ValueError:
            return None
        return pid if self.host.pid_alive(pid) else None

    def model_size_bytes(self) -> int:
        """The pinned model's size on disk, from its manifest under the models directory."""
        name, _, tag = self.model.partition(":")
        repo = name if "/" in name else f"library/{name}"
        manifest = (
            self.host.models_dir() / "manifests" / "registry.ollama.ai" / repo / (tag or "latest")
        )
        if not manifest.is_file():
            raise SessionError(f"{self.model} is not pulled (no manifest at {manifest})")
        data = json.loads(manifest.read_text(encoding="utf-8"))
        layers = [*data.get("layers", []), data.get("config", {})]
        return sum(int(layer.get("size", 0)) for layer in layers)

    def preflight(self) -> list[str]:
        """Every reason this session may not start; [] when it may."""
        problems: list[str] = []
        if self.host.which_ollama() is None:
            problems.append("the ollama binary is not on PATH")
        if services := self.host.registered_services():
            problems.append(
                f"an Ollama service is registered ({', '.join(services)}): a resident server "
                "would outlive the session; remove it (brew services stop ollama, launchctl)"
            )
        name, port = self.address
        if self.host.port_open(name, port) and self.our_pid() is None:
            problems.append(
                f"{name}:{port} is already held by a process this project did not start"
            )
        try:
            size = self.model_size_bytes()
        except SessionError as error:
            problems.append(str(error))
        else:
            needed = size + int(self.settings.memory_margin_gb * GIB)
            available = self.host.available_memory_bytes()
            self.say(
                f"memory: {available / GIB:.1f} GiB available; the model needs {size / GIB:.1f} "
                f"GiB plus a margin of {self.settings.memory_margin_gb:g} GiB"
            )
            if available < needed:
                problems.append(
                    f"not enough memory: {available / GIB:.1f} GiB available, "
                    f"{needed / GIB:.1f} GiB needed (model {size / GIB:.1f} GiB + margin "
                    f"{self.settings.memory_margin_gb:g} GiB)"
                )
        return problems

    def up(self, wait_s: float = 60) -> int:
        """Start the server after the preflight; its pid. Refuses with every problem found."""
        if (pid := self.our_pid()) is not None:
            raise SessionError(
                f"this project's server is already running (pid {pid}): make ollama-down"
            )
        if problems := self.preflight():
            raise SessionError("the session may not start:\n- " + "\n- ".join(problems))
        self.state.mkdir(parents=True, exist_ok=True)
        binary = self.host.which_ollama() or "ollama"
        pid = self.host.start([binary, "serve"], self.environment(), self.state / "serve.log")
        self.pid_file.write_text(f"{pid}\n", encoding="utf-8")
        deadline = wait_s
        while deadline > 0:
            try:
                version = self.host.http("GET", f"{self.base_url}/api/version")
            except (OSError, ValueError):
                self.host.sleep(0.5)
                deadline -= 0.5
                continue
            found = str(_field(version, "version") or "")
            if parse_version(found) < MIN_VERSION:
                self.down()
                raise SessionError(
                    f"Ollama {found or '?'} is older than {'.'.join(map(str, MIN_VERSION))}, the "
                    "first version that runs the pinned model"
                )
            self.say(
                f"ollama {found} up on {self.base_url} (pid {pid}, log {self.state / 'serve.log'})"
            )
            return pid
        self.down()
        raise SessionError(
            f"the server did not answer within {wait_s:g} s; see {self.state / 'serve.log'}"
        )

    def unload(self) -> list[str]:
        """Ask the server to unload every loaded model now (keep_alive 0); the names unloaded."""
        try:
            loaded = self.host.http("GET", f"{self.base_url}/api/ps")
        except (OSError, ValueError):
            return []
        models = _field(loaded, "models")
        names = [
            str(_field(m, "name"))
            for m in (cast(list[object], models) if isinstance(models, list) else [])
        ]
        for name in names:
            try:
                self.host.http(
                    "POST", f"{self.base_url}/api/generate", {"model": name, "keep_alive": 0}
                )
            except (OSError, ValueError) as error:
                self.say(f"unloading {name} failed: {error}")
        return names

    def down(self, grace_s: float = 15) -> list[str]:
        """Unload the models, stop this project's server and run the postcheck; its problems."""
        pid = self.our_pid()
        if pid is not None:
            if names := self.unload():
                self.say(f"unloaded {', '.join(names)}")
            self.host.signal_group(pid, signal.SIGTERM)
            waited = 0.0
            while self.host.pid_alive(pid) and waited < grace_s:
                self.host.sleep(0.5)
                waited += 0.5
            if self.host.pid_alive(pid):
                self.host.signal_group(pid, signal.SIGKILL)
                self.host.sleep(1)
            self.say(f"stopped the server (pid {pid})")
        self.pid_file.unlink(missing_ok=True)
        return self.postcheck()

    def postcheck(self) -> list[str]:
        """[] when the port is closed and no ollama process runs (so no model is resident)."""
        problems: list[str] = []
        name, port = self.address
        if self.host.port_open(name, port):
            problems.append(f"{name}:{port} is still open")
        if processes := self.host.ollama_processes():
            problems.append(f"ollama processes still run: {processes}")
        return problems

    def status(self) -> dict[str, object]:
        name, port = self.address
        loaded: object = None
        if self.host.port_open(name, port):
            try:
                loaded = self.host.http("GET", f"{self.base_url}/api/ps")
            except (OSError, ValueError):
                loaded = "unreadable"
        return {
            "pid": self.our_pid(),
            "port_open": self.host.port_open(name, port),
            "loaded": loaded,
            "processes": self.host.ollama_processes(),
            "services": self.host.registered_services(),
            "available_gib": round(self.host.available_memory_bytes() / GIB, 1),
        }

    def run(self, commands: Sequence[Sequence[str]], runner: Callable[[Sequence[str]], int]) -> int:
        """up, each command in turn (stopping at the first that fails), then down and the
        postcheck, in a finally block: on success, on failure, on Ctrl-C (SIGINT), on `kill`
        (SIGTERM) and on a closed terminal (SIGHUP), which are turned into SystemExit for the
        session's length (judge S3-J2). SIGKILL cannot be caught: the server then stays up until
        `make ollama-down`, and the pid file makes the next `up` refuse until then. The exit
        code: the first failing command's, else 1 when the postcheck fails, else 0."""
        code = 0
        problems: list[str] = []
        previous = _exit_on_signals()
        try:
            self.up()
        except BaseException:
            if self.our_pid() is not None:  # a signal while the server was starting
                self.down()
            _restore_signals(previous)
            raise
        try:
            for command in commands:
                self.say(f"session: {' '.join(command)}")
                code = runner(command)
                if code != 0:
                    break
        finally:
            problems = self.down()
            if problems:
                self.say("POSTCHECK FAILED: " + "; ".join(problems))
            else:
                self.say("postcheck passed: port closed, no ollama process, no model loaded")
            _restore_signals(previous)
        return code or (1 if problems else 0)


def _field(data: object, name: str) -> object:
    """data[name] when data is a JSON object, else None."""
    if not isinstance(data, dict):
        return None
    return cast(dict[str, object], data).get(name)


# the signals a session turns into SystemExit, so its finally block stops the server
TRAPPED = (signal.SIGTERM, signal.SIGHUP)


def _exit_on_signals() -> dict[int, object]:
    """Install handlers that raise SystemExit(128 + signal) and return the previous ones (none
    outside the main thread, where Python cannot install them)."""

    def leave(number: int, _frame: object) -> None:
        raise SystemExit(128 + number)

    previous: dict[int, object] = {}
    try:
        for sig in TRAPPED:
            previous[sig] = signal.signal(sig, leave)
    except ValueError:  # not the main thread
        return previous
    return previous


def _restore_signals(previous: dict[int, object]) -> None:
    for sig, handler in previous.items():
        signal.signal(sig, cast(signal.Handlers, handler))


def parse_version(text: str) -> tuple[int, ...]:
    """'0.40.6' -> (0, 40, 6); anything else -> ()."""
    found = re.match(r"^(\d+)\.(\d+)\.(\d+)", text.strip())
    return tuple(int(x) for x in found.groups()) if found else ()


def session_for(config: GenerationConfig, root: Path, host: Host | None = None) -> Session:
    if config.ollama is None:
        raise SessionError(f"{config.path} has no [ollama] table: it does not run a local server")
    return Session(config.ollama, config.generator.model, root, host or Host())


def run_command(command: Sequence[str]) -> int:
    """A session command: run as given, no shell, offline for the model hub."""
    executable = shutil.which(command[0]) or command[0]
    env = {**os.environ, "HF_HUB_OFFLINE": "1"}
    # commands come from the Makefile's eval-local target, never from a request
    return subprocess.run([executable, *command[1:]], env=env, check=False).returncode  # noqa: S603  # nosec B603
