"""AC3: OCR of the scanned page is within the stated character error rate of its ground truth,
and the rule that lives only on that page (F-33) is extracted.

Measured on 2026-10-06 (the S1b ledger records the runs): CER 0.22% with Tesseract 5.5.3
(Homebrew, macOS arm64) and 0.11% with Tesseract 5.3.4 (Ubuntu 24.04 package 5.3.4-1build5, the
version pr-fast installs). TOLERANCE is the larger measured value plus a margin of 0.78 points,
1%: it allows a few more misread characters (the page has 896), and stays under the plan's
ceiling of 2%.
"""

import re

import pytest

from raglab.core.text import character_error_rate, edit_distance, normalise_space
from raglab.ingest import ocr
from tests.conftest import ROOT
from tests.ingestion_support import default_inventory, parsed, section_body

GROUND_TRUTH = ROOT / "corpus" / "tenant-a" / "device-policy-annex-b-kiosk.gt.txt"
MEASURED = 0.0022
MARGIN = 0.0078
TOLERANCE = MEASURED + MARGIN
CEILING = 0.02


@pytest.mark.ocr
def test_scanned_page_is_within_the_stated_cer_of_its_ground_truth():
    document = parsed("A-DEVICE-B")
    cer = character_error_rate(document.text(), GROUND_TRUTH.read_text(encoding="utf-8"))
    print(f"Tesseract {ocr.tesseract_version()}: CER {cer:.4%} (tolerance {TOLERANCE:.2%})")
    assert TOLERANCE <= CEILING
    assert cer <= TOLERANCE, f"CER {cer:.4%} is above the tolerance {TOLERANCE:.2%}"


@pytest.mark.ocr
def test_the_scanned_only_rule_is_extracted_in_its_section():
    document = parsed("A-DEVICE-B")
    heading, body = section_body(document, "1")
    assert heading is not None
    assert heading.text == "1 Automatic sign-out"
    assert "after 5 minutes of inactivity" in normalise_space(" ".join(b.text for b in body))
    assert [p.number for p in document.pages] == [1]


@pytest.mark.ocr
def test_the_scanned_page_keeps_its_title_and_sections():
    blocks = parsed("A-DEVICE-B").pages[0].blocks
    headings = [(b.level, b.text) for b in blocks if b.kind == "heading"]
    assert headings == [
        (1, "Device Policy Annex B: Shared Kiosk Devices"),
        (2, "1 Automatic sign-out"),
        (2, "2 Accounts on kiosks"),
        (2, "3 Faults"),
    ]


@pytest.mark.ocr
def test_the_tesseract_version_is_recorded_in_the_inventory():
    version = ocr.tesseract_version()
    assert re.fullmatch(r"\d+\.\d+\.\d+.*", version), version
    assert default_inventory().tools["tesseract"] == version


@pytest.mark.unit
@pytest.mark.parametrize(
    ("a", "b", "distance"),
    [("", "", 0), ("abc", "abc", 0), ("kitten", "sitting", 3), ("1T", "IT", 1), ("", "abc", 3)],
)
def test_edit_distance_on_hand_computed_cases(a, b, distance):
    assert edit_distance(a, b) == edit_distance(b, a) == distance


@pytest.mark.unit
def test_cer_ignores_line_breaks_and_counts_characters():
    reference = "From: IT Operations\nManager"
    assert character_error_rate("From: IT Operations Manager", reference) == 0
    assert character_error_rate("From: 1T Operations Manager", reference) == 1 / 27
    with pytest.raises(ValueError, match="empty"):
        character_error_rate("x", " \n")


@pytest.mark.unit
def test_ocr_output_becomes_title_headings_and_paragraphs():
    blocks = ocr.text_blocks(
        "Annex B: Kiosks\n\nTo: shift leads\nFrom: IT\n\n1 Automatic sign-out\n\n"
        "Kiosk sessions sign out after 5 minutes. Save your\nwork first.\n\n"
        "3 November 2025\n\n2.1 Accounts on kiosks\n\f"
    )
    assert [(b.kind, b.level, b.text) for b in blocks] == [
        ("heading", 1, "Annex B: Kiosks"),
        ("paragraph", 0, "To: shift leads From: IT"),
        ("heading", 2, "1 Automatic sign-out"),
        ("paragraph", 0, "Kiosk sessions sign out after 5 minutes. Save your work first."),
        ("paragraph", 0, "3 November 2025"),
        ("heading", 3, "2.1 Accounts on kiosks"),
    ]


@pytest.mark.unit
def test_an_ocr_heading_may_end_in_a_digit_but_a_date_is_not_a_heading():
    """S1B-J4: '1 Rule 5' opens section 1 (its text would otherwise fold into the section before
    and section 1 could not be cited); '3 November 2025' stays a paragraph."""
    blocks = ocr.text_blocks(
        "Title\n\n1 Rule 5\n\nRule five text.\n\n1.1 Sub rule\n\nText.\n\n"
        "3 November 2025\n\n12 May 2026\n\n2 Version 2\n"
    )
    assert [(b.kind, b.level, b.text) for b in blocks] == [
        ("heading", 1, "Title"),
        ("heading", 2, "1 Rule 5"),
        ("paragraph", 0, "Rule five text."),
        ("heading", 3, "1.1 Sub rule"),
        ("paragraph", 0, "Text."),
        ("paragraph", 0, "3 November 2025"),
        ("paragraph", 0, "12 May 2026"),
        ("heading", 2, "2 Version 2"),
    ]
