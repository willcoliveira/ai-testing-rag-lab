"""The citation validator (R-02): an answer may cite, and flag as a conflict, only chunks that
were retrieved for it. An answer that points at any other id is blocked: it is withheld (label
abstain, status blocked) and the event names the ids, so a model can never cite a passage it was
not given."""

from raglab.core.types import Answer, GuardEvent
from raglab.guard.noop import NoopGuardrail


class CitationValidator(NoopGuardrail):
    @property
    def name(self) -> str:
        return "citations"

    def check_output(self, answer: Answer, retrieved_ids: frozenset[str]) -> GuardEvent | None:
        unknown = sorted(answer.referenced_ids() - retrieved_ids)
        if not unknown:
            return None
        return GuardEvent(
            self.name, "output", f"the answer cites ids that were not retrieved: {unknown}"
        )
