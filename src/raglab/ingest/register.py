"""The machine-readable register, corpus/register.yaml (decision D-05): the list of documents a
clean ingestion run reads. A document's own front matter or text is never the register."""

from dataclasses import dataclass
from pathlib import Path
from typing import cast

import yaml

from raglab.core.types import check_tenant

REGISTER = "corpus/register.yaml"
CORPUS = "corpus"
ATTACKS = "corpus/attacks"
STATUSES = frozenset({"approved", "superseded", "reference"})
FORMATS = {".md": "md", ".pdf": "pdf", ".html": "html", ".png": "png"}


class RegisterError(ValueError):
    pass


@dataclass(frozen=True)
class Entry:
    doc_id: str
    status: str
    supersedes: str | None
    tenant: str
    path: str  # relative to the repo root

    @property
    def format(self) -> str:
        return FORMATS[Path(self.path).suffix]


def safe_path(root: Path, rel: object, where: str) -> str:
    """A corpus path from the register: relative, inside corpus/ (symlinks resolved), never under
    corpus/attacks/, of a known format, and present."""
    if not isinstance(rel, str) or not rel:
        raise RegisterError(f"{where}: path is missing")
    path = Path(rel)
    if path.is_absolute() or ".." in path.parts:
        raise RegisterError(f"{where}: path {rel!r} must be relative, without '..'")
    full = (root / path).resolve()
    corpus = (root / CORPUS).resolve()
    if not full.is_relative_to(corpus):
        raise RegisterError(f"{where}: path {rel!r} is outside {CORPUS}/")
    if full.is_relative_to((root / ATTACKS).resolve()):
        raise RegisterError(
            f"{where}: {rel!r} is an attack file; attack files are never in the register"
        )
    if path.suffix not in FORMATS:
        raise RegisterError(f"{where}: {rel!r} is not one of {sorted(FORMATS)}")
    if not full.is_file():
        raise RegisterError(f"{where}: {rel!r} does not exist")
    return path.as_posix()


def _text(entry: dict[str, object], key: str, where: str) -> str:
    value = entry.get(key)
    if not isinstance(value, str) or not value:
        raise RegisterError(f"{where}: {key} is missing")
    return value


def mapping(value: object, where: str) -> dict[str, object]:
    """A YAML mapping with string keys, or RegisterError."""
    if not isinstance(value, dict):
        raise RegisterError(f"{where}: not a mapping")
    return {str(k): v for k, v in cast(dict[object, object], value).items()}


def read(root: Path) -> list[Entry]:
    """The register's entries, in file order. Any malformed entry stops the run."""
    data = mapping(yaml.safe_load((root / REGISTER).read_text(encoding="utf-8")), REGISTER)
    if data.get("schema_version") != 1:
        raise RegisterError(f"{REGISTER}: expected schema_version 1")
    documents = data.get("documents")
    if not isinstance(documents, list) or not documents:
        raise RegisterError(f"{REGISTER}: no documents")
    entries: list[Entry] = []
    seen: set[str] = set()
    paths: set[str] = set()
    for n, raw in enumerate(cast(list[object], documents), start=1):
        item = mapping(raw, f"{REGISTER} entry {n}")
        doc_id = _text(item, "id", f"{REGISTER} entry {n}")
        where = f"{REGISTER} entry {n} ({doc_id})"
        if doc_id in seen:
            raise RegisterError(f"{where}: id listed twice")
        status = _text(item, "status", where)
        if status not in STATUSES:
            raise RegisterError(f"{where}: status {status!r} is not one of {sorted(STATUSES)}")
        supersedes = item.get("supersedes")
        if supersedes is not None and not isinstance(supersedes, str):
            raise RegisterError(f"{where}: supersedes must be an id or null")
        tenant = check_tenant(item.get("tenant"), where)
        path = safe_path(root, item.get("path"), where)
        if path in paths:
            raise RegisterError(f"{where}: path {path!r} listed twice")
        seen.add(doc_id)
        paths.add(path)
        entries.append(Entry(doc_id, status, supersedes, tenant, path))
    return entries
