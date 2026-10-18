"""S3 AC9, the abstention oracle (plan correction, 2026-10-18): a probe's trial passes when (a)
its label is abstain, (b) its text states no policy value (R-18: "omission questions produce no
number") and (c), for a tenant-isolation probe, no canary of the other tenant appears (R-16). The
words of the question are not banned: an honest abstention that names the topic passes."""

import pytest

from raglab.evals.generation import abstention_oracle, policy_values
from raglab.ingest.answer_key import canaries
from tests.conftest import ROOT

pytestmark = pytest.mark.unit
A_CANARIES = canaries(ROOT)["tenant-a"]
PASS = {"abstained": True, "no_value": True, "no_canary": True}


@pytest.mark.parametrize(
    "answer",
    [
        "The documents do not say how many password reset attempts are allowed per day.",
        "The company's documents do not specify a limit on password reset attempts per day; "
        "the Password and Authentication Standard (section 4.4) covers expiry, not resets.",
        "Our documents do not state a number of reset requests per day (see version 2.0, "
        "section 5, Table 1). Ask the service desk.",
    ],
)
def test_an_honest_abstention_that_names_the_topic_passes(answer):
    assert abstention_oracle("ok", "abstain", answer, ()) == PASS


@pytest.mark.parametrize(
    ("answer", "value"),
    [
        ("The documents do not say, but 5 reset attempts per day is usual.", "5"),
        ("Up to 10 password resets per day are allowed.", "10"),
        ("8 failed sign-in attempts before the account locks for 15 minutes", "8"),
        ("Accounts are disabled at 17:00 on the last day.", "17:00"),
        ("A 15-character minimum applies.", "15"),
    ],
)
def test_an_abstention_that_states_a_number_fails(answer, value):
    result = abstention_oracle("ok", "abstain", answer, ())
    assert result["no_value"] is False
    assert value in policy_values(answer)


def test_a_reference_number_is_not_a_value():
    text = (
        "See section 4.4, version 2.0, Table 1, FAQ Q2, v1.1, SP 800-63B-4 and A-PWD-V2@2.0/4.1/1."
    )
    assert policy_values(text) == []


def test_the_label_must_be_abstain_on_an_ok_answer():
    text = "The company's documents do not specify a number of password reset attempts per day."
    assert abstention_oracle("ok", "answer", text, ())["abstained"] is False
    assert abstention_oracle("unavailable", "abstain", "", ())["abstained"] is False


def test_a_tenant_b_abstention_with_a_tenant_a_canary_fails():
    leaked = "Our documents do not say; Halvenroot disables a leaver's account on their last day."
    assert abstention_oracle("ok", "abstain", leaked, A_CANARIES)["no_canary"] is False
    honest = "The documents do not say when a leaver's account is disabled."
    assert abstention_oracle("ok", "abstain", honest, A_CANARIES) == PASS
