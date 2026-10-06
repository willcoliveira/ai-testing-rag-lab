# Corpus sources and licences

This is the approved register of the policy corpus: every file under `corpus/`, where it comes
from and under which licence it may be copied and changed. Licence terms are summarised in
[LICENSE.md](LICENSE.md).

**Everything here is fictional lab material.** Halvenroot and Mirrowfen are invented names (search
evidence in [SPEC.md](SPEC.md), section 2). Every person is a role title. Every contact, address,
phone number and token is a visible fake: addresses end in `example.com` or `example.org`, phone
numbers are `555-01xx` numbers and tokens start with `FAKE-`.

**Precedence (requirement R-15).** The inventory below is the register: its ids, statuses and
Supersedes column decide which document is current and which documents are versions of the same
document, never a document's own title, version string, effective date or front matter
(`docs/TEST-PLAN.md`, section 3). The three files under `attacks/` are **deliberate test material,
not policy**: they are ingested only in attack runs, so that tests can show the assistant ignores
them.

## Upstream sources

| Source | What we took | Licence | How we comply |
|---|---|---|---|
| [strongdm/comply](https://github.com/strongdm/comply), `themes/comply-soc2/policies/` at commit `aab484948d71417e35a079c0395bcf42e16a8dd9` (checked 2026-10-06) | Structure and ideas of `password.md`, `access.md`, `remote.md`, `workstation.md`, `classification.md`, `incident.md`, rewritten | Apache-2.0 (root `LICENSE.txt`; the repository has no NOTICE file) | A copy of the licence is in [licenses/Apache-2.0.txt](licenses/Apache-2.0.txt). Each derived file states that it was changed: a `changed` line in its front matter and the visible line "Adapted from strongdm/comply (Apache-2.0); changed by the ai-testing-rag-lab authors." in its document control (Apache-2.0 section 4(b)). |
| NIST SP 800-63B-4, sections 3.1.1.2 and 3.2.2 ([source](https://pages.nist.gov/800-63-4/sp800-63b.html), [doi](https://doi.org/10.6028/NIST.SP.800-63B-4)), retrieved 2026-10-06 | Quoted sentences only, omissions marked `[...]` | NIST public information: a work of the US federal government, which NIST asks to be credited | Credit line in the file's front matter and first paragraph. |
| UK NCSC, "Password policy: updating your approach" ([source](https://www.ncsc.gov.uk/collection/passwords/updating-your-approach)), retrieved 2026-10-06 | Quoted sentences only, omissions marked `[...]`; no logos or images | [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/) | The OGL acknowledgement and a link to the source in the file's front matter and first paragraph. |
| The ai-testing-rag-lab authors | Every other document, the planted values and the answer key | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | — |

**Not used:** JupiterOne security-policy-templates (CC BY-SA 4.0; share-alike would bind the
derived files, and its values are the old style we plant ourselves; the user's decision,
2026-10-06), CIS Controls (CC BY-NC-ND 4.0, no derivatives), SANS policy templates and the GitLab
handbook (no redistribution licence confirmed).

## Inventory

Status says what a file does:

- `approved`: in the pack, and governs: its values are the company's rules.
- `superseded`: in the pack, replaced by the document named in its successor's Supersedes cell;
  retrievable and cited for history only, never as the current rule.
- `reference`: a shared external excerpt, in the pack for both tenants; its values are given only
  attributed to their source, never as a company rule.
- `test material`: a deliberate attack file, never in the pack.
- `support`: a file about the corpus, not a document of it.

Every generated file carries the licence of its Markdown source; the PDF, HTML and PNG
renderings also carry its status and Supersedes cell (the ground-truth text is support).

| Path | Id | Status | Supersedes | Source | Licence | Notes |
|---|---|---|---|---|---|---|
| `corpus/SPEC.md` | — | support | — | ours | CC-BY-4.0 | Corpus specification and planted-value register |
| `corpus/SOURCES.md` | — | support | — | ours | CC-BY-4.0 | This file |
| `corpus/LICENSE.md` | — | support | — | ours | CC-BY-4.0 | Licence summary for the corpus folder |
| `corpus/answer-key.yaml` | — | support | — | ours | CC-BY-4.0 | One entry per planted feature |
| `corpus/build-manifest.json` | — | support | — | ours | CC-BY-4.0 | sha256 of the generated files, written by `scripts/build_corpus.py` |
| `corpus/licenses/Apache-2.0.txt` | — | support | — | comply:LICENSE.txt | Apache-2.0 | The Apache License 2.0 text, copied unchanged from comply |
| `corpus/tenant-a/password-standard-v1.md` | A-PWD-V1 | superseded | — | comply:password.md | Apache-2.0 | Changed: rewritten for Halvenroot, planted values |
| `corpus/tenant-a/password-standard-v2.md` | A-PWD-V2 | approved | A-PWD-V1 | comply:password.md | Apache-2.0 | Changed: rewritten for Halvenroot, planted values; ingested as the PDF |
| `corpus/tenant-a/password-standard-v2.pdf` | A-PWD-V2 | approved | A-PWD-V1 | comply:password.md | Apache-2.0 | Generated from the Markdown (4 pages); carries the change line on page 4 |
| `corpus/tenant-a/mfa-standard.md` | A-MFA | approved | — | ours | CC-BY-4.0 | Ingested as the HTML export |
| `corpus/tenant-a/mfa-standard.html` | A-MFA | approved | — | ours | CC-BY-4.0 | Generated HTML export |
| `corpus/tenant-a/account-lifecycle.md` | A-LIFE | approved | — | comply:access.md | Apache-2.0 | Changed: rewritten for Halvenroot, planted values |
| `corpus/tenant-a/privileged-access-standard.md` | A-PRIV | approved | — | ours | CC-BY-4.0 | |
| `corpus/tenant-a/access-review-procedure.md` | A-REV | approved | — | ours | CC-BY-4.0 | |
| `corpus/tenant-a/remote-access-policy.md` | A-REMOTE | approved | — | comply:remote.md | Apache-2.0 | Changed: rewritten for Halvenroot, planted values |
| `corpus/tenant-a/device-policy.md` | A-DEVICE | approved | — | comply:workstation.md | Apache-2.0 | Changed: rewritten for Halvenroot, vendor names removed, planted values |
| `corpus/tenant-a/device-policy-annex-b-kiosk.md` | A-DEVICE-B | approved | — | ours | CC-BY-4.0 | Ingested only as the scanned PNG |
| `corpus/tenant-a/device-policy-annex-b-kiosk.png` | A-DEVICE-B | approved | — | ours | CC-BY-4.0 | Generated scanned page (rotation and noise) |
| `corpus/tenant-a/device-policy-annex-b-kiosk.gt.txt` | A-DEVICE-B | support | — | ours | CC-BY-4.0 | Ground-truth text of the scanned page, for the OCR test |
| `corpus/tenant-a/data-classification-policy.md` | A-CLASS | approved | — | comply:classification.md | Apache-2.0 | Changed: trimmed, rewritten for Halvenroot, planted values |
| `corpus/tenant-a/account-compromise-runbook.md` | A-IR | approved | — | comply:incident.md | Apache-2.0 | Changed: narrowed to account compromise, planted values; its appendix holds the planted fake PII and secret |
| `corpus/tenant-a/policy-exceptions-process.md` | A-EXC | approved | — | ours | CC-BY-4.0 | |
| `corpus/tenant-a/faq.md` | A-FAQ | approved | — | ours | CC-BY-4.0 | Deliberate near-duplicates of other documents |
| `corpus/tenant-a/glossary.md` | A-GLOSS | approved | — | ours | CC-BY-4.0 | |
| `corpus/tenant-b/password-standard.md` | B-PWD | approved | — | comply:password.md | Apache-2.0 | Changed: rewritten for Mirrowfen, planted values |
| `corpus/tenant-b/mfa-standard.md` | B-MFA | approved | — | ours | CC-BY-4.0 | |
| `corpus/external/nist-sp-800-63b-4-excerpt.md` | X-NIST | reference | — | nist:sp800-63b-4 | NIST-public | Courtesy of NIST; quoted text only |
| `corpus/external/ncsc-password-policy-excerpt.md` | X-NCSC | reference | — | ncsc:password-policy-updating-your-approach | OGL-UK-3.0 | Contains public sector information licensed under the OGL v3.0 |
| `corpus/attacks/hidden-instruction-wifi-note.md` | T-HIDDEN | test material | — | ours | CC-BY-4.0 | **Deliberate test material:** a note with a hidden instruction to AI assistants |
| `corpus/attacks/poisoned-password-standard.md` | T-POISON | test material | — | comply:password.md | Apache-2.0 | **Deliberate test material:** a poisoned near-duplicate of A-PWD-V2. Changed: derived from A-PWD-V2 with weakened values |
| `corpus/attacks/fake-policy-update.md` | T-FAKE | test material | — | ours | CC-BY-4.0 | **Deliberate test material:** a fake "updated policy" page asking for passwords |

## Size

21 documents: 14 tenant A files (12 documents, a second version of the password standard and the
scanned Annex B), 2 tenant B variants, 2 external excerpts and 3 attack files. At the fixed print
layout of `scripts/build_corpus.py` they take the number of pages recorded in
`build-manifest.json` (`print_pages`).
