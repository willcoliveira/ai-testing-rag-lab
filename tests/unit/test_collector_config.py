"""S9 OB7: the collector's configuration (deploy/otel/). The receiver binds the loopback interface
only; the local pipeline writes to a file; the Langfuse pipeline deletes every content key raglab
defines before anything else happens to a span, sends with Basic auth from the environment, and no
file holds a key; the stand-in replaces only the Langfuse pipeline's exporter. `otelcol validate`
and the fixture span's run need the binary: scripts/perf_smoke.py runs them in `make perf-smoke`."""

import re

import pytest
import yaml

from raglab.obs import names
from tests.conftest import ROOT, load_script

pytestmark = pytest.mark.unit
OTEL = ROOT / "deploy" / "otel"
smoke = load_script("perf_smoke")


def config(name: str) -> dict:
    return yaml.safe_load((OTEL / name).read_text(encoding="utf-8"))


def test_the_receiver_binds_the_loopback_interface_only():
    receivers = config("collector.yaml")["receivers"]
    assert list(receivers) == ["otlp"]
    protocols = receivers["otlp"]["protocols"]
    assert list(protocols) == ["http"]  # OTLP over HTTP: no gRPC
    assert protocols["http"]["endpoint"] == "127.0.0.1:${env:RAGLAB_OTELCOL_PORT}"
    for name in ("langfuse.yaml", "langfuse-stand-in.yaml"):
        assert "receivers" not in config(name), name  # no second receiver anywhere


def test_the_local_pipeline_writes_to_a_file_and_the_collector_serves_no_metrics():
    local = config("collector.yaml")
    assert local["exporters"] == {"file/local": {"path": "${env:RAGLAB_OTELCOL_TRACES}"}}
    assert local["service"]["pipelines"] == {
        "traces/local": {
            "receivers": ["otlp"],
            "processors": ["batch"],
            "exporters": ["file/local"],
        }
    }
    assert local["service"]["telemetry"]["metrics"] == {"level": "none"}


def test_the_langfuse_pipeline_deletes_every_content_key_raglab_defines_first():
    langfuse = config("langfuse.yaml")
    actions = langfuse["processors"]["attributes/content"]["actions"]
    assert all(action["action"] == "delete" for action in actions)
    deleted = [action["key"] for action in actions]
    assert sorted(deleted) == sorted({*names.CONTENT_KEYS, *names.NEVER_SET})
    assert sorted(smoke.CONTENT_KEYS) == sorted(deleted)  # the fixture carries every one
    pipeline = langfuse["service"]["pipelines"]["traces/langfuse"]
    assert pipeline["receivers"] == ["otlp"]
    assert pipeline["processors"][0] == "attributes/content"
    assert pipeline["exporters"] == ["otlp_http/langfuse"]


def test_the_langfuse_exporter_takes_its_endpoint_and_auth_from_the_environment():
    exporter = config("langfuse.yaml")["exporters"]["otlp_http/langfuse"]
    assert exporter == {
        "endpoint": "${env:LANGFUSE_OTEL_ENDPOINT}",
        "headers": {"Authorization": "Basic ${env:LANGFUSE_BASIC_AUTH}"},
    }


def test_no_file_holds_a_key():
    for path in sorted(OTEL.glob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"\b[ps]k-lf-", text), path.name  # Langfuse's key prefixes
        for line in text.splitlines():
            setting = line.split("#", 1)[0]
            if "Authorization" in setting or "endpoint" in setting:
                assert "${env:" in setting, f"{path.name}: {line.strip()}"


def test_the_stand_in_replaces_only_the_langfuse_pipelines_exporter():
    stand_in = config("langfuse-stand-in.yaml")
    assert stand_in["exporters"] == {
        "file/langfuse-stand-in": {"path": "${env:RAGLAB_OTELCOL_LANGFUSE_FILE}"}
    }
    assert stand_in["service"] == {
        "pipelines": {"traces/langfuse": {"exporters": ["file/langfuse-stand-in"]}}
    }


def test_the_smoke_runs_the_collector_with_placeholders_that_send_nothing(tmp_path):
    env = smoke.collector_env(4391, tmp_path / "t.jsonl", tmp_path / "l.jsonl")
    assert env["LANGFUSE_OTEL_ENDPOINT"].startswith("http://127.0.0.1:")
    assert env["LANGFUSE_BASIC_AUTH"] == "placeholder"
    assert set(env) == {
        "PATH",
        "HOME",
        "RAGLAB_OTELCOL_PORT",
        "RAGLAB_OTELCOL_TRACES",
        "RAGLAB_OTELCOL_LANGFUSE_FILE",
        "LANGFUSE_OTEL_ENDPOINT",
        "LANGFUSE_BASIC_AUTH",
    }
    assert smoke.CONFIGS == ("collector.yaml", "langfuse.yaml", "langfuse-stand-in.yaml")
