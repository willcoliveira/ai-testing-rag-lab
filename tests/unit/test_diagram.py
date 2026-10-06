"""docs/ARCHITECTURE.md is the progress map; stage plans name only nodes that exist (AC13)."""

import re

import pytest

from tests.conftest import ROOT

pytestmark = pytest.mark.unit
EXPECTED_NODES = {
    "S0",
    "S1a",
    "S1b",
    "S2",
    "S3",
    "S3h",
    "S4",
    "S4b",
    "S5",
    "S6",
    "S7",
    "S8",
    "S9",
    "S10",
    "S11",
    "S12",
    "B",
}
STATUSES = {"todo", "wip", "done"}


def mermaid_blocks(text: str) -> list[str]:
    return re.findall(r"```mermaid\n(.*?)```", text, flags=re.S)


def phase_map() -> str:
    text = (ROOT / "docs" / "ARCHITECTURE.md").read_text(encoding="utf-8")
    blocks = mermaid_blocks(text)
    assert len(blocks) == 4, "expected the 4 diagrams"
    return blocks[3]


def node_status(block: str) -> dict[str, list[str]]:
    status: dict[str, list[str]] = {}
    for cls_line in re.findall(r"^\s*class\s+(\S+)\s+(\w+)\s*$", block, flags=re.M):
        nodes, cls = cls_line
        for node in nodes.split(","):
            status.setdefault(node, []).append(cls)
    return status


def test_every_stage_node_is_present():
    block = phase_map()
    defined = set(re.findall(r"\b(S\d+[a-z]?|B)\[", block))
    assert defined == EXPECTED_NODES


def test_each_node_has_exactly_one_known_status():
    status = node_status(phase_map())
    assert set(status) == EXPECTED_NODES
    for node, classes in status.items():
        assert len(classes) == 1, f"{node} has {classes}"
        assert classes[0] in STATUSES, f"{node} has unknown status {classes[0]}"


def plan_nodes() -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for plan in sorted((ROOT / "docs" / "plans").glob("*.md")):
        front = re.match(r"^---\n(.*?)\n---\n", plan.read_text(encoding="utf-8"), flags=re.S)
        if front:
            nodes = re.search(r"^nodes:\s*\[(.*?)\]\s*$", front.group(1), flags=re.M)
            if nodes:
                found[plan.name] = [n.strip() for n in nodes.group(1).split(",") if n.strip()]
    return found


def test_stage_plans_name_only_existing_nodes():
    plans = plan_nodes()
    assert plans, "no stage plan with a nodes: front matter"
    for name, nodes in plans.items():
        unknown = set(nodes) - EXPECTED_NODES
        assert not unknown, f"{name} names unknown nodes {unknown}"
