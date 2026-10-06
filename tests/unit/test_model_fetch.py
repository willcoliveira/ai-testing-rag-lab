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


def test_the_cache_directory_comes_from_the_environment(monkeypatch, tmp_path):
    monkeypatch.setenv(fe.CACHE_ENV, str(tmp_path))
    assert fe.model_dir() == tmp_path / "Qdrant--bge-small-en-v1.5-onnx-Q" / fe.REVISION
    monkeypatch.delenv(fe.CACHE_ENV)
    assert fe.cache_root().parts[-3:] == (".cache", "raglab", "models")
