#!/bin/sh
# The privacy check on what is staged (the index), not on the working tree: a string that was
# staged and then cleaned up on disk would otherwise reach the commit unseen.
# Used by .githooks/pre-commit. Exit codes as check-forbidden.mjs.
set -eu
repo=$(git rev-parse --show-toplevel)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
git checkout-index -a --prefix="$tmp/"
# the real list is gitignored, so it is not in the index; bring the local copy along if there is one
if [ -f "$repo/privacy/forbidden-strings.txt" ]; then
  mkdir -p "$tmp/privacy"
  cp "$repo/privacy/forbidden-strings.txt" "$tmp/privacy/"
fi
cd "$tmp"
# a throwaway repo, so the script lists files with git (as in the real checkout) instead of
# printing "not a git repository" and walking the tree; nothing is committed in it
git init -q
node scripts/check-forbidden.mjs
