# Go-public checklist

The repo started private, and these steps ran before and after it was made public, in this
order; some settings only exist (or are only free) on a public repository.

**It was made public on 2026-10-18, after S3 merged (PR #7),** earlier than the main plan's v0.3
timing, so that `main` could have branch protection, which a private repository on the free plan
does not get. The user's words, verbatim: "we can go public to add branch protextion no
problems"; on when: "After S3 merges (Recommended)". The public **demo** still waits for the
system audit and the adversarial re-test before v0.3 (main plan, "Security and audits"). The
history was kept, so the run records and ledgers keep their commit ids. Commits use the GitHub
noreply address from 2026-10-18; earlier commits keep the author address they were made with.

1. **History scans.** `gitleaks git . --redact` over the full history, and
   `make privacy-history RANGE=--all` with the maintainer's real list: every commit message and
   every line any commit added, on every branch and tag, so a string committed and removed later is
   found. Review each entry of `privacy/history-exceptions.txt`; a history rewrite before going
   public can remove the need for them. Annotated tag messages and notes are not in that scan:
   check them with `--file` (`git for-each-ref refs/tags --format='%(contents)'` into a file).
   *Done 2026-10-18:* gitleaks over all refs, "no leaks found"; `make privacy-history
   RANGE=--all` with the real list, "0 hits in 168 commits"; both entries of
   `privacy/history-exceptions.txt` are in the privacy script itself and were reviewed; no tags.
2. **A final `git grep -i`** for private names and for any path outside this repo.
   *Done 2026-10-18:* no private names. The only path-like strings in any branch are the planted
   fake `/Users/someone/secret/path` in `tests/api/test_api.py`, which checks that error replies
   never echo internal text. Every pull request's title, body, comments and reviews (#1 to #7)
   also passed the privacy check (`--file`), and the repo had no issues, Actions artifacts,
   environments or secrets.
3. **Make the repo public** (`gh repo edit --visibility public --accept-visibility-change-consequences`).
   *Done 2026-10-18, after `main`'s CI passed at the merge commit `fbba9c6`.*
4. **Secret scanning and push protection** on (free for public repositories).
   *Done 2026-10-18; no alerts when checked twice in the minutes after it was switched on. An
   alert on one of the corpus's planted fakes is closed as "used in tests"; any other alert is
   reported.*
5. **Private vulnerability reporting** on (SECURITY.md points to it). *Done 2026-10-18.*
6. **Dependabot alerts and security updates** on. *Done 2026-10-18.*
7. **Branch protection on `main`:** pull request required, required checks `check` and
   `conventions` from pr-fast, no force pushes. On a private repository this needs GitHub Pro;
   if the account does not have it, it is applied here.
   *Done 2026-10-18:* a pull request is required with 0 approvals (one maintainer cannot approve
   their own pull request); `check` and `conventions` are required and must be up to date; no
   force pushes and no deletion; admins are not bound (the user's choice, verbatim: "Exclude
   admins"). Merged branches `feat/s1a-policy-corpus` and `feat/s3-generation` were deleted.
8. **Environments** for keyed workflows (from S5): required reviewers, secrets scoped to the
   environment. *Open: S5.*
9. **GitHub Pages for the playground** (S2 decision: the playground stays local, `make
   playground`, until the repo is public, because Pages on a private repository needs a paid
   plan). Add a workflow that publishes `playground/` with `runs/published/` beside it (the
   layout `scripts/serve_playground.py` serves locally), with the same hardening rules as pr-fast
   (`contents: read` for the build, `pages: write` and `id-token: write` only on the deploy job,
   actions pinned by SHA), and turn Pages on with "GitHub Actions" as the source. Check the page
   loads `runs/published/index.json` and shows each run's provenance and intervals.
   *Open: a small workflow pull request, now that the repo is public.*
10. Re-run pr-fast on `main` and check the README status diagram renders.
    *`main`'s CI passed at `fbba9c6` (run 39160869584) just before the flip; the diagram is for
    the reviewer to check on the repo page.*
