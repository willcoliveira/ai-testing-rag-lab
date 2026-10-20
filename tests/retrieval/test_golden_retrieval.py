"""AC2: the golden file's retrieval questions: about 30, each with its fields, split dev and test
by kind, every planted retrieval kind covered, both tenants, tenant B questions labelling only
tenant B or shared external documents, and every label resolves to existing chunks the asker may
see, at the default chunk size and at 600. The loader and the resolver are tested on small inputs
and on the real file: a label that goes missing fails, naming the question."""

import json
import re
from collections import Counter

import pytest

from raglab.chunk.sections import ChunkSettings
from raglab.evals import golden
from raglab.ingest import pipeline, register
from tests.conftest import ROOT
from tests.corpus_text import answer_key
from tests.ingestion_support import default_inventory
from tests.retrieval_support import PACK

pytestmark = pytest.mark.retrieval
DATASET = ROOT / "datasets" / "golden.v1.jsonl"
# the retrieval kinds of datasets/DATASHEET.md ("Mix by kind and split")
QUESTION_KINDS = {
    "plain-rule",
    "table-only",
    "cross-reference",
    "glossary-dependent",
    "multi-hop",
    "scanned-page",
    "version-conflict",
    "external-conflict",
    "exception-status",
    "tenant-b",
    "paraphrase",
    "misspelling",
}


def line(**changes) -> str:
    row = {
        "id": "Q1",
        "kind": "retrieval",
        "split": "dev",
        "tenant": "tenant-a",
        "question": "How long?",
        "relevant": [{"doc_id": "A-PWD", "section_id": "4.1"}],
        "feature_ids": ["F-01"],
    }
    row.update(changes)
    return json.dumps({k: v for k, v in row.items() if v is not None})


@pytest.mark.unit
def test_a_question_line_is_read_with_its_extra_fields():
    q = golden.parse_line(line(question_kind="plain-rule"), "g:1")
    assert (q.case_id, q.kind, q.split, q.tenant) == ("Q1", "retrieval", "dev", "tenant-a")
    assert q.labels == (golden.Label("A-PWD", "4.1"),)
    assert q.question_kind == "plain-rule"
    assert q.extra["feature_ids"] == ["F-01"]


@pytest.mark.unit
@pytest.mark.parametrize(
    ("changes", "match"),
    [
        ({"id": ""}, "id must be"),
        ({"kind": "judged"}, "kind"),
        ({"split": "train"}, "split"),
        ({"tenant": "shared"}, "tenant"),
        ({"tenant": None}, "tenant must be"),
        ({"relevant": []}, "at least one relevant section"),
        ({"relevant": [{"doc_id": "A-PWD"}]}, "section_id must be"),
        ({"relevant": "A-PWD 4.1"}, "list of sections"),
        (
            {"relevant": [{"doc_id": "A", "section_id": "1"}, {"doc_id": "A", "section_id": "1"}]},
            "listed twice",
        ),
    ],
)
def test_a_wrong_question_is_refused(changes, match):
    with pytest.raises(golden.DatasetError, match=match):
        golden.parse_line(line(**changes), "g:1")


# S2 judge D2: once the id is read, every error names the question as well as the line, so a
# retrieval question without its `relevant` field is reported as R-Qnn, like a label that does not
# resolve (golden.resolve).
@pytest.mark.unit
@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"relevant": None}, "g:1 (Q1): a retrieval question needs at least one relevant section"),
        ({"tenant": "shared"}, "g:1 (Q1): tenant 'shared' is not one of"),
        ({"question": " "}, "g:1 (Q1): question must be a non-empty string"),
        ({"relevant": [{"doc_id": "A-PWD"}]}, "g:1 (Q1): section_id must be"),
    ],
)
def test_an_error_after_the_id_names_the_question(changes, message):
    with pytest.raises(golden.DatasetError) as error:
        golden.parse_line(line(**changes), "g:1")
    assert str(error.value).startswith(message), str(error.value)


@pytest.mark.unit
def test_a_committed_question_without_relevant_is_named_by_its_id(tmp_path):
    rows = DATASET.read_text(encoding="utf-8").splitlines()
    number = next(n for n, text in enumerate(rows) if json.loads(text)["id"] == "R-Q24")
    row = json.loads(rows[number])
    del row["relevant"]
    rows[number] = json.dumps(row)
    path = tmp_path / DATASET.name
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    with pytest.raises(golden.DatasetError) as error:
        golden.load(path)
    assert str(error.value) == (
        f"golden.v1.jsonl:{number + 1} (R-Q24): "
        "a retrieval question needs at least one relevant section"
    )


@pytest.mark.unit
def test_load_refuses_a_repeated_id_and_bad_json(tmp_path):
    path = tmp_path / "g.jsonl"
    path.write_text(line() + "\n\n" + line() + "\n")
    with pytest.raises(golden.DatasetError, match=r"g\.jsonl:3: id Q1 is used twice"):
        golden.load(path)
    path.write_text("{not json\n")
    with pytest.raises(golden.DatasetError, match="not JSON"):
        golden.load(path)


@pytest.mark.unit
def test_labels_resolve_to_every_chunk_of_their_section():
    questions = [golden.parse_line(line(), "g:1")]
    [resolved] = golden.resolve(questions, PACK)
    assert resolved.label_sets() == [frozenset({"A-PWD@1.0/4.1/1", "A-PWD@1.0/4.1/2"})]


@pytest.mark.unit
def test_a_group_is_read_as_one_entry_of_several_sections():
    """S4: `{"any_of": [...]}` is a label group; its first member is the primary section."""
    q = golden.parse_line(
        line(
            relevant=[
                {
                    "any_of": [
                        {"doc_id": "A-PWD", "section_id": "4.1"},
                        {"doc_id": "X-NIST", "section_id": "3.1"},
                    ]
                },
                {"doc_id": "A-PWD", "section_id": "5"},
            ]
        ),
        "g:1",
    )
    group = golden.Group((golden.Label("A-PWD", "4.1"), golden.Label("X-NIST", "3.1")))
    assert q.labels == (group, golden.Label("A-PWD", "5"))
    assert q.sections() == (*group.members, golden.Label("A-PWD", "5"))


@pytest.mark.unit
@pytest.mark.parametrize(
    ("relevant", "match"),
    [
        ([{"any_of": [{"doc_id": "A-PWD", "section_id": "4.1"}]}], "at least two sections"),
        ([{"any_of": "A-PWD 4.1"}], "nothing else"),
        (
            [
                {
                    "any_of": [
                        {"doc_id": "A-PWD", "section_id": "4.1"},
                        {"doc_id": "A-PWD", "section_id": "5"},
                    ],
                    "doc_id": "A-PWD",
                }
            ],
            "nothing else",
        ),
        (
            [
                {
                    "any_of": [
                        {"doc_id": "A-PWD", "section_id": "4.1"},
                        {"doc_id": "A-PWD", "section_id": "5"},
                    ]
                },
                {"doc_id": "A-PWD", "section_id": "5"},
            ],
            "listed twice",
        ),
        ([{"any_of": [{"doc_id": "A-PWD"}, {"doc_id": "A-PWD", "section_id": "5"}]}], "section_id"),
    ],
)
def test_a_wrong_group_is_refused(relevant, match):
    with pytest.raises(golden.DatasetError, match=match):
        golden.parse_line(line(relevant=relevant), "g:1")


@pytest.mark.unit
def test_a_section_may_sit_in_several_groups():
    """A FAQ entry that restates two rules is a member of the group of each (FAQ Q3 with A-MFA 3.1
    and with 3.2 in R-Q14): one retrieved chunk of it finds both, and it is listed once among the
    question's sections."""
    faq = {"doc_id": "X-NIST", "section_id": "3.1"}
    q = golden.parse_line(
        line(
            relevant=[
                {"any_of": [{"doc_id": "A-PWD", "section_id": "4.1"}, faq]},
                {"any_of": [{"doc_id": "A-PWD", "section_id": "5"}, faq]},
            ]
        ),
        "g:1",
    )
    assert q.sections() == (
        golden.Label("A-PWD", "4.1"),
        golden.Label("X-NIST", "3.1"),
        golden.Label("A-PWD", "5"),
    )
    [resolved] = golden.resolve([q], PACK)
    labels = resolved.label_sets()
    assert all("X-NIST@4/3.1/1" in s for s in labels)
    from raglab.evals import metrics

    assert metrics.recall_at_k(["X-NIST@4/3.1/1"], labels, 5) == 1.0


@pytest.mark.unit
def test_a_group_resolves_to_one_chunk_set_and_a_record_label_with_its_members():
    """A group is one thing to find: one label set, every member's chunks together; the record
    keeps the primary's ids, the union and each member with its own chunks."""
    q = golden.parse_line(
        line(
            relevant=[
                {
                    "any_of": [
                        {"doc_id": "A-PWD", "section_id": "4.1"},
                        {"doc_id": "X-NIST", "section_id": "3.1"},
                    ]
                }
            ]
        ),
        "g:1",
    )
    [resolved] = golden.resolve([q], PACK)
    union = ("A-PWD@1.0/4.1/1", "A-PWD@1.0/4.1/2", "X-NIST@4/3.1/1")
    assert resolved.label_sets() == [frozenset(union)]
    assert resolved.labels_json({"X-NIST@4/3.1/1"}) == [
        {
            "doc_id": "A-PWD",
            "section_id": "4.1",
            "chunk_ids": list(union),
            "found": True,
            "any_of": [
                {"doc_id": "A-PWD", "section_id": "4.1", "chunk_ids": list(union[:2])},
                {"doc_id": "X-NIST", "section_id": "3.1", "chunk_ids": [union[2]]},
            ],
        }
    ]
    plain = golden.parse_line(line(), "g:2")
    [one] = golden.resolve([plain], PACK)
    assert one.labels_json(set()) == [  # a section alone keeps the S2 record shape
        {
            "doc_id": "A-PWD",
            "section_id": "4.1",
            "chunk_ids": ["A-PWD@1.0/4.1/1", "A-PWD@1.0/4.1/2"],
            "found": False,
        }
    ]


@pytest.mark.unit
def test_a_label_that_goes_missing_or_crosses_tenants_fails():
    missing = golden.parse_line(line(relevant=[{"doc_id": "A-PWD", "section_id": "9"}]), "g:1")
    other = golden.parse_line(
        line(id="Q2", relevant=[{"doc_id": "B-PWD", "section_id": "3"}]), "g:2"
    )
    with pytest.raises(golden.LabelError) as error:
        golden.resolve([missing, other], PACK)
    assert "Q1: A-PWD section 9 has no chunk" in str(error.value)
    assert "Q2: B-PWD is tenant-b, which tenant-a cannot see" in str(error.value)


# ---------------------------------------------------------------- the committed golden file


def questions() -> list[golden.Question]:
    return golden.select(golden.load(DATASET), "retrieval", "all")


def test_about_thirty_retrieval_questions_in_both_splits_and_tenants():
    found = questions()
    assert 25 <= len(found) <= 40, len(found)
    splits = {q.split for q in found}
    assert splits == {"dev", "test"}
    assert {q.tenant for q in found} == {"tenant-a", "tenant-b"}
    dev = [q for q in found if q.split == "dev"]
    assert len(dev) >= len(found) / 2, "most questions are in dev"


def test_every_planted_retrieval_kind_is_covered():
    """The plan's kinds: plain, table-only, cross-reference, glossary, multi-hop (two labels),
    the scanned page, version and external conflicts, and tenant B."""
    found = questions()
    kinds = {q.question_kind for q in found}
    for kind in ("table-only", "cross-reference", "glossary", "multi-hop"):
        assert any(kind in (k or "") for k in kinds), (kind, kinds)
    assert any(len(q.labels) >= 2 for q in found if "multi-hop" in (q.question_kind or ""))
    assert any(s.doc_id == "A-DEVICE-B" for q in found for s in q.sections()), "scanned page"
    assert any("version" in (q.question_kind or "") for q in found)
    assert any("external" in (q.question_kind or "") for q in found)
    assert any(q.tenant == "tenant-b" for q in found)


def test_every_question_has_its_fields_and_known_features():
    """Schema: an id R-Qnn, a known question_kind, and feature ids that exist in the answer key."""
    features = {f["id"] for f in answer_key()["features"]}  # type: ignore[index]
    for q in questions():
        assert re.fullmatch(r"R-Q\d{2}", q.case_id), q.case_id
        assert q.question_kind in QUESTION_KINDS, (q.case_id, q.question_kind)
        ids = q.extra.get("feature_ids")
        assert isinstance(ids, list), (q.case_id, ids)
        assert ids, q.case_id
        assert set(ids) <= features, (q.case_id, set(ids) - features)
        assert set(q.extra) <= {"question_kind", "feature_ids"}, (q.case_id, set(q.extra))


def test_the_split_is_stratified_by_kind():
    """Every kind has questions in dev and in test, and one in test (datasheet: three split 2/1,
    two split 1/1, tenant B's four split 3/1), so test keeps one of each kind for nightly and
    release while dev holds the rest."""
    found = questions()
    total = Counter(q.question_kind for q in found)
    test = Counter(q.question_kind for q in found if q.split == "test")
    assert set(total) == QUESTION_KINDS
    for kind, n in total.items():
        assert test[kind] == 1, (kind, test[kind], n)
        assert n - test[kind] >= 1, (kind, "no dev question")


def test_tenant_b_questions_label_only_tenant_b_or_shared_documents():
    """A tenant B question labels only tenant B documents or the shared external excerpts, and a
    tenant A question only tenant A or shared ones, read from the register (the document's own
    text is never the register)."""
    tenant = {e.doc_id: e.tenant for e in register.read(ROOT)}
    for q in questions():
        for label in q.sections():  # every section, the members of a group included (S4)
            assert label.doc_id in tenant, (q.case_id, label.doc_id)
            assert tenant[label.doc_id] in {q.tenant, "shared"}, (q.case_id, label.doc_id)
            if tenant[label.doc_id] == "shared":
                assert label.doc_id.startswith("X-"), (q.case_id, label.doc_id)
    assert all(
        tenant[label.doc_id] == "tenant-b"
        for q in questions()
        if q.tenant == "tenant-b"
        for label in q.sections()
    )


@pytest.mark.ocr
def test_a_section_missing_from_the_real_inventory_fails_naming_its_questions():
    """Labels are resolved at run time: if a re-chunk or a corpus edit drops a labelled section,
    the run stops and names every question that labels it."""
    chunks = [
        c for c in default_inventory().chunks if (c.doc_id, c.section_id) != ("A-GLOSS", "10")
    ]
    with pytest.raises(golden.LabelError) as error:
        golden.resolve(questions(), chunks)
    message = str(error.value)
    assert "R-Q10: A-GLOSS section 10 has no chunk" in message
    assert "R-Q12: A-GLOSS section 10 has no chunk" in message
    assert message.count("has no chunk") == 2


@pytest.mark.ocr
@pytest.mark.parametrize("chunk_size", [1200, 600])
def test_every_label_resolves_to_existing_chunks(chunk_size):
    inventory = (
        default_inventory()
        if chunk_size == 1200
        else pipeline.ingest(ROOT, ChunkSettings(chunk_size=chunk_size))
    )
    resolved = golden.resolve(questions(), list(inventory.chunks))
    assert all(ids for r in resolved for found in r.entries for _, ids in found.sections)


# The datasheet: "All but one label is a location of one of its question's features", the
# exception being R-Q09's pointer section. A label outside its features' locations (the S2 review
# weighed adding Device Policy 6.2 to R-Q25) fails here until the datasheet and the answer key
# agree on it. S4 (AC2): the guard reads every member of a label group too, and no member may be
# an exception: a group member is always an answer-key location of the question's features.
LABELS_OUTSIDE_THE_FEATURES = {("R-Q09", "A-LIFE", "5.4")}


def labels_outside_their_features(found: list[golden.Question]) -> set[tuple[str, str, str]]:
    """(question, document, section) of every labelled section, group members included, that is
    not a location of one of the question's features in the answer key."""
    features = {f["id"]: f for f in answer_key()["features"]}  # type: ignore[index]
    outside: set[tuple[str, str, str]] = set()
    for q in found:
        locations = {
            (str(location["doc"]), str(location["section"]))
            for feature in q.extra["feature_ids"]  # type: ignore[union-attr]
            for location in features[feature]["locations"]
        }
        outside |= {
            (q.case_id, label.doc_id, label.section_id)
            for label in q.sections()
            if (label.doc_id, label.section_id) not in locations
        }
    return outside


def group_members(found: list[golden.Question]) -> set[tuple[str, str, str]]:
    return {
        (q.case_id, s.doc_id, s.section_id)
        for q in found
        for entry in q.labels
        if isinstance(entry, golden.Group)
        for s in entry.members
    }


def test_every_label_is_a_location_of_one_of_its_features():
    found = questions()
    assert labels_outside_their_features(found) == LABELS_OUTSIDE_THE_FEATURES
    assert not group_members(found) & LABELS_OUTSIDE_THE_FEATURES, "a group member is no location"


@pytest.mark.unit
def test_the_location_guard_reads_every_member_of_a_group():
    """AC2: a group member that is no answer-key location of the question's features is caught
    by the guard; the same group with members that are locations passes."""
    primary = {"doc_id": "A-PWD-V2", "section_id": "4.1"}
    faq = {"doc_id": "A-FAQ", "section_id": "Q1"}  # F-53's restatement of F-01's value
    features = ["F-01", "F-53"]
    good = golden.parse_line(
        line(id="G1", relevant=[{"any_of": [primary, faq]}], feature_ids=features), "g:1"
    )
    assert labels_outside_their_features([good]) == set()
    stray = {"doc_id": "A-FAQ", "section_id": "Q12"}  # a location of neither feature
    bad = golden.parse_line(
        line(id="G2", relevant=[{"any_of": [primary, stray]}], feature_ids=features), "g:2"
    )
    assert labels_outside_their_features([bad]) == {("G2", "A-FAQ", "Q12")}
    assert group_members([bad]) == {("G2", "A-PWD-V2", "4.1"), ("G2", "A-FAQ", "Q12")}


def datasheet() -> str:
    return re.sub(r"\s+", " ", (ROOT / "datasets" / "DATASHEET.md").read_text(encoding="utf-8"))


# S2 review findings S2-L2 and S2-L4: the label scope of R-Q14 and R-Q25 is stated, with its cost.
# Since v1.1 (S4, D2) Device Policy 6.2 is an F-17 location and a member of A-EXC 4.2's group, so
# R-Q25 finds that rule once whichever statement is retrieved; v1's sentence is history.
def test_the_datasheet_states_the_label_scope_the_review_raised():
    text = datasheet()
    assert "Labels follow the feature's reference answer." in text
    assert "R-Q14 asks which second-factor methods" in text
    assert "it labels A-MFA 3.2 (the factors that are not approved)" in text
    assert "In v1 it was not labelled for R-Q25" in text
    assert "it is a member of A-EXC 4.2's group" in text
    assert (
        "the Policy Exceptions Process section that gives the register's effect or expiry" in text
    )
    by_id = {q.case_id: q for q in questions()}
    assert golden.Label("A-MFA", "3.2") in by_id["R-Q14"].sections()
    [group] = [
        e
        for e in by_id["R-Q25"].labels
        if isinstance(e, golden.Group) and golden.Label("A-DEVICE", "6.2") in e.members
    ]
    assert group.members[0] == golden.Label("A-EXC", "4.2")
