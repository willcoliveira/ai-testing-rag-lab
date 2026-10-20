"""Every test of this project runs with DeepEval's telemetry off (set at collection, before any
test imports DeepEval; DeepEval's own pytest plugin is not loaded: pyproject.toml's `-p
no:deepeval`) and under the loopback-only socket guard, which fails a test that attempts any other
connection."""

from collections.abc import Iterator

import pytest
from deepeval_check import guard

guard.opt_out()


@pytest.fixture(autouse=True)
def loopback_only() -> Iterator[guard.SocketGuard]:
    with guard.SocketGuard() as sockets:
        yield sockets
    assert sockets.attempts == [], f"a connection beyond loopback was attempted: {sockets.attempts}"
