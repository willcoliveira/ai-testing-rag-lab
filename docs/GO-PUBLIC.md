# Go-public checklist

The repo starts private. These steps happen before it is made public, in this order, and some
settings only exist (or are only free) on a public repository.

1. **History scans.** `gitleaks git . --redact` over the full history, and the privacy check with
   the maintainer's real list over every file and every commit message:
   `git log --format=%B | node scripts/check-forbidden.mjs --file /dev/stdin` style, or each
   message to a file.
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
9. Re-run pr-fast on `main` and check the README status diagram renders.
