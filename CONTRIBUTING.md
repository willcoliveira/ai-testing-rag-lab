# Contributing

## Setup

```bash
uv sync
make hooks
make check
```

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
- Prompts are versioned code with contract tests; no developer comments inside prompt text.
- A provider failure returns an explicit "unavailable" status, never a guessed answer.
- Model ids are dated snapshots, never aliases.
- Results are published only from real runs, with provenance; nothing in this repo invents a number.

## Privacy

`node scripts/check-forbidden.mjs` checks every tracked file and every commit message.
`privacy/forbidden-strings.example.txt` holds the generic patterns and is the only list CI uses;
a maintainer's real list is `privacy/forbidden-strings.txt`, which is gitignored and must never be
committed (the script refuses to run if it is tracked). Public tokens that a pattern would flag go
in `privacy/allowlist.txt`.
