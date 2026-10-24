"""S6 JC10: docs/THRESHOLDS.md's calibration rows are the record's: per calibrated criterion its
status by the bar and its kappa with the interval. Until the labels are sealed and the record
exists, every calibrated criterion's row waits, so no criterion can be called trusted before its
record says so."""

import json
import re

import pytest

from raglab.evals import calibration
from tests.conftest import ROOT

pytestmark = pytest.mark.unit
FOLDER = ROOT / "datasets" / "calibration" / "judge-v2-c1"
SECTION = "### The calibration's verdicts (S6)"
WAITING = "waiting for the labels"


def rows() -> dict[str, list[str]]:
    text = (ROOT / "docs" / "THRESHOLDS.md").read_text(encoding="utf-8")
    assert f"\n{SECTION}\n" in text, "THRESHOLDS.md states the calibration's verdicts"
    body = text.split(f"\n{SECTION}\n", 1)[1].split("\n## ", 1)[0].split("\n### ", 1)[0]
    found: dict[str, list[str]] = {}
    for line in body.splitlines():
        if match := re.match(r"^\| `([a-z_]+)` \|", line):
            found[match.group(1)] = [c.strip() for c in line.strip().strip("|").split("|")]
    return found


def kappa_cell(block: dict) -> str:
    value = block["value"]
    if value is None:
        return "undefined"
    return f"{value:.3f} [{block['ci_low']:.3f}, {block['ci_high']:.3f}]"


def test_thresholds_calibration_rows_equal_the_record():
    bar = calibration.load_bar(FOLDER)
    found = rows()
    assert list(found) == [c.name for c in bar.criteria]
    path = FOLDER / calibration.RECORD_JSON
    if not path.exists():
        for name, cells in found.items():
            assert cells[1:4] == [WAITING, "-", "-"], f"{name}: no record yet, so it waits"
            assert "record.md" in cells[4]
        return
    record = json.loads(path.read_text(encoding="utf-8"))
    for name, cells in found.items():
        assert cells[1] == record["status"][name], name
        assert cells[2] == kappa_cell(record["agreement"][name]["kappa"]), name
