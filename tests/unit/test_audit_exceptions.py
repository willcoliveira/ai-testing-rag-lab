"""The advisories `make audit` skips (the Makefile's AUDIT_SKIP) reach pip-audit, and the exception
has a review date: once the date passes this test fails, so the exception is looked at again, not
kept by default (decision of 2026-10-21, "Dependency PR, Pillow exception (Recommended)").
"""

import datetime as dt
import re

import pytest

from tests.conftest import ROOT

pytestmark = pytest.mark.unit

MAKEFILE = (ROOT / "Makefile").read_text(encoding="utf-8")


def skipped() -> list[str]:
    match = re.search(r"^AUDIT_SKIP := (.*(?:\\\n.*)*)$", MAKEFILE, flags=re.MULTILINE)
    assert match, "the Makefile defines AUDIT_SKIP"
    return match.group(1).replace("\\\n", " ").split()


def test_every_skip_reaches_pip_audit():
    recipe = re.search(r"^audit:\n((?:\t.*\n)+)", MAKEFILE, flags=re.MULTILINE)
    assert recipe, "the Makefile has an audit target"
    assert "pip-audit --skip-editable $(foreach id,$(AUDIT_SKIP),--ignore-vuln $(id))" in (
        recipe.group(1)
    )
    assert skipped(), "AUDIT_SKIP names the advisories it skips"


def test_every_skip_reaches_the_deepeval_tools_audit_too():
    """S5 (criteria judge, S5-J7): tools/deepeval-check's lock resolves the same Pillow through
    raglab, so the audit of its exported requirements skips the same advisories."""
    recipe = re.search(r"^audit:\n((?:\t.*\n)+)", MAKEFILE, flags=re.MULTILINE)
    assert recipe, "the Makefile has an audit target"
    assert (
        "pip-audit -r runs/tmp/deepeval-check.requirements.txt --disable-pip --require-hashes "
        "$(foreach id,$(AUDIT_SKIP),--ignore-vuln $(id))"
    ) in recipe.group(1)


def test_the_exception_is_reviewed_by_its_date():
    review = re.search(r"Review by (\d{4}-\d{2}-\d{2})", MAKEFILE)
    assert review, "the Makefile's audit exception carries a review date"
    assert dt.date.today() <= dt.date.fromisoformat(review.group(1)), (
        f"the audit exception's review date {review.group(1)} has passed: check whether Pillow 13 "
        "can be used now (fastembed's pin), then drop the skips or set a new date with its reason"
    )
