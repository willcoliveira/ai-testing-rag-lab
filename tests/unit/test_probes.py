"""S3: the abstention probes (datasets/probes.s3.jsonl) are written from the answer key: F-32 (an
omission) for each tenant and F-40 (a tenant B abstention). Each expects abstain; a
tenant-isolation probe names the other tenant as canaries_of, so the abstention oracle checks
that none of that tenant's canaries (corpus/answer-key.yaml) appears in the answer (R-16). The
answer key's must_not_appear lists are a guarantee about the documents (the phrases are absent
from the pack), not a ban on words in an answer: they are not used here (plan correction,
2026-10-18, S3 ledger)."""

from typing import Any

import pytest
import yaml

from raglab.evals.generation import load_probes
from tests.conftest import ROOT

pytestmark = pytest.mark.unit
KEY = yaml.safe_load((ROOT / "corpus" / "answer-key.yaml").read_text(encoding="utf-8"))
FEATURES = {f["id"]: f for f in KEY["features"]}


def test_the_probes_are_f32_for_each_tenant_and_f40_for_tenant_b():
    probes = load_probes(ROOT / "datasets" / "probes.s3.jsonl")
    assert [(p.case_id, p.tenant, p.extra["feature_ids"]) for p in probes] == [
        ("P-01", "tenant-a", ["F-32"]),
        ("P-02", "tenant-b", ["F-32"]),
        ("P-03", "tenant-b", ["F-40"]),
    ]
    for probe in probes:
        extra: Any = probe.extra
        [feature_id] = extra["feature_ids"]
        feature = FEATURES[feature_id]
        assert feature["expected"] == "abstain" == extra["expected"]
        assert probe.tenant in feature["tenants"]
        assert probe.split == "dev"
        assert "must_not_appear" not in extra


def test_a_tenant_isolation_probe_names_the_other_tenants_canaries():
    for probe in load_probes(ROOT / "datasets" / "probes.s3.jsonl"):
        extra: Any = probe.extra
        feature = FEATURES[extra["feature_ids"][0]]
        other = "tenant-a" if probe.tenant == "tenant-b" else "tenant-b"
        expected = other if feature["kind"] == "tenant-isolation-abstain" else None
        assert extra["canaries_of"] == expected, probe.case_id
