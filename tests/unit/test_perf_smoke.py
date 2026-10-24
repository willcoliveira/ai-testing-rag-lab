"""S9 OB9 and OB7 offline: scripts/perf_smoke.py pins k6 2.3.0 and the collector v0.162.0 by
sha256 and refuses any archive that differs; a pid file left by a killed run refuses the next
start; the trace check finds a missing span, a planted marker, a content key past the Langfuse
pipeline and a fixture that did not arrive; the postcheck finds a process or a port left over;
perf/smoke.js runs one user with a warm-up and a fixed count, its checks and failures thresholds
on, and its median threshold equal to THRESHOLDS.md's cell. Nothing is downloaded and nothing
starts: the binaries' real runs are `make perf-smoke`'s."""

import hashlib
import io
import json
import re
import tarfile
from pathlib import Path

import pytest

from tests.conftest import ROOT, load_script

pytestmark = pytest.mark.unit
smoke = load_script("perf_smoke")
SCRIPT = (ROOT / "perf" / "smoke.js").read_text(encoding="utf-8")


def test_the_pins():
    assert (smoke.K6.version, smoke.OTELCOL.version) == ("2.3.0", "0.162.0")
    assert smoke.K6.archives[("Linux", "x86_64")] == smoke.Archive(
        "https://github.com/grafana/k6/releases/download/v2.3.0/k6-v2.3.0-linux-amd64.tar.gz",
        "39c3117b6af817592dcd0ce4242105c0a7af10948c2a425306f0be8f7a8a8ab1",
        "k6-v2.3.0-linux-amd64/k6",
    )
    assert smoke.K6.archives[("Darwin", "arm64")].sha256 == (
        "b2417a3038edc5fe81dc178a889237724b595c5c9cfed875822008e46e862c7d"
    )
    linux = smoke.OTELCOL.archives[("Linux", "x86_64")]
    assert linux.url.endswith("/v0.162.0/otelcol_0.162.0_linux_amd64.tar.gz")
    assert linux.sha256 == "f99929987a915d3c6b2c9b15bc4938c5cea903a37a3f49e478024a0fa0772339"
    assert smoke.OTELCOL.archives[("Darwin", "arm64")].sha256 == (
        "53de34c02913f54aa240861e0febf67a6839bc8ecf1bfab83a8ae7d355d30674"
    )
    for tool in (smoke.K6, smoke.OTELCOL):
        for archive in tool.archives.values():
            assert archive.url.startswith("https://github.com/"), archive.url
            assert re.fullmatch(r"[0-9a-f]{64}", archive.sha256)


def tar_gz(member: str, data: bytes) -> bytes:
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w:gz") as bundle:
        info = tarfile.TarInfo(member)
        info.size = len(data)
        bundle.addfile(info, io.BytesIO(data))
    return out.getvalue()


def tool_for(tmp_path: Path, monkeypatch, content: bytes, sha: str):
    monkeypatch.setattr(smoke.platform, "system", lambda: "Linux")
    monkeypatch.setattr(smoke.platform, "machine", lambda: "x86_64")
    archive = smoke.Archive("https://github.com/x/y/releases/download/v1/tool.tar.gz", sha, "tool")
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "tool.tar.gz").write_bytes(content)
    return smoke.Tool("tool", "1", {("Linux", "x86_64"): archive}), cache


def test_a_cached_archive_that_matches_its_pin_gives_its_binary(tmp_path, monkeypatch):
    content = tar_gz("tool", b"#!/bin/sh\necho ok\n")
    tool, cache = tool_for(tmp_path, monkeypatch, content, hashlib.sha256(content).hexdigest())
    binary = smoke.fetch(tool, cache, tmp_path / "bin")
    assert binary.read_bytes() == b"#!/bin/sh\necho ok\n"
    assert binary.stat().st_mode & 0o111


def test_one_character_of_a_pin_changed_refuses_the_archive(tmp_path, monkeypatch):
    """OB7's break: the fetch refuses an archive whose sha256 is not the pin, and extracts
    nothing."""
    content = tar_gz("tool", b"binary")
    real = hashlib.sha256(content).hexdigest()
    changed = ("0" if real[0] != "0" else "1") + real[1:]
    tool, cache = tool_for(tmp_path, monkeypatch, content, changed)
    with pytest.raises(smoke.SmokeError, match="not the pinned"):
        smoke.fetch(tool, cache, tmp_path / "bin")
    assert not (tmp_path / "bin").exists()


def test_a_download_whose_sum_differs_is_not_kept(tmp_path, monkeypatch):
    content = tar_gz("tool", b"binary")
    tool, cache = tool_for(tmp_path, monkeypatch, content, "a" * 64)
    (cache / "tool.tar.gz").unlink()
    monkeypatch.setattr(smoke, "download", lambda url, target: target.write_bytes(content))
    with pytest.raises(smoke.SmokeError, match="nothing was kept"):
        smoke.fetch(tool, cache, tmp_path / "bin")
    assert list(cache.iterdir()) == []


def test_only_release_archives_from_github_are_downloaded(tmp_path):
    with pytest.raises(smoke.SmokeError, match=r"come from github\.com"):
        smoke.download("https://example.com/k6.tar.gz", tmp_path / "x")


def test_a_pid_file_left_by_a_killed_run_refuses_the_start(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(smoke, "ROOT", tmp_path)
    monkeypatch.setattr(smoke, "WORK", tmp_path / "runs" / "tmp" / "perf")
    smoke.WORK.mkdir(parents=True)
    (smoke.WORK / "otelcol.pid").write_text("4242\n", encoding="utf-8")

    def nothing_starts(*args, **kwargs):
        raise AssertionError("nothing may start")

    monkeypatch.setattr(smoke.subprocess, "Popen", nothing_starts)
    monkeypatch.setattr(smoke, "fetch", nothing_starts)
    monkeypatch.setattr(smoke, "port_open", lambda port: False)
    assert smoke.main(["--port", "1", "--otlp-port", "2"]) == 1
    out = capsys.readouterr().out
    assert "may still be running (pid 4242)" in out
    assert out.splitlines()[-1].startswith("perf-smoke: failed: ")


def otlp_line(spans: list[dict]) -> str:
    return json.dumps(
        {"resourceSpans": [{"scopeSpans": [{"scope": {"name": "raglab"}, "spans": spans}]}]}
    )


def span(trace: str, name: str, **attributes: str) -> dict:
    values = [
        {"key": k.replace("_", "."), "value": {"stringValue": v}} for k, v in attributes.items()
    ]
    return {"traceId": trace, "spanId": "1" * 16, "name": name, "attributes": values}


def ask_trace(trace: str) -> list[dict]:
    return [span(trace, name) for name in smoke.SPANS]


def fixture(with_keys: bool) -> dict:
    """The fixture span as a file holds it: with every content key (the local pipeline) or with
    none (past the Langfuse pipeline's delete)."""
    keys = smoke.CONTENT_KEYS if with_keys else ()
    return {
        "traceId": smoke.FIXTURE_TRACE,
        "spanId": "2" * 16,
        "name": "raglab.ask",
        "attributes": [{"key": k, "value": {"stringValue": "x"}} for k in keys],
    }


def write_files(tmp_path: Path, local: list[dict], stand_in: list[dict]) -> tuple[Path, Path]:
    traces, standing = tmp_path / "traces.jsonl", tmp_path / "stand-in.jsonl"
    traces.write_text(otlp_line(local) + "\n", encoding="utf-8")
    standing.write_text(otlp_line(stand_in) + "\n", encoding="utf-8")
    return traces, standing


def good(tmp_path: Path) -> tuple[Path, Path]:
    asks = [*ask_trace("a" * 32), *ask_trace("b" * 32)]
    return write_files(tmp_path, [*asks, fixture(True)], [*asks, fixture(False)])


def test_complete_traces_pass_the_check(tmp_path):
    traces, stand_in = good(tmp_path)
    assert smoke.check_traces(traces, stand_in, 2, ["perf-marker-01"]) == []


def test_the_check_finds_each_fault(tmp_path):
    traces, stand_in = good(tmp_path)
    assert "2 traces of POST /ask" in smoke.check_traces(traces, stand_in, 3, [])[0]
    missing = [s for s in ask_trace("c" * 32) if not s["name"].startswith("chat")]
    traces, stand_in = write_files(tmp_path, [*missing, fixture(True)], [*missing, fixture(False)])
    assert any("lack a span" in p for p in smoke.check_traces(traces, stand_in, 1, []))
    traces, stand_in = good(tmp_path)
    with traces.open("a", encoding="utf-8") as out:
        out.write(otlp_line([span("d" * 32, "x", raglab_status="perf-marker-03")]) + "\n")
    assert any("markers" in p for p in smoke.check_traces(traces, stand_in, 2, ["perf-marker-03"]))
    asks = ask_trace("e" * 32)
    traces, stand_in = write_files(tmp_path, [*asks, fixture(True)], [*asks, fixture(True)])
    assert any("let content keys through" in p for p in smoke.check_traces(traces, stand_in, 1, []))
    traces, stand_in = write_files(tmp_path, asks, asks)
    found = smoke.check_traces(traces, stand_in, 1, [])
    assert any("did not reach" in p for p in found)
    assert any("did not pass the Langfuse pipeline" in p for p in found)


class Running:
    pid = 999_999_999

    def poll(self):
        return None


def test_the_postcheck_finds_a_process_or_a_port_left(tmp_path, monkeypatch):
    monkeypatch.setattr(smoke, "ROOT", tmp_path)
    monkeypatch.setattr(smoke, "port_open", lambda port: port == 2)
    pid_file = tmp_path / "otelcol.pid"
    pid_file.write_text("1\n", encoding="utf-8")
    problems = smoke.postcheck({"collector": Running(), "server": None}, {"a": 1, "b": 2}, pid_file)
    assert problems == [
        "the b's port 2 still answers",
        "the collector (pid 999999999) is still running",
        "otelcol.pid was not removed",
    ]


def test_the_k6_script_runs_one_user_a_warm_up_and_a_fixed_count():
    assert "vus: 1," in SCRIPT
    assert "executor: 'per-vu-iterations'" in SCRIPT
    assert re.search(r"^const WARMUP = \d+;$", SCRIPT, flags=re.M)
    assert re.search(r"^const COUNT = \d+;$", SCRIPT, flags=re.M)
    assert "iterations: WARMUP + COUNT," in SCRIPT
    assert "checks: ['rate==1']," in SCRIPT
    assert "http_req_failed: ['rate==0']," in SCRIPT
    assert "thresholds.ask_duration = [`med<${MEDIAN_THRESHOLD_MS}`];" in SCRIPT
    assert "summaryTrendStats: ['avg', 'min', 'med', 'max', 'p(90)', 'p(95)']," in SCRIPT
    assert "if (!warmup) {\n    askDuration.add(response.timings.duration);" in SCRIPT
    markers = smoke.MARKER.findall(SCRIPT)
    questions = re.findall(r"^  '(.*)',$", SCRIPT, flags=re.M)
    assert len(questions) == len(markers) == len(set(markers)) >= 5
    assert all(any(m in q for m in markers) for q in questions)


def test_the_k6_scripts_questions_are_none_of_the_golden_sets():
    golden = (ROOT / "datasets" / "golden.v1.jsonl").read_text(encoding="utf-8")
    questions = {json.loads(line).get("question") for line in golden.splitlines() if line}
    written = re.findall(r"^  '(.*) perf-marker-\d+',$", SCRIPT, flags=re.M)
    assert written
    assert not set(written) & questions


def thresholds_cell() -> str:
    text = (ROOT / "docs" / "THRESHOLDS.md").read_text(encoding="utf-8")
    row = re.search(r"^\| k6 smoke: /ask median .*$", text, flags=re.M)
    assert row is not None, "THRESHOLDS.md has no k6 row"
    return row.group(0).split("|")[3].strip()


def test_the_scripts_threshold_equals_the_thresholds_cell():
    """OB10: the median's threshold T is written in one place for people (THRESHOLDS.md) and one
    for k6 (perf/smoke.js); they must agree. Until the ten runs set it, both say it is not set."""
    value = smoke.script_constant("MEDIAN_THRESHOLD_MS")
    cell = thresholds_cell()
    if value == "null":
        assert cell.startswith("not set"), cell
    else:
        assert cell.startswith(f"median < {value} ms"), cell


def test_the_make_target_runs_the_script_offline():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    target = re.search(r"^perf-smoke:\n\t(.*)$", makefile, flags=re.M)
    assert target is not None
    assert target.group(1) == (
        "HF_HUB_OFFLINE=1 uv run python scripts/perf_smoke.py --port $(PERF_PORT) "
        "--otlp-port $(PERF_OTLP_PORT)"
    )
    check = re.search(r"^check:(.*)$", makefile, flags=re.M)
    assert check is not None
    assert "perf-smoke" not in check.group(1).split()  # the perf job runs it, not make check
    assert (smoke.CONFIG, smoke.SCRIPT) == ("config/perf.toml", "perf/smoke.js")
