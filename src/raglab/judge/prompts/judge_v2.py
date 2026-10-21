"""The judge prompt, version 2: judge-v1 with `correct`'s pass rule reworded, and nothing else.

The user's second sign-off of docs/CRITERIA.md (2026-10-21, "Reword and re-judge (Recommended)")
replaced "the governing rule" among a reference answer's decisive facts with "each rule the
reference states", and added that the document and section a reference names are its sources,
not decisive facts: in the first judged run, 17 of the 42 `correct` fails gave the missing
document and section as the reason (S5 ledger). The system prompt, the frames, the schema, the
parser and every other rule are judge-v1's, imported from it. The model reads no version name, so
a judge-v2 call differs from a judge-v1 call only in `correct`'s pass rule.

A reworded rule is a new version (tests/judge/test_judge_prompt.py): judge-v1 stays as it was,
the prompt of the first judged record, which still validates against judge-v1's fingerprint.
"""

from dataclasses import replace

from raglab.core.types import JudgeItem
from raglab.judge.prompts import judge_v1
from raglab.judge.prompts.judge_v1 import (
    ANSWER_FRAME,
    CRITERION_BLOCK,
    FIELDS,
    INPUTS,
    NO_PASSAGES,
    PASSAGE_FRAME,
    PASSAGES_HEADER,
    QUESTION_FRAME,
    REFERENCE_FRAME,
    SCHEMA_NAME,
    SYSTEM,
    VERDICT_SCHEMA,
    InvalidVerdict,
    Parsed,
    Rule,
    as_data,
    frame_passage,
    parse,
    quote_found,
)

__all__ = [
    "ANSWER_FRAME",
    "CRITERION_BLOCK",
    "FIELDS",
    "INPUTS",
    "NO_PASSAGES",
    "PASSAGES_HEADER",
    "PASSAGE_FRAME",
    "QUESTION_FRAME",
    "REFERENCE_FRAME",
    "RULES",
    "SCHEMA_NAME",
    "SYSTEM",
    "VERDICT_SCHEMA",
    "VERSION",
    "InvalidVerdict",
    "Parsed",
    "Rule",
    "as_data",
    "build",
    "check_inputs",
    "fingerprint",
    "frame_passage",
    "parse",
    "quote_found",
]

VERSION = "judge-v2"

RULES: dict[str, Rule] = {
    **judge_v1.RULES,
    "correct": replace(
        judge_v1.RULES["correct"],
        passes=(
            "the answer gives every decisive fact of the reference answer (each value with its "
            "unit, each rule the reference states, an exception with its end date, both sides of "
            "a conflict, the route) and contradicts none of them; the document and section a "
            "reference names are its sources, not decisive facts"
        ),
    ),
}


def fingerprint() -> str:
    """sha256 of everything that makes up this prompt (judge_v1.fingerprint_of)."""
    return judge_v1.fingerprint_of(VERSION, RULES)


def check_inputs(item: JudgeItem) -> None:
    """ValueError unless the item shows exactly the inputs its criterion sees."""
    judge_v1.check_inputs_of(item, RULES)


def build(item: JudgeItem) -> tuple[str, str]:
    """(system prompt, user message) of one judge call, as judge-v1 builds it, with these rules."""
    return judge_v1.build_of(item, RULES)
