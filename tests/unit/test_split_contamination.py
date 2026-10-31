"""S8 (GA9): test-split contamination. Every test-split id of golden.v2.jsonl (the latest golden
file) appears in none of: src/, config/, datasets/security/, the prompts, docs/THRESHOLDS.md, or a
published record on the dev split; the test-split runs that exist are v1.1's under gate release
(the plan: "no test-split run on v2 has been made yet; v0.2.0's release makes the first").
Runs in `make test` (pr-fast's test step, no workflow change). The break: a test-split id planted
in a comment of src/raglab/guard/injection.py, on a copy of the tree's scan."""

import json
import re
from pathlib import Path

import pytest

from tests.conftest import ROOT

pytestmark = pytest.mark.unit
GOLDEN = ROOT / "datasets" / "golden.v2.jsonl"
SCANNED = ("src", "config", "datasets/security", "docs/THRESHOLDS.md")
PROMPTS = "src/raglab/generate/prompts"
PUBLISHED = ROOT / "runs" / "published"
HELD_OUT_GATES = ("nightly", "release")


def held_out_ids(golden: Path = GOLDEN) -> set[str]:
    lines = [
        json.loads(line) for line in golden.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    return {str(line["id"]) for line in lines if line["split"] == "test"}


def pattern(ids: set[str]) -> re.Pattern[str]:
    """An id as a whole token: G-02 is not inside G-020 or XG-02."""
    return re.compile(
        r"(?<![\w-])(?:" + "|".join(re.escape(i) for i in sorted(ids)) + r")(?![\w-])"
    )


def files_under(root: Path, places: tuple[str, ...] = SCANNED) -> list[Path]:
    found: list[Path] = []
    for place in places:
        path = root / place
        if path.is_file():
            found.append(path)
        elif path.is_dir():
            found += [
                p for p in sorted(path.rglob("*")) if p.is_file() and "__pycache__" not in p.parts
            ]
    return found


def hits(root: Path, ids: set[str], places: tuple[str, ...] = SCANNED) -> list[str]:
    """Each file under the scanned places holding a test-split id, with the id."""
    found: list[str] = []
    regex = pattern(ids)
    for path in files_under(root, places):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for match in sorted(set(regex.findall(text))):
            found.append(f"{path.relative_to(root).as_posix()}: {match}")
    return found


def dev_record_hits(published: Path, ids: set[str]) -> list[str]:
    """Each published dev record whose cases hold a test-split id."""
    found: list[str] = []
    for manifest_path in sorted(published.glob("*/manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["split"] != "dev":
            continue
        cases = manifest_path.parent / "cases.jsonl"
        for line in cases.read_text(encoding="utf-8").splitlines():
            case = json.loads(line)
            if case["case_id"] in ids or case.get("split") == "test":
                found.append(f"{manifest_path.parent.name}: {case['case_id']}")
                break
    return found


def test_no_test_split_id_is_in_the_code_the_configs_the_pack_the_prompts_or_the_thresholds():
    ids = held_out_ids()
    assert len(ids) == 53, "golden set v2's test split: 12 retrieval questions and 41 cases"
    assert hits(ROOT, ids) == []
    assert (ROOT / PROMPTS).is_dir()
    assert hits(ROOT, ids, (PROMPTS,)) == []


def test_no_published_dev_record_holds_a_test_split_case():
    ids = held_out_ids()
    assert dev_record_hits(PUBLISHED, ids) == []


def test_the_test_split_runs_that_exist_are_v1_1s_under_release():
    v2 = json.loads(GOLDEN.read_text(encoding="utf-8").splitlines()[0])
    assert v2
    found: list[tuple[str, str, str]] = []
    for manifest_path in sorted(PUBLISHED.glob("*/manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["split"] in ("test", "all"):
            found.append((manifest_path.parent.name, manifest["gate"], manifest["dataset"]["path"]))
    assert found, "v0.1.0's test slice is published"
    for run_id, gate, dataset in found:
        assert gate in HELD_OUT_GATES, (run_id, gate)
        assert dataset == "datasets/golden.v1.jsonl", (run_id, dataset)
    assert all(gate == "release" for _, gate, _ in found)


def test_a_planted_id_in_a_comment_of_the_injection_guard_is_named(tmp_path):
    ids = held_out_ids()
    planted = sorted(ids)[0]
    copy = tmp_path / "src" / "raglab" / "guard"
    copy.mkdir(parents=True)
    source = ROOT / "src" / "raglab" / "guard" / "injection.py"
    target = copy / "injection.py"
    target.write_text(
        source.read_text(encoding="utf-8") + f"\n# seen in {planted}\n", encoding="utf-8"
    )
    assert hits(tmp_path, ids, ("src",)) == [f"src/raglab/guard/injection.py: {planted}"]
    assert hits(ROOT, ids, ("src/raglab/guard/injection.py",)) == []
    # a longer id that holds the planted one is not a hit
    target.write_text(f"# X{planted}0 and {planted}1\n", encoding="utf-8")
    assert hits(tmp_path, ids, ("src",)) == []
