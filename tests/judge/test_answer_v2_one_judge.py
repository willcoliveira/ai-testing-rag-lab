"""answer-v2's AV4, the judge's half: the measure and the judge are frozen while answer-v1 and
answer-v2 are compared (docs/plans/2026-10-21-answer-v2.md). Two judged records compare only under
one judge, so the judge a new judged run would use today (judge-v2's fingerprint, docs/CRITERIA.md,
the canary set, `config/judge-local.toml` and the model it pins) must be the one that judged
answer-v1's consistency baseline, `20261021T081852Z-judge-local-dev-5aa0ec5`: its manifest names
each of them, and publish would refuse a judged run made under another CRITERIA.md or canary set
as stale.

answer-v2's judged record, `20261023T090413Z-judge-local-dev-c14acb0` (the first of answer-v2's
five runs, judged in that pull request), is held to the same judge, so the two compare.

S6 (docs/plans/2026-10-23-s6-judge-calibration.md, JC2): the same judge, the cap excepted. The
judged run's wall-clock cap (`judging.run_timeout_s`) is how long a run may take, not how it
judges, and S6 raises it by its plan's rule for the judged baseline on golden set v2 (about 1,450
calls, where the records here made about 600). So the test holds the same judge, not the same
file: today's config with only the cap set back to the one a record was made under must hash to
that record's canonical config sha256. The file's sha256 is compared only for a record made under
today's cap, because the cap's comment changes the file. The committed manifests are the oracle: a
cap restored with the wrong type (7200, an int, where the loader gives 7200.0) hashes to another
value, a red test rather than a silent pass. Everything else is held as before: the prompt's
version and fingerprint, CRITERIA.md, the canary set, the model and its digest, and no publish
problem.

The behaviour checks and the oracle are held by the committed-runs test
(tests/retrieval/test_publish.py), because the validator recomputes every published record's
checks from its fields; the gate's code and `raglab compare` are held by the ledger's
`git diff origin/main` over their paths.
"""

import json
from dataclasses import replace
from typing import cast

import pytest

from raglab.evals import judged_record, publish, record
from raglab.evals.config import JudgeConfig, canonical_sha256, load_judge
from raglab.judge.llm import LLMJudge
from raglab.judge.prompts import judge_v2
from tests.conftest import ROOT

pytestmark = pytest.mark.unit
# answer-v1's judged consistency baseline (S5), and answer-v2's judged record compared with it
A_JUDGED = "20261021T081852Z-judge-local-dev-5aa0ec5"
B_JUDGED = "20261023T090413Z-judge-local-dev-c14acb0"
# S6's judged baseline on golden set v2 (S4b's run 1, judged on 2026-10-24 under today's cap)
V2_JUDGED = "20261024T210231Z-judge-local-dev-c8da78b"
JUDGE_CONFIG = ROOT / "config" / "judge-local.toml"
# Each record held to today's judge, with the cap it was made under: the S5 cap (set from the
# short judge session of 2026-10-20) for the two v1.1 records; today's, S6's, for the judged
# baseline on golden set v2, which is then matched exactly, its file sha256 included.
RECORDS: dict[str, float] = {A_JUDGED: 7200.0, B_JUDGED: 7200.0, V2_JUDGED: 12600.0}


def judged_manifest(run_id: str) -> dict:
    return json.loads((ROOT / publish.PUBLISHED / run_id / record.MANIFEST).read_text("utf-8"))


def with_cap(config: JudgeConfig, cap: float) -> JudgeConfig:
    """Today's judge config with only its judged run's wall-clock cap replaced."""
    return replace(config, judging=replace(config.judging, run_timeout_s=cap))


@pytest.mark.parametrize("run_id", list(RECORDS))
def test_todays_judge_is_the_one_that_judged_the_compared_records(run_id):
    manifest = judged_manifest(run_id)
    config = load_judge(JUDGE_CONFIG, ROOT)
    judge = LLMJudge(None)  # type: ignore[arg-type]
    assert manifest["judge_prompt"] == {"version": judge.version, "sha256": judge.fingerprint()}
    assert judge.version == judge_v2.VERSION == judged_record.CURRENT
    cap = RECORDS[run_id]
    held = manifest["config"]
    assert (held["name"], held["path"]) == (config.name, config.path)
    # the same judge, the cap excepted: only judging.run_timeout_s is set back to the record's
    assert held["sha256"] == canonical_sha256(with_cap(config, cap).resolved()), (
        f"{run_id}: today's judge config differs from the record's in more than its cap"
    )
    if cap == config.judging.run_timeout_s:  # made under today's cap: the same file, too
        assert held["file_sha256"] == config.file_sha256
        assert held["sha256"] == canonical_sha256(config.resolved())
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


def test_the_cap_is_the_only_exception():
    """with_cap replaces the cap and nothing else: every other value of the resolved config is
    today's, so a change anywhere else still changes the hash the records are held to."""
    config = load_judge(JUDGE_CONFIG, ROOT)
    other = with_cap(config, config.judging.run_timeout_s + 1800.0)
    today, changed = config.resolved(), other.resolved()

    def without_cap(resolved: dict[str, object]) -> dict[str, object]:
        judging = cast(dict[str, object], resolved["judging"])
        rest = {k: v for k, v in judging.items() if k != "run_timeout_s"}
        return {**resolved, "judging": rest}

    assert without_cap(today) == without_cap(changed)
    assert cast(dict[str, object], changed["judging"])["run_timeout_s"] == (
        config.judging.run_timeout_s + 1800.0
    )
    assert canonical_sha256(changed) != canonical_sha256(today)
