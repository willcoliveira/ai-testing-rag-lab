"""S8 (GA1): docs/GATES.md, the gate map in how-to 08's seven columns plus a mode: one row per
gate of the main plan's map; a mode of ci, local or documented only on every row; every `make`
target named exists in the Makefile; every runbook named exists; every pytest marker named is
registered; and pr-fast's "What runs" names every `make` step of .github/workflows/pr-fast.yml,
read from the workflow. Each break runs on a copy of the text."""

import re
import tomllib

import pytest
import yaml

from tests.conftest import ROOT

pytestmark = pytest.mark.unit
DOC = ROOT / "docs" / "GATES.md"
WORKFLOW = ROOT / ".github" / "workflows" / "pr-fast.yml"
COLUMNS = (
    "Gate", "Trigger", "Keys", "Blocks", "Threshold and reason", "Owner and runbook",
    "What runs", "Mode",
)  # fmt: skip
MODES = ("ci", "local", "documented only")
GATES = ("pr-fast", "eval-on-change", "nightly", "manual", "weekly", "release", "prod-sample")
MAKE = re.compile(r"`make ([a-z][a-z0-9-]*)")
RUNBOOK = re.compile(r"`(runbooks/[\w-]+\.md)`")
MARKERS = re.compile(r"markers? ((?:`[a-z0-9_]+`(?:, | or )?)+)")
MARKER = re.compile(r"`([a-z0-9_]+)`")


def table(text: str) -> tuple[list[str], dict[str, dict[str, str]]]:
    """(the header, each row's cells by column, keyed by its Gate cell) of the gates table."""
    body = text.split("\n## The gates\n", 1)[1].split("\n## ", 1)[0]
    lines = [line for line in body.splitlines() if line.startswith("|")]
    header = [c.strip() for c in lines[0].strip().strip("|").split("|")]
    rows: dict[str, dict[str, str]] = {}
    for line in lines[2:]:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        rows[cells[0]] = dict(zip(header, cells, strict=False))
    return header, rows


def make_targets() -> set[str]:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    return set(re.findall(r"^([a-z][a-z0-9-]*):", makefile, flags=re.M))


def registered_markers() -> set[str]:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return {m.split(":", 1)[0] for m in data["tool"]["pytest"]["ini_options"]["markers"]}


def workflow_make_steps(text: str | None = None) -> set[str]:
    """Every `make <target>` a step of the workflow runs, in any job, the arguments dropped."""
    wf = yaml.safe_load(text or WORKFLOW.read_text(encoding="utf-8"))
    found: set[str] = set()
    for job in wf["jobs"].values():
        for step in job.get("steps", []):
            found |= set(re.findall(r"(?:^|\s)make ([a-z][a-z0-9-]*)", str(step.get("run", ""))))
    return found


def problems(text: str, workflow: str | None = None) -> list[str]:
    header, rows = table(text)
    out: list[str] = []
    if tuple(header) != COLUMNS:
        out.append(f"the columns are {header}, not {list(COLUMNS)}")
        return out
    out += [f"{gate}: no row" for gate in GATES if gate not in rows]
    targets, markers = make_targets(), registered_markers()
    for gate, cells in rows.items():
        if len(cells) != len(COLUMNS):
            out.append(f"{gate}: {len(cells)} cells, not {len(COLUMNS)}")
            continue
        if cells["Mode"] not in MODES:
            out.append(f"{gate}: mode {cells['Mode']!r} is not one of {MODES}")
        for cell in cells.values():
            out += [
                f"{gate}: `make {t}` is no Makefile target"
                for t in MAKE.findall(cell)
                if t not in targets
            ]
            out += [
                f"{gate}: {r} does not exist"
                for r in RUNBOOK.findall(cell)
                if not (ROOT / r).is_file()
            ]
            for listed in MARKERS.findall(cell):
                out += [
                    f"{gate}: marker `{m}` is not registered"
                    for m in MARKER.findall(listed)
                    if m not in markers
                ]
    if "pr-fast" in rows:
        runs = rows["pr-fast"]["What runs"]
        named = set(MAKE.findall(runs))
        out += [
            f"pr-fast: the workflow runs `make {step}`, which What runs does not name"
            for step in sorted(workflow_make_steps(workflow) - named)
        ]
    return out


def test_the_gate_map_has_every_row_in_the_eight_columns_with_a_mode():
    header, rows = table(DOC.read_text(encoding="utf-8"))
    assert tuple(header) == COLUMNS
    assert list(rows) == list(GATES)
    assert problems(DOC.read_text(encoding="utf-8")) == []
    modes = {gate: cells["Mode"] for gate, cells in rows.items()}
    assert modes["pr-fast"] == "ci"
    assert modes["prod-sample"] == "documented only"
    assert all(m in MODES for m in modes.values())
    assert any("documented only" in text for text in DOC.read_text(encoding="utf-8").splitlines())


def test_pr_fasts_what_runs_names_every_make_step_of_the_workflow():
    steps = workflow_make_steps()
    assert {"check-dataset", "model", "test", "gate", "api-smoke", "perf-smoke"} <= steps
    _, rows = table(DOC.read_text(encoding="utf-8"))
    named = set(MAKE.findall(rows["pr-fast"]["What runs"]))
    assert steps <= named, sorted(steps - named)


def test_the_three_lab_runbooks_exist_beside_release():
    for name in ("pr-fast", "eval", "nightly", "release"):
        path = ROOT / "runbooks" / f"{name}.md"
        assert path.is_file(), name
        text = path.read_text(encoding="utf-8")
        assert text.startswith(f"# Runbook: {name}") or name == "release", name
        assert "## When" in text
        assert "## Steps" in text
        assert "What a production" in text


def test_a_renamed_target_an_added_step_and_an_emptied_mode_are_each_named():
    text = DOC.read_text(encoding="utf-8")
    renamed = text.replace("`make api-smoke`", "`make api-smoke-test`", 1)
    assert problems(renamed) == [
        "pr-fast: `make api-smoke-test` is no Makefile target",
        "pr-fast: the workflow runs `make api-smoke`, which What runs does not name",
    ]
    workflow = WORKFLOW.read_text(encoding="utf-8").replace(
        "        run: make api-smoke\n",
        "        run: make api-smoke\n      - name: A new step\n        run: make zap\n",
        1,
    )
    assert problems(text, workflow) == [
        "pr-fast: the workflow runs `make zap`, which What runs does not name"
    ]
    [row] = [line for line in text.splitlines() if line.startswith("| nightly |")]
    emptied = text.replace(row, row.rsplit("|", 2)[0] + "|  |", 1)
    assert problems(emptied) == [
        "nightly: mode '' is not one of ('ci', 'local', 'documented only')"
    ]
    gone = text.replace("`runbooks/eval.md`", "`runbooks/evaluate.md`", 1)
    assert problems(gone) == ["eval-on-change: runbooks/evaluate.md does not exist"]
    marker = text.replace("`e2e_fake`, `security`", "`e2e_fake`, `secure`", 1)
    assert problems(marker) == ["pr-fast: marker `secure` is not registered"]
