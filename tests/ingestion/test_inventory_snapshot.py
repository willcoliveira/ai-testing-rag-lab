"""AC6: the committed inventory snapshot (corpus/inventory.snapshot.json) is what the pipeline
produces at the default settings, so any parser, chunker or corpus change shows up as a diff
that `make inventory-snapshot` regenerates on purpose and the PR review reads.

OCR text depends on the Tesseract build. When the running Tesseract is not the version the
snapshot recorded (pr-fast runs the Ubuntu package, the snapshot may come from a Mac), the scanned
page's chunks are compared by id, document, section and page only; their text is checked by
character error rate in test_ocr.py. Every other chunk is compared field by field everywhere.
"""

import json
import subprocess
import sys

import pytest

from raglab.ingest import inventory
from tests.conftest import ROOT
from tests.ingestion_support import default_inventory

pytestmark = pytest.mark.ingestion

SNAPSHOT = ROOT / "corpus" / "inventory.snapshot.json"
OCR_TEXT_FIELDS = ("length", "first_words", "sha256")


def committed() -> dict:
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


def comparable(snapshot: dict, same_tesseract: bool) -> dict:
    """The snapshot without what legitimately varies with the Tesseract build."""
    out = json.loads(json.dumps(snapshot))
    out["tools"].pop("tesseract", None)
    if not same_tesseract:
        ocr_docs = {d["doc"] for d in out["documents"] if d["format"] == "png"}
        for row in out["chunks"]:
            if row["doc"] in ocr_docs:
                for field in OCR_TEXT_FIELDS:
                    row.pop(field)
    return out


@pytest.mark.ocr
def test_committed_snapshot_matches_a_fresh_run():
    kept = committed()
    fresh: dict = inventory.snapshot_json(default_inventory())
    same = kept["tools"].get("tesseract") == fresh["tools"].get("tesseract")
    if comparable(kept, same) != comparable(fresh, same):
        summary = inventory.diff_summary(kept, fresh)
        pytest.fail(
            "corpus/inventory.snapshot.json differs from a fresh run; if the change is intended,"
            f" run `make inventory-snapshot` and review the diff:\n{summary}"
        )


def test_snapshot_is_at_the_default_settings_and_lists_every_chunk_field():
    kept = committed()
    assert kept["settings"] == {"chunk_size": 1200, "overlap": 1}
    assert kept["schema_version"] == inventory.SCHEMA_VERSION
    assert {"pypdf", "pyyaml", "pytesseract", "tesseract"} <= set(kept["tools"])
    for row in kept["chunks"]:
        assert set(row) == {"id", "doc", "section", "page", "length", "first_words", "sha256"}
    assert sum(d["chunks"] for d in kept["documents"]) == len(kept["chunks"])


def test_a_changed_chunk_shows_up_in_the_diff():
    kept = committed()
    edited = json.loads(json.dumps(kept))
    edited["chunks"][0]["sha256"] = "0" * 64
    removed = edited["chunks"].pop()
    edited["chunks"].append({**removed, "id": removed["id"] + "-new"})
    changes = inventory.diff(kept, edited)
    assert changes["changed"] == [kept["chunks"][0]["id"]]
    assert changes["removed"] == [removed["id"]]
    assert changes["added"] == [removed["id"] + "-new"]
    summary = inventory.diff_summary(kept, edited)
    assert "1 added, 1 removed, 1 changed" in summary


@pytest.mark.ocr
def test_snapshot_comparison_still_fails_when_a_non_ocr_chunk_changes():
    kept = committed()
    edited = json.loads(json.dumps(kept))
    row = next(r for r in edited["chunks"] if r["doc"] == "A-MFA")
    row["first_words"] = "something else"
    assert comparable(kept, False) != comparable(edited, False)
    ocr_row = next(r for r in edited["chunks"] if r["doc"] == "A-DEVICE-B")
    row["first_words"] = next(r for r in kept["chunks"] if r["id"] == row["id"])["first_words"]
    ocr_row["sha256"] = "0" * 64
    assert comparable(kept, False) == comparable(edited, False)
    assert comparable(kept, True) != comparable(edited, True)


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "raglab", "ingest", *args],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )


@pytest.mark.ocr
def test_cli_writes_the_inventory_and_compares_with_the_snapshot(tmp_path):
    out = tmp_path / "inventory.json"
    result = run_cli("--out", str(out), "--compare", "corpus/inventory.snapshot.json")
    assert result.returncode == 0, result.stderr
    assert "ingested 18 documents" in result.stdout
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["settings"] == {"chunk_size": 1200, "overlap": 1}
    assert {d["doc_id"] for d in data["documents"]} == {r["doc"] for r in committed()["chunks"]}
    assert all(c["text"] and c["tenant"] for c in data["chunks"])


@pytest.mark.unit
@pytest.mark.parametrize(
    ("args", "message"),
    [
        (["--chunk-size", "0"], "chunk size must be at least 1"),
        (["--overlap", "-1"], "overlap must be 0 or more"),
        (["--chunk-size", "600", "--snapshot", "x.json"], "default settings only"),
    ],
)
def test_cli_refuses_bad_settings(args, message):
    result = run_cli(*args)
    assert result.returncode == 2
    assert message in result.stderr
