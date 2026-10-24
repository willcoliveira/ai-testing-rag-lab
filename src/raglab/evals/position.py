"""The position test (S5, how-to 17 step 8): "move the answering chunk to the start, middle and end
of a long context; middle placement is where models degrade". It tests the generator; the judge's
own position bias is the order check (raglab.evals.judged_record).

- **Cases**: the dev single-chunk `answer` cases of the golden file named in the config's
  [position] table (S5: G-01, G-03, G-05, G-06, G-08 to G-12, G-14). Each case's answering chunk
  is the one chunk of its primary labelled section.
- **Context**: the answering chunk and filler chunks of the asker's tenant that belong to none of
  the case's labelled sections or group members, in the retriever's rank order (the config's
  retriever ranking every chunk the tenant may see), as many as fit the prompt budget: the
  current prompt's characters (raglab.generate.prompts.CURRENT; answer-v1 when S5 measured and
  ran it) over the measured characters per token (`measure`, from a generation record's reported
  prompt tokens) stay within the budget. The count is recorded on every line.
- **Positions**: first, middle (index n // 2 of the n + 1 chunks) and last, each case at each
  position for the config's trials, at the config's sampling, through the pipeline's guards with
  the context in place of retrieval.
- **Scored by code first** (raglab.evals.position_record): the label is `answer`, the answer
  cites the answering chunk, and it states the answering section's values as the answer key
  writes them (R-11). The judge's `correct` is reported beside it, in a judged run of this record.
- **Reported**: each position's pass rate with a Wilson interval at n = cases, and the paired
  differences middle minus first and middle minus last with a seeded bootstrap over cases.

The run is a generation record (run record v1) whose lines are of kind `position`; its manifest
carries the [position] settings. Nothing here is gated.
"""

import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from typing import cast

from raglab.core.types import Chunk, ScoredChunk, Status
from raglab.evals import generation, generation_record, golden, record, retrieval
from raglab.evals.config import GenerationConfig, canonical_sha256
from raglab.evals.position_record import POSITION, POSITIONS, answering_index, checks
from raglab.generate.assemble import Assembled
from raglab.generate.pipeline import Pipeline
from raglab.generate.prompts import CURRENT as prompt
from raglab.guard import guard_set
from raglab.ingest.answer_key import Feature

type Json = dict[str, object]


class PositionError(ValueError):
    """A position case cannot be built: not a dev single-chunk answer case, or its answering
    section has more than one chunk."""


def answering_chunk(item: golden.Resolved, chunks: Mapping[str, Chunk]) -> Chunk:
    """The one chunk of a case's primary labelled section (a group's first member)."""
    question = item.question
    if not item.entries:
        raise PositionError(f"{question.case_id}: a position case has a labelled section")
    _, ids = item.entries[0].sections[0]
    if len(ids) != 1:
        raise PositionError(f"{question.case_id}: its answering section has {len(ids)} chunks")
    return chunks[ids[0]]


def fillers(question: golden.Question, ranked: Sequence[ScoredChunk]) -> list[Chunk]:
    """The asker's tenant's chunks, in rank order, that belong to none of the case's labelled
    sections or group members."""
    excluded = {(s.doc_id, s.section_id) for s in question.sections()}
    return [
        r.chunk
        for r in ranked
        if r.chunk.tenant == question.tenant
        and (r.chunk.doc_id, r.chunk.section_id) not in excluded
    ]


def place(answering: Chunk, filler: Sequence[Chunk], position: str) -> list[Chunk]:
    """The context: the fillers in their order with the answering chunk first, in the middle
    (index n // 2 of the n + 1 chunks) or last."""
    index = answering_index(position, len(filler))
    return [*filler[:index], answering, *filler[index:]]


def prompt_chars(question: golden.Question, context: Sequence[Chunk]) -> int:
    """The characters of the current prompt (system and user message) for this context."""
    system, user = prompt.build(
        question.question, question.tenant, [ScoredChunk(c, 0.0) for c in context]
    )
    return len(system) + len(user)


def fit(
    question: golden.Question,
    answering: Chunk,
    candidates: Sequence[Chunk],
    budget_tokens: int,
    chars_per_token: float,
) -> int:
    """How many fillers fit: the most n whose prompt, at chars_per_token, stays within
    budget_tokens (the place of the answering chunk does not change the count)."""
    best = 0
    for n in range(len(candidates) + 1):
        if prompt_chars(question, [answering, *candidates[:n]]) / chars_per_token > budget_tokens:
            break
        best = n
    return best


def measure(prompts: Sequence[tuple[int, int]]) -> float:
    """The characters per token to budget with: the fewest seen over (prompt characters, prompt
    tokens the server reported) pairs, so the estimate errs towards more tokens."""
    ratios = [chars / tokens for chars, tokens in prompts if tokens > 0]
    if not ratios:
        raise ValueError("no prompt with reported tokens to measure")
    return min(ratios)


class FixedContext:
    """A retriever that returns the position's context, in its order, whatever the query."""

    def __init__(self, context: Sequence[Chunk], scores: Mapping[str, float]) -> None:
        self.context = list(context)
        self.scores = scores

    @property
    def name(self) -> str:
        return "position"

    def retrieve(self, query: str, tenant: str, k: int) -> list[ScoredChunk]:
        return [ScoredChunk(c, self.scores.get(c.chunk_id, 0.0)) for c in self.context]


def plan(
    config: GenerationConfig, root: Path, built: Assembled
) -> list[tuple[golden.Question, Chunk, list[Chunk], dict[str, float]]]:
    """Each position case with its answering chunk, the fillers that fit and the ranking's
    scores; PositionError for a case that is not a dev single-chunk answer case."""
    settings = config.position
    if settings is None:
        raise PositionError(f"{config.path} has no [position] table")
    questions = {q.case_id: q for q in golden.load(root / config.dataset)}
    if missing := [i for i in settings.cases if i not in questions]:
        raise PositionError(f"{missing} are not in {config.dataset}")
    for case_id in settings.cases:
        q = questions[case_id]
        shape = (q.kind, q.split, q.extra.get("mix"), q.extra.get("expected"))
        if shape != ("behaviour", "dev", "single-chunk", "answer"):
            raise PositionError(f"{case_id}: a position case is a dev single-chunk answer case")
    chunks = list(built.chunks)
    by_id: dict[str, Chunk] = {str(c.chunk_id): c for c in chunks}
    planned: list[tuple[golden.Question, Chunk, list[Chunk], dict[str, float]]] = []
    for item in golden.resolve([questions[i] for i in settings.cases], chunks):
        question = item.question
        answering = answering_chunk(item, by_id)
        ranked = built.pipeline.retriever.retrieve(question.question, question.tenant, len(chunks))
        candidates = fillers(question, ranked)
        n = fit(
            question,
            answering,
            candidates,
            settings.prompt_budget_tokens,
            settings.chars_per_token,
        )
        scores = {str(r.chunk.chunk_id): round(r.score, 6) for r in ranked}
        planned.append((question, answering, candidates[:n], scores))
    return planned


def run(
    config: GenerationConfig,
    root: Path,
    built: Assembled,
    features: Mapping[str, Feature],
    gate: str = "manual",
    git: retrieval.GitState | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    monotonic: Callable[[], float] = time.monotonic,
) -> tuple[Json, list[Json]]:
    """(manifest without its files block, lines) of one position run."""
    started = monotonic()
    created = clock().replace(microsecond=0)
    git = git or retrieval.git_state(root)
    settings = config.position
    if settings is None:
        raise PositionError(f"{config.path} has no [position] table")
    planned = plan(config, root, built)
    cases: list[Json] = []
    stopped: str | None = None
    cap = config.generation.run_timeout_s
    for question, answering, filler, scores in planned:
        for where in POSITIONS:
            context = place(answering, filler, where)
            pipeline = Pipeline(
                FixedContext(context, scores), built.pipeline.chat, built.pipeline.guards, 1
            )
            for trial in range(1, config.generation.trials + 1):
                if monotonic() - started > cap:
                    stopped = f"the run hit its wall-clock cap of {cap:g} s"
                    break
                outcome = pipeline.ask(
                    question.question, question.tenant, None, config.generation.seed + trial - 1
                )
                case: Json = {
                    "case_id": f"{question.case_id}:{where}",
                    "trial": trial,
                    "split": question.split,
                    "tenant": question.tenant,
                    "question": question.question,
                    "kind": POSITION,
                    "golden_id": question.case_id,
                    "position": where,
                    "expected": "answer",
                    "feature_ids": [
                        str(f) for f in cast(list[object], question.extra["feature_ids"])
                    ],
                    "answering_chunk": answering.chunk_id,
                    "fillers": len(filler),
                    "retrieved": [
                        {
                            "rank": rank,
                            "chunk_id": r.chunk.chunk_id,
                            "score": r.score,
                            "relevant": r.chunk.chunk_id == answering.chunk_id,
                        }
                        for rank, r in enumerate(outcome.retrieved, start=1)
                    ],
                    **generation.answer_fields(outcome),
                }
                case["checks"] = checks(case, features)
                cases.append(case)
            if stopped:
                break
        if stopped:
            break
    if not cases:
        raise PositionError(f"the run stopped before its first case: {stopped}")
    unavailable = sum(1 for c in cases if c["status"] == Status.UNAVAILABLE.value)
    if unavailable:
        reason = f"{unavailable} of {len(cases)} trial(s) unavailable, the model gave no reply"
        stopped = f"{stopped}; {reason}" if stopped else reason
    chunks = list(built.chunks)
    retriever_json: Json = {"kind": config.retriever.kind, "k": config.retriever.k}
    chunker_json: Json = {
        "chunk_size": config.chunker.chunk_size,
        "overlap": config.chunker.overlap,
    }
    embedder_json = {k: v for k, v in built.embedder_description.items() if k != "sha256"}
    generator_json = {k: v for k, v in built.chat_description.items() if k != "sha256"}
    totals: Json = {"cases": len(cases), "duration_s": round(monotonic() - started, 3)}
    if stopped:
        totals["stopped"] = stopped
    position_json: Json = {
        "cases": list(settings.cases),
        "positions": list(POSITIONS),
        "prompt_budget_tokens": settings.prompt_budget_tokens,
        "chars_per_token": settings.chars_per_token,
        "resamples": settings.resamples,
        "seed": config.generation.seed,
    }
    dataset_path = root / config.dataset
    manifest: Json = {
        "schema_version": record.SCHEMA_VERSION,
        "run_id": f"{created:%Y%m%dT%H%M%SZ}-{config.name}-{config.split}-{git.sha[:7]}",
        "created_at": created.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "suite": config.suite,
        "gate": gate,
        "split": config.split,
        "trials": config.generation.trials,
        "seed": config.generation.seed,
        "provenance": built.provenance,
        "partial": stopped is not None,
        "git_sha": git.sha,
        "git_dirty": git.dirty,
        "config": {
            "name": config.name,
            "path": config.path,
            "file_sha256": config.file_sha256,
            "sha256": canonical_sha256(config.resolved()),
        },
        "chunker": {**chunker_json, "sha256": canonical_sha256(chunker_json)},
        "embedder": {**embedder_json, "sha256": canonical_sha256(embedder_json)},
        "retriever": {**retriever_json, "sha256": canonical_sha256(retriever_json)},
        "generator": {**generator_json, "sha256": canonical_sha256(generator_json)},
        "prompt": {"version": prompt.VERSION, "sha256": prompt.fingerprint()},
        "guards": [guard.name for guard in built.pipeline.guards],
        "guard_set": guard_set(built.pipeline.guards),
        "intervals": {"method": "wilson", "level": config.generation.level, "unit": "case"},
        "position": position_json,
        "dataset": {
            "path": config.dataset,
            "sha256": record.sha256_bytes(dataset_path.read_bytes()),
            "questions": len({str(c["case_id"]) for c in cases}),
        },
        "corpus": {
            "documents": len({c.doc_id for c in chunks}),
            "chunks": len(chunks),
            "sha256": retrieval.corpus_sha256(chunks),
        },
        "tools": {**retrieval.tools(built.inventory.tools), "httpx": version("httpx")},
        "results": generation_record.results(
            cases, config.generation.trials, config.generation.level, position_json
        ),
        "totals": totals,
    }
    if config.ollama is not None:
        manifest["ollama"] = {
            k: v for k, v in asdict(config.ollama).items() if k != "memory_margin_gb"
        }
    return manifest, cases
