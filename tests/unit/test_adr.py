"""S5 AC13: ADR-002 quotes `raglab cost`'s output word for word. Rendered again here from the
committed judged record, price table and assumptions, the output must appear in the ADR, so a cost
edited by hand, or a price or a record changed without the ADR, fails."""

import re
from pathlib import Path

import pytest

from raglab.evals import cost
from tests.conftest import ROOT

pytestmark = pytest.mark.unit
ADR = ROOT / "docs" / "decisions" / "ADR-002-providers.md"


def test_the_adrs_estimate_is_raglab_costs_output_for_the_committed_record_and_table():
    text = ADR.read_text(encoding="utf-8")
    found = re.search(r"^Tokens: (\S+) \(judged;", text, flags=re.M)
    assert found, "ADR-002 quotes raglab cost's output, from its Tokens line"
    run_dir = ROOT / "runs" / "published" / found.group(1)
    assert (run_dir / "manifest.json").is_file(), f"{found.group(1)} is not a published record"
    output = cost.report(
        ROOT, run_dir, Path("config/prices.toml"), Path("config/cost-assumptions.toml")
    )
    assert output in text, (
        "ADR-002's estimate is not raglab cost's output: run make cost and copy it word for word"
    )


def test_the_adr_names_the_choice_it_waits_for_and_its_sources():
    text = ADR.read_text(encoding="utf-8")
    assert "## Decision (D6)" in text
    for source in ("[A1]", "[A2]", "[A3]", "[O1]", "[O2]"):
        assert re.search(rf"^- {re.escape(source)} \S", text, flags=re.M), source
