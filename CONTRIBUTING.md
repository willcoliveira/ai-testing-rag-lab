# Contributing

## Setup

```bash
uv sync
make hooks   # required in every clone
make check
```

`make hooks` is required in every clone. It points Git at `.githooks/`: commit-msg checks the
message (privacy and Conventional Commits), pre-commit checks what is staged (privacy, gitleaks,
formatting), and pre-push checks every message and added line of the commits being pushed. Hooks
can be skipped (`--no-verify`); CI then still checks the pull request's files and commits, but with
the example list only, so a maintainer's real names are enforced only where the hooks run.

## How work lands

- One stage per pull request, from a plan in `docs/plans/` with numbered acceptance criteria.
  A planner writes the plan, a developer builds it, an independent judge re-runs the evidence and
  tries to break each gate, and a human reviews and merges. Nothing merges itself.
- **Commits** follow [Conventional Commits 1.0](https://www.conventionalcommits.org/en/v1.0.0/):
  `type(scope): subject`, with type one of feat, fix, docs, test, ci, build, chore, refactor, perf,
  style, revert. The commit-msg hook checks it.
- **Branches** are `<type>/sN-<slug>` for stage work (e.g. `feat/s1a-policy-corpus`) or
  `<type>/<slug>` otherwise. **PR titles** follow the commit format. CI checks both.
- **CHANGELOG.md** gets one line per pull request.
- Every stage PR updates its nodes in `docs/ARCHITECTURE.md` (todo, wip, done), and the README
  status diagram with it.

## Design rules

- `raglab.core` imports the standard library only. Ports and types live there.
- Vendor SDKs (model providers, vector stores, guard libraries) are imported only in
  `raglab.adapters`, which also holds the only constructors for their clients.
  `scripts/check_architecture.py` enforces both rules.
- File-format parsers (pypdf, pytesseract, pyyaml, Pillow) are not vendor SDKs; they are
  imported only in `raglab.ingest`, which turns files into parsed documents for the rest of
  raglab (also enforced by `scripts/check_architecture.py`).
- `corpus/inventory.snapshot.json` is regenerated on purpose with `make inventory-snapshot` after
  a parser, chunker or corpus change, and its diff is reviewed in the pull request.
- Prompts are versioned code with contract tests; no developer comments inside prompt text.
- A provider failure returns an explicit "unavailable" status, never a guessed answer.
- Model ids are dated snapshots, never aliases.
- Results are published only from real runs, with provenance; nothing in this repo invents a number.

## Privacy

`node scripts/check-forbidden.mjs` (`make privacy`) checks every tracked and untracked file, and
with `--file` a commit message. `make privacy-history` checks every commit message and every line
added in a range of commits (`RANGE`, default `--all`): the pre-push hook runs it on the commits
being pushed and CI on a pull request's commits.
`privacy/forbidden-strings.example.txt` holds the generic patterns and is the only list CI uses; it
may contain only comments, `<placeholders>` and `/regex/` lines. A maintainer's real list is
`privacy/forbidden-strings.txt`, which is gitignored and must never be committed: the check refuses
to run, in CI too, while it or any copy of it is in the index. Public tokens that a pattern would
flag go in `privacy/allowlist.txt`; the planted fakes of the lab corpus (example.com and example.org
addresses, `FAKE-` tokens) go in `privacy/allowlist-corpus.txt`, which applies only to files under
`corpus/`; a reviewed false positive in the history goes in
`privacy/history-exceptions.txt` (full commit id, path and line) with its reason.
