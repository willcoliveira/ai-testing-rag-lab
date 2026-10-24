"""The suites per filter, binary per build (S7, AG4, AG5, AG6; how-to 07 step 9): every
handwritten case of the security pack decided by its layer, then the derived suites: the golden
set's dev questions (the input layers; the test split is never read here), the clean inventory and
the attack pages (the instruction scan and the register filter), and the recorded answers of the
consistency baseline and its repeats (the output layers: the replay of D3). One wrong decision
fails the build, and the failure names the case and the layer."""

from functools import cache

import pytest

from raglab.core.ports import Guardrail
from raglab.core.types import ScoredChunk
from raglab.evals import golden, guard_suites, replay
from raglab.evals.config import load_generation
from raglab.generate.prompts import CURRENT
from raglab.guard import default_guards
from raglab.ingest import scan
from raglab.ingest import security_pack as pack
from tests import security_support as s
from tests.conftest import ROOT

pytestmark = pytest.mark.security


@cache
def guards() -> dict[str, Guardrail]:
    return {g.name: g for g in default_guards(ROOT, s.clean())}


@cache
def resolved() -> dict[str, tuple[pack.Case, dict[str, object]]]:
    found = pack.sources(ROOT, CURRENT.SYSTEM)
    return {
        c.id: (c, pack.resolved_input(c, found)) for c in pack.load(ROOT) if c.layer != "attack"
    }


CASES = [pytest.param(case_id, id=case_id) for case_id in resolved()]


@pytest.mark.parametrize("case_id", CASES)
def test_each_handwritten_case_gets_its_decision(case_id: str):
    case, data = resolved()[case_id]
    blocked = guard_suites.decide(case.layer, data, guards())
    expected = case.kind == "must_block"
    assert blocked == expected, (
        f"{case.layer}: {case.id} ({case.kind}) was {'blocked' if blocked else 'let through'}"
    )


def dev_questions() -> list[golden.Question]:
    """The dev questions of the golden file the local config names (v1.1 until S4b merges)."""
    local = load_generation(ROOT / "config" / "local-ollama.toml", ROOT, require_digest=False)
    items = golden.load(ROOT / local.dataset)
    return [*golden.select(items, "retrieval", "dev"), *golden.select(items, "behaviour", "dev")]


@pytest.mark.parametrize("layer", guard_suites.INPUT_LAYERS)
def test_no_dev_question_of_the_golden_set_is_refused(layer: str):
    questions = dev_questions()
    assert questions
    assert {q.split for q in questions} == {"dev"}
    refused = [
        q.case_id
        for q in questions
        if guard_suites.decide(
            layer, {"stage": "input", "question": q.question, "tenant": q.tenant}, guards()
        )
    ]
    assert refused == [], f"{layer}: refuses the dev questions {refused}"


def test_the_clean_pack_raises_no_flag_and_loses_no_chunk():
    flagged = [str(c.chunk_id) for c in s.clean() if scan.flags(c.text)]
    assert flagged == [], f"{scan.LAYER}: flags the clean chunks {flagged}"
    register = guards()["register"]
    dropped = [
        str(c.chunk_id)
        for c in s.clean()
        if not register.drop_retrieved(c.tenant, (ScoredChunk(c, 1.0),))[0]
    ]
    assert dropped == [], f"register: drops the clean chunks {dropped}"
    assert len(s.clean()) == 228


def test_every_attack_page_is_left_out_and_the_planted_instruction_flagged():
    register = guards()["register"]
    kept = [
        str(c.chunk_id)
        for c in s.pages()
        if register.drop_retrieved(c.tenant, (ScoredChunk(c, 1.0),))[0]
    ]
    assert kept == [], f"register: keeps the attack pages' chunks {kept}"
    assert [str(c.chunk_id) for c in s.pages() if scan.flags(c.text)] == ["T-HIDDEN@1.0/5/1"]


def test_the_recorded_answers_of_the_consistency_baseline_raise_no_event():
    """The replay (D3) as a pr-fast test: today's guard set over the baseline and its repeats."""
    runs = replay.baseline_runs(ROOT)
    assert len(runs) == 5
    result = replay.replay(runs, list(guards().values()), s.clean())
    assert result.checked["answers"] > 0
    assert [e.line() for e in result.events] == []
