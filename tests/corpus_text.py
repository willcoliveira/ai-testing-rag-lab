"""Read the corpus as the answer key cites it: documents, sections, paragraphs, tables, pages."""

import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import yaml

from tests.conftest import ROOT

CORPUS = ROOT / "corpus"
DOC_DIRS = ("tenant-a", "tenant-b", "external", "attacks")
HEADING = re.compile(r"^(#{1,3}) (\S+)(?: (.*))?$")
PAGE_MARKER = re.compile(r"^<!-- page: (\d+) -->$")


def norm(text: str) -> str:
    """Whitespace runs as one space, Markdown bold markers removed."""
    return re.sub(r"\s+", " ", text.replace("**", "")).strip()


@dataclass(frozen=True)
class Section:
    id: str
    level: int
    text: str  # the lines under the heading, up to the next heading of any level
    page: int | None

    def paragraphs(self) -> list[str]:
        """Blocks separated by blank lines, without page markers and comment-only blocks."""
        blocks = [b.strip() for b in re.split(r"\n\s*\n", self.text)]
        return [b for b in blocks if b and not PAGE_MARKER.match(b) and not b.startswith("<!--")]

    def table(self, caption: str) -> list[dict[str, str]]:
        """The rows of the table whose caption line is `caption`, as dicts by header."""
        lines = self.text.splitlines()
        start = lines.index(caption)
        rows = [line for line in lines[start + 1 :] if line.strip()]
        table: list[list[str]] = []
        for line in rows:
            if not line.startswith("|"):
                break
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if not all(re.fullmatch(r":?-+:?", c) for c in cells):
                table.append(cells)
        header, *body = table
        return [dict(zip(header, row, strict=True)) for row in body]


@dataclass(frozen=True)
class Document:
    path: str
    front: dict[str, object]
    body: str

    @property
    def id(self) -> str:
        return str(self.front["id"])

    @property
    def tenant(self) -> str:
        return str(self.front["tenant"])

    def sections(self) -> dict[str, Section]:
        out: dict[str, Section] = {}
        page: int | None = None
        current: tuple[str, int, int | None] | None = None
        lines: list[str] = []
        for line in [*self.body.splitlines(), "# END"]:
            if marker := PAGE_MARKER.match(line):
                page = int(marker.group(1))
            heading = HEADING.match(line)
            if heading:
                if current is not None:
                    sid, level, at = current
                    assert sid not in out, f"{self.path}: section {sid} twice"
                    out[sid] = Section(sid, level, "\n".join(lines), at)
                level = len(heading.group(1))
                current = (heading.group(2), level, page) if level > 1 else None
                lines = []
            else:
                lines.append(line)
        return out


def parse(path: Path) -> Document:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, flags=re.S)
    assert match, f"{path}: no front matter"
    front = yaml.safe_load(match.group(1))
    return Document(path.relative_to(ROOT).as_posix(), front, text[match.end() :])


@cache
def documents() -> dict[str, Document]:
    """Every corpus document by id (the Markdown files under the four document folders)."""
    docs = [parse(p) for d in DOC_DIRS for p in sorted((CORPUS / d).glob("*.md"))]
    by_id = {d.id: d for d in docs}
    assert len(by_id) == len(docs), "duplicate document ids"
    return by_id


@cache
def answer_key() -> dict[str, object]:
    return yaml.safe_load((CORPUS / "answer-key.yaml").read_text(encoding="utf-8"))
