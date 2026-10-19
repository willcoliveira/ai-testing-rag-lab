"""The gates of docs/THRESHOLDS.md: the retrieval no-regression gate (S2, pr-fast) and the
consistency gate (S4, Q-05, local until keys exist).

**Retrieval.** A fresh run of the default configuration on the dev split is compared with the
published baseline of the same suite, config and split (runs/published/index.json). It passes when
recall@k is at least the baseline's minus a margin of one question (1 / n): the baseline is made on
one machine and CI runs on another, where the scanned page's OCR text (another Tesseract build) and
ONNX arithmetic in the last bits differ. Measured in the CI image (docs/THRESHOLDS.md): the same
top 5 for every dev question and scores within 0.0010, while the closest labelled chunk sits 0.0021
from the rank-k boundary, so one near-tied chunk may cross; the margin absorbs one such flip and no
more. A baseline made with a different dataset or config is stale, and the gate fails until a new
baseline is published in a reviewed pull request.

**Consistency (Q-05).** A finished dev run of the generation suite is compared with the published
local baseline of the same config: behaviour pass^N (raglab.evals.behaviour; a case passes only
when all N trials pass every check that applies) must be at least the baseline's minus the margin
docs/THRESHOLDS.md gives on its consistency row (`margin: M case(s)`, M / n of the baseline's
cases). The baseline is stale, and the gate fails asking for a new one in a reviewed pull request,
when the dataset sha256, the config sha256, the prompt fingerprint (the prompt is code, not
config), the model digest or the number of trials differs. A new Ollama version is not stale: it is
a change the gate exists to see. The gate refuses a fake run (the fake model's trials are
identical and its label is answer whenever a chunk is retrieved, so its pass^N measures the
plumbing, never Q-05), a partial run, a run on another split and a run without behaviour cases; and
while THRESHOLDS.md sets no margin (it is set from runs after the sign-off, never invented), it
refuses to judge. Either way it prints one line.
"""

import re
from dataclasses import dataclass
from typing import cast

from raglab.evals.record import Json, as_json, fake_models


@dataclass(frozen=True)
class Verdict:
    passed: bool
    message: str


def check(baseline: Json, current: Json) -> Verdict:
    k = cast(int, as_json(baseline["retriever"])["k"])
    name = f"recall@{k}"
    for section, key in (("dataset", "sha256"), ("config", "sha256"), ("retriever", "k")):
        old = as_json(baseline[section])[key]
        new = as_json(current[section])[key]
        if old != new:
            return Verdict(
                False,
                f"the baseline {baseline['run_id']} has another {section}.{key} ({old} vs "
                f"{new}): publish a new baseline in a reviewed pull request",
            )
    base = as_json(as_json(as_json(baseline["results"])["metrics"])[name])
    now = as_json(as_json(as_json(current["results"])["metrics"])[name])
    n = cast(int, base["n"])
    threshold = round(cast(float, base["value"]) - 1 / n, 6)
    value = cast(float, now["value"])
    verdict = "passes" if value >= threshold else "fails"
    return Verdict(
        value >= threshold,
        f"{name} {value:.3f} (n {now['n']}) {verdict}: the threshold is the baseline "
        f"{cast(float, base['value']):.3f} ({baseline['run_id']}) minus one question (1/{n}), "
        f"{threshold:.3f}",
    )


# ---------------------------------------------------------------- the consistency gate (S4)

THRESHOLDS = "docs/THRESHOLDS.md"
# the consistency row of THRESHOLDS.md: its first cell starts with this, its third cell (the
# threshold) holds the margin as "margin: M case(s)" once runs have set it
CONSISTENCY_ROW = "| behaviour pass^"
MARGIN = re.compile(r"\bmargin:\s*(\d+)\s*cases?\b")
# what makes a baseline stale: (manifest section, key); the trials are a top-level field
STALE = (
    ("dataset", "sha256"),
    ("config", "sha256"),
    ("prompt", "sha256"),
    ("generator", "digest"),
    ("", "trials"),
)


def consistency_margin(thresholds: str) -> int | None:
    """The margin in cases on THRESHOLDS.md's consistency row, or None while the row sets none."""
    for line in thresholds.splitlines():
        if line.startswith(CONSISTENCY_ROW):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            found = MARGIN.search(cells[2]) if len(cells) > 2 else None
            return int(found.group(1)) if found else None
    return None


def _field(manifest: Json, section: str, key: str) -> object:
    return manifest[key] if not section else as_json(manifest[section]).get(key)


def consistency(baseline: Json, current: Json, margin: int | None) -> Verdict:
    """The consistency gate's verdict on a finished run against its baseline (both valid run
    records; the caller validates them)."""
    run = current["run_id"]
    fake = fake_models(current)
    if current["provenance"] == "fake" or fake:
        return Verdict(
            False,
            f"refused: {run} is a fake run ({', '.join(fake) or 'provenance fake'}): the fake "
            "model's trials are identical, so its pass^N measures the plumbing, never Q-05",
        )
    if current["partial"]:
        return Verdict(False, f"refused: {run} is partial: the gate reads complete runs only")
    if (current["suite"], current["split"]) != ("generation", "dev"):
        return Verdict(
            False,
            f"refused: {run} is a {current['suite']} run on {current['split']}: the gate reads "
            "generation runs on the dev split",
        )
    for section, key in STALE:
        old, new = _field(baseline, section, key), _field(current, section, key)
        if old != new:
            name = f"{section}.{key}" if section else key
            return Verdict(
                False,
                f"stale: the baseline {baseline['run_id']} has another {name} ({old} vs {new}): "
                "publish a new baseline in a reviewed pull request",
            )
    name = f"behaviour_pass^{current['trials']}"
    base_metrics = as_json(as_json(baseline["results"])["metrics"])
    now_metrics = as_json(as_json(current["results"])["metrics"])
    if name not in base_metrics or name not in now_metrics:
        return Verdict(False, f"refused: {run} or its baseline has no {name} (no behaviour cases)")
    if margin is None:
        return Verdict(
            False,
            f"refused: {THRESHOLDS} sets no margin for {name} yet (it is set from runs after the "
            "sign-off, never invented)",
        )
    if margin < 1:
        return Verdict(False, f"refused: the margin in {THRESHOLDS} is at least one case")
    base, now = as_json(base_metrics[name]), as_json(now_metrics[name])
    n = cast(int, base["n"])
    threshold = round(cast(float, base["value"]) - margin / n, 6)
    value = cast(float, now["value"])
    verdict = "passes" if value >= threshold else "fails"
    return Verdict(
        value >= threshold,
        f"{name} {value:.3f} (n {now['n']}) {verdict}: the threshold is the baseline "
        f"{cast(float, base['value']):.3f} ({baseline['run_id']}) minus {margin} case(s) "
        f"({margin}/{n}), {threshold:.3f}",
    )
