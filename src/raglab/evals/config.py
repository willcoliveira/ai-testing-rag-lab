"""Evaluation configs (config/*.toml): what a run uses, read strictly (an unknown key or a missing
one stops the run, so a typo never falls back to a default silently).

```toml
name = "retrieval-dense"        # lower case, digits and dashes; part of the run id
suite = "retrieval"

[dataset]
path = "datasets/golden.v1.jsonl"
split = "dev"                   # dev, test or all

[chunker]
chunk_size = 1200
overlap = 1

[embedder]
provider = "fastembed"
model = "BAAI/bge-small-en-v1.5"
revision = "<the pinned commit>"

[retriever]
kind = "dense"                  # dense, bm25 or hybrid
k = 5
# candidates = 50, rrf_k = 60   # hybrid only

[bootstrap]
seed = 20261006
resamples = 2000
level = 0.95
```
"""

import hashlib
import json
import re
import tomllib
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import cast

from raglab.chunk.sections import ChunkSettings

NAME = re.compile(r"^[a-z0-9-]+$")
SPLITS = ("dev", "test", "all")
SECTIONS: dict[str, dict[str, type | tuple[type, ...]]] = {
    "": {"name": str, "suite": str},
    "dataset": {"path": str, "split": str},
    "chunker": {"chunk_size": int, "overlap": int},
    "embedder": {"provider": str, "model": str, "revision": str},
    "retriever": {"kind": str, "k": int, "candidates": int, "rrf_k": int},
    "bootstrap": {"seed": int, "resamples": int, "level": (float, int)},
}
OPTIONAL = {("retriever", "candidates"), ("retriever", "rrf_k")}


class ConfigError(ValueError):
    pass


def canonical_sha256(data: object) -> str:
    """sha256 of the data as canonical JSON (sorted keys, no spaces)."""
    text = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EmbedderConfig:
    provider: str
    model: str
    revision: str


@dataclass(frozen=True)
class RetrieverConfig:
    kind: str
    k: int
    candidates: int | None = None
    rrf_k: int | None = None


@dataclass(frozen=True)
class BootstrapConfig:
    seed: int
    resamples: int
    level: float


@dataclass(frozen=True)
class EvalConfig:
    name: str
    suite: str
    path: str  # relative to the repo root
    file_sha256: str
    dataset: str
    split: str
    chunker: ChunkSettings
    embedder: EmbedderConfig
    retriever: RetrieverConfig
    bootstrap: BootstrapConfig

    def resolved(self) -> dict[str, object]:
        """Everything the run depends on, as plain data (hashed into the manifest)."""
        return {
            "name": self.name,
            "suite": self.suite,
            "dataset": {"path": self.dataset, "split": self.split},
            "chunker": asdict(self.chunker),
            "embedder": asdict(self.embedder),
            "retriever": {k: v for k, v in asdict(self.retriever).items() if v is not None},
            "bootstrap": asdict(self.bootstrap),
        }


def _table(data: dict[str, object], section: str, where: str) -> dict[str, object]:
    value = data if not section else data.get(section)
    if not isinstance(value, dict):
        raise ConfigError(f"{where}: no [{section}] table")
    table = {str(k): v for k, v in cast(dict[object, object], value).items()}
    allowed = SECTIONS[section]
    for key, item in table.items():
        if not section and key in SECTIONS:
            continue
        if key not in allowed:
            raise ConfigError(f"{where}: unknown key {(section + '.' if section else '') + key}")
        kind = allowed[key]
        if isinstance(item, bool) or not isinstance(item, kind):
            raise ConfigError(f"{where}: {key} has the wrong type ({type(item).__name__})")
    for key in allowed:
        if key not in table and (section, key) not in OPTIONAL:
            raise ConfigError(f"{where}: missing {(section + '.' if section else '') + key}")
    return table


def load(path: Path, root: Path) -> EvalConfig:
    where = str(path)
    raw = path.read_bytes()
    try:
        data: dict[str, object] = tomllib.loads(raw.decode("utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as error:
        raise ConfigError(f"{where}: not TOML ({error})") from error
    unknown = set(data) - set(SECTIONS) - set(SECTIONS[""])
    if unknown:
        raise ConfigError(f"{where}: unknown tables or keys {sorted(unknown)}")
    top = _table(data, "", where)
    dataset = _table(data, "dataset", where)
    chunker = _table(data, "chunker", where)
    embedder = _table(data, "embedder", where)
    retriever = _table(data, "retriever", where)
    bootstrap = _table(data, "bootstrap", where)
    name, suite = str(top["name"]), str(top["suite"])
    if not NAME.match(name):
        raise ConfigError(f"{where}: name {name!r} must be lower case letters, digits and dashes")
    if suite != "retrieval":
        raise ConfigError(f"{where}: suite {suite!r}: only retrieval exists (S2)")
    split = str(dataset["split"])
    if split not in SPLITS:
        raise ConfigError(f"{where}: split {split!r} is not dev, test or all")
    kind = str(retriever["kind"])
    if kind not in {"dense", "bm25", "hybrid"}:
        raise ConfigError(f"{where}: retriever kind {kind!r} is not dense, bm25 or hybrid")
    hybrid_keys = {"candidates", "rrf_k"} & set(retriever)
    if kind == "hybrid" and hybrid_keys != {"candidates", "rrf_k"}:
        raise ConfigError(f"{where}: a hybrid retriever needs candidates and rrf_k")
    if kind != "hybrid" and hybrid_keys:
        raise ConfigError(f"{where}: candidates and rrf_k are for the hybrid retriever only")
    k = cast(int, retriever["k"])
    if k < 1:
        raise ConfigError(f"{where}: k must be at least 1")
    level = float(cast(float, bootstrap["level"]))
    if not 0 < level < 1 or cast(int, bootstrap["resamples"]) < 1:
        raise ConfigError(f"{where}: bootstrap level must be in (0, 1) and resamples at least 1")
    try:
        settings = ChunkSettings(cast(int, chunker["chunk_size"]), cast(int, chunker["overlap"]))
    except ValueError as error:
        raise ConfigError(f"{where}: {error}") from error
    try:
        rel = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        rel = path.as_posix()
    return EvalConfig(
        name=name,
        suite=suite,
        path=rel,
        file_sha256=hashlib.sha256(raw).hexdigest(),
        dataset=str(dataset["path"]),
        split=split,
        chunker=settings,
        embedder=EmbedderConfig(
            str(embedder["provider"]), str(embedder["model"]), str(embedder["revision"])
        ),
        retriever=RetrieverConfig(
            kind,
            k,
            cast(int | None, retriever.get("candidates")),
            cast(int | None, retriever.get("rrf_k")),
        ),
        bootstrap=BootstrapConfig(
            cast(int, bootstrap["seed"]), cast(int, bootstrap["resamples"]), level
        ),
    )


def with_split(config: EvalConfig, split: str) -> EvalConfig:
    """The same config on another split (`raglab eval --split`): the split is part of the resolved
    settings, so the run id and the config sha256 in the manifest say which questions ran, and a
    run on another split never matches the dev baseline the gate reads."""
    if split not in SPLITS:
        raise ConfigError(f"split {split!r} is not dev, test or all")
    return replace(config, split=split)
