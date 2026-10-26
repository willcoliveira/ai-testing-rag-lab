"""The secrets and personal-details guard (S7, R-19, arrow R8 of docs/TEST-PLAN.md; OWASP LLM02
in docs/THREAT-MODEL.md): an answer that holds a credential-shaped token, or an email address or
phone number outside the published team contacts, is withheld (status blocked, label abstain, no
text). Withhold, not mask: masking is one of S7b's comparisons.

- **Credentials**: a token of the lab's planted shape (`FAKE-` and upper-case groups, the
  convention of corpus/SPEC.md section 6), a private key's header, a token of a provider's known
  shape (an access key id, a personal access token, a chat or cloud API key, a JSON web token), a
  password, key or token followed by a value of twelve or more letters and digits, and any token
  of twenty or more characters that mixes upper and lower case letters and digits.
- **Personal details**: every email address except the team contacts of SPEC section 6, and
  every phone number (a country code, an area code or three groups of digits) whose digits are
  not a team contact's.

The team contacts pass (F-46 and Mirrowfen IT Support's, must-not-block), and so do the values a
policy states: lengths, durations, dates, versions, section and exception ids. The event names
the rule, never the value.

Lab practice: rules, and a list of three team contacts. Production would use a secrets detector
and a PII service (S7b compares detect-secrets and Presidio) and the directory's published
contacts.
"""

import re
from collections.abc import Sequence

from raglab.core.types import Answer, GuardEvent, ScoredChunk
from raglab.guard.noop import NoopGuardrail
from raglab.ingest.trusted import TeamContacts, digits

CREDENTIALS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bFAKE-[A-Z0-9]+(?:-[A-Z0-9]+)+\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY(?: BLOCK)?-----"),
    re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
    re.compile(r"\bsk_(?:live|test)_[0-9A-Za-z]{16,}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),
    re.compile(
        r"\b(?:password|passwd|passphrase|pwd|secret|api[ _-]?key|access[ _-]?key|secret[ _-]?key|"
        r"client[ _-]?secret|auth[ _-]?token|token)\s*(?:is|=|:)\s*[\"'`]?"
        r"(?=[A-Za-z0-9_\-+/=.]{12,})(?=[^\s\"'`]*\d)(?=[^\s\"'`]*[A-Za-z])",
        re.IGNORECASE,
    ),
    re.compile(r"(?<![\w-])(?=[A-Za-z0-9_-]{20,})(?=\S*\d)(?=\S*[a-z])(?=\S*[A-Z])[A-Za-z0-9_-]+"),
)
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE = re.compile(
    r"(?<![\w+-])(?:\+\d{1,3}[ .-]?)?(?:\(\d{2,4}\)[ .-]?|\d{2,4}[ .-])\d{3,4}[ .-]\d{3,4}(?![\w-])"
)


class SecretsGuard(NoopGuardrail):
    def __init__(self, contacts: TeamContacts) -> None:
        self.contacts = contacts

    @property
    def name(self) -> str:
        return "secrets-pii"

    def rules(self) -> object:
        return {
            "credentials": [p.pattern for p in CREDENTIALS],
            "email": EMAIL.pattern,
            "phone": PHONE.pattern,
            "team_addresses": sorted(self.contacts.addresses),
            "team_phones": sorted(self.contacts.phones),
        }

    def team_phone(self, number: str) -> bool:
        found = digits(number)
        return any(
            p == found or (len(found) >= 10 and p.endswith(found)) for p in self.contacts.phones
        )

    def finding(self, text: str) -> str | None:
        """The rule a text breaks, or None."""
        if any(p.search(text) for p in CREDENTIALS):
            return "credential: the answer holds a credential-shaped token"
        if any(m.group(0).lower() not in self.contacts.addresses for m in EMAIL.finditer(text)):
            return "personal-email: the answer holds an address outside the team contacts"
        if any(not self.team_phone(m.group(0)) for m in PHONE.finditer(text)):
            return "personal-phone: the answer holds a phone number outside the team contacts"
        return None

    def check_output(self, answer: Answer, retrieved: Sequence[ScoredChunk]) -> GuardEvent | None:
        for text in (answer.text, answer.conflict.note if answer.conflict else ""):
            if found := self.finding(text):
                return GuardEvent(self.name, "output", f"rule {found}")
        return None
