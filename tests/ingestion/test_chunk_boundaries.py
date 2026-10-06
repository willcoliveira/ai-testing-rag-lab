"""AC5: the planted rule and its exception (F-15: A-MFA 4.1, paragraphs 1 and 2) share a chunk at
the default settings, and when they do not, the failure names the boundary that splits them.
Also: every answer-key feature keeps its cited values together at the default settings, and the
chunker's rules (sections, budget, overlap, oversize units, ids) hold on small documents."""

import pytest

from raglab.chunk.sections import INTRO, ChunkSettings, SectionChunker, empty_sections
from raglab.core.types import Block, Chunk, Document, DocumentMeta, Page
from tests.conftest import load_script
from tests.ingestion_support import answer_key, default_inventory, parsed

pytestmark = pytest.mark.ingestion


def rule_and_exception() -> tuple[str, str, str, str]:
    """(doc, section, rule, exception) of F-15, from the answer key."""
    feature = next(f for f in answer_key()["features"] if f["id"] == "F-15")
    by_paragraph = {loc["paragraph"]: loc for loc in feature["locations"]}
    rule, exception = by_paragraph[1], by_paragraph[2]
    assert (rule["doc"], rule["section"]) == (exception["doc"], exception["section"])
    return rule["doc"], str(rule["section"]), rule["values"][0], exception["values"][0]


def boundary_problem(chunks: list[Chunk]) -> str | None:
    """None when one chunk holds the rule and its exception; else which boundary splits them."""
    doc, section, rule, exception = rule_and_exception()
    found = [c for c in chunks if c.doc_id == doc and c.section_id == section]
    if any(rule in c.text and exception in c.text for c in found):
        return None
    with_rule = next(c for c in found if rule in c.text)
    with_exception = next(c for c in found if exception in c.text)
    return (
        f"{doc} {section}: the rule (paragraph 1, {rule!r}) ends chunk {with_rule.chunk_id} "
        f"at character {with_rule.char_end}, and the exception (paragraph 2, {exception!r}) "
        f"starts chunk {with_exception.chunk_id} at character {with_exception.char_start}: "
        f"the boundary between {with_rule.chunk_id} and {with_exception.chunk_id} splits them"
    )


def chunks_at(settings: ChunkSettings) -> list[Chunk]:
    return SectionChunker(settings).chunk(parsed(rule_and_exception()[0]))


def test_rule_and_exception_share_a_chunk_at_default_settings():
    problem = boundary_problem(chunks_at(ChunkSettings()))
    assert problem is None, problem


def test_a_budget_that_splits_them_names_the_boundary():
    """The positive control: at 300 characters section 4.1 (348 with its heading) splits."""
    problem = boundary_problem(chunks_at(ChunkSettings(chunk_size=300)))
    assert problem is not None
    assert "boundary between A-MFA@1.0/4.1/1 and A-MFA@1.0/4.1/2" in problem
    assert "Administrators must always use MFA" in problem
    assert "The only exception is the break-glass accounts" in problem


@pytest.mark.ocr
def test_every_feature_keeps_its_cited_values_in_one_chunk_at_default_settings():
    experiment = load_script("chunk_experiment")
    splits = experiment.split_groups(default_inventory().chunks, answer_key())
    assert splits == [], "\n".join(str(s) for s in splits)


def test_a_table_split_from_its_header_is_reported():
    experiment = load_script("chunk_experiment")
    chunks = SectionChunker(ChunkSettings(chunk_size=600)).chunk(parsed("A-EXC"))
    splits = [str(s) for s in experiment.split_groups(tuple(chunks), answer_key())]
    assert any(s.startswith("F-16 A-EXC 5.1:") for s in splits), splits


# ---------------------------------------------------------------- the chunker on small documents


def document(*blocks: Block, pages: list[int | None] | None = None) -> Document:
    meta = DocumentMeta(
        "A-X", "Doc", "1.0", "approved", "tenant-a", "company", "CC-BY-4.0", "x.md", "md"
    )
    numbers = pages or [None] * len(blocks)
    grouped: dict[int | None, list[Block]] = {}
    for block, number in zip(blocks, numbers, strict=True):
        grouped.setdefault(number, []).append(block)
    return Document(meta, tuple(Page(n, tuple(b)) for n, b in grouped.items()))


def h(text: str, level: int = 2) -> Block:
    return Block("heading", text, level=level)


def p(text: str) -> Block:
    return Block("paragraph", text)


def chunk(doc: Document, size: int = 1200, overlap: int = 1) -> list[Chunk]:
    return SectionChunker(ChunkSettings(size, overlap)).chunk(doc)


@pytest.mark.unit
def test_sections_split_and_a_heading_only_parent_gives_no_chunk():
    doc = document(h("Doc", 1), p("Intro text."), h("4 Rules"), h("4.1 Length", 3), p("Long."))
    chunks = chunk(doc)
    assert [(c.chunk_id, c.section_id, c.section_title) for c in chunks] == [
        ("A-X@1.0/intro/1", INTRO, "Doc"),
        ("A-X@1.0/4.1/1", "4.1", "Length"),
    ]
    assert chunks[0].text == "Doc\n\nIntro text."
    assert chunks[1].text == "4.1 Length\n\nLong."


@pytest.mark.unit
def test_packing_respects_the_budget_and_overlaps_one_paragraph():
    a, b, c = "a" * 40, "b" * 40, "c" * 40
    doc = document(h("1 S"), p(a), p(b), p(c))
    chunks = chunk(doc, size=90)
    assert [x.text for x in chunks] == [f"1 S\n\n{a}\n\n{b}", f"{b}\n\n{c}"]
    assert all(len(x.text) <= 90 for x in chunks)
    assert [x.text for x in chunk(doc, size=90, overlap=0)] == [f"1 S\n\n{a}\n\n{b}", c]
    # the heading travels with the first paragraph, so that unit is too long to repeat here
    assert [x.text for x in chunk(doc, size=85)] == [f"1 S\n\n{a}", f"{b}\n\n{c}"]


@pytest.mark.unit
def test_overlap_is_dropped_when_it_would_not_fit_beside_a_new_paragraph():
    a, b = "a" * 60, "b" * 60
    chunks = chunk(document(h("1 S"), p(a), p(b)), size=100)
    assert [x.text for x in chunks] == [f"1 S\n\n{a}", b]


@pytest.mark.unit
def test_an_oversize_paragraph_splits_between_sentences_and_a_table_between_rows():
    sentences = " ".join(f"Sentence {n} is here." for n in range(10))
    table = Block("table", "\n".join(f"| row {n} | value {n} |" for n in range(10)))
    chunks = chunk(document(h("1 S"), p(sentences), h("2 T"), table), size=60, overlap=0)
    assert all(len(c.text) <= 60 for c in chunks)
    first = [c.text for c in chunks if c.section_id == "1"]
    assert first[0].startswith("1 S\n\nSentence 0 is here.")
    assert all(t.endswith(".") for t in first)
    rows = [c.text for c in chunks if c.section_id == "2"]
    assert all(line.startswith("| row") for t in rows[1:] for line in t.split("\n"))
    assert "".join(t.replace("\n", "") for t in rows).count("| row") == 10


@pytest.mark.unit
def test_a_single_sentence_longer_than_the_budget_is_kept_whole():
    long = "x" * 80 + "."
    chunks = chunk(document(h("1 S"), p(long)), size=50)
    assert [c.text for c in chunks] == [f"1 S\n\n{long}"]


@pytest.mark.unit
def test_chunks_never_cross_a_section_and_record_their_pages():
    doc = document(h("1 A"), p("one"), p("two"), h("2 B"), p("three"), pages=[1, 1, 2, 2, 2])
    chunks = chunk(doc, size=1200)
    assert [(c.section_id, c.page, c.page_end) for c in chunks] == [("1", 1, 2), ("2", 2, 2)]
    text = doc.text()
    assert all(text[c.char_start : c.char_end] == c.text for c in chunks)


@pytest.mark.unit
def test_repeated_section_ids_still_give_unique_chunk_ids():
    doc = document(h("1 A"), p("one"), h("1 A"), p("again"))
    assert [c.chunk_id for c in chunk(doc)] == ["A-X@1.0/1/1", "A-X@1.0/1~2/1"]


@pytest.mark.unit
@pytest.mark.parametrize(("size", "overlap"), [(0, 1), (-5, 1), (100, -1)])
def test_invalid_settings_are_refused(size, overlap):
    with pytest.raises(ValueError, match="must be"):
        ChunkSettings(size, overlap)


# ---------------------------------------------------------------- empty sections (S1b decision)


def test_an_empty_leaf_section_is_reported_and_a_parent_heading_is_not():
    doc = document(
        h("Doc", level=1),
        p("Intro."),
        h("1 First"),
        p("One."),
        h("2 Reserved"),
        h("3 Parent"),
        h("3.1 Child", level=3),
        p("Child text."),
        h("4 Trailing"),
    )
    assert empty_sections(doc) == ["2", "4"]


@pytest.mark.ocr
def test_the_project_pack_has_no_empty_section():
    """User decision (S1b): empty sections are reported, and fail on our own pack."""
    assert default_inventory().empty_sections == ()
