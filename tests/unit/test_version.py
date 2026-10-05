import subprocess
import sys
import tomllib

import pytest

from raglab import __version__
from tests.conftest import ROOT

pytestmark = pytest.mark.unit


def test_version_matches_pyproject():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert __version__ == project["version"]


def test_cli_prints_version():
    out = subprocess.run(
        [sys.executable, "-m", "raglab", "--version"], capture_output=True, text=True, check=True
    )
    assert out.stdout.strip() == f"raglab {__version__}"
