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

A generation config (S3, `suite = "generation"`, read by `load_generation`) has the same
dataset, chunker, embedder and retriever tables, no [bootstrap] (its intervals are Wilson
intervals at [generation] level), and:

```toml
[generator]
provider = "fake"               # fake (FakeChat, provenance fake) or openai-compat
model = "fake-echo"
# openai-compat also needs base_url (loopback only in S3), digest (64 hex, from the server's
# /api/tags after the pull), temperature, max_tokens and timeout_s; reasoning_effort is optional
# and is sent to the server as it is written

[generation]
trials = 3
seed = 20261018                 # trial t uses seed + t - 1
level = 0.95                    # of the Wilson intervals
probes = "datasets/probes.s3.jsonl"
run_timeout_s = 600             # the whole run's wall-clock cap; a run that hits it is partial

[api]                           # optional: the caller tokens `raglab serve` accepts (lab)
tokens = { demo = ["tenant-a", "tenant-b"] }

[ollama]                        # optional, openai-compat only: the local server's session limits
host = "127.0.0.1:11434"
keep_alive = "2m"
max_loaded_models = 1
num_parallel = 1
context_length = 8192
memory_margin_gb = 8
```
"""

import hashlib
import json
import re
import tomllib
from dataclasses import asdict, dataclass, fields, replace
from pathlib import Path
from typing import cast

from raglab.chunk.sections import ChunkSettings
from raglab.core.types import REQUEST_TENANTS

NAME = re.compile(r"^[a-z0-9-]+$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
SPLITS = ("dev", "test", "all")
SUITES = ("retrieval", "generation")
SECTIONS: dict[str, dict[str, type | tuple[type, ...]]] = {
    "": {"name": str, "suite": str},
    "dataset": {"path": str, "split": str},
    "chunker": {"chunk_size": int, "overlap": int},
    "embedder": {"provider": str, "model": str, "revision": str},
    "retriever": {"kind": str, "k": int, "candidates": int, "rrf_k": int},
    "bootstrap": {"seed": int, "resamples": int, "level": (float, int)},
    "generator": {
        "provider": str,
        "model": str,
        "digest": str,
        "base_url": str,
        "temperature": (float, int),
        "max_tokens": int,
        "timeout_s": (float, int),
        "reasoning_effort": str,
    },
    "generation": {
        "trials": int,
        "seed": int,
        "level": (float, int),
        "probes": str,
        "run_timeout_s": (float, int),
    },
    "api": {"tokens": dict},
    "ollama": {
        "host": str,
        "keep_alive": str,
        "max_loaded_models": int,
        "num_parallel": int,
        "context_length": int,
        "memory_margin_gb": (float, int),
    },
}
OPTIONAL = {
    ("retriever", "candidates"),
    ("retriever", "rrf_k"),
    *(("generator", key) for key in SECTIONS["generator"] if key not in {"provider", "model"}),
}
# the tables each suite has (required) and may have (optional)
TABLES = {
    "retrieval": ({"dataset", "chunker", "embedder", "retriever", "bootstrap"}, set[str]()),
    "generation": (
        {"dataset", "chunker", "embedder", "retriever", "generator", "generation"},
        {"api", "ollama"},
    ),
}
OPENAI_COMPAT_KEYS = frozenset({"base_url", "digest", "temperature", "max_tokens", "timeout_s"})


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


def _read(path: Path) -> tuple[bytes, dict[str, object], str]:
    """(raw bytes, the TOML data, the suite), after the checks every config shares."""
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
    name, suite = str(top["name"]), str(top["suite"])
    if not NAME.match(name):
        raise ConfigError(f"{where}: name {name!r} must be lower case letters, digits and dashes")
    if suite not in SUITES:
        raise ConfigError(f"{where}: suite {suite!r}: only retrieval and generation exist (S3)")
    required, optional = TABLES[suite]
    tables = set(data) - set(SECTIONS[""])
    if tables - required - optional:
        raise ConfigError(
            f"{where}: tables {sorted(tables - required - optional)} are not for suite {suite}"
        )
    return raw, data, suite


def suite_of(path: Path) -> str:
    """The suite a config file names (retrieval or generation)."""
    return _read(path)[2]


@dataclass(frozen=True)
class _Shared:
    """What retrieval and generation configs share."""

    name: str
    suite: str
    path: str
    file_sha256: str
    dataset: str
    split: str
    chunker: ChunkSettings
    embedder: EmbedderConfig
    retriever: RetrieverConfig


def _shared(path: Path, root: Path, raw: bytes, data: dict[str, object], suite: str) -> _Shared:
    where = str(path)
    top = _table(data, "", where)
    dataset = _table(data, "dataset", where)
    chunker = _table(data, "chunker", where)
    embedder = _table(data, "embedder", where)
    retriever = _table(data, "retriever", where)
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
    try:
        settings = ChunkSettings(cast(int, chunker["chunk_size"]), cast(int, chunker["overlap"]))
    except ValueError as error:
        raise ConfigError(f"{where}: {error}") from error
    try:
        rel = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        rel = path.as_posix()
    return _Shared(
        name=str(top["name"]),
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
    )


def load(path: Path, root: Path) -> EvalConfig:
    """A retrieval config."""
    where = str(path)
    raw, data, suite = _read(path)
    if suite != "retrieval":
        raise ConfigError(f"{where}: suite {suite!r}: this command reads retrieval configs only")
    shared = _shared(path, root, raw, data, suite)
    bootstrap = _table(data, "bootstrap", where)
    level = float(cast(float, bootstrap["level"]))
    if not 0 < level < 1 or cast(int, bootstrap["resamples"]) < 1:
        raise ConfigError(f"{where}: bootstrap level must be in (0, 1) and resamples at least 1")
    return EvalConfig(
        **{f.name: getattr(shared, f.name) for f in fields(_Shared)},
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


# ---------------------------------------------------------------- generation configs (S3)


@dataclass(frozen=True)
class GeneratorConfig:
    provider: str
    model: str
    digest: str | None = None
    base_url: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    timeout_s: float | None = None
    reasoning_effort: str | None = None

    def extra(self) -> dict[str, str]:
        """The request fields sent only because the config names them."""
        return {} if self.reasoning_effort is None else {"reasoning_effort": self.reasoning_effort}


@dataclass(frozen=True)
class GenerationSettings:
    trials: int
    seed: int
    level: float
    probes: str
    run_timeout_s: float


@dataclass(frozen=True)
class OllamaSettings:
    """The local server's session settings (raglab.runtime.ollama), given to `ollama serve` as its
    environment and recorded in the manifest."""

    host: str
    keep_alive: str
    max_loaded_models: int
    num_parallel: int
    context_length: int
    memory_margin_gb: float


@dataclass(frozen=True)
class GenerationConfig:
    name: str
    suite: str
    path: str
    file_sha256: str
    dataset: str
    split: str
    chunker: ChunkSettings
    embedder: EmbedderConfig
    retriever: RetrieverConfig
    generator: GeneratorConfig
    generation: GenerationSettings
    tokens: dict[str, frozenset[str]]  # [api] tokens: not part of what a run depends on
    ollama: OllamaSettings | None

    def resolved(self) -> dict[str, object]:
        """Everything the run depends on, as plain data (hashed into the manifest)."""
        out: dict[str, object] = {
            "name": self.name,
            "suite": self.suite,
            "dataset": {"path": self.dataset, "split": self.split},
            "chunker": asdict(self.chunker),
            "embedder": asdict(self.embedder),
            "retriever": {k: v for k, v in asdict(self.retriever).items() if v is not None},
            "generator": {k: v for k, v in asdict(self.generator).items() if v is not None},
            "generation": asdict(self.generation),
        }
        if self.ollama is not None:
            out["ollama"] = asdict(self.ollama)
        return out


def _positive(value: object, where: str, name: str) -> float:
    number = float(cast(float, value))
    if number <= 0:
        raise ConfigError(f"{where}: {name} must be above 0")
    return number


def _generator(table: dict[str, object], where: str, require_digest: bool) -> GeneratorConfig:
    provider, model = str(table["provider"]), str(table["model"])
    given = set(table) - {"provider", "model"}
    if provider == "fake":
        if given:
            raise ConfigError(f"{where}: the fake generator takes provider and model only")
        return GeneratorConfig(provider, model)
    if provider != "openai-compat":
        raise ConfigError(f"{where}: generator provider {provider!r} is not fake or openai-compat")
    if missing := OPENAI_COMPAT_KEYS - given:
        raise ConfigError(f"{where}: an openai-compat generator needs {sorted(missing)}")
    digest = str(table["digest"])
    if require_digest and not DIGEST.match(digest):
        raise ConfigError(
            f"{where}: generator.digest {digest!r} is not a pinned digest (64 hex characters). "
            f"Pull {model}, then copy its digest from the server's /api/tags into the config: "
            "a run refuses to start until the tag's digest is pinned"
        )
    temperature = float(cast(float, table["temperature"]))
    if not 0 <= temperature <= 2:
        raise ConfigError(f"{where}: temperature must be between 0 and 2")
    max_tokens = cast(int, table["max_tokens"])
    if max_tokens < 1:
        raise ConfigError(f"{where}: max_tokens must be at least 1")
    effort = table.get("reasoning_effort")
    return GeneratorConfig(
        provider,
        model,
        digest,
        str(table["base_url"]),
        temperature,
        max_tokens,
        _positive(table["timeout_s"], where, "timeout_s"),
        None if effort is None else str(effort),
    )


def _tokens(data: dict[str, object], where: str) -> dict[str, frozenset[str]]:
    if "api" not in data:
        return {}
    raw = _table(data, "api", where)["tokens"]
    tokens: dict[str, frozenset[str]] = {}
    for token, tenants in cast(dict[object, object], raw).items():
        if not isinstance(tenants, list) or not tenants:
            raise ConfigError(f"{where}: api.tokens.{token} must list the tenants it may use")
        names = cast(list[object], tenants)
        if bad := [t for t in names if t not in REQUEST_TENANTS]:
            raise ConfigError(f"{where}: api.tokens.{token} names unknown tenants {bad}")
        tokens[str(token)] = frozenset(str(t) for t in names)
    return tokens


def _ollama(data: dict[str, object], where: str, provider: str) -> OllamaSettings | None:
    if "ollama" not in data:
        return None
    if provider != "openai-compat":
        raise ConfigError(f"{where}: [ollama] is for an openai-compat generator only")
    table = _table(data, "ollama", where)
    host = str(table["host"])
    if not re.fullmatch(r"(127\.0\.0\.1|localhost):\d{1,5}", host):
        raise ConfigError(f"{where}: ollama.host {host!r} must be loopback (127.0.0.1:<port>)")
    counts = {key: cast(int, table[key]) for key in ("max_loaded_models", "num_parallel")}
    if any(value != 1 for value in counts.values()):
        raise ConfigError(f"{where}: max_loaded_models and num_parallel are 1 on a laptop")
    context = cast(int, table["context_length"])
    if not 1024 <= context <= 131072:
        raise ConfigError(f"{where}: context_length must be between 1024 and 131072")
    return OllamaSettings(
        host,
        str(table["keep_alive"]),
        counts["max_loaded_models"],
        counts["num_parallel"],
        context,
        _positive(table["memory_margin_gb"], where, "memory_margin_gb"),
    )


def load_generation(path: Path, root: Path, require_digest: bool = True) -> GenerationConfig:
    """A generation config. require_digest=False reads a config whose model digest is not pinned
    yet (only the local server's lifecycle commands do, to start the server the pull needs)."""
    where = str(path)
    raw, data, suite = _read(path)
    if suite != "generation":
        raise ConfigError(f"{where}: suite {suite!r}: this command reads generation configs only")
    shared = _shared(path, root, raw, data, suite)
    generator = _generator(_table(data, "generator", where), where, require_digest)
    table = _table(data, "generation", where)
    trials = cast(int, table["trials"])
    level = float(cast(float, table["level"]))
    if trials < 1 or not 0 < level < 1:
        raise ConfigError(f"{where}: trials must be at least 1 and level in (0, 1)")
    generation = GenerationSettings(
        trials,
        cast(int, table["seed"]),
        level,
        str(table["probes"]),
        _positive(table["run_timeout_s"], where, "run_timeout_s"),
    )
    return GenerationConfig(
        **{f.name: getattr(shared, f.name) for f in fields(_Shared)},
        generator=generator,
        generation=generation,
        tokens=_tokens(data, where),
        ollama=_ollama(data, where, generator.provider),
    )
