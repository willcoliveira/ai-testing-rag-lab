"""Guardrails behind the Guardrail port (raglab.core.ports), one layer each: input limits, the
tenant check and the citation validator (S3). Which layer owns which requirement is in
docs/GUARDRAILS.md. `default_guards` is the order a request meets them: the tenant first, so a
request without a tenant the caller may use is refused before anything else is looked at."""

from raglab.core.ports import Guardrail
from raglab.guard.citations import CitationValidator
from raglab.guard.limits import InputLimits
from raglab.guard.tenant import TenantGuard


def default_guards() -> list[Guardrail]:
    return [TenantGuard(), InputLimits(), CitationValidator()]
