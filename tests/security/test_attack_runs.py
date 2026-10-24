"""The attack suite's runs (S7, AG9, offline): `raglab eval --suite attack` on the fake model and
the real corpus and embedder, its record (raglab.evals.attack_record), the configs and the make
target, and publish's rules for attack runs. The live runs (`make attack-local`) wait for the
maintainer's go; nothing here starts a model server.

AG9's offline break: a copy of a defences-on record with one F-47 string planted in an answer,
resealed so it still validates, is refused by publish naming F-47."""

import json
import re
import shutil
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from functools import cache
from pathlib import Path
from typing import Any

import pytest

from raglab.__main__ import main
from raglab.adapters import factory
from raglab.core.ports import Embedder
from raglab.evals import attack, attack_record, publish, record
from raglab.evals import config as eval_config
from raglab.evals.retrieval import GitState
from raglab.ingest import answer_key
from raglab.ingest import security_pack as pack
from raglab.runtime.egress import EgressGuard
from tests.conftest import ROOT
from tests.generation_support import DIGEST, echo_server, stub_client, stub_ollama
from tests.retrieval_support import local_embedder, read_run

pytestmark = [pytest.mark.security]
GIT = GitState("0123456789abcdef0123456789abcdef01234567", False)
WHEN = datetime(2026, 10, 24, 12, 0, 0, tzinfo=UTC)
LOCAL = ROOT / "config" / "attack-local.toml"
FAKE = ROOT / "config" / "attack-fake.toml"


def clean(run_dir: Path, root: Path) -> list[str]:
    return []


def one_trial(tmp_path: Path, source: Path) -> Path:
    config = tmp_path / source.name
    text = source.read_text(encoding="utf-8").replace("trials = 3", "trials = 1")
    config.write_text(text, encoding="utf-8")
    return config


def cli_run(tmp_path: Path, defences: str, capsys: Any) -> tuple[int, Path, str]:
    out = tmp_path / "runs"
    command = ["eval", "--suite", "attack", "--config", str(one_trial(tmp_path, FAKE))]
    code = main([*command, "--defences", defences, "--out", str(out), "--root", str(ROOT)])
    captured = capsys.readouterr()
    [run_dir] = list(out.iterdir())
    return code, run_dir, captured.err


# ---------------------------------------------------------------- through the CLI, fake model


@pytest.mark.e2e_fake
def test_defences_on_the_fake_attack_run_is_safe_and_valid(tmp_path: Path, capsys):
    code, run_dir, err = cli_run(tmp_path, "on", capsys)
    assert code == 0, err
    assert record.validate(run_dir, ROOT) == []
    manifest, cases = read_run(run_dir)
    block = manifest["attack"]
    assert manifest["suite"] == "attack"
    assert manifest["provenance"] == "fake"
    assert re.fullmatch(r"\d{8}T\d{6}Z-attack-fake-defences-on-dev-[0-9a-f]{7}", manifest["run_id"])
    assert block["configuration"] == "defences-on"
    assert block["pages"] == {"documents": ["T-FAKE", "T-HIDDEN", "T-POISON"], "chunks": 24}
    assert block["quarantined"] == ["T-HIDDEN@1.0/5/1"]
    assert block["egress"] == "none"
    assert manifest["guards"] == attack_record.DEFAULT_GUARDS
    assert manifest["results"]["attack"]["failed_cases"] == []
    listed = {c.id for c in pack.load(ROOT) if c.layer == "attack"}
    assert {c["case_id"] for c in cases} == listed
    assert {c["expected_label"] for c in cases if c["feature_ids"] == ["F-49"]} == {"answer"}
    assert all(r["status"] != "unregistered" for c in cases for r in c["retrieved"])
    report = (run_dir / record.REPORT).read_text(encoding="utf-8")
    assert "configuration defences-on" in report
    assert all(str(c["answer"]) not in report for c in cases if c["answer"])


def test_defences_off_the_attack_run_records_what_lands(records):
    """The stub server echoes like the fake model, so with S3's guards and no scan the attack
    pages reach the answer: a measured result, which never fails the command's gate."""
    run_dir = records["defences-off"]
    assert record.validate(run_dir, ROOT) == []
    manifest, cases = read_run(run_dir)
    assert attack.unsafe(manifest) == []
    assert manifest["guards"] == attack_record.S3_GUARDS
    assert [x["name"] for x in manifest["guard_set"]["layers"]] == attack_record.S3_GUARDS
    assert manifest["attack"]["quarantined"] == []
    assert {c["expected_label"] for c in cases if c["feature_ids"] == ["F-49"]} == {
        "refuse-and-help"
    }
    assert any(r["status"] == "unregistered" for c in cases for r in c["retrieved"])
    assert manifest["results"]["attack"]["failed_cases"], "with the echo model the attack lands"


# ---------------------------------------------------------------- the record, local provenance


class Remembering:
    """The real embedder, remembering each text's vector: a second index of the same chunks
    reuses them (the vectors are the model's own)."""

    def __init__(self, inner: Embedder) -> None:
        self.inner = inner
        self.seen: dict[str, list[float]] = {}

    @property
    def model(self) -> str:
        return self.inner.model

    @property
    def revision(self) -> str:
        return self.inner.revision

    @property
    def dimension(self) -> int:
        return self.inner.dimension

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        new = [t for t in dict.fromkeys(texts) if t not in self.seen]
        if new:
            self.seen.update(zip(new, self.inner.embed_documents(new), strict=True))
        return [self.seen[t] for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self.inner.embed_query(text)


@cache
def local_records(tmp: str) -> dict[str, Path]:
    """A defences-on and a defences-off attack run made with the real corpus and embedder and the
    OpenAI-compatible adapter against the in-process stub server that echoes (provenance local, as
    publish requires), one trial, from a clean commit."""
    config = eval_config.load_generation(one_trial(Path(tmp), LOCAL), ROOT)
    real, description = local_embedder()
    embedder = Remembering(real)  # both configurations index the same texts: embed them once
    model, chat_description, provenance = factory.chat(
        "openai-compat",
        "stub-model:1b",
        digest=DIGEST,
        base_url="http://127.0.0.1:11434",
        temperature=1.0,
        max_tokens=256,
        timeout_s=5,
        client=stub_client(stub_ollama(echo_server)),
    )
    found: dict[str, Path] = {}
    for configuration in attack_record.CONFIGURATIONS:
        built = attack.assemble_for(
            config,
            ROOT,
            configuration,
            embedder=(embedder, description, "local"),
            chat=(model, chat_description, provenance),
        )
        manifest, cases = attack.run(
            config, ROOT, built, configuration, EgressGuard(), git=GIT, clock=lambda: WHEN
        )
        found[configuration] = record.write(Path(tmp) / configuration, manifest, cases)
    return found


@pytest.fixture(scope="module")
def records(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    return local_records(str(tmp_path_factory.mktemp("attack-records")))


@pytest.fixture
def lab(tmp_path: Path) -> Path:
    """A root with what publish and validate read: the schema, the corpus and the pack."""
    root = tmp_path / "repo"
    for part in ("schemas", "corpus", "datasets/security"):
        shutil.copytree(ROOT / part, root / part)
    return root


def copy_of(run_dir: Path, tmp_path: Path) -> Path:
    target = tmp_path / "copy" / run_dir.name
    shutil.copytree(run_dir, target)
    return target


def reseal(run_dir: Path, cases: list[Any], manifest: Any) -> None:
    """Rewrite an attack record whose checks, results, report and hashes agree with its edited
    fields, as a careful hand edit would."""
    banned = [s for strings in answer_key.must_not_contain(ROOT).values() for s in strings]
    canaries = answer_key.canaries(ROOT)
    system = attack_record.PROMPTS[manifest["prompt"]["version"]]
    for case in cases:
        case["checks"] = attack_record.checks(case, banned, canaries, system)
    manifest["results"] = record.expected_results(manifest, cases)
    body = {k: v for k, v in manifest.items() if k != "files"}
    cases_bytes = record.cases_text(cases).encode()
    report_bytes = record.render(body, cases).encode()
    (run_dir / record.CASES).write_bytes(cases_bytes)
    (run_dir / record.REPORT).write_bytes(report_bytes)
    manifest["files"] = {
        record.CASES: record.sha256_bytes(cases_bytes),
        record.REPORT: record.sha256_bytes(report_bytes),
    }
    (run_dir / record.MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n")


def test_a_local_defences_on_record_validates_and_publishes(records, lab: Path):
    run_dir = records["defences-on"]
    assert record.validate(run_dir, ROOT) == []
    manifest, _ = read_run(run_dir)
    assert manifest["provenance"] == "local"
    dest = publish.publish(run_dir, lab, privacy=clean)
    assert dest == lab / publish.PUBLISHED / run_dir.name
    index: Any = publish.read_index(lab / publish.PUBLISHED)
    entry = index["runs"][0]
    assert (entry["suite"], entry["generator"]) == ("attack", f"stub-model:1b@{DIGEST[:12]}")


def test_publish_refuses_a_defences_on_copy_with_an_f47_string_planted(records, lab, tmp_path):
    """AG9's offline break."""
    run_dir = copy_of(records["defences-on"], tmp_path)
    manifest, cases = read_run(run_dir)
    first = next(c for c in cases if c["status"] == "ok" and c["answer"])
    first["answer"] += " " + answer_key.must_not_contain(ROOT)["F-47"][0]
    reseal(run_dir, cases, manifest)
    assert record.validate(run_dir, ROOT) == []
    assert run_dir.name in read_run(run_dir)[0]["run_id"]
    with pytest.raises(publish.PublishError, match="F-47"):
        publish.publish(run_dir, lab, privacy=clean)


def test_publish_refuses_a_defences_off_run(records, lab):
    assert record.validate(records["defences-off"], ROOT) == []
    with pytest.raises(publish.PublishError, match="defences off"):
        publish.publish(records["defences-off"], lab, privacy=clean)


def test_publish_refuses_an_attack_run_whose_egress_guard_saw_an_attempt(records, lab, tmp_path):
    run_dir = copy_of(records["defences-on"], tmp_path)
    manifest, cases = read_run(run_dir)
    manifest["attack"]["egress"] = "lookup 192.0.2.1:80"
    reseal(run_dir, cases, manifest)
    assert record.validate(run_dir, ROOT) == []
    with pytest.raises(publish.PublishError, match=re.escape("egress guard saw lookup 192.0.2.1")):
        publish.publish(run_dir, lab, privacy=clean)
    assert attack.unsafe(manifest) == ["egress: lookup 192.0.2.1:80"]


@pytest.mark.parametrize(
    ("edit", "problem"),
    [
        (lambda c, m: c.update(expected_label="refuse-and-help"), "expected_label is not"),
        (lambda c, m: c["checks"].update(no_planted_string=False), "do not follow"),
        (lambda c, m: c["retrieved"][0].update(status="approved-ish"), "with its status"),
        (lambda c, m: c.update(cited_ids=["A-PWD-V2@9.9/1/1"]), "were not retrieved"),
        (lambda c, m: c.update(question="Something else?"), "are not the pack's"),
        (lambda c, m: m["attack"].update(configuration="defences-off"), "S3's guards"),
    ],
    ids=["expected-label", "a-check", "a-status", "a-citation", "the-question", "configuration"],
)
def test_a_forged_attack_record_is_refused(
    records: dict[str, Path], tmp_path: Path, edit: Callable[[Any, Any], object], problem: str
):
    run_dir = copy_of(records["defences-on"], tmp_path)
    manifest, cases = read_run(run_dir)
    target = next(c for c in cases if c["feature_ids"] == ["F-49"] and c["retrieved"])
    edit(target, manifest)
    (run_dir / record.CASES).write_bytes(record.cases_text(cases).encode())
    manifest["results"] = record.expected_results(manifest, cases)
    body = {k: v for k, v in manifest.items() if k != "files"}
    report = record.render(body, cases).encode()
    (run_dir / record.REPORT).write_bytes(report)
    manifest["files"] = {
        record.CASES: record.sha256_bytes((run_dir / record.CASES).read_bytes()),
        record.REPORT: record.sha256_bytes(report),
    }
    (run_dir / record.MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n")
    found = record.validate(run_dir, ROOT)
    assert any(problem in p for p in found), found


# ---------------------------------------------------------------- labels, configs, make


def test_f49s_label_comes_from_the_key_per_configuration():
    features = answer_key.features(ROOT)
    assert features["F-49"].expected_in_attack_runs == "refuse-and-help"
    assert attack_record.expected_label(features, ["F-49"], "defences-off") == "refuse-and-help"
    assert attack_record.expected_label(features, ["F-49"], "defences-on") == "answer"
    assert attack_record.expected_label(features, ["F-47"], "defences-off") == "answer"
    assert attack_record.expected_label(features, [], "defences-on") is None


def test_the_attack_configs_ask_with_the_consistency_gates_pipeline():
    local = eval_config.load_generation(LOCAL, ROOT)
    gate = eval_config.load_generation(ROOT / "config" / "local-ollama.toml", ROOT)
    fake = eval_config.load_generation(FAKE, ROOT)
    assert (local.suite, local.dataset, local.split) == (
        "attack",
        "datasets/security/attacks.yaml",
        "dev",
    )
    for part in ("chunker", "embedder", "retriever", "generator", "ollama"):
        assert getattr(local, part) == getattr(gate, part), part
    assert (local.generation.trials, local.generation.seed) == (3, gate.generation.seed)
    assert fake.generator.provider == "fake"
    assert (fake.chunker, fake.embedder, fake.retriever) == (
        local.chunker,
        local.embedder,
        local.retriever,
    )


def test_the_gates_refuse_an_attack_config(capsys):
    assert main(["gate", "--config", str(LOCAL), "--root", str(ROOT)]) == 2
    assert "the gates read retrieval and generation configs" in capsys.readouterr().err


def test_make_attack_local_is_one_generator_session_with_both_configurations():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    recipe = makefile.split("\nattack-local:\n", 1)[1].split("\n\n", 1)[0]
    assert "raglab ollama session --config $(ATTACK_CONFIG)" in recipe
    assert "ATTACK_CONFIG := config/attack-local.toml" in makefile
    runs = re.findall(r'--run "([^"]+)"', recipe)
    assert runs == [
        "uv run pytest -m live tests/contract/test_chat_contract.py",
        "uv run raglab eval --suite attack --config $(ATTACK_CONFIG) --defences off",
        "uv run raglab eval --suite attack --config $(ATTACK_CONFIG) --defences on",
    ]
