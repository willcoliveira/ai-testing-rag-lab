"""HTML to blocks with the standard library parser: the text a reader of the page sees.

h1 to h6 become headings, p and loose text paragraphs, li items, and a table one table block (its
rows of th and td cells). The head, scripts, styles, templates and elements with the hidden
attribute are not shown to a reader, so their text is not kept. Text hidden with CSS is not
detected (a lab limit: the corpus export has no styles).
"""

from html.parser import HTMLParser
from pathlib import Path

from raglab.core.types import Block, Page, table_block

HEADINGS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}
INVISIBLE = frozenset({"head", "script", "style", "template", "noscript"})
# elements that end the current paragraph
BLOCK_TAGS = frozenset(
    {"p", "div", "li", "ul", "ol", "table", "article", "section", "main", "body", "br", "hr"}
    | set(HEADINGS)
    | {"blockquote", "pre", "header", "footer", "nav", "aside", "dl", "dt", "dd"}
)
VOID = frozenset({"br", "hr", "img", "meta", "link", "input", "area", "base", "col", "wbr"})


class _Reader(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[Block] = []
        self.meta: dict[str, str] = {}
        self.hidden_depth = 0  # >0 inside an invisible element
        self.stack: list[str] = []  # open elements, for the hidden-depth bookkeeping
        self.text: list[str] = []
        self.kind: str = "paragraph"
        self.level = 0
        self.rows: list[list[str]] | None = None
        self.cell: list[str] | None = None
        self.table_text: list[str] = []  # a caption or loose text inside a table, outside cells

    # ---------------------------------------------------------------- text runs

    def _flush(self) -> None:
        text = " ".join("".join(self.text).split())
        self.text = []
        if not text:
            return
        if self.kind == "heading":
            self.blocks.append(Block("heading", text, level=self.level))
        elif self.kind == "item":
            self.blocks.append(Block("item", "- " + text))
        else:
            self.blocks.append(Block("paragraph", text))
        self.kind, self.level = "paragraph", 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "meta" and (attributes.get("name") or "").startswith("corpus-"):
            self.meta[(attributes.get("name") or "").removeprefix("corpus-")] = (
                attributes.get("content") or ""
            )
        if tag in VOID:
            if tag in ("br", "hr") and not self.hidden_depth and self.cell is None:
                self._flush()
            elif tag == "br" and self.cell is not None:
                self.cell.append(" ")
            return
        hidden = tag in INVISIBLE or "hidden" in attributes
        self.stack.append(tag)
        if hidden or self.hidden_depth:
            self.hidden_depth += 1
            return
        if tag == "table":
            self._flush()
            self.rows = []
        elif tag == "tr" and self.rows is not None:
            self.rows.append([])
        elif tag in ("td", "th") and self.rows is not None:
            self.cell = []
        elif self.cell is not None:
            return  # markup inside a table cell stays in the cell
        elif tag in HEADINGS:
            self._flush()
            self.kind, self.level = "heading", HEADINGS[tag]
        elif tag == "li":
            self._flush()
            self.kind = "item"
        elif tag in BLOCK_TAGS:
            self._flush()

    def handle_endtag(self, tag: str) -> None:
        if tag in VOID or tag not in self.stack:
            return
        # close everything up to the matching open element (browsers do the same)
        while self.stack:
            open_tag = self.stack.pop()
            if self.hidden_depth:
                self.hidden_depth -= 1
            else:
                self._close(open_tag)
            if open_tag == tag:
                break

    def _close(self, tag: str) -> None:
        if tag in ("td", "th") and self.cell is not None and self.rows is not None:
            if self.rows:
                self.rows[-1].append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "table" and self.rows is not None:
            if caption := " ".join("".join(self.table_text).split()):
                self.blocks.append(Block("paragraph", caption))
            rows = [row for row in self.rows if any(row)]
            if rows:
                self.blocks.append(table_block(rows))
            self.rows, self.table_text = None, []
        elif self.cell is None and (tag in HEADINGS or tag == "li" or tag in BLOCK_TAGS):
            self._flush()

    def handle_data(self, data: str) -> None:
        if self.hidden_depth:
            return
        if self.cell is not None:
            self.cell.append(data)
        elif self.rows is not None:
            self.table_text.append(data)
        else:
            self.text.append(data)

    def close(self) -> None:
        super().close()
        self._flush()


def read(path: Path) -> tuple[list[Block], dict[str, str]]:
    """The blocks of an HTML file and its corpus-* meta values (id, version, tenant, ...)."""
    reader = _Reader()
    reader.feed(path.read_text(encoding="utf-8"))
    reader.close()
    return reader.blocks, reader.meta


class HtmlParser:
    """An HTML export: its visible text as one page without a print number."""

    format = "html"

    def parse(self, path: Path) -> tuple[Page, ...]:
        blocks, _ = read(path)
        return (Page(None, tuple(blocks)),)
