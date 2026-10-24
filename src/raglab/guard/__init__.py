"""Guardrails behind the Guardrail port (raglab.core.ports), one layer each: input limits, the
tenant check and the citation validator (S3); the input injection detector, the register filter,
the link guard, the secrets and personal-details guard and the prompt-leak guard, and the citation
validator extended to the register (S7). Which layer owns which requirement is in
docs/GUARDRAILS.md. `default_guards` is the order a request meets them: the tenant first, so a
request without a tenant the caller may use is refused before anything else is looked at.

The link guard lets through the links of the register's chunks (the inventory's, those the
instruction scan does not flag) and the contacts guard SPEC section 6's team contacts under root
(raglab.ingest.trusted); the prompt-leak guard reads the current prompt's system text.
`guard_set` is what a run records of them: each layer's name and the sha256 of its rules, and one
sha256 over the list, which the staleness rule reads (S7, D3).
"""

from collections.abc import Sequence
from pathlib import Path

from raglab.core.ports import Guardrail
from raglab.core.types import Chunk, sha256_text
from raglab.generate.prompts import CURRENT as prompt
from raglab.guard.citations import CitationValidator
from raglab.guard.disclosure import SecretsGuard
from raglab.guard.injection import InjectionDetector
from raglab.guard.limits import InputLimits
from raglab.guard.links import LinkGuard
from raglab.guard.noop import rules_sha256
from raglab.guard.prompt_leak import PromptLeakGuard
from raglab.guard.register_filter import RegisterFilter
from raglab.guard.tenant import TenantGuard
from raglab.ingest import scan, trusted

type Json = dict[str, object]


def s3_guards() -> list[Guardrail]:
    """The S3 guard set, the citation validator without S7's register rule: the defences-off
    configuration of the attack runs (S7)."""
    return [TenantGuard(), InputLimits(), CitationValidator(register=False)]


def default_guards(root: Path, register_chunks: Sequence[Chunk]) -> list[Guardrail]:
    """S7a's guard set. register_chunks: the inventory's chunks, whose links the link guard lets
    through (a chunk the register did not give a status, or that the scan flags, adds none)."""
    return [
        TenantGuard(),
        InputLimits(),
        InjectionDetector(),
        RegisterFilter(),
        CitationValidator(),
        LinkGuard(trusted.register_links(register_chunks)),
        SecretsGuard(trusted.team_contacts(root)),
        PromptLeakGuard(prompt.SYSTEM),
    ]


def guard_set(guards: Sequence[Guardrail]) -> Json:
    """Each layer's name and rules sha256, in order (the instruction scan first: it runs where
    the index is built), and the sha256 of that list."""
    layers: list[Json] = [
        {"name": scan.LAYER, "sha256": rules_sha256(scan.LAYER, scan.rules())},
        *({"name": g.name, "sha256": g.fingerprint()} for g in guards),
    ]
    text = "\n".join(f"{layer['name']} {layer['sha256']}" for layer in layers)
    return {"layers": layers, "sha256": sha256_text(text)}
