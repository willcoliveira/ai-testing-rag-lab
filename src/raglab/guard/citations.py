"""The citation validator (R-02): an answer may cite, and flag as a conflict, only chunks that
were retrieved for it. An answer that points at any other id is blocked: it is withheld (label
abstain, status blocked) and the event names the ids, so a model can never cite a passage it was
not given.

S7 extends it (R-15): an answer that cites, or names in its conflict field, a chunk of a document
outside the register is blocked too, even when that chunk was in the prompt. The register filter
already leaves such chunks out of the prompt; this is the second line, for a pipeline without it.
A chunk is outside the register when its status is not one the register gives (approved,
superseded or reference): ingestion sets the status from corpus/register.yaml, and the attack
loader sets `unregistered`. A document's front matter is never read here.
"""

from collections.abc import Sequence

from raglab.core.types import Answer, GuardEvent, ScoredChunk
from raglab.guard.noop import NoopGuardrail
from raglab.ingest.register import STATUSES as REGISTER_STATUSES


class CitationValidator(NoopGuardrail):
    def __init__(self, register: bool = True) -> None:
        self.register = register  # False: S3's validator, for the defences-off attack runs

    @property
    def name(self) -> str:
        return "citations"

    def rules(self) -> object:
        return {
            "cited_and_conflict_ids": "retrieved for the answer",
            "register_statuses": sorted(REGISTER_STATUSES) if self.register else None,
        }

    def check_output(self, answer: Answer, retrieved: Sequence[ScoredChunk]) -> GuardEvent | None:
        referenced = answer.referenced_ids()
        unknown = sorted(referenced - {r.chunk.chunk_id for r in retrieved})
        if unknown:
            return GuardEvent(
                self.name, "output", f"the answer cites ids that were not retrieved: {unknown}"
            )
        outside = sorted(
            r.chunk.chunk_id
            for r in retrieved
            if self.register
            and r.chunk.chunk_id in referenced
            and r.chunk.status not in REGISTER_STATUSES
        )
        if outside:
            return GuardEvent(
                self.name,
                "output",
                f"rule register-citation: the answer cites or flags chunks of a document outside "
                f"the register: {outside}",
            )
        return None
