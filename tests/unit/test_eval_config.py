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
        # S5 made "judged" a suite and S7 "attack"; any other name is refused
        (lambda t: t.replace('suite = "retrieval"', 'suite = "red-team"'), "only retrieval"),
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


# ---------------------------------------------------------------- S3: generation configs


def test_the_committed_generation_configs():
    fake = config.load_generation(ROOT / "config" / "fake.toml", ROOT)
    assert (fake.suite, fake.generator.provider, fake.generator.model) == (
        "generation",
        "fake",
        "fake-echo",
    )
    assert fake.tokens == {
        "demo": frozenset({"tenant-a", "tenant-b"}),
        "tenant-a-only": frozenset({"tenant-a"}),
    }
    local = config.load_generation(
        ROOT / "config" / "local-ollama.toml", ROOT, require_digest=False
    )
    assert (local.generator.provider, local.generator.model) == (
        "openai-compat",
        "nemotron-3.5-lightning:30b-a3b-mlx",
    )
    assert local.generator.base_url == "http://127.0.0.1:11434"
    assert local.generator.extra() == {"reasoning_effort": "none"}
    assert local.generator.response_format == "none"
    assert (local.generator.temperature, local.generator.top_p) == (1.0, 0.95)
    assert local.ollama is not None
    assert (local.ollama.host, local.ollama.max_loaded_models, local.ollama.num_parallel) == (
        "127.0.0.1:11434",
        1,
        1,
    )
    for c in (fake, local):
        assert (c.dataset, c.split, c.retriever.k, c.chunker.chunk_size) == (
            "datasets/golden.v1.jsonl",
            "dev",
            5,
            1200,
        )
        # S4: the probes are golden cases, so no committed config names the S3 probes file
        assert (c.generation.trials, c.generation.probes) == (3, None)
        assert "probes" not in c.resolved()["generation"]  # type: ignore[operator]


def test_a_retrieval_command_refuses_a_generation_config_and_the_reverse():
    with pytest.raises(config.ConfigError, match="retrieval configs only"):
        config.load(ROOT / "config" / "fake.toml", ROOT)
    with pytest.raises(config.ConfigError, match="generation configs only"):
        config.load_generation(ROOT / "config" / "retrieval-dense.toml", ROOT)
    assert config.suite_of(ROOT / "config" / "fake.toml") == "generation"


def test_the_retrieval_configs_resolve_as_they_did_in_s2():
    """The gate compares config.sha256 with the baseline's: S3 must not move it."""
    dense = config.load(ROOT / "config" / "retrieval-dense.toml", ROOT)
    assert set(dense.resolved()) == {
        "name",
        "suite",
        "dataset",
        "chunker",
        "embedder",
        "retriever",
        "bootstrap",
    }


def local_text() -> str:
    return (ROOT / "config" / "local-ollama.toml").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("edit", "match"),
    [
        (
            lambda t: t.replace('provider = "openai-compat"', 'provider = "anthropic"'),
            "not fake or",
        ),
        (lambda t: t.replace("max_tokens = 1024\n", ""), "needs \\['max_tokens'\\]"),
        (lambda t: t.replace("temperature = 1.0", "temperature = 3"), "temperature"),
        (lambda t: t.replace("trials = 3", "trials = 0"), "trials"),
        (lambda t: t.replace("top_p = 0.95", "top_p = 1.5"), "top_p"),
        (
            lambda t: t.replace('response_format = "none"', 'response_format = "json_object"'),
            "response_format",
        ),
        (lambda t: t.replace("run_timeout_s = 3600", "run_timeout_s = 0"), "run_timeout_s"),
        (lambda t: t.replace('host = "127.0.0.1:11434"', 'host = "0.0.0.0:11434"'), "loopback"),
        (lambda t: t.replace("num_parallel = 1", "num_parallel = 4"), "num_parallel"),
        (
            lambda t: t.replace("context_length = 8192", "context_length = 1048576"),
            "context_length",
        ),
        (lambda t: t.replace('tenant-a-only = ["tenant-a"]', 'x = ["shared"]'), "unknown tenants"),
        (lambda t: t + "\n[bootstrap]\nseed = 1\nresamples = 1\nlevel = 0.9\n", "not for suite"),
    ],
)
def test_a_wrong_generation_config_is_refused(tmp_path, edit, match):
    path = tmp_path / "c.toml"
    path.write_text(edit(local_text()), encoding="utf-8")
    with pytest.raises(config.ConfigError, match=match):
        config.load_generation(path, ROOT, require_digest=False)


def test_the_fake_generator_takes_no_server_settings(tmp_path):
    text = (ROOT / "config" / "fake.toml").read_text(encoding="utf-8")
    path = tmp_path / "c.toml"
    path.write_text(text.replace('model = "fake-echo"', 'model = "fake-echo"\nmax_tokens = 5'))
    with pytest.raises(config.ConfigError, match="provider and model only"):
        config.load_generation(path, ROOT)
    path.write_text(text + '\n[ollama]\nhost = "127.0.0.1:11434"\n')
    with pytest.raises(config.ConfigError, match="openai-compat generator only"):
        config.load_generation(path, ROOT)


# ---------------------------------------------------------------- S5: the judge config

JUDGE_CONFIG = ROOT / "config" / "judge-local.toml"


def test_the_committed_judge_config_pins_the_judge_and_shares_the_generators_session_limits():
    judge = config.load_judge(JUDGE_CONFIG, ROOT)
    spec = judge.judge
    assert (judge.name, judge.suite, spec.provider, spec.model) == (
        "judge-local",
        "judged",
        "openai-compat",
        "ministral-3:14b-instruct-2512-q4_K_M",
    )
    # the digest /api/tags reported after the pull, with the tags page's prefix (D3)
    assert spec.digest == "4760c35aeb9d9e9c6174c2492562c0b999e80a222804fd96b1915ab72bbcdcf7"
    assert spec.base_url == "http://127.0.0.1:11434"
    assert (spec.temperature, spec.top_p, spec.extra()) == (0.0, None, {})
    assert spec.response_format in ("json_schema", "none")
    assert (judge.judging.criteria, judge.judging.canaries) == (
        "docs/CRITERIA.md",
        "datasets/canaries.judge.jsonl",
    )
    local = config.load_generation(ROOT / "config" / "local-ollama.toml", ROOT)
    assert judge.ollama == local.ollama  # one model at a time, the same limits
    assert "judge" in judge.resolved()
    assert config.suite_of(JUDGE_CONFIG) == "judged"


def judge_text() -> str:
    return JUDGE_CONFIG.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("edit", "match"),
    [
        (
            lambda t: t.replace('digest = "4760c35a', 'digest = "fill in from /api/tags 4760c35a'),
            "judge.digest .* is not a pinned digest",
        ),
        (lambda t: t.replace('provider = "openai-compat"', 'provider = "anthropic"'), "judge"),
        (lambda t: t.replace("max_tokens = 512\n", ""), "openai-compat judge needs"),
        (lambda t: t.replace('criteria = "docs/CRITERIA.md"\n', ""), "missing judging.criteria"),
        (lambda t: t.replace("level = 0.95", "level = 1.5"), "judging.level"),
        (lambda t: t.replace("run_timeout_s = 7200", "run_timeout_s = 0"), "run_timeout_s"),
        (lambda t: t.replace('host = "127.0.0.1:11434"', 'host = "0.0.0.0:11434"'), "loopback"),
        (lambda t: t + '\n[generator]\nprovider = "fake"\nmodel = "x"\n', "not for suite"),
    ],
)
def test_a_wrong_judge_config_is_refused(tmp_path, edit, match):
    path = tmp_path / "j.toml"
    path.write_text(edit(judge_text()), encoding="utf-8")
    with pytest.raises(config.ConfigError, match=match):
        config.load_judge(path, ROOT)


def test_each_loader_reads_its_own_suite():
    with pytest.raises(config.ConfigError, match="judge configs only"):
        config.load_judge(ROOT / "config" / "local-ollama.toml", ROOT)
    with pytest.raises(config.ConfigError, match="generation configs only"):
        config.load_generation(JUDGE_CONFIG, ROOT)
