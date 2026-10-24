"""S5 AC9, offline: the position test's contexts and suite. The answering chunk sits first, in the
middle and last; the fillers are the asker's tenant's chunks in rank order, never a labelled
section or a group member of the case; as many fit as the prompt budget allows at the measured
characters per token; the code checks read the answer key's values (R-11); and a position run
writes a valid generation record whose lines are refused when they are moved or forged."""

import json
from pathlib import Path

import pytest

from raglab.adapters.fake import FakeChat, HashingEmbedder
from raglab.chunk.sections import ChunkSettings
from raglab.core.types import ScoredChunk
from raglab.evals import config as eval_config
from raglab.evals import golden, position, position_record, record
from raglab.generate import prompts
from raglab.generate.assemble import Assembled
from raglab.generate.pipeline import Pipeline
from raglab.guard import default_guards
from raglab.ingest import answer_key
from raglab.ingest.pipeline import Inventory
from tests.conftest import ROOT
from tests.generation_support import (
    BEHAVIOUR_CHUNKS,
    FAQ_Q2,
    GOOD,
    V1_43,
    V2_5,
    V2_41,
    V2_44,
    V2_46,
    generation_config_text,
    per_question,
    write_behaviour_register,
)
from tests.retrieval_support import GIT, dense, lab_root, make_chunk, read_run, write_snapshot

pytestmark = pytest.mark.unit
POSITION_CONFIG = ROOT / "config" / "position-local.toml"
F1, F2, F3, F4 = (make_chunk(f"A-F@1.0/{n}/1", "tenant-a", f"Filler {n}.", str(n)) for n in "1234")


def test_the_answering_chunk_sits_first_in_the_middle_and_last():
    """AC9's break: a builder that puts the answering chunk first at every position fails."""
    filler = [F1, F2, F3, F4]
    ids = {
        w: [c.chunk_id for c in position.place(V2_41, filler, w)]
        for w in ("first", "middle", "last")
    }
    assert ids["first"] == [V2_41.chunk_id, *(c.chunk_id for c in filler)]
    assert ids["middle"] == [F1.chunk_id, F2.chunk_id, V2_41.chunk_id, F3.chunk_id, F4.chunk_id]
    assert ids["last"] == [*(c.chunk_id for c in filler), V2_41.chunk_id]
    odd = position.place(V2_41, [F1, F2, F3], "middle")
    assert [c.chunk_id for c in odd].index(V2_41.chunk_id) == 1  # n // 2 of n + 1 chunks
    assert position.place(V2_41, [], "middle") == [V2_41]


def test_fillers_are_the_tenants_other_chunks_in_rank_order_never_a_label_or_group_member():
    """AC9's break: a group member allowed as filler fails. The case's label is a group: A-PWD-V2
    4.4 and its FAQ restatement Q2; and A-PWD-V1 4.3 is a second label."""
    question = golden.parse_line(
        json.dumps(
            {
                "id": "G-99",
                "kind": "behaviour",
                "split": "dev",
                "tenant": "tenant-a",
                "question": "How often do passwords expire?",
                "relevant": [
                    {
                        "any_of": [
                            {"doc_id": "A-PWD-V2", "section_id": "4.4"},
                            {"doc_id": "A-FAQ", "section_id": "Q2"},
                        ]
                    },
                    {"doc_id": "A-PWD-V1", "section_id": "4.3"},
                ],
            }
        ),
        "test",
    )
    other_tenant = make_chunk("B-X@1.0/1/1", "tenant-b", "Tenant B's chunk.", "1")
    shared = make_chunk("X-S@1.0/1/1", "shared", "A shared reference.", "1")
    ranked = [
        ScoredChunk(c, 1.0 - n / 10)
        for n, c in enumerate([FAQ_Q2, V2_5, other_tenant, V2_44, shared, V2_46, V1_43, V2_41])
    ]
    assert [c.chunk_id for c in position.fillers(question, ranked)] == [
        V2_5.chunk_id,
        V2_46.chunk_id,
        V2_41.chunk_id,
    ]


def test_as_many_fillers_fit_as_the_budget_allows():
    question = golden.parse_line(
        json.dumps(
            {
                "id": "G-98",
                "kind": "behaviour",
                "split": "dev",
                "tenant": "tenant-a",
                "question": "How long must a password be?",
                "relevant": [{"doc_id": "A-PWD-V2", "section_id": "4.1"}],
            }
        ),
        "test",
    )
    candidates = [F1, F2, F3, F4]
    sizes = [position.prompt_chars(question, [V2_41, *candidates[:n]]) for n in range(5)]
    assert sizes == sorted(sizes)
    # at 2.0 characters a token, a budget of exactly the 2-filler prompt fits two, not three
    budget = sizes[2] // 2
    assert position.fit(question, V2_41, candidates, budget, 2.0) == (2 if sizes[2] % 2 == 0 else 1)
    assert position.fit(question, V2_41, candidates, sizes[4], 1.0) == 4
    assert position.fit(question, V2_41, candidates, 1, 1.0) == 0


def test_the_characters_per_token_are_the_fewest_measured():
    assert position.measure([(4000, 1000), (3000, 1000), (5000, 1000)]) == 3.0
    assert position.measure([(10, 0), (900, 300)]) == 3.0
    with pytest.raises(ValueError, match="no prompt with reported tokens"):
        position.measure([(10, 0)])


@pytest.mark.parametrize(
    ("value", "answer", "stated"),
    [
        ("at least 64 characters", "Systems must accept at least 64 characters.", True),
        ("at least 64 characters", "They must accept 64-character passwords.", False),
        ("at least 64 characters", "Up to 64 characters are accepted.", True),  # number and unit
        ("after 12 hours", "SSO asks again after 12  hours.", True),
        ("after 12 hours", "SSO asks again after 24 hours.", False),
        ("30 seconds, doubling after each further failure", "A 30 seconds delay.", True),
        ("Until the IAM team unlocks the account", "until the IAM team unlocks the account", True),
        ("Until the IAM team unlocks the account", "The IAM team unlocks it.", False),
        ("+1-202-555-0147", "Call +1-202-555-0147.", True),
        ("+1-202-555-0147", "Call 202-555-0147.", False),
        ("exactly 2 break-glass accounts", "There are 2 break-glass accounts.", True),
    ],
)
def test_a_value_is_stated_as_the_answer_key_writes_it_or_by_its_numbers_and_units(
    value, answer, stated
):
    assert position_record.value_stated(value, answer) is stated


def test_the_committed_position_config_names_the_ten_dev_single_chunk_answer_cases():
    config = eval_config.load_generation(POSITION_CONFIG, ROOT)
    assert config.position is not None
    derived = [
        q.case_id
        for q in golden.load(ROOT / "datasets" / "golden.v1.jsonl")
        if (q.kind, q.split, q.extra.get("mix"), q.extra.get("expected"))
        == ("behaviour", "dev", "single-chunk", "answer")
    ]
    plan = ["G-01", "G-03", "G-05", "G-06", "G-08", "G-09", "G-10", "G-11", "G-12", "G-14"]
    assert list(config.position.cases) == derived == plan
    local = eval_config.load_generation(ROOT / "config" / "local-ollama.toml", ROOT)
    assert config.generator == local.generator  # the generator under test, its sampling
    assert config.ollama == local.ollama
    assert (config.generation.trials, config.generation.seed) == (3, local.generation.seed)
    assert config.ollama is not None
    window = config.ollama.context_length - (config.generator.max_tokens or 0)
    assert config.position.prompt_budget_tokens <= window


# ---------------------------------------------------------------- a position run (small pack)


def position_root(tmp_path: Path) -> tuple[Path, eval_config.GenerationConfig, Assembled]:
    from tests.generation_support import behaviour_cases

    root = lab_root(tmp_path, behaviour_cases())
    write_behaviour_register(root)
    write_snapshot(root, BEHAVIOUR_CHUNKS)
    path = root / "config" / "position.toml"
    path.parent.mkdir(exist_ok=True)
    text = generation_config_text(trials=2, probes=False).replace(
        'name = "generation-fake"', 'name = "position-fake"'
    )
    path.write_text(
        text
        + '\n[position]\ncases = ["B-ANS", "B-TB"]\nprompt_budget_tokens = 6000\n'
        + "chars_per_token = 3.0\nresamples = 200\n",
        encoding="utf-8",
    )
    config = eval_config.load_generation(path, root)
    chat = FakeChat(per_question(GOOD))
    hashing = HashingEmbedder()
    description = {
        "provider": "fake",
        "model": hashing.model,
        "revision": hashing.revision,
        "dimension": hashing.dimension,
    }
    pipeline = Pipeline(dense(BEHAVIOUR_CHUNKS), chat, default_guards(ROOT, BEHAVIOUR_CHUNKS), 2)
    inventory = Inventory(ChunkSettings(), {"pypdf": "x"}, (), tuple(BEHAVIOUR_CHUNKS))
    return root, config, Assembled(pipeline, inventory, description, chat.describe(), "fake")


def position_run(tmp_path: Path) -> tuple[Path, Path]:
    root, config, built = position_root(tmp_path)
    manifest, cases = position.run(config, root, built, answer_key.features(root), git=GIT)
    return root, record.write(root / "runs" / "tmp", manifest, cases)


def test_a_position_run_writes_a_valid_generation_record(tmp_path):
    root, run_dir = position_run(tmp_path)
    assert record.validate(run_dir, root) == []
    manifest, cases = read_run(run_dir)
    assert manifest["suite"] == "generation"
    # answer-v2's AV3: the position suite builds and records the current prompt
    assert manifest["prompt"] == {"version": "answer-v1", "sha256": prompts.CURRENT.fingerprint()}
    assert manifest["position"]["cases"] == ["B-ANS", "B-TB"]
    assert [(c["case_id"], c["trial"]) for c in cases[:6]] == [
        (f"B-ANS:{w}", t) for w in ("first", "middle", "last") for t in (1, 2)
    ]
    ans = [c for c in cases if c["golden_id"] == "B-ANS"]
    assert {c["answering_chunk"] for c in ans} == {V2_41.chunk_id}
    fillers = {tuple(r["chunk_id"] for r in c["retrieved"] if not r["relevant"]) for c in ans}
    assert len(fillers) == 1  # the same fillers at every position and trial
    [same] = fillers
    assert V2_41.chunk_id not in same
    assert all(c["checks"]["passed"] for c in ans)  # GOOD's reply states "15 characters"
    metrics = manifest["results"]["metrics"]
    assert {"position[first]", "position[middle]", "position[last]"} <= set(metrics)
    assert metrics["position[first]"]["n"] == 2
    assert metrics["position[middle-first]"]["value"] == 0.0
    assert "## Position test" in (run_dir / "report.md").read_text(encoding="utf-8")


def reseal(run_dir: Path, cases: list) -> None:
    manifest, _ = read_run(run_dir)
    body = {k: v for k, v in manifest.items() if k != "files"}
    body["results"] = record.expected_results(body, cases)
    cases_bytes = record.cases_text(cases).encode()
    report_bytes = record.render(body, cases).encode()
    (run_dir / record.CASES).write_bytes(cases_bytes)
    (run_dir / record.REPORT).write_bytes(report_bytes)
    body["files"] = {
        record.CASES: record.sha256_bytes(cases_bytes),
        record.REPORT: record.sha256_bytes(report_bytes),
    }
    (run_dir / record.MANIFEST).write_text(json.dumps(body, indent=2) + "\n")


def test_a_moved_answering_chunk_or_a_labelled_filler_is_refused(tmp_path):
    root, run_dir = position_run(tmp_path)
    _, cases = read_run(run_dir)
    middle = next(c for c in cases if c["case_id"] == "B-ANS:middle")
    rows = middle["retrieved"]
    answering = next(r for r in rows if r["relevant"])
    rows.remove(answering)
    rows.insert(0, answering)  # the answering chunk moved first, the fillers' order kept
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    reseal(run_dir, cases)
    problems = record.validate(run_dir, root)
    assert any("not where middle puts it" in p for p in problems), problems

    root, run_dir = position_run(tmp_path / "b")
    _, cases = read_run(run_dir)
    first = next(c for c in cases if c["case_id"] == "B-ANS:first")
    # a chunk of the labelled section itself, A-PWD-V2 4.1, slipped in as a filler
    labelled = {"rank": 0, "chunk_id": "A-PWD-V2@2.0/4.1/2", "score": 0.1, "relevant": False}
    first["retrieved"].append(labelled)
    for rank, row in enumerate(first["retrieved"], start=1):
        row["rank"] = rank
    reseal(run_dir, cases)
    problems = record.validate(run_dir, root)
    assert any("a filler belongs to a labelled section" in p for p in problems), problems


def test_checks_that_do_not_follow_from_the_answer_key_are_refused(tmp_path):
    root, run_dir = position_run(tmp_path)
    _, cases = read_run(run_dir)
    cases[0]["checks"]["states_value"] = False
    cases[0]["checks"]["passed"] = False
    reseal(run_dir, cases)
    problems = record.validate(run_dir, root)
    assert any("do not follow from the fields" in p for p in problems), problems


def test_the_judges_correct_is_judged_beside_the_code_on_a_position_run(tmp_path):
    """The judge session of the position test: correct only, against the golden case's
    reference answer, on every trial; no repeat and no order check (not a behaviour case)."""
    from raglab.evals import judged
    from tests.judge_support import (
        config,
        fake_judge,
        judge_config_text,
        small_inventory,
        write_canaries,
    )

    root, run_dir = position_run(tmp_path)
    write_canaries(root)
    (root / "CRITERIA.md").write_text("# Criteria (test)\n", encoding="utf-8")
    (root / "config" / "judge.toml").write_text(judge_config_text(), encoding="utf-8")
    judge, chat = fake_judge()
    manifest, lines = judged.run(
        config(root), root, run_dir, judge, chat.describe(), "fake", git=GIT,
        inventory=small_inventory(),
    )  # fmt: skip
    judged_dir = record.write(root / "runs" / "tmp", manifest, lines)
    assert record.validate(judged_dir, root) == []
    _, lines = read_run(judged_dir)
    assert {tuple(sorted(c["verdicts"])) for c in lines} == {("correct",)}
    assert all("repeat" not in c and "reversed" not in c for c in lines)
    assert {c["golden_id"] for c in lines} == {"B-ANS", "B-TB"}
    assert all(c["reference_sha256"] for c in lines)
