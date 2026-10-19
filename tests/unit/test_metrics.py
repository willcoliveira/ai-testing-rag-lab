"""AC1: hit@k, MRR, recall@k, the paired difference and the bootstrap interval match values
computed by hand on small fixtures."""

import math
import statistics

import pytest

from raglab.evals import metrics as m

pytestmark = pytest.mark.unit

# Two labelled sections: S1 = {a1, a2} (a section cut into two chunks) and S2 = {b1}.
S1 = frozenset({"a1", "a2"})
S2 = frozenset({"b1"})


@pytest.mark.parametrize(
    ("retrieved", "k", "hit", "rr", "recall"),
    [
        (["a2", "x", "b1", "y", "z"], 5, 1, 1.0, 1.0),  # a2 at rank 1, both sections found
        (["x", "y", "a1", "a2", "z"], 5, 1, 1 / 3, 0.5),  # first relevant at 3; S1 only, once
        (["x", "y", "z", "w", "b1"], 5, 1, 1 / 5, 0.5),  # rank 5 is inside k = 5
        (["x", "y", "z", "w", "b1"], 4, 0, 0.0, 0.0),  # and outside k = 4
        (["x", "y", "z", "w", "v"], 5, 0, 0.0, 0.0),
        (["a1", "a2", "x", "y", "z"], 5, 1, 1.0, 0.5),  # two chunks of S1 still count once
        ([], 5, 0, 0.0, 0.0),
    ],
)
def test_case_metrics_by_hand(retrieved, k, hit, rr, recall):
    labels = [S1, S2]
    assert m.hit_at_k(retrieved, labels, k) == hit
    assert math.isclose(m.reciprocal_rank(retrieved, labels, k), rr)
    assert math.isclose(m.recall_at_k(retrieved, labels, k), recall)


# S4 (AC2): a label group, sections that state the same rule, is one thing to find. The question
# below labels a group G of two sections, A-PWD 4.1 (two chunks, /1 and /2) and X-NIST 3.1 (one
# chunk), and a section S, A-PWD 5 (one chunk): two things to find, not three. It goes through
# the golden loader and resolver, so the per-thing chunk sets are the ones a run scores.
G_PRIMARY, G_SECOND = "A-PWD@1.0/4.1/2", "X-NIST@4/3.1/1"
S_CHUNK = "A-PWD@1.0/5/1"


@pytest.mark.parametrize(
    ("retrieved", "k", "hit", "rr", "recall"),
    [
        ([G_SECOND, "z", S_CHUNK], 3, 1, 1.0, 1.0),  # G by its second member at rank 1, S at 3
        (["z", G_PRIMARY, G_SECOND], 3, 1, 1 / 2, 1 / 2),  # G at rank 2 (counted once), S missed
        ([S_CHUNK, "z", G_SECOND], 2, 1, 1.0, 1 / 2),  # G's member at rank 3, outside k = 2
        (["z", "y", G_SECOND], 3, 1, 1 / 3, 1 / 2),  # only the second member: G is found
        (["z", "y", "w"], 3, 0, 0.0, 0.0),
    ],
)
def test_a_group_is_one_thing_to_find_by_hand(retrieved, k, hit, rr, recall):
    from raglab.evals import golden
    from tests.retrieval_support import PACK

    line = (
        '{"id": "Q", "kind": "retrieval", "split": "dev", "tenant": "tenant-a", "question": "q",'
        ' "relevant": [{"any_of": [{"doc_id": "A-PWD", "section_id": "4.1"},'
        ' {"doc_id": "X-NIST", "section_id": "3.1"}]}, {"doc_id": "A-PWD", "section_id": "5"}]}'
    )
    [resolved] = golden.resolve([golden.parse_line(line, "g:1")], PACK)
    labels = resolved.label_sets()
    assert len(labels) == 2  # G and S
    assert m.hit_at_k(retrieved, labels, k) == hit
    assert math.isclose(m.reciprocal_rank(retrieved, labels, k), rr)
    assert math.isclose(m.recall_at_k(retrieved, labels, k), recall)


def test_means_over_questions_by_hand():
    # three questions: RR 1, 1/3, 0 -> MRR 4/9; recall 1, 0.5, 0 -> 0.5; hit 1, 1, 0 -> 2/3
    assert math.isclose(m.mean([1.0, 1 / 3, 0.0]), 4 / 9)
    assert math.isclose(m.mean([1.0, 0.5, 0.0]), 0.5)
    assert math.isclose(m.mean([1, 1, 0]), 2 / 3)
    with pytest.raises(ValueError, match="no values"):
        m.mean([])
    with pytest.raises(ValueError, match="at least one labelled section"):
        m.recall_at_k(["a"], [], 5)


def test_quantile_interpolates_between_order_statistics():
    values = [4.0, 1.0, 3.0, 2.0]  # sorted 1, 2, 3, 4; position (n - 1) q
    assert m.quantile(values, 0.0) == 1.0
    assert m.quantile(values, 1.0) == 4.0
    assert math.isclose(m.quantile(values, 0.5), 2.5)  # position 1.5
    assert math.isclose(m.quantile(values, 0.025), 1.075)  # position 0.075
    assert math.isclose(m.quantile(values, 0.975), 3.925)  # position 2.925
    assert m.quantile([7.0], 0.3) == 7.0
    # the same rule as statistics.quantiles(method="inclusive")
    data = [0.0, 0.2, 0.5, 0.5, 0.9, 1.0, 1.0]
    cuts = statistics.quantiles(data, n=40, method="inclusive")
    assert math.isclose(m.quantile(data, 0.025), cuts[0])
    assert math.isclose(m.quantile(data, 0.975), cuts[-1])


def test_paired_difference_by_hand():
    a = [1.0, 0.0, 1.0, 0.5]
    b = [1.0, 1.0, 0.0, 1.0]
    assert m.paired_differences(a, b) == [0.0, 1.0, -1.0, 0.5]
    diff = m.paired_difference(a, b, seed=1)
    assert math.isclose(diff.value, 0.125)  # (0 + 1 - 1 + 0.5) / 4
    assert diff.n == 4
    assert diff.low <= diff.value <= diff.high
    with pytest.raises(ValueError, match="same questions"):
        m.paired_differences([1.0], [1.0, 0.0])


def test_bootstrap_of_a_constant_is_the_constant():
    interval = m.bootstrap_interval([0.6] * 9, seed=3)
    assert (interval.value, interval.low, interval.high, interval.n) == (0.6, 0.6, 0.6, 9)
    same = m.paired_difference([1.0, 0.0, 1.0], [1.0, 0.0, 1.0], seed=3)
    assert (same.value, same.low, same.high) == (0.0, 0.0, 0.0)


def test_bootstrap_of_two_values_reaches_both_ends():
    """Resamples of [0, 1] have means 0, 0.5 or 1 with chances 1/4, 1/2, 1/4; with 2,000 of them
    the 2.5% and 97.5% quantiles are 0 and 1 (a run of fewer than 50 zeros among 2,000 draws at
    1/4 each is about 30 standard deviations away)."""
    means = m.bootstrap_means([0.0, 1.0], 2000, seed=11)
    assert set(means) == {0.0, 0.5, 1.0}
    assert abs(means.count(0.5) / 2000 - 0.5) < 0.05
    interval = m.bootstrap_interval([0.0, 1.0], seed=11)
    assert (interval.value, interval.low, interval.high) == (0.5, 0.0, 1.0)


def test_bootstrap_is_seeded_and_uses_the_resample_count():
    values = [1.0, 0.0, 1.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0, 1.0]
    first = m.bootstrap_means(values, 2000, seed=20261006)
    assert first == m.bootstrap_means(values, 2000, seed=20261006)
    assert first != m.bootstrap_means(values, 2000, seed=20261007)
    assert len(first) == 2000
    interval = m.bootstrap_interval(values, seed=20261006)
    assert interval == m.bootstrap_interval(values, seed=20261006)
    assert (interval.low, interval.high) == (m.quantile(first, 0.025), m.quantile(first, 0.975))
    # near the normal approximation: mean 0.7, standard error sqrt(0.7 * 0.3 / 10) = 0.145
    assert interval.low == pytest.approx(0.7 - 1.96 * 0.145, abs=0.1)
    assert interval.high == pytest.approx(0.7 + 1.96 * 0.145, abs=0.1)
    with pytest.raises(ValueError, match="resamples"):
        m.bootstrap_means(values, 0, seed=1)
    with pytest.raises(ValueError, match="level"):
        m.bootstrap_interval(values, seed=1, level=1.0)


def test_interval_json_is_rounded():
    assert m.Interval(1 / 3, 0.1, 0.9, 3).as_json() == {
        "value": 0.333333,
        "ci_low": 0.1,
        "ci_high": 0.9,
        "n": 3,
    }
