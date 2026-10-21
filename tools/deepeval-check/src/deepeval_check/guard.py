"""What runs before DeepEval is imported (S5, AC10): its telemetry switched off and a socket guard
that lets this process reach the loopback Ollama port only.

- **Telemetry.** DeepEval sends event and metric names, an anonymous id and the public IP to
  PostHog unless DEEPEVAL_TELEMETRY_OPT_OUT is set to 1 (https://deepeval.com/docs/data-privacy,
  read 2026-10-20). `opt_out` sets it; the checks call it before their first DeepEval import, and
  `deepeval_imported` says whether that order held.
- **The guard.** Every name lookup and every connection this Python process makes goes through
  `socket.getaddrinfo` and `socket.socket.connect` (or `connect_ex`); the guard replaces them, so
  a lookup of a name that is not loopback, or a connection to anything but 127.0.0.1 or ::1 on the
  allowed port, raises OSError and is recorded in `attempts`. A telemetry call then fails the check
  instead of leaving the Mac.

What the guard cannot see: sockets that a C extension opens without Python's socket module (the
gRPC C core, for one, which DeepEval's OpenTelemetry dependency can load), and anything a child
process does. The checks start no child process; the ledger records whether any attempt was made.
"""

import os
import socket
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import cast

OPT_OUT = "DEEPEVAL_TELEMETRY_OPT_OUT"
OLLAMA_PORT = 11434
LOOPBACK_NAMES = frozenset({"localhost", "127.0.0.1", "::1"})


def opt_out() -> None:
    """Switch DeepEval's telemetry off, before it is imported."""
    os.environ[OPT_OUT] = "1"


def deepeval_imported() -> bool:
    return any(name == "deepeval" or name.startswith("deepeval.") for name in sys.modules)


def _host_port(address: object) -> tuple[str, int | None]:
    if isinstance(address, tuple) and address:
        parts = cast(tuple[object, ...], address)
        port = parts[1] if len(parts) > 1 and isinstance(parts[1], int) else None
        return str(parts[0]), port
    return str(address), None


@dataclass
class SocketGuard:
    """The loopback-only guard: install, run, uninstall (or use it as a context manager)."""

    port: int = OLLAMA_PORT
    attempts: list[str] = field(default_factory=list[str])
    _saved: dict[str, object] = field(default_factory=dict[str, object], repr=False)

    def allowed(self, host: str, port: int | None) -> bool:
        return host in LOOPBACK_NAMES and port in (None, self.port)

    def _refuse(self, what: str) -> OSError:
        self.attempts.append(what)
        return OSError(f"blocked by the loopback-only socket guard: {what}")

    def install(self) -> "SocketGuard":
        if self._saved:
            return self
        real_lookup = cast(Callable[..., object], socket.getaddrinfo)
        real_connect = socket.socket.connect
        real_connect_ex = socket.socket.connect_ex
        guard = self

        def getaddrinfo(host: object, port: object, *args: object, **kwargs: object) -> object:
            name = str(host)
            number = port if isinstance(port, int) else None
            if isinstance(port, str) and port.isdigit():
                number = int(port)
            if not guard.allowed(name, number):
                raise guard._refuse(f"lookup {name}:{port}")
            return real_lookup(host, port, *args, **kwargs)

        def connect(sock: socket.socket, address: object) -> None:
            host, number = _host_port(address)
            if not guard.allowed(host, number):
                raise guard._refuse(f"connect {host}:{number}")
            real_connect(sock, address)  # type: ignore[arg-type]

        def connect_ex(sock: socket.socket, address: object) -> int:
            host, number = _host_port(address)
            if not guard.allowed(host, number):
                raise guard._refuse(f"connect {host}:{number}")
            return real_connect_ex(sock, address)  # type: ignore[arg-type]

        self._saved = {
            "getaddrinfo": real_lookup,
            "connect": real_connect,
            "connect_ex": real_connect_ex,
        }
        socket.getaddrinfo = getaddrinfo  # type: ignore[assignment]
        socket.socket.connect = connect  # type: ignore[method-assign,assignment]
        socket.socket.connect_ex = connect_ex  # type: ignore[method-assign,assignment]
        return self

    def uninstall(self) -> None:
        if not self._saved:
            return
        socket.getaddrinfo = self._saved["getaddrinfo"]  # type: ignore[assignment]
        socket.socket.connect = self._saved["connect"]  # type: ignore[method-assign,assignment]
        socket.socket.connect_ex = self._saved["connect_ex"]  # type: ignore[method-assign,assignment]
        self._saved = {}

    def __enter__(self) -> "SocketGuard":
        return self.install()

    def __exit__(self, *exc: object) -> None:
        self.uninstall()
