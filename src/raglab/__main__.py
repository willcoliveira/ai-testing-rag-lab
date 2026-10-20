"""Command line entry point: ingest, fetch-model, check-dataset, eval, compare, judge, canaries,
publish, gate, ask, serve and ollama (the local model server's session: up, down, status,
session)."""

import argparse
import json
import shlex
import signal
import sys
from datetime import UTC, datetime
from pathlib import Path

from raglab import __version__
from raglab.adapters import factory, fastembed_embed
from raglab.chunk.sections import DEFAULT_CHUNK_SIZE, DEFAULT_OVERLAP, ChunkSettings
from raglab.core.types import TenantError
from raglab.evals import compare as compare_runs
from raglab.evals import config as eval_config
from raglab.evals import dataset_check, generation, golden, judged, publish, record, retrieval
from raglab.evals import gate as retrieval_gate
from raglab.generate import assemble
from raglab.ingest import inventory, pipeline
from raglab.judge import canaries

INVENTORY = "runs/tmp/inventory.json"
RUNS = "runs/tmp"
DATASET = "datasets/golden.v1.jsonl"
GATES = ["manual", "pr-fast", "eval-on-change", "nightly", "weekly", "release"]
EVAL_ERRORS = (
    eval_config.ConfigError,
    dataset_check.CheckError,
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


def check_dataset(args: argparse.Namespace) -> int:
    """`raglab check-dataset`: the golden file against its ten rules (raglab.evals.dataset_check);
    exit 1 naming each case and rule."""
    root: Path = args.root
    dataset: Path = args.dataset if args.dataset.is_absolute() else root / args.dataset
    try:
        report = dataset_check.check(root, dataset)
    except dataset_check.CheckError as error:
        print(f"check-dataset: {error}", file=sys.stderr)
        return 1
    print("\n".join(report.lines()))
    return 0 if report.passed else 1


def _check_first(root: Path, dataset: str) -> None:
    """The dataset hard stop every run passes first: a problem stops the run before any model,
    embedder or ingestion starts (S4)."""
    report = dataset_check.check(root, root / dataset)
    if not report.passed:
        raise dataset_check.CheckError(
            "check-dataset stopped the run:\n" + "\n".join(report.lines())
        )
    print("\n".join(report.lines()), file=sys.stderr)  # the pass line


def _held_out(split: str, gate: str) -> None:
    """S4: a run that holds the test cases runs only under the nightly or release gate."""
    if problem := eval_config.held_out_problem(split, gate):
        raise eval_config.ConfigError(problem)


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
        _check_first(root, gen.dataset)
        _held_out(gen.split, args.gate)
        built = assemble.assemble(gen, root)
        return generation.run(gen, root, built, gate=args.gate)
    config = eval_config.load(args.config, root)
    split: str | None = getattr(args, "split", None)
    if split is not None:
        config = eval_config.with_split(config, split)
    _check_first(root, config.dataset)
    _held_out(config.split, args.gate)
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


CONSISTENCY = "consistency gate (Q-05)"


def _consistency(root: Path, run_dir: Path) -> int:
    """The consistency gate on a finished generation run against the published local baseline of
    its config, with the margin of docs/THRESHOLDS.md: one line, exit 0 only when it passes."""

    def say(text: str, passed: bool = False) -> int:
        print(f"{CONSISTENCY}: {text}", flush=True)
        return 0 if passed else 1

    if problems := record.validate(run_dir, root):
        return say(f"refused: {run_dir.name} is not a valid run record: " + "; ".join(problems))
    manifest, _ = record.read(run_dir)
    key = publish.baseline_key(manifest)
    baseline_dir = publish.baseline_run(root, key)
    if baseline_dir is None:
        return say(f"refused: no published baseline for {key} (run {run_dir.name})")
    if problems := record.validate(baseline_dir, root):
        return say("refused: the baseline is invalid: " + "; ".join(problems))
    baseline, _ = record.read(baseline_dir)
    thresholds = root / retrieval_gate.THRESHOLDS
    text = thresholds.read_text(encoding="utf-8") if thresholds.is_file() else ""
    verdict = retrieval_gate.consistency(
        baseline, manifest, retrieval_gate.consistency_margin(text)
    )
    return say(verdict.message, verdict.passed)


def gate(args: argparse.Namespace) -> int:
    root: Path = args.root
    if (args.config is None) == (args.run is None):
        print(
            "gate: give --config (run, then gate) or --run (gate a finished run)", file=sys.stderr
        )
        return 2
    if args.run is not None:
        try:
            run_dir = _run_dir(root, args.run)
        except FileNotFoundError as error:
            print(f"gate failed: {error}", file=sys.stderr)
            return 1
        return _consistency(root, run_dir)
    try:
        suite = eval_config.suite_of(args.config)
    except (eval_config.ConfigError, OSError) as error:
        print(f"gate failed: {error}", file=sys.stderr)
        return 1
    args.suite = suite
    if args.gate is None:  # pr-fast runs the retrieval gate; the consistency gate runs by hand
        args.gate = "manual" if suite == "generation" else "pr-fast"
    if suite == "generation":
        try:
            if (split := eval_config.load_generation(args.config, root).split) != "dev":
                raise eval_config.ConfigError(f"the gate runs on dev, not on {split}")
            manifest, cases = _evaluate(args)
        except EVAL_ERRORS as error:
            print(f"gate failed: {error}", file=sys.stderr)
            return 1
        run_dir = record.write(root / RUNS, manifest, cases)
        print(f"run record: {run_dir}", file=sys.stderr, flush=True)
        return _consistency(root, run_dir)
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


JUDGE_ERRORS = (
    eval_config.ConfigError,
    factory.AdapterError,
    judged.JudgedError,
    canaries.CanaryError,
    golden.DatasetError,
    pipeline.IngestError,
    OSError,
    ValueError,
)


def _say(text: str) -> None:
    print(text, file=sys.stderr, flush=True)


def judge_run(args: argparse.Namespace) -> int:
    """`raglab judge --run <run> --config <judge config>` (S5): the canaries first, then every
    answer of a finished generation run on its criteria, written as a judged run record under
    runs/tmp. Exit 1 when a canary is off its side (no judged call is made, no record written)."""
    from raglab.judge.build import judge_from_config

    root: Path = args.root
    try:
        config = eval_config.load_judge(args.config, root)
        source = _run_dir(root, args.run)
        judge, description, provenance = judge_from_config(config)
        manifest, lines = judged.run(
            config, root, source, judge, description, provenance, gate=args.gate, say=_say
        )
    except canaries.CanaryStop as stop:
        print(f"judge stopped: {stop}", file=sys.stderr, flush=True)
        return 1
    except JUDGE_ERRORS as error:
        print(f"judge failed: {error}", file=sys.stderr, flush=True)
        return 1
    out: Path = args.out if args.out.is_absolute() else root / args.out
    run_dir = record.write(out, manifest, lines)
    if problems := record.validate(run_dir, root):
        print("judge wrote an invalid run record:\n" + "\n".join(problems), file=sys.stderr)
        return 1
    print((run_dir / record.REPORT).read_text(encoding="utf-8"))
    print(f"run record: {run_dir}")
    if manifest["git_dirty"]:
        print("note: the work tree is dirty, so this run cannot be published", file=sys.stderr)
    return 0


def canary_check(args: argparse.Namespace) -> int:
    """`raglab canaries --config <judge config>` (S5): the canary set judged, one line per item;
    exit 1 when any is off its side. A judge session that runs no judged run (DeepEval's checks)
    runs this first."""
    from raglab.judge.build import judge_from_config

    root: Path = args.root
    try:
        config = eval_config.load_judge(args.config, root)
        items = canaries.load(root / config.judging.canaries)
        passages = canaries.corpus_passages(root, items)
        judge, _, _ = judge_from_config(config)
        results = canaries.run(judge, items, passages, config.judging.seed)
    except JUDGE_ERRORS as error:
        print(f"canaries failed: {error}", file=sys.stderr, flush=True)
        return 1
    print("\n".join(judged.summary(results)), flush=True)
    # every call's verdict, reply, seconds and tokens, for the ledger (runs/tmp is gitignored)
    out = root / RUNS / "canaries"
    out.mkdir(parents=True, exist_ok=True)
    log = out / f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}.jsonl"
    rows = canaries.results_json(results)
    log.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8")
    seconds = sorted(r.verdict.latency_ms / 1000 for r in results)
    print(
        f"canaries: {len(results)} calls, {seconds[0]:.3f} to {seconds[-1]:.3f} s a call "
        f"(median {seconds[len(seconds) // 2]:.3f} s); written {log}",
        flush=True,
    )
    if problems := canaries.off_side(results):
        print("canaries: the judge is stopped:\n- " + "\n- ".join(problems), file=sys.stderr)
        return 1
    print(f"canaries: all {len(results)} on their side", flush=True)
    return 0


def position_run(args: argparse.Namespace) -> int:
    """`raglab position --config <a generation config with a [position] table>` (S5, how-to 17
    step 8): each position case with its answering chunk first, in the middle and last of a long
    context, written as a generation record under runs/tmp."""
    from raglab.evals import position
    from raglab.ingest import answer_key

    root: Path = args.root
    try:
        config = eval_config.load_generation(args.config, root)
        if config.position is None:
            raise eval_config.ConfigError(f"{args.config} has no [position] table")
        _check_first(root, config.dataset)
        _held_out(config.split, args.gate)
        built = assemble.assemble(config, root)
        manifest, cases = position.run(
            config, root, built, answer_key.features(root), gate=args.gate
        )
    except (*EVAL_ERRORS, position.PositionError) as error:
        print(f"position failed: {error}", file=sys.stderr)
        return 1
    out: Path = args.out if args.out.is_absolute() else root / args.out
    run_dir = record.write(out, manifest, cases)
    if problems := record.validate(run_dir, root):
        print("position wrote an invalid run record:\n" + "\n".join(problems), file=sys.stderr)
        return 1
    print((run_dir / record.REPORT).read_text(encoding="utf-8"))
    print(f"run record: {run_dir}")
    if manifest["git_dirty"]:
        print("note: the work tree is dirty, so this run cannot be published", file=sys.stderr)
    return 0


def cost_estimate(args: argparse.Namespace) -> int:
    """`raglab cost --judged <run>` (S5, AC12): the tokens a judged record measured, priced with
    config/prices.toml per call, case-trial, run and month for each option of
    config/cost-assumptions.toml (raglab.evals.cost), printed as Markdown."""
    from raglab.evals import cost

    root: Path = args.root
    try:
        run_dir = _run_dir(root, args.judged)
        table = cost.load_prices(args.prices if args.prices.is_absolute() else root / args.prices)
        assumptions = cost.load_assumptions(
            args.assumptions if args.assumptions.is_absolute() else root / args.assumptions, table
        )
        found = cost.measured(run_dir)
        print(cost.render(found, table, assumptions, cost.estimate(found, table, assumptions)))
    except (cost.CostError, FileNotFoundError, KeyError, ValueError) as error:
        print(f"cost failed: {error}", file=sys.stderr)
        return 1
    return 0


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
        # S5: a judge config's session serves its judge; a generation config's its generator
        config = (
            eval_config.load_judge(args.config, root)
            if eval_config.suite_of(args.config) == "judged"
            else eval_config.load_generation(args.config, root, require_digest=False)
        )
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
        try:
            return session.run([shlex.split(c) for c in args.run], runtime.run_command)
        except KeyboardInterrupt:
            # Ctrl-C (judge S3-J13): Session.run has already run its stop, and its lines are
            # above, so one line here instead of a traceback, and 128 + SIGINT. A SIGTERM or
            # SIGHUP ends the session as SystemExit(128 + n), which passes through.
            print(
                "interrupted: see the lines above for the stop and the postcheck",
                file=sys.stderr,
                flush=True,
            )
            return 128 + signal.SIGINT
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
    checked = commands.add_parser(
        "check-dataset",
        help="the golden file against its ten rules, before any run (no model, no embedder)",
    )
    checked.add_argument(
        "--dataset", type=Path, default=Path(DATASET), help=f"golden file (default {DATASET})"
    )
    checked.add_argument("--root", type=Path, default=Path.cwd(), help="repo root (default: here)")
    for name, text in (
        ("eval", "run an evaluation suite and write a run record under runs/tmp"),
        (
            "gate",
            "the retrieval no-regression gate (a retrieval config) or the consistency gate (a "
            "generation config, or --run for a finished run) against the published baseline",
        ),
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
            sub.add_argument("--gate", choices=GATES, default="manual")
        else:
            sub.add_argument("--config", type=Path, help="a config/*.toml file: run, then gate")
            sub.add_argument(
                "--run", type=Path, help="a finished generation run (a directory or a run id)"
            )
            sub.add_argument(
                "--gate",
                choices=GATES,
                help="the run's gate (default pr-fast for retrieval, manual for generation)",
            )
        sub.add_argument("--out", type=Path, default=Path(RUNS), help=f"(default {RUNS})")
        sub.add_argument("--root", type=Path, default=Path.cwd(), help="repo root (default: here)")
    cmp = commands.add_parser("compare", help="paired differences and flipped questions, B - A")
    cmp.add_argument("a", type=Path, help="run A: a directory or a run id")
    cmp.add_argument("b", type=Path, help="run B: a directory or a run id")
    cmp.add_argument("--out", type=Path, help="where compare.json and compare.md go")
    cmp.add_argument("--root", type=Path, default=Path.cwd(), help="repo root (default: here)")
    judging = commands.add_parser(
        "judge",
        help="the canaries, then every answer of a finished generation run on its criteria (S5)",
    )
    judging.add_argument("--run", type=Path, required=True, help="a generation run: dir or id")
    judging.add_argument("--config", type=Path, required=True, help="a judge config/*.toml")
    judging.add_argument("--gate", choices=GATES, default="manual")
    judging.add_argument("--out", type=Path, default=Path(RUNS), help=f"(default {RUNS})")
    judging.add_argument("--root", type=Path, default=Path.cwd(), help="repo root (default: here)")
    where = commands.add_parser(
        "position", help="the position test: the answering chunk first, middle and last (S5)"
    )
    where.add_argument("--config", type=Path, required=True, help="a config with [position]")
    where.add_argument("--gate", choices=GATES, default="manual")
    where.add_argument("--out", type=Path, default=Path(RUNS), help=f"(default {RUNS})")
    where.add_argument("--root", type=Path, default=Path.cwd(), help="repo root (default: here)")
    priced = commands.add_parser(
        "cost", help="a judged run's measured tokens priced per call, case-trial, run, month (S5)"
    )
    priced.add_argument("--judged", type=Path, required=True, help="a judged run: dir or id")
    priced.add_argument("--prices", type=Path, default=Path("config/prices.toml"))
    priced.add_argument("--assumptions", type=Path, default=Path("config/cost-assumptions.toml"))
    priced.add_argument("--root", type=Path, default=Path.cwd(), help="repo root (default: here)")
    canary = commands.add_parser("canaries", help="the judge's canary set, a hard stop (S5)")
    canary.add_argument("--config", type=Path, required=True, help="a judge config/*.toml")
    canary.add_argument("--root", type=Path, default=Path.cwd(), help="repo root (default: here)")
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
        "check-dataset": check_dataset,
        "eval": evaluate,
        "compare": compare,
        "judge": judge_run,
        "canaries": canary_check,
        "position": position_run,
        "cost": cost_estimate,
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
