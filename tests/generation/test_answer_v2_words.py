"""answer-v2's AV2: the words of its system text come from the requirements (TEST-PLAN section 3
and the R-ids its rules name, traced rule by rule in the plan's ledger), never from the golden set
or the answer key, so the prompt is not fitted to the cases it is measured on.

The text holds no answer-key value, no canary of either tenant, no `answer_must_not_contain`
string and no name from the pack (a document's id or title, an external source, a tenant or a
team), and it shares no run of five or more words with any golden question, dev or test. The
longest run it shares with a golden question and with a corpus document are measured by
`measure()` and reported in the ledger; only the first is bounded, because a rule worded from R-14
or section 3 can repeat a policy's phrase, while a question's wording or a value is the leak that
would fit the prompt to dev.

Words are S2's (runs of letters and digits, case-folded) and the runs are S2's measure
(tests/retrieval/test_golden_behaviour.py). The test reads every golden question, the test split's
too, but never prints a test question: a failure names a test case by its id and the run's length
only.
"""

import json
import re
from collections.abc import Iterator
from functools import cache

import pytest

from raglab.generate.prompts import answer_v2
from raglab.ingest import answer_key
from tests.conftest import ROOT
from tests.corpus_text import documents
from tests.retrieval.test_golden_behaviour import longest_run, texts, words

pytestmark = pytest.mark.unit
DATASET = ROOT / "datasets" / "golden.v1.jsonl"
SPEC = ROOT / "corpus" / "SPEC.md"
LIMIT = 5  # the plan's bound: no run of five or more words shared with a golden question
# a rule's number at the start of a line ("5. "), which is the list, not a value
LIST_MARKER = re.compile(r"^\d+\. ", flags=re.M)


def prose(system: str) -> str:
    """The system text without its rules' numbers."""
    return LIST_MARKER.sub("", system)


def holds(text: str, phrase: str) -> bool:
    """Whether the text holds the phrase, in any letter case, not inside a longer word or
    number."""
    pattern = rf"(?<!\w){re.escape(phrase.casefold())}(?!\w)"
    return re.search(pattern, text.casefold()) is not None


@cache
def questions() -> tuple[tuple[str, str, tuple[str, ...]], ...]:
    """(id, split, words) of every golden question, retrieval and behaviour, dev and test."""
    found: list[tuple[str, str, tuple[str, ...]]] = []
    for line in DATASET.read_text(encoding="utf-8").splitlines():
        if line.strip():
            item = json.loads(line)
            found.append((item["id"], item["split"], tuple(words(item["question"]))))
    return tuple(found)


def values() -> Iterator[tuple[str, str]]:
    """(feature id, value) of every value the answer key's locations state."""
    for feature in answer_key.features(ROOT).values():
        for location in feature.locations:
            for value in location.values:
                yield feature.id, value


def spec_names() -> tuple[list[str], list[str]]:
    """(tenant names, team names) from corpus/SPEC.md: section 2's names, and the rows of
    section 6's contact table that name a tenant's team, with and without the tenant's name."""
    text = SPEC.read_text(encoding="utf-8")
    names = text.split("\n## 2. Names", 1)[1].split("\n## 3.", 1)[0]
    tenants = re.findall(r"^\| Tenant [AB][^|]*\| \*\*(\w+)\*\* \|", names, flags=re.M)
    rules = text.split("\n## 6. ", 1)[1].split("\n## 7. ", 1)[0]
    teams: list[str] = []
    for purpose in re.findall(r"^\s*\| ([^|]+?) \| `", rules, flags=re.M):
        tenant = next((t for t in tenants if purpose.startswith(f"{t} ")), None)
        if tenant is not None:
            teams += [purpose, purpose.removeprefix(f"{tenant} ")]
    return tenants, teams


def pack_names() -> list[str]:
    """Every name of the pack: each document's id and title, the external documents' sources,
    the tenants and their teams."""
    names: list[str] = []
    for doc in documents().values():
        names += [doc.id, str(doc.front["title"])]
        if doc.front.get("kind") == "external":
            names.append(str(doc.front["source"]).split(":", 1)[0])
    tenants, teams = spec_names()
    return [*names, *tenants, *teams]


def golden_runs(system: str) -> list[tuple[int, str, str]]:
    """(longest run of words shared with the text, case id, split) of every golden question,
    longest first."""
    within = texts([words(prose(system))])
    runs = [(longest_run(list(q), within), case_id, split) for case_id, split, q in questions()]
    return sorted(runs, key=lambda r: (-r[0], r[1]))


def measure(system: str = answer_v2.SYSTEM) -> dict[str, tuple[int, str]]:
    """The longest run of words the text shares with a golden question (its case id and split)
    and with a corpus document of the register (its id): what the ledger reports."""
    n, case_id, split = golden_runs(system)[0]
    mine = list(words(prose(system)))
    register = [d for d in documents().values() if not d.path.startswith("corpus/attacks/")]
    by_doc = sorted(
        ((longest_run(mine, texts([words(d.body)])), d.id) for d in register),
        key=lambda r: (-r[0], r[1]),
    )
    return {"golden question": (n, f"{case_id} ({split})"), "corpus document": by_doc[0]}


def value_problems(system: str) -> list[str]:
    text = prose(system)
    return sorted({f"{fid}: {value!r}" for fid, value in values() if holds(text, value)})


def _canaries() -> list[tuple[str, str]]:
    return [(t, c) for t, cs in answer_key.canaries(ROOT).items() for c in cs]


def string_problems(system: str) -> list[str]:
    text = prose(system)
    canaries = [f"canary of {t}: {c!r}" for t, c in _canaries() if holds(text, c)]
    banned = [
        f"{fid} must not contain {s!r}"
        for fid, strings in answer_key.must_not_contain(ROOT).items()
        for s in strings
        if holds(text, s)
    ]
    return sorted({*canaries, *banned})


def name_problems(system: str) -> list[str]:
    text = prose(system)
    return sorted({name for name in pack_names() if holds(text, name)})


def run_problems(system: str) -> list[str]:
    """A golden question sharing five or more words: a dev case by its id and the run's length,
    a test case by its id and length too (its words are never printed)."""
    return [
        f"{case_id} ({split}) shares a run of {n} words"
        for n, case_id, split in golden_runs(system)
        if n >= LIMIT
    ]


# ---------------------------------------------------------------- the committed text


def test_the_text_holds_no_answer_key_value():
    assert value_problems(answer_v2.SYSTEM) == []


def test_the_text_holds_no_canary_and_no_banned_string():
    assert string_problems(answer_v2.SYSTEM) == []


def test_the_text_names_nothing_of_the_pack():
    assert name_problems(answer_v2.SYSTEM) == []


def test_no_run_of_five_words_is_shared_with_a_golden_question():
    assert run_problems(answer_v2.SYSTEM) == []
    assert len(questions()) == 74  # 34 retrieval questions and 40 behaviour cases, both splits


def test_the_longest_runs_are_measured():
    """Reported in the ledger, not bounded but for the golden questions (above)."""
    found = measure()
    assert found["golden question"][0] < LIMIT
    assert found["corpus document"][0] > 0


# ---------------------------------------------------------------- the checks themselves


def test_the_checks_find_what_they_look_for():
    """Each check on a planted text: an answer-key value, a canary, a banned string, a pack name
    and a run of a golden question's words, each named; the list's numbers are not values."""
    feature_id, value = next((f, v) for f, v in values() if " " in v)
    assert f"{feature_id}: {value!r}" in value_problems(f"Rules:\n1. Say {value}.\n")
    assert value_problems("Rules:\n5. Cite.\n10. Reply.\n") == []
    tenant, canary = _canaries()[0]
    assert string_problems(f"Ask {canary} first.") == [f"canary of {tenant}: {canary!r}"]
    fid, strings = next(iter(answer_key.must_not_contain(ROOT).items()))
    assert f"{fid} must not contain {strings[0]!r}" in string_problems(f"x {strings[0]} y")
    tenants, teams = spec_names()
    assert len(tenants) == 2
    assert len(teams) == 6
    assert name_problems(f"Ask the {teams[1]}.") == [teams[1]]
    case_id, split, q = next(item for item in questions() if item[1] == "dev")
    planted = f"Rules:\n1. {' '.join(q[:LIMIT])}.\n"
    assert f"{case_id} ({split}) shares a run of {LIMIT} words" in run_problems(planted)


def test_holds_reads_whole_words_in_any_letter_case():
    assert holds("Name the Source.", "source")
    assert not holds("resources", "source")
    assert holds("after 15 days", "15")
    assert not holds("after 150 days", "15")
