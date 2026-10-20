"""S5 AC4 to AC7, offline: the judged run and its record. The canaries run first and a canary off
its side stops the run before any judged call; each answer is judged on its criteria; the record
(run record v1, suite judged) is tied to its source line by line and validates; every call's tokens
are totalled by role; and a hand edit is refused even when resealed. The source is a finished
behaviour run of the small pack (tests.generation_support), the judge a scripted one."""

import json
from pathlib import Path
from typing import Any

import pytest

from raglab.core.types import ChatRequest
from raglab.evals import judged, publish, record
from raglab.judge import canaries
from tests.generation_support import Q_ANS, reply
from tests.judge_support import (
    CANARIES,
    INVENTED,
    answer_of,
    criterion_of,
    fake_judge,
    judged_root,
    local_judge,
    reseal,
    run_judged,
    script,
    verdict,
    write_canaries,
)

pytestmark = pytest.mark.unit


def read(run_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest, lines = record.read(run_dir)
    return manifest, lines  # type: ignore[return-value]


def test_a_judged_run_writes_a_valid_record_tied_to_its_source(tmp_path):
    root, source = judged_root(tmp_path)
    run_dir = run_judged(root, source)
    assert record.validate(run_dir, root) == []
    manifest, lines = read(run_dir)
    _, source_lines = read(source)
    assert manifest["suite"] == "judged"
    assert manifest["provenance"] == "fake"  # a fake judge: never published
    assert manifest["source"]["run_id"] == source.name
    assert [(c["case_id"], c["trial"]) for c in lines] == [
        (c["case_id"], c["trial"]) for c in source_lines
    ]
    assert manifest["judge_prompt"] == {
        "version": "judge-v1",
        "sha256": "10d96ed31467c42c13e2b037956fef94e9a011b47156ffb88d095a40c3955368",
    }
    assert manifest["criteria"]["sha256"] == record.sha256_bytes(
        (root / "CRITERIA.md").read_bytes()
    )
    assert manifest["canaries"]["sha256"] == record.sha256_bytes(
        (root / "canaries.jsonl").read_bytes()
    )
    for name in ("chunker", "embedder", "retriever", "corpus", "dataset"):
        assert manifest[name] == read(source)[0][name], name
    for line, source_line in zip(lines, source_lines, strict=True):
        assert line["answer_sha256"] == record.sha256_bytes(source_line["answer"].encode())
        assert line["retrieved"] == source_line["retrieved"]


def test_each_answer_is_judged_on_its_criteria_and_context_once_per_case(tmp_path):
    root, source = judged_root(tmp_path)
    _, lines = read(run_judged(root, source))
    by_case = {(c["case_id"], c["trial"]): sorted(c["verdicts"]) for c in lines}
    answer = ["cites_support", "correct", "grounded", "relevant"]
    assert by_case[("B-ANS", 1)] == sorted([*answer, "context_sufficient"])
    assert by_case[("B-ANS", 2)] == answer  # one retrieval, so context once per case
    assert by_case[("B-FC", 1)] == sorted([*answer, "context_sufficient"])
    assert by_case[("B-RH", 1)] == sorted(
        ["context_sufficient", "correct", "grounded", "refuses_and_helps", "relevant"]
    )
    assert by_case[("B-ABS", 1)] == ["abstains", "grounded"]
    assert by_case[("B-ABS", 2)] == ["abstains", "grounded"]


def test_a_cited_answer_is_shown_its_cited_passages_and_the_others_their_retrieved_ones(tmp_path):
    root, source = judged_root(tmp_path)
    _, lines = read(run_judged(root, source))
    _, sources = read(source)
    fc = next(c for c in lines if (c["case_id"], c["trial"]) == ("B-FC", 1))
    fc_source = next(c for c in sources if (c["case_id"], c["trial"]) == ("B-FC", 1))
    retrieved = [r["chunk_id"] for r in fc_source["retrieved"]]
    assert fc["verdicts"]["grounded"]["shown_ids"] == retrieved
    assert fc["verdicts"]["cites_support"]["shown_ids"] == list(
        dict.fromkeys([*fc_source["cited_ids"], *fc_source["conflict"]["chunk_ids"]])
    )
    assert fc["verdicts"]["correct"]["shown_ids"] == []
    assert fc["verdicts"]["relevant"]["shown_ids"] == []


def test_a_withheld_trial_is_not_judged_but_its_retrieval_still_is(tmp_path):
    """A trial whose answer was withheld has no text: no criterion that reads the answer, no
    repeat and no order check; context_sufficient reads only its passages."""
    from tests.generation_support import behaviour_run

    root, source = judged_root(tmp_path)
    _, source = behaviour_run(
        tmp_path,
        {Q_ANS: reply("answer", "x", ["A-NOPE@1.0/1/1"])},  # cites an unretrieved id: blocked
        local=True,
        root=root,
        when=__import__("datetime").datetime(
            2026, 10, 19, 13, 0, tzinfo=__import__("datetime").UTC
        ),
    )
    run_dir = run_judged(root, source)
    assert record.validate(run_dir, root) == []
    _, lines = read(run_dir)
    first = next(c for c in lines if (c["case_id"], c["trial"]) == ("B-ANS", 1))
    assert first["source_status"] == "blocked"
    assert sorted(first["verdicts"]) == ["context_sufficient"]
    assert "repeat" not in first
    assert "reversed" not in first


def test_the_canaries_run_first_and_a_miss_stops_the_run_before_any_judged_call(tmp_path):
    root, source = judged_root(tmp_path)
    seen: list[str] = []

    def lenient(request: ChatRequest) -> str:
        seen.append(answer_of(request) or "")
        return verdict("pass", (answer_of(request) or "")[:5])  # the invented canary passes

    judge, chat = fake_judge(lenient)
    with pytest.raises(canaries.CanaryStop, match="canary C-01 \\(grounded\\) must fail"):
        run_judged(root, source, judge, chat.describe())
    assert len(chat.requests) == len(CANARIES)  # the canaries only: no judged call
    assert seen[0] == CANARIES[0]["answer"]
    assert [p.name for p in (root / "runs" / "tmp").iterdir()] == [source.name]


def test_the_canaries_are_judged_before_every_answer_and_recorded(tmp_path):
    root, source = judged_root(tmp_path)
    judge, chat = fake_judge()
    run_dir = run_judged(root, source, judge, chat.describe())
    first = [answer_of(r) for r in chat.requests[: len(CANARIES)]]
    assert first == [c.get("answer") for c in CANARIES]
    manifest, _ = read(run_dir)
    assert [
        (r["id"], r["side"], r["verdict"], r["on_side"]) for r in manifest["canaries"]["results"]
    ] == [
        ("C-01", "fail", "fail", True),
        ("C-02", "pass", "pass", True),
    ]
    assert manifest["results"]["judged"]["canaries"] == {"items": 2, "on_side": 2}


def test_the_cli_writes_no_record_when_a_canary_stops_the_judge(tmp_path, monkeypatch, capsys):
    from raglab.__main__ import main
    from raglab.evals import retrieval
    from raglab.ingest import pipeline
    from tests.judge_support import small_inventory
    from tests.retrieval_support import GIT

    root, source = judged_root(tmp_path)
    monkeypatch.setattr(pipeline, "ingest", lambda root, settings=None: small_inventory())
    monkeypatch.setattr(retrieval, "git_state", lambda root: GIT)
    for fn, code in ((lambda r: verdict("pass"), 1), (script, 0)):
        judge, chat = fake_judge(fn)
        monkeypatch.setattr(
            "raglab.judge.build.judge_from_config",
            lambda config, response_format=None, j=judge, c=chat: (j, c.describe(), "fake"),
        )
        config = str(root / "config" / "judge.toml")
        argv = ["judge", "--run", str(source), "--config", config, "--root", str(root)]
        assert main(argv) == code
        written = sorted(p.name for p in (root / "runs" / "tmp").iterdir())
        if code == 1:
            assert written == [source.name]
            assert "judge stopped: the canaries stopped the judge" in capsys.readouterr().err
    [judged_dir] = [p for p in (root / "runs" / "tmp").iterdir() if p.name != source.name]
    assert record.validate(judged_dir, root) == []


def test_every_calls_tokens_are_totalled_by_role(tmp_path):
    """AC6: the generator's from the source lines (the stub reports 100 and 20), the judge's and
    the checks' from the verdicts (300 and 40), the canaries' from their results; a call whose
    server reported none is unreported."""
    root, source = judged_root(tmp_path)  # a local source through the stub: 100 and 20 a call
    judge, description, provenance = local_judge()
    run_dir = run_judged(root, source, judge, description, provenance)
    manifest, lines = read(run_dir)
    tokens = manifest["results"]["judged"]["tokens"]
    calls = sum(len(c["verdicts"]) for c in lines)
    checks = sum(len(c.get("repeat", {})) + len(c.get("reversed", {})) for c in lines)
    assert tokens["generator"] == {"calls": 14, "prompt": 1400, "completion": 280, "unreported": 0}
    assert tokens["judge"] == {
        "calls": calls,
        "prompt": 300 * calls,
        "completion": 40 * calls,
        "unreported": 0,
    }
    assert tokens["judge_checks"] == {
        "calls": checks,
        "prompt": 300 * checks,
        "completion": 40 * checks,
        "unreported": 0,
    }
    assert tokens["canaries"] == {"calls": 2, "prompt": 600, "completion": 80, "unreported": 0}
    fake = run_judged(
        root,
        source,
        when=__import__("datetime").datetime(
            2026, 10, 20, 13, 0, tzinfo=__import__("datetime").UTC
        ),
    )
    unreported = read(fake)[0]["results"]["judged"]["tokens"]["judge"]
    assert (unreported["prompt"], unreported["unreported"]) == (0, unreported["calls"])


def test_the_run_stops_at_its_cap_and_is_partial(tmp_path):
    root, source = judged_root(tmp_path)
    clock = iter(range(0, 10_000, 5))
    judge, description, provenance = local_judge()
    run_dir = run_judged(
        root, source, judge, description, provenance, cap=20, monotonic=lambda: float(next(clock))
    )
    manifest, lines = read(run_dir)
    assert manifest["partial"] is True
    assert "wall-clock cap of 20 s" in manifest["totals"]["stopped"]
    assert 0 < len(lines) < 14
    assert record.validate(run_dir, root) == []
    with pytest.raises(publish.PublishError, match="partial"):
        publish.publish(run_dir, root, privacy=lambda *_: [])


# ---------------------------------------------------------------- hand edits, resealed (AC5 to AC7)


def edited(tmp_path: Path, edit) -> tuple[Path, list[str]]:
    root, source = judged_root(tmp_path)
    run_dir = run_judged(root, source)
    manifest, lines = read(run_dir)
    edit(manifest, lines)
    reseal(run_dir, manifest, lines)
    return run_dir, record.validate(run_dir, root)


def first_line(lines: list[dict[str, Any]], case_id: str = "B-ANS") -> dict[str, Any]:
    return next(c for c in lines if c["case_id"] == case_id and c["trial"] == 1)


def test_a_line_whose_answer_sha256_differs_from_its_source_is_refused(tmp_path):
    def edit(manifest, lines):
        first_line(lines)["answer_sha256"] = "0" * 64

    _, problems = edited(tmp_path, edit)
    assert any("answer_sha256 is not its source line's" in p for p in problems), problems


def test_edited_results_are_refused(tmp_path):
    root, source = judged_root(tmp_path)
    run_dir = run_judged(root, source)
    manifest, _ = read(run_dir)
    manifest["results"]["metrics"]["grounded"]["value"] = 0.5
    body = {k: v for k, v in manifest.items() if k != "files"}
    (run_dir / record.MANIFEST).write_text(json.dumps({**body, "files": manifest["files"]}))
    problems = record.validate(run_dir, root)
    assert any("results do not match the cases" in p for p in problems), problems


def test_a_verdict_flipped_and_resealed_is_refused_by_its_reply(tmp_path):
    """AC7's break, offline: a verdict edited apart from the reply it came in."""

    def edit(manifest, lines):
        first_line(lines)["verdicts"]["grounded"]["verdict"] = "fail"

    _, problems = edited(tmp_path, edit)
    assert any("are not its reply's" in p for p in problems), problems


def test_dropping_the_judges_completion_tokens_from_the_totals_is_refused(tmp_path):
    """AC6's break: validate recomputes the totals by role from the lines."""
    root, source = judged_root(tmp_path)
    judge, description, provenance = local_judge()
    run_dir = run_judged(root, source, judge, description, provenance)
    manifest, _ = read(run_dir)
    manifest["results"]["judged"]["tokens"]["judge"]["completion"] = 0
    (run_dir / record.MANIFEST).write_text(json.dumps(manifest))
    problems = record.validate(run_dir, root)
    assert any("results do not match the cases" in p for p in problems), problems


def test_a_verdict_shown_other_passages_is_refused(tmp_path):
    def edit(manifest, lines):
        first_line(lines)["verdicts"]["grounded"]["shown_ids"].reverse()

    _, problems = edited(tmp_path, edit)
    assert any("not the passages it sees" in p for p in problems), problems


def test_a_missing_line_or_a_changed_source_is_refused(tmp_path):
    def drop(manifest, lines):
        lines.pop(3)

    _, problems = edited(tmp_path, drop)
    assert any("not the source run's case-trials" in p for p in problems), problems
    root, source = judged_root(tmp_path / "b")
    run_dir = run_judged(root, source)
    text = (source / record.MANIFEST).read_text().replace('"gate": "manual"', '"gate": "weekly"')
    (source / record.MANIFEST).write_text(text)
    problems = record.validate(run_dir, root)
    assert any("has another manifest sha256" in p for p in problems), problems


def test_a_quote_check_that_does_not_follow_from_the_answer_is_refused(tmp_path):
    def edit(manifest, lines):
        verdict_ = first_line(lines)["verdicts"]["relevant"]
        verdict_["quote_found"] = not verdict_["quote_found"]

    _, problems = edited(tmp_path, edit)
    assert any("quote_found does not follow from the answer" in p for p in problems), problems


def test_a_canary_off_its_side_cannot_be_in_a_record(tmp_path):
    def edit(manifest, lines):
        row = manifest["canaries"]["results"][0]
        row["verdict"], row["on_side"] = "pass", False

    _, problems = edited(tmp_path, edit)
    assert any("canary C-01 is off its side" in p for p in problems), problems


# ---------------------------------------------------------------- publish (AC1, AC5)


def published_pair(tmp_path: Path) -> tuple[Path, Path, Path]:
    """A local judged run of a local source; nothing published yet."""
    root, source = judged_root(tmp_path)
    judge, description, provenance = local_judge()
    run_dir = run_judged(root, source, judge, description, provenance)
    assert record.validate(run_dir, root) == []
    return root, source, run_dir


def test_publish_requires_the_source_run_published(tmp_path):
    root, source, run_dir = published_pair(tmp_path)
    with pytest.raises(publish.PublishError, match=r"its source run .* is not published"):
        publish.publish(run_dir, root, privacy=lambda *_: [])
    publish.publish(source, root, privacy=lambda *_: [])
    dest = publish.publish(run_dir, root, privacy=lambda *_: [])
    assert record.validate(dest, root) == []
    index = publish.read_index(root / publish.PUBLISHED)
    entry = next(r for r in index["runs"] if r["run_id"] == run_dir.name)  # type: ignore[index]
    assert entry["judge"] == f"stub-judge:1b@{'a' * 12}"
    assert (entry["prompt"], entry["source"]) == ("judge-v1", source.name)


def test_a_judged_run_under_an_edited_criteria_file_is_refused_as_stale(tmp_path):
    """AC1's break: CRITERIA.md edited after the run."""
    root, source, run_dir = published_pair(tmp_path)
    publish.publish(source, root, privacy=lambda *_: [])
    (root / "CRITERIA.md").write_text("# Criteria (edited)\n", encoding="utf-8")
    with pytest.raises(publish.PublishError, match="stale: it was made under another version of"):
        publish.publish(run_dir, root, privacy=lambda *_: [])


def test_a_judged_run_under_a_canary_set_with_one_side_flipped_is_refused_as_stale(tmp_path):
    """AC1's break: one canary's side flipped after the run."""
    root, source, run_dir = published_pair(tmp_path)
    publish.publish(source, root, privacy=lambda *_: [])
    flipped = [dict(CANARIES[0], side="pass"), CANARIES[1]]
    write_canaries(root, flipped)
    with pytest.raises(publish.PublishError, match="the canary set"):
        publish.publish(run_dir, root, privacy=lambda *_: [])
    assert record.validate(run_dir, root) == []  # still valid, as history: stale, not forged


def test_judged_runs_are_held_to_their_sources_planted_strings(tmp_path):
    root, _, run_dir = published_pair(tmp_path)
    assert publish.planted_strings(run_dir, root) == []
    manifest, _ = read(run_dir)
    assert manifest["source"]["suite"] == "generation"


def test_a_source_that_is_not_a_complete_valid_generation_run_is_refused(tmp_path):
    root, source = judged_root(tmp_path)
    judged_once = run_judged(root, source)
    with pytest.raises(judged.JudgedError, match="only generation runs are judged"):
        run_judged(root, judged_once)
    assert INVENTED  # the scripted judge fails only an invented answer
    assert criterion_of  # used by the order check's tests
