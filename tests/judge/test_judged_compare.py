"""S8 (GA6, D1 A): `raglab compare` on two judged records under one judge (per criterion, B minus
A of the case's pass share with a paired bootstrap interval and the cases that moved), and
`raglab gate --judged B --against A`, which reads the calibration record (S6's `record.json`): a
trusted criterion fails on an interval entirely below zero, a reported-only, not-trusted or
unnamed criterion never gates, and with no record or no trusted criterion the gate refuses.

The published v2 judged record is S6's and does not exist at `ef46a61`; the evidence here is the
published v1.1 judged baseline (`5aa0ec5`) against copies of itself: identical (every interval
[0, 0]), 20 trusted verdicts flipped to fail (the interval below zero, the gate fails), the same on
a reported-only criterion (expected pass). The trust check is re-run on S6's record after it merges.
"""

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from raglab.__main__ import main
from raglab.evals import compare, judged_gate, publish, record
from raglab.judge.prompts import judge_v2
from tests.conftest import ROOT
from tests.judge_support import reseal
from tests.retrieval_support import read_run

pytestmark = pytest.mark.unit
A = "20261021T081852Z-judge-local-dev-5aa0ec5"  # answer-v1's judged consistency baseline (S5)
B = "20261023T090413Z-judge-local-dev-c14acb0"  # answer-v2's, under the same judge
A_DIR = ROOT / publish.PUBLISHED / A


def copy_of(tmp_path: Path, run_id: str = A) -> Path:
    """A copy of a published judged record under a tmp runs folder (its source is found
    published under ROOT)."""
    target = tmp_path / "runs" / run_id
    shutil.copytree(ROOT / publish.PUBLISHED / run_id, target)
    return target


def flip(run_dir: Path, criterion: str, count: int | None, to: str = "fail") -> int:
    """Flip up to `count` (all when None) first-pass verdicts of a criterion from pass to `to`,
    reply text included so the parser agrees, and reseal; the number flipped."""
    manifest, lines = read_run(run_dir)
    flipped = 0
    for line in lines:
        verdicts = line.get("verdicts") or {}
        found = verdicts.get(criterion)
        if found is None or found["verdict"] != "pass" or (count is not None and flipped >= count):
            continue
        reply = json.loads(found["reply"])
        reply["verdict"] = to
        found["reply"] = json.dumps(reply, indent=2)
        found["verdict"] = to
        flipped += 1
    reseal(run_dir, manifest, lines)
    return flipped


def calibration_record(manifest: dict[str, Any], **status: str) -> dict[str, Any]:
    """A hand-built calibration record in S6's shape: the judge block by identity, a status per
    calibrated criterion, and agreement numbers the gate quotes beside the verdict."""
    return {
        "schema_version": "calibration-record.v1",
        "calibration": "test-c1",
        "judge": {
            "model": manifest["judge"]["model"],
            "digest": manifest["judge"]["digest"],
            "temperature": manifest["judge"].get("temperature"),
            "prompt": manifest["judge_prompt"]["version"],
            "prompt_sha256": manifest["judge_prompt"]["sha256"],
        },
        "bar": {"reads": "kappa", "criteria": {k: {"trusted": 0.8, "stop": 0.6} for k in status}},
        "agreement": {
            name: {"kappa": {"value": 0.9}, "tpr_weighted": {"value": 0.9}, "tnr_weighted": 0.8}
            for name in status
        },
        "status": status,
    }


def write_record(root: Path, data: dict[str, Any], name: str = "test-c1") -> Path:
    path = root / judged_gate.CALIBRATION_DIR / name / judged_gate.RECORD
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------- the comparison


def test_a_judged_record_against_a_copy_of_itself_is_zero_everywhere(tmp_path):
    copy = copy_of(tmp_path)
    result: Any = compare.compare(A_DIR, copy, ROOT)
    assert (result["suite"], result["a"], result["b"]) == ("judged", A, A)
    assert set(result["judge"]) == {f"{p}.{k}" for p, k in compare.JUDGE_IDENTITY}
    assert result["metrics"], "the criteria judged"
    for name, m in result["metrics"].items():
        assert (m["diff"], m["ci_low"], m["ci_high"]) == (0, 0, 0), name
        assert m["a"] == m["b"]
        assert result["changed"][name] == {"better": [], "worse": []}
    assert result["flipped"] == {"gained": [], "lost": []}
    assert "One judge:" in compare.render(result)
    assert "Nothing here gates" in compare.render(result)


def test_the_two_published_judged_records_compare_under_one_judge():
    """answer-v1's and answer-v2's judged records (the one-judge test holds them to one judge)
    are a real paired comparison: the same 49 cases, every criterion with its interval."""
    result: Any = compare.compare(A_DIR, ROOT / publish.PUBLISHED / B, ROOT)
    assert result["n"] == 49
    assert result["sources"]["a"] != result["sources"]["b"]
    assert "grounded" in result["metrics"]
    assert all(m["ci_low"] <= m["diff"] <= m["ci_high"] for m in result["metrics"].values())


def test_a_judged_run_under_another_judge_or_dataset_is_not_paired(tmp_path):
    copy = copy_of(tmp_path)
    manifest, lines = read_run(copy)
    manifest["judge"]["digest"] = "0" * 12
    reseal(copy, manifest, lines)
    with pytest.raises(compare.CompareError, match="compare only under one judge"):
        compare.compare(A_DIR, copy, ROOT)
    # another dataset is refused before pairing: a judged record's dataset is its source's
    generation = ROOT / publish.PUBLISHED / "20261019T172035Z-generation-local-ollama-dev-97011a7"
    with pytest.raises(compare.CompareError, match="not paired"):
        compare.compare(generation, A_DIR, ROOT)


# ---------------------------------------------------------------- the gate's rule


def test_twenty_trusted_verdicts_flipped_fail_the_gate_and_a_reported_only_criterion_does_not(
    tmp_path,
):
    manifest, _ = read_run(A_DIR)
    data = calibration_record(manifest, grounded="trusted", abstains="reported only")
    identical = copy_of(tmp_path / "same")
    result: Any = compare.compare(A_DIR, identical, ROOT)
    outcome = judged_gate.verdict(result, data)
    assert outcome.passed, outcome.lines
    assert outcome.lines[-1] == "passes: no trusted criterion (grounded) dropped"
    assert any(line.startswith("  grounded: trusted, passes:") for line in outcome.lines)
    assert any(line.startswith("  abstains: reported only, never gates:") for line in outcome.lines)
    assert any("not calibrated" in line and "never gates" in line for line in outcome.lines)
    # 20 trusted verdicts flipped to fail: the interval lies entirely below zero
    dropped = copy_of(tmp_path / "dropped")
    assert flip(dropped, "grounded", 20) == 20
    assert record.validate(dropped, ROOT) == []
    result: Any = compare.compare(A_DIR, dropped, ROOT)
    grounded = result["metrics"]["grounded"]
    assert grounded["ci_high"] < 0, grounded
    outcome = judged_gate.verdict(result, data)
    assert not outcome.passed
    assert outcome.lines[-1] == "fails: grounded dropped by an interval entirely below zero"
    assert any(line.startswith("  grounded: trusted, FAILS:") for line in outcome.lines)
    assert any("tpr_weighted 0.900" in line for line in outcome.lines)
    assert set(result["changed"]["grounded"]["worse"]) >= set(result["flipped"]["lost"])
    # the same on a reported-only criterion: printed, never gating (expected pass)
    reported = copy_of(tmp_path / "reported")
    assert flip(reported, "abstains", None) > 0
    result: Any = compare.compare(A_DIR, reported, ROOT)
    assert result["metrics"]["abstains"]["diff"] < 0
    outcome = judged_gate.verdict(result, data)
    assert outcome.passed, outcome.lines
    assert any(line.startswith("  abstains: reported only, never gates:") for line in outcome.lines)
    # the trust check: a record that marks grounded reported only stops gating it
    demoted = calibration_record(manifest, grounded="reported only", abstains="reported only")
    result: Any = compare.compare(A_DIR, dropped, ROOT)
    outcome = judged_gate.verdict(result, demoted)
    assert not outcome.passed
    assert outcome.lines[-1].startswith("refused: the record marks no compared criterion trusted")
    assert any(line.startswith("  grounded: reported only, never gates:") for line in outcome.lines)


def test_an_unnamed_criterion_is_refused_from_gating_and_a_bad_record_is_refused(tmp_path):
    manifest, _ = read_run(A_DIR)
    data = calibration_record(manifest, abstains="trusted")
    result: Any = compare.compare(A_DIR, copy_of(tmp_path), ROOT)
    outcome = judged_gate.verdict(result, data)
    assert outcome.passed
    assert any(
        line.startswith("  grounded: not calibrated (no status in the record), never gates:")
        for line in outcome.lines
    )
    path = write_record(tmp_path, {**data, "status": {"abstains": "maybe"}})
    with pytest.raises(judged_gate.GateError, match="not one of"):
        judged_gate.read_record(path)
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(judged_gate.GateError, match="not a calibration record"):
        judged_gate.read_record(path)


# ---------------------------------------------------------------- finding the record


def test_the_record_is_found_by_the_pin_or_by_identity_and_a_changed_pin_is_refused(tmp_path):
    manifest, _ = read_run(A_DIR)
    assert judged_gate.find_record(tmp_path, manifest) is None  # none under datasets/calibration
    data = calibration_record(manifest, grounded="trusted")
    path = write_record(tmp_path, data)
    found: Any = judged_gate.find_record(tmp_path, manifest)
    assert found is not None
    assert found[0] == path
    assert found[1]["status"] == {"grounded": "trusted"}
    other = {**data, "judge": {**data["judge"], "digest": "0" * 12}}
    write_record(tmp_path, other, name="other-judge")
    assert judged_gate.find_record(tmp_path, manifest) == found  # by identity, the other skipped
    # the pin: a judged manifest names the record it gates on; a record changed since is refused
    pinned = {**manifest, "judge": {**manifest["judge"]}}
    pinned["judge"]["calibration_record"] = {
        "path": path.relative_to(tmp_path).as_posix(),
        "sha256": record.sha256_bytes(path.read_bytes()),
    }
    assert judged_gate.find_record(tmp_path, pinned) == (path, data)
    path.write_text(json.dumps({**data, "status": {"grounded": "reported only"}}), encoding="utf-8")
    with pytest.raises(judged_gate.GateError, match=r"changed since .* pinned it"):
        judged_gate.find_record(tmp_path, pinned)
    pinned["judge"]["calibration_record"]["path"] = "datasets/calibration/none/record.json"
    with pytest.raises(judged_gate.GateError, match="does not exist"):
        judged_gate.find_record(tmp_path, pinned)


def test_a_new_judged_run_names_the_record_that_describes_its_judge(tmp_path):
    """GA6: new judged manifests carry judge.calibration_record when a record describes their
    judge; without one the key is absent (S6's baseline predates the record and is matched by
    identity, never edited)."""
    from tests.judge_support import judged_root, run_judged

    root, source = judged_root(tmp_path)
    plain = run_judged(root, source)
    manifest, _ = read_run(plain)
    assert "calibration_record" not in manifest["judge"]
    assert record.validate(plain, root) == []
    data = calibration_record(manifest, grounded="trusted")
    path = write_record(root, data)
    shutil.rmtree(plain)
    pinned = run_judged(root, source)
    manifest, _ = read_run(pinned)
    assert manifest["judge"]["calibration_record"] == {
        "path": "datasets/calibration/test-c1/record.json",
        "sha256": record.sha256_bytes(path.read_bytes()),
    }
    assert record.validate(pinned, root) == []
    assert judged_gate.find_record(root, manifest) == (path, data)
    assert manifest["judge_prompt"]["version"] == judge_v2.VERSION
    # a malformed record never costs the session: the run is written without the pin
    path.write_text("{}", encoding="utf-8")
    shutil.rmtree(pinned)
    unpinned = run_judged(root, source)
    manifest, _ = read_run(unpinned)
    assert "calibration_record" not in manifest["judge"]
    assert record.validate(unpinned, root) == []


# ---------------------------------------------------------------- the judged drift alert (GA7)


def nightly_copy(root: Path, run_id: str, created_at: str) -> Path:
    """A copy of the v1.1 judged baseline as a published nightly judged run under root (its
    manifest renamed and dated; the alert reads lines and manifests, never validates)."""
    target = root / publish.PUBLISHED / run_id
    shutil.copytree(A_DIR, target)
    manifest = json.loads((target / record.MANIFEST).read_text(encoding="utf-8"))
    manifest["run_id"], manifest["created_at"], manifest["gate"] = run_id, created_at, "nightly"
    (target / record.MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return target


def test_the_judged_alert_reads_the_trusted_criteria_and_names_the_recalibration_trigger(tmp_path):
    """GA7's judged half (the judge's S8-J1): with no calibration record the block says no judged
    alert is read; with a record trusting nothing, the same; with `grounded` trusted, the first
    nightly judged run is the reference, an identical second run does not fire, and one with 20
    grounded verdicts flipped to fail fires on grounded alone, naming S6's recalibration trigger."""
    from raglab.evals import drift

    root = tmp_path / "root"
    first = nightly_copy(root, "20261022T000000Z-judge-local-dev-5aa0ec5", "2026-10-22T00:00:00Z")
    published = root / publish.PUBLISHED
    publish.write_index(published, publish.build_index(published, {}))
    manifest, lines = read_run(first)
    alert: Any = drift.judged_alert_for(root, manifest, lines)
    assert alert == {
        "gate": "nightly",
        "against": None,
        "fired": False,
        "note": "no judged alert: no calibration record describes the judge",
    }
    nothing_trusted = write_record(root, calibration_record(manifest, grounded="reported only"))
    alert = drift.judged_alert_for(root, manifest, lines)
    assert (alert["fired"], alert["criteria"], alert["note"]) == (
        False,
        [],
        "no judged alert: no trusted criterion",
    )
    nothing_trusted.write_text(
        json.dumps(calibration_record(manifest, grounded="trusted", abstains="reported only")),
        encoding="utf-8",
    )
    alert = drift.judged_alert_for(root, manifest, lines)  # the first nightly: the reference
    assert (alert["against"], alert["fired"], alert["criteria"]) == (None, False, ["grounded"])
    assert alert["note"] == "the first nightly judged run is the reference"
    second = nightly_copy(root, "20261023T000000Z-judge-local-dev-5aa0ec5", "2026-10-23T00:00:00Z")
    manifest, lines = read_run(second)
    alert = drift.judged_alert_for(root, manifest, lines)
    assert (alert["against"], alert["fired"], alert["criteria"]) == (
        first.name,
        False,
        ["grounded"],
    )
    assert alert["diff"]["grounded"] == 0
    assert alert["flipped"] == {"gained": [], "lost": []}
    assert "note" not in alert
    assert flip(second, "grounded", 20) == 20
    manifest, lines = read_run(second)
    alert = drift.judged_alert_for(root, manifest, lines)
    assert alert["fired"] is True
    assert alert["against"] == first.name
    assert alert["criteria"] == ["grounded"]
    assert alert["diff"]["grounded.ci_high"] < 0
    assert alert["flipped"]["lost"], "the cases whose share dropped are named"
    assert alert["note"] == drift.RECALIBRATION
    assert "recalibrat" in alert["note"]
    assert "FIRED against" in drift.line(alert)
    # a drop on a criterion the record does not trust never fires: abstains flipped, grounded not
    third = nightly_copy(root, "20261024T000000Z-judge-local-dev-5aa0ec5", "2026-10-24T00:00:00Z")
    assert flip(third, "abstains", None) > 0
    manifest, lines = read_run(third)
    alert = drift.judged_alert_for(root, manifest, lines)
    assert alert["fired"] is False
    assert "abstains" not in alert["diff"]


# ---------------------------------------------------------------- the CLI


def test_the_cli_refuses_without_a_record_and_gates_with_a_given_one(tmp_path, capsys):
    identical = copy_of(tmp_path / "same")
    code = main(["gate", "--judged", str(identical), "--against", A, "--root", str(ROOT)])
    out = capsys.readouterr().out.strip().splitlines()
    assert code == 1
    assert out == [
        f"{judged_gate.NAME}: refused: no calibration record under datasets/calibration/ "
        f"describes the judge of {A} (model ministral-3:14b-instruct-2512-q4_K_M, prompt "
        "judge-v2): nothing judged gates until S6's record trusts a criterion"
    ]
    manifest, _ = read_run(A_DIR)
    path = write_record(tmp_path, calibration_record(manifest, grounded="trusted"))
    command = ["gate", "--judged", str(identical), "--against", A, "--root", str(ROOT)]
    code = main([*command, "--calibration", str(path)])
    out = capsys.readouterr().out.strip().splitlines()
    assert code == 0, out
    assert out[0].startswith(f"{judged_gate.NAME}: {A} against {A}, record ")
    assert out[-1] == "passes: no trusted criterion (grounded) dropped"
    dropped = copy_of(tmp_path / "dropped")
    flip(dropped, "grounded", 20)
    command[2] = str(dropped)
    code = main([*command, "--calibration", str(path)])
    out = capsys.readouterr().out.strip().splitlines()
    assert code == 1
    assert out[-1] == "fails: grounded dropped by an interval entirely below zero"
    assert main(["gate", "--judged", str(identical), "--root", str(ROOT)]) == 2
    assert main(["gate", "--against", A, "--root", str(ROOT)]) == 2
