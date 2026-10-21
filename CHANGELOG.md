# Changelog

One line per change, newest first, grouped by release. Each pull request adds its line
(checked in CI; Dependabot is exempt).

## Unreleased

- Dependency updates of 2026-10-21, replacing Dependabot's #19, #20 and #21: fastembed 0.9.0,
  numpy 2.5.4, ruff 0.17.0, `uv_build>=0.13.1` (both projects), actions/setup-node 7.1.0, and the
  DeepEval tool re-locked with them. pypdf stays at 6.19.0 (decision: "Keep 6.19.0, skip its 4
  advisories (Recommended)"): 6.20.0 to 6.21.1 change plain text extraction and fail the corpus
  build's checks, so its advisories (five, one published after the decision) join `make audit`'s
  skips with the reason in the Makefile, under the same review date, and Dependabot ignores those
  versions. Seven more Pillow 12.3.0 advisories of the same kinds join the Pillow exception.
- S5, judged metrics on local models (plan `docs/plans/2026-10-20-s5-judged-metrics.md`, ledger
  beside it): `docs/CRITERIA.md` and the canary set, signed off on 2026-10-20 and again on
  2026-10-21; the `Judge` port and judge-v2 (judge-v1 kept for the first judged record) on a
  local Ministral 3 14B judge, pinned by tag and digest, its session checking its own model and
  running on AC power only (AC22); the canaries as a hard stop; the judged baseline of the dev
  slice and the position test published, reported and not gated until S6; the tokens of every
  call by role, a dated price table, `raglab cost` and ADR-002, accepted as local only for now
  (D6: the hosted half deferred); DeepEval 4.3.1 fenced in `tools/deepeval-check` and checked
  live; S5 before S4b (D1).
- uv 0.13.4 in CI and on the maintainer's Mac, and the `uv_build` backend at 0.13 (decision: "One
  uv PR after S5's sessions (Recommended)"): uv before 0.13.4 trusts a root CA whose intermediate
  keys were compromised (GHSA-hq85-5cpj-mr62), the root certifi dropped in the line below. The
  lock is unchanged (`uv lock --check` passes under 0.13.4). Replaces Dependabot's #14 and #2.
- `make audit` green again after the advisories of 2026-10-20 (decision: "Dependency PR, Pillow
  exception (Recommended)"): certifi 2026.10.19 (GHSA-6q48-6c7w-9gw2, revoked intermediates of
  a bundled root); Pillow 12.3.0's nine advisories skipped, with the reason in the Makefile, until
  Pillow 13 can be used (fastembed 0.9.0 still requires pillow<13); review by 2026-11-21, enforced
  by `tests/unit/test_audit_exceptions.py`.

## v0.1.0 (2026-10-20)

- Release v0.1.0, the lab release after S4 (decision D4: "Release after S4 (Recommended)"; plan
  `docs/plans/2026-10-20-v0.1-release.md`):
  - the version is 0.1.0;
  - `make release-local` runs the test slice once, retrieval and one guarded generation session,
    under gate release, and both runs are published;
  - the gitleaks and privacy history scans are run;
  - release notes in `docs/releases/v0.1.0.md` mark each release-gate item as run or not built yet;
  - `runbooks/release.md` is the lab release runbook;
  - the S4 ledger gains the record of its pull request's CI run.
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
  (blind agreement 40 of 40); the user's answer on its sign-off was "Signed off as is". Published,
  all made at 97011a7: the retrieval baseline `20261019T180502Z-retrieval-dense-dev-97011a7`
  (recall@5 0.682) with `20261019T180515Z-retrieval-hybrid-dev-97011a7` and
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
