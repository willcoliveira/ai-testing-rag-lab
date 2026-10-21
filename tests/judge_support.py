"""Judged runs for the S5 tests: a finished behaviour run as the source
(tests.generation_support.behaviour_run, its small pack and the real answer key), a small canary
set and a criteria file written into the test's root, and a judge whose replies are scripted:
FakeChat, or (local=True) the OpenAI-compatible adapter against the in-process stub server, so the
record is not fake and publish may read it."""

import json
import re
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from raglab.adapters import factory
from raglab.adapters.fake import FakeChat
from raglab.chunk.sections import ChunkSettings
from raglab.core.ports import ChatModel
from raglab.core.types import ChatMessage, ChatRequest
from raglab.evals import config as eval_config
from raglab.evals import judged, record
from raglab.ingest.pipeline import Inventory
from raglab.judge.llm import LLMJudge
from tests.generation_support import (
    BEHAVIOUR_CHUNKS,
    DIGEST,
    behaviour_run,
    completion,
    stub_client,
    stub_ollama,
)
from tests.retrieval_support import GIT

INVENTED = "INVENTED"
CANARIES: list[dict[str, Any]] = [
    {
        "id": "C-01",
        "criterion": "grounded",
        "side": "fail",
        "purpose": "An invented value.",
        "question": "How many reset attempts are allowed a day?",
        "passages": [
            {
                "chunk_id": "A-TEST@1.0/1/1",
                "document": "Test standard",
                "version": "1.0",
                "section": "1",
                "status": "approved",
                "text": "User passwords expire every 60 days.",
            }
        ],
        "answer": f"{INVENTED}: five reset attempts a day.",
    },
    {
        "id": "C-02",
        "criterion": "relevant",
        "side": "pass",
        "purpose": "Known good.",
        "question": "How long must a password be?",
        "answer": "At least 15 characters.",
    },
]
WHEN = datetime(2026, 10, 20, 12, 0, 0, tzinfo=UTC)

type Script = Callable[[ChatRequest], str]


def verdict(value: str, quote: str = "", ids: list[str] | None = None) -> str:
    return json.dumps(
        {
            "answer_quote": quote,
            "passage_ids": ids or [],
            "reason": "Scripted.",
            "verdict": value,
        }
    )


def criterion_of(request: ChatRequest) -> str:
    found = re.search(r"^Criterion: (\w+)$", request.messages[-1].content, flags=re.M)
    assert found is not None
    return found.group(1)


def answer_of(request: ChatRequest) -> str | None:
    found = re.search(r"<answer>\n(.*?)\n</answer>", request.messages[-1].content, flags=re.S)
    return found.group(1) if found else None


def passage_ids_of(request: ChatRequest) -> list[str]:
    return re.findall(r'<passage id="([^"]*)"', request.messages[-1].content)


def script(request: ChatRequest) -> str:
    """pass on every answer but one marked INVENTED, quoting the answer's first words."""
    answer = answer_of(request)
    quote = (answer or "")[:12]
    return verdict("fail" if answer and INVENTED in answer else "pass", quote)


def judge_config_text(cap: int = 600) -> str:
    return (
        'name = "judge-test"\nsuite = "judged"\n\n[judge]\nprovider = "fake"\n'
        'model = "fake-judge"\n\n[judging]\nseed = 11\nlevel = 0.95\n'
        f'run_timeout_s = {cap}\ncriteria = "CRITERIA.md"\ncanaries = "canaries.jsonl"\n'
    )


def write_canaries(root: Path, items: list[dict[str, Any]] | None = None) -> Path:
    path = root / "canaries.jsonl"
    rows = CANARIES if items is None else items
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return path


def judged_root(tmp_path: Path, local: bool = True, trials: int = 2) -> tuple[Path, Path]:
    """(root, source run) of a finished behaviour run (local by default, as publish needs), with
    the canary set, a criteria file and the judge config written into its root."""
    root, source = behaviour_run(tmp_path, local=local, trials=trials)
    write_canaries(root)
    (root / "CRITERIA.md").write_text("# Criteria (test)\n", encoding="utf-8")
    (root / "config" / "judge.toml").write_text(judge_config_text(), encoding="utf-8")
    return root, source


def config(root: Path, cap: int | None = None) -> eval_config.JudgeConfig:
    path = root / "config" / "judge.toml"
    if cap is not None:
        path.write_text(judge_config_text(cap), encoding="utf-8")
    return eval_config.load_judge(path, root)


def small_inventory() -> Inventory:
    return Inventory(ChunkSettings(), {"pypdf": "x"}, (), tuple(BEHAVIOUR_CHUNKS))


def fake_judge(fn: Script = script) -> tuple[LLMJudge, FakeChat]:
    chat = FakeChat(fn, name="fake-judge")
    return LLMJudge(chat), chat


def local_judge(fn: Script = script) -> tuple[LLMJudge, dict[str, object], str]:
    """The judge through the OpenAI-compatible adapter against the stub server: a local judge."""

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        messages = tuple(ChatMessage(m["role"], m["content"]) for m in body["messages"])
        return completion(fn(ChatRequest(messages, "s", {}, body["seed"])), 300, 40)

    chat: ChatModel
    chat, description, provenance = factory.chat(
        "openai-compat",
        "stub-judge:1b",
        digest=DIGEST,
        base_url="http://127.0.0.1:11434",
        temperature=0.0,
        max_tokens=512,
        timeout_s=5,
        response_format="json_schema",
        client=stub_client(stub_ollama(handler, model="stub-judge:1b")),
    )
    return LLMJudge(chat), description, provenance


def run_judged(
    root: Path,
    source: Path,
    judge: LLMJudge | None = None,
    description: dict[str, object] | None = None,
    provenance: str = "fake",
    cap: int | None = None,
    monotonic: Callable[[], float] | None = None,
    when: datetime = WHEN,
) -> Path:
    """A judged run of source written under root/runs/tmp; its directory."""
    if judge is None:
        judge, chat = fake_judge()
        description = chat.describe()
    kwargs: dict[str, Any] = {"monotonic": monotonic} if monotonic else {}
    manifest, lines = judged.run(
        config(root, cap),
        root,
        source,
        judge,
        description or {"provider": "fake", "model": "fake-judge", "digest": "fake"},
        provenance,
        git=GIT,
        clock=lambda: when,
        inventory=small_inventory(),
        **kwargs,
    )
    return record.write(root / "runs" / "tmp", manifest, lines)


def reseal(run_dir: Path, manifest: dict[str, Any], lines: list[dict[str, Any]]) -> None:
    """Rewrite a judged run with its results, report and file hashes recomputed, as a careful
    hand edit would: only the checks against the source and the replies can tell."""
    body = {k: v for k, v in manifest.items() if k != "files"}
    body["results"] = record.expected_results(body, lines)
    cases_bytes = record.cases_text(lines).encode()
    report_bytes = record.render(body, lines).encode()
    (run_dir / record.CASES).write_bytes(cases_bytes)
    (run_dir / record.REPORT).write_bytes(report_bytes)
    full = {
        **body,
        "files": {
            record.CASES: record.sha256_bytes(cases_bytes),
            record.REPORT: record.sha256_bytes(report_bytes),
        },
    }
    (run_dir / record.MANIFEST).write_text(json.dumps(full, indent=2) + "\n", encoding="utf-8")
