"""The leak canaries of corpus/answer-key.yaml (docs/TEST-PLAN.md, section 4): for each tenant, the
strings that identify its content (its name, document ids, titles, contacts and planted phrases).
Read here because YAML stays inside raglab.ingest (scripts/check_architecture.py, rule 3); the
generation suite's abstention oracle and the run record validator use them, so a run record never
has to carry the strings themselves."""

from pathlib import Path
from typing import cast

import yaml

from raglab.core.types import REQUEST_TENANTS

ANSWER_KEY = "corpus/answer-key.yaml"
PARTS = ("tenant", "documents", "titles", "contacts", "phrases")


class AnswerKeyError(ValueError):
    pass


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
