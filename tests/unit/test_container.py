"""S3 AC10 and AC11, the parts a test can read: the container builds from a digest-pinned base,
runs as a non-root user with the fake model, and is published on 127.0.0.1 only; the build context
holds nothing but what the image needs; the ZAP image is pinned by digest and every ignored ZAP
rule has its reason. The build, the curl and the scan themselves are in the S3 ledger (Docker)."""

import re

import pytest

from tests.conftest import ROOT

pytestmark = pytest.mark.unit
DOCKERFILE = (ROOT / "deploy" / "Dockerfile").read_text(encoding="utf-8")
DIGEST = r"@sha256:[0-9a-f]{64}"


def test_the_base_image_is_pinned_by_digest():
    froms = re.findall(r"^FROM (\S+)", DOCKERFILE, flags=re.M)
    assert froms, "no FROM"
    for image in froms:
        assert re.search(DIGEST + "$", image), image


def test_the_container_runs_as_a_non_root_user_with_the_fake_model():
    users = re.findall(r"^USER (\S+)", DOCKERFILE, flags=re.M)
    assert users == ["10001"]
    cmd = re.search(r"^CMD (.*)$", DOCKERFILE, flags=re.M)
    assert cmd is not None
    assert '"config/fake.toml"' in cmd.group(1)
    assert "raglab fetch-model" in DOCKERFILE  # the embedder baked in, hashes checked
    assert "ENV HF_HUB_OFFLINE=1" in DOCKERFILE
    pins = re.findall(r'"(tesseract-ocr[\w-]*)=([^"]+)"', DOCKERFILE)
    assert {name for name, _ in pins} == {"tesseract-ocr", "tesseract-ocr-eng", "tesseract-ocr-osd"}
    assert "--require-hashes" in DOCKERFILE
    assert "uv sync --locked --no-dev" in DOCKERFILE


def test_the_container_is_published_on_loopback_only():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    scan = (ROOT / "deploy" / "zap" / "scan.sh").read_text(encoding="utf-8")
    for text in (makefile, scan):
        published = re.findall(r"docker run[^\n]* -p (\S+)", text)
        assert published, "no published port"
        assert all(p.startswith("127.0.0.1:") for p in published), published


def test_the_build_context_is_an_allow_list():
    lines = [
        line
        for line in (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    ]
    assert lines[0] == "*"
    allowed = {line[1:] for line in lines if line.startswith("!")}
    assert allowed == {
        "pyproject.toml",
        "uv.lock",
        "README.md",
        "LICENSE",
        ".github/ci-requirements.txt",
        "src/",
        "corpus/",
        "config/",
        "datasets/",
        "schemas/",
    }


def test_zap_is_pinned_and_every_ignored_rule_has_a_reason():
    scan = (ROOT / "deploy" / "zap" / "scan.sh").read_text(encoding="utf-8")
    image = re.search(r'^ZAP="([^"]+)"', scan, flags=re.M)
    assert image is not None
    assert re.search(r"^ghcr\.io/zaproxy/zaproxy:stable" + DIGEST + "$", image.group(1))
    rules = (ROOT / "deploy" / "zap" / "rules.tsv").read_text(encoding="utf-8").splitlines()
    for number, line in enumerate(rules):
        if not line or line.startswith("#"):
            continue
        rule, action, _ = line.split("\t")
        assert action in {"IGNORE", "WARN", "FAIL"}, line
        if action == "IGNORE":
            reason = rules[number - 1]
            assert reason.startswith(f"# {rule} ") or reason.startswith("# "), line
            assert any(r.startswith(f"# {rule} ") for r in rules[:number]), f"{rule} has no reason"
