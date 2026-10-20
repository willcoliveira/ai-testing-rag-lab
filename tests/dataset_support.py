"""A valid golden set for the S4 tests: the 34 committed retrieval questions and 40 behaviour
cases built from the plan's draft (docs/plans/2026-10-19-s4-golden-set.md, "The mix") and the
answer key, with a datasheet whose latest version line carries the file's sha256.

It exists only in the tests, so `raglab check-dataset` and the behaviour checks can be held to the
contract before the real cases (datasets/golden.v1.jsonl, written by the question author) land.
The question texts are placeholders; P-01 to P-03 keep their S3 wording.
"""

import hashlib
import json
from pathlib import Path
from typing import Any

from tests.conftest import ROOT

S = dict[str, str]


def sec(doc: str, section: str) -> S:
    return {"doc_id": doc, "section_id": section}


def group(*members: S) -> dict[str, list[S]]:
    return {"any_of": list(members)}


def case(
    case_id: str,
    mix: str,
    expected: str,
    split: str,
    features: list[str],
    relevant: list[Any] | None = None,
    tenant: str = "tenant-a",
    question: str | None = None,
    may_quote: S | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": case_id,
        "kind": "behaviour",
        "tenant": tenant,
        "question": question or f"Fixture case {case_id}: a question on {features[0]}?",
        "split": split,
        "mix": mix,
        "expected": expected,
        "feature_ids": features,
        "reference_answer": None
        if expected == "abstain"
        else f"Fixture reference answer from {features[0]}.",
        "relevant": relevant or [],
        "origin": "synthetic",
    }
    if may_quote is not None:
        row["may_quote"] = may_quote
    return row


RESET = "How many password reset attempts are allowed per day?"
B = "tenant-b"

CASES: list[dict[str, Any]] = [
    # single-chunk (15): 5 in test
    case("G-01", "single-chunk", "answer", "dev", ["F-01", "F-53"],
         [group(sec("A-PWD-V2", "4.1"), sec("A-FAQ", "Q1"))]),
    case("G-02", "single-chunk", "answer", "test", ["F-03"], [sec("A-PWD-V2", "4.3")]),
    case("G-03", "single-chunk", "answer", "dev", ["F-09"], [sec("A-PWD-V2", "5")]),
    case("G-04", "single-chunk", "answer", "test", ["F-10"], [sec("A-PWD-V2", "5")]),
    case("G-05", "single-chunk", "answer", "dev", ["F-15"], [sec("A-MFA", "4.1")]),
    case("G-06", "single-chunk", "answer", "dev", ["F-24"], [sec("A-MFA", "7.1")]),
    case("G-07", "single-chunk", "answer", "test", ["F-29"], [sec("A-REV", "5.1")]),
    case("G-08", "single-chunk", "answer", "dev", ["F-33"], [sec("A-DEVICE-B", "1")]),
    case("G-09", "single-chunk", "answer", "dev", ["F-46"], [sec("A-IR", "3.2")]),
    case("G-10", "single-chunk", "answer", "test", ["F-50"], [sec("A-PRIV", "6.1")]),
    case("G-11", "single-chunk", "answer", "dev", ["F-51"], [sec("A-EXC", "4.1")]),
    case("G-12", "single-chunk", "answer", "dev", ["F-56"], [sec("A-PWD-V2", "5")]),
    case("G-13", "single-chunk", "refuse-and-help", "dev", ["F-42"], [sec("A-PWD-V2", "4.6")]),
    case("G-14", "single-chunk", "answer", "dev", ["F-39"], [sec("B-MFA", "7.1")], tenant=B),
    case("G-15", "single-chunk", "answer", "test", ["F-52"], [sec("B-MFA", "5.1")], tenant=B),
    # multi-chunk (8): 3 in test
    case("G-16", "multi-chunk", "answer", "dev", ["F-22"],
         [sec("A-LIFE", "5.2"), sec("A-MFA", "6.1")]),
    case("G-17", "multi-chunk", "answer", "test", ["F-23"],
         [sec("A-LIFE", "3.3"), sec("A-MFA", "3.1"), sec("A-MFA", "3.2")]),
    case("G-18", "multi-chunk", "answer", "dev", ["F-16"],
         [sec("A-EXC", "5.1"), sec("A-EXC", "5.2"), sec("A-REMOTE", "4.5")]),
    case("G-19", "multi-chunk", "answer", "test", ["F-17"],
         [sec("A-EXC", "5.1"), sec("A-EXC", "4.2"), sec("A-DEVICE", "6.1")]),
    case("G-20", "multi-chunk", "answer", "dev", ["F-57"],
         [sec("A-IR", s) for s in ("5", "5.1", "5.2", "5.3", "5.4", "5.5", "5.6")]),
    case("G-21", "multi-chunk", "answer", "dev", ["F-55"],
         [sec("A-IR", "5.3"), sec("A-MFA", "6.2")]),
    case("G-22", "multi-chunk", "flag-conflict", "dev", ["F-08"],
         [sec("A-PWD-V2", "4.4"), sec("X-NIST", "3.1.1.2")]),
    case("G-23", "multi-chunk", "refuse-and-help", "test", ["F-41"],
         [sec("A-MFA", "5.1"), sec("A-MFA", "5.3"), sec("A-EXC", "3.1")]),
    # unanswerable (8): the S3 probes in dev, 3 in test
    case("P-01", "unanswerable", "abstain", "dev", ["F-32"], question=RESET),
    case("P-02", "unanswerable", "abstain", "dev", ["F-32"], tenant=B, question=RESET),
    case("P-03", "unanswerable", "abstain", "dev", ["F-40"], tenant=B,
         question="When is a leaver's account disabled?"),
    case("G-24", "unanswerable", "abstain", "test", ["F-40"], tenant=B),
    case("G-25", "unanswerable", "abstain", "dev", ["F-40"], tenant=B),
    case("G-26", "unanswerable", "abstain", "test", ["F-40"], tenant=B,
         may_quote=sec("X-NIST", "3.1.1.2")),
    case("G-27", "unanswerable", "abstain", "dev", ["F-32"]),
    case("G-28", "unanswerable", "abstain", "test", ["F-40"], tenant=B),
    # version-conflict (4): 2 in test
    case("G-29", "version-conflict", "flag-conflict", "dev", ["F-04"],
         [sec("A-PWD-V2", "4.4"), sec("A-PWD-V1", "4.3")]),
    case("G-30", "version-conflict", "flag-conflict", "test", ["F-04", "F-53"],
         [group(sec("A-PWD-V2", "4.4"), sec("A-FAQ", "Q2")), sec("A-PWD-V1", "4.3")]),
    case("G-31", "version-conflict", "answer", "dev", ["F-05"], [sec("A-PWD-V2", "4.1")]),
    case("G-32", "version-conflict", "answer", "test", ["F-07"], [sec("A-PWD-V2", "5")]),
    # paraphrased or misspelled (5): 2 in test
    case("G-33", "paraphrase", "answer", "dev", ["F-54"],
         [sec("A-MFA", "5.1"), sec("A-FAQ", "Q4")]),
    case("G-34", "paraphrase", "refuse-and-help", "test", ["F-43"],
         [sec("A-EXC", "2.1"), sec("A-EXC", "3.1")]),
    case("G-35", "misspelling", "answer", "dev", ["F-28"], [sec("A-DEVICE", "3.3")]),
    case("G-36", "paraphrase", "answer", "test", ["F-30"], [sec("A-IR", "3.1")]),
    case("G-37", "misspelling", "abstain", "dev", ["F-32"]),
]  # fmt: skip


def retrieval_lines() -> list[str]:
    """The committed retrieval questions, as they are."""
    text = (ROOT / "datasets" / "golden.v1.jsonl").read_text(encoding="utf-8")
    return [line for line in text.splitlines() if json.loads(line)["kind"] == "retrieval"]


def write_dataset(
    directory: Path,
    cases: list[dict[str, Any]] | None = None,
    datasheet: str | None = None,
    with_retrieval: bool = True,
) -> Path:
    """golden.v1.jsonl (the retrieval questions and the cases) and DATASHEET.md beside it, whose
    latest version line carries the file's sha256 unless another datasheet text is given."""
    directory.mkdir(parents=True, exist_ok=True)
    lines = [
        *(retrieval_lines() if with_retrieval else []),
        *(json.dumps(c) for c in (cases or CASES)),
    ]
    path = directory / "golden.v1.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    (directory / "DATASHEET.md").write_text(
        datasheet
        if datasheet is not None
        else (
            "# Datasheet (test fixture)\n\n## Versioning\n\n"
            "| Version | Stage | Change | sha256 |\n|---|---|---|---|\n"
            f"| v1 | S2 | 34 retrieval questions | {'0' * 64} |\n"
            f"| v1.1 | S4 | 40 behaviour cases | {sha} |\n"
        ),
        encoding="utf-8",
    )
    return path


def edited(
    case_id: str,
    drop: tuple[str, ...] = (),
    cases: list[dict[str, Any]] | None = None,
    **changes: Any,
) -> list[dict[str, Any]]:
    """The fixture's cases with one case changed: fields set from changes, those in drop removed."""
    out: list[dict[str, Any]] = []
    for row in cases or CASES:
        if row["id"] == case_id:
            row = {k: v for k, v in {**row, **changes}.items() if k not in drop}
        out.append(row)
    assert out != (cases or CASES), f"no case {case_id} changed"
    return out
