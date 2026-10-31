"""S8 (GA8): the suite audit report (docs/audits/<date>-suite-audit-v0.2.md) has the seven
sections of the main plan's list, the not-covered list and the lab-versus-production line, and
scripts/audit_suite.py recounts every count of its Counts table from the files: a count edited
in the report fails naming the section; a section heading removed fails."""

import re
from pathlib import Path

import pytest

from tests.conftest import ROOT, load_script

pytestmark = pytest.mark.unit
audit = load_script("audit_suite")
REPORTS = sorted((ROOT / "docs" / "audits").glob("*-suite-audit-*.md"))
SECTIONS = (
    "## 1. Coverage cells against cases",
    "## 2. Skips",
    "## 3. Phrase-locked criteria",
    "## 4. Calibration record",
    "## 5. Test-split contamination",
    "## 6. Intervals and pairing",
    "## 7. Thresholds with reasons",
    "## Not covered",
    "## Counts",
)


def report() -> Path:
    assert REPORTS, "no suite audit report under docs/audits/"
    return REPORTS[-1]


def test_the_report_has_every_section_in_order_and_the_lab_line():
    text = report().read_text(encoding="utf-8")
    positions = [text.find(heading + "\n") for heading in SECTIONS]
    assert all(p >= 0 for p in positions), [
        h for h, p in zip(SECTIONS, positions, strict=True) if p < 0
    ]
    assert positions == sorted(positions)
    assert "Lab practice" in text or "what production would do" in text
    assert "```" in text, "every section quotes a command and its output"
    assert "R-22" in text.split("## Not covered", 1)[1]


def test_every_count_of_the_report_is_the_recount():
    assert audit.compare(report()) == []


def test_an_edited_count_fails_naming_the_section(tmp_path):
    text = report().read_text(encoding="utf-8")
    [row] = [
        line for line in text.splitlines() if line.startswith("| 6. intervals | published runs |")
    ]
    cells = [c.strip() for c in row.strip().strip("|").split("|")]
    edited = row.replace(f"| {cells[2]} |", f"| {int(cells[2]) + 1} |", 1)
    copy = tmp_path / "audit.md"
    copy.write_text(text.replace(row, edited, 1), encoding="utf-8")
    assert audit.compare(copy) == [
        f"6. intervals: 'published runs' is '{int(cells[2]) + 1}' in the report, recounted "
        f"{int(cells[2])!r}"
    ]
    removed = text.replace(row + "\n", "", 1)
    copy.write_text(removed, encoding="utf-8")
    assert audit.compare(copy) == [
        "6. intervals: 'published runs' is not in the report's Counts table"
    ]


def test_a_count_edited_in_the_prose_is_named(tmp_path):
    """The judge's S8-J6 (a): a number in a section's prose is recounted too."""
    text = report().read_text(encoding="utf-8")
    claim = "33 published runs carry 56 distinct metric keys in 336 (run, key) pairs"
    assert claim in text
    copy = tmp_path / "audit.md"
    copy.write_text(
        text.replace(
            claim,
            claim.replace("33 published", "34 published").replace("56 distinct", "57 distinct"),
            1,
        ),
        encoding="utf-8",
    )
    assert audit.compare(copy) == [
        "6. intervals: the prose says 34 for 'published runs', recounted 33",
        "6. intervals: the prose says 57 for 'published metric keys', recounted 56",
    ]
    copy.write_text(text.replace(claim, "the runs carry their keys", 1), encoding="utf-8")
    [problem] = audit.compare(copy)
    assert problem.startswith("6. intervals: the prose no longer states ")


def test_every_run_metric_pair_is_read_for_its_interval(tmp_path, monkeypatch):
    """The judge's S8-J6 (b): a metric without its interval in an earlier manifest, not the last
    one per key, lowers the pairs-with-interval count."""
    import json
    import shutil

    published = tmp_path / "runs" / "published"
    for run_id in (
        "20261006T172928Z-retrieval-dense-dev-5f1d3a0",
        "20261024T090200Z-retrieval-dense-dev-ade9397",
    ):
        shutil.copytree(ROOT / "runs" / "published" / run_id, published / run_id)
    monkeypatch.setattr(audit, "PUBLISHED", published)
    before = audit.counts()["6. intervals"]
    assert (before["published runs"], before["published (run, metric) pairs"]) == (2, 6)
    assert before["published (run, metric) pairs with an interval"] == 6
    earlier = published / "20261006T172928Z-retrieval-dense-dev-5f1d3a0" / "manifest.json"
    manifest = json.loads(earlier.read_text(encoding="utf-8"))
    del manifest["results"]["metrics"]["recall@5"]["ci_low"]
    earlier.write_text(json.dumps(manifest), encoding="utf-8")
    after = audit.counts()["6. intervals"]
    assert after["published (run, metric) pairs with an interval"] == 5
    assert after["published metric keys"] == 3


def test_a_removed_section_heading_is_named():
    text = report().read_text(encoding="utf-8")
    without = text.replace("## 5. Test-split contamination\n", "## 5. Contamination\n", 1)
    positions = [without.find(heading + "\n") for heading in SECTIONS]
    missing = [h for h, p in zip(SECTIONS, positions, strict=True) if p < 0]
    assert missing == ["## 5. Test-split contamination"]


def test_the_recount_reads_the_files_not_the_report():
    counts = audit.counts()
    assert set(counts) >= {"1. coverage", "2. skips", "5. contamination", "6. intervals"}
    coverage = counts["1. coverage"]
    assert coverage["requirements"] == 23
    assert coverage["judged criteria"] == 7
    assert coverage["Gate cells tbd"] == 0
    assert coverage["Gate cells not covered"] == "R-22"
    assert counts["5. contamination"]["test-split ids of golden.v2.jsonl"] == 53
    assert counts["2. skips"]["audit skips (AUDIT_SKIP)"] > 5, "the continuation lines are read"
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(counts["2. skips"]["audit skips review date"]))
    intervals = counts["6. intervals"]
    assert (
        intervals["published (run, metric) pairs with an interval"]
        == intervals["published (run, metric) pairs"]
    )
    assert intervals["published (run, metric) pairs"] >= intervals["published metric keys"]
