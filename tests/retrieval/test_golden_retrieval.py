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
    assert any(label.doc_id == "A-DEVICE-B" for q in found for label in q.labels), "scanned page"
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
        for label in q.labels:
            assert label.doc_id in tenant, (q.case_id, label.doc_id)
            assert tenant[label.doc_id] in {q.tenant, "shared"}, (q.case_id, label.doc_id)
            if tenant[label.doc_id] == "shared":
                assert label.doc_id.startswith("X-"), (q.case_id, label.doc_id)
    assert all(
        tenant[label.doc_id] == "tenant-b"
        for q in questions()
        if q.tenant == "tenant-b"
        for label in q.labels
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
    assert all(ids for r in resolved for _, ids in r.groups)
