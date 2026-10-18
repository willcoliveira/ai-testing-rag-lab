"""S3: the abstention probes (datasets/probes.s3.jsonl) are written from the answer key: F-32 (an
omission) for each tenant and F-40 (a tenant B abstention). Each one's must_not_appear list is
derived, not chosen: the answer key's phrases for its feature, less any that the probe's own
question or the feature's reference answer contains (an honest abstention may repeat those), plus,
for a tenant-isolation feature, the other tenant's canaries (R-13, R-16): its name, document ids,
titles and phrases. The contacts and the exception ids (EX-...) are left out: they are planted
fakes the privacy check allows under corpus/ only, and a run record carries this list, so it would
fail publish's privacy scan. tests/e2e/test_e2e_fake.py checks every canary, contacts included."""

import re
from typing import Any

import pytest
import yaml

from raglab.evals.generation import load_probes
from tests.conftest import ROOT

pytestmark = pytest.mark.unit
KEY = yaml.safe_load((ROOT / "corpus" / "answer-key.yaml").read_text(encoding="utf-8"))
FEATURES = {f["id"]: f for f in KEY["features"]}


EXCEPTION_ID = re.compile(r"\b[A-Z]{2,6}-\d{3,5}\b")


def other_canaries(tenant: str) -> list[str]:
    other = KEY["canaries"]["tenant-a" if tenant == "tenant-b" else "tenant-b"]
    found = [other["tenant"], *other["documents"], *other["titles"], *other["phrases"]]
    return [c for c in found if not EXCEPTION_ID.search(c)]


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
        assert feature["expected"] == "abstain" == probe.extra["expected"]
        assert probe.tenant in feature["tenants"]
        assert probe.split == "dev"


def test_each_must_not_appear_list_is_derived_from_the_answer_key():
    for probe in load_probes(ROOT / "datasets" / "probes.s3.jsonl"):
        extra: Any = probe.extra
        feature = FEATURES[extra["feature_ids"][0]]
        said = (probe.question + " " + feature["reference_answer"]).lower()
        expected = [p for p in feature["must_not_appear"]["phrases"] if p.lower() not in said]
        if feature["kind"] == "tenant-isolation-abstain":
            expected += other_canaries(probe.tenant)
        assert probe.extra["must_not_appear"] == expected, probe.case_id
        assert probe.extra["must_not_appear"], probe.case_id
