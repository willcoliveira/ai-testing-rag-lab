"""HTML to blocks with the standard library parser: the text a reader of the page sees.

h1 to h6 become headings, p and loose text paragraphs, li items ('- ...', or '1. ...' inside an
ol, numbered from its start attribute), and a table one table block (its rows of th and td cells).
A br is a line break inside its block, read as a space, as the Markdown parser reads a line break
inside a paragraph; an hr ends the block. The head, scripts, styles, templates and elements with
the hidden attribute are not shown to a reader, so their text is not kept. A byte-order mark and
CRLF line ends are normalised as for Markdown. Text hidden with CSS is not detected (a lab limit:
the corpus export has no styles).
"""

import re
from html.parser import HTMLParser
from pathlib import Path

from raglab.core.types import Block, Page, table_block
from raglab.ingest import frontmatter

HEADINGS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}
INVISIBLE = frozenset({"head", "script", "style", "template", "noscript"})
# elements that end the current paragraph
BLOCK_TAGS = frozenset(
    {"p", "div", "li", "ul", "ol", "table", "article", "section", "main", "body", "hr"}
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
        self.lists: list[int | None] = []  # open ul (None) and ol (the next item's number)
        self.marker = "- "  # the current item's marker

    # ---------------------------------------------------------------- text runs

    def _flush(self) -> None:
        text = " ".join("".join(self.text).split())
        self.text = []
        if not text:
            return
        if self.kind == "heading":
            self.blocks.append(Block("heading", text, level=self.level))
        elif self.kind == "item":
            self.blocks.append(Block("item", self.marker + text))
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
            if self.hidden_depth:
                return
            if tag == "br":  # a line break inside the block, never a block end
                self.handle_data(" ")
            elif tag == "hr" and self.cell is None:
                self._flush()
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
            self.kind, self.marker = "item", "- "
            if self.lists and self.lists[-1] is not None:
                self.marker = f"{self.lists[-1]}. "
                self.lists[-1] += 1
        elif tag in BLOCK_TAGS:
            self._flush()
            if tag in ("ul", "ol"):
                self.lists.append(_start(attributes) if tag == "ol" else None)

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
            if tag in ("ul", "ol") and self.lists:
                self.lists.pop()

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


def _start(attributes: dict[str, str | None]) -> int:
    """The number of an ol's first item: its start attribute, 1 when absent or not a number."""
    start = (attributes.get("start") or "").strip()
    return int(start) if re.fullmatch(r"-?[0-9]+", start) else 1


def read(path: Path) -> tuple[list[Block], dict[str, str]]:
    """The blocks of an HTML file and its corpus-* meta values (id, version, tenant, ...)."""
    reader = _Reader()
    reader.feed(frontmatter.normalise_newlines(path.read_text(encoding="utf-8")))
    reader.close()
    return reader.blocks, reader.meta


class HtmlParser:
    """An HTML export: its visible text as one page without a print number."""

    format = "html"

    def parse(self, path: Path) -> tuple[Page, ...]:
        blocks, _ = read(path)
        return (Page(None, tuple(blocks)),)
