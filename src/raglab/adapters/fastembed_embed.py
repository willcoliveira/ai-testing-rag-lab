"""The local embedder: BAAI/bge-small-en-v1.5 as ONNX, run by fastembed (onnxruntime, no PyTorch).

The model files are pinned: the ONNX export fastembed uses for this model (Hugging Face repo
Qdrant/bge-small-en-v1.5-onnx-Q) at one commit, with the sha256 of each file. `make model`
(`raglab fetch-model`) downloads them once, over https, into a known cache directory
(RAGLAB_MODEL_DIR, default ~/.cache/raglab/models) and checks every hash; CI restores the same
directory from its cache, keyed by the revision. Loading never downloads: fastembed is given the
directory (specific_model_path), and a missing or altered file stops the load with
ModelUnavailable, so the tests stay offline and a run can only use the pinned files.

S8 (GA10, the embedder swap): the pins are a `ModelSpec`, and `MODELS` holds one per pinned model
by its name. The first, `PINNED`, is the one every config names today and pr-fast caches; its
module-level names (`MODEL`, `SOURCE_REPO`, `REVISION`, `DIMENSION`, `FILES`) are unchanged. The
second, `SWAP`, is a small ONNX export of another family at the same dimension
(snowflake/snowflake-arctic-embed-xs, which fastembed 0.9.0 lists with its source repository):
declared here with its name, source and dimension, and **not pinned yet**: its revision and every
file's sha256 are written only after the maintainer's go for the download (`make model-swap`,
`raglab fetch-model --model snowflake/snowflake-arctic-embed-xs`), from the fetched bytes, never
from this file. `fetch` refuses an unpinned spec, and the factory refuses a config that names one.

onnxruntime runs on one thread, so the same text gives the same vector run after run.
"""

import hashlib
import os
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from types import MappingProxyType

from fastembed import TextEmbedding

CACHE_ENV = "RAGLAB_MODEL_DIR"
BASE_URL = "https://huggingface.co"

type Download = Callable[[str], bytes]


class ModelUnavailable(RuntimeError):
    """The pinned model files are not in the cache, or one does not match its hash."""


@dataclass(frozen=True)
class ModelSpec:
    """One pinned embedding model: its fastembed name, the Hugging Face repository of its ONNX
    export, the commit pinned, its dimension, the ONNX file fastembed loads, and the sha256 of
    every file it reads at that commit. A spec with no revision or no files is not pinned."""

    model: str
    source: str
    revision: str
    dimension: int
    onnx_file: str
    files: Mapping[str, str] = MappingProxyType[str, str]({})

    @property
    def pinned(self) -> bool:
        return bool(self.revision) and bool(self.files) and self.onnx_file in self.files

    def directory(self, root: Path) -> Path:
        """Where the files live: <root>/<source repo>/<revision>."""
        return root / self.source.replace("/", "--") / self.revision

    def url(self, name: str) -> str:
        return f"{BASE_URL}/{self.source}/resolve/{self.revision}/{name}"


PINNED = ModelSpec(
    model="BAAI/bge-small-en-v1.5",
    source="Qdrant/bge-small-en-v1.5-onnx-Q",
    revision="aa8f8b060edb00e03bfdd08813a2949946c8ba55",
    dimension=384,
    onnx_file="model_optimized.onnx",
    # the files fastembed reads for this model, and their sha256 at the revision
    files={
        "config.json": "13582bcf2effc85b7bf3d3f5532e686bc1c9ce86bb009d10f0ec33cbe92299dd",
        "model_optimized.onnx": "51f1bd0addd6e859e42c2c8021a5e5461385bb676a649f4b269aa445449f2431",
        "special_tokens_map.json": "5d5b662e421ea9fac075174bb0688ee0d9431699900b90662acd44b2a350503a",  # noqa: E501
        "tokenizer.json": "d241a60d5e8f04cc1b2b3e9ef7a4921b27bf526d9f6050ab90f9267a1f9e5c66",
        "tokenizer_config.json": "0b29c7bfc889e53b36d9dd3e686dd4300f6525110eaa98c76a5dafceb2029f53",
    },
)
# S8: the second model, another family at the same dimension (fastembed 0.9.0 lists its ONNX
# export at the repository below, model file onnx/model.onnx, about 0.09 GB). Not pinned until the
# maintainer's go for the download: the revision and the hashes come from the fetched bytes.
SWAP = ModelSpec(
    model="snowflake/snowflake-arctic-embed-xs",
    source="Snowflake/snowflake-arctic-embed-xs",
    revision="",
    dimension=384,
    onnx_file="onnx/model.onnx",
)
MODELS: dict[str, ModelSpec] = {PINNED.model: PINNED, SWAP.model: SWAP}

MODEL = PINNED.model
SOURCE_REPO = PINNED.source
REVISION = PINNED.revision
DIMENSION = PINNED.dimension
FILES = dict(PINNED.files)


def spec_for(model: str) -> ModelSpec:
    """The pinned spec a model name names; ModelUnavailable for a name this adapter lacks."""
    if model not in MODELS:
        raise ModelUnavailable(f"{model} is not a pinned embedding model ({', '.join(MODELS)})")
    return MODELS[model]


def cache_root() -> Path:
    configured = os.environ.get(CACHE_ENV)
    return Path(configured) if configured else Path.home() / ".cache" / "raglab" / "models"


def model_dir(root: Path | None = None, spec: ModelSpec = PINNED) -> Path:
    """Where the pinned files live: <root>/<source repo>/<revision>."""
    return spec.directory(root or cache_root())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def problems(directory: Path, files: Mapping[str, str] = PINNED.files) -> list[str]:
    """What is wrong with the files in directory: each one missing or with another hash."""
    found: list[str] = []
    for name, expected in sorted(files.items()):
        path = directory / name
        if not path.is_file():
            found.append(f"{name} is missing")
        elif (actual := sha256_file(path)) != expected:
            found.append(f"{name} has sha256 {actual}, not the pinned {expected}")
    return found


def file_url(name: str, spec: ModelSpec = PINNED) -> str:
    return spec.url(name)


def https_get(url: str) -> bytes:
    if not url.startswith("https://"):
        raise ModelUnavailable(f"refusing a model download that is not https: {url}")
    # https only (checked above); the bytes are checked against the pinned sha256 by fetch
    with urllib.request.urlopen(url, timeout=120) as response:  # noqa: S310  # nosec B310
        return response.read()


def fetch(
    root: Path | None = None,
    files: Mapping[str, str] | None = None,
    download: Download = https_get,
    spec: ModelSpec = PINNED,
) -> tuple[Path, list[str]]:
    """Download every pinned file that is missing or wrong; (directory, names downloaded). A file
    whose bytes do not match its pinned hash is never kept. An unpinned spec is refused: nothing
    is fetched whose revision and hashes are not written here first."""
    wanted = dict(spec.files if files is None else files)
    if not spec.revision or not wanted:
        raise ModelUnavailable(
            f"{spec.model} is not pinned yet (no revision or no file hashes in "
            "raglab.adapters.fastembed_embed): pin its revision and every file's sha256 from the "
            "fetched bytes, with the maintainer's go, before anything is downloaded"
        )
    directory = model_dir(root, spec)
    directory.mkdir(parents=True, exist_ok=True)
    fetched: list[str] = []
    for name, expected in sorted(wanted.items()):
        path = directory / name
        if path.is_file() and sha256_file(path) == expected:
            continue
        data = download(spec.url(name))
        actual = hashlib.sha256(data).hexdigest()
        if actual != expected:
            raise ModelUnavailable(
                f"{name} from {spec.url(name)} has sha256 {actual}, not the pinned {expected}"
            )
        path.parent.mkdir(parents=True, exist_ok=True)
        partial = path.with_name(path.name + ".part")
        partial.write_bytes(data)
        partial.replace(path)
        fetched.append(name)
    return directory, fetched


class FastEmbedEmbedder:
    def __init__(self, root: Path | None = None, spec: ModelSpec = PINNED) -> None:
        if not spec.pinned:
            raise ModelUnavailable(f"{spec.model} is not pinned yet: it cannot be loaded")
        directory = model_dir(root, spec)
        if found := problems(directory, spec.files):
            raise ModelUnavailable(
                f"the pinned {spec.model} files in {directory} are not usable "
                f"({'; '.join(found)}); run `make model` (it downloads them once, outside the "
                "tests)"
            )
        self.spec = spec
        self._model = TextEmbedding(spec.model, specific_model_path=str(directory), threads=1)

    @property
    def model(self) -> str:
        return self.spec.model

    @property
    def revision(self) -> str:
        return self.spec.revision

    @property
    def dimension(self) -> int:
        return self.spec.dimension

    def describe(self) -> dict[str, object]:
        """What a run record says about this embedder."""
        return {
            "provider": "fastembed",
            "model": self.spec.model,
            "source": self.spec.source,
            "revision": self.spec.revision,
            "dimension": self.spec.dimension,
            "onnx_sha256": self.spec.files[self.spec.onnx_file],
            "fastembed": version("fastembed"),
            "onnxruntime": version("onnxruntime"),
        }

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [[float(x) for x in vector] for vector in self._model.embed(list(texts))]

    def embed_query(self, text: str) -> list[float]:
        return [float(x) for x in next(iter(self._model.query_embed(text)))]
