"""The architecture checker finds what it must find, and nothing else (AC3, AC4)."""

from pathlib import Path

import pytest

from tests.conftest import ROOT, load_script

pytestmark = pytest.mark.unit
arch = load_script("check_architecture")


def make_package(tmp_path: Path, files: dict[str, str]) -> Path:
    package = tmp_path / "raglab"
    for rel, source in {
        "__init__.py": "",
        "core/__init__.py": "",
        "adapters/__init__.py": "",
        **files,
    }.items():
        path = package / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
    return package


def messages(package: Path) -> list[str]:
    return [str(v) for v in arch.check(package)]


def test_real_source_tree_is_clean():
    assert arch.check(ROOT / "src" / "raglab") == []


def test_clean_fixture_passes(tmp_path):
    package = make_package(
        tmp_path,
        {
            "core/ports.py": "import json\nfrom dataclasses import field\nfrom . import types\n",
            "core/types.py": "from raglab.core import ports\n",
            "adapters/openai_compat.py": "import openai\nfrom anthropic import Anthropic\n",
        },
    )
    assert messages(package) == []


def test_third_party_import_in_core_is_reported_with_file_and_module(tmp_path):
    package = make_package(tmp_path, {"core/ports.py": "import json\nimport requests\n"})
    found = messages(package)
    assert len(found) == 1
    assert "core/ports.py:2" in found[0]
    assert "requests" in found[0]


@pytest.mark.parametrize(
    "source",
    [
        "from raglab.generate import pipeline\n",
        "from .. import generate\n",
    ],
)
def test_core_importing_another_raglab_layer_is_reported(tmp_path, source):
    package = make_package(tmp_path, {"core/ports.py": source})
    assert len(messages(package)) == 1


@pytest.mark.parametrize(
    "source",
    [
        "import openai\n",
        "from anthropic import Anthropic\n",
        "import anthropic\nclient = anthropic.Anthropic()\n",
        "import importlib\nsdk = importlib.import_module('qdrant_client')\n",
        "boto3 = __import__('boto3')\n",
    ],
)
def test_vendor_sdk_outside_adapters_is_reported(tmp_path, source):
    package = make_package(tmp_path, {"generate/pipeline.py": source})
    found = messages(package)
    assert found, source
    assert all("generate/pipeline.py" in f and "outside raglab.adapters" in f for f in found)


def test_vendor_sdk_inside_adapters_passes(tmp_path):
    package = make_package(
        tmp_path,
        {"adapters/anthropic_adapter.py": "import anthropic\nclient = anthropic.Anthropic()\n"},
    )
    assert messages(package) == []


def test_cli_exit_codes(tmp_path):
    clean = make_package(tmp_path / "a", {})
    dirty = make_package(tmp_path / "b", {"core/x.py": "import numpy\n"})
    assert arch.main(["check_architecture.py", str(clean)]) == 0
    assert arch.main(["check_architecture.py", str(dirty)]) == 1
    assert arch.main(["check_architecture.py", str(tmp_path / "missing")]) == 2
