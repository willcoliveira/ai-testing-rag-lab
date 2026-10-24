"""The security pack's schema test (S7, AG6): datasets/security/ keeps how-to 07's template, every
layer has at least five handwritten must-block and five must-not-block cases, every case is
ratified (`maintainer, <date>`: the maintainer ratified all 127 as written on 2026-10-24),
planted values are referenced and never written, and the README labels the pack test material.
Each break is made on a copy of the pack."""

import shutil
from pathlib import Path

import pytest

from raglab.generate.prompts import CURRENT
from raglab.ingest import security_pack as pack
from tests.conftest import ROOT

pytestmark = pytest.mark.security
GUARD_LAYERS = [layer for layer in pack.LAYERS if layer != "attack"]
RATIFIED = "maintainer, 2026-10-24"


def found_problems(root: Path) -> list[str]:
    return pack.problems(root, pack.load(root), pack.sources(root, CURRENT.SYSTEM))


def test_the_committed_pack_keeps_its_template():
    assert found_problems(ROOT) == []


def test_every_committed_case_is_ratified_by_role_and_date():
    cases = pack.load(ROOT)
    assert len(cases) == 127
    pending = [c.id for c in cases if c.ratified_by == "pending"]
    assert pending == [], f"cases waiting for the maintainer's ratification: {pending}"
    assert {c.ratified_by for c in cases} == {"maintainer, 2026-10-24"}


@pytest.mark.parametrize("layer", GUARD_LAYERS)
def test_every_layer_has_five_handwritten_cases_of_each_kind(layer: str):
    cases = [c for c in pack.load(ROOT) if c.layer == layer]
    for kind in ("must_block", "must_not_block"):
        assert len([c for c in cases if c.kind == kind]) >= 5, f"{layer}: fewer than 5 {kind}"


def test_every_attack_row_of_the_threat_model_has_cases():
    attacks = {str(c.input["attack"]) for c in pack.load(ROOT) if c.layer == "attack"}
    assert attacks == set(pack.ATTACKS)


def test_the_readme_labels_the_pack_deliberate_test_material():
    text = (ROOT / pack.PACK / "README.md").read_text(encoding="utf-8")
    assert "deliberate test material" in text.casefold()
    assert "never ingested" in text
    for name in sorted(p.name for p in (ROOT / pack.PACK).glob("*.yaml")):
        assert f"`{name}`" in text, f"the README does not list {name}"


def test_a_reference_resolves_from_the_answer_key_and_spec_never_from_the_pack():
    found = pack.sources(ROOT, CURRENT.SYSTEM)
    banned = found.banned["F-44"][0]
    assert pack.resolve("{ref:F-44:0}", found) == banned
    address = pack.resolve("{contact:Halvenroot SOC:address}", found)
    assert address.endswith(".example.com")
    assert pack.resolve("{prompt:system}", found) == CURRENT.SYSTEM
    text = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / pack.PACK).glob("*"))
    assert banned not in text
    assert address not in text


# ---------------------------------------------------------------- the breaks, on a copy


@pytest.fixture
def copy(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    shutil.copytree(ROOT / pack.PACK, root / pack.PACK)
    (root / "corpus").mkdir(parents=True)
    for name in ("answer-key.yaml", "SPEC.md"):
        shutil.copyfile(ROOT / "corpus" / name, root / "corpus" / name)
    return root


def edit(root: Path, name: str, old: str, new: str) -> None:
    path = root / pack.PACK / name
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def test_a_must_not_block_case_that_expects_block_is_refused_naming_it(copy: Path):
    origin = "  origin: handwritten 2026-10-24 (R-17 must-not-block)\n"
    why = '  why: "A link of a register document'
    edit(
        copy,
        "links.yaml",
        f'  expected: pass\n  ratified_by: "{RATIFIED}"\n{origin}{why}',
        f'  expected: block\n  ratified_by: "{RATIFIED}"\n{origin}{why}',
    )
    assert found_problems(copy) == [
        "datasets/security/links.yaml LNK-N01: a must_not_block case expects 'pass'"
    ]


def test_an_empty_ratified_by_is_refused_naming_the_case(copy: Path):
    edit(
        copy,
        "tenant.yaml",
        f'  ratified_by: "{RATIFIED}"\n  origin: handwritten 2026-10-24 (R-21)\n'
        '  why: "A request that names no tenant',
        "  ratified_by:\n  origin: handwritten "
        '2026-10-24 (R-21)\n  why: "A request that names no tenant',
    )
    assert found_problems(copy) == [
        "datasets/security/tenant.yaml TEN-B01: ratified_by is empty or not 'maintainer, <date>'"
    ]


def test_a_reference_to_a_feature_that_does_not_exist_is_refused(copy: Path):
    edit(copy, "secrets-pii.yaml", "{ref:F-44:0}", "{ref:F-99:0}")
    assert found_problems(copy) == [
        "datasets/security/secrets-pii.yaml SPI-B01: {ref:F-99:0} names no "
        "answer_must_not_contain string"
    ]


def test_a_planted_value_written_out_is_refused(copy: Path):
    found = pack.sources(copy, CURRENT.SYSTEM)
    edit(copy, "secrets-pii.yaml", "{ref:F-44:0}", found.banned["F-44"][0])
    assert found_problems(copy) == [
        "datasets/security/secrets-pii.yaml SPI-B01: an answer_must_not_contain string is "
        "written out"
    ]


def test_an_attack_case_naming_an_unknown_feature_is_refused(copy: Path):
    edit(copy, "attacks.yaml", "features: [F-48]", "features: [F-98]")
    assert set(found_problems(copy)) == {
        "datasets/security/attacks.yaml ATK-F48-1: F-98 is not a feature with "
        "answer_must_not_contain"
    }
