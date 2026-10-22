"""The API smoke test (S3 AC12): start `raglab serve` with config/fake.toml on 127.0.0.1, then
check /healthz, /version, an /ask answer and a no-tenant refusal, and stop the server whatever
happens; last, check that it stopped as a graceful shutdown on SIGTERM ends it (exit -15, judge
S3-J12). Offline: the fake model, the embedder from its cache (HF_HUB_OFFLINE=1), loopback only.
`make api-smoke` runs it, in `make check` and in pr-fast.

Usage: uv run python scripts/api_smoke.py [--port 8765] [--timeout 180]
"""

import argparse
import contextlib
import json
import os
import signal
import subprocess  # nosec B404
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parent.parent
CONFIG = "config/fake.toml"
TOKEN = "demo"  # noqa: S105  # nosec B105  # lab: the public demo token of config/fake.toml
QUESTION = "How many characters must a password have?"
# The server is stopped with SIGTERM to its process group. uvicorn's graceful shutdown on it ends
# with "Application shutdown complete", then raises the signal again with its default action, so
# the process ends by SIGTERM: -15 (on SIGINT it would exit 0). Any other exit fails the smoke
# (judge S3-J12): -6 is an abort, as onnxruntime 1.30.0 can give at exit on macOS, and -9 the
# SIGKILL after GRACE_S.
STOP = signal.SIGTERM
GRACEFUL_EXIT = -STOP
GRACE_S = 15


def call(base: str, method: str, path: str, body: object = None) -> tuple[int, dict[str, object]]:
    data = None if body is None else json.dumps(body).encode()
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {TOKEN}"}
    if not base.startswith("http://127.0.0.1:"):
        raise SystemExit(f"api-smoke talks to its loopback server only, not {base}")
    # loopback only, checked above
    request = urllib.request.Request(base + path, data=data, method=method, headers=headers)  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310  # nosec B310
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read() or b"{}")


def wait_until_up(base: str, server: subprocess.Popen[bytes], timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if server.poll() is not None:
            raise SystemExit(f"api-smoke: the server exited with {server.returncode}")
        try:
            if call(base, "GET", "/healthz")[0] == 200:
                return
        except (urllib.error.URLError, ConnectionError, OSError):
            pass
        time.sleep(1)
    raise SystemExit(f"api-smoke: no answer from {base}/healthz within {timeout:g} s")


def check(base: str) -> list[str]:
    failures: list[str] = []

    def expect(name: str, ok: bool, seen: object) -> None:
        print(f"{'ok  ' if ok else 'FAIL'} {name}: {seen}")
        if not ok:
            failures.append(name)

    code, body = call(base, "GET", "/healthz")
    expect("/healthz is 200 ok", (code, body) == (200, {"status": "ok"}), (code, body))
    code, body = call(base, "GET", "/version")
    expect(
        "/version names the prompt and the fake model",
        code == 200
        and body.get("prompt_version") == "answer-v2"
        and body.get("model") == "fake-echo"
        and body.get("provenance") == "fake",
        (code, body),
    )
    code, body = call(base, "POST", "/ask", {"tenant": "tenant-a", "question": QUESTION})
    cited = body.get("citations")
    count = len(cast(list[object], cited)) if isinstance(cited, list) else 0
    expect(
        "/ask answers with citations",
        code == 200 and body.get("status") == "ok" and count > 0,
        (code, body.get("status"), body.get("label"), count),
    )
    code, body = call(base, "POST", "/ask", {"question": QUESTION})
    expect(
        "/ask without a tenant is 403 refused",
        code == 403 and body.get("status") == "refused" and body.get("answer") == "",
        (code, body.get("status"), body.get("reason")),
    )
    return failures


def stop(server: subprocess.Popen[bytes]) -> int:
    """STOP to the server's process group, SIGKILL after GRACE_S; its exit code."""
    with contextlib.suppress(ProcessLookupError):  # it has exited already: its code says how
        os.killpg(server.pid, STOP)
    try:
        return server.wait(timeout=GRACE_S)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(server.pid, signal.SIGKILL)
        return server.wait()


def in_words(code: int) -> str:
    """An exit code as the check prints it: 'exited with 1', or 'ended by SIGABRT (-6)'."""
    if code >= 0:
        return f"exited with {code}"
    try:
        name = signal.Signals(-code).name
    except ValueError:
        name = f"signal {-code}"
    return f"ended by {name} ({code})"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--timeout", type=float, default=180)
    args = parser.parse_args(argv)
    base = f"http://127.0.0.1:{args.port}"
    command = [
        sys.executable,
        "-m",
        "raglab",
        "serve",
        "--config",
        CONFIG,
        "--port",
        str(args.port),
    ]
    env = {**os.environ, "HF_HUB_OFFLINE": "1"}
    # our own CLI with fixed arguments, no shell
    server = subprocess.Popen(command, cwd=ROOT, env=env, start_new_session=True)  # nosec B603
    try:
        wait_until_up(base, server, args.timeout)
        failures = check(base)
    finally:
        code = stop(server)
    name = f"the server stops gracefully on {STOP.name} (exit {GRACEFUL_EXIT})"
    graceful = code == GRACEFUL_EXIT
    print(f"{'ok  ' if graceful else 'FAIL'} {name}: {in_words(code)}")
    if not graceful:
        failures.append(name)
    print(f"api-smoke: {'failed: ' + ', '.join(failures) if failures else 'passed'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
