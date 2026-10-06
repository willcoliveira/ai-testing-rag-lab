"""The README status diagram is the same as diagram 4 in docs/ARCHITECTURE.md."""

import re

import pytest

from tests.conftest import ROOT

pytestmark = pytest.mark.unit


def blocks(name: str) -> list[str]:
    return re.findall(
        r"```mermaid\n(.*?)```", (ROOT / name).read_text(encoding="utf-8"), flags=re.S
    )


def test_readme_status_matches_architecture():
    assert blocks("README.md") == [blocks("docs/ARCHITECTURE.md")[3]]
