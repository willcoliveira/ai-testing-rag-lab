"""The API smoke's exit check (judge S3-J12): scripts/api_smoke.py stops `raglab serve` with
SIGTERM and passes only when the server then ends as uvicorn's graceful shutdown on SIGTERM ends
it, by the signal raised again (-15). An abort at exit (-6, as onnxruntime 1.30.0 can on macOS),
an error exit, or a server killed after the grace fails it with one clear line. A fake process
stands in for the server and the HTTP checks are stubbed: nothing starts, and os.killpg is
replaced, so no signal is sent."""

import signal
import subprocess
from dataclasses import dataclass

import pytest

from tests.conftest import load_script

pytestmark = pytest.mark.unit
GRACEFUL = "the server stops gracefully on SIGTERM (exit -15)"


@dataclass
class FakeServer:
    """`raglab serve` as the script sees it: a pid, and wait() giving the exit code it was made
    with. A stubborn one still runs when the grace ends (TimeoutExpired), so the script's SIGKILL
    ends it (-9)."""

    code: int
    stubborn: bool = False
    pid: int = 4242
    returncode: int | None = None

    def wait(self, timeout: float | None = None) -> int:
        if self.stubborn and timeout is not None:
            raise subprocess.TimeoutExpired("raglab serve", timeout)
        self.returncode = -signal.SIGKILL if self.stubborn else self.code
        return self.returncode


@pytest.mark.parametrize(
    ("code", "stubborn", "seen"),
    [
        (-signal.SIGTERM, False, f"ok   {GRACEFUL}: ended by SIGTERM (-15)"),
        (-signal.SIGABRT, False, f"FAIL {GRACEFUL}: ended by SIGABRT (-6)"),
        (1, False, f"FAIL {GRACEFUL}: exited with 1"),
        (0, True, f"FAIL {GRACEFUL}: ended by SIGKILL (-9)"),
    ],
    ids=["graceful", "abort", "error", "killed-after-the-grace"],
)
def test_the_smoke_passes_only_when_the_server_stops_gracefully(
    monkeypatch, capsys, code, stubborn, seen
):
    smoke = load_script("api_smoke")
    server = FakeServer(code, stubborn)
    sent: list[tuple[int, int]] = []
    monkeypatch.setattr(smoke.subprocess, "Popen", lambda *args, **kwargs: server)
    monkeypatch.setattr(smoke.os, "killpg", lambda pid, sig: sent.append((pid, sig)))
    monkeypatch.setattr(smoke, "wait_until_up", lambda base, process, timeout: None)
    monkeypatch.setattr(smoke, "check", lambda base: [])
    graceful = code == -signal.SIGTERM
    assert smoke.main([]) == (0 if graceful else 1)
    assert sent == [(4242, signal.SIGTERM), *([(4242, signal.SIGKILL)] if stubborn else [])]
    lines = capsys.readouterr().out.splitlines()
    assert seen in lines, lines
    assert lines[-1] == ("api-smoke: passed" if graceful else f"api-smoke: failed: {GRACEFUL}")
