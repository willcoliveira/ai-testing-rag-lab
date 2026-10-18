"""The tenant guard (R-21, and the S3 part of R-13 and R-16).

At input it fails closed: a request with no tenant, an empty one, "shared" or an unknown one is
refused (raglab.core.types.visible_tenants), and so is a tenant the caller may not use. The
caller's tenants come from the API's token map (config [api.tokens]); a local run (CLI, eval) has
no caller and passes None. After retrieval it checks every chunk once more against the request's
tenant (the store and the retrievers already filter before ranking): a chunk of another tenant
blocks the answer before any model sees it.

Lab practice: the API maps a demo token to tenants from config. Production takes the tenant from
the identity provider's claims and never from the request body.
"""

from collections.abc import Sequence

from raglab.core.types import GuardEvent, ScoredChunk, TenantError, visible_tenants
from raglab.guard.noop import NoopGuardrail


class TenantGuard(NoopGuardrail):
    @property
    def name(self) -> str:
        return "tenant"

    def check_input(
        self, question: str, tenant: str | None, caller_tenants: frozenset[str] | None
    ) -> GuardEvent | None:
        try:
            visible_tenants(tenant)
        except TenantError as error:
            return GuardEvent(self.name, "input", str(error))
        if caller_tenants is not None and tenant not in caller_tenants:
            return GuardEvent(self.name, "input", f"the caller may not use {tenant}")
        return None

    def check_retrieved(self, tenant: str, retrieved: Sequence[ScoredChunk]) -> GuardEvent | None:
        visible = visible_tenants(tenant)
        for result in retrieved:
            if result.chunk.tenant not in visible:
                return GuardEvent(
                    self.name,
                    "retrieved",
                    f"chunk {result.chunk.chunk_id} of {result.chunk.tenant} was retrieved for "
                    f"{tenant}",
                )
        return None
