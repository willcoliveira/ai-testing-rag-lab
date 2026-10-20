"""The abstention oracle (S3, named in the S3 ledger's plan correction), shared by the S3 probes
(raglab.evals.generation_record) and the S4 behaviour cases (raglab.evals.behaviour).

A trial abstains when (a) its label is abstain on an ok answer, (b) its text states no policy
value (R-18's acceptance: "omission questions produce no number") and (c) none of the given
canaries appears in it (R-16). An honest abstention may name the topic ("the documents do not say
how many reset attempts..."): the words of the question are not banned, a value is.

S4 adds one thing for D-03: a number is allowed when a cited chunk of the case's may_quote
section (a shared reference section) states it, so an abstention may quote an external value.
Whether the quote is attributed in words is S5's to judge. A probe passes no such values, so its
oracle is the S3 one, unchanged.
"""

import re
from collections.abc import Collection, Sequence

# a number standing alone: not inside an id, a version or a citation (an exception id, v2.0,
# 800-63B-4, A-PWD-V2@2.0/4.1/1), so "15", "15-character", "17:00", "2.5" and "90%" count
NUMBER = re.compile(r"(?<![\w@./-])\d+(?:[.,:]\d+)*%?(?![\w@/]|-\d|\.\d)")
# a number right after one of these words points at a place in a document, not a value
REFERENCE_WORDS = frozenset(
    {
        "section",
        "sections",
        "version",
        "versions",
        "table",
        "page",
        "pages",
        "step",
        "steps",
        "appendix",
        "annex",
        "chapter",
        "part",
        "q",
        "faq",
        "sp",
        "figure",
        "clause",
    }
)


def policy_values(answer: str) -> list[str]:
    """The numbers an answer states as values: every standalone number except one that follows a
    reference word ("section 4.4", "version 2.0", "Table 1"). Number words ("eight") are not
    counted: a known limit of this oracle, which S5's judged metrics cover."""
    values: list[str] = []
    for match in NUMBER.finditer(answer):
        before = answer[: match.start()].split()
        previous = before[-1].strip("(:,").lower() if before else ""
        if previous not in REFERENCE_WORDS:
            values.append(match.group())
    return values


def abstention_oracle(
    status: str,
    label: str,
    answer: str,
    canaries: Sequence[str],
    quotable: Collection[str] = (),
) -> dict[str, bool]:
    """The checks of an abstaining trial: (a) abstained, the label is abstain on an ok answer;
    (b) no_value, the text states no policy value (R-18) other than one in quotable, the values
    a cited chunk of the case's may_quote section states (D-03, S4; empty for an S3 probe); (c)
    no_canary, none of the given canaries (the other tenant's, for a tenant-isolation probe; none
    otherwise) is in the text (R-16)."""
    return {
        "abstained": status == "ok" and label == "abstain",
        "no_value": not [v for v in policy_values(answer) if v not in quotable],
        "no_canary": not [c for c in canaries if c in answer],
    }
