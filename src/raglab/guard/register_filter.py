"""The register filter (S7, R-15; OWASP LLM05 and LLM09 in docs/THREAT-MODEL.md).

After retrieval and before the prompt is built, every chunk of a document that did not come from
the register is left out: the model never sees it and so cannot cite it. The answer goes on from
the chunks that remain, so a planted page cannot deny service by being retrieved. One event per
document left out names the document id and the rule; it never quotes the chunk.

What decides it is the chunk's status, which only the register gives: ingestion sets it from
corpus/register.yaml (approved, superseded or reference), and the attack loader
(raglab.ingest.attacks) sets `unregistered` for a page that arrived outside it. A page's own front
matter (`kind`, `status`, `test_material`, or a claimed register id) is never read, so a page that
claims to be A-PWD-V2 and current is still left out (corpus/SPEC.md, section 3).

Lab practice: the register is a YAML file. Production would read the document system's approval
state, set at ingestion by the system that holds it, never by the document.
"""

from collections.abc import Sequence

from raglab.core.types import GuardEvent, ScoredChunk
from raglab.guard.noop import NoopGuardrail
from raglab.ingest.register import STATUSES as REGISTER_STATUSES

RULE = "register-membership"


class RegisterFilter(NoopGuardrail):
    @property
    def name(self) -> str:
        return "register"

    def rules(self) -> object:
        return {"rule": RULE, "keeps_statuses": sorted(REGISTER_STATUSES)}

    def drop_retrieved(
        self, tenant: str, retrieved: Sequence[ScoredChunk]
    ) -> tuple[tuple[ScoredChunk, ...], tuple[GuardEvent, ...]]:
        kept: list[ScoredChunk] = []
        dropped: dict[str, int] = {}
        for result in retrieved:
            if result.chunk.status in REGISTER_STATUSES:
                kept.append(result)
            else:
                dropped[result.chunk.doc_id] = dropped.get(result.chunk.doc_id, 0) + 1
        events = tuple(
            GuardEvent(
                self.name,
                "retrieved",
                f"rule {RULE}: {count} chunk(s) of {doc_id} left out, a document outside the "
                "register",
            )
            for doc_id, count in dropped.items()
        )
        return tuple(kept), events
