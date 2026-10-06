"""AC3: the tenant filter fails closed. A query without a known tenant is refused by every
retriever, and no tenant B chunk is ever returned for tenant A (or the reverse), even when the
query is a tenant B chunk's own text. Checked on small fixtures and on the whole pack."""

import pytest

from raglab.core.types import ScoredChunk, TenantError, check_visible, visible_tenants
from tests.ingestion_support import default_inventory
from tests.retrieval_support import CHUNKS, make_chunk, retrievers

pytestmark = pytest.mark.retrieval
KINDS = ["dense", "bm25", "hybrid"]
OTHER = {"tenant-a": "tenant-b", "tenant-b": "tenant-a"}


@pytest.mark.unit
@pytest.mark.parametrize("tenant", [None, "", "shared", "tenant-c", "TENANT-A", 1])
def test_a_request_without_a_known_tenant_is_refused(tenant):
    with pytest.raises(TenantError, match="needs the tenant of the request"):
        visible_tenants(tenant)


@pytest.mark.unit
@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("tenant", [None, "", "shared", "tenant-c"])
def test_every_retriever_refuses_a_request_without_a_known_tenant(kind, tenant):
    retriever = retrievers(CHUNKS)[kind]
    with pytest.raises(TenantError):
        retriever.retrieve("password length", tenant, 5)


@pytest.mark.unit
@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("tenant", ["tenant-a", "tenant-b"])
def test_no_chunk_of_the_other_tenant_is_returned_even_for_its_own_text(kind, tenant):
    retriever = retrievers(CHUNKS)[kind]
    for chunk in CHUNKS:
        results = retriever.retrieve(chunk.text, tenant, len(CHUNKS))
        tenants = {r.chunk.tenant for r in results}
        assert OTHER[tenant] not in tenants, (kind, chunk.chunk_id, tenants)
        assert tenants <= {tenant, "shared"}
    # and the tenant's own and the shared chunks are all reachable
    found = {r.chunk.chunk_id for r in retriever.retrieve("password MFA", tenant, 10)}
    assert found == {c.chunk_id for c in CHUNKS if c.tenant in {tenant, "shared"}}


@pytest.mark.unit
def test_a_result_of_another_tenant_is_caught_on_the_way_out():
    leaked = [ScoredChunk(CHUNKS[2], 1.0)]  # B-1
    with pytest.raises(TenantError, match=r"B-1@1\.0/1/1 of tenant-b was retrieved for tenant-a"):
        check_visible(leaked, "tenant-a")
    assert check_visible([ScoredChunk(CHUNKS[4], 1.0)], "tenant-a")  # shared is visible


@pytest.mark.unit
def test_a_tenant_with_no_visible_chunk_gets_nothing():
    only_b = [make_chunk("B-1@1.0/1/1", "tenant-b", "Passwords are 12 characters.")]
    for kind, retriever in retrievers(only_b).items():
        assert retriever.retrieve("Passwords are 12 characters.", "tenant-a", 5) == [], kind


@pytest.mark.ocr
@pytest.mark.parametrize("kind", KINDS)
def test_no_cross_tenant_chunk_on_the_whole_pack(kind):
    """Every tenant B chunk's text, asked as tenant A (and the reverse), at k = 20."""
    chunks = list(default_inventory().chunks)
    retriever = retrievers(chunks)[kind]
    for chunk in chunks:
        if chunk.tenant == "shared":
            continue
        asker = OTHER[chunk.tenant]
        results = retriever.retrieve(chunk.text, asker, 20)
        assert results, chunk.chunk_id
        leaked = [r.chunk.chunk_id for r in results if r.chunk.tenant == chunk.tenant]
        assert leaked == [], f"{kind}: {chunk.chunk_id} asked as {asker} returned {leaked}"
