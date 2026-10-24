"""The loopback-only egress guard (S7, AG8, "nothing is sent out"), written for raglab after the
pattern of tools/deepeval-check's socket guard: while it is installed, a name lookup of anything
but a loopback name and a connection to anything but 127.0.0.1 or ::1 raise OSError, and each
attempt is recorded. It wraps the deterministic attack suite (tests/security/) and the live
attack runs, whose record says `egress: none` when nothing was attempted.

Every lookup and connection a Python process makes through the socket module goes through
`socket.getaddrinfo` and `socket.socket.connect` (or `connect_ex`; `socket.create_connection`
calls both), so those are the functions replaced. What it cannot see: a socket a C extension opens
without the socket module, and anything a child process does; the attack runs start no child
process. The guard is not a firewall: it proves what this process tried.
"""

import ipaddress
import socket
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import cast

LOOPBACK_NAMES = frozenset({"localhost", "localhost.localdomain"})


def loopback(host: object) -> bool:
    """Whether a host is the loopback interface: 127.0.0.0/8, ::1 or a loopback name. None (a
    lookup for binding a local socket) is local too."""
    if host is None:
        return True
    name = host.decode() if isinstance(host, bytes) else str(host)
    if name.lower() in LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(name.split("%", 1)[0]).is_loopback
    except ValueError:
        return False


def _host(address: object) -> object:
    if isinstance(address, tuple):
        parts = cast(tuple[object, ...], address)
        return parts[0] if parts else None
    return address


@dataclass
class EgressGuard:
    """Install, run, uninstall; or `with EgressGuard() as guard:`. `attempts` lists every refused
    lookup and connection, in order."""

    attempts: list[str] = field(default_factory=list[str])
    _saved: dict[str, object] = field(default_factory=dict[str, object], repr=False)

    def _refuse(self, what: str) -> OSError:
        self.attempts.append(what)
        return OSError(f"refused by the loopback-only egress guard: {what}")

    def summary(self) -> str:
        """What a run record says: `none`, or the refused attempts."""
        return "none" if not self.attempts else "; ".join(self.attempts)

    def install(self) -> "EgressGuard":
        if self._saved:
            return self
        lookup = cast(Callable[..., object], socket.getaddrinfo)
        connect = socket.socket.connect
        connect_ex = socket.socket.connect_ex
        guard = self

        def guarded_lookup(host: object, port: object, *args: object, **kwargs: object) -> object:
            if not loopback(host):
                raise guard._refuse(f"lookup {host}:{port}")
            return lookup(host, port, *args, **kwargs)

        def guarded_connect(sock: socket.socket, address: object) -> None:
            if not loopback(_host(address)):
                raise guard._refuse(f"connect {_host(address)}")
            connect(sock, address)  # type: ignore[arg-type]

        def guarded_connect_ex(sock: socket.socket, address: object) -> int:
            if not loopback(_host(address)):
                raise guard._refuse(f"connect {_host(address)}")
            return connect_ex(sock, address)  # type: ignore[arg-type]

        self._saved = {"lookup": lookup, "connect": connect, "connect_ex": connect_ex}
        socket.getaddrinfo = guarded_lookup  # type: ignore[assignment]
        socket.socket.connect = guarded_connect  # type: ignore[method-assign,assignment]
        socket.socket.connect_ex = guarded_connect_ex  # type: ignore[method-assign,assignment]
        return self

    def uninstall(self) -> None:
        if not self._saved:
            return
        socket.getaddrinfo = self._saved["lookup"]  # type: ignore[assignment]
        socket.socket.connect = self._saved["connect"]  # type: ignore[method-assign,assignment]
        socket.socket.connect_ex = self._saved["connect_ex"]  # type: ignore[method-assign,assignment]
        self._saved = {}

    def __enter__(self) -> "EgressGuard":
        return self.install()

    def __exit__(self, *_: object) -> None:
        self.uninstall()
