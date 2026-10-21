"""S5 AC4: the canaries stop the judge. A scripted judge with every canary on its side passes them;
one item off its side (a verdict on the other side, unable_to_verify, a reply off the schema or no
reply) stops the session, naming the item. The loader is strict: an item shows exactly the inputs
its criterion sees, and every corpus passage it names is read from the corpus.

The judged run's own test (tests/judge/test_judged_run.py) shows the canaries run first and that
a stop leaves no judged call and no record."""

import json

import pytest

from raglab.adapters.fake import FakeChat
from raglab.core.types import ChatUnavailable
from raglab.judge import canaries
from raglab.judge.llm import LLMJudge
from tests.conftest import ROOT

pytestmark = pytest.mark.unit
COMMITTED = ROOT / "datasets" / "canaries.judge.jsonl"


def reply(verdict: str) -> str:
    return json.dumps(
        {"answer_quote": "", "passage_ids": [], "reason": "Scripted.", "verdict": verdict}
    )


def committed():
    items = canaries.load(COMMITTED)
    return items, canaries.corpus_passages(ROOT, items)


def on_side_replies(items) -> list[str]:
    return [reply(c.side) for c in items]


def test_a_judge_with_every_canary_on_its_side_passes_them():
    items, passages = committed()
    chat = FakeChat(on_side_replies(items))
    results = canaries.run(LLMJudge(chat), items, passages, seed=7)
    assert [r.on_side for r in results] == [True] * len(items)
    canaries.require_on_side(results)  # no stop
    assert len(chat.requests) == len(items)
    assert {r.seed for r in chat.requests} == {7}


@pytest.mark.parametrize(
    "wrong",
    [
        lambda side: reply("pass" if side == "fail" else "fail"),
        lambda side: reply("unable_to_verify"),
        lambda side: '{"verdict": "fail"}',
        lambda side: ChatUnavailable("HTTP 500 from /v1/chat/completions"),
    ],
    ids=["other-side", "unable-to-verify", "off-schema", "no-reply"],
)
def test_one_canary_off_its_side_stops_the_judge_naming_it(wrong):
    items, passages = committed()
    script: list[object] = list(on_side_replies(items))
    flipped = next(i for i, c in enumerate(items) if c.id == "C-01")  # the metric canary
    script[flipped] = wrong(items[flipped].side)
    results = canaries.run(LLMJudge(FakeChat(script)), items, passages, seed=7)  # type: ignore[arg-type]
    assert [r.canary.id for r in results if not r.on_side] == ["C-01"]
    with pytest.raises(canaries.CanaryStop) as stopped:
        canaries.require_on_side(results)
    message = str(stopped.value)
    assert "canary C-01 (grounded) must fail" in message
    assert "before any judged call" in message
    assert message.count("canary C-") == 1  # only the item off its side is named


def test_every_item_off_its_side_is_named_not_only_the_first():
    items, passages = committed()
    script = [reply("unable_to_verify")] * len(items)
    results = canaries.run(LLMJudge(FakeChat(script)), items, passages, seed=7)
    assert len(canaries.off_side(results)) == len(items)


def test_the_results_a_manifest_carries_name_each_item_its_side_and_its_verdict():
    items, passages = committed()
    results = canaries.run(LLMJudge(FakeChat(on_side_replies(items))), items, passages, seed=7)
    rows = canaries.results_json(results)
    assert [(r["id"], r["criterion"], r["side"], r["verdict"], r["on_side"]) for r in rows] == [
        (c.id, c.criterion, c.side, c.side, True) for c in items
    ]
    assert all(isinstance(r["reply"], str) for r in rows)
    assert all("text" not in r for r in rows)  # passages by id, never their text


def test_corpus_passages_are_read_from_the_corpus_and_a_written_one_is_kept():
    items, passages = committed()
    c19 = next(c for c in items if c.id == "C-19")
    item = canaries.item(c19, passages, seed=1)
    assert item.passages is not None
    assert [p.chunk_id for p in item.passages] == [
        "A-NOTE@1.0/1/1",
        "X-NCSC@1.0/3/1",
        "A-FAQ@1.0/Q2/1",
        "X-NCSC@1.0/1/1",
        "A-IR@1.0/5.4/1",
        "A-PWD-V2@2.0/4.4/1",
    ]
    faq = item.passages[2]
    assert (faq.document, faq.version, faq.section, faq.status) == (
        "Identity and Access FAQ",
        "1.0",
        "Q2",
        "approved",
    )
    assert "User passwords expire every 60 days" in faq.text


def line(**row: object) -> str:
    base: dict[str, object] = {
        "id": "C-99",
        "criterion": "relevant",
        "side": "pass",
        "purpose": "A test item.",
        "question": "q?",
        "answer": "a.",
    }
    base.update(row)
    return json.dumps({k: v for k, v in base.items() if v is not None})


@pytest.mark.parametrize(
    ("text", "match"),
    [
        (line(side="maybe"), "side 'maybe' is not pass or fail"),
        (line(criterion="helpful"), "criterion 'helpful' is not one of"),
        (line(answer=None), "has exactly the inputs relevant sees"),
        (line(reference="extra"), "has exactly the inputs relevant sees"),
        (line(purpose=""), "purpose must be a non-empty string"),
        (
            line(criterion="grounded", passages=[{"chunk_id": "X", "text": "t"}]),
            "a written passage has exactly",
        ),
        (line(criterion="grounded", passages="A-PWD@1.0/1/1"), "passages is a list"),
        ("not json", "not JSON"),
    ],
)
def test_a_wrong_canary_is_refused_naming_the_line(tmp_path, text, match):
    path = tmp_path / "c.jsonl"
    path.write_text(text + "\n", encoding="utf-8")
    with pytest.raises(canaries.CanaryError, match=match):
        canaries.load(path)


def test_a_repeated_id_and_an_unknown_chunk_are_refused(tmp_path):
    path = tmp_path / "c.jsonl"
    path.write_text(line() + "\n" + line() + "\n", encoding="utf-8")
    with pytest.raises(canaries.CanaryError, match="C-99 is used twice"):
        canaries.load(path)
    path.write_text(
        line(criterion="grounded", passages=["A-PWD-V2@2.0/99/1"]) + "\n", encoding="utf-8"
    )
    with pytest.raises(canaries.CanaryError, match="does not hold"):
        canaries.corpus_passages(ROOT, canaries.load(path))


def test_raglab_canaries_prints_and_logs_each_calls_verdict_seconds_and_tokens(
    tmp_path, monkeypatch, capsys
):
    """`raglab canaries` (the short judge session of `make judge-canaries`): one line per item
    with its seconds and tokens, a log of every result under runs/tmp/canaries/, and exit 1 when
    an item is off its side."""
    from raglab.__main__ import main
    from tests.judge_support import fake_judge, judged_root, script, verdict

    root, _ = judged_root(tmp_path, local=False)
    config = str(root / "config" / "judge.toml")
    for fn, code in ((script, 0), (lambda request: verdict("pass"), 1)):
        judge, chat = fake_judge(fn)
        monkeypatch.setattr(
            "raglab.judge.build.judge_from_config",
            lambda config, response_format=None, j=judge, c=chat: (j, c.describe(), "fake"),
        )
        assert main(["canaries", "--config", config, "--root", str(root)]) == code
        out = capsys.readouterr()
        assert "C-01 grounded: must fail, judged" in out.out
        assert " s, None prompt and None completion tokens" in out.out  # FakeChat reports none
        assert "canaries: 2 calls, " in out.out
    logs = sorted((root / "runs" / "tmp" / "canaries").glob("*.jsonl"))
    assert logs
    rows = [json.loads(x) for x in logs[-1].read_text(encoding="utf-8").splitlines()]
    assert [(r["id"], r["on_side"]) for r in rows] == [("C-01", False), ("C-02", True)]
    assert all("reply" in r and "latency_ms" in r for r in rows)
