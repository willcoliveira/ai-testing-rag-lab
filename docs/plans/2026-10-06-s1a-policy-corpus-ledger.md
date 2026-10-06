---
stage: S1a
nodes: [S1a]
---

# S1a ledger: requirements, corpus pack and answer key

Plan: [2026-10-06-s1a-policy-corpus.md](2026-10-06-s1a-policy-corpus.md).

## Approval

The user's answers, verbatim (2026-10-06, quoted in the plan): JupiterOne templates: "No, write
those parts ourselves (Recommended)"; plan: "Approve and start".

S0 follow-up: AC12 of S0 (Dependabot accepted by GitHub) was confirmed after PR #1 merged; see the
"After merge" section of the S0 ledger.

## How the stage ran

1. A PM agent wrote `docs/TEST-PLAN.md` part 1 and `corpus/SPEC.md` (names, layout, front matter,
   briefs and the planted-value register).
2. One author agent per document wrote the 21 corpus files from the SPEC (none committed).
3. The developer (this ledger) checked every file against the register, fixed the drift and the
   unplanted contradictions, built the answer key, sources, licence notes, the build script and the
   tests, and committed.

## Developer fixes to the authors' drafts

| File | Problem | Fix |
|---|---|---|
| `tenant-a/access-review-procedure.md` 3.2 | said privileged accounts are defined in the Privileged Access Standard; the definition lives only in the glossary (F-20), and the Privileged Access Standard says so | points to the Halvenroot Security Glossary, section 10 |
| `tenant-a/access-review-procedure.md` 3.3 | a service account with privileged rights is a privileged account (glossary 10), so 3.2 (30 days) and 3.3 (12 months) both applied: an unplanted conflict | one sentence: such an account is reviewed under section 3.2 |
| `tenant-a/faq.md` Q6 | "Yes" to working from a café, while the Remote Access Policy section 5 requires written line-manager authorisation for telework | adds that sentence with its citation |
| `tenant-a/password-standard-v1.md` 3 | banned the browser "remember password" feature while v2 4.6 allows autofill: a v1/v2 difference the register does not plant | sentence removed (no value involved) |
| `tenant-a/account-compromise-runbook.md` 2 | the account-compromise definition was broken across lines mid-sentence | one line |

Checked and left as written: every author report's notes (the fixed `changed` format, word
counts, connecting prose without values). No register value had drifted: every one is found
verbatim at its cited place by `test_answer_key.py`.

## Decisions taken in assembly (for the review)

- **Corpus allowlist is token by token, not a path exemption.** `privacy/allowlist-corpus.txt`
  lists the 8 planted fakes the generic patterns flag (5 example.com/.org addresses,
  the attack canary token, the two exception ids). `scripts/check-forbidden.mjs` applies it only to files
  under `corpus/`, in tree, staged and history scans, never to commit messages or identities. An
  unlisted address inside `corpus/` is still a hit. gitleaks found nothing in the corpus, so no
  gitleaks allowlist was added; the scope test still guards any future one.
- **The key's tokens:** the planted secret (`FAKE-HVR-...`) and the 555 numbers match no generic
  pattern, so they need no allowlist entry.
- **Annex B has no "Document control" section.** SPEC section 7 fixes its layout as a signed memo,
  which conflicts with SPEC section 5; the memo layout was kept and the test exempts it.
- **Owner and approver roles** were chosen by each author (SPEC fixes none); they differ across
  documents (IAM team, IT Operations Manager, SOC; approver CISO, CEO for classification, Head of
  Mirrowfen). No value depends on them.
- **`markdown` was not added**: it ships no type information and pyright is strict on `scripts/`,
  so the HTML export uses a small renderer in `build_corpus.py` (the same block parser as the PDF).
- **deptry**: `fpdf`, `PIL` and `pypdf` are ignored for DEP004 only (dev dependencies imported from
  `scripts/`), with the reason in `pyproject.toml`.
- **PNG determinism** is compared on pixels, not file bytes (zlib builds differ). The pixels match
  only when FreeType is the version the manifest records (2.14.3, bundled with Pillow 12.3.0); with
  another FreeType the test compares size and ground truth and skips the manifest comparison.
  Whether CI's Linux wheel renders the same pixels shows on the PR.
- **Page count.** At the fixed print layout (A4, 20 mm margins, Helvetica 10.5 pt, each document
  starting on a new page) the 21 documents take **44 pages**; the bodies hold 12,997 words, about
  37 pages at the plan's 350 words a page. The difference is the half-empty last page of each
  document. The plan's "about 30–40 pages" is met by words, not by rendered pages; the reviewer
  decides whether that needs a change.

## Developer evidence (2026-10-06)

| # | Result | Evidence |
|---|---|---|
| AC1 | met (judge to review) | `docs/TEST-PLAN.md` part 1: users and jobs, R-01 to R-22, safety R-16 to R-21, Q-01 to Q-06, out of scope, traceability and gaps. `test_test_plan.py` (6 tests): sections in order, the five users, R-ids unique and without holes, every R-id in the traceability table, every gap row has a reason. **Break:** R-19 renamed in its table row, 1 test fails; restored |
| AC2 | met | `test_answer_key.py::test_every_requirement_is_covered_or_a_gap`: plan R-ids = key R-ids ∪ gaps (R-02, R-20, R-21, R-22, each with a reason, equal to the plan's gaps table); `test_traceability_rows_agree_with_the_key`. **Break:** gap R-22 renamed to R-23 in the key, 1 fails; restored |
| AC3 | met, page count to review | 14 tenant A files (12 documents), 2 tenant B, 2 external, 3 attack (`test_corpus_sources.py::test_pack_size`); inventory in `corpus/SOURCES.md`; build page count 44 at the print layout (`corpus/build-manifest.json`, `print_pages`), 12,997 words (about 37 pages at 350 words a page) |
| AC4 | met | `test_corpus_sources.py`: every file under `corpus/` is in the SOURCES inventory with a licence from {Apache-2.0, CC-BY-4.0, NIST-public, OGL-UK-3.0} and matching front matter; the 9 comply-derived files carry the fixed `changed` line and the visible change line; no source or licence matches JupiterOne, CIS, SANS, GitLab or a share-alike, NC or ND licence; `corpus/licenses/Apache-2.0.txt` copied from comply `LICENSE.txt` at `aab4849` (comply has no NOTICE file: 404 for NOTICE, NOTICE.txt, NOTICE.md). **Break:** a SOURCES row renamed, 2 fail; the visible change line removed from A-LIFE, 1 fails; restored |
| AC5 | met | `corpus/answer-key.yaml`: 79 features (F-01 to F-53, F-60 to F-85), equal to the SPEC register's ids, expected behaviours, tenants and R-ids. `test_answer_key.py` (20 tests): every value verbatim (whitespace normalised) in its section, its paragraph, its table cell, its PDF page and in the rendered PDF, HTML or ground-truth text; omission phrases (F-32, the F-22 "18:00" check, F-40 for tenant B) appear nowhere in their scope; the scanned-only value is in no other document; no tenant A file states a sign-in protection number outside Table 1 (and v1 4.4); no single document holds both halves of a multi-hop feature. **Breaks:** F-01 value changed to 16, 3 fail; "reset attempts" added to the glossary, 1 fails; "7 failed attempts" added to the FAQ, 1 fails; the kiosk value copied into the Device Policy, 1 fails; all restored |
| AC6 | met | `test_answer_key.py::test_version_and_tenant_conflicts_really_differ` (F-04 to F-07 old against new, with v1 superseded and v2 current; F-34 to F-39 and F-52 tenant B against tenant A: numbers disjoint or exactly one side negates) and `test_company_expiry_contradicts_the_quoted_external_lines` (v2 4.4 states expiry; the quoted NIST and NCSC lines argue against it; v2 section 6 does not claim a disagreement). **Break:** v1 4.3 changed to 60 days, 2 fail; restored |
| AC7 | met locally; Linux pixels need CI | `test_corpus_build.py` (9 tests): a rebuild into a temp dir gives the same PDF bytes and extracted text, the same HTML and ground truth, the same PNG pixels (FreeType 2.14.3) and the same manifest; the manifest's sha256 match the committed files and their Markdown sources; the PDF has 4 pages with each section on its marked page; the HTML has an anchor per section. `uv run python scripts/build_corpus.py --check` prints "up to date". **Break:** v2 Markdown edited without a rebuild, 3 fail; restored |
| AC8 | needs the hygiene reviewer | the PM's searches are in `corpus/SPEC.md` section 2; the reviewer repeats them and records the result here |
| AC9 | met | contacts are example.com/.org, phones `555-01xx`, tokens `FAKE-` (`test_corpus_sources.py::test_every_email_phone_and_token_is_visibly_fake`). `make privacy`: 0 hits across 90 files with the real list (42 rules); gitleaks dir and git: no leaks. `test_corpus_allowlist_scope.py` (16 tests): every corpus allowlist entry is visibly fake; none is in the global allowlist; all pass under `corpus/` and each is a hit at 8 paths outside it (including `docs/corpus/x.md` and `corpus.md`) and in a commit message; an unlisted address under `corpus/` is a hit; any gitleaks allowlist matching a corpus path matches nothing outside. **Break:** the `inCorpus` condition replaced with `true`, 9 fail; restored |
| AC10 | pending | the three-lens review, merge agent and decision list come next |
| AC11 | met (CI check on the PR) | `docs/ARCHITECTURE.md` and README mark S1a done (`test_diagram.py`, `test_readme.py` pass); CHANGELOG line added; S0 AC12 noted above |
| AC12 | needs CI | — |

`make check`: exit 0, 309 tests passed (macOS arm64, Python 3.13.12, uv 0.12.23, gitleaks 8.30.1,
node 24.14.1).
