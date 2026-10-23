"""answer-v2's AV4, the judge's half: the measure and the judge are frozen while answer-v1 and
answer-v2 are compared (docs/plans/2026-10-21-answer-v2.md). Two judged records compare only under
one judge, so the judge a new judged run would use today (judge-v2's fingerprint, docs/CRITERIA.md,
the canary set, `config/judge-local.toml` and the model it pins) must be the one that judged
answer-v1's consistency baseline, `20261021T081852Z-judge-local-dev-5aa0ec5`: its manifest names
each of them, and publish would refuse a judged run made under another CRITERIA.md or canary set
as stale.

answer-v2's judged record, `20261023T090413Z-judge-local-dev-c14acb0` (the first of answer-v2's
five runs, judged in that pull request), is held to the same judge, so the two compare.

The behaviour checks and the oracle are held by the committed-runs test
(tests/retrieval/test_publish.py), because the validator recomputes every published record's
checks from its fields; the gate's code and `raglab compare` are held by the ledger's
`git diff origin/main` over their paths.
"""

import json

import pytest

from raglab.evals import judged_record, publish, record
from raglab.evals.config import canonical_sha256, load_judge
from raglab.judge.llm import LLMJudge
from raglab.judge.prompts import judge_v2
from tests.conftest import ROOT

pytestmark = pytest.mark.unit
# answer-v1's judged consistency baseline (S5), and answer-v2's judged record compared with it
A_JUDGED = "20261021T081852Z-judge-local-dev-5aa0ec5"
B_JUDGED = "20261023T090413Z-judge-local-dev-c14acb0"
JUDGE_CONFIG = ROOT / "config" / "judge-local.toml"


def judged_manifest(run_id: str) -> dict:
    return json.loads((ROOT / publish.PUBLISHED / run_id / record.MANIFEST).read_text("utf-8"))


@pytest.mark.parametrize("run_id", [A_JUDGED, B_JUDGED])
def test_todays_judge_is_the_one_that_judged_the_compared_records(run_id):
    manifest = judged_manifest(run_id)
    config = load_judge(JUDGE_CONFIG, ROOT)
    judge = LLMJudge(None)  # type: ignore[arg-type]
    assert manifest["judge_prompt"] == {"version": judge.version, "sha256": judge.fingerprint()}
    assert judge.version == judge_v2.VERSION == judged_record.CURRENT
    assert manifest["config"] == {
        "name": config.name,
        "path": config.path,
        "file_sha256": config.file_sha256,
        "sha256": canonical_sha256(config.resolved()),
    }
    assert (manifest["judge"]["model"], manifest["judge"]["digest"]) == (
        config.judge.model,
        config.judge.digest,
    )
    for part, path in (
        ("criteria", config.judging.criteria),
        ("canaries", config.judging.canaries),
    ):
        assert manifest[part]["path"] == path
        assert manifest[part]["sha256"] == record.sha256_bytes((ROOT / path).read_bytes()), path
    assert publish.judged_problems(manifest, ROOT) == []
