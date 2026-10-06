"""Conventional Commits 1.0 for commit messages and PR titles, `<type>/<slug>` for branches.

Usage:
  python scripts/check_conventions.py --message-file PATH   # the commit-msg hook
  python scripts/check_conventions.py --title "feat(api): add /healthz"
  python scripts/check_conventions.py --branch chore/s0-repo-skeleton
Exits 1 with the reason when a value does not follow the convention.
"""

import argparse
import re
import sys
from pathlib import Path

TYPES = (
    "feat",
    "fix",
    "docs",
    "test",
    "ci",
    "build",
    "chore",
    "refactor",
    "perf",
    "style",
    "revert",
)
MAX_HEADER = 100
HEADER = re.compile(rf"^(?:{'|'.join(TYPES)})(?:\([a-z0-9][a-z0-9._/-]*\))?!?: \S")
BRANCH = re.compile(rf"^(?:{'|'.join(TYPES)})/(?:s\d+[a-z]?-)?[a-z0-9]+(?:-[a-z0-9]+)*$")
# Messages Git writes itself, matched in full so they cannot carry free text. A merge subject
# follows git's fmt-merge-msg: "Merge " then, per source repository, groups of branches,
# remote-tracking branches, tags and commits ("branch 'a'", "branches 'a', 'b' and 'c'"), joined
# by ", ", then " of <repo>" for a remote one; sources joined by "; "; then " into <branch>".
# A ref name holds no whitespace or quote; a commit is a hex id only.
_NAME = r"'[^'\s]+'"
_HEX = r"'[0-9a-f]{4,64}'"


def _group(singular: str, plural: str, item: str) -> str:
    return rf"(?:{singular} {item}|{plural} {item}(?:, {item})* and {item})"


_GROUP = "|".join(
    (
        # "(early part)": Git's suffix for a merge of an earlier commit of a branch (judge round 4)
        _group("branch", "branches", rf"{_NAME}(?: \(early part\))?"),
        _group("remote-tracking branch", "remote-tracking branches", _NAME),
        _group("tag", "tags", _NAME),
        _group("commit", "commits", _HEX),
    )
)
_SOURCE = rf"(?:HEAD|{_GROUP})(?:, (?:{_GROUP}))*(?: of \S+)?"
GIT_MERGE = re.compile(
    rf"^Merge (?:{_SOURCE}(?:; {_SOURCE})*(?: into \S+)?|pull request #\d+ from \S+)$"
)
# `git revert`, and `git revert` of a revert (Git 2.43+ writes Reapply "<subject>")
GIT_REVERT = re.compile(r'^(?:Revert|Reapply) "(.+)"$')
# `git commit --fixup/--squash`: allowed in commits (squashed away before merge), not in PR titles
AUTOSQUASH = re.compile(r"^(?:fixup|squash|amend)! (.+)$")


def check_header(header: str, *, git_generated: bool = True) -> str | None:
    """None if the header follows the convention, else the reason.

    git_generated allows the merge, revert and reapply subjects Git writes itself (commit messages
    only; a PR title must be a Conventional Commit)."""
    if git_generated:
        if GIT_MERGE.match(header):
            return None
        reverted = GIT_REVERT.match(header)
        if reverted:
            return check_header(reverted.group(1), git_generated=True)
        squashed = AUTOSQUASH.match(header)
        if squashed:
            return check_header(squashed.group(1), git_generated=False)
    if not HEADER.match(header):
        return f'"{header}" is not "type(scope): subject" with type one of {", ".join(TYPES)}'
    if len(header) > MAX_HEADER:
        return f"header is {len(header)} characters, the limit is {MAX_HEADER}"
    return None


def check_message(text: str) -> str | None:
    lines = [line for line in text.splitlines() if not line.startswith("#")]
    header = next((line for line in lines if line.strip()), "")
    if not header:
        return "empty commit message"
    return check_header(header.rstrip())


def check_branch(name: str) -> str | None:
    if name == "main" or name.startswith("dependabot/"):
        return None
    if not BRANCH.match(name):
        return (
            f'branch "{name}" is not "<type>/<slug>" or "<type>/sN-<slug>"'
            f" with type one of {', '.join(TYPES)}"
        )
    return None


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--message-file", type=Path)
    group.add_argument("--title")
    group.add_argument("--branch")
    args = parser.parse_args(argv)
    if args.message_file:
        problem = check_message(args.message_file.read_text(encoding="utf-8"))
    elif args.title is not None:
        problem = check_header(args.title, git_generated=False)
    else:
        problem = check_branch(args.branch)
    if problem:
        print(f"conventions: {problem}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
