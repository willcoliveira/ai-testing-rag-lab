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
        # the S0 judge's bypasses
        "from importlib import import_module as im\nsdk = im('openai')\n",
        "import importlib\nname = 'openai'\nsdk = importlib.import_module(name)\n",
        "import importlib\nsdk = importlib.import_module('ope' + 'nai')\n",
        "import openai.types\n",
        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import openai\n",
        # the importer reached through other names (judge round 2 narrowed what counts)
        "import importlib as il\nsdk = il.import_module('openai')\n",
        "import importlib.util\nsdk = importlib.import_module('openai')\n",
        "import importlib\nloader = importlib\nsdk = loader.import_module('openai')\n",
        "import importlib\nim = importlib.import_module\nsdk = im('openai')\n",
        "from importlib import import_module\nim = import_module\nsdk = im('openai')\n",
        "from importlib import *\nsdk = import_module('openai')\n",
        "sdk = __import__('importlib').import_module('openai')\n",
        "import importlib as il\nif (im := il.import_module):\n    sdk = im('openai')\n",
        "import builtins\nsdk = builtins.__import__('openai')\n",
        "def load(name):\n    return __import__(name)\n",
        "from importlib import import_module\ndef load(name):\n    return import_module(name)\n",
        # judge round 3 (D5): importlib bound by a call, by tuple unpacking or through sys.modules
        "importlib = __import__('importlib')\nsdk = importlib.import_module('openai')\n",
        "import importlib\nil, x = importlib, 1\nsdk = il.import_module('openai')\n",
        "import sys\nsdk = sys.modules['importlib'].import_module('openai')\n",
        "import importlib\nim, x = importlib.import_module, 1\nsdk = im('openai')\n",
        "import importlib\nsdk = getattr(importlib, 'import_module')('openai')\n",
        "import importlib\nim = getattr(importlib, 'import_module')\nsdk = im('openai')\n",
        "import importlib\nsdk = importlib.import_module(name='openai')\n",
        "import importlib\ndef load():\n    return importlib.import_module(*['openai'])\n",
        # judge round 3 (D6): pkgutil, importlib.util, runpy and sys.modules routes
        "import pkgutil\nsdk = pkgutil.resolve_name('openai')\n",
        "import pkgutil\ncls = pkgutil.resolve_name('openai:OpenAI')\n",
        "from pkgutil import resolve_name\ncls = resolve_name('anthropic.types:Message')\n",
        "import importlib.util\nspec = importlib.util.find_spec('openai')\n"
        "sdk = importlib.util.module_from_spec(spec)\nspec.loader.exec_module(sdk)\n",
        "from importlib.util import find_spec\nspec = find_spec('boto3')\n",
        "import runpy\nrunpy.run_module('openai')\n",
        "import importlib\nsdk = importlib.import_module('.types', package='openai')\n",
        "import sys\nsdk = sys.modules['openai']\n",
        "import sys\nsdk = sys.modules.get('openai')\n",
        "from sys import modules\nsdk = modules['openai']\n",
        "from sys import modules as m\nsdk = m.setdefault('openai', None)\n",
        "s = __import__('sys')\nsdk = s.modules['openai']\n",
        "import sys\nmods, x = sys.modules, 1\nsdk = mods['openai']\n",
        "import pkgutil\ndef load(name):\n    return pkgutil.resolve_name(name)\n",
        "import importlib.util\ndef load(name):\n    return importlib.util.find_spec(name)\n",
        "import sys\ndef get(name):\n    return sys.modules[name]\n",
        "import sys\ndef get(name):\n    return sys.modules.get(name)\n",
    ],
)
def test_vendor_sdk_outside_adapters_is_reported(tmp_path, source):
    package = make_package(tmp_path, {"generate/pipeline.py": source})
    found = messages(package)
    assert found, source
    assert all("generate/pipeline.py" in f and "raglab.adapters" in f for f in found)


@pytest.mark.parametrize(
    "source",
    [
        # judge round 2: a function of this file that happens to be called import_module
        "def import_module(name):\n    return name.upper()\n\nvalue = import_module(input())\n",
        "def outer():\n    def import_module(name):\n        return name\n"
        "    return import_module(input())\n",
    ],
)
def test_a_local_function_named_import_module_is_not_an_importer(tmp_path, source):
    package = make_package(tmp_path, {"generate/pipeline.py": source})
    assert messages(package) == []


@pytest.mark.parametrize(
    "source",
    [
        "class Loader:\n    def import_module(self, name):\n        return name\n\n"
        "value = Loader().import_module(input())\n",
        "from mylib import plugins\nvalue = plugins.import_module(input())\n",
    ],
)
def test_any_import_module_attribute_call_is_an_importer(tmp_path, source):
    """Judge round 3 (D5): an attribute call named import_module counts whatever its receiver,
    since importlib can be bound where no tracker sees it. The cost: a method of that name called
    with a computed name outside adapters is reported, and must be renamed."""
    package = make_package(tmp_path, {"generate/pipeline.py": source})
    found = messages(package)
    assert len(found) == 1
    assert "dynamic import with a computed name" in found[0]


@pytest.mark.parametrize(
    "source",
    [
        # judge round 3 (D6): a provider name is data in config and later stages
        "provider = 'openai'\nCONFIG = {'provider': 'openai'}\nchoice = CONFIG['provider']\n",
        "modules = {'openai': 1}\nvalue = modules['openai']\n",
        "class Registry:\n    modules = {}\n\n    def get(self):\n"
        "        return self.modules['openai']\n",
        "import sys\nthis = sys.modules[__name__]\n",
        "from importlib import import_module\nthis = import_module(__package__)\n",
        "def find_spec(name):\n    return name\n\nvalue = find_spec(input())\n",
        "import importlib.util\nspec = importlib.util.find_spec('json')\n",
    ],
)
def test_data_and_this_module_are_not_imports(tmp_path, source):
    package = make_package(tmp_path, {"generate/pipeline.py": source})
    assert messages(package) == []


def test_run_time_import_in_core_must_name_the_stdlib(tmp_path):
    source = "import importlib.util\nspec = importlib.util.find_spec('requests')\n"
    package = make_package(tmp_path, {"core/ports.py": source})
    found = messages(package)
    assert len(found) == 1
    assert "core/ports.py:2" in found[0]
    assert "not requests" in found[0]


def test_relative_import_above_the_package_names_the_import(tmp_path):
    package = make_package(tmp_path, {"core/ports.py": "from ... import x\n"})
    found = messages(package)
    assert len(found) == 1
    assert "not ...x" in found[0]


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


# S1b: file-format parsers are not vendor SDKs, but only raglab.ingest imports them
@pytest.mark.parametrize("module", ["pypdf", "pytesseract", "yaml", "PIL"])
def test_parser_libraries_are_allowed_in_ingest(tmp_path, module):
    package = make_package(tmp_path, {"ingest/reader.py": f"import {module}\n"})
    assert messages(package) == []


@pytest.mark.parametrize(
    ("path", "source"),
    [
        ("chunk/sections.py", "import yaml\n"),
        ("generate/pipeline.py", "from pypdf import PdfReader\n"),
        ("adapters/store.py", "import pytesseract\n"),
        ("__main__.py", "from PIL import Image\n"),
    ],
)
def test_parser_libraries_outside_ingest_are_reported(tmp_path, path, source):
    package = make_package(tmp_path, {path: source})
    found = messages(package)
    assert len(found) == 1, found
    assert path in found[0]
    assert "outside raglab.ingest" in found[0]


def test_core_importing_a_parser_breaks_both_rules(tmp_path):
    package = make_package(tmp_path, {"core/types.py": "import yaml\n"})
    found = messages(package)
    assert len(found) == 2
    assert any("standard library" in f for f in found)
    assert any("outside raglab.ingest" in f for f in found)


# S2: the local embedder's SDKs are vendor SDKs, imported only in raglab.adapters
@pytest.mark.parametrize(
    "source",
    [
        "from fastembed import TextEmbedding\n",
        "import onnxruntime\n",
        "import huggingface_hub\n",
        "import importlib\nort = importlib.import_module('onnxruntime')\n",
    ],
)
def test_embedder_sdks_outside_adapters_are_reported(tmp_path, source):
    package = make_package(tmp_path, {"retrieve/dense.py": source})
    found = messages(package)
    assert len(found) == 1, found
    assert "retrieve/dense.py" in found[0]
    assert "outside raglab.adapters" in found[0]


def test_embedder_sdks_inside_adapters_pass(tmp_path):
    source = "from fastembed import TextEmbedding\nimport onnxruntime\n"
    package = make_package(tmp_path, {"adapters/fastembed_embed.py": source})
    assert messages(package) == []


# Rule 4 (S2, changed in S3): the fake adapters are imported only by raglab.adapters.factory,
# which builds FakeChat on provider = "fake"; every other module of the package is refused
@pytest.mark.parametrize(
    ("path", "source"),
    [
        ("retrieve/dense.py", "from raglab.adapters.fake import HashingEmbedder\n"),
        ("evals/run.py", "from raglab.adapters import fake\n"),
        ("__main__.py", "import raglab.adapters.fake\n"),
        ("api/app.py", "from raglab.adapters.fake import FakeChat\n"),
        ("generate/pipeline.py", "from raglab.adapters.fake import FakeChat\n"),
        ("adapters/openai_compat.py", "from . import fake\n"),
        ("adapters/fastembed_embed.py", "from .fake import HashingEmbedder\n"),
        (
            "evals/run.py",
            "import importlib\nfake = importlib.import_module('raglab.adapters.fake')\n",
        ),
    ],
)
def test_the_fake_adapters_are_imported_by_the_factory_only(tmp_path, path, source):
    package = make_package(tmp_path, {"adapters/fake.py": "import hashlib\n", path: source})
    found = messages(package)
    assert len(found) == 1, found
    assert path in found[0]
    assert "raglab.adapters.fake is built only by raglab.adapters.factory" in found[0]


@pytest.mark.parametrize(
    "source",
    [
        "from . import fake\n",
        "from .fake import FakeChat\n",
        "from raglab.adapters import fake, fastembed_embed\n",
    ],
)
def test_the_factory_may_import_the_fake_adapters(tmp_path, source):
    package = make_package(
        tmp_path, {"adapters/fake.py": "import hashlib\n", "adapters/factory.py": source}
    )
    assert messages(package) == []


def test_a_planted_fake_import_in_a_copy_of_the_real_tree_fails(tmp_path):
    import shutil

    copy = tmp_path / "raglab"
    shutil.copytree(ROOT / "src" / "raglab", copy, ignore=shutil.ignore_patterns("__pycache__"))
    target = copy / "generate" / "pipeline.py"
    target.write_text(
        "from raglab.adapters.fake import FakeChat\n" + target.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    found = messages(copy)
    assert len(found) == 1, found
    assert "generate/pipeline.py:1" in found[0]
    assert "built only by raglab.adapters.factory" in found[0]


def test_the_fake_adapter_itself_and_other_adapters_pass(tmp_path):
    package = make_package(
        tmp_path,
        {
            "adapters/fake.py": "import hashlib\nfrom raglab.core import ports\n",
            "retrieve/dense.py": "from raglab.adapters import fastembed_embed\n",
            "adapters/fastembed_embed.py": "import fastembed\n",
        },
    )
    assert messages(package) == []


# Rule 5 (S3): HTTP clients only in raglab.adapters, the web framework only in raglab.api
@pytest.mark.parametrize(
    ("path", "source", "expected"),
    [
        ("generate/pipeline.py", "import httpx\n", "vendor SDK httpx is imported outside"),
        ("api/app.py", "import httpx\n", "vendor SDK httpx is imported outside"),
        ("evals/run.py", "import aiohttp\n", "HTTP client aiohttp is imported outside"),
        ("generate/pipeline.py", "from fastapi import FastAPI\n", "web framework fastapi"),
        ("__main__.py", "import uvicorn\n", "web framework uvicorn"),
        ("adapters/openai_compat.py", "from starlette.responses import Response\n", "starlette"),
    ],
)
def test_http_clients_and_the_web_framework_stay_in_their_layers(tmp_path, path, source, expected):
    package = make_package(tmp_path, {path: source})
    found = messages(package)
    assert len(found) == 1, found
    assert path in found[0]
    assert expected in found[0]


def test_httpx_in_adapters_and_fastapi_in_api_pass(tmp_path):
    package = make_package(
        tmp_path,
        {
            "adapters/openai_compat.py": "import httpx\n",
            "api/app.py": "from fastapi import FastAPI\nimport uvicorn\nimport starlette\n",
        },
    )
    assert messages(package) == []


# Rule 6 (S5, D4): DeepEval is fenced in tools/deepeval-check; nothing in the package imports it,
# raglab.adapters included (before S5 it was a vendor SDK allowed in adapters)
@pytest.mark.parametrize(
    "path",
    ["adapters/deepeval_judge.py", "judge/llm.py", "evals/judged.py", "core/ports.py"],
)
@pytest.mark.parametrize(
    "source",
    [
        "import deepeval\n",
        "from deepeval.metrics import FaithfulnessMetric\n",
        "import importlib\nm = importlib.import_module('deepeval.models')\n",
    ],
)
def test_deepeval_is_imported_nowhere_in_the_package_adapters_included(tmp_path, path, source):
    package = make_package(tmp_path, {path: source})
    found = [f for f in messages(package) if "fenced in tools/deepeval-check" in f]
    assert len(found) == 1, messages(package)
    assert path in found[0]


def test_deepeval_is_no_longer_a_vendor_sdk_but_fenced():
    assert "deepeval" not in arch.VENDORS
    assert "deepeval" in arch.FENCED


def test_the_main_environment_never_installs_deepeval():
    """S5 AC10: DeepEval and its pytest plugins live in tools/deepeval-check's environment only, so
    they never load into make test."""
    import importlib.metadata
    import importlib.util

    assert importlib.util.find_spec("deepeval") is None
    assert 'name = "deepeval"' not in (ROOT / "uv.lock").read_text(encoding="utf-8")
    plugins = {ep.name for ep in importlib.metadata.entry_points(group="pytest11")}
    assert "deepeval" not in plugins


# Rule 7 (S9): OpenTelemetry is imported only in raglab.obs; the pipeline writes to the Tracer port
# of raglab.core and the web layer gets the provider as an opaque object
@pytest.mark.parametrize(
    "path",
    ["generate/pipeline.py", "core/ports.py", "api/app.py", "adapters/factory.py", "evals/x.py"],
)
@pytest.mark.parametrize(
    "source",
    [
        "from opentelemetry import trace\n",
        "import opentelemetry.sdk.trace\n",
        "from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter\n",
        "import importlib\nm = importlib.import_module('opentelemetry.trace')\n",
    ],
)
def test_opentelemetry_is_imported_only_in_obs(tmp_path, path, source):
    package = make_package(tmp_path, {path: source})
    found = [f for f in messages(package) if "OpenTelemetry" in f]
    assert len(found) == 1, messages(package)
    assert path in found[0]
    assert "raglab.obs" in found[0]


def test_the_pipeline_and_the_names_load_no_opentelemetry():
    """S9-J5: rule 7 fences the imports of opentelemetry; raglab.generate imports raglab.obs's
    names and traced embedder, which import none, so the pipeline (and every run that is not
    `raglab serve` with an endpoint) never loads the SDK. Checked in a fresh interpreter."""
    import subprocess
    import sys

    code = (
        "import sys, raglab.core.ports, raglab.obs.names, raglab.obs.traced, "
        "raglab.generate.pipeline; "
        "print(sorted(m for m in sys.modules if m.split('.')[0] == 'opentelemetry'))"
    )
    done = subprocess.run(
        [sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, check=True
    )
    assert done.stdout.strip() == "[]", done.stdout


def test_opentelemetry_in_obs_passes(tmp_path):
    package = make_package(
        tmp_path,
        {
            "obs/__init__.py": "",
            "obs/otel.py": "from opentelemetry import trace\nimport opentelemetry.sdk.trace\n",
        },
    )
    assert messages(package) == []


def test_a_planted_opentelemetry_import_in_a_copy_of_the_real_tree_fails(tmp_path):
    """OB2's break, on a copy: an opentelemetry import in raglab.generate, then in raglab.core,
    each reported with its file."""
    import shutil

    package = tmp_path / "raglab"
    shutil.copytree(ROOT / "src" / "raglab", package)
    assert messages(package) == []
    for rel in ("generate/pipeline.py", "core/ports.py"):
        with (package / rel).open("a", encoding="utf-8") as source:
            source.write("\nfrom opentelemetry import trace  # planted\n")
    found = [f for f in messages(package) if "OpenTelemetry" in f]
    assert [f.split(":")[0].split("raglab/")[-1] for f in found] == [
        "core/ports.py",
        "generate/pipeline.py",
    ]
