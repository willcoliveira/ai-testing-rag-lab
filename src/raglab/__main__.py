"""Command line entry point: ingest, fetch-model, eval, compare, publish, gate, ask, serve and
ollama (the local model server's session: up, down, status, session)."""

import argparse
import json
import shlex
import sys
from pathlib import Path

from raglab import __version__
from raglab.adapters import factory, fastembed_embed
from raglab.chunk.sections import DEFAULT_CHUNK_SIZE, DEFAULT_OVERLAP, ChunkSettings
from raglab.core.types import TenantError
from raglab.evals import compare as compare_runs
from raglab.evals import config as eval_config
from raglab.evals import gate as retrieval_gate
from raglab.evals import generation, golden, publish, record, retrieval
from raglab.generate import assemble
from raglab.ingest import inventory, pipeline

INVENTORY = "runs/tmp/inventory.json"
RUNS = "runs/tmp"
GATES = ["manual", "pr-fast", "eval-on-change", "nightly", "weekly", "release"]
EVAL_ERRORS = (
    eval_config.ConfigError,
    factory.AdapterError,
    fastembed_embed.ModelUnavailable,
    golden.DatasetError,
    golden.LabelError,
    pipeline.IngestError,
    TenantError,
    OSError,
)


def ingest(args: argparse.Namespace) -> int:
    root: Path = args.root
    try:
        settings = ChunkSettings(chunk_size=args.chunk_size, overlap=args.overlap)
    except ValueError as error:
        print(f"ingest: {error}", file=sys.stderr)
        return 2
    if args.snapshot and settings != ChunkSettings():
        print("ingest: --snapshot writes the default settings only", file=sys.stderr)
        return 2
    try:
        result = pipeline.ingest(root, settings)
    except (pipeline.IngestError, OSError) as error:
        print(f"ingest failed: {error}", file=sys.stderr)
        return 1
    out: Path = args.out if args.out.is_absolute() else root / args.out
    inventory.write_json(out, inventory.inventory_json(result))
    print(
        f"ingested {len(result.documents)} documents into {len(result.chunks)} chunks "
        f"(chunk size {settings.chunk_size}, overlap {settings.overlap}): {args.out}"
    )
    for empty in result.empty_sections:
        print(f"warning: empty section (heading with no text): {empty}", file=sys.stderr)
    snapshot = inventory.snapshot_json(result)
    if args.snapshot:
        inventory.write_json(root / args.snapshot, snapshot)
        print(f"snapshot written: {args.snapshot}")
    if args.compare:
        old = json.loads((root / args.compare).read_text(encoding="utf-8"))
        print(f"compared with {args.compare}:")
        print(inventory.diff_summary(old, snapshot))
    return 0


def fetch_model(args: argparse.Namespace) -> int:
    try:
        directory, fetched = fastembed_embed.fetch(args.cache)
    except (fastembed_embed.ModelUnavailable, OSError) as error:
        print(f"fetch-model failed: {error}", file=sys.stderr)
        return 1
    state = f"downloaded {', '.join(fetched)}" if fetched else "already in the cache"
    print(
        f"{fastembed_embed.MODEL} at revision {fastembed_embed.REVISION}: {state}; "
        f"every file matches its pinned sha256: {directory}"
    )
    return 0


def _evaluate(args: argparse.Namespace) -> tuple[record.Json, list[record.Json]]:
    root: Path = args.root
    suite: str = getattr(args, "suite", "retrieval")
    if eval_config.suite_of(args.config) != suite:
        raise eval_config.ConfigError(f"{args.config} is not a {suite} config")
    if suite == "generation":
        gen = eval_config.load_generation(args.config, root)
        split_: str | None = getattr(args, "split", None)
        if split_ is not None:
            raise eval_config.ConfigError("a generation run uses its config's split")
        built = assemble.assemble(gen, root)
        return generation.run(gen, root, built, gate=args.gate)
    config = eval_config.load(args.config, root)
    split: str | None = getattr(args, "split", None)
    if split is not None:
        config = eval_config.with_split(config, split)
    embedder, description, provenance = factory.embedder(
        config.embedder.provider, config.embedder.model, config.embedder.revision
    )
    return retrieval.run(config, root, embedder, description, provenance, gate=args.gate)


def evaluate(args: argparse.Namespace) -> int:
    try:
        manifest, cases = _evaluate(args)
    except EVAL_ERRORS as error:
        print(f"eval failed: {error}", file=sys.stderr)
        return 1
    root: Path = args.root
    out: Path = args.out if args.out.is_absolute() else root / args.out
    run_dir = record.write(out, manifest, cases)
    if problems := record.validate(run_dir, root):
        print("eval wrote an invalid run record:\n" + "\n".join(problems), file=sys.stderr)
        return 1
    print((run_dir / record.REPORT).read_text(encoding="utf-8"))
    print(f"run record: {run_dir}")
    if manifest["git_dirty"]:
        print("note: the work tree is dirty, so this run cannot be published", file=sys.stderr)
    return 0


def _run_dir(root: Path, name: Path) -> Path:
    """A run given as a directory, or as a run id under runs/published or runs/tmp."""
    for candidate in (name, root / name, root / publish.PUBLISHED / name, root / RUNS / name):
        if (candidate / record.MANIFEST).is_file():
            return candidate
    raise FileNotFoundError(f"no run record at {name}")


def compare(args: argparse.Namespace) -> int:
    root: Path = args.root
    try:
        a, b = _run_dir(root, args.a), _run_dir(root, args.b)
        result = compare_runs.compare(a, b, root)
    except (compare_runs.CompareError, FileNotFoundError) as error:
        print(f"compare failed: {error}", file=sys.stderr)
        return 1
    out: Path = args.out or root / RUNS / "compare" / f"{a.name}--{b.name}"
    compare_runs.write(result, out)
    print(compare_runs.render(result))
    print(f"written: {out}")
    return 0


def publish_run(args: argparse.Namespace) -> int:
    root: Path = args.root
    try:
        dest = publish.publish(_run_dir(root, args.run), root, baseline=args.baseline)
    except (publish.PublishError, FileNotFoundError) as error:
        print(f"publish refused: {error}", file=sys.stderr)
        return 1
    print(f"published: {dest} (index: {root / publish.PUBLISHED / publish.INDEX})")
    return 0


def gate(args: argparse.Namespace) -> int:
    root: Path = args.root
    try:
        manifest, cases = _evaluate(args)
    except EVAL_ERRORS as error:
        print(f"gate failed: {error}", file=sys.stderr)
        return 1
    key = publish.baseline_key(manifest)
    baseline_dir = publish.baseline_run(root, key)
    if baseline_dir is None:
        print(f"gate failed: no published baseline for {key}", file=sys.stderr)
        return 1
    if problems := record.validate(baseline_dir, root):
        print("gate failed: the baseline is invalid: " + "; ".join(problems), file=sys.stderr)
        return 1
    baseline, _ = record.read(baseline_dir)
    verdict = retrieval_gate.check(baseline, manifest)
    print(f"retrieval no-regression gate ({len(cases)} questions): {verdict.message}")
    return 0 if verdict.passed else 1


def ask(args: argparse.Namespace) -> int:
    """One question through the pipeline; the outcome as JSON. Exit 0 when the status is ok."""
    root: Path = args.root
    try:
        config = eval_config.load_generation(args.config, root)
        built = assemble.assemble(config, root)
    except EVAL_ERRORS as error:
        print(f"ask failed: {error}", file=sys.stderr)
        return 1
    outcome = built.pipeline.ask(args.question, args.tenant, None, config.generation.seed)
    answer = outcome.answer
    print(
        json.dumps(
            {
                "status": answer.status.value,
                "label": answer.label,
                "answer": answer.text,
                "cited_ids": list(answer.cited_ids),
                "conflict": None
                if answer.conflict is None
                else {"chunk_ids": list(answer.conflict.chunk_ids), "note": answer.conflict.note},
                "retrieved_ids": [r.chunk.chunk_id for r in outcome.retrieved],
                "guard_events": [e.reason for e in outcome.events],
                "error": outcome.error,
                "provenance": built.provenance,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0 if answer.status.value == "ok" else 1


def serve(args: argparse.Namespace) -> int:
    """The API and the page; the web framework is imported here only when serving."""
    from raglab.api import server

    try:
        return server.serve(args.config, args.root, args.host, args.port)
    except EVAL_ERRORS as error:
        print(f"serve failed: {error}", file=sys.stderr)
        return 1


def ollama(args: argparse.Namespace) -> int:
    """The local model server for one session (raglab.runtime.ollama; docs/LOCAL-MODEL.md)."""
    from raglab.runtime import ollama as runtime

    root: Path = args.root
    try:
        config = eval_config.load_generation(args.config, root, require_digest=False)
        session = runtime.session_for(config, root)
        if args.action == "up":
            session.up()
            return 0
        if args.action == "down":
            problems = session.down()
            for problem in problems:
                print(f"POSTCHECK FAILED: {problem}", file=sys.stderr, flush=True)
            if not problems:
                print(
                    "postcheck passed: port closed, no ollama process, no model loaded", flush=True
                )
            return 1 if problems else 0
        if args.action == "status":
            print(json.dumps(session.status(), indent=2))
            return 0
        if not args.run:
            print("ollama session: give at least one --run command", file=sys.stderr)
            return 2
        return session.run([shlex.split(c) for c in args.run], runtime.run_command)
    except (eval_config.ConfigError, runtime.SessionError, OSError) as error:
        print(f"ollama {args.action}: {error}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="raglab", description=__doc__)
    parser.add_argument("--version", action="version", version=f"raglab {__version__}")
    commands = parser.add_subparsers(dest="command")
    run = commands.add_parser(
        "ingest", help="parse and chunk the register's documents into an inventory"
    )
    run.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help=f"character budget per chunk (default {DEFAULT_CHUNK_SIZE})",
    )
    run.add_argument(
        "--overlap",
        type=int,
        default=DEFAULT_OVERLAP,
        help=f"paragraphs repeated at the start of the next chunk (default {DEFAULT_OVERLAP})",
    )
    run.add_argument("--root", type=Path, default=Path.cwd(), help="repo root (default: here)")
    run.add_argument(
        "--out", type=Path, default=Path(INVENTORY), help=f"inventory file (default {INVENTORY})"
    )
    run.add_argument(
        "--snapshot", type=Path, help="also write the snapshot here (default settings only)"
    )
    run.add_argument("--compare", type=Path, help="print the diff against this snapshot")
    fetch = commands.add_parser(
        "fetch-model",
        help="download the pinned embedding model files once and check their hashes",
    )
    fetch.add_argument(
        "--cache",
        type=Path,
        help=f"cache directory (default ${fastembed_embed.CACHE_ENV} or ~/.cache/raglab/models)",
    )
    for name, text in (
        ("eval", "run an evaluation suite and write a run record under runs/tmp"),
        ("gate", "retrieval no-regression gate: a fresh run against the published baseline"),
    ):
        sub = commands.add_parser(name, help=text)
        if name == "eval":
            sub.add_argument("--suite", choices=["retrieval", "generation"], required=True)
            sub.add_argument(
                "--split",
                choices=eval_config.SPLITS,
                help="run on another split than the config's (the gate always uses the config's)",
            )
        sub.add_argument("--config", type=Path, required=True, help="a config/*.toml file")
        default_gate = "pr-fast" if name == "gate" else "manual"
        sub.add_argument("--gate", choices=GATES, default=default_gate)
        sub.add_argument("--out", type=Path, default=Path(RUNS), help=f"(default {RUNS})")
        sub.add_argument("--root", type=Path, default=Path.cwd(), help="repo root (default: here)")
    cmp = commands.add_parser("compare", help="paired differences and flipped questions, B - A")
    cmp.add_argument("a", type=Path, help="run A: a directory or a run id")
    cmp.add_argument("b", type=Path, help="run B: a directory or a run id")
    cmp.add_argument("--out", type=Path, help="where compare.json and compare.md go")
    cmp.add_argument("--root", type=Path, default=Path.cwd(), help="repo root (default: here)")
    pub = commands.add_parser("publish", help="validate a run, check privacy, add it to the index")
    pub.add_argument("run", type=Path, help="a run directory or run id")
    pub.add_argument(
        "--baseline", action="store_true", help="make it the baseline of its config and split"
    )
    pub.add_argument("--root", type=Path, default=Path.cwd(), help="repo root (default: here)")
    ask_ = commands.add_parser("ask", help="answer one question as a tenant, printed as JSON")
    ask_.add_argument("question", help="the question")
    ask_.add_argument("--tenant", required=True, help="tenant-a or tenant-b")
    ask_.add_argument("--config", type=Path, required=True, help="a generation config/*.toml")
    ask_.add_argument("--root", type=Path, default=Path.cwd(), help="repo root (default: here)")
    serve_ = commands.add_parser("serve", help="the API and the page (127.0.0.1 by default)")
    serve_.add_argument("--config", type=Path, required=True, help="a generation config/*.toml")
    serve_.add_argument("--host", default="127.0.0.1", help="interface (default 127.0.0.1)")
    serve_.add_argument("--port", type=int, default=8000, help="port (default 8000)")
    serve_.add_argument("--root", type=Path, default=Path.cwd(), help="repo root (default: here)")
    local = commands.add_parser("ollama", help="the local model server, for one session only")
    local.add_argument("action", choices=["up", "down", "status", "session"])
    local.add_argument("--config", type=Path, required=True, help="a config with an [ollama] table")
    local.add_argument(
        "--run", action="append", help="session: a command to run while the server is up"
    )
    local.add_argument("--root", type=Path, default=Path.cwd(), help="repo root (default: here)")
    args = parser.parse_args(argv)
    handlers = {
        "ingest": ingest,
        "fetch-model": fetch_model,
        "eval": evaluate,
        "compare": compare,
        "publish": publish_run,
        "gate": gate,
        "ask": ask,
        "serve": serve,
        "ollama": ollama,
    }
    if args.command in handlers:
        return handlers[args.command](args)
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
