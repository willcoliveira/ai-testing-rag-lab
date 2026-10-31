"""The suite audit's recounts (S8, GA8; how-to 09 part B as the main plan quotes it).

The audit report in docs/audits/ carries a "Counts" table whose every number is recounted here
from the repository's files, never from the report: the requirements and their Test and Gate
cells, the golden set's cases and splits, the judged criteria and how many a calibration bar
names, the audit skips and their review date, the pytest markers kept out of `make check`, ZAP's
ignored rules, the published runs by split and gate, the published metric keys and how many carry
an interval, the comparison files, the derived causes files, the flake register's rows and the
not-covered list's entries. `make audit-suite` prints the counts and compares them with the
report's table; a count that drifted fails, naming the section.

Usage:
    uv run python scripts/audit_suite.py [--report docs/audits/<date>-suite-audit-v0.2.md]

Reads files only: no subprocess, no network, no model.
"""

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEST_PLAN = ROOT / "docs" / "TEST-PLAN.md"
CRITERIA = ROOT / "docs" / "CRITERIA.md"
GATES = ROOT / "docs" / "GATES.md"
MAKEFILE = ROOT / "Makefile"
PYPROJECT = ROOT / "pyproject.toml"
ZAP_RULES = ROOT / "deploy" / "zap" / "rules.tsv"
GOLDEN = ROOT / "datasets" / "golden.v2.jsonl"
PUBLISHED = ROOT / "runs" / "published"
CAUSES = ROOT / "runs" / "causes"
COMPARE = ROOT / "runs" / "compare"
CALIBRATION = ROOT / "datasets" / "calibration"
AUDITS = ROOT / "docs" / "audits"


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def traceability() -> dict[str, list[str]]:
    """Each requirement row's cells (requirement, features, cases, test, gate) by R-id."""
    body = TEST_PLAN.read_text(encoding="utf-8").split("## 8. Traceability", 1)[1]
    table = body.split("### Gaps", 1)[0]
    return {
        m.group(1): _cells(m.group(0))[1:]
        for m in re.finditer(r"^\| (R-\d{2}) \|.*$", table, flags=re.M)
    }


def gap_rows() -> list[str]:
    body = TEST_PLAN.read_text(encoding="utf-8").split("### Gaps", 1)[1].split("\n# Part 2", 1)[0]
    return re.findall(r"^\| (R-\d{2}) \|", body, flags=re.M)


def criteria() -> list[str]:
    text = CRITERIA.read_text(encoding="utf-8").split("\n## The criteria\n", 1)[1]
    text = text.split("\n## ", 1)[0]
    return re.findall(r"^### `([a-z_]+)`", text, flags=re.M)


def calibrated_criteria() -> list[str]:
    """The criteria a calibration bar names, from every bar.toml under datasets/calibration/."""
    found: list[str] = []
    for bar in sorted(CALIBRATION.glob("*/bar.toml")) if CALIBRATION.is_dir() else []:
        data = tomllib.loads(bar.read_text(encoding="utf-8"))
        found += [name for name in data.get("criteria", {}) if name not in found]
    return found


def calibration_records() -> list[str]:
    return (
        [p.parent.name for p in sorted(CALIBRATION.glob("*/record.json"))]
        if CALIBRATION.is_dir()
        else []
    )


def audit_skips() -> tuple[int, str]:
    makefile = MAKEFILE.read_text(encoding="utf-8")
    review = re.search(r"Review by (\d{4}-\d{2}-\d{2})", makefile)
    lines = makefile.splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith("AUDIT_SKIP := ")]
    if len(starts) != 1 or review is None:
        raise ValueError("the Makefile defines AUDIT_SKIP once, with a review date")
    ids: list[str] = []
    i = starts[0]
    line = lines[i].split(":=", 1)[1]
    while True:  # a line ending with a backslash continues on the next
        ids += line.rstrip("\\").split()
        if not line.rstrip().endswith("\\"):
            break
        i += 1
        line = lines[i]
    return len(ids), review.group(1)


def excluded_markers() -> list[str]:
    makefile = MAKEFILE.read_text(encoding="utf-8")
    match = re.search(r"^PYTEST_OFFLINE := (.*)$", makefile, flags=re.M)
    if match is None:
        raise ValueError("the Makefile defines PYTEST_OFFLINE")
    return re.findall(r"not (\w+)", match.group(1))


def registered_markers() -> list[str]:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    return [m.split(":", 1)[0] for m in data["tool"]["pytest"]["ini_options"]["markers"]]


def zap_ignored() -> int:
    lines = ZAP_RULES.read_text(encoding="utf-8").splitlines()
    return sum(1 for line in lines if re.match(r"^\d+\tIGNORE\t", line))


def golden_counts() -> dict[str, int]:
    lines = GOLDEN.read_text(encoding="utf-8").splitlines()
    rows = [json.loads(line) for line in lines if line.strip()]
    out: dict[str, int] = {}
    for kind in ("retrieval", "behaviour"):
        for split in ("dev", "test"):
            out[f"{kind} {split}"] = sum(
                1 for r in rows if r["kind"] == kind and r["split"] == split
            )
    out["test-split ids"] = sum(1 for r in rows if r["split"] == "test")
    return out


def published() -> list[dict[str, object]]:
    found: list[dict[str, object]] = []
    for path in sorted(PUBLISHED.glob("*/manifest.json")):
        found.append(json.loads(path.read_text(encoding="utf-8")))
    return found


def counts() -> dict[str, dict[str, object]]:
    """Every count of the report's table, by section."""
    rows = traceability()
    tbd_tests = sorted(rid for rid, cells in rows.items() if cells[3].startswith("tbd"))
    not_covered = sorted(rid for rid, cells in rows.items() if cells[4] == "not covered")
    names = criteria()
    calibrated = calibrated_criteria()
    skips, review = audit_skips()
    runs = published()
    metric_keys = {k: v for m in runs for k, v in m["results"]["metrics"].items()}
    with_interval = sum(1 for v in metric_keys.values() if {"ci_low", "ci_high"} <= set(v))
    held_out = [m for m in runs if m["split"] in ("test", "all")]
    gates_text = GATES.read_text(encoding="utf-8")
    register = gates_text.split("\n### Register\n", 1)[1].split("\n### ", 1)[0]
    register_rows = [
        line
        for line in register.splitlines()
        if line.startswith("|") and "---" not in line and not line.startswith("| Test id")
    ]
    not_covered_list = 0
    for path in sorted(AUDITS.glob("*-suite-audit-*.md")) if AUDITS.is_dir() else []:
        section = path.read_text(encoding="utf-8").split("\n## Not covered\n", 1)
        if len(section) == 2:
            body = section[1].split("\n## ", 1)[0]
            not_covered_list = max(not_covered_list, len(re.findall(r"^- \*\*", body, flags=re.M)))
    golden = golden_counts()
    return {
        "1. coverage": {
            "requirements": len(rows),
            "gap rows": len(gap_rows()),
            "Test cells tbd": len(tbd_tests),
            "Test cells tbd, ids": ", ".join(tbd_tests),
            "Gate cells tbd": sum(1 for cells in rows.values() if cells[4] == "tbd"),
            "Gate cells not covered": ", ".join(not_covered),
            "behaviour cases (dev/test)": f"{golden['behaviour dev']}/{golden['behaviour test']}",
            "retrieval questions (dev/test)": (
                f"{golden['retrieval dev']}/{golden['retrieval test']}"
            ),
            "judged criteria": len(names),
            "criteria a calibration bar names": len(calibrated),
            "criteria a calibration bar names, ids": ", ".join(calibrated) or "none",
            "uncalibrated criteria": len(names) - len(calibrated),
        },
        "2. skips": {
            "audit skips (AUDIT_SKIP)": skips,
            "audit skips review date": review,
            "markers out of make check": ", ".join(excluded_markers()),
            "registered markers": len(registered_markers()),
            "ZAP rules ignored": zap_ignored(),
            "published held-out runs (split test or all)": len(held_out),
            "published held-out runs under release": sum(
                1 for m in held_out if m["gate"] == "release"
            ),
        },
        "4. calibration": {
            "calibration records": len(calibration_records()),
            "calibration records, ids": ", ".join(calibration_records()) or "none",
        },
        "5. contamination": {
            "test-split ids of golden.v2.jsonl": golden["test-split ids"],
            "published dev runs": sum(1 for m in runs if m["split"] == "dev"),
        },
        "6. intervals": {
            "published runs": len(runs),
            "published metric keys": len(metric_keys),
            "published metric keys with an interval": with_interval,
            "comparison files (runs/compare)": len(list(COMPARE.glob("*/compare.json")))
            if COMPARE.is_dir()
            else 0,
            "derived causes files (runs/causes)": len(list(CAUSES.glob("*.json")))
            if CAUSES.is_dir()
            else 0,
        },
        "flakes": {"register rows": len(register_rows)},
        "not covered": {"entries in the not-covered list": not_covered_list},
    }


def report_table(text: str) -> dict[str, str]:
    """The report's Counts table: name to value."""
    body = text.split("\n## Counts\n", 1)[1].split("\n## ", 1)[0]
    found: dict[str, str] = {}
    for line in body.splitlines():
        if line.startswith("| ") and not line.startswith("| Section") and "---" not in line:
            cells = _cells(line)
            found[cells[1]] = cells[2]
    return found


def compare(report: Path) -> list[str]:
    """Each count of the report's table that is not the recount, naming its section."""
    recounted = counts()
    table = report_table(report.read_text(encoding="utf-8"))
    out: list[str] = []
    for section, items in recounted.items():
        for name, value in items.items():
            if name not in table:
                out.append(f"{section}: {name!r} is not in the report's Counts table")
            elif table[name] != str(value):
                out.append(
                    f"{section}: {name!r} is {table[name]!r} in the report, recounted {value!r}"
                )
    for name in table:
        if not any(name in items for items in recounted.values()):
            out.append(f"the report's Counts table has {name!r}, which nothing recounts")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--report", type=Path, help="the audit report to compare the counts with")
    args = parser.parse_args(argv)
    for section, items in counts().items():
        print(f"[{section}]")
        for name, value in items.items():
            print(f"  {name}: {value}")
    if args.report is None:
        return 0
    report = args.report if args.report.is_absolute() else ROOT / args.report
    problems = compare(report)
    for problem in problems:
        print(f"DRIFT {problem}", file=sys.stderr)
    state = "the counts agree" if not problems else f"{len(problems)} count(s) drifted"
    print(f"{report.relative_to(ROOT)}: {state}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
