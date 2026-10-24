"""S9 OB6: PERF_TEST_MODE serves the perf stub, and prod refuses it. config/perf.toml is served only
with PERF_TEST_MODE=1; the mode only with a perf-stub config and only where RAGLAB_ENV is exactly ci
or local; under prod, unset or any other value the server exits non-zero with one line before the
port binds; create_app refuses too; the content opt-in follows the same rule; /version names
perf-stub with provenance fake; with neither switch set nothing changes.

In process for the whole table (raglab.api.environment and create_app), and as a subprocess of
`raglab serve` for the refusals: the test holds the port itself, so a server that tried to bind
before refusing would fail on the bind, not with its one line."""

import os
import re
import socket
import subprocess
import sys

import pytest

from raglab.__main__ import main
from raglab.adapters.fake import HashingEmbedder
from raglab.api import environment, server
from raglab.api.app import create_app
from raglab.evals import config as eval_config
from raglab.generate import assemble
from raglab.ingest.pipeline import Inventory
from tests.conftest import ROOT
from tests.generation_support import TOKENS, small_pipeline
from tests.obs_support import INFO
from tests.retrieval_support import PACK

pytestmark = [pytest.mark.unit, pytest.mark.security]
PERF = ROOT / "config" / "perf.toml"
FAKE = ROOT / "config" / "fake.toml"
LOCAL_OLLAMA = ROOT / "config" / "local-ollama.toml"
SWITCHES = ("RAGLAB_ENV", "PERF_TEST_MODE", "RAGLAB_TRACE_CONTENT")

# (environment, the config's generator provider, the switches it allows, or the refusal's words)
TABLE = [
    ({}, "fake", (False, False)),
    ({"RAGLAB_ENV": "prod"}, "fake", (False, False)),
    ({"RAGLAB_ENV": "ci"}, "openai-compat", (False, False)),
    ({"PERF_TEST_MODE": "1", "RAGLAB_ENV": "ci"}, "perf-stub", (True, False)),
    ({"PERF_TEST_MODE": "1", "RAGLAB_ENV": "local"}, "perf-stub", (True, False)),
    ({"PERF_TEST_MODE": "1", "RAGLAB_ENV": "prod"}, "perf-stub", "not 'prod'"),
    ({"PERF_TEST_MODE": "1"}, "perf-stub", "not unset"),
    ({"PERF_TEST_MODE": "1", "RAGLAB_ENV": "CI"}, "perf-stub", "not 'CI'"),
    ({"PERF_TEST_MODE": "1", "RAGLAB_ENV": "ci "}, "perf-stub", "not 'ci '"),
    ({"PERF_TEST_MODE": "1", "RAGLAB_ENV": ""}, "perf-stub", "not ''"),
    ({"PERF_TEST_MODE": "1", "RAGLAB_ENV": "staging"}, "perf-stub", "not 'staging'"),
    ({"PERF_TEST_MODE": "1", "RAGLAB_ENV": "ci"}, "fake", "serves only a perf-stub config"),
    ({"PERF_TEST_MODE": "1", "RAGLAB_ENV": "ci"}, "openai-compat", "never runs under a real"),
    ({"RAGLAB_ENV": "ci"}, "perf-stub", "only with PERF_TEST_MODE=1"),
    ({}, "perf-stub", "only with PERF_TEST_MODE=1"),
    ({"PERF_TEST_MODE": "0", "RAGLAB_ENV": "ci"}, "perf-stub", "only PERF_TEST_MODE=1"),
    ({"PERF_TEST_MODE": "true", "RAGLAB_ENV": "ci"}, "perf-stub", "only PERF_TEST_MODE=1"),
    ({"PERF_TEST_MODE": "", "RAGLAB_ENV": "ci"}, "fake", "only PERF_TEST_MODE=1"),
    ({"RAGLAB_TRACE_CONTENT": "1", "RAGLAB_ENV": "local"}, "fake", (False, True)),
    ({"RAGLAB_TRACE_CONTENT": "1", "RAGLAB_ENV": "ci"}, "fake", (False, True)),
    ({"RAGLAB_TRACE_CONTENT": "1", "RAGLAB_ENV": "prod"}, "fake", "not 'prod'"),
    ({"RAGLAB_TRACE_CONTENT": "1"}, "fake", "not unset"),
    ({"RAGLAB_TRACE_CONTENT": "yes", "RAGLAB_ENV": "local"}, "fake", "only RAGLAB_TRACE_CONTENT=1"),
    (
        {"PERF_TEST_MODE": "1", "RAGLAB_TRACE_CONTENT": "1", "RAGLAB_ENV": "ci"},
        "perf-stub",
        (True, True),
    ),
]


@pytest.mark.parametrize(("environ", "provider", "expected"), TABLE)
def test_the_environment_table(environ, provider, expected):
    if isinstance(expected, tuple):
        allowed = environment.switches(environ, provider)
        assert (allowed.perf_mode, allowed.capture_content) == expected
        return
    with pytest.raises(environment.EnvironmentRefused, match=re.escape(expected)) as error:
        environment.switches(environ, provider)
    assert "\n" not in str(error.value)  # one line


@pytest.mark.parametrize(("environ", "provider", "expected"), TABLE)
def test_create_app_refuses_the_same_rows(environ, provider, expected):
    pipeline, _ = small_pipeline()
    info = INFO.__class__(**{**INFO.__dict__, "provider": provider})
    if isinstance(expected, tuple):
        assert create_app(pipeline, info, TOKENS, environ=environ) is not None
    else:
        with pytest.raises(environment.EnvironmentRefused):
            create_app(pipeline, info, TOKENS, environ=environ)


def test_create_app_reads_the_process_environment_by_default(monkeypatch):
    pipeline, _ = small_pipeline()
    perf = INFO.__class__(**{**INFO.__dict__, "provider": "perf-stub"})
    monkeypatch.setenv("PERF_TEST_MODE", "1")
    monkeypatch.setenv("RAGLAB_ENV", "prod")
    with pytest.raises(environment.EnvironmentRefused, match="not 'prod'"):
        create_app(pipeline, perf, TOKENS)
    monkeypatch.setenv("RAGLAB_ENV", "ci")
    assert create_app(pipeline, perf, TOKENS) is not None


REAL_ASSEMBLE = assemble.assemble


def small_assemble(config, root, tracer=None):
    """The real assembly (the factory builds the configured chat model) over the small pack with
    the hashing embedder: no corpus ingest, no model files."""
    hashing = HashingEmbedder()
    description: dict[str, object] = {"provider": "fake", "model": hashing.model}
    return REAL_ASSEMBLE(
        config,
        root,
        embedder=(hashing, description, "fake"),
        inventory=Inventory(config.chunker, {}, (), tuple(PACK)),
        tracer=tracer,
    )


def test_the_perf_config_serves_the_stub_and_version_names_it(monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.setattr(server.assemble, "assemble", small_assemble)
    app = server.build_app(PERF, ROOT, environ={"PERF_TEST_MODE": "1", "RAGLAB_ENV": "ci"})
    client = TestClient(app)
    version = client.get("/version").json()
    assert (version["provider"], version["model"], version["provenance"]) == (
        "perf-stub",
        "perf-stub",
        "fake",
    )
    reply = client.post(
        "/ask",
        json={"tenant": "tenant-a", "question": "How many characters must passwords have?"},
        headers={"Authorization": "Bearer demo"},
    )
    assert (reply.status_code, reply.json()["status"]) == (200, "ok")


def test_neither_switch_set_changes_nothing(monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.setattr(server.assemble, "assemble", small_assemble)
    app = server.build_app(FAKE, ROOT, environ={})
    assert TestClient(app).get("/version").json()["provider"] == "fake"
    with pytest.raises(environment.EnvironmentRefused, match="serves only a perf-stub config"):
        server.build_app(FAKE, ROOT, environ={"PERF_TEST_MODE": "1", "RAGLAB_ENV": "ci"})


def test_only_serve_reads_a_perf_stub_config(capsys):
    with pytest.raises(eval_config.ConfigError, match=r"only \(S9\); no run, question or session"):
        eval_config.load_generation(PERF, ROOT)
    assert eval_config.load_generation(PERF, ROOT, perf_stub=True).generator.provider == "perf-stub"
    with pytest.raises(eval_config.ConfigError, match="perf-stub is for `raglab serve`"):
        eval_config.load_generation(PERF, ROOT, require_digest=False)
    for argv in (
        ["eval", "--suite", "generation", "--config", str(PERF)],
        ["ask", "--config", str(PERF), "--tenant", "tenant-a", "How long?"],
        ["ollama", "status", "--config", str(PERF)],
    ):
        assert main(argv) != 0, argv
        assert "perf-stub is for `raglab serve`" in capsys.readouterr().err, argv


def test_the_perf_config_matches_the_local_configs_retrieval():
    perf = eval_config.load_generation(PERF, ROOT, perf_stub=True)
    local = eval_config.load_generation(LOCAL_OLLAMA, ROOT)
    assert (perf.chunker, perf.embedder, perf.retriever) == (
        local.chunker,
        local.embedder,
        local.retriever,
    )
    assert perf.tokens == local.tokens
    assert (perf.generator.provider, perf.generator.model) == ("perf-stub", "perf-stub")


@pytest.mark.parametrize(
    ("config", "environ", "words"),
    [
        (PERF, {"PERF_TEST_MODE": "1", "RAGLAB_ENV": "prod"}, "not 'prod'"),
        (PERF, {"PERF_TEST_MODE": "1"}, "not unset"),
        (PERF, {"RAGLAB_ENV": "ci"}, "only with PERF_TEST_MODE=1"),
        (LOCAL_OLLAMA, {"PERF_TEST_MODE": "1", "RAGLAB_ENV": "ci"}, "never runs under a real"),
        (FAKE, {"RAGLAB_TRACE_CONTENT": "1", "RAGLAB_ENV": "prod"}, "not 'prod'"),
        (FAKE, {"RAGLAB_OTLP_ENDPOINT": "http://192.0.2.1:4318"}, "loopback interface"),
    ],
    ids=["prod", "unset", "no-mode", "real-model", "content-in-prod", "remote-collector"],
)
def test_serve_refuses_with_one_line_before_the_port_binds(config, environ, words):
    with socket.socket() as held:  # bind is not patched by the no-network fixture; connect is
        held.bind(("127.0.0.1", 0))
        held.listen()
        port = held.getsockname()[1]
        env = {k: v for k, v in os.environ.items() if k not in (*SWITCHES, "RAGLAB_OTLP_ENDPOINT")}
        command = [sys.executable, "-m", "raglab", "serve", "--config", str(config)]
        done = subprocess.run(
            [*command, "--port", str(port)],
            cwd=ROOT,
            env={**env, **environ, "HF_HUB_OFFLINE": "1"},
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    assert done.returncode == 1, done
    lines = done.stderr.strip().splitlines()
    assert len(lines) == 1, lines
    assert lines[0].startswith("serve failed: "), lines
    assert words in lines[0], lines
    assert done.stdout == ""  # "raglab serve: http://..." is printed only once it may serve
