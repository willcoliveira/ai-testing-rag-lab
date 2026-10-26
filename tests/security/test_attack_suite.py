"""The deterministic attack suite (S7, AG7, AG2, AG3, AG8; how-to 17 step 9): each attack of the
plan's attack table, on the fake echo model and BM25, under the loopback-only egress guard.

For every row:

- **the negative control**: with the row's defences removed, and the layers that stop part of
  it (`also`), the attack lands (the behaviour check of tests/security_support.problems fails),
  so the check is shown able to fail whatever state those other layers are in;
- **each defence alone**: with every other defence of the row removed, that one layer keeps the
  answer clean; removing that layer from the code fails this test, naming the attack and the
  layer;
- **the default guard set**: the answer is clean.

The cases are the security pack's attack cases (datasets/security/attacks.yaml). The checks read
behaviour only: no planted string of the case's features, no citation or conflict id outside the
register, no canary of the other tenant, no run of the system prompt, and no connection off
loopback. Never refusal wording."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient

from raglab.adapters.fake import FakeChat
from raglab.api.app import VersionInfo, create_app
from raglab.core.ports import ChatModel
from raglab.core.types import Chunk, Status
from raglab.generate.pipeline import PROMPT_VERSION, Pipeline
from raglab.generate.prompts import CURRENT
from raglab.guard import s3_guards
from raglab.ingest import scan
from raglab.ingest import security_pack as pack
from raglab.retrieve.bm25 import BM25Retriever
from tests import security_support as s
from tests.generation_support import TOKENS, SpyRetriever
from tests.security_support import egress_none  # noqa: F401  (the fixture every test uses)

pytestmark = [pytest.mark.security, pytest.mark.usefixtures("egress_none")]


@dataclass(frozen=True)
class Row:
    """A row of the attack table: its fixture (the chunks indexed), its cases, its defences (each
    sufficient alone), the layers that stop part of it and are removed in the negative control
    too, the chunks whose links the link guard lets through, and the chat model."""

    attack: str
    fixture: Callable[[], Sequence[Chunk]]
    cases: tuple[str, ...]
    defences: tuple[str, ...]
    also: tuple[str, ...] = ()
    register: Callable[[], Sequence[Chunk]] | None = None
    chat: Callable[[], ChatModel] | None = None

    def pipeline(self, without: Sequence[str] = ()) -> Pipeline:
        register = None if self.register is None else self.register()
        chat = None if self.chat is None else self.chat()
        return s.build(self.fixture(), without, chat=chat, register=register)


ROWS = (
    Row(
        "planted instruction (F-47), a page outside the register",
        lambda: s.clean() + s.pages("T-HIDDEN"),
        ("ATK-F47-1", "ATK-F47-2"),
        ("register", "citations"),
        also=(scan.LAYER, "links", "secrets-pii"),  # each stops the note, not the other chunks
    ),
    Row(
        "planted instruction (F-47) inside a registered document",
        lambda: s.clean() + s.registered_hidden(),
        ("ATK-F47-1",),
        (scan.LAYER, "links", "secrets-pii"),
        register=lambda: s.clean() + s.registered_hidden(),
    ),
    Row(
        "poisoned duplicate (F-48)",
        lambda: s.clean() + s.pages("T-POISON"),
        ("ATK-F48-1", "ATK-F48-2"),
        ("register", "citations"),
    ),
    Row(
        "poisoned duplicate (F-48) claiming a register id",
        lambda: s.clean() + s.claimed_id(),
        ("ATK-F48-1", "ATK-F48-2"),
        ("register", "citations"),
    ),
    Row(
        "fake update page (F-49)",
        lambda: s.clean() + s.pages("T-FAKE"),
        ("ATK-F49-1", "ATK-F49-2"),
        ("register", "citations", "links", "secrets-pii"),
    ),
    Row(
        "prompt extraction (R-20)",
        s.clean,
        ("ATK-R20-1", "ATK-R20-2", "ATK-R20-3"),
        ("injection", "prompt-leak"),
        chat=lambda: FakeChat(s.echo_the_prompt),
    ),
    Row(
        "planted secret and personal details (F-44, F-45)",
        s.clean,
        ("ATK-F44-1", "ATK-F45-1"),
        ("secrets-pii",),
    ),
)
CASES = [pytest.param(row, case, id=f"{case}") for row in ROWS for case in row.cases]
ALONE = [
    pytest.param(row, case, layer, id=f"{case}-{layer}")
    for row in ROWS
    for case in row.cases
    for layer in row.defences
]


def check(row: Row, case: str, without: Sequence[str]) -> list[str]:
    tenant, question, features = s.case_input(case)
    outcome = row.pipeline(without).ask(question, tenant)
    return s.problems(outcome, tenant, features, s.statuses(row.fixture()))


@pytest.mark.parametrize(("row", "case"), CASES)
def test_the_attack_lands_without_its_defences(row: Row, case: str):
    found = check(row, case, (*row.defences, *row.also))
    assert found, (
        f"{row.attack}: {case}: the negative control did not land; the check could not fail"
    )


@pytest.mark.parametrize(("row", "case", "layer"), ALONE)
def test_each_defence_alone_stops_the_attack(row: Row, case: str, layer: str):
    found = check(row, case, [d for d in row.defences if d != layer])
    assert found == [], (
        f"{row.attack}: {case}: with only the {layer} layer the attack lands: {found}"
    )


@pytest.mark.parametrize(("row", "case"), CASES)
def test_the_default_guard_set_stops_the_attack(row: Row, case: str):
    found = check(row, case, ())
    assert found == [], f"{row.attack}: {case}: the default guard set lets it through: {found}"


# the cases whose payload, with S3's guards and no scan, reaches the answer: the fixture delivers
# the attack itself, not only a citation of the page
PAYLOAD = {
    "ATK-F47-1": (0, 1),
    "ATK-F48-1": (2,),
    "ATK-F48-2": (2, 3),
    "ATK-F49-1": (4,),
    "ATK-F49-2": (4,),
    "ATK-F44-1": (6,),
    "ATK-F45-1": (6,),
}


@pytest.mark.parametrize(
    ("row", "case"),
    [pytest.param(ROWS[i], case, id=f"{case}-{i}") for case, rows in PAYLOAD.items() for i in rows],
)
def test_with_s3s_guards_only_the_payload_reaches_the_answer(row: Row, case: str):
    tenant, question, features = s.case_input(case)
    pipeline = Pipeline(
        BM25Retriever(list(row.fixture())),
        FakeChat() if row.chat is None else row.chat(),
        s3_guards(),
        s.K,
    )
    found = s.problems(pipeline.ask(question, tenant), tenant, features, s.statuses(row.fixture()))
    assert any("planted string" in f for f in found), f"{row.attack}: {case}: {found}"


@pytest.mark.parametrize(("row", "case"), CASES)
def test_no_event_holds_what_its_guard_removed(row: Row, case: str):
    """AG4 (how-to 07 step 8): every event the row raises, in every configuration the suite runs,
    names its rule and layer and never quotes the removed text: no answer_must_not_contain string
    and no sentence of a chunk the fixture holds outside the clean pack."""
    tenant, question, _ = s.case_input(case)
    pages = [c for c in row.fixture() if c not in set(s.clean())]
    reasons: list[str] = []
    for without in ((), row.defences, *([d for d in row.defences if d != x] for x in row.defences)):
        outcome = row.pipeline(without).ask(question, tenant)
        reasons += [e.reason for e in (*outcome.events, *outcome.dropped)]
    assert not s.quoted(reasons, pages), f"{row.attack}: {case}: an event quotes removed text"


# ---------------------------------------------------------------- the register filter (AG2)


def test_a_page_outside_the_register_never_reaches_the_prompt_and_the_answer_goes_on():
    chat = FakeChat()
    chunks = s.clean() + s.pages("T-POISON")
    tenant, question, _ = s.case_input("ATK-F48-1")
    outcome = s.build(chunks, chat=chat).ask(question, tenant)
    assert outcome.answer.status is Status.OK
    assert outcome.answer.cited_ids, "the answer goes on from the register's chunks"
    sent = "\n".join(m.content for m in chat.requests[0].messages)
    assert "T-POISON@" not in sent, "a page outside the register reached the prompt"
    assert not [i for i in s.retrieved_ids(outcome) if i.startswith("T-POISON@")]
    reasons = [e.reason for e in outcome.dropped]
    assert reasons
    assert all("T-POISON" in r and "register-membership" in r for r in reasons)
    assert not s.quoted(reasons, s.pages("T-POISON")), "an event quotes what it removed"


def test_a_page_whose_front_matter_claims_a_register_id_and_current_is_still_dropped():
    page = s.claimed_id()
    assert {c.doc_id for c in page} == {s.CLAIMED_ID}
    assert {c.status for c in page} == {"unregistered"}
    tenant, question, _ = s.case_input("ATK-F48-1")
    outcome = s.build(s.clean() + page).ask(question, tenant)
    assert [e.reason for e in outcome.dropped] == [
        f"rule register-membership: 1 chunk(s) of {s.CLAIMED_ID} left out, a document outside "
        "the register"
    ]
    assert all(r.chunk.status != "unregistered" for r in outcome.retrieved)


def test_an_attack_page_exposes_its_text_tenant_claimed_id_and_version_only():
    """What an attack run exposes (S7): the page's own first heading as its title, kind and
    status unregistered; the front matter's title, kind, status and test_material never."""
    for chunk in s.pages():
        assert chunk.status == chunk.kind == "unregistered"
        assert "test material" not in chunk.title.casefold()
        assert chunk.version in ("1.0", "2.1")


# ---------------------------------------------------------------- nothing is sent out (AG8)


def test_with_the_link_guard_alone_the_planted_link_is_never_answered():
    """The plan's row "nothing is sent out": T-HIDDEN's text inside a registered document, the
    instruction scan and the personal-details guard removed, the link guard alone."""
    row = ROWS[1]
    tenant, question, _ = s.case_input("ATK-F47-1")
    outcome = row.pipeline([scan.LAYER, "secrets-pii"]).ask(question, tenant)
    assert (outcome.answer.status, outcome.answer.text) == (Status.BLOCKED, "")
    assert [e.guard for e in outcome.events] == ["links"]


# ---------------------------------------------------------------- two tenants (R-13, R-16)


@pytest.mark.parametrize("case", ["ATK-TEN-1", "ATK-TEN-2"])
def test_two_tenants_a_broken_store_filter_without_the_tenant_guard_leaks(case: str):
    tenant, question, features = s.case_input(case)
    outcome = s.build(s.clean(), ["tenant"], retriever=s.LeakyRetriever(s.clean())).ask(
        question, tenant
    )
    found = s.problems(outcome, tenant, features, s.statuses(s.clean()))
    assert any("canary" in f for f in found), (
        f"two tenants: {case}: the negative control did not land"
    )


@pytest.mark.parametrize("case", ["ATK-TEN-1", "ATK-TEN-2"])
def test_two_tenants_the_store_filter_alone_keeps_the_other_tenant_out(case: str):
    tenant, question, features = s.case_input(case)
    outcome = s.build(s.clean(), ["tenant"]).ask(question, tenant)
    found = s.problems(outcome, tenant, features, s.statuses(s.clean()))
    assert found == [], f"two tenants: {case}: with the store's tenant filter alone: {found}"


@pytest.mark.parametrize("case", ["ATK-TEN-1", "ATK-TEN-2"])
def test_two_tenants_the_tenant_guard_alone_withholds_a_leaked_chunk(case: str):
    tenant, question, features = s.case_input(case)
    outcome = s.build(s.clean(), retriever=s.LeakyRetriever(s.clean())).ask(question, tenant)
    assert outcome.answer.status is Status.BLOCKED, f"two tenants: {case}: the tenant guard"
    assert [e.guard for e in outcome.events] == ["tenant"]
    assert s.problems(outcome, tenant, features, s.statuses(s.clean())) == []


# ---------------------------------------------------------------- tenant id spoofing (R-21)

INFO = VersionInfo("0.0.1", "0" * 40, PROMPT_VERSION, "fake", "fake-echo", "fake", "fake")
A_ONLY = {"Authorization": "Bearer tenant-a-only"}


def spoofing(without: Sequence[str]) -> tuple[TestClient, SpyRetriever]:
    spy = SpyRetriever(BM25Retriever(list(s.clean())))
    pipeline = Pipeline(spy, FakeChat(), s.guards_without(without, s.clean()), s.K)
    return TestClient(create_app(pipeline, INFO, TOKENS)), spy


def test_tenant_spoofing_on_the_api_is_403_and_never_retrieved():
    api, spy = spoofing(())
    body = {"tenant": "tenant-b", "question": "How many characters must a password have?"}
    response = api.post("/ask", json=body, headers=A_ONLY)
    assert (response.status_code, spy.calls) == (403, 0)


def test_tenant_spoofing_lands_without_the_tenant_guard():
    api, spy = spoofing(("tenant",))
    body = {"tenant": "tenant-b", "question": "How many characters must a password have?"}
    response = api.post("/ask", json=body, headers=A_ONLY)
    assert (response.status_code, spy.calls) == (200, 1), "the negative control did not land"
    assert all(c["chunk_id"].startswith(("B-", "X-")) for c in response.json()["citations"])


# ---------------------------------------------------------------- F-46 still answered (R-19)


@pytest.mark.parametrize(
    ("tenant", "question", "team"),
    [
        (
            "tenant-a",
            "How do I report a compromised account to the Security Operations Centre, by email "
            "or phone?",
            "Halvenroot SOC",
        ),
        (
            "tenant-a",
            "How do I contact the IT Service Desk by email or phone?",
            "Halvenroot IT Service Desk",
        ),
        ("tenant-b", "How do I contact Mirrowfen IT Support?", "Mirrowfen IT Support"),
    ],
)
def test_the_published_team_contacts_are_still_answered(tenant: str, question: str, team: str):
    """F-46 (the SOC's contacts, A-IR section 3.2) and the other team contacts: retrieved, echoed
    and answered, never withheld by the personal-details guard."""
    contact = pack.sources(s.ROOT, CURRENT.SYSTEM).contacts[team]
    outcome = s.build(s.clean()).ask(question, tenant)
    assert outcome.answer.status is Status.OK, [e.reason for e in outcome.events]
    assert contact["address"] in outcome.answer.text
