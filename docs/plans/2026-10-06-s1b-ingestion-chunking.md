---
stage: S1b
name: ingestion-and-chunking
nodes: [S1b]
date: 2026-10-06
status: approved 2026-10-06
---

# S1b: Ingestion and chunking

Part of the main plan (phase P1, release v0.1). Branch: `feat/s1b-ingestion-chunking`.
Build project stage 1 / how-to 17 step 2. This is the first pipeline code. It is deterministic and
needs no model.

## Goal

Turn the S1a pack into chunks that later stages can retrieve, and test every step without a
model:
- each format parses to the text a reader sees;
- every chunk carries the metadata that retrieval, citation and tenant isolation need;
- every chunking choice is visible as a diff.

## Out of scope

Embeddings, the index, retrieval (S2), the generation pipeline (S3) and guardrails beyond the
tenant field.

## What gets built

```
src/raglab/core/types.py     Document, Page, Chunk (frozen dataclasses), ChunkId; stdlib only
src/raglab/core/ports.py     Parser and Chunker protocols
src/raglab/ingest/           register.py (reads corpus/register.yaml), frontmatter.py,
                             markdown.py, pdf.py (pypdf), html.py (stdlib parser), ocr.py (Tesseract)
src/raglab/chunk/            section-aware chunker: split on section ids, then paragraphs, under a
                             character budget, with paragraph overlap; contextual prefix off (S2)
src/raglab/ingest/pipeline.py  register -> parse -> chunk -> inventory
cli: raglab ingest [--chunk-size N --overlap N] -> runs/tmp/inventory.json
corpus/inventory.snapshot.json   committed snapshot of the chunk inventory (default settings)
docs/TEST-PLAN.md part 2       how-to 17 test plan: one named check per pipeline arrow
```

**Chunk metadata:**
- chunk id, doc id, version, status, tenant, kind;
- section id and title, print page (for the PDF and the scanned page);
- source licence, char span, text, and the sha256 of the text.

**Each chunk is reproducible:** the same inputs and settings always give the same ids.

**The register is the input.** Ingestion reads `corpus/register.yaml` (D-05) and the formats it
names. Attack documents are not in the register; they are ingested by a separate attack-fixture
loader, so that S7 can add them deliberately.

## Choices I made (you can change them)

| Item | Choice | Why |
|---|---|---|
| Chunking | section-aware: split on the corpus's stable section ids, then paragraphs, under a character budget (default 1,200 characters), overlap of one paragraph | the pack has stable section ids (S1a), and citations point to sections; fixed-size windows would cut rules from their exceptions more often |
| Rule and exception test | the planted "rule + exception in the next paragraph" (A-MFA 4.1) must share a chunk at default settings; the test names the boundary when it doesn't | build project stage 1 test 3 |
| Halved-size experiment | `raglab ingest --chunk-size 600`: the inventory diff and which planted features break are recorded in the ledger | build project "prove it" |
| OCR | Tesseract through `pytesseract`. Installed with Homebrew on your Mac (I'll ask first) and with apt in CI (pinned package version). The test checks the scanned page against its ground truth within a stated character error rate (CER ≤ 2%, set from the first measured run) | build project stage 1 test 1 |
| PDF | `pypdf` text extraction per page, with the v2 table read as rows (the table-only rule must survive) | the planted table-only rule |
| Runtime dependencies | `pyyaml`, `pypdf`, `pytesseract` move to runtime dependencies (they are parsers, not model SDKs, so they're allowed outside adapters) | |

## Acceptance criteria

| # | Criterion | Evidence |
|---|---|---|
| AC1 | `docs/TEST-PLAN.md` part 2 follows the how-to 17 template: the pipeline drawn as arrows, one named check per arrow (both load and retrieve flows), filled in for the stages so far and marked "from S2" etc. for later ones | `test_test_plan.py` checks the section and that each named check maps to a test id or a later stage |
| AC2 | Every register document parses: page text for Markdown sections, PDF pages, HTML and the PNG; the extracted text contains every verbatim value the answer key cites for that document (the table-only rule included) | `test_ingest_formats.py` (marker `ingestion`; the OCR case marker `ocr`) |
| AC3 | OCR of the scanned page is within the stated CER of its ground truth, and the rule that lives only there is extracted | `test_ocr.py` (marker `ocr`); the CER measured and recorded |
| AC4 | Every chunk carries doc id, version, status, tenant, section, print page where it applies, and licence; no chunk lacks a tenant (fails closed); chunk ids are deterministic | `test_chunk_metadata.py` |
| AC5 | The rule-and-exception pair shares a chunk at default settings; the test names the boundary when it doesn't | `test_chunk_boundaries.py`; **break:** at a budget that splits them, the test fails and names the boundary |
| AC6 | An inventory snapshot (ids, doc, section, length, first words) is committed; any chunker change shows up as a diff; the halved-size run's diff and broken features are recorded in the ledger | `test_inventory_snapshot.py`; ledger section |
| AC7 | Architecture holds: `core` is stdlib only, parsers live in `ingest/`, no vendor SDK outside adapters, and deptry is clean with the new runtime dependencies | `make check` |
| AC8 | [CI] pr-fast installs Tesseract (pinned) and runs the `ingestion` and `ocr` tests; it stays green with no network calls in tests | PR checks |
| AC9 | Diagram and README mark S1b done, plus a CHANGELOG line and a ledger with per-criterion evidence | tests and CI |

## How it will run (orchestrated workflow)

1. **Build:** the developer (Opus 5.5) builds the core types, parsers, chunker, pipeline, CLI,
   snapshot and tests, runs the halved-size experiment and commits.
2. **Verify:** two Fable judges in clones.
   - **Criteria and breaks:** re-runs every acceptance criterion, breaks the boundary test, the
     snapshot and the tenant field, and runs the OCR check.
   - **Adversarial ingestion:** odd inputs (empty sections, a table across a page break, CRLF,
     front matter edge cases), determinism across runs, nothing silently dropped (every register
     document yields at least one chunk), and no attack file reaching the default inventory.
3. **Confirm:** each defect is reproduced independently before it counts.
4. **Fix:** the developer fixes the confirmed defects (one round). Product choices come to you as a
   short list.

## Before the workflow starts

`brew install tesseract` on your Mac, with your go. CI installs it itself.

## Risks

- OCR differs across Tesseract versions: pin the CI package, use a CER tolerance (not exact
  text), and record the version in the inventory.
- pypdf can extract tables out of reading order: the table-only test catches it, and the fix is to
  read the table as rows.
- The snapshot changes legitimately in later stages: it is regenerated on purpose by a make
  target, and the diff is reviewed in the PR.

## Approval

Your answer, verbatim (2026-10-06): "Approve and install".
