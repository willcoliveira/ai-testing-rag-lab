"""The link guard (S7, R-17; "nothing is sent out", OWASP LLM10 in docs/THREAT-MODEL.md): an
answer that holds a link appearing in no register document is withheld (status blocked, label
abstain, no text).

A link is a URL with a scheme, a `www.` host, or a host with a path (raglab.ingest.trusted.LINK);
the planted collector link of F-47 and the fake verify page of F-49 are both refused, with or
without their scheme. An answer's link passes when it is a register document's link, or that link
cut at a `/` (a model may name the site without the page). A register link with a query added, the
way an instruction would carry the user's question out, is another link and is refused. The event
names the rule, never the link.

Lab practice: the allowed links are the register's own. Production would use the document
system's link policy and a URL classifier, and would still render answers as text only, as the
web page and the playground do.
"""

from collections.abc import Iterable, Sequence

from raglab.core.types import Answer, GuardEvent, ScoredChunk
from raglab.guard.noop import NoopGuardrail
from raglab.ingest.trusted import LINK, links

RULE = "register-links"


class LinkGuard(NoopGuardrail):
    def __init__(self, allowed: Iterable[str]) -> None:
        self.allowed = frozenset(allowed)

    @property
    def name(self) -> str:
        return "links"

    def rules(self) -> object:
        return {"rule": RULE, "link": LINK.pattern, "allowed": sorted(self.allowed)}

    def allows(self, link: str) -> bool:
        """Whether a normalised link is a register link, or one cut at a `/`."""
        return any(a == link or a.startswith(link + "/") for a in self.allowed)

    def check_output(self, answer: Answer, retrieved: Sequence[ScoredChunk]) -> GuardEvent | None:
        texts = [answer.text, answer.conflict.note if answer.conflict else ""]
        foreign = [link for text in texts for link in links(text) if not self.allows(link)]
        if not foreign:
            return None
        return GuardEvent(
            self.name,
            "output",
            f"rule {RULE}: the answer holds {len(foreign)} link(s) that appear in no register "
            "document",
        )
