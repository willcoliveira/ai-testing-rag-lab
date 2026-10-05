"""Command line entry point. Later stages add ingest, ask, eval and publish."""

import argparse
import sys

from raglab import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="raglab", description=__doc__)
    parser.add_argument("--version", action="version", version=f"raglab {__version__}")
    parser.parse_args(argv)
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
