"""`raglab publish` validates a run, runs the privacy check on its files, copies it to
runs/published/<run_id>/ and rebuilds index.json (AC9: the index the playground reads); a dirty,
fake, invalid or private run is refused. And the no-regression gate against the baseline."""

import json
import re
import shutil
from datetime import UTC, datetime
from typing import Any

import pytest

from raglab.evals import gate, publish, record, retrieval
from tests.conftest import ROOT
from tests.golden_support import maintenance
from tests.retrieval_support import fake_run, lab_root, local_run, read_run, reseal

pytestmark = [pytest.mark.unit, pytest.mark.retrieval]


def clean(run_dir, root):
    return []


def test_publish_copies_the_run_and_builds_the_index(tmp_path):
    root = lab_root(tmp_path)
    first = local_run(root, name="retrieval-a")
    second = local_run(
        root, name="retrieval-b", kind="hybrid", when=datetime(2026, 10, 7, 9, 0, 0, tzinfo=UTC)
    )
    dest = publish.publish(first, root, baseline=True, privacy=clean)
    publish.publish(second, root, privacy=clean)
    assert dest == root / "runs" / "published" / first.name
    for name in publish.FILES:
        assert (dest / name).read_bytes() == (first / name).read_bytes()
    index = json.loads((root / "runs" / "published" / "index.json").read_text())
    assert index["schema_version"] == "published-index.v1"
    assert [r["run_id"] for r in index["runs"]] == [second.name, first.name]  # newest first
    entry = index["runs"][1]
    manifest, _ = read_run(first)
    assert entry == {
        "run_id": first.name,
        "path": f"{first.name}/",
        "created_at": "2026-10-06T12:00:00Z",
        "suite": "retrieval",
        "split": "dev",
        "config": "retrieval-a",
        "provenance": "local",
        "git_sha": manifest["git_sha"],
        "embedder": "BAAI/bge-small-en-v1.5@aa8f8b0",
        "retriever": "dense",
        "k": 2,
        "chunk_size": 1200,
        "n": 4,
        "metrics": manifest["results"]["metrics"],
    }
    assert index["baselines"] == {"retrieval/retrieval-a/dev": first.name}
    assert publish.baseline_run(root, "retrieval/retrieval-a/dev") == dest
    assert publish.baseline_run(root, "retrieval/retrieval-b/dev") is None
    # publishing the same run again changes nothing
    publish.publish(first, root, privacy=clean)
    assert json.loads((root / "runs" / "published" / "index.json").read_text()) == index


@pytest.mark.parametrize(
    ("label", "kwargs", "match"),
    [
        ("dirty", {"git": retrieval.GitState("a" * 40, True)}, "dirty work tree"),
        ("fake", {"provenance": "fake"}, "fake provenance"),
    ],
)
def test_a_dirty_or_fake_run_is_refused(tmp_path, label, kwargs, match):
    root = lab_root(tmp_path)
    run_dir = fake_run(root, **kwargs)
    with pytest.raises(publish.PublishError, match=match):
        publish.publish(run_dir, root, privacy=clean)
    assert not (root / "runs" / "published").exists(), label


def test_an_invalid_or_private_run_is_refused(tmp_path):
    root = lab_root(tmp_path)
    run_dir = local_run(root)
    with pytest.raises(publish.PublishError, match="the privacy check found"):
        publish.publish(run_dir, root, privacy=lambda d, r: ["cases.jsonl:3: a private name"])
    (run_dir / record.REPORT).write_text("edited by hand\n")
    with pytest.raises(publish.PublishError, match="not a valid run record"):
        publish.publish(run_dir, root, privacy=clean)
    assert not (root / "runs" / "published").exists()


def test_a_published_run_is_never_replaced_by_other_files(tmp_path):
    root = lab_root(tmp_path)
    run_dir = local_run(root)
    publish.publish(run_dir, root, privacy=clean)
    dest = root / "runs" / "published" / run_dir.name
    (dest / record.REPORT).write_text("changed\n")
    with pytest.raises(publish.PublishError, match="already published with different files"):
        publish.publish(run_dir, root, privacy=clean)


@pytest.mark.skipif(shutil.which("node") is None, reason="the privacy check needs node")
def test_the_real_privacy_check_runs_on_the_run_files(tmp_path):
    """The repo's checker (example list) over a run's directory: clean, then with a string the
    example list forbids (an email address outside the allowlist) planted in the report."""
    root = lab_root(tmp_path)
    shutil.copytree(ROOT / "scripts", root / "scripts")
    shutil.copytree(
        ROOT / "privacy", root / "privacy", ignore=shutil.ignore_patterns("forbidden-strings.txt")
    )
    run_dir = local_run(root)
    assert publish.node_privacy_check(run_dir, root) == []
    report = run_dir / record.REPORT
    address = "@".join(["someone", "private-domain.org"])  # joined here, so this file stays clean
    report.write_text(report.read_text() + f"contact {address}\n")
    assert publish.node_privacy_check(run_dir, root) != []


def test_the_gate_passes_within_one_question_and_fails_below(tmp_path):
    root = lab_root(tmp_path)
    baseline, _ = read_run(local_run(root))
    k = baseline["retriever"]["k"]
    name = f"recall@{k}"
    value = baseline["results"]["metrics"][name]["value"]
    n = baseline["results"]["metrics"][name]["n"]

    def current(recall: float, dataset_sha256: str | None = None):
        manifest = json.loads(json.dumps(baseline))
        manifest["run_id"] = "now"
        manifest["results"]["metrics"][name]["value"] = recall
        if dataset_sha256:
            manifest["dataset"]["sha256"] = dataset_sha256
        return manifest

    assert gate.check(baseline, current(value)).passed
    assert gate.check(baseline, current(round(value - 1 / n, 6))).passed
    verdict = gate.check(baseline, current(round(value - 1 / n - 0.01, 6)))
    assert not verdict.passed
    assert "fails" in verdict.message
    assert f"minus one question (1/{n})" in verdict.message
    stale = gate.check(baseline, current(value, dataset_sha256="0" * 64))
    assert not stale.passed
    assert "publish a new baseline" in stale.message


# ---------------------------------------------------------------- the committed published runs


def test_the_committed_runs_are_valid_local_dev_runs_with_a_current_baseline():
    """runs/published holds real, clean, complete local runs on the dev split (a run holding the
    test cases only under the nightly or release gate: S4 AC9), index.json is what publish builds
    from them, and the dense dev baseline the gate reads was made with today's dataset and config
    (else the gate is stale)."""
    from raglab.evals import config as eval_config

    published = ROOT / publish.PUBLISHED
    index = publish.read_index(published)
    runs = sorted(p.parent for p in published.glob(f"*/{record.MANIFEST}"))
    assert runs, "no published run"
    for run_dir in runs:
        assert record.validate(run_dir, ROOT) == [], run_dir.name
        manifest, cases = record.read(run_dir)
        assert manifest["provenance"] == "local", run_dir.name
        assert manifest["git_dirty"] is False, run_dir.name
        assert manifest["partial"] is False, run_dir.name
        if manifest["split"] == "dev":
            assert {c["split"] for c in cases} == {"dev"}, run_dir.name
        else:
            assert manifest["gate"] in eval_config.HELD_OUT_GATES, run_dir.name
        assert publish.planted_strings(run_dir, ROOT) == [], run_dir.name
    baselines = {str(k): str(v) for k, v in record.as_json(index["baselines"]).items()}
    assert index == publish.build_index(published, baselines)
    key = "retrieval/retrieval-dense/dev"
    baseline_dir = publish.baseline_run(ROOT, key)
    assert baseline_dir is not None, f"no baseline for {key}"
    baseline, _ = record.read(baseline_dir)
    dense = eval_config.load(ROOT / "config" / "retrieval-dense.toml", ROOT)
    dataset = record.as_json(baseline["dataset"])
    assert dataset["sha256"] == record.sha256_bytes((ROOT / dense.dataset).read_bytes())
    used = record.as_json(baseline["config"])
    assert used["sha256"] == eval_config.canonical_sha256(dense.resolved())


def consistency_staleness(root: Any) -> tuple[str, dict[str, tuple[object, object]]]:
    """(the local generation baseline's run id, the stale fields): each field the consistency gate
    reads to call a baseline stale (raglab.evals.gate.STALE), the baseline's value against
    today's, where they differ."""
    from raglab.evals import config as eval_config
    from raglab.generate import prompts

    key = "generation/generation-local-ollama/dev"
    baseline_dir = publish.baseline_run(root, key)
    assert baseline_dir is not None, f"no baseline for {key}"
    baseline, _ = record.read(baseline_dir)
    local = eval_config.load_generation(root / "config" / "local-ollama.toml", root)
    today: dict[str, object] = {
        "dataset.sha256": record.sha256_bytes((root / local.dataset).read_bytes()),
        "config.sha256": eval_config.canonical_sha256(local.resolved()),
        "prompt.sha256": prompts.CURRENT.fingerprint(),
        "generator.digest": local.generator.digest,
        "trials": local.generation.trials,
    }
    recorded: dict[str, object] = {
        "dataset.sha256": record.as_json(baseline["dataset"])["sha256"],
        "config.sha256": record.as_json(baseline["config"])["sha256"],
        "prompt.sha256": record.as_json(baseline["prompt"])["sha256"],
        "generator.digest": record.as_json(baseline["generator"])["digest"],
        "trials": baseline["trials"],
    }
    stale = {k: (recorded[k], today[k]) for k in today if recorded[k] != today[k]}
    return baseline_dir.name, stale


def test_the_committed_consistency_baseline_is_current():
    """answer-v2's AV9: the consistency gate's local baseline (index.json's
    generation/generation-local-ollama/dev) was made with today's dataset, config, current prompt
    (raglab.generate.prompts.CURRENT), model digest and number of trials, the fields the gate
    calls stale (raglab.evals.gate.STALE). Before this test only `make gate-local`, run by hand,
    saw a stale consistency baseline; now pr-fast does. answer-v2 was not adopted (2026-10-23), so
    the baseline is answer-v1's and the current prompt is answer-v1."""
    from raglab.evals import gate

    assert {f"{s}.{k}" if s else k for s, k in gate.STALE} == {
        "dataset.sha256",
        "config.sha256",
        "prompt.sha256",
        "generator.digest",
        "trials",
    }
    run_id, stale = consistency_staleness(ROOT)
    assert not stale, f"the consistency baseline {run_id} is stale: {stale}"


# ---------------------------------------------------------------- S4-J10 (fix round 2)

DATASHEET = ROOT / "datasets" / "DATASHEET.md"
PACK = ROOT / "datasets" / "security" / "README.md"  # S7: the security pack's Versions table
ATTACK_SUITE = "attack"


def listed_dataset_versions(datasheet: Any) -> dict[str, str]:
    """The datasheet's Maintenance table: each version's sha256 of its golden file, read from the
    table's rows (never copied here), as {sha256: version}."""
    rows = maintenance(datasheet.read_text(encoding="utf-8"))
    assert len({row.sha256 for row in rows}) == len(rows), "a sha256 is listed twice"
    return {row.sha256: row.version for row in rows}


def unlisted_dataset_problems(published: Any, datasheet: Any, pack: Any = PACK) -> list[str]:
    """Each published run whose manifest's dataset.sha256 is no version its table lists, or
    whose dataset path is not the file its version's row names (S4b: the File column). A run on
    the golden set is held to the datasheet's Maintenance table; an attack run (S7), whose dataset
    is the security pack's attacks.yaml, to the pack's Versions table (the orchestrator's
    integration decision of 2026-10-25, the S7 ledger)."""
    golden = {row.sha256: row for row in maintenance(datasheet.read_text(encoding="utf-8"))}
    attacks = {row.sha256: row for row in maintenance(pack.read_text(encoding="utf-8"), "Versions")}
    problems: list[str] = []
    for path in sorted(published.glob(f"*/{record.MANIFEST}")):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        dataset = manifest["dataset"]
        sha, name = dataset["sha256"], dataset["path"].rsplit("/", 1)[-1]
        if manifest.get("suite") == ATTACK_SUITE:
            rows, table = attacks, "the security pack's Versions table"
        else:
            rows, table = golden, "the datasheet's Maintenance table"
        row = rows.get(sha)
        if row is None:
            problems.append(f"{path.parent.name}: dataset.sha256 {sha} is no version {table} lists")
        elif row.file != name:
            problems.append(
                f"{path.parent.name}: dataset {dataset['path']} is {row.version} by its sha256, "
                f"whose row names {row.file}"
            )
    return problems


def test_every_published_run_names_a_dataset_version_the_datasheet_lists():
    """S4-J10, the criteria judge's info finding, closed by the user's answer "Close it in this PR"
    (fix round 2). The validator derives a record's labels and behaviour fields again only when
    the record claims the golden file's current sha256, so a record that misstated its dataset
    would keep them unchecked, as history. Every published record must therefore name a version
    the datasheet's Maintenance table lists, read from the table: v1 (the S2 and S3 runs) and
    v1.1 (S4's and later runs on golden.v1.jsonl), and from S4b's runs v2 (golden.v2.jsonl), each
    in the file its row names. The index entries hold no dataset sha256, so the manifests are
    what is read. An attack run (S7) names a version of the security pack's Versions table
    instead (datasets/security/README.md), as the pack's record check has the same limit."""
    listed = listed_dataset_versions(DATASHEET)
    assert {"v1", "v1.1"} <= set(listed.values())
    index = publish.read_index(ROOT / publish.PUBLISHED)
    assert not any("dataset" in record.as_json(run) for run in record.as_list(index["runs"]))
    assert unlisted_dataset_problems(ROOT / publish.PUBLISHED, DATASHEET) == []


def test_a_published_attack_run_is_held_to_the_security_packs_versions(tmp_path):
    """S7, the orchestrator's integration decision of 2026-10-25 (the S7 ledger): an attack
    record's dataset is held to the security pack's Versions table, never to the datasheet.
    Records in a temporary folder: one naming the table's first version of attacks.yaml passes;
    one naming a sha256 the table does not list, one naming a golden-set version and one naming
    the listed sha256 under another file are each named."""
    first = maintenance(PACK.read_text(encoding="utf-8"), "Versions")[0]
    golden = maintenance(DATASHEET.read_text(encoding="utf-8"))[-1]
    published = tmp_path / "runs" / "published"

    def attack_run(run_id: str, sha: str, path: str = "datasets/security/attacks.yaml") -> None:
        target = published / run_id / record.MANIFEST
        target.parent.mkdir(parents=True)
        manifest = {"suite": ATTACK_SUITE, "dataset": {"path": path, "sha256": sha}}
        target.write_text(json.dumps(manifest), encoding="utf-8")

    assert first.file == "attacks.yaml"
    attack_run("a-listed", first.sha256)
    assert unlisted_dataset_problems(published, DATASHEET) == []
    unknown = "0" * 64
    attack_run("b-unlisted", unknown)
    attack_run("c-golden", golden.sha256, f"datasets/{golden.file}")
    attack_run("d-elsewhere", first.sha256, "datasets/security/other.yaml")
    table = "is no version the security pack's Versions table lists"
    assert unlisted_dataset_problems(published, DATASHEET) == [
        f"b-unlisted: dataset.sha256 {unknown} {table}",
        f"c-golden: dataset.sha256 {golden.sha256} {table}",
        f"d-elsewhere: dataset datasets/security/other.yaml is {first.version} by its sha256, "
        f"whose row names {first.file}",
    ]


def test_a_published_run_whose_file_is_not_its_versions_is_named(tmp_path):
    """S4b (GV8): with a File column, a record must also name the file of its version's row. A
    copy of a published v1.1 run that claims golden.v2.jsonl, checked against a datasheet whose
    rows name their files (in a temporary folder), is named."""
    from tests.dataset_support import maintenance as datasheet_of

    rows = maintenance(DATASHEET.read_text(encoding="utf-8"))
    planted = tmp_path / "DATASHEET.md"
    planted.write_text(
        datasheet_of(*((r.version, "golden.v1.jsonl", r.sha256) for r in rows)), encoding="utf-8"
    )
    run_id = "20261019T174018Z-generation-local-ollama-dev-97011a7"
    published = tmp_path / "runs" / "published"
    shutil.copytree(ROOT / publish.PUBLISHED / run_id, published / run_id)
    assert unlisted_dataset_problems(published, planted) == []
    manifest_path = published / run_id / record.MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["dataset"]["path"] = "datasets/golden.v2.jsonl"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    assert unlisted_dataset_problems(published, planted) == [
        f"{run_id}: dataset datasets/golden.v2.jsonl is v1.1 by its sha256, whose row names "
        "golden.v1.jsonl"
    ]


def test_a_published_run_with_a_dataset_hash_no_version_has_is_named(tmp_path):
    """The judge's shape: a copy of a published S4 run with dataset.sha256 set to zeros, in a
    temporary folder (the committed tree is never edited), is named with its run id and hash."""
    run_id = "20261019T174018Z-generation-local-ollama-dev-97011a7"
    published = tmp_path / "runs" / "published"
    shutil.copytree(ROOT / publish.PUBLISHED / run_id, published / run_id)
    manifest_path = published / run_id / record.MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["dataset"]["sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    assert unlisted_dataset_problems(published, DATASHEET) == [
        f"{run_id}: dataset.sha256 {'0' * 64} is no version the datasheet's Maintenance table lists"
    ]


def test_the_versions_are_read_from_the_maintenance_table_only():
    """S4-J11 (fix round 3): the committed datasheet mentions more 64-hex strings than it lists
    versions (a labels judge's seal, in the agreement section, is one), and only the Maintenance
    table's rows are versions. Since S4b the counts are read from the datasheet, never written
    here: every row of the Maintenance section's table that starts with a version is listed,
    with its own sha256, and at least one hash of the datasheet is outside the table."""
    text = DATASHEET.read_text(encoding="utf-8")
    every = set(re.findall(r"[0-9a-f]{64}", text))
    section = text.split("\n## Maintenance\n", 1)[1].split("\n## ", 1)[0]
    version_rows = re.findall(r"^\| \*{0,2}(v\d+(?:\.\d+)*)\*{0,2} \|", section, flags=re.M)
    listed = listed_dataset_versions(DATASHEET)
    assert sorted(listed.values()) == sorted(version_rows)
    assert {"v1", "v1.1"} <= set(listed.values())
    assert set(listed) < every, "a hash outside the Maintenance table (the seal) is no version"


def test_a_hash_outside_the_maintenance_table_is_no_version(tmp_path):
    """S4-J11 (fix round 3): a copy of the datasheet, in a temporary folder, with a backticked
    hash in prose and a version row in another section's table, both before the Maintenance
    section: neither is listed, and the Maintenance rows are."""
    text = DATASHEET.read_text(encoding="utf-8")
    prose, row = "1" * 64, "2" * 64
    head, tail = text.split("\n## Maintenance\n", 1)
    planted = (
        f"{head}\n\nA hash in prose: `{prose}`.\n\n"
        "| Version | Date | Stage | What changed | sha256 |\n|---|---|---|---|---|\n"
        f"| v9 | 2026-10-20 | S9 | planted | `{row}` |\n"
        f"\n## Maintenance\n{tail}"
    )
    copy = tmp_path / "DATASHEET.md"
    copy.write_text(planted, encoding="utf-8")
    listed = listed_dataset_versions(copy)
    assert prose not in listed
    assert row not in listed
    assert listed == listed_dataset_versions(DATASHEET)


def test_a_published_run_edited_to_show_another_tenants_chunk_is_refused(tmp_path):
    """S2 judge D3, as reproduced: the dense baseline copied, R-Q01 (tenant A) given tenant B's
    B-PWD 1.0 3.1 at rank 1 with every flag, score, hash and the report made to agree. The
    validator refuses it, so neither publish nor the gate accepts it."""
    baseline_dir = publish.baseline_run(ROOT, "retrieval/retrieval-dense/dev")
    assert baseline_dir is not None
    run_dir = tmp_path / baseline_dir.name
    shutil.copytree(baseline_dir, run_dir)
    assert record.validate(run_dir, ROOT) == []
    _, cases = read_run(run_dir)
    q01 = next(c for c in cases if c["case_id"] == "R-Q01")
    assert q01["tenant"] == "tenant-a"
    q01["retrieved"][0]["chunk_id"] = "B-PWD@1.0/3.1/1"
    reseal(run_dir, cases)
    assert record.validate(run_dir, ROOT) == [
        "case R-Q01 (tenant-a): chunk B-PWD@1.0/3.1/1 is tenant-b, which it cannot see"
    ]
    with pytest.raises(publish.PublishError, match=r"B-PWD@1\.0/3\.1/1 is tenant-b"):
        publish.publish(run_dir, ROOT, privacy=clean)


# ---------------------------------------------------------------- S3: generation runs


def test_a_fake_generation_run_is_never_published(tmp_path):
    from tests.generation_support import fake_generation_run, generation_root

    root = generation_root(tmp_path)
    run_dir = fake_generation_run(root)
    with pytest.raises(publish.PublishError, match="fake provenance"):
        publish.publish(run_dir, root, privacy=clean)


def test_a_partial_generation_run_is_never_published(tmp_path):
    from tests.generation_support import (
        fake_generation_run,
        generation_config_text,
        generation_root,
    )

    root = generation_root(tmp_path)
    ticks = iter(range(0, 10_000, 100))
    run_dir = fake_generation_run(
        root,
        config_text=generation_config_text(cap=250),
        local=True,
        monotonic=lambda: next(ticks),
    )
    with pytest.raises(publish.PublishError, match="is partial"):
        publish.publish(run_dir, root, privacy=clean)


def test_a_local_generation_run_is_published_with_its_model_in_the_index(tmp_path):
    """A local run of the small pack (the real embedder, the adapter against the stub server)."""
    from tests.generation_support import fake_generation_run, generation_root

    root = generation_root(tmp_path)
    run_dir = fake_generation_run(root, local=True)
    dest = publish.publish(run_dir, root, privacy=clean)
    index: Any = publish.read_index(root / publish.PUBLISHED)
    [entry] = index["runs"]
    assert entry["run_id"] == dest.name
    assert (entry["suite"], entry["generator"], entry["prompt"]) == (
        "generation",
        "stub-model:1b@aaaaaaaaaaaa",
        "answer-v1",
    )
    assert "pass^2" in entry["metrics"]


def test_compare_refuses_generation_runs_without_behaviour_cases(tmp_path):
    """S3 refused every generation pair; S4 compares their behaviour cases (tests/retrieval/
    test_compare.py), so a pair with none, as S3's runs, is still refused."""
    from raglab.evals import compare
    from tests.generation_support import fake_generation_run, generation_root

    root = generation_root(tmp_path)
    a = fake_generation_run(root)
    b = fake_generation_run(root, when=datetime(2026, 10, 18, 13, 0, 0, tzinfo=UTC))
    with pytest.raises(compare.CompareError, match="no behaviour cases to compare"):
        compare.compare(a, b, root)


# ---------------------------------------------------------------- S3 fix round 1 (judge S3-S2)


def test_a_fake_model_run_labelled_local_is_refused(tmp_path):
    """A run made with the fake embedder, its provenance edited to local and the record resealed
    (hashes, report and results made to agree): validate and publish refuse it on the model
    fields, whatever the provenance string says."""
    root = lab_root(tmp_path)
    run_dir = fake_run(root)  # the hashing embedder, provenance fake
    manifest, cases = read_run(run_dir)
    manifest["provenance"] = "local"
    (run_dir / record.MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n")
    reseal(run_dir, cases)
    problems = record.validate(run_dir, root)
    assert any("embedder.provider fake" in p for p in problems), problems
    with pytest.raises(publish.PublishError, match="fake"):
        publish.publish(run_dir, root, privacy=clean)
    assert not (root / publish.PUBLISHED).exists()


def test_a_fake_chat_run_labelled_local_is_refused(tmp_path):
    from tests.generation_support import fake_generation_run, generation_root

    root = generation_root(tmp_path)
    run_dir = fake_generation_run(root, provenance="local")
    problems = record.validate(run_dir, root)
    assert any("generator.provider fake" in p for p in problems), problems
    with pytest.raises(publish.PublishError, match="fake"):
        publish.publish(run_dir, root, privacy=clean)


# ---------------------------------------------------------------- S3 fix round 3 (judge S3-J10)


def test_a_run_whose_model_never_answered_is_partial_and_never_published(tmp_path):
    """A local run (the real embedder, the adapter against the stub server) whose every request
    meets a connection error: every trial is unavailable, so the run is partial, with the count
    in the manifest, and publish refuses it."""
    import httpx

    from tests.generation_support import fake_generation_run, generation_root

    def refused(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    root = generation_root(tmp_path)
    run_dir = fake_generation_run(root, local=True, handler=refused)
    assert record.validate(run_dir, root) == []
    manifest, cases = read_run(run_dir)
    assert {c["status"] for c in cases} == {"unavailable"}
    assert manifest["provenance"] == "local"
    assert manifest["partial"] is True
    assert manifest["results"]["generation"]["status_counts"]["unavailable"] == len(cases)
    assert f"{len(cases)} of {len(cases)} trial(s) unavailable" in manifest["totals"]["stopped"]
    with pytest.raises(publish.PublishError, match="is partial"):
        publish.publish(run_dir, root, privacy=clean)
