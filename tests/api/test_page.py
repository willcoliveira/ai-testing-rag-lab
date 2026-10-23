"""S3 AC10: the page. Its inputs have labels, the keyboard order is the reading order (no
tabindex), it carries no inline script, style or event handler, and its script writes text only.
Lab practice: axe and a browser come with Track B; this checks what a parser can."""

import re
from html.parser import HTMLParser

import pytest
from fastapi.testclient import TestClient

from raglab.api.app import WEB, VersionInfo, create_app
from raglab.generate.pipeline import PROMPT_VERSION
from tests.generation_support import TOKENS, small_pipeline

pytestmark = pytest.mark.unit
FOCUSABLE = {"a", "button", "input", "select", "textarea"}


class Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.labels: dict[str, str] = {}
        self.focusable: list[tuple[str, dict[str, str | None]]] = []
        self.scripts: list[dict[str, str | None]] = []
        self.attributes: list[str] = []
        self.inline: list[str] = []
        self._label: str | None = None
        self._in_script = False

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        self.attributes += list(attributes)
        if tag == "label":
            self._label = attributes.get("for")
        if tag in FOCUSABLE:
            self.focusable.append((tag, attributes))
        if tag == "script":
            self.scripts.append(attributes)
            self._in_script = True
        if tag == "style":
            self.inline.append("style element")

    def handle_endtag(self, tag):
        if tag == "label":
            self._label = None
        if tag == "script":
            self._in_script = False

    def handle_data(self, data):
        if self._label and data.strip():
            self.labels[self._label] = data.strip()
        if self._in_script and data.strip():
            self.inline.append(data)


def page() -> Page:
    parsed = Page()
    parsed.feed((WEB / "index.html").read_text(encoding="utf-8"))
    return parsed


def test_every_input_has_a_label():
    parsed = page()
    controls = [a for tag, a in parsed.focusable if tag in {"input", "select", "textarea"}]
    assert [c["id"] for c in controls] == ["tenant", "question"]
    assert parsed.labels == {"tenant": "Tenant", "question": "Question"}


def test_the_keyboard_order_is_tenant_question_ask():
    parsed = page()
    assert [(tag, a.get("id")) for tag, a in parsed.focusable] == [
        ("select", "tenant"),
        ("textarea", "question"),
        ("button", "submit"),
    ]
    assert "tabindex" not in parsed.attributes
    question = dict(parsed.focusable)["textarea"]
    assert question["maxlength"] == "500"


def test_no_inline_script_style_or_handler():
    parsed = page()
    assert parsed.inline == []
    assert parsed.scripts == [{"type": "module", "src": "app.js"}]
    assert not [a for a in parsed.attributes if a.startswith("on") or a == "style"]


def test_the_script_writes_text_never_html():
    script = (WEB / "app.js").read_text(encoding="utf-8")
    for sink in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval("):
        assert sink not in script, sink
    assert "textContent" in script
    assert re.search(r'fetch\("/ask"', script)


def test_the_served_page_is_the_file_with_the_csp():
    pipeline, _ = small_pipeline()
    info = VersionInfo("0", "0", PROMPT_VERSION, "fake", "fake-echo", "fake", "fake")
    api = TestClient(create_app(pipeline, info, TOKENS))
    response = api.get("/")
    assert response.text == (WEB / "index.html").read_text(encoding="utf-8")
    assert response.headers["content-type"].startswith("text/html")
    assert "script-src 'self'" in response.headers["content-security-policy"]
    assert api.get("/app.js").headers["content-type"].startswith("text/javascript")
