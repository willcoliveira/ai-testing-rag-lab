"""AC2: every register document parses to the text a reader sees, and that text holds every value
the answer key cites for the document, at its cited section, paragraph, table cell and page.

The PDF and the HTML export are also compared, block by block and page by page, with the
Markdown they were rendered from: the tests read the Markdown as the oracle; ingestion never does.
The scanned page (OCR) is compared with its ground truth by character error rate in test_ocr.py.
"""

import re

import pytest

from raglab.core.text import normalise_space
from raglab.ingest import markdown
from raglab.ingest.frontmatter import split
from tests.conftest import ROOT
from tests.ingestion_support import (
    answer_key,
    doc_params,
    entries,
    locations,
    parsed,
    section_body,
    section_pages,
    table_cell,
)

pytestmark = pytest.mark.ingestion

PAGE_MARKER = re.compile(r"^<!-- page: (\d+) -->$", flags=re.M)


def source_body(rel: str) -> str:
    return split((ROOT / rel).read_text(encoding="utf-8"), rel)[1]


def source_pages(rel: str) -> dict[int, list]:
    """The Markdown source's blocks per page marker (the oracle for the PDF's pages)."""
    parts = PAGE_MARKER.split(source_body(rel))
    return {int(n): markdown.blocks(text) for n, text in zip(parts[1::2], parts[2::2], strict=True)}


@pytest.mark.parametrize("doc_id", doc_params())
def test_document_parses_to_text_with_a_title_and_sections(doc_id):
    document = parsed(doc_id)
    entry = entries()[doc_id]
    assert document.meta.format == entry.format
    assert document.text().strip(), f"{doc_id}: no text"
    blocks = [b for p in document.pages for b in p.blocks]
    assert (blocks[0].kind, blocks[0].level) == ("heading", 1), f"{doc_id}: no title first"
    assert any(b.kind == "heading" and b.level >= 2 for b in blocks), f"{doc_id}: no section"
    pages = [p.number for p in document.pages]
    if entry.format in ("pdf", "png"):
        assert pages == list(range(1, len(pages) + 1)), f"{doc_id}: print pages {pages}"
    else:
        assert pages == [None]


@pytest.mark.parametrize("doc_id", doc_params())
def test_every_cited_value_is_in_the_extracted_text_at_its_place(doc_id):
    document = parsed(doc_id)
    for feature, loc in locations(doc_id):
        where = f"{feature} {doc_id} section {loc['section']}"
        heading, body = section_body(document, str(loc["section"]))
        section_text = normalise_space(" ".join(b.text for b in [heading, *body] if b))
        if "page" in loc:
            assert section_pages(document, str(loc["section"])) == {loc["page"]}, where
        for value in loc.get("values", []):
            if "table" in loc:
                table = loc["table"]
                cell = table_cell(body, table["caption"], table["row"], table["column"])
                assert value in cell, f"{where}: {table} is {cell!r}, not {value!r}"
            elif "paragraph" in loc:
                paragraph = body[loc["paragraph"] - 1].text
                assert normalise_space(value) in normalise_space(paragraph), (
                    f"{where} paragraph {loc['paragraph']}: {value!r} not in {paragraph!r}"
                )
            else:
                assert normalise_space(value) in section_text, f"{where}: {value!r} missing"


def test_every_cited_document_is_in_the_register_or_an_attack_file():
    cited = {loc["doc"] for f in answer_key()["features"] for loc in f.get("locations", [])}
    attacks = {"T-HIDDEN", "T-POISON", "T-FAKE"}
    assert cited - attacks <= set(entries()), cited - attacks - set(entries())


def test_pdf_pages_parse_to_the_blocks_of_their_source_pages():
    rel = entries()["A-PWD-V2"].path
    document = parsed("A-PWD-V2")
    expected = source_pages(rel.removesuffix(".pdf") + ".md")
    assert [p.number for p in document.pages] == sorted(expected) == [1, 2, 3, 4]
    for page in document.pages:
        assert page.number is not None
        assert list(page.blocks) == expected[page.number], f"page {page.number} differs"


def test_pdf_table_is_read_as_rows():
    """The table-only rule survives: each row of Table 1 is one row, cells in their columns
    (pypdf's plain extraction gives 'Failed sign-in attempts before' and 'lockout 10 5')."""
    document = parsed("A-PWD-V2")
    tables = [b for p in document.pages for b in p.blocks if b.kind == "table"]
    assert len(tables) == 1
    assert tables[0].rows() == [
        ["Control", "Standard accounts", "Privileged accounts"],
        ["Failed sign-in attempts before lockout", "10", "5"],
        ["Counting window for failed attempts", "15 minutes", "15 minutes"],
        ["Lockout duration", "30 minutes", "Until the IAM team unlocks the account"],
        [
            "Delay after the 3rd consecutive failed attempt",
            "30 seconds, doubling after each further failure",
            "30 seconds, doubling after each further failure",
        ],
        ["Maximum delay between attempts", "10 minutes", "10 minutes"],
    ]
    assert document.pages[2].blocks[-1] == tables[0]


def test_html_export_parses_to_the_blocks_of_its_source():
    rel = entries()["A-MFA"].path
    document = parsed("A-MFA")
    expected = markdown.blocks(source_body(rel.removesuffix(".html") + ".md"))
    assert list(document.pages[0].blocks) == expected


def test_markdown_drops_front_matter_comments_and_inline_marks():
    blocks = markdown.blocks(
        "# Title\r\n\r\nSome **bold** text with `code`\r\nand a [link](https://example.org).\r\n"
        "<!-- page: 2 -->\r\n<!-- a hidden\r\nnote -->\r\n\r\n## 2 Next\r\n\r\n- one\r\n  more\r\n"
        "- two\r\n\r\n| A | B |\r\n|---|---|\r\n| 1 | 2 |\r\n"
    )
    assert [(b.kind, b.text) for b in blocks] == [
        ("heading", "Title"),
        ("paragraph", "Some bold text with code and a link."),
        ("heading", "2 Next"),
        ("item", "- one more"),
        ("item", "- two"),
        ("table", "| A | B |\n| 1 | 2 |"),
    ]
