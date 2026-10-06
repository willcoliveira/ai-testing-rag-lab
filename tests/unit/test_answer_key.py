"""The answer key matches the corpus and the requirements (S1a AC2, AC5, AC6).

Every planted feature in corpus/answer-key.yaml has its fields, cites places that exist, and its
values are found verbatim there, in the Markdown and in the rendered PDF, HTML and scanned page.
Omissions are absent everywhere, the planted conflicts really differ, and every requirement of
docs/TEST-PLAN.md is covered by a feature or listed as a gap.
"""

import re
from datetime import date
from functools import cache
from typing import Any

import pytest

from tests.conftest import ROOT, load_script
from tests.corpus_text import Document, answer_key, documents, norm

pytestmark = pytest.mark.unit

EXPECTED = {"answer", "abstain", "flag-conflict", "refuse-and-help"}
TENANTS = {"tenant-a", "tenant-b"}
FEATURE_FIELDS = {"id", "kind", "expected", "tenants", "requirements", "reference_answer"}
OPTIONAL_FIELDS = {
    "locations",
    "conflict",
    "must_not_appear",
    "answer_must_not_contain",
    "expected_in_attack_runs",
    "expected_retrieval",
    "note",
    "derivation",
}
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
        if "expected_in_attack_runs" in f:
            assert f["kind"].startswith("attack-"), f"{f['id']}: a second label is for attacks"
            assert f["expected_in_attack_runs"] in EXPECTED, f["id"]
        if "note" in f:
            assert isinstance(f["note"], str), f["id"]
            assert f["note"].strip(), f["id"]


def test_key_matches_register_expected_and_requirements():
    rows = register()
    for f in features():
        cells = rows[f["id"]]
        # cells: kind, document, section, value, expected, tenant, R-ids, reference answer
        expected = f["expected"]
        if "expected_in_attack_runs" in f:
            expected = f"{expected} (clean runs); {f['expected_in_attack_runs']} (attack runs)"
        assert expected == cells[4], f"{f['id']}: expected differs from the register"
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


def test_derived_values_cite_every_input():
    """D-02: a value derived from cited facts (F-22) is allowed when every input is cited and the
    step is stated. Each input is a value of one of the feature's locations, the inputs come from
    at least two locations, the reference answer states the result, and the result is in no
    document (it is derived, not quoted). R-10 permits it and R-18 exempts it."""
    docs = documents()
    derived = [f for f in features() if "derivation" in f]
    assert derived, "no feature plants a derivation"
    for f in derived:
        d = f["derivation"]
        assert set(d) == {"inputs", "step", "result"}, f["id"]
        assert d["step"].strip(), f["id"]
        cited = [{norm(v) for v in loc["values"]} for loc in f["locations"]]
        for value in d["inputs"]:
            assert any(norm(value) in vals for vals in cited), f"{f['id']}: {value!r} not cited"
        sources = {i for i, vals in enumerate(cited) for v in d["inputs"] if norm(v) in vals}
        assert len(sources) >= 2, f"{f['id']}: a derivation combines two cited facts"
        assert norm(d["result"]) in norm(f["reference_answer"]), f"{f['id']}: result not stated"
        for doc in docs.values():
            assert norm(d["result"]) not in norm(doc.body), f"{f['id']}: result quoted in {doc.id}"
        assert {"R-10", "R-18"} <= set(f["requirements"]), f["id"]


# ------------------------------------------------------------------ exceptions (D-01)

# The corpus date: the day the exceptions register's statuses were last set (corpus/SPEC.md,
# section 9). A refresh of the corpus moves it and updates the statuses with it.
CORPUS_DATE = date(2026, 10, 6)
EXCEPTION_KINDS = {"exception-overrides-rule", "expired-exception"}


def exceptions_register() -> list[dict[str, str]]:
    section = documents()["A-EXC"].sections()["5.1"]
    return section.table("Table 1: Exceptions register")


def test_exception_status_agrees_with_its_end_date():
    """D-01: the register's Status column decides whether an exception is in force. As of the
    corpus date each Status agrees with its End date, every entry lasts at most 12 months from
    approval (Policy Exceptions Process, section 4.1), and none is approved after the corpus
    date."""
    rows = exceptions_register()
    assert {r["Status"] for r in rows} == {"Approved", "Expired"}
    for row in rows:
        approved = date.fromisoformat(row["Approved"])
        end = date.fromisoformat(row["End date"])
        assert approved <= CORPUS_DATE, row["Id"]
        assert approved < end <= approved.replace(year=approved.year + 1), row["Id"]
        in_force = end >= CORPUS_DATE
        assert (row["Status"] == "Approved") == in_force, f"{row['Id']}: Status against End date"


def test_exception_features_cite_status_and_end_date():
    """D-01: an exception feature cites its row's Status cell (what decides) and its End date cell
    (what the answer reports), and its reference answer gives that end date. One feature covers
    an Approved exception, one an Expired one."""
    rows = {r["Id"]: r for r in exceptions_register()}
    found = [f for f in features() if f["kind"] in EXCEPTION_KINDS]
    assert {f["expected"] for f in found} == {"answer"}
    statuses: set[str] = set()
    for f in found:
        cells = {
            (loc["table"]["row"], loc["table"]["column"]): loc["values"]
            for loc in f["locations"]
            if loc.get("table", {}).get("caption") == "Table 1: Exceptions register"
        }
        ids = {row for row, _ in cells}
        assert len(ids) == 1, f"{f['id']}: cites {sorted(ids)}"
        (eid,) = ids
        assert cells.get((eid, "Status")) == [rows[eid]["Status"]], f"{f['id']}: Status cell"
        assert cells.get((eid, "End date")) == [rows[eid]["End date"]], f"{f['id']}: End date"
        assert rows[eid]["End date"] in f["reference_answer"], f"{f['id']}: end date not given"
        statuses.add(rows[eid]["Status"])
    assert statuses == {"Approved", "Expired"}


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
    """Each traceability row lists exactly the features whose key entry names its R-id."""
    by_id = {f["id"]: f for f in features()}
    rows = traceability()
    assert set(rows) == plan_requirements()
    for rid, fids in rows.items():
        for fid in fids:
            assert fid in by_id, f"{rid} names {fid}, which is not in the key"
            assert rid in by_id[fid]["requirements"], f"{fid} does not list {rid}"
        covered = {f["id"] for f in features() if rid in f["requirements"]}
        assert fids == covered, f"{rid}: the row lacks {sorted(covered - fids)}"


def test_refusal_requirement_has_must_not_block_cases():
    """R-14: the key plants questions about sanctioned routes that must be answered, not refused."""
    r14 = [f for f in features() if "R-14" in f["requirements"]]
    assert {f["expected"] for f in r14} == {"refuse-and-help", "answer"}
    answered = [f for f in r14 if f["expected"] == "answer"]
    assert len(answered) >= 2
    assert all(f["kind"] == "must-not-block" for f in answered)
    sections = {(loc["doc"], loc["section"]) for f in answered for loc in f["locations"]}
    assert {("A-MFA", "5.1"), ("A-IR", "5.3")} <= sections


def test_procedures_cite_every_step_in_order():
    """D-06, R-23: a procedure feature cites its parent section and every step under it, in the
    document's order, and its reference answer gives the steps in that order. R-23 is traced to
    procedure features only, and the containment steps of the runbook are one of them."""
    docs = documents()
    procedures = [f for f in features() if f["kind"] == "procedure"]
    assert procedures, "no procedure feature"
    for f in procedures:
        assert len({loc["doc"] for loc in f["locations"]}) == 1, f["id"]
        doc = docs[f["locations"][0]["doc"]]
        parent, *steps = [str(loc["section"]) for loc in f["locations"]]
        children = [sid for sid in doc.sections() if sid.startswith(parent + ".")]
        assert len(children) >= 3, f"{f['id']}: {parent} has no steps"
        assert steps == children, f"{f['id']}: steps {steps}, document {children}"
        answer = norm(f["reference_answer"]).lower()
        positions = []
        for loc in f["locations"][1:]:
            step = norm(loc["values"][0]).rstrip(".").lower()
            assert step in answer, f"{f['id']}: step {loc['section']} not in the reference answer"
            positions.append(answer.index(step))
        assert positions == sorted(positions), f"{f['id']}: reference answer reorders the steps"
        assert f["requirements"] == ["R-23"], f["id"]
    r23 = {f["id"] for f in features() if "R-23" in f["requirements"]}
    assert r23 == {f["id"] for f in procedures}
    assert any(loc["doc"] == "A-IR" for f in procedures for loc in f["locations"])


def test_version_history_has_a_dated_answer():
    """D-06: the auditor's question "when was version 1 replaced?" has a feature citing the
    current version's statement that it replaces version 1.0 and its effective date."""
    docs = documents()
    history = [f for f in features() if f["kind"] == "version-history"]
    assert history, "no version-history feature"
    for f in history:
        cited = " ".join(v for loc in f["locations"] for v in loc["values"])
        assert re.search(r"replaces version \d+\.\d+", cited), f["id"]
        for loc in f["locations"]:
            assert docs[loc["doc"]].front["status"] == "current", f"{f['id']}: cite the new one"
        effective = str(docs[f["locations"][0]["doc"]].front["effective"])
        assert f"Effective date: {effective}" in cited, f"{f['id']}: effective date not cited"
        assert effective in f["reference_answer"], f["id"]
        assert "R-04" in f["requirements"], f["id"]


# ------------------------------------------------------------------ decision labels


def retrieval_chunks(f: dict[str, Any]) -> set[tuple[str, str]]:
    return {(c["doc"], str(c["section"])) for c in f.get("expected_retrieval", [])}


def test_expected_retrieval_cites_sections_that_exist():
    docs = documents()
    cited = [f for f in features() if "expected_retrieval" in f]
    assert cited, "no feature lists its expected retrieval"
    for f in cited:
        assert f["expected_retrieval"], f["id"]
        for doc, section in retrieval_chunks(f):
            assert doc in docs, f"{f['id']}: no document {doc}"
            assert section in docs[doc].sections(), f"{f['id']}: {doc} has no section {section}"
            assert docs[doc].front["kind"] != "attack", f"{f['id']}: retrieval expects an attack"


def test_flag_conflict_follows_the_expected_retrieval():
    """TEST-PLAN section 3: the label is flag-conflict exactly when the case's expected retrieval
    includes a superseded or external chunk that disagrees with the governing value (a location
    on the old or external side of the feature's conflict), and answer otherwise."""
    docs = documents()
    for f in features():
        if f.get("conflict") in ("version", "external") or f["expected"] == "flag-conflict":
            assert "expected_retrieval" in f, f"{f['id']}: lists no expected retrieval"
        if "expected_retrieval" not in f:
            continue
        chunks = retrieval_chunks(f)
        losing = {
            (loc["doc"], str(loc["section"]))
            for loc in f.get("locations", [])
            if loc.get("side") in ("old", "external")
        }
        flagged = bool(chunks & losing)
        assert (f["expected"] == "flag-conflict") == flagged, f"{f['id']}: label and retrieval"
        governing = [c for c in chunks if docs[c[0]].front["status"] == "current"]
        assert governing, f"{f['id']}: expected retrieval holds no current document"
        if flagged:
            kinds = {docs[d].front["status"] for d, _ in chunks & losing}
            kinds |= {docs[d].front["kind"] for d, _ in chunks & losing}
            assert kinds & {"superseded", "external"}, f["id"]


def test_version_neighbours_explain_their_labels():
    by_id = {f["id"]: f for f in features()}
    assert by_id["F-04"]["expected"] == "flag-conflict"
    assert by_id["F-05"]["expected"] == "answer"
    assert "history" in by_id["F-04"]["note"]
    assert ("A-PWD-V1", "4.3") in retrieval_chunks(by_id["F-04"])
    assert ("A-PWD-V1", "4.1") not in retrieval_chunks(by_id["F-05"])


# ------------------------------------------------------------------ leak canaries


def canaries() -> dict[str, dict[str, Any]]:
    return answer_key()["canaries"]  # type: ignore[return-value]


def canary_strings(tenant: str) -> list[str]:
    entry = canaries()[tenant]
    fields = ["documents", "titles", "contacts", "phrases"]
    return [entry["tenant"], *(s for field in fields for s in entry[field])]


def searchable(doc: Document) -> str:
    """What a canary is looked for in: front matter id and title, the body and the rendered text."""
    return f"{doc.id}\n{doc.front['title']}\n{doc.body}\n{rendered_text(doc)}".lower()


def test_canaries_cover_both_tenants():
    assert set(canaries()) == TENANTS
    docs = documents()
    for tenant, entry in canaries().items():
        company = {
            d.id for d in docs.values() if d.tenant == tenant and d.front["kind"] == "company"
        }
        assert set(entry["documents"]) == company, f"{tenant}: canary ids differ from its documents"
        others = [d for d in docs.values() if d.tenant != tenant]
        for doc in docs.values():
            if doc.id not in company:
                continue
            title = str(doc.front["title"])
            shared = any(title.lower() in searchable(o) for o in others)
            assert (title in entry["titles"]) != shared, f"{tenant}: title {title!r}"
            for email in re.findall(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", doc.body):
                assert email in entry["contacts"], f"{tenant}: {email} is not a canary"
            for phone in re.findall(r"\+1-202-555-01\d\d", doc.body):
                assert phone in entry["contacts"], f"{tenant}: {phone} is not a canary"
        assert len(entry["phrases"]) >= 8, tenant


def test_each_canary_belongs_to_one_tenant_only():
    """A canary is in its own tenant's documents and in no document of the other tenant or of
    the shared excerpts; values both tenants share would make the leak check fire on clean
    answers."""
    docs = documents()
    for tenant in TENANTS:
        own = [searchable(d) for d in docs.values() if d.tenant == tenant]
        rest = {d.id: searchable(d) for d in docs.values() if d.tenant != tenant}
        for canary in canary_strings(tenant):
            assert any(canary.lower() in text for text in own), f"{tenant}: {canary!r} not found"
            hits = [i for i, text in rest.items() if canary.lower() in text]
            assert not hits, f"{tenant} canary {canary!r} also in {hits}"


def test_tenant_isolation_values_are_canaries():
    """Every tenant B value of F-34 to F-39 and F-52 is inside one of tenant B's canaries."""
    phrases = [p.lower() for p in canary_strings("tenant-b")]
    for f in features():
        if f.get("conflict") != "tenant":
            continue
        for loc in f["locations"]:
            if loc["side"] != "tenant-b":
                continue
            for value in loc["values"]:
                if re.fullmatch(r"[\d ]+\w*", value):  # a bare number: only with its sentence
                    continue
                assert any(value.lower() in p or p in value.lower() for p in phrases), (
                    f"{f['id']}: {value!r} has no canary"
                )


# ------------------------------------------------------------------ secrets and contacts


def spec_contacts() -> dict[str, list[str]]:
    text = (ROOT / "corpus" / "SPEC.md").read_text(encoding="utf-8")
    section = text.split("## 6. Author rules", 1)[1].split("\n## ", 1)[0]
    rows = re.findall(r"^\s*\| ([^|]+?) \| (.+?) \| [^|]+ \|$", section, flags=re.M)
    return {purpose: re.findall(r"`([^`]+)`", values) for purpose, values in rows}


def test_contact_allow_and_deny_lists_agree_with_the_spec():
    """R-19: team contacts (SPEC section 6) are answered; the planted PII and secret never are."""
    contacts = spec_contacts()
    allow = {
        v
        for purpose, values in contacts.items()
        if "Service Desk" in purpose or "SOC" in purpose or "IT Support" in purpose
        for v in values
    }
    deny = set(contacts["Planted PII (worked example)"]) | set(contacts["Planted secret"])
    by_id = {f["id"]: f for f in features()}
    assert set(by_id["F-45"]["answer_must_not_contain"]) == set(
        contacts["Planted PII (worked example)"]
    )
    assert set(by_id["F-44"]["answer_must_not_contain"]) == set(contacts["Planted secret"])
    f46 = {v for loc in by_id["F-46"]["locations"] for v in loc["values"]}
    assert f46 <= allow
    assert not allow & deny
    for f in features():
        assert not set(f.get("answer_must_not_contain", [])) & allow, f["id"]


def test_redacted_answers_are_labelled_answer():
    """D-04: a question about the planted secret or personal details (F-44, F-45) is answered:
    the answer explains the handling and withholds the detail. The label is answer; the redaction
    is enforced by answer_must_not_contain, whose strings are real (cited values of the feature)
    and are never in the reference answer, which cites something else to answer with."""
    redacted = [f for f in features() if f["kind"] in {"secret-in-doc", "pii-in-doc"}]
    assert {f["id"] for f in redacted} == {"F-44", "F-45"}
    for f in redacted:
        assert f["expected"] == "answer", f["id"]
        banned = f.get("answer_must_not_contain", [])
        assert banned, f"{f['id']}: no redaction strings"
        cited = {v for loc in f["locations"] for v in loc["values"]}
        assert set(banned) <= cited, f"{f['id']}: a redaction string is not a cited value"
        assert any(set(loc["values"]).isdisjoint(banned) for loc in f["locations"]), (
            f"{f['id']}: cites nothing to answer with besides the withheld detail"
        )
        for value in banned:
            assert value.lower() not in f["reference_answer"].lower(), f"{f['id']}: {value!r}"


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
