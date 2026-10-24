"""S3 AC7 (R-13, R-16, the S3 part): no other tenant's content in an answer. The app is built from
config/fake.toml as `raglab serve` builds it (the real pack, the real local embedder, the default
guards) with FakeChat, which echoes every chunk it is given and cites each one, so anything the
model sees reaches the answer. Every dev question is asked as each tenant; no tenant B canary
(corpus/answer-key.yaml) appears in a tenant A answer or its citations, and the reverse. A
positive control shows the canaries do appear in the answers of their own tenant, so the check
can fail."""

import json
from functools import cache

import pytest
import yaml
from fastapi.testclient import TestClient

from raglab.api import server
from raglab.evals import config as eval_config
from raglab.evals import golden
from tests.conftest import ROOT

pytestmark = [pytest.mark.e2e_fake, pytest.mark.security]
TENANTS = ("tenant-a", "tenant-b")
DEMO = {"Authorization": "Bearer demo"}


def canaries(tenant: str) -> list[str]:
    key = yaml.safe_load((ROOT / "corpus" / "answer-key.yaml").read_text(encoding="utf-8"))
    found = key["canaries"][tenant]
    return [
        found["tenant"],
        *found["documents"],
        *found["titles"],
        *found["contacts"],
        *found["phrases"],
    ]


@cache
def answers() -> dict[str, list[tuple[str, str]]]:
    """Every dev question asked as each tenant: (case id, answer text and citations as JSON)."""
    app = server.build_app(ROOT / "config" / "fake.toml", ROOT)
    api = TestClient(app)
    dataset = eval_config.load_generation(ROOT / "config" / "fake.toml", ROOT).dataset
    questions = golden.select(golden.load(ROOT / dataset), "retrieval", "dev")
    out: dict[str, list[tuple[str, str]]] = {t: [] for t in TENANTS}
    for tenant in TENANTS:
        for question in questions:
            response = api.post(
                "/ask", json={"tenant": tenant, "question": question.question}, headers=DEMO
            )
            assert response.status_code == 200, (question.case_id, tenant, response.text)
            body = response.json()
            assert body["status"] == "ok"
            text = body["answer"] + "\n" + json.dumps(body["citations"], ensure_ascii=False)
            out[tenant].append((question.case_id, text))
    return out


@pytest.mark.parametrize(("asker", "other"), [("tenant-a", "tenant-b"), ("tenant-b", "tenant-a")])
def test_no_canary_of_the_other_tenant_in_any_answer(asker, other):
    found = [
        (case_id, canary)
        for case_id, text in answers()[asker]
        for canary in canaries(other)
        if canary in text
    ]
    assert found == [], f"{other} content in {asker} answers: {found}"
    assert len(answers()[asker]) == 22


@pytest.mark.parametrize("tenant", TENANTS)
def test_positive_control_the_canaries_of_the_askers_own_tenant_do_appear(tenant):
    own = canaries(tenant)
    hits = [case_id for case_id, text in answers()[tenant] if any(c in text for c in own)]
    assert hits, f"no {tenant} canary in any {tenant} answer: the check could not fail"
