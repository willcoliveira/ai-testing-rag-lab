"""S3, the user's decision of 2026-10-18 ("Allow those IDs only"): the exceptions-register ids the
corpus plants may appear in published run records, because a model quotes them in its answers.
privacy/allowlist-published.txt enumerates exactly those ids (never a pattern), and the privacy
check applies it only under runs/published/. Another id of the same shape is still a hit there,
and so is a planted contact; the planted secret and personal details (F-44, F-45), which no
privacy pattern catches, are refused by publish itself from the answer key."""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from raglab.evals import publish, record
from raglab.ingest.answer_key import must_not_contain
from tests.conftest import ROOT
from tests.retrieval_support import fake_run, lab_root, read_run, reseal

pytestmark = pytest.mark.unit
NODE = shutil.which("node")
LIST = ROOT / "privacy" / "allowlist-published.txt"
ID = re.compile(r"^EX-\d{4}-\d{3}$")
# another id of the same shape, built here so this file holds none
OTHER_ID = "-".join(["EX", "2026", "999"])


def entries(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]


def corpus_ids() -> set[str]:
    found: set[str] = set()
    for path in (ROOT / "corpus").rglob("*.md"):
        found |= set(re.findall(r"\bEX-\d{4}-\d{3}\b", path.read_text(encoding="utf-8")))
    return found


def test_the_list_enumerates_exactly_the_planted_exception_ids():
    listed = entries(LIST)
    assert all(ID.match(entry) for entry in listed), listed  # whole ids, never a pattern
    assert set(listed) == corpus_ids()
    assert len(listed) == len(set(listed))


def run_check(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    assert NODE is not None
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["CI"] = "1"  # the example list only
    return subprocess.run(
        [NODE, "scripts/check-forbidden.mjs", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    if NODE is None:
        pytest.fail("node is required for the privacy check")
    shutil.copytree(ROOT / "scripts", tmp_path / "scripts")
    shutil.copytree(
        ROOT / "privacy",
        tmp_path / "privacy",
        ignore=shutil.ignore_patterns("forbidden-strings.txt"),
    )
    return tmp_path


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def answer_line(text: str) -> str:
    return '{"answer": "' + text + '", "case_id": "R-Q24"}\n'


def test_a_published_record_with_a_planted_id_passes(tree: Path):
    for entry in entries(LIST):
        write(tree, "runs/published/r/cases.jsonl", answer_line(f"Exception {entry} applies."))
        result = run_check(tree, "--dir", "runs/published/r")
        assert result.returncode == 0, result.stdout


@pytest.mark.parametrize("where", ["runs/tmp/r/cases.jsonl", "docs/x.md", "src/raglab/x.py"])
def test_the_planted_ids_are_hits_outside_runs_published(tree: Path, where: str):
    write(tree, where, answer_line(f"Exception {entries(LIST)[0]} applies."))
    write(tree, "files", where + "\0")
    assert run_check(tree, "--files-from", "files").returncode == 1


def test_another_id_of_the_same_shape_is_a_hit_under_runs_published(tree: Path):
    write(tree, "runs/published/r/cases.jsonl", answer_line(f"Exception {OTHER_ID} applies."))
    result = run_check(tree, "--dir", "runs/published/r")
    assert result.returncode == 1
    assert OTHER_ID.split("-")[0] + "-" + OTHER_ID.split("-")[1] in result.stdout


def test_a_planted_contact_is_a_hit_under_runs_published(tree: Path):
    [address, _phone] = must_not_contain(ROOT)["F-45"]
    write(tree, "runs/published/r/cases.jsonl", answer_line(f"Write to {address}."))
    assert run_check(tree, "--dir", "runs/published/r").returncode == 1


def plant(run_dir: Path, text: str) -> None:
    """Put text in a case's question and reseal the record (hashes, scores and report agree), so
    the run is valid and only the publish checks can refuse it."""
    _, cases = read_run(run_dir)
    cases[0]["question"] += f" {text}"
    reseal(run_dir, cases)


@pytest.mark.parametrize("feature", ["F-44", "F-45"])
def test_publish_refuses_the_planted_secret_and_personal_details(tmp_path, feature):
    for n, planted in enumerate(must_not_contain(ROOT)[feature]):
        root = lab_root(tmp_path / feature / str(n))
        run_dir = fake_run(root, provenance="local")
        plant(run_dir, f"leak {planted}")
        assert record.validate(run_dir, root) == []
        with pytest.raises(publish.PublishError, match=f"{feature}'s"):
            publish.publish(run_dir, root, privacy=lambda d, r: [])
        assert not (root / publish.PUBLISHED).exists()


@pytest.mark.skipif(NODE is None, reason="the privacy check needs node")
def test_publish_scans_at_the_published_path_and_removes_a_refused_copy(tmp_path):
    """The real check: a run quoting a planted id publishes; one quoting another id of the same
    shape is refused, and nothing of it is left under runs/published."""
    root = lab_root(tmp_path)
    shutil.copytree(ROOT / "scripts", root / "scripts")
    shutil.copytree(
        ROOT / "privacy", root / "privacy", ignore=shutil.ignore_patterns("forbidden-strings.txt")
    )
    good = fake_run(root, provenance="local")
    plant(good, f"see {entries(LIST)[0]}")
    assert publish.publish(good, root).is_dir()
    bad = fake_run(root, name="retrieval-other", provenance="local")
    plant(bad, f"see {OTHER_ID}")
    with pytest.raises(publish.PublishError, match="the privacy check found"):
        publish.publish(bad, root)
    assert not (root / publish.PUBLISHED / bad.name).exists()
