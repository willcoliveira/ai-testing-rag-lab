"""The guard that checks nothing, at every stage: the base of the other guards (each overrides
the stages it owns) and the stand-in where a test needs a pipeline with a layer switched off."""

from collections.abc import Sequence

from raglab.core.types import Answer, GuardEvent, ScoredChunk


class NoopGuardrail:
    @property
    def name(self) -> str:
        return "noop"

    def check_input(
        self, question: str, tenant: str | None, caller_tenants: frozenset[str] | None
    ) -> GuardEvent | None:
        return None

    def check_retrieved(self, tenant: str, retrieved: Sequence[ScoredChunk]) -> GuardEvent | None:
        return None

    def check_output(self, answer: Answer, retrieved_ids: frozenset[str]) -> GuardEvent | None:
        return None
