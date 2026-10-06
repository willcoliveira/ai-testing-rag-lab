"""A scanned page (PNG) to blocks with Tesseract, through pytesseract.

Tesseract runs with English and page segmentation mode 3 (automatic layout), its default. Its
output separates blocks with a blank line; the lines of a block join into one paragraph. A block
of one short line is a heading when it starts with a numeric section id and a capitalised title
that does not end in a full stop and is not a date such as "3 November 2025" (level from the id:
1 is level 2, 1.1 level 3); a title may end in a digit ("2 Rule 5"). The first block of the page
is the title (level 1) when it is one line without a full stop.

OCR text depends on the Tesseract build and its English model, so the version is recorded in the
inventory (`raglab ingest`), and tests compare OCR text with its ground truth by character error
rate, never exactly.
"""

import re
from pathlib import Path

import pytesseract

from raglab.core.types import Block, Page

LANGUAGE = "eng"
CONFIG = "--psm 3"
OCR_HEADING = re.compile(r"^([0-9]+(?:\.[0-9]+)*) [A-Z][^.]*[^.]$")
MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
# a date on a line of its own ("3 November 2025") looks like a section id and a title
DATE = re.compile(rf"^[0-9]{{1,2}} (?:{MONTHS}) [0-9]{{4}}$")
MAX_HEADING = 80


def tesseract_version() -> str:
    """The version of the Tesseract binary pytesseract runs, e.g. 5.5.3."""
    return str(pytesseract.get_tesseract_version())


def image_text(path: Path) -> str:
    """Tesseract's text for one image file."""
    return pytesseract.image_to_string(str(path), lang=LANGUAGE, config=CONFIG)


def text_blocks(text: str) -> list[Block]:
    """Blocks from Tesseract's plain-text output."""
    groups: list[list[str]] = [[]]
    for line in text.replace("\f", "\n").splitlines():
        if line.strip():
            groups[-1].append(" ".join(line.split()))
        elif groups[-1]:
            groups.append([])
    blocks: list[Block] = []
    for n, lines in enumerate(g for g in groups if g):
        joined = " ".join(lines)
        single = len(lines) == 1 and len(joined) <= MAX_HEADING
        if single and (match := OCR_HEADING.match(joined)) and not DATE.match(joined):
            blocks.append(Block("heading", joined, level=2 + match.group(1).count(".")))
        elif single and n == 0 and not joined.endswith("."):
            blocks.append(Block("heading", joined, level=1))
        else:
            blocks.append(Block("paragraph", joined))
    return blocks


class OcrParser:
    """A scanned single-page image: one page, print page 1."""

    format = "png"

    def parse(self, path: Path) -> tuple[Page, ...]:
        return (Page(1, tuple(text_blocks(image_text(path)))),)
