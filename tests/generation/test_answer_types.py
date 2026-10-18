"""S3 AC1: the ChatModel and Guardrail ports live in raglab.core (standard library only, checked
by scripts/check_architecture.py); an Answer carries text, cited ids, label, conflict and status,
and a withheld answer carries nothing; FakeChat lives in raglab.adapters.fake."""

import inspect
import json
from typing import Protocol

import pytest

from raglab.adapters import fake
from raglab.core import ports, types
from raglab.core.types import LABELS, Answer, ChatMessage, ChatRequest, Conflict, Status
from tests.conftest import ROOT, load_script

pytestmark = pytest.mark.unit


def test_the_ports_are_protocols_in_core():
    for name in ("ChatModel", "Guardrail"):
        port = getattr(ports, name)
        assert Protocol in port.__mro__, name
        assert inspect.getsourcefile(port) == str(ROOT / "src" / "raglab" / "core" / "ports.py")
    assert set(dir(ports.Guardrail)) >= {"check_input", "check_retrieved", "check_output", "name"}
    assert set(dir(ports.ChatModel)) >= {"complete", "describe", "model"}
    arch = load_script("check_architecture")
    assert [str(v) for v in arch.check(ROOT / "src" / "raglab")] == []


def test_an_answer_carries_its_five_fields():
    conflict = Conflict(("A@1/1/1", "X@1/1/1"), "the external guidance differs")
    answer = Answer("15 characters.", ("A@1/1/1",), "flag-conflict", conflict, Status.OK)
    assert (answer.text, answer.cited_ids, answer.label, answer.conflict, answer.status) == (
        "15 characters.",
        ("A@1/1/1",),
        "flag-conflict",
        conflict,
        Status.OK,
    )
    assert answer.referenced_ids() == {"A@1/1/1", "X@1/1/1"}
    assert LABELS == ("answer", "abstain", "flag-conflict", "refuse-and-help")
    assert [s.value for s in Status] == [
        "ok",
        "refused",
        "blocked",
        "unavailable",
        "invalid_output",
    ]


@pytest.mark.parametrize("status", [s for s in Status if s is not Status.OK])
def test_a_withheld_answer_has_no_text_no_citations_and_abstains(status):
    answer = Answer.withheld(status)
    assert (answer.text, answer.cited_ids, answer.label, answer.conflict) == (
        "",
        (),
        "abstain",
        None,
    )
    with pytest.raises(ValueError, match="carries no text"):
        Answer("a guess", (), "abstain", None, status)
    with pytest.raises(ValueError, match="carries no text"):
        Answer("", ("A@1/1/1",), "abstain", None, status)
    with pytest.raises(ValueError, match="carries no text"):
        Answer("", (), "answer", None, status)


def test_an_unknown_label_and_an_empty_conflict_are_refused():
    with pytest.raises(ValueError, match="is not one of"):
        Answer("x", (), "maybe", None, Status.OK)  # pyright: ignore[reportArgumentType]
    with pytest.raises(ValueError, match="at least one chunk"):
        Conflict((), "no chunks")
    with pytest.raises(ValueError, match="never withheld"):
        Answer.withheld(Status.OK)


def test_fake_chat_lives_in_the_fake_adapters_and_echoes_or_follows_its_script():
    assert inspect.getsourcefile(fake.FakeChat) == str(
        ROOT / "src" / "raglab" / "adapters" / "fake.py"
    )
    framed = (
        'Question:\n<question>\nq\n</question>\n\n<chunk id="A@1/1/1" document="D">\nfirst\n'
        '</chunk>\n\n<chunk id="A@1/2/1" document="D">\nsecond\n</chunk>'
    )
    request = ChatRequest((ChatMessage("user", framed),), "s", {}, 1)
    echoed = json.loads(fake.FakeChat().complete(request).text)
    assert echoed["cited_ids"] == ["A@1/1/1", "A@1/2/1"]
    assert echoed["answer"] == "first\n\nsecond"
    assert echoed["label"] == "answer"
    empty = ChatRequest((ChatMessage("user", "no passages"),), "s", {}, 1)
    assert json.loads(fake.FakeChat().complete(empty).text)["label"] == "abstain"
    scripted = fake.FakeChat(["one", types.ChatUnavailable("down")])
    assert scripted.complete(request).text == "one"
    with pytest.raises(types.ChatUnavailable, match="down"):
        scripted.complete(request)
    with pytest.raises(types.ChatUnavailable, match="no reply left"):
        scripted.complete(request)
    assert fake.FakeChat(lambda r: "called").complete(request).text == "called"
    assert fake.FakeChat().describe() == {
        "provider": "fake",
        "model": "fake-echo",
        "digest": "fake",
    }
