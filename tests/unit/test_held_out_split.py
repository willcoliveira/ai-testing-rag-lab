"""S4 AC9: the test slice stays held out. `raglab eval` refuses split test or all outside the
nightly and release gates, for both suites, before any run starts; publish refuses such a run
under any other gate; the nightly config and `make nightly-local` exist; a FakeChat nightly run
validates."""

import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from raglab.__main__ import main
from raglab.evals import config as eval_config
from raglab.evals import drift, publish, record
from tests.conftest import ROOT
from tests.retrieval_support import read_run

pytestmark = pytest.mark.unit
NIGHTLY = ROOT / "config" / "local-ollama-nightly.toml"
RELEASE = ROOT / "config" / "local-ollama-release.toml"
LOCAL = ROOT / "config" / "local-ollama.toml"
DENSE = ROOT / "config" / "retrieval-dense.toml"
OTHER_GATES = ["manual", "pr-fast", "eval-on-change", "weekly"]


class Reached(Exception):
    """The run got past every refusal and was about to build its embedder or pipeline."""


@pytest.fixture
def stop_at_the_run(monkeypatch: pytest.MonkeyPatch) -> None:
    from raglab.adapters import factory
    from raglab.generate import assemble

    def reached(*args: object, **kwargs: object) -> None:
        raise Reached

    monkeypatch.setattr(factory, "embedder", reached)
    monkeypatch.setattr(assemble, "assemble", reached)


@pytest.mark.usefixtures("stop_at_the_run")
@pytest.mark.parametrize("gate", OTHER_GATES)
def test_eval_refuses_the_test_cases_outside_nightly_and_release(capsys, gate):
    commands = [
        ["--suite", "retrieval", "--config", str(DENSE), "--split", "test"],
        ["--suite", "retrieval", "--config", str(DENSE), "--split", "all"],
        ["--suite", "generation", "--config", str(NIGHTLY)],  # its split is all
    ]
    for command in commands:
        assert main(["eval", *command, "--gate", gate, "--root", str(ROOT)]) == 1, command
        err = capsys.readouterr().err
        assert "holds the test cases, which run only under the nightly or release gate" in err


@pytest.mark.usefixtures("stop_at_the_run")
@pytest.mark.parametrize("gate", ["nightly", "release"])
def test_nightly_and_release_may_run_the_test_cases(gate):
    for command in (
        ["--suite", "retrieval", "--config", str(DENSE), "--split", "all"],
        ["--suite", "generation", "--config", str(NIGHTLY)],
    ):
        with pytest.raises(Reached):
            main(["eval", *command, "--gate", gate, "--root", str(ROOT)])


@pytest.mark.usefixtures("stop_at_the_run")
def test_dev_runs_under_any_gate():
    with pytest.raises(Reached):
        main(["eval", "--suite", "retrieval", "--config", str(DENSE), "--root", str(ROOT)])


def clean(run_dir: Path, root: Path) -> list[str]:
    return []


def test_publish_refuses_a_test_or_all_run_under_any_other_gate(tmp_path):
    from tests.generation_support import (
        fake_generation_run,
        generation_config_text,
        generation_root,
    )
    from tests.retrieval_support import lab_root, local_run

    root = lab_root(tmp_path / "r")
    refused = local_run(root, name="retrieval-a", split="test")
    with pytest.raises(publish.PublishError, match="holds the test cases"):
        publish.publish(refused, root, privacy=clean)
    assert not (root / publish.PUBLISHED).exists()
    allowed = local_run(root, name="retrieval-b", split="test", gate="release")
    assert publish.publish(allowed, root, privacy=clean).is_dir()
    root = generation_root(tmp_path / "g")
    text = generation_config_text(split="all")
    refused = fake_generation_run(root, local=True, config_text=text)
    with pytest.raises(publish.PublishError, match="holds the test cases"):
        publish.publish(refused, root, privacy=clean)
    later = datetime(2026, 10, 18, 13, 0, 0, tzinfo=UTC)
    nightly = fake_generation_run(root, local=True, config_text=text, gate="nightly", when=later)
    assert publish.publish(nightly, root, privacy=clean).is_dir()


def test_a_fakechat_nightly_run_of_every_split_validates(tmp_path):
    from tests.generation_support import behaviour_cases, behaviour_run

    cases = [
        {**c, "split": "test"} if c["id"] in ("B-ABS", "B-TB") else c for c in behaviour_cases()
    ]
    root, run_dir = behaviour_run(tmp_path, cases=cases, split="all", gate="nightly")
    assert record.validate(run_dir, root) == []
    manifest, rows = read_run(run_dir)
    assert (manifest["split"], manifest["gate"], manifest["provenance"]) == (
        "all",
        "nightly",
        "fake",
    )
    assert {r["split"] for r in rows} == {"dev", "test"}
    assert "split all, 2 trial(s), seed 7, gate nightly" in (run_dir / record.REPORT).read_text()


def test_the_nightly_config_is_the_local_config_on_every_split():
    nightly = eval_config.load_generation(NIGHTLY, ROOT)
    local = eval_config.load_generation(LOCAL, ROOT)
    assert (nightly.name, nightly.split) == ("generation-local-ollama-nightly", "all")
    one, two = nightly.resolved(), local.resolved()
    for settings in (one, two):
        settings.pop("name")
        settings.pop("dataset")
    assert one == two
    assert nightly.dataset == local.dataset


def test_make_nightly_local_runs_the_nightly_gate_in_one_session():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert re.search(r"^nightly-local:", makefile, flags=re.M)
    target = makefile.split("\nnightly-local:", 1)[1].split("\n\n", 1)[0].replace("\\\n", "")
    target = target.replace("$(NIGHTLY_CONFIG)", "config/local-ollama-nightly.toml")
    assert "raglab ollama session --config config/local-ollama-nightly.toml" in target
    assert "-m live tests/contract/test_chat_contract.py" in target
    assert (
        "raglab eval --suite generation --config config/local-ollama-nightly.toml --gate nightly"
        in target
    )


def test_make_release_local_runs_the_test_slice_under_the_release_gate():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert re.search(r"^release-local:", makefile, flags=re.M)
    target = makefile.split("\nrelease-local:", 1)[1].split("\n\n", 1)[0].replace("\\\n", " ")
    target = " ".join(
        target.replace("$(RELEASE_CONFIG)", "config/local-ollama-release.toml").split()
    )
    retrieval = (
        "raglab eval --suite retrieval --config config/retrieval-dense.toml --split test "
        "--gate release"
    )
    session = "raglab ollama session --config config/local-ollama-release.toml"
    assert retrieval in target
    assert session in target
    assert target.index(retrieval) < target.index(session)
    assert "-m live tests/contract/test_chat_contract.py" in target
    assert (
        "raglab eval --suite generation --config config/local-ollama-release.toml --gate release"
        in target
    )


def test_the_release_config_is_the_local_config_on_the_test_split():
    release = eval_config.load_generation(RELEASE, ROOT)
    local = eval_config.load_generation(LOCAL, ROOT)
    assert (release.name, release.split) == ("generation-local-ollama-release", "test")
    one, two = release.resolved(), local.resolved()
    for settings in (one, two):
        settings.pop("name")
        settings.pop("dataset")
    assert one == two
    assert release.dataset == local.dataset


# ---------------------------------------------------------------- S8 (GA7): the drift alert


def publish_as_is(root: Path, run_dir: Path) -> None:
    """A fake record placed under runs/published with the index rebuilt (publish itself refuses
    a fake run; the alert reads the index, never the provenance)."""
    published = root / publish.PUBLISHED
    shutil.copytree(run_dir, published / run_dir.name)
    publish.write_index(published, publish.build_index(published, {}))


def test_the_first_nightly_is_the_reference_and_a_drop_fires_the_alert_naming_the_cases(tmp_path):
    """GA7: with no published nightly of the config, the alert block says the run is the
    reference; against a published nightly (a FakeChat pair, paired by case) an identical run
    does not fire, and one with five of seven cases lost fires, naming them; the interval is the
    paired bootstrap's and the alert block validates in the record."""
    from tests.generation_support import Q_ABQ, Q_ABS, Q_ANS, Q_FC, Q_RH, behaviour_run, reply

    root, first = behaviour_run(tmp_path, gate="nightly")
    manifest, cases = read_run(first)
    assert drift.previous_nightly(root, manifest) is None
    assert drift.alert_for(root, manifest, cases) == {
        "gate": "nightly",
        "against": None,
        "fired": False,
        "note": "the first nightly of this config is the reference",
    }
    publish_as_is(root, first)
    later = datetime(2026, 10, 19, 13, 0, 0, tzinfo=UTC)
    _, same = behaviour_run(tmp_path, root=root, gate="nightly", when=later)
    manifest, cases = read_run(same)
    assert drift.previous_nightly(root, manifest) == root / publish.PUBLISHED / first.name
    alert: Any = drift.alert_for(root, manifest, cases)
    assert (alert["against"], alert["fired"], alert["metric"]) == (
        first.name,
        False,
        "behaviour_pass^2",
    )
    assert alert["diff"] == {"value": 0, "ci_low": 0, "ci_high": 0, "n": 7}
    assert alert["flipped"] == {"gained": [], "lost": []}
    worse = {
        Q_ANS: reply("abstain", "The documents do not say."),
        Q_FC: reply("answer", "They expire every 60 days."),
        Q_ABS: reply("answer", "Three attempts a day.", []),
        Q_ABQ: reply("answer", "At most 64 characters."),
        Q_RH: reply("answer", "Yes, share it."),
    }
    even_later = datetime(2026, 10, 19, 14, 0, 0, tzinfo=UTC)
    _, dropped = behaviour_run(tmp_path, worse, root=root, gate="nightly", when=even_later)
    manifest, cases = read_run(dropped)
    alert: Any = drift.alert_for(root, manifest, cases)
    assert alert["fired"] is True
    assert alert["against"] == first.name
    assert alert["diff"]["ci_high"] < 0
    assert set(alert["flipped"]["lost"]) == {"B-ANS", "B-FC", "B-ABS", "B-ABQ", "B-RH"}
    assert alert["flipped"]["gained"] == []
    assert "FIRED against" in drift.line(alert)
    assert "cases lost: " in drift.line(alert)
    manifest["alert"] = alert
    reseal_with_alert(dropped, manifest, cases)
    assert record.validate(dropped, root) == []
    assert "## Drift alert (nightly)" in (dropped / record.REPORT).read_text(encoding="utf-8")
    # a dev run under another gate: no alert block, and a retrieval record refuses one
    assert "alert" not in read_run(first)[0]


def reseal_with_alert(run_dir: Path, manifest: dict, cases: list) -> None:
    import json

    body = {k: v for k, v in manifest.items() if k != "files"}
    cases_bytes = record.cases_text(cases).encode()
    report_bytes = record.render(body, cases).encode()
    (run_dir / record.CASES).write_bytes(cases_bytes)
    (run_dir / record.REPORT).write_bytes(report_bytes)
    body["files"] = {
        record.CASES: record.sha256_bytes(cases_bytes),
        record.REPORT: record.sha256_bytes(report_bytes),
    }
    (run_dir / record.MANIFEST).write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")


def test_an_unpaired_previous_nightly_is_noted_and_never_fires(tmp_path):
    from tests.generation_support import behaviour_run

    root, first = behaviour_run(tmp_path, gate="nightly", trials=2)
    publish_as_is(root, first)
    later = datetime(2026, 10, 19, 13, 0, 0, tzinfo=UTC)
    _, three = behaviour_run(tmp_path, root=root, gate="nightly", trials=3, when=later)
    manifest, cases = read_run(three)
    alert: Any = drift.alert_for(root, manifest, cases)
    assert alert["fired"] is False
    assert alert["against"] == first.name
    assert alert["note"].startswith("not compared: not the same trials")


def test_the_cli_writes_the_alert_on_a_nightly_run_and_never_blocks(tmp_path, capsys, monkeypatch):
    """GA7: `raglab eval --gate nightly` writes the alert block (here, through the fake
    generation config on the dev split: the first nightly of that config, the reference) and a
    fired alert leaves the exit code at 0: it never blocks."""
    source = (ROOT / "config" / "fake.toml").read_text(encoding="utf-8")
    config = tmp_path / "fake.toml"
    config.write_text(source.replace("trials = 3", "trials = 1"), encoding="utf-8")
    out = tmp_path / "runs"
    command = ["eval", "--suite", "generation", "--config", str(config), "--out", str(out)]
    fired = {
        "gate": "nightly",
        "against": "20261019T000000Z-generation-fake-dev-0000000",
        "fired": True,
        "metric": "behaviour_pass^1",
        "diff": {"value": -0.5, "ci_low": -0.7, "ci_high": -0.3, "n": 2},
        "flipped": {"gained": [], "lost": ["G-01", "G-02"]},
    }
    calls: list[str] = []

    def alert_for(root: Path, manifest: dict, cases: list) -> dict:
        calls.append(manifest["run_id"])
        return fired

    monkeypatch.setattr(drift, "alert_for", alert_for)
    code = main([*command, "--gate", "nightly", "--root", str(ROOT)])
    captured = capsys.readouterr()
    assert code == 0, captured.err
    assert len(calls) == 1
    [run_dir] = list(out.iterdir())
    manifest, _ = read_run(run_dir)
    assert manifest["alert"] == fired
    assert record.validate(run_dir, ROOT) == []
    assert "drift alert (nightly): FIRED against" in captured.out
    assert "cases lost: G-01, G-02" in captured.out
    assert "## Drift alert (nightly)" in (run_dir / record.REPORT).read_text(encoding="utf-8")
    # under any other gate no alert is read or written
    shutil.rmtree(out)
    code = main([*command, "--root", str(ROOT)])
    assert code == 0
    assert len(calls) == 1
    [run_dir] = list(out.iterdir())
    assert "alert" not in read_run(run_dir)[0]
