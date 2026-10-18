import importlib.util
import socket
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parent.parent


def load_script(name: str) -> ModuleType:
    """Import scripts/<name>.py as a module, so its functions can be tested directly."""
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def no_network(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests never use the network: a socket connection from the test process fails the test.
    (Child processes, such as the CLI or git run by a test, are not covered.) A test marked
    `live` talks to a local model server on purpose; `make check` and CI never select it."""
    if request.node.get_closest_marker("live") is not None:
        return

    def refuse(*args: object, **kwargs: object) -> None:
        raise RuntimeError("tests never use the network")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
