"""S6 JC1: the bar is written before any label, in `bar.toml` (which `raglab calibrate` reads) and
in docs/THRESHOLDS.md's judged section, and the two are held equal here. The bar is the
maintainer's answers of 2026-10-23: D1 "grounded and abstains, 15 each (Recommended)" and D2
"kappa 0.80 trusts, under 0.60 stops (Recommended)" (docs/plans/2026-10-23-s6-judge-calibration.md).
"""

import re
import tomllib

import pytest

from tests.conftest import ROOT

pytestmark = pytest.mark.unit
BAR = ROOT / "datasets" / "calibration" / "judge-v2-c1" / "bar.toml"
SECTION = "### The judge's calibration bar (S6)"


def bar() -> dict:
    return tomllib.loads(BAR.read_text(encoding="utf-8"))


def section() -> str:
    text = (ROOT / "docs" / "THRESHOLDS.md").read_text(encoding="utf-8")
    assert f"\n{SECTION}\n" in text, "THRESHOLDS.md states the calibration bar"
    return text.split(f"\n{SECTION}\n", 1)[1].split("\n## ", 1)[0].split("\n### ", 1)[0]


def table_rows(text: str) -> list[list[str]]:
    return [
        [c.strip() for c in line.strip().strip("|").split("|")]
        for line in text.splitlines()
        if re.match(r"^\| `[a-z_]+` \|", line)
    ]


def bar_rows(data: dict) -> list[list[str]]:
    """THRESHOLDS.md's rows as bar.toml gives them: criterion, items (judge pass, judge fail), the
    three statuses' ranges and the status of an undefined kappa."""
    rows = []
    for name, c in data["criteria"].items():
        trusted, stop = f"{c['trusted']:.2f}", f"{c['stop']:.2f}"
        rows.append(
            [
                f"`{name}`",
                f"{c['judge_pass'] + c['judge_fail']} ({c['judge_pass']}, {c['judge_fail']})",
                f"kappa >= {trusted}",
                f"{stop} <= kappa < {trusted}",
                f"kappa < {stop}",
                data["undefined"],
            ]
        )
    return rows


def test_thresholds_states_the_bar_of_bar_toml():
    """The equality test: each calibrated criterion's row in THRESHOLDS.md is bar.toml's, in its
    order, and nothing else; and the section says what the bar reads."""
    data = bar()
    assert table_rows(section()) == bar_rows(data)
    assert data["reads"] == "kappa"
    assert "the bar reads Cohen's kappa of the judge against the maintainer's sealed labels" in (
        " ".join(section().split())
    )
    assert "datasets/calibration/judge-v2-c1/bar.toml" in section()


def test_the_bar_is_the_maintainers_answers_d1_and_d2():
    """D1: grounded and abstains, 15 each (7 judge passes, 8 judge fails: the odd item goes to the
    fails); D2: kappa 0.80 trusts, under 0.60 stops; the seed and rule the plan wrote before the
    judged record exists."""
    data = bar()
    assert list(data["criteria"]) == ["grounded", "abstains"]
    for c in data["criteria"].values():
        assert (c["judge_pass"], c["judge_fail"], c["trusted"], c["stop"]) == (7, 8, 0.80, 0.60)
    assert data["sample"] == {"rule": "s6-1", "seed": 20261023}
    assert data["agreement"] == {"resamples": 2000, "level": 0.95, "seed": 20261023}
    assert data["relabel"] == {"per_criterion": 6, "min_gap_hours": 24}
    assert data["judge_prompt"] == "judge-v2"
