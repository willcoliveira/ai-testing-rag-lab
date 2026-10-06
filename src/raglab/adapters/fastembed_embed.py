"""The local embedder: BAAI/bge-small-en-v1.5 as ONNX, run by fastembed (onnxruntime, no PyTorch).

The model files are pinned: the ONNX export fastembed uses for this model (Hugging Face repo
Qdrant/bge-small-en-v1.5-onnx-Q) at one commit, with the sha256 of each file. `make model`
(`raglab fetch-model`) downloads them once, over https, into a known cache directory
(RAGLAB_MODEL_DIR, default ~/.cache/raglab/models) and checks every hash; CI restores the same
directory from its cache, keyed by the revision. Loading never downloads: fastembed is given the
directory (specific_model_path), and a missing or altered file stops the load with
ModelUnavailable, so the tests stay offline and a run can only use the pinned files.

onnxruntime runs on one thread, so the same text gives the same vector run after run.
"""

import hashlib
import os
import urllib.request
from collections.abc import Callable, Sequence
from importlib.metadata import version
from pathlib import Path

from fastembed import TextEmbedding

MODEL = "BAAI/bge-small-en-v1.5"
SOURCE_REPO = "Qdrant/bge-small-en-v1.5-onnx-Q"
REVISION = "aa8f8b060edb00e03bfdd08813a2949946c8ba55"
DIMENSION = 384
# the files fastembed reads for this model, and their sha256 at REVISION
FILES = {
    "config.json": "13582bcf2effc85b7bf3d3f5532e686bc1c9ce86bb009d10f0ec33cbe92299dd",
    "model_optimized.onnx": "51f1bd0addd6e859e42c2c8021a5e5461385bb676a649f4b269aa445449f2431",
    "special_tokens_map.json": "5d5b662e421ea9fac075174bb0688ee0d9431699900b90662acd44b2a350503a",
    "tokenizer.json": "d241a60d5e8f04cc1b2b3e9ef7a4921b27bf526d9f6050ab90f9267a1f9e5c66",
    "tokenizer_config.json": "0b29c7bfc889e53b36d9dd3e686dd4300f6525110eaa98c76a5dafceb2029f53",
}
CACHE_ENV = "RAGLAB_MODEL_DIR"
BASE_URL = "https://huggingface.co"

type Download = Callable[[str], bytes]


class ModelUnavailable(RuntimeError):
    """The pinned model files are not in the cache, or one does not match its hash."""


def cache_root() -> Path:
    configured = os.environ.get(CACHE_ENV)
    return Path(configured) if configured else Path.home() / ".cache" / "raglab" / "models"


def model_dir(root: Path | None = None) -> Path:
    """Where the pinned files live: <root>/<source repo>/<revision>."""
    return (root or cache_root()) / SOURCE_REPO.replace("/", "--") / REVISION


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def problems(directory: Path, files: dict[str, str] = FILES) -> list[str]:
    """What is wrong with the files in directory: each one missing or with another hash."""
    found: list[str] = []
    for name, expected in sorted(files.items()):
        path = directory / name
        if not path.is_file():
            found.append(f"{name} is missing")
        elif (actual := sha256_file(path)) != expected:
            found.append(f"{name} has sha256 {actual}, not the pinned {expected}")
    return found


def file_url(name: str) -> str:
    return f"{BASE_URL}/{SOURCE_REPO}/resolve/{REVISION}/{name}"


def https_get(url: str) -> bytes:
    if not url.startswith("https://"):
        raise ModelUnavailable(f"refusing a model download that is not https: {url}")
    # https only (checked above); the bytes are checked against the pinned sha256 by fetch
    with urllib.request.urlopen(url, timeout=120) as response:  # noqa: S310  # nosec B310
        return response.read()


def fetch(
    root: Path | None = None, files: dict[str, str] = FILES, download: Download = https_get
) -> tuple[Path, list[str]]:
    """Download every pinned file that is missing or wrong; (directory, names downloaded). A file
    whose bytes do not match its pinned hash is never kept."""
    directory = model_dir(root)
    directory.mkdir(parents=True, exist_ok=True)
    fetched: list[str] = []
    for name, expected in sorted(files.items()):
        path = directory / name
        if path.is_file() and sha256_file(path) == expected:
            continue
        data = download(file_url(name))
        actual = hashlib.sha256(data).hexdigest()
        if actual != expected:
            raise ModelUnavailable(
                f"{name} from {file_url(name)} has sha256 {actual}, not the pinned {expected}"
            )
        partial = path.with_name(name + ".part")
        partial.write_bytes(data)
        partial.replace(path)
        fetched.append(name)
    return directory, fetched


class FastEmbedEmbedder:
    def __init__(self, root: Path | None = None) -> None:
        directory = model_dir(root)
        if found := problems(directory):
            raise ModelUnavailable(
                f"the pinned {MODEL} files in {directory} are not usable ({'; '.join(found)}); "
                "run `make model` (it downloads them once, outside the tests)"
            )
        self._model = TextEmbedding(MODEL, specific_model_path=str(directory), threads=1)

    @property
    def model(self) -> str:
        return MODEL

    @property
    def revision(self) -> str:
        return REVISION

    @property
    def dimension(self) -> int:
        return DIMENSION

    def describe(self) -> dict[str, object]:
        """What a run record says about this embedder."""
        return {
            "provider": "fastembed",
            "model": MODEL,
            "source": SOURCE_REPO,
            "revision": REVISION,
            "dimension": DIMENSION,
            "onnx_sha256": FILES["model_optimized.onnx"],
            "fastembed": version("fastembed"),
            "onnxruntime": version("onnxruntime"),
        }

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [[float(x) for x in vector] for vector in self._model.embed(list(texts))]

    def embed_query(self, text: str) -> list[float]:
        return [float(x) for x in next(iter(self._model.query_embed(text)))]
