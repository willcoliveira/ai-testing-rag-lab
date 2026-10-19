"""S4 AC7: the consistency gate (Q-05). Behaviour pass^N of a finished dev run against the
published local baseline, with the margin docs/THRESHOLDS.md gives on its consistency row: it
passes at the baseline minus the margin and fails below; it calls the baseline stale on the
dataset sha256, the config sha256, the prompt fingerprint, the model digest or the trials, but not
on a new server version; it refuses a fake run, a partial run and a judgement without a margin;
and it prints one line. Scripted runs (manifests) for the rule, and real records through the CLI
(the in-process stub server, no model)."""

import copy
import json
from datetime import UTC, datetime
from typing import Any

import pytest

from raglab.__main__ import main
from raglab.evals import gate, publish, record
from tests.conftest import ROOT

pytestmark = pytest.mark.unit
N = 10  # the baseline's behaviour cases: one case is 0.1


def manifest(value: float, **changes: Any) -> dict[str, Any]:
    """A scripted run: what the gate reads of a finished generation run."""
    run: dict[str, Any] = {
        "run_id": "20261019T120000Z-generation-local-ollama-dev-0123456",
        "suite": "generation",
        "split": "dev",
        "trials": 3,
        "provenance": "local",
        "partial": False,
        "dataset": {"path": "datasets/golden.v1.jsonl", "sha256": "d" * 64},
        "config": {"name": "generation-local-ollama", "sha256": "c" * 64},
        "prompt": {"version": "answer-v1", "sha256": "e" * 64},
        "generator": {"provider": "openai-compat", "digest": "f" * 64, "server_version": "0.40.6"},
        "embedder": {"provider": "fastembed", "revision": "aa8f8b0"},
        "results": {
            "metrics": {"behaviour_pass^3": {"value": value, "ci_low": 0, "ci_high": 1, "n": N}}
        },
    }
    for path, new in changes.items():
        where = run
        *parents, key = path.split("__")
        for parent in parents:
            where = where[parent]
        where[key] = new
    return run


BASELINE = manifest(0.8, run_id="20261019T110000Z-generation-local-ollama-dev-0123456")


def test_it_passes_at_the_baseline_minus_the_margin_and_fails_below():
    passed = gate.consistency(BASELINE, manifest(0.8), margin=1)
    assert passed.passed
    assert passed.message == (
        "behaviour_pass^3 0.800 (n 10) passes: the threshold is the baseline 0.800 "
        "(20261019T110000Z-generation-local-ollama-dev-0123456) minus 1 case(s) (1/10), 0.700"
    )
    assert gate.consistency(BASELINE, manifest(0.7), margin=1).passed  # at the margin
    below = gate.consistency(BASELINE, manifest(0.6), margin=1)
    assert not below.passed
    assert "0.600 (n 10) fails: the threshold is the baseline 0.800" in below.message
    assert gate.consistency(BASELINE, manifest(0.6), margin=2).passed  # two cases of margin
    assert not gate.consistency(BASELINE, manifest(0.5), margin=2).passed


@pytest.mark.parametrize(
    ("change", "name"),
    [
        ({"dataset__sha256": "0" * 64}, "dataset.sha256"),
        ({"config__sha256": "0" * 64}, "config.sha256"),
        ({"prompt__sha256": "0" * 64}, "prompt.sha256"),
        ({"generator__digest": "0" * 64}, "generator.digest"),
        ({"trials": 5}, "trials"),
    ],
)
def test_a_changed_input_makes_the_baseline_stale(change, name):
    verdict = gate.consistency(BASELINE, manifest(0.8, **change), margin=1)
    assert not verdict.passed
    assert verdict.message.startswith(f"stale: the baseline {BASELINE['run_id']} has another ")
    assert f"another {name} (" in verdict.message
    assert verdict.message.endswith("publish a new baseline in a reviewed pull request")


def test_a_new_server_version_is_not_stale():
    """A new Ollama version is a change the gate exists to see, not a reason to skip it."""
    assert gate.consistency(BASELINE, manifest(0.8, generator__server_version="0.41.0"), 1).passed


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ({"provenance": "fake"}, "is a fake run"),
        ({"generator__provider": "fake"}, "is a fake run (generator.provider fake)"),
        ({"partial": True}, "is partial"),
        ({"split": "all"}, "the gate reads generation runs on the dev split"),
    ],
)
def test_a_fake_partial_or_other_split_run_is_refused(change, reason):
    verdict = gate.consistency(BASELINE, manifest(0.8, **change), margin=1)
    assert not verdict.passed
    assert verdict.message.startswith("refused: ")
    assert reason in verdict.message


def test_without_a_margin_it_refuses_to_judge():
    for margin in (None, 0):
        verdict = gate.consistency(BASELINE, manifest(0.8), margin)
        assert not verdict.passed
        assert verdict.message.startswith("refused: ")
    no_cases = manifest(0.8)
    no_cases["results"]["metrics"] = {}
    assert "no behaviour_pass^3" in gate.consistency(BASELINE, no_cases, 1).message


def test_the_margin_is_read_from_the_consistency_row():
    row = "| behaviour pass^3, dev (Q-05) | local, by hand | {} | reason |"
    assert gate.consistency_margin(row.format("margin: 2 cases below the baseline")) == 2
    assert gate.consistency_margin(row.format("margin: 1 case")) == 1
    assert gate.consistency_margin(row.format("set from runs after the sign-off")) is None
    assert gate.consistency_margin("| recall@5 | pr-fast | margin: 9 cases | r |") is None
    committed = (ROOT / gate.THRESHOLDS).read_text(encoding="utf-8")
    assert "| behaviour pass^3" in committed  # the row exists, and sets no number yet
    assert gate.consistency_margin(committed) is None


# ---------------------------------------------------------------- the CLI, on real records

THRESHOLDS_ROW = "| behaviour pass^2, dev (Q-05) | local | margin: {} | the rule |\n"


def published_baseline(tmp_path):
    """A local run of the behaviour fixture (every case passes) published as the baseline of its
    config, and the root it lives in."""
    from tests.generation_support import behaviour_run

    root, baseline = behaviour_run(tmp_path, local=True)
    publish.publish(baseline, root, baseline=True, privacy=lambda d, r: [])
    return root, baseline


def gate_cli(root, run_dir, capsys) -> tuple[int, list[str]]:
    code = main(["gate", "--run", str(run_dir), "--root", str(root)])
    return code, capsys.readouterr().out.splitlines()


def test_the_cli_gates_a_finished_run_in_one_line(tmp_path, capsys):
    from tests.generation_support import Q_ABS, Q_TB, behaviour_run, reply

    root, baseline = published_baseline(tmp_path)
    (root / "docs").mkdir()
    (root / gate.THRESHOLDS).write_text(THRESHOLDS_ROW.format("1 case"), encoding="utf-8")
    later = datetime(2026, 10, 19, 13, 0, 0, tzinfo=UTC)
    _, same = behaviour_run(tmp_path, local=True, root=root, when=later)
    code, out = gate_cli(root, same, capsys)
    assert (code, len(out)) == (0, 1)
    assert out[0].startswith("consistency gate (Q-05): behaviour_pass^2 1.000 (n 7) passes")
    worse = {
        Q_ABS: reply("answer", "The documents do not say."),
        Q_TB: reply("answer", "Halvenroot does it too.", []),
    }
    _, two_down = behaviour_run(
        tmp_path, worse, local=True, root=root, when=datetime(2026, 10, 19, 14, 0, tzinfo=UTC)
    )
    code, out = gate_cli(root, two_down, capsys)
    assert (code, len(out)) == (1, 1)
    assert "behaviour_pass^2 0.714 (n 7) fails: the threshold is the baseline 1.000" in out[0]
    assert f"({baseline.name}) minus 1 case(s) (1/7), 0.857" in out[0]


def test_the_cli_refuses_without_a_baseline_a_margin_or_a_real_model(tmp_path, capsys):
    from tests.generation_support import behaviour_run

    root, run_dir = behaviour_run(tmp_path, local=True)
    code, out = gate_cli(root, run_dir, capsys)
    assert code == 1
    assert out == [
        "consistency gate (Q-05): refused: no published baseline for "
        f"generation/generation-fake/dev (run {run_dir.name})"
    ]
    root, _ = published_baseline(tmp_path / "b")
    later = datetime(2026, 10, 19, 13, 0, 0, tzinfo=UTC)
    _, current = behaviour_run(tmp_path, local=True, root=root, when=later)
    code, out = gate_cli(root, current, capsys)
    assert code == 1
    assert out[0].startswith(f"consistency gate (Q-05): refused: {gate.THRESHOLDS} sets no margin")
    _, fake = behaviour_run(tmp_path, root=root, when=datetime(2026, 10, 19, 14, 0, tzinfo=UTC))
    (root / "docs").mkdir()
    (root / gate.THRESHOLDS).write_text(THRESHOLDS_ROW.format("1 case"), encoding="utf-8")
    code, out = gate_cli(root, fake, capsys)
    assert code == 1
    assert "is a fake run" in out[0]


def test_the_cli_refuses_a_partial_run_and_an_edited_record(tmp_path, capsys):
    root, _ = published_baseline(tmp_path)
    (root / "docs").mkdir()
    (root / gate.THRESHOLDS).write_text(THRESHOLDS_ROW.format("1 case"), encoding="utf-8")
    from tests.generation_support import behaviour_run

    later = datetime(2026, 10, 19, 13, 0, 0, tzinfo=UTC)
    _, current = behaviour_run(tmp_path, local=True, root=root, when=later)
    edited = copy.deepcopy(json.loads((current / record.MANIFEST).read_text()))
    edited["partial"] = True
    (current / record.MANIFEST).write_text(json.dumps(edited, indent=2) + "\n")
    code, out = gate_cli(root, current, capsys)
    assert code == 1
    assert "is not a valid run record" in out[0]  # the report no longer matches the manifest


def test_make_gate_local_gates_a_dev_run_in_one_session():
    import re

    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert re.search(r"^gate-local:", makefile, flags=re.M)
    target = makefile.split("\ngate-local:", 1)[1].split("\n\n", 1)[0].replace("\\\n", "")
    target = target.replace("$(LOCAL_CONFIG)", "config/local-ollama.toml")
    assert "raglab ollama session --config config/local-ollama.toml" in target
    assert "-m live tests/contract/test_chat_contract.py" in target
    assert "raglab gate --config config/local-ollama.toml" in target
