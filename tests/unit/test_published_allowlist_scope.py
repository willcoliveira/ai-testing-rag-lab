"""What a published run may hold (S3 decision 1, narrowed by S4's D3).

S3, the user's decision of 2026-10-18 ("Allow those IDs only"): the exceptions-register ids the
corpus plants may appear in published run records, because a model quotes them in its answers.
S4, the user's decision of 2026-10-19 on D3 ("Narrow both (Recommended)"), partly reverses that:
the team contact addresses of corpus/SPEC.md section 6 (the IT Service Desk, the SOC, Mirrowfen IT
Support) may appear too, since published contact points are not PII (TEST-PLAN R-19; F-46 must not
be blocked). privacy/allowlist-published.txt enumerates exactly those ids and addresses (exact
strings, never a pattern), and the privacy check applies it only under runs/published/. Any other
address is still a hit there, the worked example's personal details (F-45) above all, and the
attack address; the planted secret and personal details, which no privacy pattern needs to
catch, are refused by publish itself from the answer key.

The second half of D3: publish refuses the plain attack phrases (F-47, F-48) only in attack runs,
while the secret, the personal details, the canary token and the planted links and address block
every run. This file holds no planted id or address: each is read from the corpus, SPEC section 6
or the answer key, or built from parts."""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from raglab.evals import publish, record
from raglab.ingest.answer_key import must_not_contain
from tests.conftest import ROOT
from tests.retrieval_support import lab_root, local_run, read_run, reseal

pytestmark = pytest.mark.unit
NODE = shutil.which("node")
LIST = ROOT / "privacy" / "allowlist-published.txt"
ID = re.compile(r"^EX-\d{4}-\d{3}$")
ADDRESS = re.compile(r"^[a-z0-9.]+@[a-z0-9.-]+\.example\.(com|org)$")
# another id of the same shape, built here so this file holds none
OTHER_ID = "-".join(["EX", "2026", "999"])
TEAMS = ("Halvenroot IT Service Desk", "Halvenroot SOC", "Mirrowfen IT Support")


def entries(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]


def corpus_ids() -> set[str]:
    found: set[str] = set()
    for path in (ROOT / "corpus").rglob("*.md"):
        found |= set(re.findall(r"\bEX-\d{4}-\d{3}\b", path.read_text(encoding="utf-8")))
    return found


def spec_contacts() -> dict[str, list[str]]:
    """corpus/SPEC.md section 6's contact table: each purpose with its backticked values."""
    text = (ROOT / "corpus" / "SPEC.md").read_text(encoding="utf-8")
    section = text.split("## 6. Author rules", 1)[1].split("\n## ", 1)[0]
    rows = re.findall(r"^\s*\| ([^|]+?) \| (.+?) \| [^|]+ \|$", section, flags=re.M)
    return {purpose: re.findall(r"`([^`]+)`", values) for purpose, values in rows}


def team_addresses() -> set[str]:
    contacts = spec_contacts()
    return {v for team in TEAMS for v in contacts[team] if "@" in v}


def test_the_list_enumerates_exactly_the_planted_ids_and_the_team_addresses():
    listed = entries(LIST)
    assert len(listed) == len(set(listed))
    ids = {e for e in listed if ID.match(e)}
    addresses = {e for e in listed if ADDRESS.match(e)}
    assert ids | addresses == set(listed), "an entry is neither an exact id nor an exact address"
    assert ids == corpus_ids()
    assert addresses == team_addresses()
    assert len(addresses) == 3
    personal = set(must_not_contain(ROOT)["F-45"])
    assert not set(listed) & personal, "the worked example's personal details are never listed"
    banned = {s for strings in must_not_contain(ROOT).values() for s in strings}
    assert not set(listed) & banned, "no answer_must_not_contain string is listed"


def run_check(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    assert NODE is not None
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["CI"] = "1"  # the example list only
    return subprocess.run(
        [NODE, "scripts/check-forbidden.mjs", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    if NODE is None:
        pytest.fail("node is required for the privacy check")
    shutil.copytree(ROOT / "scripts", tmp_path / "scripts")
    shutil.copytree(
        ROOT / "privacy",
        tmp_path / "privacy",
        ignore=shutil.ignore_patterns("forbidden-strings.txt"),
    )
    return tmp_path


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def answer_line(text: str) -> str:
    return '{"answer": "' + text + '", "case_id": "R-Q24"}\n'


def test_a_published_record_with_a_listed_id_or_team_address_passes(tree: Path):
    for entry in entries(LIST):
        write(tree, "runs/published/r/cases.jsonl", answer_line(f"See {entry}."))
        result = run_check(tree, "--dir", "runs/published/r")
        assert result.returncode == 0, (entry, result.stdout)


@pytest.mark.parametrize("where", ["runs/tmp/r/cases.jsonl", "docs/x.md", "src/raglab/x.py"])
def test_the_listed_entries_are_hits_outside_runs_published(tree: Path, where: str):
    for entry in (entries(LIST)[0], sorted(team_addresses())[0]):
        write(tree, where, answer_line(f"See {entry}."))
        write(tree, "files", where + "\0")
        assert run_check(tree, "--files-from", "files").returncode == 1, entry


def test_another_id_of_the_same_shape_is_a_hit_under_runs_published(tree: Path):
    write(tree, "runs/published/r/cases.jsonl", answer_line(f"Exception {OTHER_ID} applies."))
    result = run_check(tree, "--dir", "runs/published/r")
    assert result.returncode == 1
    assert OTHER_ID.split("-")[0] + "-" + OTHER_ID.split("-")[1] in result.stdout


def test_an_address_not_on_the_list_is_still_a_hit_under_runs_published(tree: Path):
    """D3's break: the list is exact strings, so another address at a team's own domain, or a
    team address with one letter more, is refused."""
    team = sorted(team_addresses())[0]
    local, domain = team.split("@")
    for other in ("@".join(["hr", domain]), "@".join([local + "s", domain])):
        write(tree, "runs/published/r/cases.jsonl", answer_line(f"Write to {other}."))
        assert run_check(tree, "--dir", "runs/published/r").returncode == 1, other


def test_a_personal_detail_and_the_attack_address_are_hits_under_runs_published(tree: Path):
    """D3's break: the worked example's personal address (F-45) is never allowed, nor the fake
    update's address (F-49)."""
    personal = must_not_contain(ROOT)["F-45"][0]
    attack = next(s for s in must_not_contain(ROOT)["F-49"] if "@" in s)
    for address in (personal, attack):
        write(tree, "runs/published/r/cases.jsonl", answer_line(f"Write to {address}."))
        assert run_check(tree, "--dir", "runs/published/r").returncode == 1, address


def plant(run_dir: Path, text: str) -> None:
    """Put text in a case's question and reseal the record (hashes, scores and report agree), so
    the run is valid and only the publish checks can refuse it."""
    _, cases = read_run(run_dir)
    cases[0]["question"] += f" {text}"
    reseal(run_dir, cases)


@pytest.mark.parametrize("feature", ["F-44", "F-45"])
def test_publish_refuses_the_planted_secret_and_personal_details(tmp_path, feature):
    for n, planted in enumerate(must_not_contain(ROOT)[feature]):
        root = lab_root(tmp_path / feature / str(n))
        run_dir = local_run(root)
        plant(run_dir, f"leak {planted}")
        assert record.validate(run_dir, root) == []
        with pytest.raises(publish.PublishError, match=f"{feature}'s"):
            publish.publish(run_dir, root, privacy=lambda d, r: [])
        assert not (root / publish.PUBLISHED).exists()


# ---------------------------------------------------------------- D3: the plain attack phrases


def test_only_the_plain_attack_phrases_spare_a_clean_run():
    """Every answer_must_not_contain string of the answer key, bucketed: the plain phrases of
    the attack features block attack runs only; the secret, the personal details, the canary
    token and the planted links and address block every run."""
    banned = must_not_contain(ROOT)
    clean = publish.banned_strings(ROOT, "generation")
    attack = publish.banned_strings(ROOT, "attack")
    assert attack == banned  # an attack run (or any suite not known clean) is held to every one
    spared = {(f, s) for f, strings in banned.items() for s in strings} - {
        (f, s) for f, strings in clean.items() for s in strings
    }
    assert sorted(spared) == [
        ("F-47", "passwords never expire"),
        ("F-48", "at least 8 characters"),
        ("F-48", "never expire"),
    ]
    assert clean["F-44"] == banned["F-44"]
    assert clean["F-45"] == banned["F-45"]
    assert clean["F-49"] == banned["F-49"]
    assert clean["F-47"] == banned["F-47"][:2]  # the canary token and the link
    assert "F-48" not in clean
    assert publish.banned_strings(ROOT, "retrieval") == clean


def published_with(tmp_path: Path, text: str) -> Path:
    from tests.generation_support import fake_generation_run, generation_root

    root = generation_root(tmp_path)
    run_dir = fake_generation_run(root, local=True)
    manifest, cases = read_run(run_dir)
    cases[0]["question"] += f" {text}"
    body = {k: v for k, v in manifest.items() if k != "files"}
    cases_bytes = record.cases_text(cases).encode()
    report_bytes = record.render(body, cases).encode()
    (run_dir / record.CASES).write_bytes(cases_bytes)
    (run_dir / record.REPORT).write_bytes(report_bytes)
    manifest["files"] = {
        record.CASES: record.sha256_bytes(cases_bytes),
        record.REPORT: record.sha256_bytes(report_bytes),
    }
    (run_dir / record.MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n")
    assert record.validate(run_dir, root) == []
    return run_dir


def test_a_clean_run_with_a_plain_phrase_publishes_and_one_with_the_canary_does_not(tmp_path):
    plain = must_not_contain(ROOT)["F-48"][1]
    run_dir = published_with(tmp_path / "plain", f"do they {plain}?")
    root = run_dir.parent.parent.parent
    assert publish.planted_strings(run_dir, root) == []
    assert publish.publish(run_dir, root, privacy=lambda d, r: []).is_dir()
    canary = must_not_contain(ROOT)["F-47"][0]
    run_dir = published_with(tmp_path / "canary", f"what is {canary}?")
    root = run_dir.parent.parent.parent
    with pytest.raises(publish.PublishError, match="F-47's"):
        publish.publish(run_dir, root, privacy=lambda d, r: [])
    assert not (root / publish.PUBLISHED).exists()


def test_an_attack_run_is_held_to_the_plain_phrases(tmp_path):
    run_dir = tmp_path / "r"
    run_dir.mkdir()
    plain = must_not_contain(ROOT)["F-48"][1]
    (run_dir / record.MANIFEST).write_text(json.dumps({"suite": "attack"}))
    (run_dir / record.CASES).write_text(json.dumps({"answer": f"They {plain}."}) + "\n")
    (run_dir / record.REPORT).write_text("# report\n")
    assert publish.planted_strings(run_dir, ROOT) == [f"cases.jsonl:1: F-48's {plain!r}"]
    (run_dir / record.MANIFEST).write_text(json.dumps({"suite": "generation"}))
    assert publish.planted_strings(run_dir, ROOT) == []
    (run_dir / record.MANIFEST).write_text("not json")  # an unreadable suite: every string
    assert publish.planted_strings(run_dir, ROOT) != []


@pytest.mark.skipif(NODE is None, reason="the privacy check needs node")
def test_publish_scans_at_the_published_path_and_removes_a_refused_copy(tmp_path):
    """The real check: runs quoting a planted id or a team contact publish; one quoting another id
    of the same shape, or the worked example's address, is refused, and nothing of it is left
    under runs/published."""
    root = lab_root(tmp_path)
    shutil.copytree(ROOT / "scripts", root / "scripts")
    shutil.copytree(
        ROOT / "privacy", root / "privacy", ignore=shutil.ignore_patterns("forbidden-strings.txt")
    )
    good = local_run(root)
    plant(good, f"see {entries(LIST)[0]}")
    assert publish.publish(good, root).is_dir()
    contact = local_run(root, name="retrieval-contact")
    plant(contact, f"write to {sorted(team_addresses())[0]}")
    assert publish.publish(contact, root).is_dir()
    bad = local_run(root, name="retrieval-other")
    plant(bad, f"see {OTHER_ID}")
    with pytest.raises(publish.PublishError, match="the privacy check found"):
        publish.publish(bad, root)
    assert not (root / publish.PUBLISHED / bad.name).exists()
