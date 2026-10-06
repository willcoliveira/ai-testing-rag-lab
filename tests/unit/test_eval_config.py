"""The eval configs are read strictly, and the three committed ones say what the plan compares:
dense at 1,200, hybrid at 1,200 and dense at 600, on the same questions with the pinned model."""

import pytest

from raglab.adapters import factory, fastembed_embed
from raglab.evals import config
from tests.conftest import ROOT
from tests.retrieval_support import config_text

pytestmark = pytest.mark.unit
COMMITTED = sorted((ROOT / "config").glob("retrieval-*.toml"))


def test_the_three_committed_configs():
    loaded = {c.name: c for c in (config.load(p, ROOT) for p in COMMITTED)}
    assert set(loaded) == {"retrieval-dense", "retrieval-hybrid", "retrieval-dense-600"}
    dense, hybrid, small = (
        loaded["retrieval-dense"],
        loaded["retrieval-hybrid"],
        loaded["retrieval-dense-600"],
    )
    assert (dense.retriever.kind, dense.chunker.chunk_size) == ("dense", 1200)
    assert (hybrid.retriever.kind, hybrid.retriever.candidates, hybrid.retriever.rrf_k) == (
        "hybrid",
        50,
        60,
    )
    assert (small.retriever.kind, small.chunker.chunk_size) == ("dense", 600)
    for c in loaded.values():
        assert c.path == f"config/{c.name}.toml"
        assert (c.dataset, c.split, c.retriever.k) == ("datasets/golden.v1.jsonl", "dev", 5)
        assert (c.bootstrap.resamples, c.bootstrap.level) == (2000, 0.95)
        assert c.bootstrap.seed == dense.bootstrap.seed
        assert c.chunker.overlap == 1
        assert (c.embedder.provider, c.embedder.model, c.embedder.revision) == (
            "fastembed",
            fastembed_embed.MODEL,
            fastembed_embed.REVISION,
        )


@pytest.mark.parametrize(
    ("edit", "match"),
    [
        (lambda t: t.replace('kind = "dense"', 'kind = "dense"\ntop_k = 3'), "unknown key"),
        (lambda t: t.replace("k = 2\n", ""), "missing retriever.k"),
        (lambda t: t.replace("k = 2", 'k = "2"'), "wrong type"),
        (lambda t: t.replace("k = 2", "k = true"), "wrong type"),
        (lambda t: t.replace("k = 2", "k = 0"), "k must be"),
        (lambda t: t.replace('split = "dev"', 'split = "train"'), "split"),
        (
            lambda t: t.replace('kind = "dense"', 'kind = "dense"\nrrf_k = 60'),
            "hybrid retriever only",
        ),
        (lambda t: t.replace('kind = "dense"', 'kind = "hybrid"'), "needs candidates and rrf_k"),
        (lambda t: t.replace("chunk_size = 1200", "chunk_size = 0"), "chunk size"),
        (lambda t: t.replace('name = "x"', 'name = "X Y"'), "lower case"),
        (lambda t: t.replace('suite = "retrieval"', 'suite = "judged"'), "only retrieval"),
        (lambda t: t + "\n[extra]\na = 1\n", "unknown tables or keys"),
        (lambda t: t.replace("level = 0.9", "level = 1.5"), "bootstrap level"),
        (lambda t: "not = [toml", "not TOML"),
    ],
)
def test_a_wrong_config_is_refused(tmp_path, edit, match):
    path = tmp_path / "c.toml"
    path.write_text(edit(config_text("x")), encoding="utf-8")
    with pytest.raises(config.ConfigError, match=match):
        config.load(path, tmp_path)


def test_hashes_are_of_the_file_and_of_the_resolved_settings(tmp_path):
    path = tmp_path / "c.toml"
    path.write_text(config_text("x"), encoding="utf-8")
    first = config.load(path, tmp_path)
    path.write_text("# a comment\n" + config_text("x"), encoding="utf-8")
    second = config.load(path, tmp_path)
    assert first.file_sha256 != second.file_sha256
    assert config.canonical_sha256(first.resolved()) == config.canonical_sha256(second.resolved())
    assert config.canonical_sha256({"b": 1, "a": [1, "é"]}) == config.canonical_sha256(
        {"a": [1, "é"], "b": 1}
    )


def test_another_split_changes_the_resolved_settings_and_their_hash(tmp_path):
    """`raglab eval --split all`: the full-set run says so in its config sha256 and run id, so it
    is never taken for the dev baseline the gate reads."""
    path = tmp_path / "c.toml"
    path.write_text(config_text("x"), encoding="utf-8")
    dev = config.load(path, tmp_path)
    full = config.with_split(dev, "all")
    assert (dev.split, full.split) == ("dev", "all")
    assert full.file_sha256 == dev.file_sha256
    assert full.resolved()["dataset"] == {"path": dev.dataset, "split": "all"}
    assert config.canonical_sha256(full.resolved()) != config.canonical_sha256(dev.resolved())
    with pytest.raises(config.ConfigError, match="split 'train'"):
        config.with_split(dev, "train")


def test_the_factory_builds_only_the_pinned_local_embedder():
    with pytest.raises(factory.AdapterError, match="only fastembed"):
        factory.embedder("fake", "hashing-256", "fake")
    with pytest.raises(factory.AdapterError, match="the pinned model"):
        factory.embedder("fastembed", fastembed_embed.MODEL, "main")
