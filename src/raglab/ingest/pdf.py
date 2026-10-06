"""PDF to blocks with pypdf, page by page, with tables read as rows.

pypdf's plain extraction reads a table line by line, so a wrapped row label lands on one line and
its values on the next ("Failed sign-in attempts before / lockout 10 5"), and a value can no
longer be tied to its row. This parser reads the text runs with their positions instead:

- a cell is a stroked rectangle (the `re` operator); a table is two or more adjacent rows of two
  or more cells; each run inside a cell is that cell's text, so a table becomes one table block
  with its rows intact (the table-only rule survives);
- other runs on the same baseline form a line; a line set in bold, larger than the page's body
  text, is a heading, whose level comes from its section id (4 is level 2, 4.1 level 3; a heading
  without an id is the title, level 1);
- lines join into a paragraph until a heading, a list item ('- '), or a vertical gap larger than
  1.55 times the font size (wrapped lines of the corpus PDF sit 1.42 apart, list items 1.69 and
  paragraphs 2.09).

Lab limits: a table must be drawn with cell rectangles (as the corpus build does); a table
without borders is read as lines; bold detection uses the font name.
"""

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from pypdf import PageObject, PdfReader

from raglab.core.types import SECTION_ID, Block, Page, table_block

PARAGRAPH_GAP = 1.55  # times the font size
SAME_LINE = 1.0  # points
MIN_CELL = 4.0  # points: smaller rectangles are rules or decoration, not cells
EDGE = 1.0  # points of tolerance when cells touch or contain a run


@dataclass(frozen=True)
class Run:
    text: str
    x: float
    y: float
    size: float
    bold: bool


@dataclass(frozen=True)
class Cell:
    x: float
    y: float  # bottom
    width: float
    height: float

    def contains(self, x: float, y: float) -> bool:
        return (
            self.x - EDGE <= x <= self.x + self.width + EDGE
            and self.y - EDGE <= y <= self.y + self.height + EDGE
        )


@dataclass
class _Table:
    rows: list[list[Cell]]
    cells: dict[Cell, list[Run]]
    emitted: bool = False

    def block(self) -> Block:
        return table_block([[_cell_text(self.cells[c]) for c in row] for row in self.rows])


def _apply(matrix: list[float], x: float, y: float) -> tuple[float, float]:
    a, b, c, d, e, f = matrix[:6]
    return a * x + c * y + e, b * x + d * y + f


def _cell_text(runs: list[Run]) -> str:
    lines = _lines(runs)
    return " ".join(" ".join("".join(r.text for r in line).split()) for line in lines)


def _lines(runs: list[Run]) -> list[list[Run]]:
    """Runs grouped into lines: consecutive runs on the same baseline."""
    lines: list[list[Run]] = []
    for run in runs:
        if lines and abs(lines[-1][-1].y - run.y) <= SAME_LINE:
            lines[-1].append(run)
        else:
            lines.append([run])
    return lines


def _tables(cells: list[Cell]) -> list[_Table]:
    """Cells grouped into rows (same bottom and height) and rows into tables (adjacent rows)."""
    rows: dict[tuple[float, float], list[Cell]] = {}
    for cell in cells:
        rows.setdefault((round(cell.y, 1), round(cell.height, 1)), []).append(cell)
    ordered = sorted(rows.values(), key=lambda r: -(r[0].y + r[0].height))
    tables: list[list[list[Cell]]] = []
    for row in ordered:
        row.sort(key=lambda c: c.x)
        top = row[0].y + row[0].height
        if tables and abs(tables[-1][-1][0].y - top) <= EDGE:
            tables[-1].append(row)
        else:
            tables.append([row])
    return [
        _Table(t, {c: [] for row in t for c in row})
        for t in tables
        if len(t) >= 2 and max(len(r) for r in t) >= 2
    ]


def _read_page(page: PageObject) -> tuple[list[Run], list[Cell]]:
    runs: list[Run] = []
    cells: list[Cell] = []

    def on_text(
        text: str,
        cm: list[float],
        tm: list[float],
        font: dict[str, object] | None,
        size: float,
    ) -> None:
        if not text.strip():
            return
        x, y = _apply(cm, *_apply(tm, 0, 0))
        name = str((font or {}).get("/BaseFont", ""))
        runs.append(Run(text, x, y, float(size), "Bold" in name))

    def on_operator(operator: bytes, args: list[object], cm: list[float], tm: list[float]) -> None:
        del tm
        if operator != b"re" or len(args) != 4:
            return
        x, y, w, h = (float(str(a)) for a in args)
        if abs(w) < MIN_CELL or abs(h) < MIN_CELL:
            return
        x0, y0 = _apply(cm, x, y)
        x1, y1 = _apply(cm, x + w, y + h)
        cells.append(Cell(min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0)))

    page.extract_text(visitor_text=on_text, visitor_operand_before=on_operator)
    return runs, cells


def heading_level(text: str) -> int:
    token = text.split(" ", 1)[0]
    return 2 + token.count(".") if SECTION_ID.match(token) else 1


def page_blocks(runs: list[Run], cells: list[Cell]) -> list[Block]:
    """The blocks of one page from its text runs (in content order) and stroked rectangles."""
    tables = _tables(cells)
    sizes: Counter[float] = Counter()
    for run in runs:
        sizes[run.size] += len(run.text)
    body_size = sizes.most_common(1)[0][0] if sizes else 0.0

    # each item is a table, or a line of runs outside every table
    items: list[_Table | list[Run]] = []
    loose: list[Run] = []
    for run in runs:
        table = next((t for t in tables if any(c.contains(run.x, run.y) for c in t.cells)), None)
        if table is None:
            loose.append(run)
            continue
        cell = next(c for c in table.cells if c.contains(run.x, run.y))
        table.cells[cell].append(run)
        if not table.emitted:
            items.extend(_lines(loose))
            loose = []
            items.append(table)
            table.emitted = True
    items.extend(_lines(loose))

    blocks: list[Block] = []
    paragraph: list[str] = []
    kind = "paragraph"
    last: Run | None = None

    def flush() -> None:
        nonlocal paragraph, kind
        if text := " ".join(" ".join(paragraph).split()):
            blocks.append(Block("item" if kind == "item" else "paragraph", text))
        paragraph, kind = [], "paragraph"

    for item in items:
        if isinstance(item, _Table):
            flush()
            blocks.append(item.block())
            last = None
            continue
        text = " ".join("".join(r.text for r in item).split())
        first = item[0]
        if all(r.bold for r in item) and first.size > body_size:
            flush()
            blocks.append(Block("heading", text, level=heading_level(text)))
            last = None
            continue
        gap = (last.y - first.y) if last is not None else None
        if gap is None or gap < 0 or gap > PARAGRAPH_GAP * first.size or text.startswith("- "):
            flush()
            kind = "item" if text.startswith("- ") else "paragraph"
        paragraph.append(text)
        last = first
    flush()
    return blocks


class PdfParser:
    """A PDF: one page per PDF page, numbered from 1 (the print page)."""

    format = "pdf"

    def parse(self, path: Path) -> tuple[Page, ...]:
        reader = PdfReader(path)
        pages: list[Page] = []
        for number, page in enumerate(reader.pages, start=1):
            runs, cells = _read_page(page)
            pages.append(Page(number, tuple(page_blocks(runs, cells))))
        return tuple(pages)
