"""Every corpus file has a source and an allowed licence; the corpus follows its hygiene rules
(S1a AC3, AC4, AC9; corpus/SPEC.md sections 4 to 6 and 11)."""

import re
from datetime import date

import pytest

from tests.conftest import ROOT
from tests.corpus_text import CORPUS, documents

pytestmark = pytest.mark.unit

LICENCES = {"Apache-2.0", "CC-BY-4.0", "NIST-public", "OGL-UK-3.0"}
STATUSES = {"approved", "superseded", "reference", "test material", "support"}
SOURCE = re.compile(
    r"^(comply:[a-z]+\.md|ours|nist:sp800-63b-4|ncsc:password-policy-updating-your-approach)$"
)
REQUIRED = {"id", "title", "version", "tenant", "kind", "source", "licence", "effective", "status"}
CHANGED = re.compile(
    r"^Adapted from strongdm/comply themes/comply-soc2/policies/[a-z]+\.md \(Apache-2\.0, commit "
    r"aab4849\); rewritten (for the fictional company Halvenroot|for the fictional business unit "
    r"Mirrowfen|as attack test material derived from A-PWD-V2), values replaced with planted "
    r"values, sections renumbered\. Changed by the ai-testing-rag-lab authors, 2026-10-06\.$"
)
VISIBLE_CHANGE = (
    "Adapted from strongdm/comply (Apache-2.0); changed by the ai-testing-rag-lab authors."
)
EXCLUDED = re.compile(
    r"jupiterone|\bCIS\b|\bSANS\b|gitlab|CC[- ]BY[- ]SA|CC[- ]BY[- ]NC|BY-ND", re.I
)


def corpus_files() -> set[str]:
    return {
        p.relative_to(ROOT).as_posix()
        for p in CORPUS.rglob("*")
        if p.is_file() and p.name != ".DS_Store"
    }


def inventory() -> dict[str, dict[str, str]]:
    text = (CORPUS / "SOURCES.md").read_text(encoding="utf-8")
    table = text.split("## Inventory", 1)[1]
    rows = re.findall(r"^\| `([^`]+)` \|(.*)\|$", table, flags=re.M)
    out: dict[str, dict[str, str]] = {}
    for path, rest in rows:
        cells = [c.strip() for c in rest.split("|")]
        assert path not in out, f"{path} listed twice"
        columns = ["id", "status", "supersedes", "source", "licence", "notes"]
        out[path] = dict(zip(columns, cells, strict=True))
    return out


def test_every_corpus_file_is_listed_with_an_allowed_licence():
    listed = inventory()
    files = corpus_files()
    assert files - set(listed) == set(), "files missing from corpus/SOURCES.md"
    assert set(listed) - files == set(), "SOURCES.md lists files that do not exist"
    for path, row in listed.items():
        assert row["licence"] in LICENCES, f"{path}: licence {row['licence']}"
        assert row["status"] in STATUSES, f"{path}: status {row['status']}"


def test_inventory_matches_each_documents_front_matter():
    listed = inventory()
    for doc in documents().values():
        row = listed[doc.path]
        assert row["id"] == doc.id
        assert row["licence"] == doc.front["licence"], doc.path
        assert row["source"] == doc.front["source"], doc.path
    for path, row in listed.items():
        if row["id"] == "—":
            continue
        source = next(d for d in documents().values() if d.id == row["id"])
        if path != source.path:  # a generated file: its source's licence
            assert row["licence"] == source.front["licence"], path


REGISTER_STATUS = {
    ("company", "current"): "approved",
    ("company", "superseded"): "superseded",
    ("external", "current"): "reference",
    ("attack", "test-material"): "test material",
}


def test_register_statuses_and_supersedes_links():
    """The register (TEST-PLAN section 3) agrees with the corpus: each document's status follows
    its kind and front-matter status, its renderings share it, and the Supersedes column names
    exactly the superseded documents, each from a current document of the same tenant."""
    listed = inventory()
    docs = documents()
    for doc in docs.values():
        row = listed[doc.path]
        expected = REGISTER_STATUS[(str(doc.front["kind"]), str(doc.front["status"]))]
        assert row["status"] == expected, doc.path
        assert row["supersedes"] == str(doc.front.get("supersedes", "—")), doc.path
        for path, other in listed.items():
            if other["id"] == doc.id and other["status"] != "support":
                assert (other["status"], other["supersedes"]) == (
                    row["status"],
                    row["supersedes"],
                ), path
    links = {row["id"]: row["supersedes"] for row in listed.values() if row["supersedes"] != "—"}
    superseded = {d.id for d in docs.values() if listed[d.path]["status"] == "superseded"}
    assert set(links.values()) == superseded
    assert superseded, "the register names no superseded document"
    for new, old in links.items():
        assert listed[docs[new].path]["status"] == "approved", new
        assert docs[new].tenant == docs[old].tenant, new
        assert docs[old].front.get("superseded_by") == new, old


def test_no_file_derives_from_an_excluded_source():
    for path, row in inventory().items():
        assert not EXCLUDED.search(row["source"] + " " + row["licence"]), path
    for doc in documents().values():
        assert SOURCE.match(str(doc.front["source"])), doc.path
        assert not EXCLUDED.search(str(doc.front["source"])), doc.path


def test_apache_derived_files_carry_the_change_notes():
    assert (
        (CORPUS / "licenses" / "Apache-2.0.txt")
        .read_text(encoding="utf-8")
        .lstrip()
        .startswith("Apache License\n                           Version 2.0, January 2004")
    )
    derived = [d for d in documents().values() if str(d.front["source"]).startswith("comply:")]
    assert len(derived) == 9
    for doc in derived:
        assert doc.front["licence"] == "Apache-2.0", doc.path
        assert CHANGED.match(str(doc.front.get("changed", ""))), f"{doc.path}: changed line"
        assert VISIBLE_CHANGE in re.sub(r"\s+", " ", doc.body), f"{doc.path}: visible change line"


def test_licence_file_names_each_licence():
    text = (CORPUS / "LICENSE.md").read_text(encoding="utf-8")
    for licence in LICENCES:
        assert f"**{licence}**" in text, licence


def test_attack_files_are_labelled_as_test_material():
    listed = inventory()
    attacks = {d.path for d in documents().values() if d.front["kind"] == "attack"}
    assert attacks == {p for p in corpus_files() if p.startswith("corpus/attacks/")}
    assert len(attacks) == 3
    for path in attacks:
        assert listed[path]["status"] == "test material"
        assert "Deliberate test material" in listed[path]["notes"]
        front = next(d for d in documents().values() if d.path == path).front
        assert front["test_material"] is True
        assert front["status"] == "test-material"
        assert str(front["title"]).startswith("Attack test material:")
    assert "deliberate test material" in (CORPUS / "SOURCES.md").read_text(encoding="utf-8")


def test_pack_size():
    docs = documents().values()
    by_dir: dict[str, int] = {}
    for doc in docs:
        folder = doc.path.split("/")[1]
        by_dir[folder] = by_dir.get(folder, 0) + 1
    assert 12 <= by_dir["tenant-a"] <= 14
    assert by_dir == {**by_dir, "tenant-b": 2, "external": 2, "attacks": 3}


# ------------------------------------------------------------------ front matter and headings


def test_front_matter_fields_and_values():
    for doc in documents().values():
        f = doc.front
        assert not REQUIRED - set(f), f"{doc.path} lacks {REQUIRED - set(f)}"
        assert isinstance(f["version"], str), f"{doc.path}: version must be a quoted string"
        assert f["tenant"] in {"tenant-a", "tenant-b", "shared"}
        assert f["kind"] in {"company", "external", "attack"}
        assert f["licence"] in LICENCES
        assert f["status"] in {"current", "superseded", "test-material"}
        assert f["format"] in {"md", "pdf", "html", "png"}
        assert isinstance(f["effective"], date), doc.path
        assert (f["tenant"] == "shared") == (f["kind"] == "external"), doc.path
        if f["format"] in ("pdf", "png"):
            assert isinstance(f["pages"], int), doc.path
            assert f["pages"] == doc.body.count("<!-- page: "), doc.path
        if f["kind"] == "external":
            assert f["source_url"], doc.path
            assert f["attribution"], doc.path
            assert isinstance(f["retrieved"], date), doc.path
            assert re.sub(r"\s+", " ", str(f["attribution"])) in re.sub(r"\s+", " ", doc.body)
        if f["kind"] == "attack":
            assert f["attack"] in {"hidden-instruction", "poisoned-duplicate", "fake-update"}


def test_headings_start_with_unique_section_ids():
    for doc in documents().values():
        h1 = re.findall(r"^# (.+)$", doc.body, flags=re.M)
        assert len(h1) == 1, f"{doc.path}: {len(h1)} H1 headings"
        if doc.front["kind"] != "attack":
            assert h1[0] == doc.front["title"], doc.path
        ids = [m.group(1) for m in re.finditer(r"^#{2,3} (\S+) ", doc.body, flags=re.M)]
        assert ids, doc.path
        for sid in ids:
            assert re.fullmatch(r"(\d+(\.\d+)*|[A-Z](\.\d+)?|Q\d+)", sid), f"{doc.path}: {sid}"
        assert len(ids) == len(set(ids)), f"{doc.path}: duplicate section ids"


def test_company_documents_open_with_scope_and_end_with_document_control():
    for doc in documents().values():
        if doc.front["kind"] != "company" or doc.id == "A-DEVICE-B":
            continue  # Annex B is a signed memo (SPEC section 7 layout)
        titles = re.findall(r"^## (\S+) (.+)$", doc.body, flags=re.M)
        numbered = [title for sid, title in titles if sid[0].isdigit()]
        assert numbered[-1] == "Document control", doc.path
        if doc.id not in {"A-FAQ", "A-GLOSS"}:  # a list of questions and a list of terms
            assert titles[0] == ("1", "Purpose and scope"), doc.path


def test_document_control_matches_the_front_matter():
    """SPEC section 5: document control, the last numbered section, gives the front matter's
    version and effective date (labelled "Version:" and "Effective date:"), and a comply-derived
    file's visible change line is a paragraph of its own there."""
    for doc in documents().values():
        if doc.front["kind"] != "company" or doc.id == "A-DEVICE-B":
            continue
        numbered = [s for s in doc.sections().values() if s.level == 2 and s.id[0].isdigit()]
        control = numbered[-1]
        text = control.text.replace("**", "")
        version = re.search(r"\bVersion: (\d+(?:\.\d+)*)", text)
        effective = re.search(r"\bEffective date: (\d{4}-\d{2}-\d{2})\b", text)
        assert version, f"{doc.path}: no version in document control"
        assert version.group(1) == doc.front["version"], doc.path
        assert effective, f"{doc.path}: no effective date in document control"
        assert effective.group(1) == str(doc.front["effective"]), doc.path
        if str(doc.front["source"]).startswith("comply:"):
            paragraphs = [re.sub(r"\s+", " ", p) for p in control.paragraphs()]
            assert VISIBLE_CHANGE in paragraphs, f"{doc.path}: change line is not a paragraph"


# ------------------------------------------------------------------ hygiene


def corpus_text() -> dict[str, str]:
    return {
        p: (ROOT / p).read_text(encoding="utf-8")
        for p in corpus_files()
        if p.endswith((".md", ".yaml", ".txt", ".html", ".json"))
        and p != "corpus/licenses/Apache-2.0.txt"
    }


def test_every_email_phone_and_token_is_visibly_fake():
    for path, text in corpus_text().items():
        for email in re.findall(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", text):
            assert re.search(r"(^|\.|@)example\.(com|org)$", email), f"{path}: {email}"
        for phone in re.findall(r"\+\d[\d -]{8,}\d|\b\d{3}[ -]\d{3}[ -]\d{4}\b", text):
            assert re.search(r"555-01\d\d$", phone), f"{path}: {phone}"
        for token in re.findall(r"\b[A-Z][A-Z0-9]*(?:-[A-Z0-9]+){2,}\b", text):
            if len(token) >= 14 and re.search(r"\d", token):
                assert token.startswith("FAKE-"), f"{path}: {token}"


def test_no_personal_names_vendor_names_or_placeholders():
    vendors = re.compile(r"\b(slack|gmail|okta|microsoft|google|duo|lastpass|1password)\b", re.I)
    for doc in documents().values():
        if doc.front["kind"] == "external":
            continue
        assert not vendors.search(doc.body), f"{doc.path}: vendor name"
        assert "<insert" not in doc.body.lower(), f"{doc.path}: comply placeholder"


def test_comply_values_were_replaced():
    replaced = [
        "five business days",
        "weekly email report",
        "each month",
        "every five years",
        "48 hours",
        "twice per year",
        "monthly",
        "quarterly",
        "every six months",
    ]
    for doc in documents().values():
        if not str(doc.front["source"]).startswith("comply:"):
            continue
        for phrase in replaced:
            assert phrase not in doc.body.lower(), f"{doc.path}: comply value {phrase!r}"
