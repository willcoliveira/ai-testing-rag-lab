"""The pr-fast no-regression gate for retrieval (docs/THRESHOLDS.md).

A fresh run of the default configuration on the dev split is compared with the published baseline
of the same suite, config and split (runs/published/index.json). It passes when recall@k is at
least the baseline's minus a margin of one question (1 / n): the baseline is made on one machine
and CI runs on another, where the scanned page's OCR text (another Tesseract build) and ONNX
arithmetic in the last bits differ. Measured in the CI image (docs/THRESHOLDS.md): the same top 5
for every dev question and scores within 0.0010, while the closest labelled chunk sits 0.0021 from
the rank-k boundary, so one near-tied chunk may cross; the margin absorbs one such flip and no
more. A baseline made with a different dataset or config is stale, and the gate fails until a new
baseline is published in a reviewed pull request.
"""

from dataclasses import dataclass
from typing import cast

from raglab.evals.record import Json, as_json


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
