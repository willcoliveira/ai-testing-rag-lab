"""Which planted features a chunk setting keeps together, and what a setting changes.

The rule lives in raglab.ingest.chunk_fit (S8 moved it there, so the cause rule can read it):
a planted feature (corpus/answer-key.yaml) is **kept** at a setting when one chunk of each
section it cites holds every value cited there (a table cell with its header row and its row),
and **split** otherwise, with the reason. This script prints the inventory diff of a setting
against the default and the features split at each.

Usage:
    uv run python scripts/chunk_experiment.py --chunk-size 600 [--overlap 1]

(the halved-size experiment of S1b, recorded in the stage ledger).
"""

import argparse
import sys
from pathlib import Path

from raglab.chunk.sections import ChunkSettings
from raglab.ingest import inventory, pipeline
from raglab.ingest.chunk_fit import read_answer_key, split_groups

ROOT = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--chunk-size", type=int, required=True)
    parser.add_argument("--overlap", type=int, default=ChunkSettings().overlap)
    args = parser.parse_args(argv)
    key = read_answer_key(ROOT)
    default = pipeline.ingest(ROOT)
    trial = pipeline.ingest(ROOT, ChunkSettings(args.chunk_size, args.overlap))
    print(f"inventory diff, default {default.settings} -> {trial.settings}:")
    print(inventory.diff_summary(inventory.snapshot_json(default), inventory.snapshot_json(trial)))
    for name, result in (("default", default), ("trial", trial)):
        splits = split_groups(result.chunks, key)
        print(f"features split at {name} settings ({result.settings}): {len(splits)}")
        for split in splits:
            print(f"  {split}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
