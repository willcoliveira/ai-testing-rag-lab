"""A pull request adds at least one line to CHANGELOG.md, unless a bot opened it.

Usage: python scripts/check_changelog.py --base SHA --head SHA --author LOGIN
"""

import argparse

# runs git only, with an argument list and no shell
import subprocess  # nosec B404
import sys


def added_lines(base: str, head: str) -> list[str]:
    # git from PATH; base and head are SHAs from the PR event; no shell
    diff = subprocess.run(  # nosec B603 B607
        ["git", "diff", "--unified=0", f"{base}...{head}", "--", "CHANGELOG.md"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    lines = diff.splitlines()
    removed = {
        line[1:].strip() for line in lines if line.startswith("-") and not line.startswith("---")
    }
    # an existing line re-added with only whitespace changed is not a new entry
    return [
        line[1:]
        for line in lines
        if line.startswith("+")
        and not line.startswith("+++")
        and line[1:].strip()
        and line[1:].strip() not in removed
    ]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--author", required=True)
    args = parser.parse_args(argv)
    if args.author.endswith("[bot]"):
        print(f"changelog: {args.author} is a bot, exempt")
        return 0
    if not added_lines(args.base, args.head):
        print("changelog: add a line to CHANGELOG.md describing this change", file=sys.stderr)
        return 1
    print("changelog: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
