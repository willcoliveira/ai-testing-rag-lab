#!/bin/sh
# The privacy check on what is staged (the index), not on the working tree: a string that was
# staged and then cleaned up on disk would otherwise reach the commit unseen.
# Used by .githooks/pre-commit. Exit codes as check-forbidden.mjs.
#
# Read-only on the real repo: it copies the index to a temp directory and checks the copy, and it
# never runs a git command that writes (S0 judge round 2: `git init` under the absolute GIT_DIR git
# exports to hooks in a linked worktree rewrote the shared .git/config with core.bare=true).
set -eu
repo=$(git rev-parse --show-toplevel)
cd "$repo"

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
# every index entry, force-added ignored files included, NUL-separated so no name is C-quoted.
# Both commands read GIT_INDEX_FILE, so `git commit -a` and `git commit <path>` are covered too.
# The checker refuses (exit 2) when this list names the real list or a copy of it, in CI mode too.
git ls-files -z --cached >"$tmp/files"
git checkout-index -a --ignore-skip-worktree-bits --prefix="$tmp/tree/"
mkdir -p "$tmp/tree/privacy"
# the real list is gitignored, so it is not in the index; bring the local copy along if there is
# one. A linked worktree has none of its own: take the main worktree's (beside the common .git).
list="$repo/privacy/forbidden-strings.txt"
if [ ! -f "$list" ]; then
  common=$(git rev-parse --path-format=absolute --git-common-dir)
  if [ "$(basename "$common")" = ".git" ]; then
    list="$(dirname "$common")/privacy/forbidden-strings.txt"
  fi
fi
if [ -f "$list" ]; then
  cp "$list" "$tmp/tree/privacy/forbidden-strings.txt"
fi

# From here on no git command can reach the real repo: the variables git exports to hooks
# (GIT_DIR, GIT_INDEX_FILE and the rest of --local-env-vars) are cleared, and repository discovery
# stops at the temp directory. The checker reads the list of index entries, not git.
# shellcheck disable=SC2046
unset $(git rev-parse --local-env-vars) GIT_PREFIX
GIT_CEILING_DIRECTORIES=$tmp
export GIT_CEILING_DIRECTORIES
cd "$tmp/tree"
node "$repo/scripts/check-forbidden.mjs" --files-from "$tmp/files"
