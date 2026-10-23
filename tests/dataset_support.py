"""Valid golden sets for the tests of `raglab check-dataset`, each with a datasheet whose
Maintenance table names the file and carries its sha256.

- **v1.1** (S4): the 34 committed retrieval questions and 40 behaviour cases built from the S4
  plan's draft (docs/plans/2026-10-19-s4-golden-set.md, "The mix") and the answer key; P-01 to
  P-03 keep their S3 wording.
- **v2** (S4b): the committed golden set v1.1's 74 lines, then 80 planted behaviour cases, G-38 to
  G-117, written without a split, as the question author writes them, and split by
  scripts/split_golden.py; they meet v2's contract (the mix 45/24/24/12/15, the label floors,
  must-not-block, may_quote and tenant B) with the answer key's existing features only.

They exist only in the tests, so the rules can be held to their contract before the real cases
land. The new question texts are placeholders.
"""

import hashlib
import json
from functools import cache
from pathlib import Path
from typing import Any

from tests.conftest import ROOT, load_script

S = dict[str, str]
V1 = ROOT / "datasets" / "golden.v1.jsonl"
# the Maintenance table's header since datasheet v2 (S4b), with its File column
HEADER = (
    "| Version | Date | Stage | File | What changed | sha256 of the file |\n"
    "|---|---|---|---|---|---|\n"
)


def sec(doc: str, section: str) -> S:
    return {"doc_id": doc, "section_id": section}


def group(*members: S) -> dict[str, list[S]]:
    return {"any_of": list(members)}


def case(
    case_id: str,
    mix: str,
    expected: str,
    split: str | None,
    features: list[str],
    relevant: list[Any] | None = None,
    tenant: str = "tenant-a",
    question: str | None = None,
    may_quote: S | None = None,
) -> dict[str, Any]:
    """A behaviour case; split None leaves the key out, as a new v2 case is written."""
    row: dict[str, Any] = {
        "id": case_id,
        "kind": "behaviour",
        "tenant": tenant,
        "question": question or f"Fixture case {case_id}: a question on {features[0]}?",
        **({} if split is None else {"split": split}),
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
    text = V1.read_text(encoding="utf-8")
    return [line for line in text.splitlines() if json.loads(line)["kind"] == "retrieval"]


def maintenance(*rows: tuple[str, str, str]) -> str:
    """A datasheet whose Maintenance table has a File column: rows of (version, file, sha256)."""
    lines = "".join(
        f"| {version} | 2026-10-23 | fixture | `{file}` | planted | `{sha}` |\n"
        for version, file, sha in rows
    )
    return f"# Datasheet (test fixture)\n\n## Maintenance\n\n{HEADER}{lines}\n## Known limits\n"


def write_dataset(
    directory: Path,
    cases: list[dict[str, Any]] | None = None,
    datasheet: str | None = None,
    with_retrieval: bool = True,
) -> Path:
    """golden.v1.jsonl (the retrieval questions and the cases) and DATASHEET.md beside it, whose
    latest version line for the file carries its sha256 unless another datasheet text is given."""
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
        else maintenance(("v1", path.name, "0" * 64), ("v1.1", path.name, sha)),
        encoding="utf-8",
    )
    return path


# ---------------------------------------------------------------- v2 (S4b)

A_PWD = sec("A-PWD-V2", "4.4")
F42 = [sec("A-PWD-V2", "4.6")]
F41 = [sec("A-MFA", "5.1"), sec("A-MFA", "5.3"), sec("A-EXC", "3.1")]
F43 = [sec("A-EXC", "2.1"), sec("A-EXC", "3.1")]
F54 = [sec("A-MFA", "5.1"), sec("A-FAQ", "Q4")]
F55 = [sec("A-IR", "5.3"), sec("A-MFA", "6.2")]
NIST = sec("X-NIST", "3.1.1.2")
SC, MC, UN, VC = "single-chunk", "multi-chunk", "unanswerable", "version-conflict"
TENANT_B_ANSWERS = [
    ("F-34", sec("B-PWD", "3.1")), ("F-35", sec("B-PWD", "3.3")), ("F-36", sec("B-PWD", "4.1")),
    ("F-37", sec("B-MFA", "3.2")), ("F-38", sec("B-MFA", "6.1")), ("F-39", sec("B-MFA", "7.1")),
    ("F-52", sec("B-MFA", "5.1")), ("F-52", sec("B-MFA", "5.1")), ("F-34", sec("B-PWD", "3.1")),
    ("F-37", sec("B-MFA", "3.2")),
]  # fmt: skip
# one case each for the kinds v1.1 has no case of, so the seeded split cannot leave a kind of two
# or more cases without a dev case; numeric has dev cases in v1.1
NEW_KINDS = [
    ("F-18", [sec("A-PRIV", "8.1"), sec("A-REV", "3.2")]),  # cross-reference
    ("F-20", [sec("A-GLOSS", "10")]),  # glossary-dependent
    ("F-11", [sec("A-PWD-V2", "5"), sec("A-GLOSS", "10")]),  # table-only, glossary-dependent
    ("F-13", [sec("X-NIST", "3.2.2")]),  # external-attribution
    ("F-58", [sec("A-PWD-V2", "1"), sec("A-PWD-V2", "9")]),  # version-history
    ("F-60", [sec("A-PWD-V2", "5")]),  # background
    ("F-25", [sec("A-REMOTE", "4.5")]),  # numeric
    ("F-26", [sec("A-REV", "3.1")]),  # numeric
    ("F-27", [sec("A-LIFE", "6.1")]),  # numeric
]


def _v2_cases() -> list[dict[str, Any]]:
    """The 80 planted v2 cases, in id order from G-38, none with a split."""
    rows: list[tuple[str, str, list[str], list[Any], str, S | None]] = [
        # single-chunk (30)
        *((SC, "refuse-and-help", ["F-42"], F42, "tenant-a", None) for _ in range(7)),
        *((SC, "answer", ["F-56"], [sec("A-PWD-V2", "5")], "tenant-a", None) for _ in range(3)),
        (SC, "answer", ["F-54"], F54, "tenant-a", None),
        *((SC, "answer", [f], [s], B, None) for f, s in TENANT_B_ANSWERS),
        *((SC, "answer", [f], labels, "tenant-a", None) for f, labels in NEW_KINDS),
        # multi-chunk (16)
        *((MC, "flag-conflict", ["F-08"], [A_PWD, NIST], "tenant-a", None) for _ in range(3)),
        *(
            (MC, "flag-conflict", ["F-08"], [A_PWD, sec("X-NCSC", "3")], "tenant-a", None)
            for _ in range(3)
        ),
        *((MC, "refuse-and-help", ["F-41"], F41, "tenant-a", None) for _ in range(5)),
        (MC, "answer", ["F-22"], [sec("A-LIFE", "5.2"), sec("A-MFA", "6.1")], "tenant-a", None),
        (
            MC,
            "answer",
            ["F-23"],
            [sec("A-LIFE", "3.3"), sec("A-MFA", "3.1"), sec("A-MFA", "3.2")],
            "tenant-a",
            None,
        ),
        (
            MC,
            "answer",
            ["F-17"],
            [sec("A-EXC", "5.1"), sec("A-EXC", "4.2"), sec("A-DEVICE", "6.1")],
            "tenant-a",
            None,
        ),
        *((MC, "answer", ["F-55"], F55, "tenant-a", None) for _ in range(2)),
        # unanswerable (16): two with may_quote, as G-26
        *((UN, "abstain", ["F-40"], [], B, NIST if n < 2 else None) for n in range(9)),
        *((UN, "abstain", ["F-32"], [], B, None) for _ in range(2)),
        *((UN, "abstain", ["F-32"], [], "tenant-a", None) for _ in range(3)),
        *((UN, "abstain", ["F-87"], [], "tenant-a", None) for _ in range(2)),
        # version-conflict (8)
        *(
            (VC, "flag-conflict", ["F-04"], [A_PWD, sec("A-PWD-V1", "4.3")], "tenant-a", None)
            for _ in range(4)
        ),
        (VC, "answer", ["F-05"], [sec("A-PWD-V2", "4.1")], "tenant-a", None),
        (VC, "answer", ["F-06"], [sec("A-PWD-V2", "4.3")], "tenant-a", None),
        *((VC, "answer", ["F-07"], [sec("A-PWD-V2", "5")], "tenant-a", None) for _ in range(2)),
        # paraphrased or misspelled (10)
        *(("misspelling", "abstain", ["F-87"], [], "tenant-a", None) for _ in range(2)),
        ("paraphrase", "answer", ["F-47", "F-01"], [sec("A-PWD-V2", "4.1")], "tenant-a", None),
        ("paraphrase", "answer", ["F-48", "F-01"], [sec("A-PWD-V2", "4.1")], "tenant-a", None),
        ("paraphrase", "answer", ["F-49", "F-24"], [sec("A-MFA", "7.1")], "tenant-a", None),
        ("misspelling", "answer", ["F-28"], [sec("A-DEVICE", "3.3")], "tenant-a", None),
        *(("paraphrase", "refuse-and-help", ["F-43"], F43, "tenant-a", None) for _ in range(2)),
        ("misspelling", "refuse-and-help", ["F-42"], F42, "tenant-a", None),
        ("paraphrase", "answer", ["F-54"], F54, "tenant-a", None),
    ]
    return [
        case(f"G-{n}", mix, expected, None, features, relevant, tenant, may_quote=quote)
        for n, (mix, expected, features, relevant, tenant, quote) in enumerate(rows, start=38)
    ]


V2_CASES: list[dict[str, Any]] = _v2_cases()


@cache
def v1_ids() -> frozenset[str]:
    return frozenset(json.loads(line)["id"] for line in V1.read_text("utf-8").splitlines())


@cache
def splitter() -> Any:
    """scripts/split_golden.py, loaded once."""
    return load_script("split_golden")


def v2_lines(cases: list[dict[str, Any]] | None = None, split: bool = True) -> list[str]:
    """v1.1's lines as committed, then the planted cases, split by scripts/split_golden.py unless
    split is False (a case that has a split keeps it)."""
    lines = [*V1.read_text(encoding="utf-8").splitlines(), *map(json.dumps, cases or V2_CASES)]
    return splitter().split(lines, v1_ids())[0] if split else lines


def write_v2(
    directory: Path,
    lines: list[str] | None = None,
    datasheet: str | None = None,
) -> Path:
    """golden.v2.jsonl (the given lines, or v2_lines()) and DATASHEET.md beside it: v1 and v1.1
    for golden.v1.jsonl, and v2 for this file with its sha256, unless another text is given."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "golden.v2.jsonl"
    path.write_text("\n".join(lines or v2_lines()) + "\n", encoding="utf-8")
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    v1 = hashlib.sha256(V1.read_bytes()).hexdigest()
    (directory / "DATASHEET.md").write_text(
        datasheet
        if datasheet is not None
        else maintenance(("v1", V1.name, "0" * 64), ("v1.1", V1.name, v1), ("v2", path.name, sha)),
        encoding="utf-8",
    )
    return path


def edited_lines(lines: list[str], case_id: str, **changes: Any) -> list[str]:
    """The lines with one case's fields set from changes."""
    out: list[str] = []
    for line in lines:
        row = json.loads(line)
        out.append(json.dumps({**row, **changes}) if row["id"] == case_id else line)
    assert out != lines, f"no case {case_id} changed"
    return out


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
