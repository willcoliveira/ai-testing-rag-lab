"""Allowlist entries added for the corpus apply to corpus/ paths only (S1a AC9).

The corpus plants visibly fake contacts, tokens and ids that the generic privacy patterns flag.
They are allowed by privacy/allowlist-corpus.txt, which the privacy check applies only to files
whose path starts with corpus/. Anywhere else (code, docs, a commit message) the same strings are
still hits, so the allowlist cannot hide a real leak outside the corpus. Any gitleaks allowlist
for the corpus is held to the same rule.
"""

import os
import re
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

from tests.conftest import ROOT

pytestmark = pytest.mark.unit
NODE = shutil.which("node")
CORPUS_LIST = ROOT / "privacy" / "allowlist-corpus.txt"
FAKE = re.compile(r"^([\w.+-]+@([\w-]+\.)*example\.(com|org)|FAKE-[A-Z0-9-]+|EX-\d{4}-\d{3})$")
OUTSIDE = [
    "src/raglab/x.py",
    "docs/x.md",
    "x.md",
    "tests/unit/x.py",
    "corpus.md",
    "notcorpus/x.md",
    "docs/corpus/x.md",
    "privacy/x.txt",
]


def entries(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]


def test_corpus_entries_are_visibly_fake():
    found = entries(CORPUS_LIST)
    assert found, "the corpus allowlist is empty"
    for entry in found:
        assert FAKE.match(entry), f"not a visibly fake corpus token: {entry}"


def test_global_allowlist_holds_no_corpus_token():
    corpus = set(entries(CORPUS_LIST))
    for entry in entries(ROOT / "privacy" / "allowlist.txt"):
        assert entry not in corpus
        assert not re.search(r"halvenroot|mirrowfen|FAKE-|example\.org|^EX-\d", entry, re.I), entry


def run_check(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    assert NODE is not None
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["CI"] = "1"  # the example list only, so the test never reads a maintainer's real list
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
    (tmp_path / "scripts").mkdir()
    (tmp_path / "privacy").mkdir()
    shutil.copy(ROOT / "scripts" / "check-forbidden.mjs", tmp_path / "scripts")
    for name in ("forbidden-strings.example.txt", "allowlist.txt", "allowlist-corpus.txt"):
        shutil.copy(ROOT / "privacy" / name, tmp_path / "privacy")
    return tmp_path


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_corpus_tokens_pass_inside_corpus(tree: Path):
    write(tree, "corpus/tenant-a/x.md", "\n\n".join(f"Contact: {e}." for e in entries(CORPUS_LIST)))
    result = run_check(tree, "--dir", "corpus")
    assert result.returncode == 0, result.stdout


@pytest.mark.parametrize("outside", OUTSIDE)
def test_every_corpus_token_is_a_hit_outside_corpus(tree: Path, outside: str):
    found = entries(CORPUS_LIST)
    write(tree, outside, "\n\n".join(f"Contact: {e}." for e in found))
    write(tree, "files", outside + "\0")
    result = run_check(tree, "--files-from", "files")
    assert result.returncode == 1, result.stdout
    for n, entry in enumerate(found):
        line = 2 * n + 1  # one blank line between entries
        assert f"{outside}:{line}: matches" in result.stdout, f"{entry} was allowed in {outside}"


def test_the_same_tokens_pass_when_listed_under_corpus(tree: Path):
    found = entries(CORPUS_LIST)
    write(tree, "corpus/x.md", "\n\n".join(f"Contact: {e}." for e in found))
    write(tree, "files", "corpus/x.md\0")
    result = run_check(tree, "--files-from", "files")
    assert result.returncode == 0, result.stdout


def test_corpus_tokens_are_hits_in_a_commit_message(tree: Path):
    write(tree, "COMMIT_MSG", "docs: contact " + entries(CORPUS_LIST)[0] + "\n")
    assert run_check(tree, "--file", "COMMIT_MSG").returncode == 1


def test_only_listed_tokens_pass_in_corpus(tree: Path):
    """The scope is token by token, not the whole folder: an unlisted address is still a hit."""
    unlisted = (
        "someone" + "@" + "halvenroot.example.com"
    )  # built here, so this file holds no address
    write(tree, "corpus/tenant-a/x.md", f"Mail {unlisted} today.\n")
    assert run_check(tree, "--dir", "corpus").returncode == 1


def test_repo_privacy_check_passes_with_the_corpus():
    result = run_check(ROOT)
    assert result.returncode == 0, result.stdout


def test_gitleaks_allowlists_for_the_corpus_stay_in_corpus():
    config = tomllib.loads((ROOT / ".gitleaks.toml").read_text(encoding="utf-8"))
    allowlists = list(config.get("allowlists", []))
    for rule in config.get("rules", []):
        allowlists.extend(rule.get("allowlists", []))
    for allow in allowlists:
        paths = [re.compile(p) for p in allow.get("paths", [])]
        corpus_paths = [p for p in paths if p.search("corpus/tenant-a/x.md")]
        content = any(allow.get(k) for k in ("regexes", "stopwords", "commits"))
        if content:
            # a content allowlist must be limited to corpus/ paths, with both conditions required
            assert paths, allow
            assert all(not p.search(o) for p in paths for o in OUTSIDE), allow
            assert allow.get("condition", "").upper() == "AND", allow
        for pattern in corpus_paths:
            for outside in OUTSIDE:
                assert not pattern.search(outside), f"{pattern.pattern} also matches {outside}"
