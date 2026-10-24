"""The input injection detector (S7, R-17 direct, R-20; OWASP LLM01 and LLM08 in
docs/THREAT-MODEL.md). It refuses a question before retrieval (status refused, as the input limits
do; the API answers 400) when it holds:

- **an instruction to the assistant**: a request to drop its rules ("ignore all previous
  instructions", "new instructions:", "pretend you are ..."), or to put something in every answer
  ("end every answer with ...", "followed by the user's question", a link waiting for a value):
  the strong rules of the instruction scan's change and send groups (raglab.ingest.scan);
- **text dressed as a system or developer message**: a role line ("System: ..."), a control token
  (`<|im_start|>`, `[INST]`, `<<SYS>>`), a frame tag of the prompt (`<chunk`, `</question>`), a
  role field in JSON;
- **a request to reveal the prompt or the configuration**: "system prompt", "your instructions",
  "the text above", "what were you told", "your configuration".

Each rule asks for the shape of an attack, not a word: "ignore an MFA prompt you did not start",
"the MFA system's messages" and "the instructions for a lost laptop" are policy questions and
pass. The event names the rule group, never the question's words.

Lab practice: rules, written from the requirements and checked against the golden set's dev
questions (never the test split) and the near-miss cases of datasets/security/. Production would
add a classifier (S7b compares one); paraphrase, encodings and other languages pass these rules.
"""

import re

from raglab.core.types import GuardEvent
from raglab.guard.noop import NoopGuardrail
from raglab.ingest.scan import STRONG_CHANGE, STRONG_SEND

_I = re.IGNORECASE | re.MULTILINE

INSTRUCTION: tuple[re.Pattern[str], ...] = (*STRONG_CHANGE, *STRONG_SEND)

DRESSED: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\s*(?:system|assistant)\s*(?:message|prompt)?\s*:", _I),
    re.compile(r"\bdeveloper\s+(?:message|prompt|instructions?)\s*:", _I),
    re.compile(r"<\|[a-z_]+\|>|<<\s*/?sys\s*>>|\[/?inst\]|\[/?system\]|\[/?developer\]", _I),
    re.compile(r"</?(?:system|chunk|question|instructions?)\b", _I),
    re.compile(r"^\s*#{1,6}\s*(?:system|developer|instructions?)\b", _I),
    re.compile(r"\"role\"\s*:\s*\"(?:system|developer|assistant)\"", _I),
    re.compile(r"\b(?:begin|end)\s+(?:of\s+)?(?:system|developer)\s+(?:prompt|message)\b", _I),
)

REVEAL: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bsystem[\s-]?prompts?\b", _I),
    re.compile(
        r"\b(?:reveal|show|print|repeat|display|output|dump|leak|recite|disclose|share|tell\s+me|"
        r"give\s+me|list|copy|paste|write\s+out|spell\s+out|what\s+(?:is|are|were))\s+"
        r"(?:\w+\s+){0,3}?(?:your|the\s+assistant'?s|the\s+model'?s)\s+(?:(?:initial|original|"
        r"hidden|full|exact|secret|internal|underlying|first|whole|complete)\s+)?(?:prompts?|"
        r"instructions?|system\s+messages?|configuration|config|settings)\b(?!\s+(?:for|on|about|to)\b)",
        _I,
    ),
    re.compile(
        r"\b(?:instructions?|rules?|prompts?)\s+(?:were|have|had)\s+you\s+(?:been\s+)?(?:given|told|"
        r"provided|programmed)\b",
        _I,
    ),
    re.compile(
        r"\bwhat\s+(?:were|are|have)\s+you\s+(?:been\s+)?(?:told|instructed|programmed|configured|"
        r"prompted)\b",
        _I,
    ),
    re.compile(
        r"\b(?:repeat|print|output|show|reveal|display|recite|copy)\s+(?:(?:the|all|everything|"
        r"any)\s+)*(?:(?:text|words|lines|content|messages?|instructions)\s+)?(?:above|before\s+"
        r"(?:this|my)|preceding|so\s+far|at\s+the\s+(?:start|beginning|top))\b",
        _I,
    ),
    re.compile(
        r"\byour\s+(?:api\s+keys?|environment\s+variables?|env\s+vars?|temperature|seed|"
        r"configuration\s+file|config\s+file)\b",
        _I,
    ),
)

GROUPS: dict[str, tuple[re.Pattern[str], ...]] = {
    "instruction-to-the-assistant": INSTRUCTION,
    "dressed-as-a-system-message": DRESSED,
    "reveal-the-prompt-or-configuration": REVEAL,
}


class InjectionDetector(NoopGuardrail):
    @property
    def name(self) -> str:
        return "injection"

    def rules(self) -> object:
        return {name: [r.pattern for r in group] for name, group in GROUPS.items()}

    def check_input(
        self, question: str, tenant: str | None, caller_tenants: frozenset[str] | None
    ) -> GuardEvent | None:
        for group, patterns in GROUPS.items():
            if any(p.search(question) for p in patterns):
                return GuardEvent(self.name, "input", f"rule {group}: the question is refused")
        return None
