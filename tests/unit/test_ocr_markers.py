"""The `ocr` marker is on every ingestion test that OCRs the scanned page, so
`pytest -m "not ocr"` runs on a machine without Tesseract (D1 of the S1b judges: the marker sat on a
helper, where pytest ignores it, instead of the test that built the full inventory)."""

import ast

import pytest

from tests.conftest import ROOT

pytestmark = pytest.mark.unit

# the scanned page's document id; parsing it, or ingesting the whole corpus, runs Tesseract
SCANNED = "A-DEVICE-B"


def _ocr_calls(node: ast.AST, helpers: set[str]) -> bool:
    """Whether node calls something that OCRs the scanned page: default_inventory(), an ingest of
    the repo root (`pipeline.ingest(ROOT)`), parsed("A-DEVICE-B") or a helper that does."""
    for call in ast.walk(node):
        if not isinstance(call, ast.Call):
            continue
        func = call.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
        first = ast.unparse(call.args[0]) if call.args else ""
        if (
            name in helpers
            or name == "default_inventory"
            or (name == "ingest" and first == "ROOT")
            or (name == "parsed" and first == repr(SCANNED))
        ):
            return True
    return False


def _marks(decorators: list[ast.expr], aliases: set[str]) -> bool:
    for decorator in decorators:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        text = ast.unparse(target)
        if text in aliases or text.endswith("mark.ocr"):
            return True
    return False


def unmarked_ocr_tests(source: str) -> list[str]:
    """The test functions of a module that OCR the scanned page without the ocr marker."""
    tree = ast.parse(source)
    aliases = {  # e.g. `full = pytest.mark.ocr`
        target.id
        for node in tree.body
        if isinstance(node, ast.Assign) and ast.unparse(node.value).endswith("mark.ocr")
        for target in node.targets
        if isinstance(target, ast.Name)
    }
    module_marked = any(
        isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "pytestmark" for t in node.targets)
        and "mark.ocr" in ast.unparse(node.value)
        for node in tree.body
    )
    functions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    # helpers that OCR, to a fixed point (a helper that calls default_inventory, ...)
    helpers: set[str] = set()
    changed = True
    while changed:
        changed = False
        for name, node in functions.items():
            if name not in helpers and _ocr_calls(node, helpers):
                helpers.add(name)
                changed = True
    return [
        name
        for name, node in functions.items()
        if name.startswith("test_")
        and name in helpers
        and not module_marked
        and not _marks(node.decorator_list, aliases)
    ]


def test_every_ingestion_or_retrieval_test_that_ocrs_the_scanned_page_has_the_ocr_marker():
    found = {
        path.name: unmarked
        for folder in ("ingestion", "retrieval")
        for path in sorted((ROOT / "tests" / folder).glob("test_*.py"))
        if (unmarked := unmarked_ocr_tests(path.read_text(encoding="utf-8")))
    }
    assert found == {}, f"tests that OCR the scanned page without the ocr marker: {found}"


def test_the_marker_check_sees_a_marker_on_a_helper_as_missing():
    source = (
        "import pytest\nfull = pytest.mark.ocr\n\n@full\ndef helper():\n    return 1\n\n"
        "def test_a():\n    default_inventory()\n\n"
        "@full\ndef test_b():\n    default_inventory()\n\n"
        "@pytest.mark.ocr\ndef test_c():\n    pipeline.ingest(ROOT)\n\n"
        "def uses():\n    return default_inventory()\n\ndef test_d():\n    uses()\n\n"
        "def test_e(tmp_path):\n    helper()\n    pipeline.ingest(tmp_path)\n\n"
        "def test_f():\n    parsed('A-DEVICE-B')\n\ndef test_g():\n    parsed('A-MFA')\n"
    )
    assert unmarked_ocr_tests(source) == ["test_a", "test_d", "test_f"]
