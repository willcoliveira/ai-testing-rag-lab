"""The corpus build is deterministic and the committed files are what it produces (S1a AC3, AC7).

A rebuild into a temp directory gives the same PDF, HTML and ground truth (bytes and extracted
text), and the same PNG pixels when FreeType is the version the manifest records (PNG file bytes
depend on the zlib build, so pixels are compared instead).
"""

import hashlib
import io
import json
from functools import cache

import pytest
from PIL import Image, features

from tests.conftest import ROOT, load_script
from tests.corpus_text import documents, norm

pytestmark = pytest.mark.unit

PDF = "corpus/tenant-a/password-standard-v2.pdf"
HTML = "corpus/tenant-a/mfa-standard.html"
PNG = "corpus/tenant-a/device-policy-annex-b-kiosk.png"
GT = "corpus/tenant-a/device-policy-annex-b-kiosk.gt.txt"
MANIFEST = "corpus/build-manifest.json"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@cache
def committed_manifest() -> dict[str, object]:
    return json.loads((ROOT / MANIFEST).read_text(encoding="utf-8"))


def manifest_files() -> dict[str, dict[str, object]]:
    return {str(e["path"]): e for e in committed_manifest()["files"]}  # type: ignore[union-attr]


@pytest.fixture(scope="module")
def rebuilt(tmp_path_factory: pytest.TempPathFactory):
    out = tmp_path_factory.mktemp("corpus-build")
    data = load_script("build_corpus").build(ROOT, out)
    return out, data


def test_manifest_lists_every_generated_file_with_its_sha256():
    files = manifest_files()
    assert set(files) == {PDF, HTML, PNG, GT}
    for path, entry in files.items():
        assert entry["sha256"] == sha((ROOT / path).read_bytes()), f"{path} changed since the build"
        source = ROOT / str(entry["source"])
        assert entry["source_sha256"] == sha(source.read_bytes()), (
            f"{entry['source']} changed since the build: run scripts/build_corpus.py"
        )


def test_rebuild_gives_the_same_pdf_and_text(rebuilt):
    out, _ = rebuilt
    build = load_script("build_corpus")
    fresh = (out / PDF).read_bytes()
    kept = (ROOT / PDF).read_bytes()
    assert build.pdf_page_texts(fresh) == build.pdf_page_texts(kept)
    assert sha(fresh) == sha(kept), "PDF bytes differ (fixed date, core font, no compression)"


def test_rebuild_gives_the_same_html_and_ground_truth(rebuilt):
    out, _ = rebuilt
    build = load_script("build_corpus")
    assert build.html_text((out / HTML).read_bytes()) == build.html_text((ROOT / HTML).read_bytes())
    assert (out / HTML).read_bytes() == (ROOT / HTML).read_bytes()
    assert (out / GT).read_bytes() == (ROOT / GT).read_bytes()


def test_rebuild_gives_the_same_png(rebuilt):
    out, _ = rebuilt
    with Image.open(out / PNG) as fresh, Image.open(ROOT / PNG) as kept:
        assert fresh.size == kept.size
        same_freetype = committed_manifest()["libraries"]["freetype2"] == features.version(  # type: ignore[index]
            "freetype2"
        )
        if same_freetype:
            assert sha(fresh.convert("L").tobytes()) == sha(kept.convert("L").tobytes())
    assert manifest_files()[PNG]["pixel_sha256"] == load_script("build_corpus").pixel_sha256(
        (ROOT / PNG).read_bytes()
    )


def test_rebuilt_manifest_matches(rebuilt):
    _, fresh = rebuilt
    kept = committed_manifest()
    if kept["libraries"]["freetype2"] != features.version("freetype2"):  # type: ignore[index]
        pytest.skip("another FreeType build renders other PNG pixels; compared above")
    assert fresh == kept


def test_pdf_has_the_four_marked_pages_with_their_sections():
    build = load_script("build_corpus")
    pages = build.pdf_page_texts((ROOT / PDF).read_bytes())
    doc = documents()["A-PWD-V2"]
    assert len(pages) == doc.front["pages"] == manifest_files()[PDF]["pages"] == 4
    for sid, section in doc.sections().items():
        heading = next(
            line for line in doc.body.splitlines() if line.lstrip("#").startswith(f" {sid} ")
        ).lstrip("# ")
        assert section.page is not None, sid
        assert norm(heading) in norm(pages[section.page - 1]), f"{sid} not on page {section.page}"
    assert "Table 1: Sign-in protection values" in pages[2]
    assert "Adapted from strongdm/comply (Apache-2.0)" in norm(pages[3])


def test_html_export_has_an_anchor_per_section():
    html = (ROOT / HTML).read_text(encoding="utf-8")
    doc = documents()["A-MFA"]
    for sid in doc.sections():
        assert f'id="sec-{sid.replace(".", "-")}"' in html, sid
    assert '<meta name="corpus-id" content="A-MFA">' in html


def test_scanned_page_ground_truth_is_stored():
    text = (ROOT / GT).read_text(encoding="utf-8")
    build = load_script("build_corpus")
    doc = build.read_doc(ROOT, "corpus/tenant-a/device-policy-annex-b-kiosk.md")
    assert text == build.ground_truth(doc)
    assert "Kiosk sessions sign out automatically after 5 minutes of inactivity." in text
    with Image.open(io.BytesIO((ROOT / PNG).read_bytes())) as image:
        assert image.size == (1240, 1754)


def test_print_page_count_covers_every_document():
    pages = committed_manifest()["print_pages"]
    assert set(pages["documents"]) == set(documents())  # type: ignore[index]
    assert pages["total"] == sum(pages["documents"].values())  # type: ignore[index]
