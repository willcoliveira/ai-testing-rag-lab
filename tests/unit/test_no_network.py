"""Tests never use the network (S1b AC8): the autouse fixture in tests/conftest.py refuses any
socket connection from the test process."""

import socket
import urllib.request

import pytest

pytestmark = pytest.mark.unit


def test_a_socket_connection_is_refused():
    with pytest.raises(RuntimeError, match="never use the network"):
        socket.create_connection(("192.0.2.1", 80), timeout=1)
    with socket.socket() as sock, pytest.raises(RuntimeError, match="never use the network"):
        sock.connect(("192.0.2.1", 80))


def test_an_http_request_is_refused():
    with pytest.raises((RuntimeError, OSError), match="never use the network"):
        urllib.request.urlopen("http://192.0.2.1/", timeout=1)
