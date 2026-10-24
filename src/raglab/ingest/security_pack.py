"""The security pack, datasets/security/ (S7, D2): the must-block and must-not-block cases of
every guard layer and the attack cases, in how-to 07's YAML template (`id`, `kind`, `input`,
`expected`, `layer`, `ratified_by`, `origin`; this pack adds `why`, one line for the reviewer).

It is deliberate test material, outside the corpus and the golden set: it is never ingested, and
check-dataset never reads it. Planted values are never written in it. A case refers to them, and
`resolve` reads them when a suite runs:

- `{ref:F-xx:n}`: string n of feature F-xx's answer_must_not_contain (corpus/answer-key.yaml);
- `{contact:<team>:address|phone|phone-local}`: a team contact of corpus/SPEC.md section 6
  (phone-local: the number without its country code, as (202) 555-0100);
- `{prompt:system}`: the current prompt's system text.

`problems` is the pack's schema check: every field of the template, a known kind and layer, an
expected decision that matches the kind, a unique id with its layer's prefix, a `ratified_by` that
is `pending` or names who ratified it and when, an origin, every reference resolving, no
answer_must_not_contain string written out, and attack cases naming known features.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import yaml

from raglab.ingest import answer_key, trusted

PACK = "datasets/security"
KINDS = ("must_block", "must_not_block", "injection")
# layer -> case id prefix
LAYERS = {
    "tenant": "TEN",
    "input-limits": "LIM",
    "injection": "INJ",
    "register": "REG",
    "instruction-scan": "SCN",
    "citations": "CIT",
    "links": "LNK",
    "secrets-pii": "SPI",
    "prompt-leak": "PLK",
    "attack": "ATK",
}
EXPECTED = {"must_block": "block", "must_not_block": "pass", "injection": "safe"}
STAGES = ("ingest", "input", "retrieved", "output")
# who ratified a case and when, or pending until the maintainer has
RATIFIED = re.compile(r"^(?:pending|maintainer \d{4}-\d{2}-\d{2})$")
REFERENCE = re.compile(r"\{(ref|contact|prompt):([^{}]+)\}")
ATTACKS = (
    "planted-instruction",
    "poisoned-duplicate",
    "fake-update",
    "planted-secret",
    "two-tenants",
    "prompt-extraction",
)


class PackError(ValueError):
    pass


@dataclass(frozen=True)
class Case:
    id: str
    kind: str
    layer: str
    input: dict[str, object]
    expected: str
    ratified_by: str
    origin: str
    why: str
    file: str

    @property
    def handwritten(self) -> bool:
        return self.origin.startswith("handwritten")


def _mapping(value: object, where: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise PackError(f"{where}: not a mapping")
    return {str(k): v for k, v in cast(dict[object, object], value).items()}


def load(root: Path) -> list[Case]:
    """Every case of every pack file, in file and case order. A file that is not a mapping with
    a layer and a list of cases, or a case that is not a mapping, stops the load."""
    cases: list[Case] = []
    for path in sorted((root / PACK).glob("*.yaml")):
        where = path.relative_to(root).as_posix()
        data = _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), where)
        layer, items = data.get("layer"), data.get("cases")
        if not isinstance(layer, str) or not isinstance(items, list):
            raise PackError(f"{where}: needs a layer and a list of cases")
        for n, raw in enumerate(cast(list[object], items), start=1):
            item = _mapping(raw, f"{where} case {n}")
            raw_input: object = item.get("input")
            case_input = _mapping(raw_input, f"{where} case {n} input") if raw_input else {}
            cases.append(
                Case(
                    id=str(item.get("id", "")),
                    kind=str(item.get("kind", "")),
                    layer=layer,
                    input=case_input,
                    expected=str(item.get("expected", "")),
                    ratified_by=str(item.get("ratified_by") or ""),
                    origin=str(item.get("origin") or ""),
                    why=str(item.get("why") or ""),
                    file=where,
                )
            )
    return cases


@dataclass(frozen=True)
class Sources:
    """What references resolve against: the answer key's banned strings, SPEC section 6's team
    rows, and the current system prompt."""

    banned: dict[str, list[str]]
    contacts: dict[str, dict[str, str]]
    system: str


def sources(root: Path, system: str) -> Sources:
    text = (root / trusted.SPEC).read_text(encoding="utf-8")
    section = text.split("## 6. Author rules", 1)[1].split("\n## ", 1)[0]
    rows = dict(re.findall(r"^\s*\| ([^|]+?) \| (.+?) \| [^|]+ \|$", section, flags=re.M))
    contacts: dict[str, dict[str, str]] = {}
    for team in trusted.TEAMS:
        values = re.findall(r"`([^`]+)`", rows.get(team, ""))
        address = next((v for v in values if "@" in v), "")
        phone = next((v for v in values if "@" not in v), "")
        digits = trusted.digits(phone)[-10:]
        local = f"({digits[:3]}) {digits[3:6]}-{digits[6:]}" if len(digits) == 10 else ""
        contacts[team] = {"address": address, "phone": phone, "phone-local": local}
    return Sources(answer_key.must_not_contain(root), contacts, system)


def resolve(text: str, found: Sources) -> str:
    """text with every reference replaced by its value; PackError for one that does not
    resolve."""

    def value(match: re.Match[str]) -> str:
        kind, body = match.group(1), match.group(2)
        if kind == "prompt":
            if body != "system":
                raise PackError(f"unknown prompt reference {match.group(0)}")
            return found.system
        if kind == "ref":
            feature, _, index = body.rpartition(":")
            strings = found.banned.get(feature)
            if not strings or not index.isdigit() or int(index) >= len(strings):
                raise PackError(f"{match.group(0)} names no answer_must_not_contain string")
            return strings[int(index)]
        team, _, field = body.rpartition(":")
        got = found.contacts.get(team, {}).get(field, "")
        if not got:
            raise PackError(f"{match.group(0)} names no team contact of SPEC section 6")
        return got

    return REFERENCE.sub(value, text)


def resolved_input(case: Case, found: Sources) -> dict[str, object]:
    """The case's input with every string resolved."""
    out: dict[str, object] = {}
    for key, raw in case.input.items():
        out[key] = resolve(raw, found) if isinstance(raw, str) else raw
    return out


def _strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [s for item in cast(list[object], value) for s in _strings(item)]
    if isinstance(value, dict):
        return [s for item in cast(dict[object, object], value).values() for s in _strings(item)]
    return []


def problems(root: Path, cases: list[Case], found: Sources) -> list[str]:
    """Every way the pack breaks its template, each naming the case."""
    out: list[str] = []
    banned = {s.casefold() for strings in found.banned.values() for s in strings}
    seen: set[str] = set()
    for case in cases:
        where = f"{case.file} {case.id or '?'}"
        if case.layer not in LAYERS:
            out.append(f"{where}: layer {case.layer!r} is not one of {sorted(LAYERS)}")
            continue
        if case.kind not in KINDS:
            out.append(f"{where}: kind {case.kind!r} is not one of {list(KINDS)}")
        elif case.expected != EXPECTED[case.kind]:
            out.append(f"{where}: a {case.kind} case expects {EXPECTED[case.kind]!r}")
        if (case.kind == "injection") != (case.layer == "attack"):
            out.append(f"{where}: injection cases are the attack cases, and only they")
        if not re.fullmatch(rf"{LAYERS[case.layer]}-[A-Z0-9]+(?:-\d+)?", case.id):
            out.append(f"{where}: an id of layer {case.layer} starts with {LAYERS[case.layer]}-")
        if case.id in seen:
            out.append(f"{where}: id used twice")
        seen.add(case.id)
        if not RATIFIED.match(case.ratified_by):
            out.append(f"{where}: ratified_by is empty or not 'maintainer <date>'")
        if not case.origin:
            out.append(f"{where}: origin is empty")
        if not case.why:
            out.append(f"{where}: why is empty")
        if not case.input:
            out.append(f"{where}: input is empty")
            continue
        if case.layer != "attack" and case.input.get("stage") not in STAGES:
            out.append(f"{where}: input stage is not one of {list(STAGES)}")
        for text in _strings(case.input):
            if any(b in text.casefold() for b in banned):
                out.append(f"{where}: an answer_must_not_contain string is written out")
            try:
                resolve(text, found)
            except PackError as error:
                out.append(f"{where}: {error}")
        if case.layer == "attack":
            out.extend(_attack_problems(where, case, found))
    return out


def _attack_problems(where: str, case: Case, found: Sources) -> list[str]:
    out: list[str] = []
    if case.input.get("attack") not in ATTACKS:
        out.append(f"{where}: attack is not one of {list(ATTACKS)}")
    if case.input.get("tenant") not in ("tenant-a", "tenant-b"):
        out.append(f"{where}: an attack case asks as tenant-a or tenant-b")
    features = case.input.get("features")
    if not isinstance(features, list):
        out.append(f"{where}: features is a list of answer-key features")
        return out
    for feature in cast(list[object], features):
        if feature not in found.banned:
            out.append(f"{where}: {feature} is not a feature with answer_must_not_contain")
    return out
