"""The k6 smoke against the perf stub (S9 OB7, OB9; docs/OBSERVABILITY.md): `make perf-smoke`, in
pr-fast's perf job and locally. Model-free: the perf stub answers, the embedder comes from its
cache, and everything binds the loopback interface only.

The steps, in order. Any failure makes the exit non-zero; whatever happens (an error, Ctrl-C,
SIGTERM or SIGHUP) the server and the collector are stopped and the postcheck runs.
0. k6 and the collector are fetched once into a cache (RAGLAB_TOOLS_DIR, default
   ~/.cache/raglab/tools), each archive's sha256 is checked against its pin on every use, and the
   binary is extracted from the checked archive for this run; the collector validates its three
   configurations. Nothing is installed system-wide.
1. The collector starts (deploy/otel/: the local pipeline to a file, and the Langfuse pipeline with
   a file standing in for Langfuse), with a pid file: a pid file left by a run that was killed
   makes the next start refuse.
2. `raglab serve --config config/perf.toml` starts with PERF_TEST_MODE=1 and RAGLAB_ENV=ci, tracing
   to the collector, content capture off.
3. perf/smoke.js runs (one user, a warm-up, a fixed count; every check must pass and no request
   fail; the median of /ask is gated once T is set); then a fixture span that carries every content
   key goes to the collector, for the Langfuse pipeline's check.
4. The server stops (SIGTERM: a graceful stop flushes its spans), then the collector (SIGTERM).
5. The collector's files: every /ask k6 sent has its trace with the five spans; the markers of the
   script's questions appear nowhere; no content key leaves through the Langfuse pipeline, while
   the fixture's keys reached the local file.
6. The postcheck: both ports closed, no server or collector process left, the pid file removed.
Last, the median, p90, p95, minimum and maximum of /ask are printed, and written to the job's step
summary when GITHUB_STEP_SUMMARY is set.

Usage: uv run python scripts/perf_smoke.py [--port 8791] [--otlp-port 4391] [--timeout 300]
"""

import argparse
import contextlib
import hashlib
import json
import os
import platform
import re
import signal
import socket
import subprocess  # nosec B404
import sys
import tarfile
import time
import urllib.error
import urllib.request
import zipfile
from collections.abc import Callable, Generator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "runs" / "tmp" / "perf"
OTEL = ROOT / "deploy" / "otel"
CONFIG = "config/perf.toml"
SCRIPT = "perf/smoke.js"
TOKEN = "demo"  # noqa: S105  # nosec B105  # lab: the public demo token of config/perf.toml
GRACE_S = 15
SERVER_EXIT = -signal.SIGTERM  # uvicorn re-raises SIGTERM after its graceful shutdown
MARKER = re.compile(r"perf-marker-\d+")
EMBEDDER = "BAAI/bge-small-en-v1.5"
SPANS = (
    "POST /ask",
    "raglab.ask",
    "retrieval policy-pack",
    f"embeddings {EMBEDDER}",
    "chat perf-stub",
)
# the content keys raglab defines (raglab.obs.names: CONTENT_KEYS and NEVER_SET); the fixture
# carries each of them, and the Langfuse pipeline must delete each one
CONTENT_KEYS = (
    "raglab.content.question",
    "raglab.content.answer",
    "gen_ai.input.messages",
    "gen_ai.output.messages",
    "gen_ai.system_instructions",
    "gen_ai.retrieval.query.text",
    "gen_ai.retrieval.documents",
)
FIXTURE_MARKER = "fixture-content-marker"
FIXTURE_TRACE = "5a" * 16


@dataclass(frozen=True)
class Archive:
    url: str
    sha256: str
    member: str  # the binary's path inside the archive


@dataclass(frozen=True)
class Tool:
    name: str
    version: str
    archives: Mapping[tuple[str, str], Archive]  # by (platform.system(), platform.machine())


# k6 v2.3.0 (published 2026-09-21), its k6-v2.3.0-checksums.txt
K6 = Tool(
    "k6",
    "2.3.0",
    {
        ("Linux", "x86_64"): Archive(
            "https://github.com/grafana/k6/releases/download/v2.3.0/k6-v2.3.0-linux-amd64.tar.gz",
            "39c3117b6af817592dcd0ce4242105c0a7af10948c2a425306f0be8f7a8a8ab1",
            "k6-v2.3.0-linux-amd64/k6",
        ),
        ("Darwin", "arm64"): Archive(
            "https://github.com/grafana/k6/releases/download/v2.3.0/k6-v2.3.0-macos-arm64.zip",
            "b2417a3038edc5fe81dc178a889237724b595c5c9cfed875822008e46e862c7d",
            "k6-v2.3.0-macos-arm64/k6",
        ),
    },
)
# the OpenTelemetry Collector, core distribution otelcol v0.162.0 (published 2026-09-29): the
# smallest official distribution whose `components` list has the OTLP receiver, the attributes
# processor and the file exporter; its .sha256 files
_COLLECTOR = (
    "https://github.com/open-telemetry/opentelemetry-collector-releases/releases/download/"
    "v0.162.0/otelcol_0.162.0_{}.tar.gz"
)
OTELCOL = Tool(
    "otelcol",
    "0.162.0",
    {
        ("Linux", "x86_64"): Archive(
            _COLLECTOR.format("linux_amd64"),
            "f99929987a915d3c6b2c9b15bc4938c5cea903a37a3f49e478024a0fa0772339",
            "otelcol",
        ),
        ("Darwin", "arm64"): Archive(
            _COLLECTOR.format("darwin_arm64"),
            "53de34c02913f54aa240861e0febf67a6839bc8ecf1bfab83a8ae7d355d30674",
            "otelcol",
        ),
    },
)


class SmokeError(RuntimeError):
    """A step failed; the message says which and why."""


class Interrupted(BaseException):
    """SIGTERM or SIGHUP: stop everything, as Ctrl-C does."""


def cache_dir() -> Path:
    return Path(os.environ.get("RAGLAB_TOOLS_DIR", Path.home() / ".cache" / "raglab" / "tools"))


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def archive_for(tool: Tool) -> Archive:
    key = (platform.system(), platform.machine())
    if key not in tool.archives:
        raise SmokeError(f"{tool.name} {tool.version}: no pinned archive for {key}")
    return tool.archives[key]


def download(url: str, target: Path) -> None:
    if not url.startswith("https://github.com/"):
        raise SmokeError(f"refusing to download {url}: release archives come from github.com")
    # a fixed https URL on github.com, checked above
    with urllib.request.urlopen(url, timeout=120) as response:  # noqa: S310  # nosec B310
        target.write_bytes(response.read())


def fetch(tool: Tool, cache: Path, bin_dir: Path) -> Path:
    """The tool's binary, extracted for this run from its cached archive after the archive's
    sha256 matched the pin. A missing archive is downloaded once; an archive whose sum differs is
    refused, never used and never replaced silently."""
    archive = archive_for(tool)
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / archive.url.rsplit("/", 1)[1]
    if not path.exists():
        partial = path.with_name(path.name + ".partial")
        download(archive.url, partial)
        if sha256_of(partial) != archive.sha256:
            seen = sha256_of(partial)
            partial.unlink()
            raise SmokeError(
                f"{tool.name} {tool.version}: the download's sha256 is {seen}, not the pinned "
                f"{archive.sha256}; nothing was kept"
            )
        partial.replace(path)
    seen = sha256_of(path)
    if seen != archive.sha256:
        raise SmokeError(
            f"{tool.name} {tool.version}: {path} has sha256 {seen}, not the pinned "
            f"{archive.sha256}; it is not used (delete it to fetch the archive again)"
        )
    if path.name.endswith(".zip"):
        with zipfile.ZipFile(path) as bundle:
            data = bundle.read(archive.member)
    else:
        with tarfile.open(path, "r:gz") as bundle:
            member = bundle.extractfile(archive.member)
            if member is None:
                raise SmokeError(f"{path} has no file {archive.member}")
            data = member.read()
    bin_dir.mkdir(parents=True, exist_ok=True)
    binary = bin_dir / tool.name
    binary.write_bytes(data)
    binary.chmod(0o755)
    print(f"ok   {tool.name} {tool.version}: {path.name}, sha256 {seen} (the pin)", flush=True)
    return binary


def port_open(port: int) -> bool:
    with socket.socket() as probe:
        probe.settimeout(1)
        return probe.connect_ex(("127.0.0.1", port)) == 0


def collector_env(port: int, traces: Path, stand_in: Path) -> dict[str, str]:
    """A minimal environment: the port, the two files, and placeholders for the Langfuse
    exporter, which no pipeline uses here (a loopback discard address; nothing is sent)."""
    return {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "RAGLAB_OTELCOL_PORT": str(port),
        "RAGLAB_OTELCOL_TRACES": str(traces),
        "RAGLAB_OTELCOL_LANGFUSE_FILE": str(stand_in),
        "LANGFUSE_OTEL_ENDPOINT": "http://127.0.0.1:9/api/public/otel",
        "LANGFUSE_BASIC_AUTH": "placeholder",
    }


CONFIGS = ("collector.yaml", "langfuse.yaml", "langfuse-stand-in.yaml")


def config_args(names: tuple[str, ...] = CONFIGS) -> list[str]:
    return [arg for name in names for arg in ("--config", str(OTEL / name))]


def validate(otelcol: Path, env: Mapping[str, str]) -> None:
    """`validate` on each configuration the collector can run with: the local pipeline alone,
    with the Langfuse pipeline, and with its stand-in."""
    for names in (CONFIGS[:1], CONFIGS[:2], CONFIGS):
        done = subprocess.run(  # nosec B603  # the checked binary, fixed arguments
            [str(otelcol), "validate", *config_args(names)],
            env=dict(env),
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        if done.returncode != 0:
            raise SmokeError(f"otelcol validate {' + '.join(names)}: {done.stderr.strip()}")
        print(f"ok   otelcol validate: {' + '.join(names)}", flush=True)


def wait_for(
    name: str, ready: Callable[[], bool], process: subprocess.Popen[bytes], timeout: float
):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise SmokeError(f"{name} exited with {process.returncode} before it was ready")
        if ready():
            return
        time.sleep(0.5)
    raise SmokeError(f"{name} was not ready within {timeout:g} s")


def healthz(base: str) -> bool:
    try:
        # loopback only: base is http://127.0.0.1:<port>
        with urllib.request.urlopen(base + "/healthz", timeout=5) as response:  # noqa: S310  # nosec B310
            return response.status == 200
    except (urllib.error.URLError, ConnectionError, OSError):
        return False


def stop(process: subprocess.Popen[bytes]) -> int:
    """SIGTERM to the process group, SIGKILL after GRACE_S; the exit code."""
    with contextlib.suppress(ProcessLookupError):
        os.killpg(process.pid, signal.SIGTERM)
    try:
        return process.wait(timeout=GRACE_S)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
        return process.wait()


def fixture_span() -> bytes:
    """One OTLP/JSON span of raglab's pipeline that carries every content key, for the Langfuse
    pipeline's check."""
    now = time.time_ns()
    attributes = [
        {"key": key, "value": {"stringValue": f"{FIXTURE_MARKER} {key}"}} for key in CONTENT_KEYS
    ]
    attributes.append({"key": "raglab.status", "value": {"stringValue": "ok"}})
    span = {
        "traceId": FIXTURE_TRACE,
        "spanId": "5b" * 8,
        "name": "raglab.ask",
        "kind": 1,
        "startTimeUnixNano": str(now - 1_000_000),
        "endTimeUnixNano": str(now),
        "attributes": attributes,
    }
    body = {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [{"key": "service.name", "value": {"stringValue": "raglab"}}]
                },
                "scopeSpans": [{"scope": {"name": "raglab"}, "spans": [span]}],
            }
        ]
    }
    return json.dumps(body).encode()


def send_fixture(port: int) -> None:
    request = urllib.request.Request(  # loopback only
        f"http://127.0.0.1:{port}/v1/traces",
        data=fixture_span(),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310  # nosec B310
        if response.status != 200:
            raise SmokeError(f"the collector answered the fixture span with {response.status}")


@dataclass(frozen=True)
class SpanRecord:
    trace: str
    name: str
    attributes: dict[str, object]


def read_spans(path: Path) -> list[SpanRecord]:
    """Every span in a file the collector's file exporter wrote (one OTLP/JSON request a line)."""
    spans: list[SpanRecord] = []
    if not path.exists():
        return spans
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        data = cast(dict[str, object], json.loads(line))
        for resource in cast(list[dict[str, object]], data.get("resourceSpans", [])):
            for scope in cast(list[dict[str, object]], resource.get("scopeSpans", [])):
                for span in cast(list[dict[str, object]], scope.get("spans", [])):
                    attributes = {
                        str(a["key"]): a.get("value")
                        for a in cast(list[dict[str, object]], span.get("attributes", []))
                    }
                    spans.append(SpanRecord(str(span["traceId"]), str(span["name"]), attributes))
    return spans


def check_traces(traces: Path, stand_in: Path, sent: int, markers: list[str]) -> list[str]:
    """Step 5: what is wrong with the collector's files (empty when nothing is)."""
    problems: list[str] = []
    local = read_spans(traces)
    by_trace: dict[str, list[str]] = {}
    for span in local:
        by_trace.setdefault(span.trace, []).append(span.name)
    asks = {trace: names for trace, names in by_trace.items() if "POST /ask" in names}
    if len(asks) != sent:
        problems.append(f"{len(asks)} traces of POST /ask in {traces.name}, for {sent} requests")
    incomplete = [t for t, names in asks.items() if sorted(names) != sorted(SPANS)]
    if incomplete:
        problems.append(
            f"{len(incomplete)} traces lack a span of {list(SPANS)} (one: "
            f"{sorted(asks[incomplete[0]])})"
        )
    for path in (traces, stand_in):
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        found = sorted({m for m in markers if m in text})
        if found:
            problems.append(f"{path.name} holds the questions' markers {found}")
    smoke = [s for s in local if s.trace != FIXTURE_TRACE]
    leaked = sorted({k for s in smoke for k in s.attributes if k in CONTENT_KEYS})
    if leaked:
        problems.append(f"{traces.name}: the smoke's spans carry content keys {leaked}")
    fixture = [s for s in local if s.trace == FIXTURE_TRACE]
    if not fixture or set(CONTENT_KEYS) - set(fixture[0].attributes):
        problems.append(f"the fixture span did not reach {traces.name} with its content keys")
    stood_in = read_spans(stand_in)
    if not any(s.trace == FIXTURE_TRACE for s in stood_in):
        problems.append(f"the fixture span did not pass the Langfuse pipeline ({stand_in.name})")
    if not any(s.name == "POST /ask" for s in stood_in):
        problems.append(f"no trace of the smoke passed the Langfuse pipeline ({stand_in.name})")
    kept = sorted({k for s in stood_in for k in s.attributes if k in CONTENT_KEYS})
    if kept or (stand_in.exists() and FIXTURE_MARKER in stand_in.read_text(encoding="utf-8")):
        problems.append(f"the Langfuse pipeline let content keys through: {kept}")
    return problems


def postcheck(
    processes: Mapping[str, subprocess.Popen[bytes] | None],
    ports: Mapping[str, int],
    pid_file: Path,
) -> list[str]:
    """Step 6: both ports closed, no process left, the pid file removed."""
    problems = [
        f"the {name}'s port {port} still answers" for name, port in ports.items() if port_open(port)
    ]
    for name, process in processes.items():
        if process is None:
            continue
        if process.poll() is None:
            problems.append(f"the {name} (pid {process.pid}) is still running")
        else:
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.kill(process.pid, 0)
                problems.append(f"a process with the {name}'s pid {process.pid} still exists")
    if pid_file.exists():
        problems.append(f"{pid_file.relative_to(ROOT)} was not removed")
    return problems


def median_report(summary: Path) -> dict[str, float]:
    """The ask_duration trend's statistics from k6's summary export (milliseconds)."""
    data = cast(dict[str, object], json.loads(summary.read_text(encoding="utf-8")))
    metrics = cast(dict[str, dict[str, object]], data["metrics"])
    trend = metrics["ask_duration"]
    values = cast(dict[str, object], trend.get("values", trend))
    return {key: float(cast(float, values[key])) for key in ("med", "p(90)", "p(95)", "min", "max")}


def requests_sent(summary: Path) -> int:
    data = cast(dict[str, object], json.loads(summary.read_text(encoding="utf-8")))
    metric = cast(dict[str, dict[str, object]], data["metrics"])["http_reqs"]
    return int(cast(int, cast(dict[str, object], metric.get("values", metric))["count"]))


def script_constant(name: str) -> str:
    """A `const NAME = value;` line of perf/smoke.js, as written."""
    text = (ROOT / SCRIPT).read_text(encoding="utf-8")
    found = re.search(rf"^const {name} = (\w+);$", text, flags=re.M)
    if found is None:
        raise SmokeError(f"{SCRIPT} has no line `const {name} = ...;`")
    return found.group(1)


def threshold() -> str:
    """The script's T as written: a number of milliseconds, or "not set"."""
    value = script_constant("MEDIAN_THRESHOLD_MS")
    return "not set" if value == "null" else f"{value} ms"


def report(stats: Mapping[str, float], sent: int) -> str:
    gated = script_constant("COUNT")
    line = (
        f"perf-smoke: /ask median {stats['med']:.2f} ms, p90 {stats['p(90)']:.2f} ms, p95 "
        f"{stats['p(95)']:.2f} ms, min {stats['min']:.2f} ms, max {stats['max']:.2f} ms, over the "
        f"{gated} gated requests ({sent} sent with the warm-up); the median's threshold T: "
        f"{threshold()}"
    )
    print(line, flush=True)
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file:
        table = (
            "### k6 smoke: /ask against the perf stub\n\n"
            "| median | p90 | p95 | min | max | T (median) |\n|---|---|---|---|---|---|\n"
            f"| {stats['med']:.2f} ms | {stats['p(90)']:.2f} ms | {stats['p(95)']:.2f} ms | "
            f"{stats['min']:.2f} ms | {stats['max']:.2f} ms | {threshold()} |\n\n"
            "The median is gated once T is set (docs/THRESHOLDS.md); p90, p95, the minimum and "
            "the maximum are reported, never gated.\n"
        )
        with Path(summary_file).open("a", encoding="utf-8") as out:
            out.write(table)
    return line


@contextlib.contextmanager
def interruptible() -> Generator[None]:
    """SIGTERM and SIGHUP end the run as Ctrl-C does, so every finally block runs."""

    def handler(signum: int, frame: object) -> None:
        raise Interrupted(signum)

    previous = {sig: signal.signal(sig, handler) for sig in (signal.SIGTERM, signal.SIGHUP)}
    try:
        yield
    finally:
        for sig, old in previous.items():
            signal.signal(sig, old)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--port", type=int, default=8791, help="the server's loopback port")
    parser.add_argument(
        "--otlp-port", type=int, default=4391, help="the collector's OTLP/HTTP port"
    )
    parser.add_argument("--timeout", type=float, default=300, help="the server's start, seconds")
    args = parser.parse_args(argv)
    base = f"http://127.0.0.1:{args.port}"
    traces, stand_in = WORK / "traces.jsonl", WORK / "langfuse-stand-in.jsonl"
    summary, pid_file = WORK / "k6-summary.json", WORK / "otelcol.pid"
    failures: list[str] = []
    processes: dict[str, subprocess.Popen[bytes] | None] = {"server": None, "collector": None}
    exits: dict[str, int] = {}
    stats: dict[str, float] | None = None
    sent = 0
    k6_ran = False  # steps 5 and the report read only what this run wrote, never an earlier run's
    with interruptible():
        try:
            if pid_file.exists():
                raise SmokeError(
                    f"{pid_file.relative_to(ROOT)} exists: a collector from an earlier run may "
                    f"still be running (pid {pid_file.read_text().strip()}); stop it, then delete "
                    "the file"
                )
            for name, port in (("server", args.port), ("collector", args.otlp_port)):
                if port_open(port):
                    raise SmokeError(f"port {port} for the {name} is already in use")
            WORK.mkdir(parents=True, exist_ok=True)
            for old in (traces, stand_in, summary):
                old.unlink(missing_ok=True)
            k6 = fetch(K6, cache_dir(), WORK / "bin")
            otelcol = fetch(OTELCOL, cache_dir(), WORK / "bin")
            env = collector_env(args.otlp_port, traces, stand_in)
            validate(otelcol, env)
            # step 1: the collector, its own process group, loopback only (deploy/otel/)
            collector = subprocess.Popen(  # nosec B603  # the checked binary, fixed arguments
                [str(otelcol), *config_args()], env=env, start_new_session=True
            )
            processes["collector"] = collector
            pid_file.write_text(f"{collector.pid}\n", encoding="utf-8")
            wait_for("the collector", lambda: port_open(args.otlp_port), collector, 60)
            print(f"ok   1 the collector listens on 127.0.0.1:{args.otlp_port}", flush=True)
            # step 2: the server, the perf stub, tracing to the collector, content off
            server_env = {k: v for k, v in os.environ.items() if k != "RAGLAB_TRACE_CONTENT"}
            server_env |= {
                "PERF_TEST_MODE": "1",
                "RAGLAB_ENV": "ci",
                "RAGLAB_OTLP_ENDPOINT": f"http://127.0.0.1:{args.otlp_port}",
                "HF_HUB_OFFLINE": "1",
            }
            command = [sys.executable, "-m", "raglab", "serve", "--config", CONFIG]
            server = subprocess.Popen(  # nosec B603  # our own CLI, fixed arguments, no shell
                [*command, "--port", str(args.port)],
                cwd=ROOT,
                env=server_env,
                start_new_session=True,
            )
            processes["server"] = server
            wait_for("the server", lambda: healthz(base), server, args.timeout)
            print(
                f"ok   2 the server answers on {base} (PERF_TEST_MODE=1, RAGLAB_ENV=ci)", flush=True
            )
            # step 3: k6, then the fixture span for the Langfuse pipeline's check
            k6_run = subprocess.run(  # nosec B603  # the checked binary, fixed arguments
                [
                    str(k6),
                    "run",
                    "--no-usage-report",
                    "--quiet",
                    "--include-system-env-vars=false",
                    "--summary-export",
                    str(summary),
                    "-e",
                    f"BASE_URL={base}",
                    "-e",
                    f"TOKEN={TOKEN}",
                    SCRIPT,
                ],
                cwd=ROOT,
                env={"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", "")},
                check=False,
            )
            k6_ran = True
            if k6_run.returncode != 0:
                failures.append(
                    f"3 k6 exited with {k6_run.returncode} (99: a threshold was crossed)"
                )
            else:
                print(
                    "ok   3 k6: every check passed, no request failed, the thresholds held",
                    flush=True,
                )
            send_fixture(args.otlp_port)
        except (SmokeError, OSError, urllib.error.URLError, subprocess.SubprocessError) as error:
            failures.append(str(error))
        except (KeyboardInterrupt, Interrupted) as error:
            failures.append(f"interrupted ({type(error).__name__} {error})")
        finally:
            # step 4: the server first (its spans are flushed to the collector), then the collector
            for name in ("server", "collector"):
                process = processes[name]
                if process is not None:
                    exits[name] = stop(process)
            if processes["collector"] is not None and processes["collector"].poll() is not None:
                pid_file.unlink(missing_ok=True)
    if "server" in exits and exits["server"] != SERVER_EXIT:
        failures.append(f"4 the server did not stop gracefully: exit {exits['server']}")
    if "collector" in exits and exits["collector"] != 0:
        failures.append(f"4 the collector did not stop cleanly: exit {exits['collector']}")
    if exits == {"server": SERVER_EXIT, "collector": 0}:
        print(
            f"ok   4 the server stopped gracefully on SIGTERM (exit {SERVER_EXIT}), then the "
            "collector (exit 0)",
            flush=True,
        )
    if k6_ran and summary.exists():
        sent = requests_sent(summary)
        stats = median_report(summary)
        markers = sorted(set(MARKER.findall((ROOT / SCRIPT).read_text(encoding="utf-8"))))
        problems = check_traces(traces, stand_in, sent, markers)
        failures += [f"5 {problem}" for problem in problems]
        if not problems:
            print(
                f"ok   5 the collector's files: {sent} traces of /ask with their five spans, no "
                "marker, no content key past the Langfuse pipeline",
                flush=True,
            )
    problems = postcheck(processes, {"server": args.port, "collector": args.otlp_port}, pid_file)
    failures += [f"6 {problem}" for problem in problems]
    if not problems:
        print(
            "ok   6 postcheck: both ports closed, no process left, the pid file removed", flush=True
        )
    if stats is not None:
        report(stats, sent)
    print(f"perf-smoke: {'failed: ' + '; '.join(failures) if failures else 'passed'}", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
