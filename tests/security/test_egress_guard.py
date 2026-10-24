"""Nothing is sent out (S7, AG8; how-to 17 step 9): the paths a message could leave by.

1. The answer: the link guard (tests/security/test_attack_suite.py and
   tests/security/test_guard_cases.py).
2. The page: the web UI and the playground write text with textContent only, so a link in an answer
   is never fetched or rendered as a link (below; also tests/api/test_page.py and
   tests/unit/test_playground.py).
3. The process: the loopback-only egress guard (raglab.runtime.egress) refuses and records every
   lookup and connection off loopback; it wraps the attack suite
   (tests/security_support.egress_none) and the live attack runs, whose record says
   `egress: none`.
4. The model endpoint: the adapter refuses a base URL off loopback
   (tests/contract/test_chat_contract.py::test_a_server_that_is_not_local_is_refused)."""

import re
import socket

import pytest

from raglab.runtime.egress import EgressGuard, loopback
from tests.conftest import ROOT

pytestmark = pytest.mark.security
SINKS = re.compile(r"innerHTML|outerHTML|insertAdjacentHTML|document\.write|eval\(")


def test_a_connection_off_loopback_is_refused_and_recorded():
    with EgressGuard() as guard:
        with pytest.raises(OSError, match="loopback-only egress guard"):
            socket.getaddrinfo("192.0.2.1", 80)
        with socket.socket() as sock, pytest.raises(OSError, match="loopback-only"):
            sock.connect(("198.51.100.7", 443))
    assert guard.attempts == ["lookup 192.0.2.1:80", "connect 198.51.100.7"]
    assert guard.summary() == "lookup 192.0.2.1:80; connect 198.51.100.7"


def test_a_lookup_of_a_name_off_loopback_is_refused():
    with EgressGuard() as guard, pytest.raises(OSError, match="loopback-only"):
        socket.getaddrinfo("collector.example.org", 443)
    assert guard.attempts == ["lookup collector.example.org:443"]


def test_loopback_goes_through_to_the_layer_below():
    """On loopback the guard steps aside: the next layer (here the test suite's own no-network
    fixture) decides."""
    with (
        EgressGuard() as guard,
        socket.socket() as sock,
        pytest.raises(RuntimeError, match="never use the network"),
    ):
        sock.connect(("127.0.0.1", 11434))
    assert guard.summary() == "none"
    assert all(loopback(h) for h in ("127.0.0.1", "127.8.9.10", "::1", "localhost", None))
    assert not any(loopback(h) for h in ("192.0.2.1", "10.0.0.1", "example.org", "::ffff:1.2.3.4"))


def test_the_guard_is_removed_after_its_run():
    before = (socket.getaddrinfo, socket.socket.connect, socket.socket.connect_ex)
    with EgressGuard():
        assert socket.socket.connect is not before[1]
    assert (socket.getaddrinfo, socket.socket.connect, socket.socket.connect_ex) == before


def test_the_page_and_the_playground_write_text_only():
    scripts = [
        ROOT / "src" / "raglab" / "web" / "app.js",
        *sorted((ROOT / "playground").glob("*.js")),
    ]
    assert len(scripts) >= 3
    for path in scripts:
        source = path.read_text(encoding="utf-8")
        assert not SINKS.search(source), f"{path.relative_to(ROOT)} writes HTML"
        assert "textContent" in source or path.name == "model.js", path.name
