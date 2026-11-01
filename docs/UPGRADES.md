# Upgrade records

One record per dependency or model upgrade, in a fixed shape (how-to 10 as the S8 plan words it),
the lab form of the release gate's "upgrade replay" (`docs/releases/v0.1.0.md`'s release-gate
table, `runbooks/release.md`). A record is written from the merged commit of the upgrade, with the
gates re-run at it and their lines quoted; it never invents a number.

## The shape

Each record is a section `## <date>: <what moved>` with these parts, in this order:

1. **What moved.** The package (or model), from, to, and the cooldown read (Dependabot's seven-day
   cooldown, or the reason it was not waited for); the pull request and its merge commit.
2. **What was replayed.** The gates re-run at the upgrade, each with its command and its line:
   `make check` (the tail, `/usr/bin/time -p`), `make gate` (the retrieval no-regression line),
   `make replay` (the guard set over the consistency baseline), `make guard-suites` (the record
   written); and whether any baseline went stale by rule (the retrieval gate reads the config
   sha256, which names the model and revision and not the library versions; the consistency gate
   reads the dataset, config, prompt, model digest and trials), which is what the record exists to
   say.
3. **What was tried and not taken.** A bump tested and left out, with the test that refused it.
4. **What changed in the docs.** The files the upgrade touched beside the lock.
5. **The decision**, with its date and the maintainer's words, verbatim.

## Records

The first record is the dependency upgrade of 2026-10-31 (the pull request #35, branch
`build/deps-2026-10-28`, commit `e5969f4` before its merge): fastapi, starlette and ruff bumped,
the googleapis-common-protos constraint off, the DeepEval tool re-locked, pypdf 6.21.2 tried and
not taken, and the pypdf advisories skipped under the 2026-11-21 review date. It is written here
from the merged commit, after `main` is merged into S8's branch, with its replay run then; until
then this file holds the shape only. fastembed 0.9.1 (which lifts the Pillow cap) is open: a second
record only if the maintainer takes it inside S8, with the retrieval baseline compared before and
after.
