"""docs/GO-PUBLIC.md step 9: .github/workflows/pages.yml publishes the playground to GitHub Pages.

It deploys from main only, never on a pull request; each job holds only the permissions it needs;
every action is pinned to a full commit SHA with its release; it needs no key and runs nothing but
the layout. The site it uploads is the layout `make playground` serves, as plain files, and every
path the page loads resolves below the project path it is served at, not at the site root.
"""

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urljoin

import pytest
import yaml

from tests.conftest import ROOT, load_script

pytestmark = pytest.mark.unit
WORKFLOWS = ROOT / ".github" / "workflows"
PAGES = WORKFLOWS / "pages.yml"
PAGES_URL = "https://willcoliveira.github.io/ai-testing-rag-lab/"
LAYOUT = "python3 scripts/serve_playground.py --out _site"
NODE = shutil.which("node")
# a step that uses an action pinned to a full commit SHA, with its release as the comment
PIN = re.compile(r"^\s*(?:- )?uses: (actions/[\w.-]+)@([0-9a-f]{40}) # (v\d+\.\d+\.\d+)$")


def load(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if True in data:  # YAML 1.1 reads the key `on` as True
        data["on"] = data.pop(True)
    return data


def uses_lines(path: Path) -> list[str]:
    return [
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.lstrip().startswith(("uses:", "- uses:"))
    ]


def tree(site: Path) -> dict[str, bytes]:
    """Every file below site, links followed, by its path relative to site."""
    files: dict[str, bytes] = {}
    for folder, _, names in os.walk(site, followlinks=True):
        for name in names:
            path = Path(folder) / name
            files[path.relative_to(site).as_posix()] = path.read_bytes()
    return files


def test_pages_deploys_from_main_only_never_on_a_pull_request():
    wf = load(PAGES)
    assert set(wf["on"]) == {"push", "workflow_dispatch"}, "a push to main or by hand, no other"
    assert wf["on"]["push"] == {
        "branches": ["main"],
        "paths": [
            "playground/**",
            "runs/published/**",
            "scripts/serve_playground.py",
            ".github/workflows/pages.yml",
        ],
    }
    deploy = wf["jobs"]["deploy"]
    assert deploy["needs"] == "build"
    assert deploy["if"] == "github.ref == 'refs/heads/main'"  # a manual run elsewhere never deploys
    assert deploy["environment"] == {
        "name": "github-pages",
        "url": "${{ steps.deployment.outputs.page_url }}",
    }


def test_pages_jobs_hold_only_the_permissions_they_need():
    wf = load(PAGES)
    assert wf["permissions"] == {}
    assert set(wf["jobs"]) == {"build", "deploy"}
    assert wf["jobs"]["build"]["permissions"] == {"contents": "read"}
    assert wf["jobs"]["deploy"]["permissions"] == {"pages": "write", "id-token": "write"}


def test_pages_actions_are_pinned_by_sha_with_their_release():
    lines = uses_lines(PAGES)
    assert len(lines) == 3
    unpinned = [line.strip() for line in lines if not PIN.match(line)]
    assert not unpinned, f"not pinned to a full SHA with a # vX.Y.Z comment: {unpinned}"
    pins = {m[1]: (m[2], m[3]) for line in lines if (m := PIN.match(line))}
    assert set(pins) == {
        "actions/checkout",
        "actions/upload-pages-artifact",
        "actions/deploy-pages",
    }
    # an action both workflows use has one pin, so a Dependabot bump moves them together
    for line in uses_lines(WORKFLOWS / "pr-fast.yml"):
        if (m := PIN.match(line)) and m[1] in pins:
            assert (m[2], m[3]) == pins[m[1]], m[1]


def test_pages_is_hardened_as_pr_fast_and_needs_no_key():
    wf = load(PAGES)
    assert wf["concurrency"] == {"group": "pages", "cancel-in-progress": False}
    for name, job in wf["jobs"].items():
        assert job["runs-on"] == "ubuntu-24.04", name
        assert 0 < job["timeout-minutes"] <= 10, name
        assert "env" not in job, name
        for step in job["steps"]:
            assert "env" not in step, name
    assert "env" not in wf
    steps = [step for job in wf["jobs"].values() for step in job["steps"]]
    [checkout] = [s for s in steps if s.get("uses", "").startswith("actions/checkout@")]
    assert checkout["with"] == {"persist-credentials": False}
    # the site never calls a model: the only command is the layout, and no secret is read
    assert [s["run"] for s in steps if "run" in s] == [LAYOUT]
    assert "secrets." not in PAGES.read_text(encoding="utf-8")


def test_pages_uploads_the_site_make_playground_serves(tmp_path):
    """The build job's command, run in a copy of the site's sources, writes the same files with
    the same bytes as the linked site `make playground` serves, as plain files (no link), and the
    upload step takes that directory."""
    steps = load(PAGES)["jobs"]["build"]["steps"]
    [layout] = [s for s in steps if "run" in s]
    argv = shlex.split(layout["run"])
    assert argv[:3] == ["python3", "scripts/serve_playground.py", "--out"]
    [upload] = [s for s in steps if s.get("uses", "").startswith("actions/upload-pages-artifact@")]
    assert upload["with"] == {"path": argv[3]}
    assert steps.index(layout) < steps.index(upload)

    repo = tmp_path / "repo"
    for part in ("playground", "runs/published"):
        shutil.copytree(ROOT / part, repo / part)
    (repo / "scripts").mkdir()
    shutil.copy2(ROOT / "scripts" / "serve_playground.py", repo / "scripts")
    subprocess.run([sys.executable, *argv[1:]], cwd=repo, check=True, capture_output=True)
    uploaded = repo / argv[3]
    served = load_script("serve_playground").build_site(repo, tmp_path / "served")
    assert tree(uploaded) == tree(served)
    assert {"index.html", "app.js", "model.js", "runs/published/index.json"} <= set(tree(uploaded))
    assert not [path for path in uploaded.rglob("*") if path.is_symlink()]


def test_pages_out_never_empties_an_existing_directory(tmp_path):
    """--out takes a new directory only, so a mistyped path (`.`) is never emptied first."""
    keep = tmp_path / "keep.txt"
    keep.write_text("kept")
    done = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "serve_playground.py"), "--out", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert done.returncode == 2
    assert "exists" in done.stderr
    assert keep.read_text() == "kept"


@pytest.mark.skipif(NODE is None, reason="the page's script runs in node with a stand-in DOM")
def test_every_path_the_page_loads_resolves_below_the_project_path(tmp_path):
    """Pages serves the site at /ai-testing-rag-lab/, not at the site root: the files the page
    names (its stylesheet, script and imports) and every path it fetches while each published run
    is clicked in turn resolve below that path, to a file of the uploaded site. A path that
    starts with "/" would leave it."""
    site = load_script("serve_playground").build_site(ROOT, tmp_path / "_site", copy=True)
    named = re.findall(r'(?:src|href)="([^"]+)"', (site / "index.html").read_text(encoding="utf-8"))
    for script in sorted(site.glob("*.js")):
        source = script.read_text(encoding="utf-8")
        named += re.findall(r'^import .* from "([^"]+)";$', source, flags=re.M)
    done = subprocess.run(
        [str(NODE), str(ROOT / "tests" / "playground_dom.mjs"), str(site / "runs" / "published")],
        capture_output=True,
        text=True,
        check=True,
    )
    fetched = json.loads(done.stdout)["fetchedAll"]
    for ref in [*named, *fetched]:
        url = urljoin(PAGES_URL, ref)
        assert url.startswith(PAGES_URL), f"{ref} resolves to {url}, outside the project path"
        assert (site / url.removeprefix(PAGES_URL)).is_file(), f"{ref}: not a file of the site"
    assert set(named) == {"app.css", "app.js", "./model.js"}
    index = json.loads((site / "runs" / "published" / "index.json").read_text(encoding="utf-8"))
    assert "runs/published/index.json" in fetched
    for run in index["runs"]:
        assert f"runs/published/{run['path']}manifest.json" in fetched, run["run_id"]
