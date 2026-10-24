"""The instruction scan (S7, R-17, arrow L9 of docs/TEST-PLAN.md; OWASP LLM01 in
docs/THREAT-MODEL.md): text in a document that is addressed to the assistant and tries to change
its rules or to send something out.

A chunk is flagged when it matches two of the three rule groups:

- **addressed**: it speaks to the assistant ("Note to AI assistants:", "If you are an AI ...",
  a role line or a control token dressed as a system message, a frame tag);
- **change**: it tells the reader to drop its rules ("ignore all other ... policies", "tell the
  user that ...", "new instructions:", "from now on");
- **send**: it asks for something to leave in the answer ("end every answer with ...", "include
  the link ...", "followed by the user's question", a link whose last query parameter waits for a
  value, a Markdown image).

One group alone is ordinary policy prose: a policy may say "ignore a sign-in prompt you did not
start", "send the request to the Service Desk" or "do not paste Confidential data into AI
assistants". A flagged chunk is quarantined: it is kept out of the index, so no request can
retrieve it, and the event names the chunk id and the rule groups, never the text.

The scan runs where the index is built (raglab.generate.assemble and the attack suite), after the
inventory, so the chunk inventory and its snapshot never change; on the clean pack it flags
nothing, so a clean run searches the same chunks with the same corpus sha256.

The input injection detector (raglab.guard.injection) reuses the strong rules of the change and
send groups (STRONG_CHANGE, STRONG_SEND) on questions, where one rule is enough.

Lab practice: these are rules, written from the requirements. Paraphrase, encodings and other
languages pass them; production would add a classifier, and S7b compares one.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from raglab.core.types import Chunk, GuardEvent

LAYER = "instruction-scan"
_I = re.IGNORECASE | re.MULTILINE

_AI = (
    r"(?:ai|a\.i\.|llms?|(?:large\s+)?language\s+models?|chat\s?bots?|virtual\s+assistants?|"
    r"assistants?)"
)

ADDRESSED: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(?:note|message|instructions?|attention|notice|reminder|memo|warning)\s+(?:to|for)\s+"
        rf"(?:the\s+|any\s+|all\s+)?(?:ai\s+)?{_AI}\b",
        _I,
    ),
    re.compile(rf"\b(?:dear|hey|hello|attention)\s*,?\s+(?:ai|{_AI})\b", _I),
    re.compile(rf"\bif\s+you\s+are\s+(?:an?\s+)?(?:ai|{_AI}|automated\s+system)\b", _I),
    re.compile(
        rf"\b(?:to|for)\s+(?:the|any)\s+{_AI}\s+(?:reading|processing|summari[sz]ing)\b", _I
    ),
    re.compile(r"^\s*(?:system|assistant)\s*(?:message|prompt)?\s*:", _I),
    re.compile(r"\bdeveloper\s+(?:message|prompt|instructions?)\s*:", _I),
    re.compile(r"<\|[a-z_]+\|>|<<\s*/?sys\s*>>|\[/?inst\]|\[/?system\]", _I),
    re.compile(r"</?(?:system|chunk|question)\b", _I),
)

# the change rules a question may not hold either (raglab.guard.injection): each asks the reader
# to drop or replace its rules, which no policy question does
STRONG_CHANGE: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(?:ignore|disregard|forget|override|overrule|bypass)\s+(?:(?:all|any|every|the|your|"
        r"my)\s+)?(?:previous|prior|preceding|above|earlier|existing|other|original|initial|"
        r"system|safety|these|those|all|any|every|your)\s+(?:\w+\s+){0,2}?(?:instructions?|"
        r"rules?|polic(?:y|ies)|guidelines?|prompts?|directions?|directives?|context|"
        r"guardrails?|restrictions?|system\s+messages?)\b",
        _I,
    ),
    re.compile(r"\b(?:new|updated|revised|real|actual|true)\s+instructions?\s*:", _I),
    re.compile(
        r"\bdo\s+not\s+follow\s+(?:the|your|any)\s+(?:\w+\s+)?(?:rules?|instructions?|prompts?)\b",
        _I,
    ),
    re.compile(
        r"\byou\s+(?:must|will|should)\s+now\s+(?:ignore|answer|act|respond|reply|say|tell|"
        r"follow|obey|reveal|forget)\b",
        _I,
    ),
    re.compile(r"\bpretend\s+(?:that\s+)?you\s+(?:are|have\s+no)\b", _I),
    re.compile(
        r"\byou\s+are\s+now\s+(?:an?\s+|in\s+|my\s+|the\s+)?(?:unrestricted|unfiltered|"
        r"jailbroken|different|new|evil|dan\b)",
        _I,
    ),
)

CHANGE: tuple[re.Pattern[str], ...] = (
    *STRONG_CHANGE,
    re.compile(r"\bfrom\s+now\s+on\b", _I),
    re.compile(
        r"\b(?:tell|inform|convince|assure)\s+(?:the\s+)?(?:user|reader|asker)s?\s+that\b", _I
    ),
    re.compile(r"\b(?:developer\s+mode|dan\s+mode|do\s+anything\s+now|god\s+mode)\b", _I),
    re.compile(r"\bwithout\s+(?:any\s+)?(?:restrictions|filters|guardrails)\b", _I),
)

# the send rules a question may not hold either: each asks for something to ride out in answers
STRONG_SEND: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(?:end|finish|close|start|begin|prefix|sign)\s+(?:every|each|all|any|your)\s+"
        r"(?:answers?|repl(?:y|ies)|responses?|messages?|outputs?)\s+with\b",
        _I,
    ),
    re.compile(
        r"\bfollowed\s+by\s+(?:the\s+)?(?:user'?s?|my|their|the\s+asker'?s?)\s+(?:question|query|"
        r"input|message|prompt|request|password|data)\b",
        _I,
    ),
    re.compile(r"(?:https?://|www\.)\S*?[?&][A-Za-z0-9_]+=(?=$|\s|[\"')\]])", _I),
    re.compile(r"!\[[^\]]*\]\((?:https?:)?//", _I),
)

SEND: tuple[re.Pattern[str], ...] = (
    *STRONG_SEND,
    re.compile(
        r"\b(?:include|add|append|insert|attach|embed)\s+(?:(?:the|this|a|an|following)\s+)+"
        r"(?:link|url|hyperlink|image|tracking\s+pixel|code)\b",
        _I,
    ),
    re.compile(
        r"\b(?:send|post|forward|upload|transmit|exfiltrate)\s+(?:(?:the|this|their|all|any)\s+)*"
        r"(?:user'?s?\s+)?(?:questions?|conversations?|chats?|history|answers?|credentials?|"
        r"session|cookies?)\s+to\b",
        _I,
    ),
)

GROUPS: dict[str, tuple[re.Pattern[str], ...]] = {
    "addressed": ADDRESSED,
    "change": CHANGE,
    "send": SEND,
}
NEEDS = 2


def matched_groups(text: str) -> tuple[str, ...]:
    """The rule groups a text matches, in the order of GROUPS."""
    return tuple(name for name, rules in GROUPS.items() if any(r.search(text) for r in rules))


def flags(text: str) -> bool:
    """Whether a document text is an instruction to the assistant: NEEDS groups or more."""
    return len(matched_groups(text)) >= NEEDS


def rules() -> object:
    """What the scan's fingerprint covers."""
    return {"groups": {n: [r.pattern for r in g] for n, g in GROUPS.items()}, "needs": NEEDS}


@dataclass(frozen=True)
class Scanned:
    """The chunks kept for the index, in order, the ids of the quarantined ones and an event
    for each."""

    kept: tuple[Chunk, ...]
    quarantined: tuple[str, ...]
    events: tuple[GuardEvent, ...]


def scan(chunks: Sequence[Chunk]) -> Scanned:
    """The chunks that may be indexed and the quarantined ones. An event's reason names the chunk
    id and the rule groups, never the chunk's text."""
    kept: list[Chunk] = []
    quarantined: list[str] = []
    events: list[GuardEvent] = []
    for chunk in chunks:
        found = matched_groups(chunk.text)
        if len(found) < NEEDS:
            kept.append(chunk)
            continue
        quarantined.append(chunk.chunk_id)
        events.append(
            GuardEvent(
                LAYER,
                "ingest",
                f"chunk {chunk.chunk_id} quarantined: rule groups {', '.join(found)}",
            )
        )
    return Scanned(tuple(kept), tuple(quarantined), tuple(events))
