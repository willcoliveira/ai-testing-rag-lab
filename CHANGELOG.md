# Changelog

One line per change, newest first, grouped by release. Each pull request adds its line
(checked in CI; Dependabot is exempt).

## Unreleased (v0.1)

- S3 (in progress): generation: ChatModel and Guardrail ports and a structured Answer (text, cited
  ids, decision label, conflict, status); prompt answer-v1 with a reviewed snapshot and fingerprint;
  input limits, the tenant guard and the citation validator (docs/GUARDRAILS.md); FakeChat, built
  only by the factory on provider fake; the httpx OpenAI-compatible adapter (loopback only, tag and
  digest pinned); the generation suite (no-judge checks, the abstention oracle, Wilson intervals,
  pass^3) in run record v1, extended additively; the API (/healthz, /version, /ask) and page,
  `raglab ask`, `serve` and `ollama`; an API smoke in pr-fast; the fake-model container and its
  ZAP baseline; the local model on Ollama for one session only, with usage guards
  (docs/LOCAL-MODEL.md); one local live run on nemotron-3.5-lightning, not yet published (S3
  ledger).
- docs/ONBOARDING.md: what a new team member can run, ten break-it-on-purpose exercises, the
  concepts built so far with their files and tests, and what is not testable yet; a test checks that
  every path, make target and raglab command it names exists.
- S2: retrieval without a judge: Embedder, VectorStore and Retriever ports; the local
  bge-small ONNX embedder from pinned, hash-checked files (`make model`, cached by revision in
  pr-fast); an in-memory store and dense, BM25 and hybrid (reciprocal rank fusion) retrievers,
  each with a tenant filter that fails closed; hit@k, MRR, recall@k, paired differences and a
  seeded bootstrap; run record v1 (schema, writer, validator) and `raglab eval`, `compare`,
  `publish` and `gate`; three configs; a table caption kept with its table in the chunker; the
  static playground (`make playground`, Pages at go-public); docs/THRESHOLDS.md; golden set v1
  (34 labelled retrieval questions, dev and test, with a datasheet); the dense dev baseline and the
  hybrid and chunk-600 dev runs in `runs/published/`; and the recall@5 no-regression gate in
  pr-fast and `make check` (`make gate`).
- S1b: ingestion and chunking: the register reader, Markdown, PDF (tables read as rows), HTML and
  OCR (Tesseract) parsers, the section-aware chunker (1,200 characters, one paragraph of overlap,
  deterministic ids), `raglab ingest` and the committed inventory snapshot
  (`make inventory-snapshot`), a separate attack-fixture loader for S7, docs/TEST-PLAN.md part 2
  (one named check per pipeline arrow), one test module per criterion, a parser-library
  architecture rule, a no-network guard for tests, and a pinned Tesseract in pr-fast.
- S1a: requirements (docs/TEST-PLAN.md part 1) and the fictional Halvenroot and Mirrowfen policy
  corpus (21 documents adapted from strongdm/comply, NIST and NCSC excerpts, and three labelled
  attack files), with the planted-feature answer key, the machine-readable register
  (corpus/register.yaml), SOURCES.md and licence notes, a deterministic build of the PDF, HTML
  export and scanned page, a corpus-only privacy allowlist, and tests for the plan, the key, the
  sources, the build and the allowlist scope.
- S0: repo skeleton with `make check` and the pr-fast workflow (format, lint, types, deptry,
  vulture, pip-audit, bandit, semgrep, zizmor, gitleaks, privacy, architecture rules, offline
  tests), Conventional Commits and semantic branch checks, the changelog check, Dependabot, the
  architecture progress map and the committed plans. After the judge's review: the pre-commit
  privacy check reads the staged index, and the workflow, conventions, architecture and changelog
  checks close the bypasses the judges found over four rounds (staged index, history and
  pre-push scans, commit identities, tag messages, copies of the real list). After the second review: the staged check never writes to
  the repo (safe in linked worktrees), refuses a staged real list and covers force-added and
  quoted file names, and three false positives are gone. After the third review: the privacy
  check refuses a committed real list in CI too, checks the example list, the checker and
  `uv.lock` with the real list, reads a symlink as its link text and a commit message as prose; a
  history scan checks every commit in a pull request, before each push (a new pre-push hook) and
  before going public; the conventions, architecture and changelog checks close the rest.
