"""Retrieval metrics against labelled sections, a paired difference and a bootstrap interval.

A question's labels are sections (a document and a section id), each resolved to the chunks that
section has at the run's chunk settings (raglab.evals.golden). The unit of relevance is the
section, so a setting that cuts a section into more chunks does not change how many things there
are to find:

- **hit@k**: 1 if any chunk of any labelled section is in the top k, else 0.
- **MRR@k** (reciprocal rank): 1 / the rank of the first retrieved chunk that belongs to a
  labelled section, 0 if none is in the top k; the mean over questions is the MRR.
- **recall@k**: the share of labelled sections with at least one chunk in the top k.

A label group (S4: sections that state the same rule, `any_of` in the golden file) is one thing to
find: raglab.evals.golden resolves it to one chunk set, every member's chunks together, so the
three functions below take the first chunk of any member for hit and rank and count the group
once for recall, with no special case here.

Intervals are percentile bootstrap intervals: `resamples` resamples of the questions with
replacement, drawn by random.Random(seed), the metric's mean in each, and the quantiles at
(1 - level) / 2 and 1 - (1 - level) / 2 by linear interpolation between order statistics
(Hyndman and Fan type 7, numpy's default). The paired difference of two runs on the same
questions is the mean of the per-question differences (B minus A), and its interval comes from
resampling those differences, so the pairing is kept.
"""

import math
import random
from collections.abc import Sequence
from dataclasses import dataclass
from statistics import NormalDist

DEFAULT_RESAMPLES = 2000
DEFAULT_LEVEL = 0.95


def hit_at_k(retrieved: Sequence[str], labels: Sequence[frozenset[str]], k: int) -> int:
    top = set(retrieved[:k])
    return int(any(top & label for label in labels))


def reciprocal_rank(retrieved: Sequence[str], labels: Sequence[frozenset[str]], k: int) -> float:
    relevant: frozenset[str] = frozenset[str]().union(*labels)
    for rank, chunk_id in enumerate(retrieved[:k], start=1):
        if chunk_id in relevant:
            return 1.0 / rank
    return 0.0


def recall_at_k(retrieved: Sequence[str], labels: Sequence[frozenset[str]], k: int) -> float:
    if not labels:
        raise ValueError("recall needs at least one labelled section")
    top = set(retrieved[:k])
    return sum(1 for label in labels if top & label) / len(labels)


def mean(values: Sequence[float]) -> float:
    if not values:
        raise ValueError("the mean of no values")
    return math.fsum(values) / len(values)


def quantile(values: Sequence[float], q: float) -> float:
    """The q quantile by linear interpolation between order statistics (type 7)."""
    if not values:
        raise ValueError("the quantile of no values")
    if not 0.0 <= q <= 1.0:
        raise ValueError(f"q must be between 0 and 1, not {q}")
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    low = math.floor(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def bootstrap_means(values: Sequence[float], resamples: int, seed: int) -> list[float]:
    """The mean of each of `resamples` resamples of values (with replacement)."""
    if not values:
        raise ValueError("a bootstrap needs at least one value")
    if resamples < 1:
        raise ValueError(f"resamples must be at least 1, not {resamples}")
    # a seeded resampler for reproducible intervals, not a secret
    rng = random.Random(seed)  # noqa: S311  # nosec B311
    n = len(values)
    return [mean([values[rng.randrange(n)] for _ in range(n)]) for _ in range(resamples)]


@dataclass(frozen=True)
class Interval:
    value: float
    low: float
    high: float
    n: int

    def as_json(self) -> dict[str, float | int]:
        return {
            "value": round(self.value, 6),
            "ci_low": round(self.low, 6),
            "ci_high": round(self.high, 6),
            "n": self.n,
        }


def bootstrap_interval(
    values: Sequence[float],
    seed: int,
    resamples: int = DEFAULT_RESAMPLES,
    level: float = DEFAULT_LEVEL,
) -> Interval:
    """The mean of values and its percentile bootstrap interval."""
    if not 0.0 < level < 1.0:
        raise ValueError(f"level must be between 0 and 1, not {level}")
    means = bootstrap_means(values, resamples, seed)
    tail = (1.0 - level) / 2.0
    return Interval(mean(values), quantile(means, tail), quantile(means, 1.0 - tail), len(values))


def paired_differences(a: Sequence[float], b: Sequence[float]) -> list[float]:
    """Per question, B minus A (the two lists are in the same question order)."""
    if len(a) != len(b):
        raise ValueError(f"paired values need the same questions: {len(a)} and {len(b)}")
    return [y - x for x, y in zip(a, b, strict=True)]


def paired_difference(
    a: Sequence[float],
    b: Sequence[float],
    seed: int,
    resamples: int = DEFAULT_RESAMPLES,
    level: float = DEFAULT_LEVEL,
) -> Interval:
    """The mean of B minus A over the same questions, with its bootstrap interval."""
    return bootstrap_interval(paired_differences(a, b), seed, resamples, level)


def wilson_interval(rate: float, n: int, level: float = DEFAULT_LEVEL) -> Interval:
    """The Wilson score interval of a rate observed over n units. In S3 the units are cases: a
    rate over several trials of each case gets the width of n cases, not of n times the trials,
    since the trials of one case are not independent. z is the normal quantile at
    1 - (1 - level) / 2."""
    if n < 1:
        raise ValueError(f"a Wilson interval needs n of at least 1, not {n}")
    if not 0.0 <= rate <= 1.0:
        raise ValueError(f"a rate is between 0 and 1, not {rate}")
    if not 0.0 < level < 1.0:
        raise ValueError(f"level must be between 0 and 1, not {level}")
    z = NormalDist().inv_cdf(1.0 - (1.0 - level) / 2.0)
    denominator = 1.0 + z * z / n
    centre = (rate + z * z / (2 * n)) / denominator
    half = z * math.sqrt(rate * (1.0 - rate) / n + z * z / (4 * n * n)) / denominator
    return Interval(rate, max(0.0, centre - half), min(1.0, centre + half), n)
