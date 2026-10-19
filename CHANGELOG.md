# Changelog

One line per change, newest first, grouped by release. Each pull request adds its line
(checked in CI; Dependabot is exempt).

## Unreleased (v0.1)

- S4: the golden set and the consistency gate. Label groups (`any_of`: sections that state the same
  rule are one thing to find); `raglab check-dataset`, a hard stop of ten rules before every run,
  in `make check` and as its own pr-fast step; the behaviour cases in the generation suite (the
  decision label from the structured field, abstention as its own check with D-03's quote
  allowance, the conflict field, canaries both ways, must-not-contain), with run record v1 extended
  additively; the consistency gate (Q-05, `make gate-local`, its margin to be set from runs); a
  paired comparison of generation runs; the test split held out of every run but nightly and
  release (`make nightly-local`); D3: the team contacts allowed in published runs, the plain attack
  phrases blocking attack runs only. Golden set v1.1 (40 behaviour cases, seven regrouped retrieval
  questions, the answer-key additions F-86 and F-87, datasheet v1.1), reviewed by the labels judge
  (blind agreement 40 of 40) and signed off by the user. Published, all made at 97011a7: the
  retrieval baseline `20261019T180502Z-retrieval-dense-dev-97011a7` (recall@5 0.682) with
  `20261019T180515Z-retrieval-hybrid-dev-97011a7` and
  `20261019T180529Z-retrieval-dense-600-dev-97011a7`; the local generation baseline
  `20261019T172035Z-generation-local-ollama-dev-97011a7` (behaviour pass^3 0.519, 14 of 27) with
  the repeats `20261019T172524Z-generation-local-ollama-dev-97011a7`,
  `20261019T173030Z-generation-local-ollama-dev-97011a7`,
  `20261019T173524Z-generation-local-ollama-dev-97011a7` and
  `20261019T174018Z-generation-local-ollama-dev-97011a7`; the consistency margin is one case.
- S3h, the host spike, moves from P1 to the start of P3, before S10 (the user's decision of
  2026-10-18): the main plan, the phase map in ARCHITECTURE and the README, and ONBOARDING say so;
  the S3h draft plan is committed as deferred, with the answers already given.
- S3 follow-up (judge S3-J12, S3-J13): Ctrl-C ends `raglab ollama session`, after the stop and
  the postcheck, with one line on stderr and exit 130 instead of a traceback; `make api-smoke`
  fails unless the server stops gracefully on SIGTERM (exit -15), so an abort at exit (-6) no
  longer passes unseen.
- The repo is public (2026-10-18, after S3): docs/GO-PUBLIC.md records steps 1 to 7 as done
  (history and privacy scans, the flip, secret scanning, vulnerability reporting, Dependabot,
  branch protection on `main`); Environments (S5) and Pages are still to do.
- S3: generation: ChatModel and Guardrail ports and a structured Answer (text, cited
  ids, decision label, conflict, status); prompt answer-v1 with a reviewed snapshot and fingerprint;
  input limits, the tenant guard and the citation validator (docs/GUARDRAILS.md); FakeChat, built
  only by the factory on provider fake; the httpx OpenAI-compatible adapter (loopback only, tag and
  digest pinned); the generation suite (no-judge checks, the abstention oracle, Wilson intervals,
  pass^3) in run record v1, extended additively; the API (/healthz, /version, /ask) and page,
  `raglab ask`, `serve` and `ollama`; an API smoke in pr-fast; the fake-model container and its
  ZAP baseline; the local model on Ollama for one session only, with usage guards
  (docs/LOCAL-MODEL.md); the planted exception ids allowed in published runs only, and publish
  refusing the answer key's planted secrets; one local live run on nemotron-3.5-lightning at the
  model card's sampling settings, published in `runs/published/`.
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
