"""The answer key matches the corpus and the requirements (S1a AC2, AC5, AC6).

Every planted feature in corpus/answer-key.yaml has its fields, cites places that exist, and its
values are found verbatim there, in the Markdown and in the rendered PDF, HTML and scanned page.
Omissions are absent everywhere, the planted conflicts really differ, and every requirement of
docs/TEST-PLAN.md is covered by a feature or listed as a gap.
"""

import re
from functools import cache
from typing import Any

import pytest

from tests.conftest import ROOT, load_script
from tests.corpus_text import Document, answer_key, documents, norm

pytestmark = pytest.mark.unit

EXPECTED = {"answer", "abstain", "flag-conflict", "refuse-and-help"}
TENANTS = {"tenant-a", "tenant-b"}
FEATURE_FIELDS = {"id", "kind", "expected", "tenants", "requirements", "reference_answer"}
OPTIONAL_FIELDS = {"locations", "conflict", "must_not_appear", "answer_must_not_contain"}
LOCATION_FIELDS = {"doc", "path", "version", "section", "values"}
OPTIONAL_LOCATION_FIELDS = {"page", "paragraph", "table", "side", "exclusive"}
CONFLICT_SIDES = {
    "version": {"old", "new"},
    "external": {"company", "external"},
    "tenant": {"tenant-a", "tenant-b"},
}
NEGATION = re.compile(r"\b(not|no|never|SHALL NOT|harms)\b")


def features() -> list[dict[str, Any]]:
    return answer_key()["features"]  # type: ignore[return-value]


def locations() -> list[tuple[str, dict[str, Any]]]:
    return [(f["id"], loc) for f in features() for loc in f.get("locations", [])]


def register() -> dict[str, list[str]]:
    """The register rows of corpus/SPEC.md section 8, by F-id, as their cells."""
    text = (ROOT / "corpus" / "SPEC.md").read_text(encoding="utf-8")
    section = text.split("## 8. Planted-value register", 1)[1].split("\n## ", 1)[0]
    rows = re.findall(r"^\| (F-\d+) \|(.*)\|$", section, flags=re.M)
    return {fid: [c.strip() for c in rest.split("|")] for fid, rest in rows}


def plan_text() -> str:
    return (ROOT / "docs" / "TEST-PLAN.md").read_text(encoding="utf-8")


def expand(cell: str) -> set[str]:
    """F-ids in a traceability cell: "F-24 to F-31, F-50" as a set of ids."""
    out: set[str] = set()
    for lo, hi in re.findall(r"F-(\d+) to F-(\d+)", cell):
        out |= {f"F-{n:02d}" for n in range(int(lo), int(hi) + 1)}
    out |= set(re.findall(r"F-\d+", re.sub(r"F-\d+ to F-\d+", "", cell)))
    return out


def traceability() -> dict[str, set[str]]:
    section = plan_text().split("## 8. Traceability", 1)[1].split("### Gaps", 1)[0]
    rows = re.findall(r"^\| (R-\d+) \| [^|]+ \| ([^|]+) \|", section, flags=re.M)
    return {rid: expand(cell) for rid, cell in rows}


def plan_gaps() -> set[str]:
    section = plan_text().split("### Gaps", 1)[1].split("\n# ", 1)[0]
    return set(re.findall(r"^\| (R-\d+) \|", section, flags=re.M))


def plan_requirements() -> set[str]:
    part1 = plan_text().split("# Part 2", 1)[0]
    return set(re.findall(r"^\| (R-\d+) \| (?:[MS] \| )?\*\*", part1, flags=re.M))


def section_text(doc: Document, section: str) -> str:
    if section == "body":
        return doc.body
    sections = doc.sections()
    assert section in sections, f"{doc.id} has no section {section}"
    return sections[section].text


@cache
def pdf_pages() -> list[str]:
    build = load_script("build_corpus")
    return build.pdf_page_texts((ROOT / "corpus/tenant-a/password-standard-v2.pdf").read_bytes())


@cache
def html_export() -> str:
    build = load_script("build_corpus")
    return build.html_text((ROOT / "corpus/tenant-a/mfa-standard.html").read_bytes())


def rendered_text(doc: Document) -> str:
    """The text ingestion reads for a document whose format is not Markdown, else the body."""
    fmt = doc.front["format"]
    if fmt == "pdf":
        return "\n".join(pdf_pages())
    if fmt == "html":
        return html_export()
    if fmt == "png":
        return (ROOT / doc.path.replace(".md", ".gt.txt")).read_text(encoding="utf-8")
    return doc.body


# ------------------------------------------------------------------ schema


def test_key_has_one_entry_per_register_row():
    ids = [f["id"] for f in features()]
    assert len(ids) == len(set(ids)), "duplicate feature ids"
    assert set(ids) == set(register()), "answer key ids differ from the SPEC register"


def test_every_feature_has_its_fields():
    for f in features():
        missing = FEATURE_FIELDS - set(f)
        assert not missing, f"{f['id']} lacks {missing}"
        assert set(f) <= FEATURE_FIELDS | OPTIONAL_FIELDS, f"{f['id']} has unknown fields"
        assert re.fullmatch(r"F-\d{2}", f["id"])
        assert f["expected"] in EXPECTED, f["id"]
        assert f["tenants"], f["id"]
        assert set(f["tenants"]) <= TENANTS, f["id"]
        assert f["requirements"], f["id"]
        assert all(re.fullmatch(r"R-\d{2}", r) for r in f["requirements"]), f["id"]
        assert isinstance(f["reference_answer"], str), f["id"]
        assert f["reference_answer"].strip(), f["id"]
        if f["expected"] == "abstain" or f["kind"] == "omission":
            assert f.get("must_not_appear"), f"{f['id']}: an omission names what must not appear"
        else:
            assert f.get("locations"), f"{f['id']} cites no location"


def test_key_matches_register_expected_and_requirements():
    rows = register()
    for f in features():
        cells = rows[f["id"]]
        # cells: kind, document, section, value, expected, tenant, R-ids, reference answer
        assert f["expected"] == cells[4], f"{f['id']}: expected differs from the register"
        assert f["requirements"] == [r.strip() for r in cells[6].split(",")], f["id"]
        register_tenants = {"tenant-" + t.strip().lower() for t in cells[5].split(",")}
        assert set(f["tenants"]) == register_tenants, f["id"]


def test_every_location_has_its_fields():
    for fid, loc in locations():
        missing = LOCATION_FIELDS - set(loc)
        assert not missing, f"{fid} location lacks {missing}"
        assert set(loc) <= LOCATION_FIELDS | OPTIONAL_LOCATION_FIELDS, f"{fid}: unknown fields"
        assert loc["values"], fid
        assert all(isinstance(v, str) and v for v in loc["values"]), fid


# ------------------------------------------------------------------ lookups


def test_cited_documents_exist_with_path_and_version():
    docs = documents()
    for fid, loc in locations():
        assert loc["doc"] in docs, f"{fid}: no document {loc['doc']}"
        doc = docs[loc["doc"]]
        assert loc["path"] == doc.path, f"{fid}: path of {doc.id}"
        assert loc["version"] == str(doc.front["version"]), f"{fid}: version of {doc.id}"


def test_values_appear_verbatim_in_the_cited_section():
    docs = documents()
    for fid, loc in locations():
        text = norm(section_text(docs[loc["doc"]], str(loc["section"])))
        for value in loc["values"]:
            assert norm(value) in text, f"{fid}: {value!r} not in {loc['doc']} {loc['section']}"


def test_values_appear_in_the_cited_paragraph():
    docs = documents()
    cited = [(fid, loc) for fid, loc in locations() if "paragraph" in loc]
    assert cited, "no paragraph citations"
    for fid, loc in cited:
        paragraphs = docs[loc["doc"]].sections()[str(loc["section"])].paragraphs()
        para = norm(paragraphs[loc["paragraph"] - 1])
        for value in loc["values"]:
            assert norm(value) in para, f"{fid}: {value!r} not in paragraph {loc['paragraph']}"


def test_rule_and_exception_are_consecutive_paragraphs():
    f15 = next(f for f in features() if f["id"] == "F-15")
    paras = sorted(loc["paragraph"] for loc in f15["locations"])
    assert len({loc["section"] for loc in f15["locations"]}) == 1
    assert paras == [paras[0], paras[0] + 1]


def test_table_values_are_in_the_cited_cell():
    docs = documents()
    cited = [(fid, loc) for fid, loc in locations() if "table" in loc]
    assert cited, "no table citations"
    for fid, loc in cited:
        cite = loc["table"]
        rows = docs[loc["doc"]].sections()[str(loc["section"])].table(cite["caption"])
        first = next(iter(rows[0]))
        row = next((r for r in rows if r[first] == cite["row"]), None)
        assert row is not None, f"{fid}: no row {cite['row']!r}"
        for value in loc["values"]:
            assert value in row[cite["column"]], f"{fid}: {value!r} not in {cite}"


def test_pages_match_the_page_markers_and_the_rendered_page():
    docs = documents()
    for fid, loc in locations():
        doc = docs[loc["doc"]]
        if doc.front["format"] not in ("pdf", "png"):
            assert "page" not in loc, f"{fid}: page cited for a {doc.front['format']} file"
            continue
        section = doc.sections()[str(loc["section"])]
        assert loc.get("page") == section.page, f"{fid}: page of {doc.id} {loc['section']}"
        if doc.front["format"] == "pdf":
            page_text = norm(pdf_pages()[loc["page"] - 1])
            for value in loc["values"]:
                assert norm(value) in page_text, f"{fid}: {value!r} not on PDF page {loc['page']}"


def test_values_survive_rendering():
    """A value in a PDF, HTML or PNG document is in the text ingestion will read."""
    docs = documents()
    for fid, loc in locations():
        doc = docs[loc["doc"]]
        rendered = norm(rendered_text(doc))
        for value in loc["values"]:
            assert norm(value) in rendered, f"{fid}: {value!r} lost when {doc.id} was rendered"


def test_exclusive_values_appear_in_no_other_document():
    docs = documents()
    for fid, loc in locations():
        if not loc.get("exclusive"):
            continue
        for value in loc["values"]:
            others = [d.id for d in docs.values() if d.id != loc["doc"] and value in d.body]
            assert not others, f"{fid}: {value!r} also in {others}"


def test_omissions_appear_nowhere_in_their_scope():
    docs = documents()
    checked = 0
    for f in features():
        rule = f.get("must_not_appear")
        if not rule:
            continue
        scope = rule["scope"]
        assert scope == "corpus" or scope in TENANTS, f["id"]
        texts = {d.id: d.body + rendered_text(d) for d in docs.values()}
        texts = {k: v for k, v in texts.items() if scope == "corpus" or docs[k].tenant == scope}
        for phrase in rule["phrases"]:
            hits = [k for k, v in texts.items() if phrase.lower() in v.lower()]
            assert not hits, f"{f['id']}: {phrase!r} appears in {hits}"
            checked += 1
    assert checked >= 6


def test_table_only_values_are_stated_only_in_the_table():
    """SPEC 11.5: outside Table 1 of A-PWD-V2 (and v1 section 4.4) no tenant A document states a
    number of failed sign-in attempts, a lockout duration or a delay between attempts."""
    patterns = [
        r"\b\d+\s+(?:consecutive\s+)?failed\b",
        r"\baccounts?\b[^.]*\blocks?\b[^.]*\b\d+",
        r"\block(?:ed|out)\b[^.]*\b\d+\s+(?:seconds?|minutes?|hours?)\b",
        r"\b\d+\s+(?:seconds?|minutes?)\b[^.]*\b(?:attempt|retry|retries)\b",
    ]
    docs = documents()
    for doc in docs.values():
        if doc.tenant != "tenant-a":
            continue
        text = doc.body
        if doc.id == "A-PWD-V2":
            section = doc.sections()["5"].text
            text = text.replace(section, "")
        if doc.id == "A-PWD-V1":
            text = text.replace(doc.sections()["4.4"].text, "")
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.I)
            assert not match, f"{doc.id} states a sign-in protection value: {match.group(0)!r}"


def test_multi_hop_values_live_in_different_documents():
    docs = documents()
    for f in features():
        if f["kind"] != "multi-hop":
            continue
        values = [v for loc in f["locations"] for v in loc["values"]]
        assert len({loc["doc"] for loc in f["locations"]}) >= 2, f["id"]
        for doc in docs.values():
            if all(norm(v) in norm(doc.body) for v in values):
                pytest.fail(f"{f['id']}: {doc.id} alone holds every value")


# ------------------------------------------------------------------ requirements


def test_every_requirement_is_covered_or_a_gap():
    planned = plan_requirements()
    assert len(planned) >= 20, f"found only {sorted(planned)} in the test plan"
    covered = {r for f in features() for r in f["requirements"]}
    gaps = {g["requirement"] for g in answer_key()["gaps"]}  # type: ignore[union-attr]
    assert covered <= planned, f"key names requirements the plan lacks: {covered - planned}"
    assert gaps == plan_gaps(), "the key's gaps differ from the test plan's gaps table"
    assert not covered & gaps, f"listed as gaps but covered: {covered & gaps}"
    assert planned == covered | gaps, f"neither covered nor a gap: {planned - covered - gaps}"
    for gap in answer_key()["gaps"]:  # type: ignore[union-attr]
        assert gap["reason"].strip(), gap


def test_traceability_rows_agree_with_the_key():
    by_id = {f["id"]: f for f in features()}
    rows = traceability()
    assert set(rows) == plan_requirements()
    for rid, fids in rows.items():
        for fid in fids:
            assert fid in by_id, f"{rid} names {fid}, which is not in the key"
            assert rid in by_id[fid]["requirements"], f"{fid} does not list {rid}"
        covered = {f["id"] for f in features() if rid in f["requirements"]}
        assert bool(fids) == bool(covered), f"{rid}: traceability and key disagree on a gap"


# ------------------------------------------------------------------ conflicts


def numbers(values: list[str]) -> set[str]:
    return set(re.findall(r"\b\d+\b", " ".join(values)))


def conflict_features() -> list[dict[str, Any]]:
    found = [f for f in features() if "conflict" in f]
    assert len(found) >= 12
    return found


def sides(f: dict[str, Any]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for loc in f["locations"]:
        out.setdefault(loc["side"], []).extend(loc["values"])
    return out


def test_conflicts_have_both_sides():
    for f in conflict_features():
        assert f["conflict"] in CONFLICT_SIDES, f["id"]
        assert set(sides(f)) == CONFLICT_SIDES[f["conflict"]], f["id"]


def test_version_and_tenant_conflicts_really_differ():
    """v1 against v2 and tenant B against tenant A: the numbers differ, or one side negates."""
    docs = documents()
    for f in conflict_features():
        if f["conflict"] == "external":
            continue
        (left, a), (right, b) = sides(f).items()
        assert {norm(v) for v in a}.isdisjoint({norm(v) for v in b}), f["id"]
        na, nb = numbers(a), numbers(b)
        negates = bool(NEGATION.search(" ".join(a))) != bool(NEGATION.search(" ".join(b)))
        assert (na and nb and na.isdisjoint(nb)) or negates, f"{f['id']}: {a} vs {b}"
        if f["conflict"] == "tenant":
            tenant_of = {loc["side"]: docs[loc["doc"]].tenant for loc in f["locations"]}
            assert tenant_of == {"tenant-a": "tenant-a", "tenant-b": "tenant-b"}, f["id"]
        if f["conflict"] == "version":
            status = {loc["side"]: docs[loc["doc"]].front["status"] for loc in f["locations"]}
            assert status == {"old": "superseded", "new": "current"}, f["id"]
        assert left != right


def test_company_expiry_contradicts_the_quoted_external_lines():
    docs = documents()
    f08 = next(f for f in features() if f["id"] == "F-08")
    company = [loc for loc in f08["locations"] if loc["side"] == "company"]
    external = [loc for loc in f08["locations"] if loc["side"] == "external"]
    assert {docs[loc["doc"]].front["kind"] for loc in company} == {"company"}
    assert {loc["doc"] for loc in external} == {"X-NIST", "X-NCSC"}
    for loc in company:
        text = norm(section_text(docs[loc["doc"]], loc["section"]))
        assert re.search(r"User passwords expire every \d+ days\.", text), loc
    for loc in external:
        for value in loc["values"]:
            assert NEGATION.search(value), f"{loc['doc']}: {value!r} does not argue against expiry"
    # and the company document does not say the external guidance disagrees (SPEC A-PWD-V2 brief)
    v2 = docs["A-PWD-V2"].sections()["6"].text
    assert not re.search(r"disagree|differ|contrar", v2, flags=re.I)
