"""Render the corpus files that ingestion reads in a format other than Markdown.

Markdown under `corpus/` is canonical (corpus/SPEC.md, section 3). This script renders:

- `tenant-a/password-standard-v2.md` to a PDF, one page per `<!-- page: N -->` marker, with
  Table 1 kept as a table;
- `tenant-a/mfa-standard.md` to an HTML export, with an anchor per section (`sec-4-1`);
- `tenant-a/device-policy-annex-b-kiosk.md` to one scanned page (PNG: rendered text, a slight
  rotation and noise), with its ground-truth text next to it (`.gt.txt`).

It writes `corpus/build-manifest.json` with the sha256 of every generated file and the page count
of the whole corpus at a fixed print layout (AC3).

Deterministic by construction (lab practice; a production pipeline would also pin the platform):
- the PDF uses the PDF core font Helvetica (never embedded), a fixed creation date and no stream
  compression, so its bytes do not depend on the zlib build;
- the PNG uses the font bundled with the pinned Pillow (Aileron Regular, rendered by FreeType) and
  noise from a sha256 stream with a fixed seed. Its pixels are compared, not its file bytes, since
  PNG compression depends on the zlib build; the manifest records the FreeType version.

Usage:
    uv run python scripts/build_corpus.py            # write into corpus/
    uv run python scripts/build_corpus.py --check    # rebuild in a temp dir and compare
    uv run python scripts/build_corpus.py --out DIR  # write into DIR/corpus/
"""

from __future__ import annotations

import argparse
import hashlib
import html
import io
import json
import re
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from html.parser import HTMLParser
from importlib.metadata import version
from pathlib import Path

from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont, features
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
CORPUS = "corpus"
PDF_SOURCE = "corpus/tenant-a/password-standard-v2.md"
HTML_SOURCE = "corpus/tenant-a/mfa-standard.md"
PNG_SOURCE = "corpus/tenant-a/device-policy-annex-b-kiosk.md"
MANIFEST = "corpus/build-manifest.json"
DOC_DIRS = ("tenant-a", "tenant-b", "external", "attacks")
BUILD_DATE = datetime(2026, 10, 6, tzinfo=UTC)
NOISE_SEED = b"ai-testing-rag-lab/annex-b/v1"
ROTATION_DEGREES = 0.8
PAGE_MARKER = re.compile(r"^<!-- page: (\d+) -->$")
HEADING = re.compile(r"^(#{1,3}) (.+)$")


# ---------------------------------------------------------------- Markdown model


@dataclass
class Block:
    """One block of a corpus Markdown body."""

    kind: str  # heading, para, item, table, page, comment
    text: str = ""
    level: int = 0
    rows: list[list[str]] = field(default_factory=lambda: [])


@dataclass
class Doc:
    path: str
    front: dict[str, str]
    body: str


def front_matter(text: str) -> tuple[dict[str, str], str]:
    """The flat YAML front matter of a corpus file (key: value lines) and the body after it."""
    match = re.match(r"^---\n(.*?)\n---\n", text, flags=re.S)
    if not match:
        raise ValueError("no front matter")
    front: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, _, value = line.partition(":")
        value = value.strip()
        if value.startswith('"'):
            value = str(json.loads(value))
        front[key.strip()] = value
    return front, text[match.end() :]


def read_doc(root: Path, rel: str) -> Doc:
    front, body = front_matter((root / rel).read_text(encoding="utf-8"))
    return Doc(rel, front, body)


def corpus_docs(root: Path) -> list[Doc]:
    """Every corpus document (the Markdown files with front matter), in path order."""
    paths = sorted(p for d in DOC_DIRS for p in (root / CORPUS / d).glob("*.md"))
    return [read_doc(root, p.relative_to(root).as_posix()) for p in paths]


def blocks(body: str) -> list[Block]:
    """Split a body into headings, paragraphs, list items, tables, page markers and comments."""
    out: list[Block] = []
    lines = body.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line.strip():
            i += 1
            continue
        if marker := PAGE_MARKER.match(line):
            out.append(Block("page", marker.group(1)))
            i += 1
        elif line.startswith("<!--"):
            out.append(Block("comment", line))
            i += 1
        elif heading := HEADING.match(line):
            out.append(Block("heading", heading.group(2), level=len(heading.group(1))))
            i += 1
        elif line.startswith("|"):
            rows: list[list[str]] = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            out.append(Block("table", rows=rows))
        elif line.startswith("- "):
            text = [line[2:].strip()]
            i += 1
            while i < len(lines) and lines[i].startswith("  ") and lines[i].strip():
                text.append(lines[i].strip())
                i += 1
            out.append(Block("item", " ".join(text)))
        else:
            text = [line.strip()]
            i += 1
            while i < len(lines) and lines[i].strip() and not _starts_block(lines[i]):
                text.append(lines[i].strip())
                i += 1
            out.append(Block("para", " ".join(text)))
    return out


def _starts_block(line: str) -> bool:
    return bool(
        PAGE_MARKER.match(line) or line.startswith(("<!--", "|", "- ")) or HEADING.match(line)
    )


def plain(text: str) -> str:
    """Inline Markdown removed: bold markers and code ticks."""
    return text.replace("**", "").replace("`", "")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------- PDF


class _Pdf(FPDF):
    pass


def _new_pdf(doc: Doc) -> FPDF:
    pdf = _Pdf(orientation="portrait", unit="mm", format="A4")
    pdf.set_compression(False)
    pdf.set_creation_date(BUILD_DATE)
    pdf.set_producer("ai-testing-rag-lab scripts/build_corpus.py")
    pdf.set_creator("ai-testing-rag-lab scripts/build_corpus.py")
    pdf.set_title(doc.front.get("title", doc.path))
    pdf.set_author("ai-testing-rag-lab authors (fictional lab material)")
    pdf.set_lang("en-GB")
    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(auto=True, margin=18)
    return pdf


def _write_text(pdf: FPDF, text: str, size: float, style: str = "", indent: float = 0) -> None:
    pdf.set_font("Helvetica", style, size)
    pdf.set_x(pdf.l_margin + indent)
    # fpdf2's inline markdown also reads -- and __ as markers; use it only for bold-only text
    rich = "**" in text and "--" not in text and "__" not in text
    pdf.multi_cell(
        w=pdf.epw - indent,
        h=size * 0.5,
        text=text if rich else plain(text),
        markdown=rich,
        align="L",
        new_x="LMARGIN",
        new_y="NEXT",
    )


def _render_blocks(pdf: FPDF, items: list[Block], *, paged: bool) -> None:
    """Render blocks. paged: a page marker starts a page and each page must fit on one page."""
    expected_pages = 0
    if not paged:
        pdf.add_page()
    for block in items:
        if block.kind == "page":
            if not paged:
                continue
            if pdf.page_no() != expected_pages:
                raise ValueError(f"page {expected_pages} did not fit on one page")
            expected_pages += 1
            pdf.add_page()
        elif block.kind == "comment":
            continue
        elif block.kind == "heading":
            size = {1: 16.0, 2: 13.0, 3: 11.0}[block.level]
            pdf.ln(2 if block.level > 1 else 0)
            _write_text(pdf, block.text, size, "B")
            pdf.ln(1)
        elif block.kind == "item":
            _write_text(pdf, "- " + block.text, 10.5, indent=4)
            pdf.ln(1)
        elif block.kind == "para":
            _write_text(pdf, block.text, 10.5)
            pdf.ln(2.5)
        elif block.kind == "table":
            _render_table(pdf, block.rows)
            pdf.ln(2.5)
    if paged and pdf.page_no() != expected_pages:
        raise ValueError(f"page {expected_pages} did not fit on one page")


def _render_table(pdf: FPDF, rows: list[list[str]]) -> None:
    columns = len(rows[0])
    size = 9.5 if columns <= 4 else 7.5
    pdf.set_font("Helvetica", "", size)
    with pdf.table(
        text_align="LEFT",
        line_height=size * 0.5,
        first_row_as_headings=True,
        padding=1.2,
    ) as table:
        for cells in rows:
            row = table.row()
            for cell in cells:
                row.cell(plain(cell))


def render_pdf(doc: Doc) -> bytes:
    pdf = _new_pdf(doc)
    _render_blocks(pdf, blocks(doc.body), paged=True)
    pages = int(doc.front["pages"])
    if pdf.page_no() != pages:
        raise ValueError(f"{doc.path}: rendered {pdf.page_no()} pages, front matter says {pages}")
    return bytes(pdf.output())


def print_pages(doc: Doc) -> int:
    """Pages a document takes at the fixed print layout (the PDF layout, page breaks automatic)."""
    if doc.front.get("format") == "png":
        return int(doc.front["pages"])
    pdf = _new_pdf(doc)
    paged = doc.front.get("format") == "pdf"
    _render_blocks(pdf, blocks(doc.body), paged=paged)
    return pdf.page_no()


def pdf_page_texts(data: bytes) -> list[str]:
    """Text of each page, as pypdf extracts it."""
    return [page.extract_text() for page in PdfReader(io.BytesIO(data)).pages]


# ---------------------------------------------------------------- HTML


def anchor(section_id: str) -> str:
    return "sec-" + section_id.replace(".", "-")


def _inline_html(text: str) -> str:
    escaped = html.escape(text, quote=False)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)


def render_html(doc: Doc) -> bytes:
    title = html.escape(doc.front["title"])
    meta = "".join(
        f'<meta name="corpus-{key}" content="{html.escape(doc.front[key])}">\n'
        for key in ("id", "version", "tenant", "effective", "licence")
    )
    out = [
        "<!doctype html>\n",
        '<html lang="en-GB">\n<head>\n<meta charset="utf-8">\n',
        f"<title>{title}</title>\n",
        meta,
        "</head>\n<body>\n<article>\n",
    ]
    items = [b for b in blocks(doc.body) if b.kind not in ("page", "comment")]
    in_list = False
    for block in items:
        if block.kind != "item" and in_list:
            out.append("</ul>\n")
            in_list = False
        if block.kind == "heading":
            text = _inline_html(block.text)
            if block.level == 1:
                out.append(f"<h1>{text}</h1>\n")
            else:
                sid = block.text.split(" ", 1)[0]
                out.append(f'<h{block.level} id="{anchor(sid)}">{text}</h{block.level}>\n')
        elif block.kind == "para":
            out.append(f"<p>{_inline_html(block.text)}</p>\n")
        elif block.kind == "item":
            if not in_list:
                out.append("<ul>\n")
                in_list = True
            out.append(f"<li>{_inline_html(block.text)}</li>\n")
        elif block.kind == "table":
            out.append("<table>\n")
            for n, cells in enumerate(block.rows):
                tag = "th" if n == 0 else "td"
                row = "".join(f"<{tag}>{_inline_html(c)}</{tag}>" for c in cells)
                out.append(f"<tr>{row}</tr>\n")
            out.append("</table>\n")
    if in_list:
        out.append("</ul>\n")
    out.append("</article>\n</body>\n</html>\n")
    return "".join(out).encode("utf-8")


class _TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs  # only the tag decides what is visible text
        if tag in ("head", "script", "style"):
            self.skip += 1
        elif tag in ("p", "li", "tr", "h1", "h2", "h3", "td", "th"):
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("head", "script", "style"):
            self.skip -= 1

    def handle_data(self, data: str) -> None:
        if not self.skip:
            self.parts.append(data)


def html_text(data: bytes) -> str:
    """The visible text of an HTML export."""
    parser = _TextParser()
    parser.feed(data.decode("utf-8"))
    return "".join(parser.parts)


# ---------------------------------------------------------------- scanned page


def ground_truth(doc: Doc) -> str:
    """The text a reader sees on the scanned page: one line per heading or paragraph."""
    lines = [plain(b.text) for b in blocks(doc.body) if b.kind in ("heading", "para", "item")]
    return "\n".join(lines) + "\n"


def _wrap(
    draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, width: int
) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in text.split(" "):
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=font) <= width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _noise_stream(count: int) -> list[int]:
    out: list[int] = []
    counter = 0
    while len(out) < count:
        out.extend(hashlib.sha256(NOISE_SEED + counter.to_bytes(8, "big")).digest())
        counter += 1
    return out[:count]


def _font(size: int) -> ImageFont.FreeTypeFont:
    """The font bundled with Pillow, at a size; it needs Pillow built with FreeType."""
    font = ImageFont.load_default(size=size)
    if not isinstance(font, ImageFont.FreeTypeFont):
        raise RuntimeError("Pillow has no FreeType support; the scanned page cannot be rendered")
    return font


def render_png(doc: Doc) -> Image.Image:
    """A page at 150 dpi: the memo text, rotated slightly, with speckle noise."""
    width, height, margin = 1240, 1754, 130
    page = Image.new("L", (width, height), 255)
    draw = ImageDraw.Draw(page)
    sizes = {1: 40, 2: 30, 0: 27}
    fonts = {level: _font(size) for level, size in sizes.items()}
    y = margin
    for block in blocks(doc.body):
        if block.kind not in ("heading", "para", "item"):
            continue
        level = block.level if block.kind == "heading" else 0
        font = fonts[level]
        if level:
            y += 18
        for line in _wrap(draw, plain(block.text), font, width - 2 * margin):
            draw.text((margin, y), line, fill=20, font=font)
            y += int(sizes[level] * 1.45)
        y += 16
    if y > height - margin:
        raise ValueError(f"{doc.path}: the text does not fit on one scanned page")
    page = page.rotate(
        ROTATION_DEGREES, resample=Image.Resampling.BICUBIC, expand=False, fillcolor=255
    )
    noise = _noise_stream(6000 * 5)
    pixels = page.load()
    if pixels is None:
        raise RuntimeError("Pillow returned no pixel access for the scanned page")
    for n in range(6000):
        x0, x1, y0, y1, shade = noise[n * 5 : n * 5 + 5]
        x = (x0 << 8 | x1) % width
        yy = (y0 << 8 | y1) % height
        pixels[x, yy] = 90 + shade % 120
    return page


def png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", dpi=(150, 150))
    return buffer.getvalue()


def pixel_sha256(data: bytes) -> str:
    with Image.open(io.BytesIO(data)) as image:
        return sha256(image.convert("L").tobytes())


# ---------------------------------------------------------------- build


def outputs(root: Path) -> dict[str, bytes]:
    """Every generated file, by its path relative to the repo root."""
    pdf_doc = read_doc(root, PDF_SOURCE)
    html_doc = read_doc(root, HTML_SOURCE)
    png_doc = read_doc(root, PNG_SOURCE)
    return {
        PDF_SOURCE.removesuffix(".md") + ".pdf": render_pdf(pdf_doc),
        HTML_SOURCE.removesuffix(".md") + ".html": render_html(html_doc),
        PNG_SOURCE.removesuffix(".md") + ".png": png_bytes(render_png(png_doc)),
        PNG_SOURCE.removesuffix(".md") + ".gt.txt": ground_truth(png_doc).encode("utf-8"),
    }


def manifest(root: Path, files: dict[str, bytes]) -> dict[str, object]:
    sources = {
        ".pdf": PDF_SOURCE,
        ".html": HTML_SOURCE,
        ".png": PNG_SOURCE,
        ".gt.txt": PNG_SOURCE,
    }
    entries: list[dict[str, object]] = []
    for path, data in files.items():
        suffix = ".gt.txt" if path.endswith(".gt.txt") else Path(path).suffix
        source = sources[suffix]
        entry: dict[str, object] = {
            "path": path,
            "source": source,
            "source_sha256": sha256((root / source).read_bytes()),
            "sha256": sha256(data),
        }
        if suffix == ".pdf":
            texts = pdf_page_texts(data)
            entry["pages"] = len(texts)
            entry["text_sha256"] = sha256("\f".join(texts).encode("utf-8"))
        elif suffix == ".html":
            entry["text_sha256"] = sha256(html_text(data).encode("utf-8"))
        elif suffix == ".png":
            entry["pages"] = 1
            entry["pixel_sha256"] = pixel_sha256(data)
        entries.append(entry)
    pages = {doc.front["id"]: print_pages(doc) for doc in corpus_docs(root)}
    return {
        "generator": "scripts/build_corpus.py",
        "build_date": BUILD_DATE.date().isoformat(),
        "libraries": {
            "fpdf2": version("fpdf2"),
            "pillow": version("pillow"),
            "pypdf": version("pypdf"),
            "freetype2": features.version("freetype2"),
        },
        "fonts": {
            "pdf": "Helvetica, a PDF core font (not embedded)",
            "png": "Aileron Regular, bundled with the pinned Pillow",
        },
        "files": entries,
        "print_pages": {
            "layout": "A4, 20 mm margins, Helvetica 10.5 pt body (the PDF layout)",
            "documents": pages,
            "total": sum(pages.values()),
        },
    }


def build(source_root: Path, out_root: Path) -> dict[str, object]:
    """Render source_root's Markdown into out_root (same relative paths); return the manifest."""
    files = outputs(source_root)
    for path, data in files.items():
        target = out_root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    data = manifest(source_root, files)
    (out_root / MANIFEST).parent.mkdir(parents=True, exist_ok=True)
    (out_root / MANIFEST).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return data


def check(root: Path) -> list[str]:
    """Differences between the committed generated files and a fresh build."""
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        fresh = build(root, Path(tmp))
        committed = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
        if fresh != committed:
            problems.append(f"{MANIFEST} differs from a fresh build")
        for path in outputs(root):
            if path.endswith(".png"):
                same = pixel_sha256((root / path).read_bytes()) == pixel_sha256(
                    (Path(tmp) / path).read_bytes()
                )
            else:
                same = (root / path).read_bytes() == (Path(tmp) / path).read_bytes()
            if not same:
                problems.append(f"{path} differs from a fresh build")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--out", type=Path, help="write into this directory instead of the repo")
    parser.add_argument("--check", action="store_true", help="compare a fresh build, write nothing")
    args = parser.parse_args(argv)
    if args.check:
        problems = check(ROOT)
        for problem in problems:
            print(problem)
        print("corpus build: " + ("out of date" if problems else "up to date"))
        return 1 if problems else 0
    data = build(ROOT, args.out or ROOT)
    print(f"corpus build: done; print pages {json.dumps(data['print_pages'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
