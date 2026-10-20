"""S4 AC9: the test slice stays held out. `raglab eval` refuses split test or all outside the
nightly and release gates, for both suites, before any run starts; publish refuses such a run
under any other gate; the nightly config and `make nightly-local` exist; a FakeChat nightly run
validates."""

import re
from datetime import UTC, datetime
from pathlib import Path

import pytest

from raglab.__main__ import main
from raglab.evals import config as eval_config
from raglab.evals import publish, record
from tests.conftest import ROOT

pytestmark = pytest.mark.unit
NIGHTLY = ROOT / "config" / "local-ollama-nightly.toml"
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
    manifest, rows = record.read(run_dir)
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
    target = " ".join(target.replace("$(LOCAL_CONFIG)", "config/local-ollama.toml").split())
    retrieval = (
        "raglab eval --suite retrieval --config config/retrieval-dense.toml --split test "
        "--gate release"
    )
    session = "raglab ollama session --config config/local-ollama.toml"
    assert retrieval in target
    assert session in target
    assert target.index(retrieval) < target.index(session)
    assert "-m live tests/contract/test_chat_contract.py" in target
    assert (
        "raglab eval --suite generation --config config/local-ollama.toml --split test "
        "--gate release" in target
    )
