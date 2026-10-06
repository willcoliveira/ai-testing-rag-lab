"""AC2: every register document parses to the text a reader sees, and that text holds every value
the answer key cites for the document, at its cited section, paragraph, table cell and page.

The PDF and the HTML export are also compared, block by block and page by page, with the
Markdown they were rendered from: the tests read the Markdown as the oracle; ingestion never does.
The scanned page (OCR) is compared with its ground truth by character error rate in test_ocr.py.
"""

import re

import pytest

from raglab.core.text import normalise_space
from raglab.ingest import html, markdown
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


def html_blocks(tmp_path, text: str, encoding: str = "utf-8") -> list[tuple[str, str]]:
    path = tmp_path / "page.html"
    path.write_bytes(text.encode(encoding))
    return [(b.kind, b.text) for b in html.read(path)[0]]


def test_a_line_break_inside_an_html_block_is_a_space(tmp_path):
    """S1B-J2/D6: a <br> inside a paragraph, item or heading does not start a new block (it would
    shift the paragraph numbers the answer key cites, such as F-15's 4.1 paragraphs 1 and 2)."""
    blocks = html_blocks(
        tmp_path,
        "<body><h2>4.1 A<br>title</h2><p>Administrators must<br>always use MFA.</p>"
        "<p>The only exception is.</p><ul><li>Line one<br/>line two</li></ul>"
        "<table><tr><th>a<br />b</th></tr></table><p>before</p><hr><p>after</p></body>",
    )
    assert blocks == [
        ("heading", "4.1 A title"),
        ("paragraph", "Administrators must always use MFA."),
        ("paragraph", "The only exception is."),
        ("item", "- Line one line two"),
        ("table", "| a b |"),
        ("paragraph", "before"),
        ("paragraph", "after"),
    ]
    assert blocks[:3] == [
        (b.kind, b.text)
        for b in markdown.blocks(
            "## 4.1 A title\n\nAdministrators must\nalways use MFA.\n\nThe only exception is.\n"
        )
    ]


def test_an_html_export_with_a_byte_order_mark_and_crlf_reads_like_one_without(tmp_path):
    """D2: a BOM is not text (the Markdown parser already drops it)."""
    page = "<html><head><title>T</title></head>\n<body>\n<h1>Title</h1>\n<p>one\ntwo</p>\n</body>"
    plain = html_blocks(tmp_path, page)
    assert plain == [("heading", "Title"), ("paragraph", "one two")]
    assert html_blocks(tmp_path, "\ufeff" + page.replace("\n", "\r\n")) == plain


def test_numbered_markdown_items_are_items_and_thematic_breaks_are_not_text():
    """S1B-J3/D7: an ordered list keeps its item structure (and its numbers); '---', '***' and
    '___' on a line of their own are dropped; a wrapped line that starts with a number other
    than 1 stays in its paragraph; '##2' without a space is not a heading (corpus/SPEC.md)."""
    blocks = markdown.blocks(
        "## 5 Steps\n\n1. Disable sign-in.\n2. Revoke\n   sessions.\n3) Reset the password.\n\n"
        "---\n\n* * *\n\nA line that wraps at\n12. stays in its paragraph.\nAnd a list\n"
        "1. can start here.\n\n___\n\n##2 Rules\n\n## 6 Next\n\n- one\n"
    )
    assert [(b.kind, b.text) for b in blocks] == [
        ("heading", "5 Steps"),
        ("item", "1. Disable sign-in."),
        ("item", "2. Revoke sessions."),
        ("item", "3. Reset the password."),
        ("paragraph", "A line that wraps at 12. stays in its paragraph. And a list"),
        ("item", "1. can start here."),
        ("paragraph", "##2 Rules"),
        ("heading", "6 Next"),
        ("item", "- one"),
    ]


def test_an_html_ordered_list_numbers_its_items_as_markdown_does(tmp_path):
    """S1B-J3: the HTML export of a numbered list gives the blocks of its Markdown source."""
    blocks = html_blocks(
        tmp_path,
        "<body><h2>5 Steps</h2><ol><li>Disable sign-in.</li><li>Revoke sessions.</li></ol>"
        '<ol start="3"><li>Reset the password.</li><li>Tell the user.<ul><li>by phone</li></ul>'
        "</li></ol><ul><li>one</li></ul></body>",
    )
    expected = markdown.blocks(
        "## 5 Steps\n\n1. Disable sign-in.\n2. Revoke sessions.\n\n"
        "3. Reset the password.\n4. Tell the user.\n\n- by phone\n\n- one\n"
    )
    assert blocks == [(b.kind, b.text) for b in expected]
