# Changelog

One line per change, newest first, grouped by release. Each pull request adds its line
(checked in CI; Dependabot is exempt).

## Unreleased

- pr-fast's `check` job gets 20 minutes instead of 15 (the maintainer's decision of 2026-10-25,
  in S7a's pull request): S7a's tests add about 2 minutes on CI, which leaves the job about 13 min
  20 s of 15, and S6's come next. The `perf` and `conventions` jobs keep their limits.
- S7a, attack and guardrails (plan `docs/plans/2026-10-23-s7-attack-guardrails.md`, ledger beside
  it; S7b, the promptfoo red team and Guardrails AI, follows S6): the rule layer behind the
  `Guardrail` port (an input injection detector, a register filter that leaves pages outside the
  register out of the prompt, an instruction scan before indexing, link, secrets and
  personal-details and prompt-leak guards, the citation validator extended to the register), each
  with a fixed reason key; `docs/THREAT-MODEL.md` (OWASP LLM Top 10 2026); the security pack
  `datasets/security/` (deliberate test material, planted values by reference); the deterministic
  attack suite in pr-fast, each attack landing without its defences and stopped by each alone; the
  guard set in the staleness rule, kept current by a zero-event replay (`make replay`); per-layer
  error rates and latency (`make guard-suites`, docs/THRESHOLDS.md); the attack suite's live runs,
  `make attack-local` (suite `attack` in run record v1, defences off and on; publish refuses a
  defences-off run), built and tested on the fake model, not yet run on the local model.
- Three Pillow 12.3.0 advisories published on 2026-10-21 join `make audit`'s skips ahead of
  pip-audit's database, which does not list them yet, so `main` stays green when they reach it:
  image data decoded as P;2L or P;4L, `Image.quantize()` with an empty palette, and the TIFF
  encoder. raglab uses none of the three. The same decision and review date apply.
- S9, observability and performance, brought forward from v0.3 to ship in v0.2 (plan
  `docs/plans/2026-10-23-s9-observability-perf.md`, ledger beside it; docs/OBSERVABILITY.md):
  gen_ai spans for /ask behind a Tracer port, leaving through an allowlist with content off by
  default and nothing a guard removed; `PERF_TEST_MODE` and the content opt-in refused outside
  `RAGLAB_ENV` ci or local; `make perf-smoke` and pr-fast's `perf` job, the k6 smoke against the
  perf stub with the collector and its Langfuse pipeline checked; the median gated at 40 ms, set
  from ten runs on GitHub's runner.
- S4b, golden set v2 (plan `docs/plans/2026-10-23-s4b-golden-set-v2.md`, ledger beside it):
  `datasets/golden.v2.jsonl`, golden set v1.1's 74 lines and 80 new behaviour cases (120 in the mix
  45/24/24/12/15, 33 asked as tenant B, every requirement with a planted feature traced), the
  answer-key additions F-88 to F-98, datasheet v2, a labels judge's 80 of 80, and the
  maintainer's sign-off ("Signed off as is"); `raglab check-dataset` holds each golden file to its
  own version, read from the datasheet's Maintenance row; `scripts/split_golden.py`, the seeded
  split (seed 20261023) with a second pass added after the first draw by the maintainer's answer
  to the labels judge's call C1; `make eval-retrieval`. Republished on v2 at the frozen commit
  `ade9397`: the retrieval baseline (dense, recall@5 0.682, hybrid 0.720 and dense-600 0.659 beside
  it, each question's top 5 as on v1.1) and the consistency baseline
  (`20261024T090351Z-generation-local-ollama-dev-ade9397`, behaviour pass^3 0.418, 33 of 79, four
  repeats at 34, 33, 33 and 33, margin one case). The judged baseline stays on v1.1 until S6
  (D2); R-22 stays a gap for S8 (D3).
- The advisories published on 2026-10-23, so the audit passes on `main` again: filelock 4.0.12 →
  4.2.1 (three advisories, fixed in 4.2.1, taken once its 7-day cooldown had passed; replaces
  Dependabot's #28); and five more join `make audit`'s skips, under the same decisions and review
  date: two for Pillow 12.3.0 (a crafted FlashPix file, and an image exported to Arrow with
  `PILLOW_ALIGNMENT` above 1, which raglab never does) and three for pypdf 6.19.0 (crafted PDFs with
  long runtimes, fixed only in 6.21.2, which stays untried until its 7-day cooldown ends on
  2026-10-28).
- answer-v2, the prompt fix for abstention (plan `docs/plans/2026-10-21-answer-v2.md`, ledger
  beside it), measured on dev and not adopted (the user's decision, verbatim: "Not adopted, runs
  stay published (Recommended)"): its first run after the sign-off gained four cases on answer-v1's
  baseline with none lost (+0.148, +0.037 to +0.296), but one of its four repeats fell back to
  answer-v1's 14 of 27 with a reply off the schema, so robustness and the reply-format guard, read
  over the five runs, failed. answer-v1 stays the current prompt, now chosen in code
  (`raglab.generate.prompts.CURRENT`), and the consistency baseline; pr-fast now reports a stale
  consistency baseline; answer-v2's module, its five runs and its judged record stay published as
  a measured result.
- S5's AC4 live break (the criteria judge's S5-J5), run on AC power on 2026-10-22 after S5 merged
  and recorded in S5's ledger: with C-05 flipped, the canaries stopped the judge before any judged
  call. S5 ends at 16 criteria met, 6 not applicable by D6, 0 not met.
- The playground on GitHub Pages (`docs/GO-PUBLIC.md` step 9; decision: "Small PR now, in parallel
  (Recommended)"): `.github/workflows/pages.yml` publishes `playground/` with `runs/published/`
  beside it, laid out by `scripts/serve_playground.py --out` as `make playground` serves it, on a
  push to `main` or by hand, never on a pull request; only the deploy job holds `pages: write` and
  `id-token: write`, and every action is pinned by SHA (`tests/unit/test_pages.py`). A generation
  or judged run no longer stops the page on an error; per-question rows stay retrieval-only. Live
  at https://willcoliveira.github.io/ai-testing-rag-lab/ once Settings → Pages → Source is
  "GitHub Actions".
- Dependency updates of 2026-10-21, replacing Dependabot's #19, #20 and #21: fastembed 0.9.0,
  numpy 2.5.4, ruff 0.17.0, `uv_build>=0.13.1` (both projects), actions/setup-node 7.1.0, and the
  DeepEval tool re-locked with them. pypdf stays at 6.19.0 (decision: "Keep 6.19.0, skip its 4
  advisories (Recommended)"): 6.20.0 to 6.21.1 change plain text extraction and fail the corpus
  build's checks, so its advisories (eight, four published after the decision) join `make audit`'s
  skips with the reason in the Makefile, under the same review date, and Dependabot ignores those
  versions. Twenty-seven more Pillow 12.3.0 advisories of the same kinds (seven on 2026-10-21,
  twenty on 2026-10-22) join the Pillow exception.
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
