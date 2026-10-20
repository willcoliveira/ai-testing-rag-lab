"""The leak canaries of corpus/answer-key.yaml (docs/TEST-PLAN.md, section 4): for each tenant, the
strings that identify its content (its name, document ids, titles, contacts and planted phrases).
Read here because YAML stays inside raglab.ingest (scripts/check_architecture.py, rule 3); the
generation suite's abstention oracle and the run record validator use them, so a run record never
has to carry the strings themselves.

`features` (S4) reads what `raglab check-dataset` and the behaviour checks need of each planted
feature: its kind, its clean-run decision label, its locations and the side each takes in a
planted conflict, its silence proof (`must_not_appear`) and its `answer_must_not_contain` strings.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import cast

import yaml

from raglab.core.types import REQUEST_TENANTS

ANSWER_KEY = "corpus/answer-key.yaml"
PARTS = ("tenant", "documents", "titles", "contacts", "phrases")


class AnswerKeyError(ValueError):
    pass


@dataclass(frozen=True)
class Location:
    doc: str
    section: str
    side: str | None  # its side of a planted conflict: old/new, company/external, tenant-a/b


@dataclass(frozen=True)
class Silence:
    """A silence proof: phrases the answer key guarantees are absent from every document of the
    scope (corpus, or one tenant's documents), checked by tests/unit/test_answer_key.py."""

    scope: str
    phrases: tuple[str, ...]


@dataclass(frozen=True)
class Feature:
    id: str
    kind: str
    expected: str  # the clean-run decision label
    tenants: tuple[str, ...]
    locations: tuple[Location, ...]
    conflict: str | None  # version, external or tenant
    silence: Silence | None
    must_not_contain: tuple[str, ...]


def _strings(value: object) -> tuple[str, ...]:
    return tuple(str(v) for v in cast(list[object], value)) if isinstance(value, list) else ()


def features(root: Path) -> dict[str, Feature]:
    """Every feature of the answer key, by id, in the file's order."""
    data: object = yaml.safe_load((root / ANSWER_KEY).read_text(encoding="utf-8"))
    listed = cast(dict[str, object], data).get("features") if isinstance(data, dict) else None
    if not isinstance(listed, list):
        raise AnswerKeyError(f"{ANSWER_KEY}: no features list")
    found: dict[str, Feature] = {}
    for raw in cast(list[object], listed):
        if not isinstance(raw, dict):
            raise AnswerKeyError(f"{ANSWER_KEY}: a feature is not a mapping")
        entry = cast(dict[str, object], raw)
        locations: list[Location] = []
        for item in cast(list[object], entry.get("locations") or []):
            location = cast(dict[str, object], item)
            side = location.get("side")
            locations.append(
                Location(
                    str(location["doc"]),
                    str(location["section"]),
                    None if side is None else str(side),
                )
            )
        rule = entry.get("must_not_appear")
        silence = None
        if isinstance(rule, dict):
            proof = cast(dict[str, object], rule)
            silence = Silence(str(proof.get("scope")), _strings(proof.get("phrases")))
        conflict = entry.get("conflict")
        feature = Feature(
            id=str(entry.get("id")),
            kind=str(entry.get("kind")),
            expected=str(entry.get("expected")),
            tenants=_strings(entry.get("tenants")),
            locations=tuple(locations),
            conflict=None if conflict is None else str(conflict),
            silence=silence,
            must_not_contain=_strings(entry.get("answer_must_not_contain")),
        )
        found[feature.id] = feature
    return found


def must_not_contain(root: Path) -> dict[str, list[str]]:
    """Each feature's answer_must_not_contain strings (the planted secret, personal details and
    attack canaries that no answer may repeat: R-19, R-17), by feature id."""
    data: object = yaml.safe_load((root / ANSWER_KEY).read_text(encoding="utf-8"))
    features = cast(dict[str, object], data).get("features") if isinstance(data, dict) else None
    if not isinstance(features, list):
        raise AnswerKeyError(f"{ANSWER_KEY}: no features list")
    found: dict[str, list[str]] = {}
    for raw in cast(list[object], features):
        if not isinstance(raw, dict):
            continue
        feature = cast(dict[str, object], raw)
        strings = feature.get("answer_must_not_contain")
        if isinstance(strings, list) and strings:
            found[str(feature.get("id"))] = [str(s) for s in cast(list[object], strings)]
    return found


def canaries(root: Path) -> dict[str, list[str]]:
    """Each request tenant's canaries, in the answer key's order."""
    data: object = yaml.safe_load((root / ANSWER_KEY).read_text(encoding="utf-8"))
    table = cast(dict[str, object], data).get("canaries") if isinstance(data, dict) else None
    if not isinstance(table, dict):
        raise AnswerKeyError(f"{ANSWER_KEY}: no canaries table")
    found: dict[str, list[str]] = {}
    for tenant in sorted(REQUEST_TENANTS):
        entry = cast(dict[str, object], table).get(tenant)
        if not isinstance(entry, dict):
            raise AnswerKeyError(f"{ANSWER_KEY}: no canaries for {tenant}")
        strings: list[str] = []
        for part in PARTS:
            value = cast(dict[str, object], entry).get(part)
            items = [value] if isinstance(value, str) else value
            if not isinstance(items, list) or not items:
                raise AnswerKeyError(f"{ANSWER_KEY}: canaries.{tenant}.{part} is empty")
            strings += [str(item) for item in cast(list[object], items)]
        found[tenant] = strings
    return found
