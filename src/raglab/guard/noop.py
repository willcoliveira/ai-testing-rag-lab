"""The guard that checks nothing, at every stage: the base of the other guards (each overrides
the stages it owns) and the stand-in where a test needs a pipeline with a layer switched off."""

import hashlib
import json
from collections.abc import Sequence

from raglab.core.types import Answer, GuardEvent, ScoredChunk


def rules_sha256(name: str, rules: object) -> str:
    """The sha256 of a layer's name and its rules as canonical JSON (S7: the guard set's
    fingerprint)."""
    text = json.dumps({"layer": name, "rules": rules}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class NoopGuardrail:
    @property
    def name(self) -> str:
        return "noop"

    def rules(self) -> object:
        """What the layer's fingerprint covers: its patterns, limits and lists (S7)."""
        return None

    def fingerprint(self) -> str:
        return rules_sha256(self.name, self.rules())

    def check_input(
        self, question: str, tenant: str | None, caller_tenants: frozenset[str] | None
    ) -> GuardEvent | None:
        return None

    def check_retrieved(self, tenant: str, retrieved: Sequence[ScoredChunk]) -> GuardEvent | None:
        return None

    def drop_retrieved(
        self, tenant: str, retrieved: Sequence[ScoredChunk]
    ) -> tuple[tuple[ScoredChunk, ...], tuple[GuardEvent, ...]]:
        return tuple(retrieved), ()

    def check_output(self, answer: Answer, retrieved: Sequence[ScoredChunk]) -> GuardEvent | None:
        return None
