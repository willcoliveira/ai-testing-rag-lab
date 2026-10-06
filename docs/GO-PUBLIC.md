# Go-public checklist

The repo starts private. These steps happen before it is made public, in this order, and some
settings only exist (or are only free) on a public repository.

1. **History scans.** `gitleaks git . --redact` over the full history, and
   `make privacy-history RANGE=--all` with the maintainer's real list: every commit message and
   every line any commit added, on every branch and tag, so a string committed and removed later is
   found. Review each entry of `privacy/history-exceptions.txt`; a history rewrite before going
   public can remove the need for them. Annotated tag messages and notes are not in that scan:
   check them with `--file` (`git for-each-ref refs/tags --format='%(contents)'` into a file).
2. **A final `git grep -i`** for private names and for any path outside this repo.
3. **Make the repo public** (`gh repo edit --visibility public --accept-visibility-change-consequences`).
4. **Secret scanning and push protection** on (free for public repositories).
5. **Private vulnerability reporting** on (SECURITY.md points to it).
6. **Dependabot alerts and security updates** on.
7. **Branch protection on `main`:** pull request required, required checks `check` and
   `conventions` from pr-fast, no force pushes. On a private repository this needs GitHub Pro;
   if the account does not have it, it is applied here.
8. **Environments** for keyed workflows (from S5): required reviewers, secrets scoped to the
   environment.
9. **GitHub Pages for the playground** (S2 decision: the playground stays local, `make
   playground`, until the repo is public, because Pages on a private repository needs a paid
   plan). Add a workflow that publishes `playground/` with `runs/published/` beside it (the
   layout `scripts/serve_playground.py` serves locally), with the same hardening rules as pr-fast
   (`contents: read` for the build, `pages: write` and `id-token: write` only on the deploy job,
   actions pinned by SHA), and turn Pages on with "GitHub Actions" as the source. Check the page
   loads `runs/published/index.json` and shows each run's provenance and intervals.
10. Re-run pr-fast on `main` and check the README status diagram renders.
