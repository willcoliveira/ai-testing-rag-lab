"""YAML front matter of a corpus Markdown file (corpus/SPEC.md, section 4)."""

import datetime
import re
from pathlib import Path
from typing import cast

import yaml

FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---(?:\n|\Z)", flags=re.S)


class FrontMatterError(ValueError):
    pass


def normalise_newlines(text: str) -> str:
    """CRLF and lone CR line ends as LF, and no byte-order mark."""
    return text.removeprefix("﻿").replace("\r\n", "\n").replace("\r", "\n")


def split(text: str, where: str) -> tuple[dict[str, str], str]:
    """(front matter, body) of a Markdown file's text. Every value is a string (dates in ISO
    form); a file without front matter, or with front matter that is not a flat mapping, fails."""
    text = normalise_newlines(text)
    match = FRONT_MATTER.match(text)
    if not match:
        raise FrontMatterError(f"{where}: no front matter (a --- block at the top)")
    try:
        data: object = yaml.safe_load(match.group(1))
    except yaml.YAMLError as error:
        raise FrontMatterError(f"{where}: front matter is not valid YAML: {error}") from error
    if not isinstance(data, dict):
        raise FrontMatterError(f"{where}: front matter is not a mapping")
    front: dict[str, str] = {}
    for key, value in cast(dict[object, object], data).items():
        if isinstance(value, dict | list) or value is None:
            raise FrontMatterError(f"{where}: front matter field {key!r} is not a single value")
        if isinstance(value, datetime.date):
            value = value.isoformat()
        front[str(key)] = str(value)
    return front, text[match.end() :]


def read(path: Path, where: str) -> dict[str, str]:
    """The front matter of the Markdown file at path."""
    return split(path.read_text(encoding="utf-8"), where)[0]
