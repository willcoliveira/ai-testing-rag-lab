"""Command line entry point: ingest, fetch-model, eval, compare, publish. Later stages add ask."""

import argparse
import json
import sys
from pathlib import Path

from raglab import __version__
from raglab.adapters import fastembed_embed
from raglab.chunk.sections import DEFAULT_CHUNK_SIZE, DEFAULT_OVERLAP, ChunkSettings
from raglab.ingest import inventory, pipeline

INVENTORY = "runs/tmp/inventory.json"


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
    args = parser.parse_args(argv)
    if args.command == "ingest":
        return ingest(args)
    if args.command == "fetch-model":
        return fetch_model(args)
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
