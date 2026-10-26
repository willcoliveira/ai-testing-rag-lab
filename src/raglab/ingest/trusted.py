"""What the output guards may let through, read from the corpus (S7): the links the register's
documents carry, and the published team contacts of corpus/SPEC.md section 6.

- **Links** come from the chunks of the register's documents (a chunk whose status the register
  gave: approved, superseded or reference) that the instruction scan (raglab.ingest.scan) does not
  flag. A page outside the register adds none, and neither does a passage that reads as an
  instruction to the assistant, even inside a registered document: an allowlist must not be
  something an injected passage can extend.
- **Team contacts** are the rows of SPEC section 6's contact table whose purpose is a team (the
  Halvenroot IT Service Desk, the Halvenroot SOC, Mirrowfen IT Support): published contact points
  are not PII (TEST-PLAN R-19). The worked example's personal details and the attack contacts in
  the same table are never read as allowed.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from raglab.core.types import Chunk
from raglab.ingest import scan
from raglab.ingest.register import STATUSES as REGISTER_STATUSES

SPEC = "corpus/SPEC.md"
TEAMS = ("Halvenroot IT Service Desk", "Halvenroot SOC", "Mirrowfen IT Support")
# a link as the link guard reads one: a scheme or www., or a host with a path (no @ before it)
LINK = re.compile(
    r"(?<![@\w.-])(?:(?:https?|ftp)://[^\s<>\"'`]+|www\.[^\s<>\"'`]+|"
    r"(?:[a-z0-9-]+\.)+[a-z]{2,}/[^\s<>\"'`]*)",
    re.IGNORECASE,
)
_TRAILING = ".,;:!?)]}>*_"


class TrustedError(ValueError):
    pass


def normalise_link(link: str) -> str:
    """A link without its scheme, trailing punctuation and trailing slash, its host in lower
    case: `https://WWW.Example.org/a/.` and `www.example.org/a` are the same link."""
    link = link.rstrip(_TRAILING).rstrip("/")
    link = re.sub(r"^(?:https?|ftp)://", "", link, flags=re.IGNORECASE)
    host, slash, path = link.partition("/")
    return host.lower() + slash + path


def links(text: str) -> list[str]:
    """Every link in a text, normalised (normalise_link), in order."""
    return [normalise_link(m.group(0)) for m in LINK.finditer(text)]


def register_links(chunks: Iterable[Chunk]) -> frozenset[str]:
    """Every link in the register's chunks that the instruction scan does not flag, normalised."""
    return frozenset(
        link
        for chunk in chunks
        if chunk.status in REGISTER_STATUSES and not scan.flags(chunk.text)
        for link in links(chunk.text)
    )


@dataclass(frozen=True)
class TeamContacts:
    """The published team contacts: addresses in lower case, phone numbers as their digits."""

    addresses: frozenset[str]
    phones: frozenset[str]


def digits(text: str) -> str:
    return re.sub(r"\D", "", text)


def team_contacts(root: Path) -> TeamContacts:
    """SPEC section 6's team rows: each team's backticked address and phone number."""
    text = (root / SPEC).read_text(encoding="utf-8")
    if "## 6. Author rules" not in text:
        raise TrustedError(f"{SPEC} has no section 6")
    section = text.split("## 6. Author rules", 1)[1].split("\n## ", 1)[0]
    rows = dict(re.findall(r"^\s*\| ([^|]+?) \| (.+?) \| [^|]+ \|$", section, flags=re.M))
    addresses: set[str] = set()
    phones: set[str] = set()
    for team in TEAMS:
        if team not in rows:
            raise TrustedError(f"{SPEC} section 6 has no row for {team}")
        for value in re.findall(r"`([^`]+)`", rows[team]):
            if "@" in value:
                addresses.add(value.lower())
            elif len(digits(value)) >= 7:
                phones.add(digits(value))
    if len(addresses) != len(TEAMS) or len(phones) != len(TEAMS):
        raise TrustedError(f"{SPEC} section 6: each team has one address and one phone number")
    return TeamContacts(frozenset(addresses), frozenset(phones))
