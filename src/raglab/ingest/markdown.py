"""Markdown to blocks: the text a reader of the rendered page sees.

Front matter, HTML comments (page markers included) and thematic breaks ('---', '***', '___' on a
line of their own) are not part of what a reader sees as text, so they are removed; bold markers
and code ticks are dropped; a link keeps its text. Headings keep their level, a table becomes a
table block (one '| cell |' line per row, the separator row dropped) and each list item becomes an
item block: '- ...' for a bullet ('-', '*', '+'), '1. ...' for a numbered item ('1.' or '1)').
A line break inside a paragraph or item is a space.

Only ATX headings are headings ('#' to '######' followed by a space, the form corpus/SPEC.md
requires): '##2 Rules' without the space and a setext heading (a line underlined with '===' or
'---') are read as paragraphs, and their text stays in the section before them.
"""

import re
from pathlib import Path

from raglab.core.types import Block, Page, table_block
from raglab.ingest import frontmatter

HEADING = re.compile(r"^ {0,3}(#{1,6})\s+(.+?)(?:\s+#+)?\s*$")
ITEM = re.compile(r"^\s{0,3}([-*+]|[0-9]{1,9}[.)])\s+(.*)$")
THEMATIC_BREAK = re.compile(r"^ {0,3}([-*_])(?:[ \t]*\1){2,}[ \t]*$")
COMMENT = re.compile(r"<!--.*?-->", flags=re.S)
TABLE_SEPARATOR = re.compile(r"^:?-+:?$")
LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def inline(text: str) -> str:
    """Inline Markdown removed: links keep their text, bold markers and code ticks go."""
    text = LINK.sub(r"\1", text)
    return " ".join(text.replace("**", "").replace("`", "").split())


def _cells(line: str) -> list[str]:
    return [inline(c) for c in line.strip().strip("|").split("|")]


def _starts_block(line: str, in_list: bool = False) -> bool:
    """Whether a line ends the paragraph or item before it. Inside a paragraph only a numbered
    item that starts at 1 does (as in CommonMark), so a wrapped line that happens to start with
    '12. ' stays in its paragraph; inside a list any item does."""
    item = ITEM.match(line)
    return bool(
        HEADING.match(line)
        or THEMATIC_BREAK.match(line)
        or (item and (in_list or item.group(1) in ("-", "*", "+", "1.", "1)")))
        or line.lstrip().startswith("|")
    )


def _marker(token: str) -> str:
    """An item's marker as the block shows it: '- ' for a bullet, '3. ' for a numbered item."""
    return "- " if token in ("-", "*", "+") else f"{int(token[:-1])}. "


def blocks(body: str) -> list[Block]:
    """The blocks of a Markdown body (front matter already removed)."""
    lines = COMMENT.sub("", frontmatter.normalise_newlines(body)).split("\n")
    out: list[Block] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or THEMATIC_BREAK.match(line):
            i += 1
        elif heading := HEADING.match(line):
            text = inline(heading.group(2))
            if text:
                out.append(Block("heading", text, level=len(heading.group(1))))
            i += 1
        elif line.lstrip().startswith("|"):
            rows: list[list[str]] = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                cells = _cells(lines[i])
                if not all(TABLE_SEPARATOR.match(c) for c in cells):
                    rows.append(cells)
                i += 1
            if any(any(row) for row in rows):
                out.append(table_block(rows))
        elif item := ITEM.match(line):
            text = [item.group(2)]
            i += 1
            while i < len(lines) and lines[i].strip() and not _starts_block(lines[i], True):
                text.append(lines[i])
                i += 1
            if body_text := inline(" ".join(text)):
                out.append(Block("item", _marker(item.group(1)) + body_text))
        else:
            text = [line]
            i += 1
            while i < len(lines) and lines[i].strip() and not _starts_block(lines[i]):
                text.append(lines[i])
                i += 1
            if body_text := inline(" ".join(text)):
                out.append(Block("paragraph", body_text))
    return out


class MarkdownParser:
    """A corpus Markdown file: its body as one page without a print number."""

    format = "md"

    def parse(self, path: Path) -> tuple[Page, ...]:
        _, body = frontmatter.split(path.read_text(encoding="utf-8"), path.as_posix())
        return (Page(None, tuple(blocks(body))),)
