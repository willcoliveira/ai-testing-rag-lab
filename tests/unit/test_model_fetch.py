"""The model download keeps only files that match their pinned hash, downloads only what is
missing or wrong, and refuses anything but https; loading never downloads (no network here: the
download is a function the test passes in)."""

import hashlib

import pytest

from raglab.adapters import fastembed_embed as fe

pytestmark = pytest.mark.unit
FILES = {"a.json": hashlib.sha256(b"A").hexdigest(), "b.onnx": hashlib.sha256(b"B").hexdigest()}


class Server:
    def __init__(self, content: dict[str, bytes]) -> None:
        self.content = content
        self.asked: list[str] = []

    def __call__(self, url: str) -> bytes:
        self.asked.append(url)
        return self.content[url.rsplit("/", 1)[1]]


def test_the_pins_name_a_full_revision_and_a_hash_per_file():
    assert len(fe.REVISION) == 40
    assert int(fe.REVISION, 16) >= 0
    assert set(fe.FILES) >= {"model_optimized.onnx", "tokenizer.json", "config.json"}
    assert all(len(h) == 64 and int(h, 16) >= 0 for h in fe.FILES.values())
    assert fe.file_url("config.json") == (
        f"https://huggingface.co/Qdrant/bge-small-en-v1.5-onnx-Q/resolve/{fe.REVISION}/config.json"
    )


def test_fetch_downloads_what_is_missing_and_verifies_it(tmp_path):
    server = Server({"a.json": b"A", "b.onnx": b"B"})
    directory, fetched = fe.fetch(tmp_path, FILES, server)
    assert directory == tmp_path / "Qdrant--bge-small-en-v1.5-onnx-Q" / fe.REVISION
    assert fetched == ["a.json", "b.onnx"]
    assert all(u.startswith("https://huggingface.co/") and fe.REVISION in u for u in server.asked)
    assert fe.problems(directory, FILES) == []
    # a second fetch finds everything in place and downloads nothing
    again = Server({})
    assert fe.fetch(tmp_path, FILES, again)[1] == []
    assert again.asked == []
    # an altered file is downloaded again
    (directory / "b.onnx").write_bytes(b"tampered")
    tampered = hashlib.sha256(b"tampered").hexdigest()
    assert fe.problems(directory, FILES) == [
        f"b.onnx has sha256 {tampered}, not the pinned {FILES['b.onnx']}"
    ]
    assert fe.fetch(tmp_path, FILES, server)[1] == ["b.onnx"]


def test_a_download_with_the_wrong_hash_is_never_kept(tmp_path):
    server = Server({"a.json": b"A", "b.onnx": b"not B"})
    with pytest.raises(fe.ModelUnavailable, match=r"b\.onnx from https://.* has sha256"):
        fe.fetch(tmp_path, FILES, server)
    directory = fe.model_dir(tmp_path)
    assert not (directory / "b.onnx").exists()
    assert not (directory / "b.onnx.part").exists()


def test_only_https_is_downloaded():
    with pytest.raises(fe.ModelUnavailable, match="not https"):
        fe.https_get("http://huggingface.co/x")


def test_loading_from_an_empty_cache_says_how_to_get_the_model(tmp_path):
    with pytest.raises(fe.ModelUnavailable, match="run `make model`"):
        fe.FastEmbedEmbedder(tmp_path)


# ---------------------------------------------------------------- S8 (GA10): the second model


def test_the_first_models_pins_are_the_module_names_and_pr_fasts_key():
    """The refactor into specs leaves the first model's pins where every reader finds them."""
    first = fe.PINNED
    assert (
        first.model,
        first.source,
        first.revision,
        first.dimension,
    ) == (fe.MODEL, fe.SOURCE_REPO, fe.REVISION, fe.DIMENSION)
    assert dict(first.files) == fe.FILES
    assert first.pinned
    assert first.onnx_file == "model_optimized.onnx"
    assert fe.MODELS[fe.MODEL] is first
    assert fe.model_dir(fe.cache_root()) == fe.model_dir(fe.cache_root(), first)


def test_the_second_model_is_pinned_and_an_unpinned_spec_is_refused(tmp_path):
    """The swap's spec names the model, its source repository and its dimension, and since the
    maintainer's go of 2026-10-31 a full revision and the sha256 of each of its five files (the
    S8 ledger quotes the fetch); an unpinned spec is refused by fetch and the embedder, so nothing
    is downloaded or loaded that this file does not pin."""
    swap = fe.SWAP
    assert swap.model == "snowflake/snowflake-arctic-embed-xs"
    assert swap.source == "Snowflake/snowflake-arctic-embed-xs"
    assert swap.dimension == fe.PINNED.dimension
    assert swap.onnx_file == "onnx/model.onnx"
    assert swap.pinned
    assert len(swap.revision) == 40
    assert int(swap.revision, 16) >= 0
    assert set(swap.files) == {
        "config.json", "onnx/model.onnx", "special_tokens_map.json", "tokenizer.json",
        "tokenizer_config.json",
    }  # fmt: skip
    assert all(len(h) == 64 and int(h, 16) >= 0 for h in swap.files.values())
    assert swap.url("onnx/model.onnx") == (
        f"https://huggingface.co/{swap.source}/resolve/{swap.revision}/onnx/model.onnx"
    )
    assert fe.MODELS[swap.model] is swap
    assert fe.PINNED.revision != swap.revision
    unpinned = fe.ModelSpec(swap.model, swap.source, "", 384, "onnx/model.onnx")
    assert not unpinned.pinned
    asked = Server({})
    with pytest.raises(fe.ModelUnavailable, match="is not pinned yet"):
        fe.fetch(tmp_path, download=asked, spec=unpinned)
    assert asked.asked == []
    with pytest.raises(fe.ModelUnavailable, match="is not pinned yet"):
        fe.FastEmbedEmbedder(tmp_path, unpinned)
    with pytest.raises(fe.ModelUnavailable, match="is not a pinned embedding model"):
        fe.spec_for("some/other-model")


def test_a_pinned_second_spec_fetches_into_its_own_directory_with_subfolders(tmp_path):
    """Once pinned, the second model's files (one under onnx/) are fetched and checked as the
    first's are, into <cache>/<source repo>/<revision>; a changed pin refuses the download."""
    files = {"onnx/model.onnx": hashlib.sha256(b"M").hexdigest(), "config.json": FILES["a.json"]}
    pinned = fe.ModelSpec(fe.SWAP.model, fe.SWAP.source, "f" * 40, 384, "onnx/model.onnx", files)
    assert pinned.pinned
    server = Server({"model.onnx": b"M", "config.json": b"A"})
    directory, fetched = fe.fetch(tmp_path, download=server, spec=pinned)
    assert directory == tmp_path / "Snowflake--snowflake-arctic-embed-xs" / ("f" * 40)
    assert fetched == ["config.json", "onnx/model.onnx"]
    assert (directory / "onnx" / "model.onnx").read_bytes() == b"M"
    assert fe.problems(directory, files) == []
    assert all(
        u.startswith(f"https://huggingface.co/{pinned.source}/resolve/") for u in server.asked
    )
    changed = fe.ModelSpec(
        pinned.model, pinned.source, pinned.revision, 384, "onnx/model.onnx",
        {**files, "onnx/model.onnx": hashlib.sha256(b"other").hexdigest()},
    )  # fmt: skip
    with pytest.raises(fe.ModelUnavailable, match=r"onnx/model\.onnx from https://.* has sha256"):
        fe.fetch(tmp_path, download=server, spec=changed)
    assert fe.problems(directory, changed.files) == [
        f"onnx/model.onnx has sha256 {files['onnx/model.onnx']}, not the pinned "
        f"{changed.files['onnx/model.onnx']}"
    ]


def test_the_cache_directory_comes_from_the_environment(monkeypatch, tmp_path):
    monkeypatch.setenv(fe.CACHE_ENV, str(tmp_path))
    assert fe.model_dir() == tmp_path / "Qdrant--bge-small-en-v1.5-onnx-Q" / fe.REVISION
    monkeypatch.delenv(fe.CACHE_ENV)
    assert fe.cache_root().parts[-3:] == (".cache", "raglab", "models")
