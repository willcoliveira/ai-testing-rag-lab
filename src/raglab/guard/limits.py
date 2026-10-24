"""Input limits (S3): the question must be non-empty, at most 500 characters, and free of control
and invisible characters. Line breaks and tabs are allowed (a question typed in a text box has
them); every other character in the Unicode categories Cc (control), Cf (format: zero-width and
bidirectional overrides, which can hide text from a reader), Cs (surrogates), Co (private use) and
Cn (unassigned) is refused. Characters are code points, counted without normalisation.

Lab practice: a production service would also cap the request body and rate-limit callers (S10);
here the API caps the body size and this guard caps the question.
"""

import unicodedata

from raglab.core.types import GuardEvent
from raglab.guard.noop import NoopGuardrail

MAX_CHARS = 500
ALLOWED_CONTROLS = frozenset({"\n", "\t"})
REFUSED_CATEGORIES = frozenset({"Cc", "Cf", "Cs", "Co", "Cn"})


class InputLimits(NoopGuardrail):
    def __init__(self, max_chars: int = MAX_CHARS) -> None:
        if max_chars < 1:
            raise ValueError(f"max_chars must be at least 1, not {max_chars}")
        self.max_chars = max_chars

    @property
    def name(self) -> str:
        return "input-limits"

    def rules(self) -> object:
        return {
            "max_chars": self.max_chars,
            "allowed_controls": sorted(ALLOWED_CONTROLS),
            "refused_categories": sorted(REFUSED_CATEGORIES),
        }

    def _refuse(self, reason: str) -> GuardEvent:
        return GuardEvent(self.name, "input", reason)

    def check_input(
        self, question: str, tenant: str | None, caller_tenants: frozenset[str] | None
    ) -> GuardEvent | None:
        if not question.strip():
            return self._refuse("the question is empty")
        if len(question) > self.max_chars:
            return self._refuse(
                f"the question has {len(question)} characters; the limit is {self.max_chars}"
            )
        for char in question:
            if char in ALLOWED_CONTROLS:
                continue
            category = unicodedata.category(char)
            if category in REFUSED_CATEGORIES:
                return self._refuse(
                    f"the question contains character U+{ord(char):04X} (category {category})"
                )
        return None
