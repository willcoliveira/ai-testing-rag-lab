"""AC9: the static playground renders runs/published/index.json (run list, metrics with
intervals, per-question hits) with no network and no model. The page's data model
(playground/model.js) runs in Node against a published directory made by `raglab publish`; the
page itself loads nothing but its own files and the published runs, and writes text, never HTML.
A browser test of the page comes with Track B (Playwright)."""

import json
import re
import shutil
import subprocess
from datetime import UTC, datetime

import pytest

from raglab.evals import publish
from tests.conftest import ROOT, load_script
from tests.retrieval_support import lab_root, local_run

pytestmark = pytest.mark.unit
PLAYGROUND = ROOT / "playground"
NODE = shutil.which("node")


@pytest.mark.skipif(NODE is None, reason="the smoke check runs the page's model in node")
def test_the_page_model_renders_a_published_index(tmp_path):
    root = lab_root(tmp_path)
    run_dir = local_run(root)
    publish.publish(run_dir, root, baseline=True, privacy=lambda d, r: [])
    published = root / "runs" / "published"
    done = subprocess.run(
        [str(NODE), str(ROOT / "tests" / "playground_smoke.mjs"), str(published)],
        capture_output=True,
        text=True,
        check=True,
    )
    out = json.loads(done.stdout)
    [shown] = out["runs"]
    run = shown["run"]
    assert run["runId"] == run_dir.name
    assert run["baseline"] is True
    assert (run["config"], run["retriever"], run["provenance"]) == (
        "retrieval-fake",
        "dense, k 2",
        "local",
    )
    index = json.loads((published / "index.json").read_text())
    metric = index["runs"][0]["metrics"]["recall@2"]
    low, high = metric["ci_low"], metric["ci_high"]
    expected = f"{metric['value']:.3f} ({low:.3f} to {high:.3f}, n {metric['n']})"
    assert {"name": "recall@2", "text": expected} in run["metrics"]
    assert [c["caseId"] for c in shown["cases"]] == ["Q1", "Q2", "Q3", "Q4"]
    cases = [json.loads(line) for line in (run_dir / "cases.jsonl").read_text().splitlines()]
    for row, case in zip(shown["cases"], cases, strict=True):
        assert row["hit"] == (case["hit"] == 1)
        assert [r["id"] for r in row["retrieved"]] == [r["chunk_id"] for r in case["retrieved"]]
        assert [r["relevant"] for r in row["retrieved"]] == [
            r["relevant"] for r in case["retrieved"]
        ]
    assert {"label": "Provenance", "value": "local"} in shown["manifest"]
    assert out["refused"] == ["../x/", "https://example.org/", "/etc/", ".hidden/"]


def test_the_page_loads_only_its_own_files_and_writes_text_only():
    html = (PLAYGROUND / "index.html").read_text(encoding="utf-8")
    assert "default-src 'none'" in html
    assert "connect-src 'self'" in html
    assert re.findall(r'(?:src|href)="([^"]+)"', html) == ["app.css", "app.js"]
    for path in sorted(PLAYGROUND.glob("*.js")):
        source = path.read_text(encoding="utf-8")
        assert not re.search(
            r"innerHTML|outerHTML|insertAdjacentHTML|document\.write|eval\(", source
        ), path.name
        assert not re.search(r"https?://", source), f"{path.name} names a URL"
    app = (PLAYGROUND / "app.js").read_text(encoding="utf-8")
    assert re.findall(r"fetch\(([^,)]+)", app) == ["path"]
    assert "runs/published/" in (PLAYGROUND / "model.js").read_text(encoding="utf-8")


def test_the_local_site_serves_the_playground_next_to_the_published_runs(tmp_path):
    serve = load_script("serve_playground")
    root = tmp_path / "repo"
    shutil.copytree(PLAYGROUND, root / "playground")
    (root / "runs" / "published").mkdir(parents=True)
    (root / "runs" / "published" / "index.json").write_text("{}")
    site = serve.build_site(root, tmp_path / "site")
    assert sorted(p.name for p in site.iterdir()) == sorted(
        [*(p.name for p in PLAYGROUND.iterdir()), "runs"]
    )
    assert (site / "runs" / "published" / "index.json").read_text() == "{}"
    assert not (site / "pyproject.toml").exists()


@pytest.mark.skipif(NODE is None, reason="node checks the page's script syntax")
@pytest.mark.parametrize("name", ["app.js", "model.js"])
def test_the_page_scripts_parse(name):
    subprocess.run([str(NODE), "--check", str(PLAYGROUND / name)], check=True, capture_output=True)


@pytest.mark.skipif(NODE is None, reason="the page's script runs in node with a stand-in DOM")
def test_the_page_script_renders_runs_metrics_and_questions(tmp_path):
    """app.js itself (not only its model) against a published directory, with a minimal DOM and a
    fetch that reads the files: the run list, the newest run's metrics and questions, a click on
    the other run, no error in the status line, and only runs/published files fetched."""
    root = lab_root(tmp_path)
    older = local_run(root)
    newer = local_run(
        root, name="retrieval-hybrid", kind="hybrid", when=datetime(2026, 10, 7, tzinfo=UTC)
    )
    for run_dir in (older, newer):
        publish.publish(run_dir, root, privacy=lambda d, r: [])
    published = root / "runs" / "published"
    done = subprocess.run(
        [str(NODE), str(ROOT / "tests" / "playground_dom.mjs"), str(published)],
        capture_output=True,
        text=True,
        check=True,
    )
    out = json.loads(done.stdout)
    assert out["status"] == ""
    assert out["runs"][0].startswith("retrieval-hybrid")  # newest first
    assert out["runs"][1].startswith("retrieval-fake")
    assert "recall@2" in out["runs"][0]
    assert out["first"]["heading"] == ["retrieval-hybrid"]
    assert out["first"]["tables"] == [4, 5]  # 3 metrics + header; 4 questions + header
    assert out["second"]["heading"] == ["retrieval-fake"]
    assert out["pressed"] == ["false", "true"]
    assert all(path.startswith("runs/published/") for path in out["fetched"])


@pytest.mark.skipif(NODE is None, reason="the page's script runs in node with a stand-in DOM")
def test_the_page_shows_every_published_run_without_an_error():
    """GO-PUBLIC step 9: the page Pages serves shows each run of runs/published, clicked in turn,
    with its provenance, its interval method and its metrics, and never an error in the status
    line. A retrieval run adds its per-question rows; a generation or judged run, whose cases have
    other fields, names its cases file instead, and no row is filled in for it."""
    published = ROOT / "runs" / "published"
    index = json.loads((published / "index.json").read_text(encoding="utf-8"))
    done = subprocess.run(
        [str(NODE), str(ROOT / "tests" / "playground_dom.mjs"), str(published)],
        capture_output=True,
        text=True,
        check=True,
    )
    out = json.loads(done.stdout)
    assert out["status"] == ""
    assert [shown["run"] for shown in out["every"]] == [run["run_id"] for run in index["runs"]]
    for shown, run in zip(out["every"], index["runs"], strict=True):
        assert shown["status"] == "", run["run_id"]
        assert shown["heading"] == [run["config"]]
        meta = dict(zip(shown["meta"][::2], shown["meta"][1::2], strict=True))
        assert meta["Provenance"] == run["provenance"]
        manifest = json.loads((published / run["path"] / "manifest.json").read_text())
        if "bootstrap" in manifest:
            b = manifest["bootstrap"]
            interval = f"{b['resamples']} resamples, seed {b['seed']}, {round(b['level'] * 100)}%"
            assert meta["Bootstrap"] == interval
        else:
            i = manifest["intervals"]
            assert (
                meta["Intervals"] == f"{i['method']}, {round(i['level'] * 100)}%, per {i['unit']}"
            )
        metrics = len(run["metrics"]) + 1  # and the header row
        if run["suite"] == "retrieval":
            cases = (published / run["path"] / "cases.jsonl").read_text().splitlines()
            assert shown["tables"] == [metrics, len(cases) + 1]
            assert shown["notes"] == []
        else:
            assert shown["tables"] == [metrics]
            assert shown["notes"] == [
                f"Per-question rows are drawn for retrieval runs only; this {run['suite']} run's "
                f"cases are in runs/published/{run['path']}cases.jsonl."
            ]
