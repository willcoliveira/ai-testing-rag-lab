---
stage: S5
nodes: [S5]
---

# S5 ledger: judged metrics on local models, token measurement and the provider decision

Plan: [2026-10-20-s5-judged-metrics.md](2026-10-20-s5-judged-metrics.md).

This ledger covers **phase 1, the offline build, up to the user's sign-off of docs/CRITERIA.md and
the canary set**. Nothing has been judged: no golden answer has met the judge, no judged record
exists, and no run was published. The later phases (the judge sessions, ADR-002 and D6, the
hosted half) add their sections below.

## Approval and decisions

The message that opened S5 planning (2026-10-20), verbatim (quoted in the plan): "we can continue".

The user's answers (2026-10-20), verbatim (quoted in the plan's Approval):

| Decision | Answer | What was done |
|---|---|---|
| D1 S5 before S4b? | "S5 now, S4b after (Recommended)" | S5 runs on golden set v1.1. The main plan's phase map and its README and ARCHITECTURE copies put S5 before S4b, with a decision note quoting the question and the answer, as pull request #10 did for S3h (`57f6fad`) |
| D2 answer-v2 | "After S5, own PR (Recommended)" | S5 judges answer-v1; no prompt change here. The main plan's note names answer-v2 between S5 and S4b |
| D3 The judge model | "Ministral 3 14B (Recommended)" | `config/judge-local.toml` pins `ministral-3:14b-instruct-2512-q4_K_M` by tag and digest (below) |
| D4 DeepEval or our own judge | "Own judge; DeepEval fenced (Recommended)" | The own judge decides every criterion (`raglab.judge`); DeepEval 4.3.1 lives in `tools/deepeval-check` only (`956d9e4`) |
| D5 The hosted half | "One PR" | The hosted criteria AC16 to AC21 belong to this stage, after the sign-up; D6 is asked mid-stage, once ADR-002's costs exist. Nothing hosted is built yet |
| The download | "You run it (Recommended)" | The orchestrator ran the pull (below); the developer pinned the digest |
| D7 This plan | "Approve and start (Recommended)" | The build started on `feat/s5-judged-metrics` at `22569e0` |

**The sign-off of docs/CRITERIA.md and the canary set (2026-10-20).** At 20:33 WEST, through the
orchestrator's question prompt, the user chose, verbatim: "Sign off with the clause (Recommended)".
No note was typed. The user reviewed the drafts at `526f4cd` on a review page: docs/CRITERIA.md
sha256 `981f63c2ebebe0c6708613a76405282cbebbd3d4065a3a44fe32ae485f1fc3e3`, the canary set sha256
`4ca54c3ced557118f26306543164dc01c7509d1866e9e77f6cd4f2d3284b328f` (checked with `shasum -a 256`
before the change: both matched).

The clause is the one change the user took: `grounded`'s pass rule gains "; an answer that states
no value or rule passes", the words `cites_support` already uses, in judge-v1's rules and in
CRITERIA.md's "Passes when" line. The orchestrator's reason: C-03 (the honest twin) and every
honest abstention on dev otherwise rest on the judge reading `grounded` as met when nothing is
stated, and on a canary, unable_to_verify is on neither side. Nothing else in the rules changed; no
canary changed side, and the canary file did not change. CRITERIA.md's status line now says it is
signed off, with the quote.

**Frozen, in the commit that applies the clause and the freeze:** docs/CRITERIA.md sha256
`7e3a522335c7009dded6b6048a24d90365b7eec5e488ec258ea0562cb9a898da`; the canary set sha256
`4ca54c3ced557118f26306543164dc01c7509d1866e9e77f6cd4f2d3284b328f` (unchanged); judge-v1's
fingerprint `10d96ed31467c42c13e2b037956fef94e9a011b47156ffb88d095a40c3955368` (the draft's,
`481783ef736170802f28d82fc8e2055d26b12424b552acaab8ffee2fa563d575`, was used by no record), with
its reviewed snapshot. From that commit on, neither file changes: if a run shows a canary or a rule
is wrong, the stage stops and reports, and a change needs a new sign-off. CRITERIA.md's "Checked at
DeepEval 4.3.1" section therefore stays as signed off ("Not run yet"); DeepEval's results go to
docs/COMPATIBILITY.md and this ledger.

## The judge model, pinned

The orchestrator pulled the judge on 2026-10-20 at 17:00, in one guarded session (`make
ollama-up`, `ollama pull ministral-3:14b-instruct-2512-q4_K_M`, `make ollama-down`; the
postcheck passed). The server's `/api/tags` then reported, as the orchestrator relayed it: tag
`ministral-3:14b-instruct-2512-q4_K_M`; digest
`4760c35aeb9d9e9c6174c2492562c0b999e80a222804fd96b1915ab72bbcdcf7` (the tags page's prefix
`4760c35aeb9d` matches); size 9082537546 bytes; format gguf, Q4_K_M, family mistral3, 13.9B
parameters, runner ggml, context length 262144. `config/judge-local.toml` pins the tag and the
digest and records the rest in its comments (`174ace2`). No model was pulled or deleted by the
developer.

**Where the session reads the digest.** On this Mac, each model's local manifest (under
`~/.ollama/models/manifests/registry.ollama.ai/library/`) lists, as its last layer, an entry of
media type `application/vnd.docker.distribution.manifest.v2+json` whose digest is the one
`/api/tags` reports: `sha256:4760c35aeb9d...bcdcf7` for the judge, `sha256:d1e17d7dabac...7397be`
for the generator (read 2026-10-20). The manifest files' own sha256 are other values
(`88e91efab87a...` and `29ca9916f0cd...`). So the session's preflight checks the pinned digest from
that layer before the server starts, and refuses a manifest without it (fails closed). The
manifest's layers and config add up to 9082538404 bytes for the judge: `/api/tags`' 9082537546
plus the 858-byte registry-manifest layer, which the memory guard counts too.

## What was built (developer, 2026-10-20)

| Part | Where |
|---|---|
| The judge config and its session (AC3) | `config/judge-local.toml` (`suite = "judged"`: `[judge]`, `[judging]`, `[ollama]`); `raglab.evals.config.load_judge`; `raglab.runtime.ollama.session_for` serves the model the config pins, a generation config's generator or a judge config's judge, and `Session.digest_problem` checks the pinned digest in the preflight; `raglab ollama ... --config` reads either kind; `make judge-contract` |
| The judge (AC2) | `raglab.core`: the `Judge` port, `Passage`, `JudgeItem`, `Verdict`, `CRITERIA`, `VERDICTS`; `raglab.judge.prompts.judge_v1` (VERSION, SYSTEM, each criterion's inputs and rules, frames its inputs cannot close, the verdict schema, the strict parser, the quote check, the fingerprint); `raglab.judge.llm.LLMJudge` over the `ChatModel` port; `raglab.judge.build.judge_from_config`; `tests/snapshots/judge-v1.txt` |
| CRITERIA.md and the canary set (AC1, drafts) | `docs/CRITERIA.md` (seven criteria, what each answer is judged on, the reference answer rule, how a criterion is reported, the canary table, "Checked at DeepEval 4.3.1" waiting); `datasets/canaries.judge.jsonl` (19 items) |
| The canaries (AC4) | `raglab.judge.canaries` (the strict loader, corpus passages by chunk id, the runner, the hard stop naming every item off its side, the results a manifest carries); `raglab canaries --config` |
| The judged run and record (AC5 to AC8) | `raglab.evals.judged` (the source checked, passages rebuilt, the canaries first, every answer on its criteria, then the repeatability and order passes); `raglab.evals.judged_record` (applicability, shown passages, results, report, the checks against the source and against each verdict's reply); `raglab.evals.record` and `schemas/run-record.v1.json` extended additively (suite `judged`); `raglab.evals.publish` (a judged run needs its source published, and is refused as stale under another CRITERIA.md or canary set); `raglab judge --run --config`; `make judge-local RUN=` |
| The position test (AC9) | `raglab.evals.position` (cases, answering chunk, fillers, the fit to the budget, the run) and `raglab.evals.position_record` (the code checks, the results by position, the checks of the lines); the generation record's `position` kind; `config/position-local.toml`; `raglab position --config`; `make position-local` |
| DeepEval (AC10, AC11 offline) | `tools/deepeval-check` (its own `pyproject.toml` and `uv.lock`, `deepeval==4.3.1`, raglab by path): `guard` (the opt-out, the loopback-only socket guard), `llm` (`RaglabJudgeLLM`, a `DeepEvalBaseLLM` over raglab's adapter), `checks` (the four checks and the direction report), `__main__`, offline tests; `scripts/check_architecture.py` rule 6; `make audit` over its lock; `.github/dependabot.yml`; `make deepeval-test`, `make deepeval-check JUDGED=` |
| Cost (AC12) | `config/prices.toml`, `config/cost-assumptions.toml`, `raglab.evals.cost`, `raglab cost --judged`; `make cost JUDGED=` |
| Docs (AC14, the parts that need no run) | TEST-PLAN (R5, Q-01, Q-02, section 10, the Test column), THRESHOLDS (the judged section, the cost formula), COMPATIBILITY (the judge's row, DeepEval's offline checks), LOCAL-MODEL, ONBOARDING, ARCHITECTURE and README (S5 `wip`, S5 before S4b), the main plan (D1), CHANGELOG |

The file and target names follow the plan's suggestions, with these additions: `raglab canaries`
(a judge session that runs no judged run, DeepEval's, runs the canaries first with it),
`raglab.evals.position_record` (the record side of the position test, kept apart from the run so
`raglab.evals.record` imports no run code), `config/cost-assumptions.toml` (the runs a month and the
priced options, apart from the prices), and `make deepeval-test`.

## Evidence per criterion (developer, 2026-10-20, phase 1, macOS arm64)

Each break was made on a committed file with `PYTHONDONTWRITEBYTECODE=1`, run, and restored with
`git checkout -- <file>`; the same check was green again after the restore, and `git status
--short` was empty. The break spec is a scratch file outside the repository; each edit is described
below.

| AC | Status after phase 1 | Evidence | Break (restored from git) |
|---|---|---|---|
| AC1 | signed off on 2026-10-20 with the clause (above); the date check against the first judged manifest waits for it | `docs/CRITERIA.md` and `datasets/canaries.judge.jsonl` (`78d32e0`). `tests/unit/test_criteria.py`, 9 tests: every criterion has every field (applies to, the judge sees, passes, fails, requirements, grader, status); its pass and fail rules are judge-v1's words exactly; what the judge sees is judge-v1's inputs; every requirement named is one of TEST-PLAN's; every criterion is graded by judge-v1 and reported; the canary table is the canary file; every canary names a criterion and a side, and every criterion has an item on each side; the metric canary, its honest twin and the two injection canaries are there; every corpus passage a canary names is in the committed inventory. A judged manifest carries the sha256 of both files, and publish refuses a judged run made under another version of either (`tests/judge/test_judged_run.py`). The date check against the first judged manifest waits for that manifest | (1) context_sufficient's "Fails when" line removed from docs/CRITERIA.md: "2 failed, 7 passed" ("context_sufficient has no ['Fails when']"), restored "9 passed". (2) publish's stale check disabled (`if False:` in `publish.judged_problems`): the edited-CRITERIA and flipped-side tests "2 failed" ("DID NOT RAISE PublishError"), restored "2 passed". The plan's live form of this break (a published judged record) waits for one |
| AC2 | met offline | `tests/judge/test_judge_prompt.py` (18 tests: the snapshot of all seven criteria's prompts; the reviewed fingerprint, `10d96ed31467...` since the sign-off (the draft's was `481783ef7361...`); every criterion has rules; a criterion is shown exactly the inputs it sees, and an item showing more or less is refused; no passages is said plainly; no input can close its frame or open another, in any letter case; a passage attribute cannot break out of its tag; no developer comments; the schema puts the evidence before the verdict) and `tests/judge/test_verdict_parser.py` (22 tests: a reply in the schema parses; thirteen replies off the schema are refused, an extra field, a missing one, a verdict outside the enum, a code fence, text after the JSON, a repeated field among them; an off-schema reply is unable_to_verify with status invalid_output and the reply kept; no reply is unavailable; the quote is checked against the answer and reported; passage ids not shown are reported; a verdict's seed, schema and system prompt; an off-schema or unavailable verdict is never a pass). `make architecture`: 0 violations (`raglab.core` imports the standard library only) | (1) one word of SYSTEM changed ("given" to "shown"): "2 failed, 16 passed" (snapshot and fingerprint), restored "18 passed". (2) the parser made to accept extra fields (`not FIELDS <= frozenset(data)`): "2 failed, 20 passed", restored "22 passed". (3) `as_data` made a no-op: "5 failed, 13 passed" (the four frames and the attribute), restored "18 passed" |
| AC3 | met offline; the live contract test passed (below) | `tests/unit/test_ollama_session.py` additions: a judge config's session checks the judge, never the generator (with only the generator pulled it refuses, naming the judge); it starts with its pinned model and says its size and digest; a replaced digest refuses before the server starts, for the judge and for the generator; a manifest without a registry digest refuses; an unpinned generator digest is not checked and the session says so; the CLI builds the judge's session; the make targets run one model per session. `tests/unit/test_eval_config.py` additions: the committed judge config (tag, digest, temperature 0, the generator's session limits) and eight wrong judge configs refused. `tests/contract/test_judge_contract.py`: the stub contract in pr-fast (the config's temperature, cap, seed and schema sent; a reply off the schema is invalid_output with its tokens; an HTTP error is unavailable; another digest refuses to start); the live test in the session. COMPATIBILITY.md: "Tested against ministral-3:14b-instruct-2512-q4_K_M@4760c35aeb9d9e9c6174c2492562c0b999e80a222804fd96b1915ab72bbcdcf7 on Ollama 0.40.6 on 2026-10-20" | (1) the preflight given the generator's model for a judge config (in `session_for`): "4 failed, 6 passed", restored "10 passed". (2) the digest replaced in `config/judge-local.toml` (`4760...` to `5760...`): the judge tests "5 failed, 11 passed"; and `make judge-contract` against this Mac's real manifest: "ollama session: the session may not start: - ministral-3:14b-instruct-2512-q4_K_M on this Mac has digest sha256:4760c35aeb9d9e9c6174c2492562c0b999e80a222804fd96b1915ab72bbcdcf7, not the pinned sha256:5760c35aeb9d9e9c6174c2492562c0b999e80a222804fd96b1915ab72bbcdcf7: a session never serves other weights than its config pins", `make` error 1, no server started; restored "16 passed", and `make ollama-status` showed no pid, the port closed, no process, nothing loaded |
| AC4 | met offline; the live run and the live flipped canary wait for phase 2 | `tests/judge/test_canaries.py` (17 tests: a judge with every committed canary on its side passes them; one canary off its side stops the judge, naming it, whether the verdict is the other side, unable_to_verify, off the schema or missing; every item off its side is named, not only the first; the results name each item, its side and its verdict, never a passage's text; corpus passages are read from the corpus and a written one is kept; a wrong canary is refused, naming the line). `tests/judge/test_judged_run.py`: the canaries run before every answer, a miss stops the run before any judged call (the chat saw the canary calls only), and the CLI writes no record then | The stop removed (`off_side(results)[:0]`): "6 failed, 33 passed" (the four stop cases, the run and the CLI), restored "39 passed" |
| AC5 | met offline; the published judged record waits for phase 2 | `tests/judge/test_judged_run.py` (22 tests): a judged run writes a valid record tied to its source (case-trials in the source's order, the answer's sha256, the copied retrieval, the source's chunker, embedder, retriever, corpus and dataset); each answer takes its criteria, context_sufficient once per case; a cited answer is shown its cited passages; a withheld trial is not judged but its retrieval is; the run stops at its cap and is partial; a resealed line whose answer sha256 differs, edited results, a flipped verdict, dropped completion tokens, other shown passages, a missing line, a changed source, a forged quote check and a canary off its side are refused; publish requires the source published and refuses a stale run; judged runs are held to their source's planted strings. The committed-runs test validates every published record unchanged | (1) the answer-sha256 tie skipped in `line_problems`: "1 failed, 21 passed", restored "22 passed". (2) the judged results trusted as recorded instead of recomputed (in `record.expected_results`): "2 failed, 20 passed", restored "22 passed" |
| AC6 | the code met offline; the published records wait for phase 2 | Every call's tokens: the generator's per case-trial from the source lines (`source_tokens`, `source_called`), the judge's per verdict, the checks' and the canaries', totalled by role in `results.judged.tokens` (calls, prompt, completion, unreported); with the stub's usage (`test_every_calls_tokens_are_totalled_by_role`: generator 14 calls, 1400 and 280; the judge's 300 and 40 a call) and without (FakeChat: every judge call unreported). The DeepEval wrapper records every call's tokens (`RaglabJudgeLLM.tokens`); the position run is a generation record, whose tokens S3 records | The judge's completion tokens dropped from the totals (`"completion": 0` in `judged_record._role`): "3 failed, 34 passed", restored "37 passed" |
| AC7 | the code met offline; the judged run waits for the sign-off | `raglab judge`, `make judge-local RUN=`; THRESHOLDS.md marks every judged criterion reported with the reason (`57f6fad`) | The verdict no longer read again from its reply (only the quote, ids and reason compared): the flipped-verdict test "1 failed, 21 passed", restored "22 passed". The plan's break on the published record waits for it |
| AC8 | the code met offline | The repeatability pass (trial 1 of every behaviour case judged again) and the order pass (grounded on trial 1 of every case with the passages reversed), both after every answer is judged, both in the record and validated (`tests/judge/test_order_check.py`, 4 tests) | The order check given the passages in their original order (`reverse=False` in `judged.run`): "2 failed, 2 passed", restored "4 passed" |
| AC9 | the code met offline | `tests/generation/test_position_contexts.py` (20 tests): first, middle (n // 2) and last; the fillers are the tenant's other chunks in rank order, never a labelled section or a group member, nor another tenant's or a shared chunk; the fit to the budget; the measured characters per token are the fewest; a value is stated as the answer key writes it or by its numbers and units (11 cases); the committed config names the ten cases, derived from the golden file; a position run writes a valid generation record; a moved answering chunk, a labelled filler and forged checks are refused; the judge's `correct` runs on a position run | (1) the answering chunk put first at every position (`index = 0` in `place`): "3 failed, 17 passed", restored "20 passed". (2) a group member allowed as filler (only plain labels excluded in `fillers`): "1 failed, 19 passed", restored "20 passed" |
| AC10 | met offline; needs CI for `make audit` on the runner | `tools/deepeval-check` locks `deepeval==4.3.1` (94 packages resolved); the main environment never installs it (`uv sync --locked` unchanged, the main `uv.lock` holds no deepeval, `find_spec("deepeval")` is None and no `deepeval` pytest plugin is registered: `test_the_main_environment_never_installs_deepeval`); rule 6 forbids a deepeval import anywhere under `src/` (`test_deepeval_is_imported_nowhere_in_the_package_adapters_included`, 12 cases); `make audit` exports its 92 pinned requirements with their hashes and audits them without installing ("No known vulnerabilities found"); deptry leaves `tools/` to its own lock; Dependabot watches it, a DeepEval bump in a PR of its own. `make deepeval-test`: "8 passed" (the opt-out set before the first DeepEval import, recorded by an import hook; the guard lets nothing but the loopback Ollama port through; the custom-LLM API returns the schema's instance and records tokens; a whole FaithfulnessMetric in mode llm through the wrapper against a stub, with no connection attempted; the direction report; the canary reading) | (1) `import deepeval` added to `src/raglab/adapters/openai_compat.py`: `make architecture` "1 architecture violations" ("src/raglab/adapters/openai_compat.py:28: deepeval is fenced in tools/deepeval-check and imported nowhere in raglab, adapters included"), restored "0 architecture violations". (2) The opt-out unset with the guard on (a probe outside the repository: DeepEval imported and a FaithfulnessMetric run against a stub judge, the guard installed before the import and kept until the interpreter exits): no attempt during the import or the metric, then at exit "[PostHog] error uploading: HTTPSConnectionPool(host='us.i.posthog.com', port=443)": 12 lookups of `us.i.posthog.com:443`, every one caught. With the opt-out set to 1 before the import: no attempt at all, exit included |
| AC11 | offline parts met; the live checks wait for phase 2 | The checks are code (`tools/deepeval-check/src/deepeval_check/checks.py`): the custom-LLM API, the metric canary (C-01 and C-03 with penalize_ambiguous_claims off and on), the hallucination direction (G-01's labelled passage, a consistent and a contradicting output, the page's sentence and its read date), the cross-check against the own judge's grounded on trial 1 of the dev answer cases; every metric in mode llm. Offline: `test_the_direction_report_names_the_output_that_scored_higher` (3 cases) and `test_the_canary_reading_follows_the_invented_answers_verdict` | The direction report's scores swapped (`x, c = ...`): `make deepeval-test` "2 failed, 6 passed", restored "8 passed" |
| AC12 | the code and the table met offline; the estimate waits for a judged record | `config/prices.toml` (seven rows, each with its source URL and read date 2026-10-20; the table's date is its latest read date); `config/cost-assumptions.toml`; `raglab cost --judged` (`tests/unit/test_cost.py`, 15 tests: a call's cost by hand; the estimate by hand, per call, per case-trial, per run and per month; a prompt above a price's tier refused; the committed table's rows and dates; eight wrong tables refused; the committed options keep the judge's family apart; an option naming no price refused; the CLI on a judged record). THRESHOLDS.md states the formula | (1) the output price applied to prompt tokens (`prompt * price.output` in `call_cost`): "2 failed, 13 passed" (`0.0022 == 0.0012`), restored "15 passed". (2) one price's `source` line removed from `config/prices.toml`: "7 failed, 8 passed" ("price 5 (openai-gpt-5-nano): missing ['source']"), restored "15 passed" |
| AC13 | not started (phase 2: ADR-002 from `raglab cost`'s output, then D6) | | |
| AC14 | the parts that need no run met | TEST-PLAN R5 names its tests (nine) and its gate ("local until keys (`make judge-local`); reported, not gated, until S6 calibrates the judge"), its oracle says what is judged and what stays label-based; section 10's judges line and the metric canary line; Q-01 and Q-02 point at THRESHOLDS.md; the Test column names the judged criteria (reported) for R-01, R-03 to R-07, R-10, R-11, R-14 and R-18 (`tests/unit/test_test_plan.py`, two new tests); LOCAL-MODEL, COMPATIBILITY, ONBOARDING (current as of S5, in progress), ARCHITECTURE and README (S5 `wip`; S5 before S4b), a CHANGELOG line. The measured numbers (THRESHOLDS cost and Q-01, the judge's session time on the judged run, COMPATIBILITY's DeepEval lines) wait for the runs | |
| AC15 | met locally (the tail below); needs CI (pr-fast) | No new runtime dependency in the main project (`pyproject.toml` changed only in tool settings: deptry's `extend_exclude`, ruff's per-file ignores for the tool's tests); `make gate` passes; every published record validates | |
| AC16 to AC21 | not started: after the sign-up (D5), if D6 picks a provider | | |

## The judge's live contract test (AC3), the one live session before the sign-off

One session, through `make judge-contract` only, judging hand-written contract items of a fictional
document, never a golden answer. Before the session `make ollama-status` showed no pid, the port
closed, no process, nothing loaded, 26.1 GiB available.

- **Clock before launch** 17:28:47 WEST; **after the postcheck** 17:29:18 WEST: 31 s for the whole
  session.
- **Preflight:** "model: ministral-3:14b-instruct-2512-q4_K_M at the pinned digest 4760c35aeb9d",
  "memory: 26.3 GiB available; the model needs 8.5 GiB plus a margin of 4 GiB"; then "ollama
  0.40.6 up on http://127.0.0.1:11434".
- **The adapter described** the model, the digest, server 0.40.6, temperature 0.0, max_tokens 512,
  timeout_s 180.0, response_format json_schema, no extra fields.
- **Per call** (from `runs/tmp/judge-contract/20261020T162848Z.jsonl`):

  | Format | Item | Call | Seconds | Status | Verdict | Prompt | Completion |
  |---|---|---|---|---|---|---|---|
  | json_schema | supported | 1 (loads the model) | 6.909 | ok | pass | 495 | 85 |
  | json_schema | supported | 2 | 3.101 | ok | pass | 495 | 85 |
  | json_schema | invented | 3 | 2.948 | ok | fail | 497 | 78 |
  | json_schema | off-topic | 4 | 2.645 | ok | fail | 326 | 61 |
  | none | supported | 1 | 3.457 | invalid_output | unable_to_verify | 495 | 94 |
  | none | invented | 2 | 3.098 | invalid_output | unable_to_verify | 497 | 82 |
  | none | off-topic | 3 | 2.717 | invalid_output | unable_to_verify | 326 | 65 |

  The contract check made one more json_schema call (not logged). Every reply reported its
  tokens and carried no reasoning text; every json_schema reply's quote was found in its answer
  and its passage ids were among those shown.
- **json_schema works on this runner**: four of four logged calls returned a verdict in the
  schema. Without a response format, three of three replies were refused by the strict parser
  ("the reply is not JSON (Expecting value)"), so `config/judge-local.toml` keeps `json_schema`.
- **Seconds per call**: 6.909 s for the call that loads the model, then 2.645 to 3.101 s for the
  warm json_schema calls, on prompts of 326 to 497 tokens. The judged run's prompts are longer
  (five passages), so its seconds per call are measured again by the first judge session of phase
  2, which sets the run's wall-clock cap.
- **The test**: "1 passed, 4 deselected in 29.29s".
- **After**: "unloaded ministral-3:14b-instruct-2512-q4_K_M", "stopped the server (pid 46064)",
  "postcheck passed: port closed, no ollama process, no model loaded"; `make ollama-status`: no
  pid, the port closed, no process, nothing loaded, no service; `pgrep -fl ollama` found nothing.

The only other Ollama contact in phase 1 was AC3's digest break through `make judge-contract`,
whose preflight refused before any server started (above).

## Measured offline for the position test

The characters per token of the answer-v1 prompt, measured on the published consistency baseline
`20261019T172035Z-generation-local-ollama-dev-97011a7` (each of its 147 case-trials' prompt rebuilt
from its question, tenant and retrieved chunk ids, the corpus checked against its sha256, over the
prompt tokens the server reported): min 3.7436, median 4.1238, max 4.3632. `config/position-local.toml`
budgets with the fewest, rounded down to 3.7435, and a prompt budget of 6,144 tokens (the window
of 8,192 less the output cap of 1,024 and a margin of 1,024). With the dense retriever's ranking, the
fillers that fit (an estimate; the run counts them again and records the count on every line, with
each call's reported prompt tokens): G-01 43, G-03 42, G-05 43, G-06 48, G-08 48, G-09 46, G-10 38,
G-11 48, G-12 41 (of 200 or 201 tenant A candidates each), and G-14 17, all of tenant B's 17
candidates (an estimated 2,516 tokens: tenant B's pack is small, so its context is shorter).

## DeepEval, installed in its own environment

- `uv lock --project tools/deepeval-check`: "Resolved 94 packages", `deepeval` 4.3.1 from PyPI;
  `uv sync --project tools/deepeval-check --locked` installed them in `tools/deepeval-check/.venv`
  (gitignored), never in the main environment.
- The installed API, read with `inspect.signature` only (no source read): `DeepEvalBaseLLM`'s
  abstract methods `a_generate`, `generate`, `get_model_name`, `load_model`, and
  `__init__(self, model=None, *args, **kwargs)`; `FaithfulnessMetric(threshold=0.5, model, ...,
  eval_mode=None, ..., async_mode=True, ..., penalize_ambiguous_claims=False, ...)`;
  `HallucinationMetric(threshold=0.5, model, ..., eval_mode=None, ...)`; `measure(test_case)` and
  `is_successful()`. The docs read on 2026-10-20: telemetry goes to PostHog unless
  `DEEPEVAL_TELEMETRY_OPT_OUT=1`; the eval mode is the metric's `eval_mode` argument first, then
  `DEEPEVAL_EVAL_MODE`, then `llm`; a custom model's `generate` returns the schema's instance.
- **One unguarded test run (before `956d9e4`, before the tool's conftest existed).** The tool's
  offline tests were run once without the opt-out in the shell (the run before it had it); pytest
  loaded DeepEval's own pytest plugin at start, before the tests
  set the opt-out, and the socket guard was installed only around the one metric run, where it
  recorded nothing. That run's exit was not guarded. Reproduced afterwards under the guard from the
  very start of the process (the same tests, the opt-out unset in the environment, the plugin
  loading): no attempt at any point, exit included ("pytest exit: 0 attempts so far: []", "ATTEMPTS
  AT EXIT: []"), since the tests set the opt-out before any metric runs. Since then the tool's
  pytest never loads DeepEval's plugin (`-p no:deepeval`), its conftest sets the opt-out at
  collection and guards every test, and `make deepeval-test` sets the opt-out in the environment.

## The price table (AC12)

The developer read the providers' pages again on 2026-10-20: the Anthropic pricing page (its
markdown searched for each row), the Claude Haiku 5.5 overview (model id `claude-haiku-5-5`; "the
same text counts as approximately 30% more tokens than on Claude Haiku 4.5"; "Omit
`temperature`, `top_p`, and `top_k`"), and the OpenAI pricing page (its Standard and Batch rows
copied verbatim). Every price matches the plan's table; one is new: gpt-6-luna's batch prices,
"not read" in the plan, are $0.05 and $0.25 for prompts of 272K tokens or fewer. Only the short
tier of Claude Haiku 5.5 (prompts up to 100,000 tokens) and gpt-6-luna (272K) is listed, with
`max_prompt_tokens`, which makes `raglab cost` refuse a call above it.

## Runs S5 made

None published. Under `runs/tmp` (gitignored): the judge contract log
`runs/tmp/judge-contract/20261020T162848Z.jsonl`, and the exported requirements of the tool's lock
that `make audit` writes. The runs pytest makes are fake or stub-server records in temporary
directories.

## Developer choices (for the review)

1. **A judge config is a suite of its own** (`suite = "judged"`, `[judge]` with the generator's
   keys, `[judging]`, `[ollama]`), and the run to judge is given on the command line, so one config
   judges any finished run.
2. **The digest is checked before the server starts,** from the local manifest's registry layer
   (above), for the generator's sessions too; a manifest without that layer refuses (fails
   closed), and an unpinned generator digest (the lifecycle commands, for a pull) is not checked
   and said.
3. **The criteria's rules live in judge-v1 and in CRITERIA.md, word for word,** held equal by a
   test: the model reads versioned code, and the user signs off the same text.
4. **The verdict schema puts the evidence before the verdict** (quote, passage ids, reason, then
   the verdict), so a schema-constrained reply decides after its evidence.
5. **Canary passages are named by their corpus chunk ids at 1,200/1** and read from the corpus as
   the judged run reads its passages; only C-19's planted instruction is written in the item. No
   corpus text is copied into `datasets/`.
6. **A judged record keeps each judge reply as it came,** and the validator parses it again with
   the record's judge prompt version: a verdict edited apart from its reply is refused, which is
   what makes AC7's "one verdict flipped and resealed" refusable.
7. **`cites_support` is shown the passages the answer cites:** its citations, then its conflict
   field's chunks, in that order, retrieved ones only.
8. **G-09's reference** (S4's labels judge, S4-L5): a case whose features include a contact
   feature (kind `contact (must-not-block)`) gets that feature's reference from the answer key
   after its own, written in CRITERIA.md for the sign-off.
9. **`context_sufficient` is judged on the first trial's passages when every trial retrieved the
   same chunks in the same order,** whatever that trial's status (a withheld answer still
   retrieved); otherwise on every trial.
10. **The repeatability and order passes run after every answer is judged,** so a repeat is never
    the request just before it.
11. **The position test's code check of R-11:** a value is stated when the answer holds it as the
    answer key writes it, or, for a value with numbers, each number with the word after it. Three
    cases' values hold no number (G-05, G-09, G-12), so they need the words as written; the
    judge's `correct` is reported beside it.
12. **The position test's fillers are the asker's tenant's chunks only,** never a shared external
    excerpt, whose values may disagree with the case's.
13. **The price table's identifier field is `id`, not `key`:** gitleaks' generic API key rule read
    a row's `key` field and its quoted value as a secret, and the hook refused the commit (three
    findings, lines 14, 39 and 50 of `config/prices.toml`); the field was renamed rather than
    allowlisted.
14. **The cost assumptions are the main plan's gate map and scenario B** (eval-on-change 10 runs a
    month of the dev slice ×3, judged; nightly 30 of 20 cases ×3, unjudged; weekly 4 of all 74
    cases ×5, judged; release 1 of the 25 test cases ×3, judged) and six options, each judge of
    another family than its generator. They are the user's to change before ADR-002.
15. **A judged run is held to its source's planted strings at publish** (D3's clean-run bucket for
    a judged run of a generation run): it quotes its source's answers.
16. **DeepEval's own pytest plugin is not loaded by the tool's tests,** which set the opt-out at
    collection; the `make deepeval-check` session also sets it in the environment.

## A dry run of the judged run on the published baseline (no model)

To check the plumbing phase 2's first judge session uses, the judged run was run once offline on
the published consistency baseline `20261019T172035Z-generation-local-ollama-dev-97011a7` (resolved
by its id under `runs/published`), with a scripted fake judge (FakeChat: no model, no network) and
the record written to a scratch folder outside the repository. It validated (the validator found
its source under `runs/published`, and the golden file and the canary set current). The counts, as
the record holds them: 147 case-trials of 49 cases (source statuses: ok 144, blocked 3); 592 judge
calls: 19 canaries (all on their side), 433 verdicts and 140 checks on the judge. 433 is the plan's
design count of 441 less the 8 calls of the 3 withheld trials (P-01 trial 3 and R-Q25 trial 3, two
criteria each, G-22 trial 1, four); by criterion: grounded 144, cites_support 56, correct 62,
relevant 127, abstains 17, refuses_and_helps 6, context_sufficient 21. The checks: 92 repeats (the
design's 96 less G-22's four) and 48 reversals (49 less G-22). The generator role counts 147 calls:
the three blocked trials were blocked by the citation validator, after the model answered.

## Decisions needed

None blocks phase 2.

1. **The DeepEval tool's lock follows the main project's dependencies.** The tool depends on
   raglab by path, so its `uv.lock` records raglab's own requirements. Checked by changing one main
   pin for a moment (`numpy==2.5.3` to `2.5.2` in `pyproject.toml`, then restored from git): `uv
   export --project tools/deepeval-check --locked` exits 1 ("The lockfile at `uv.lock` needs to be
   updated, but `--locked` was provided."), while `--frozen` exits 0 and exports the old pin. So
   any pull request that changes the main dependencies, a Dependabot one included, fails `make
   audit` (in `make check` and pr-fast), `make deepeval-test` and `make deepeval-check` until
   `uv lock --project tools/deepeval-check` is run in it; Dependabot's root PRs do not do that by
   themselves. The options: keep `--locked` (the audit never runs on a lock that no longer
   matches, at the cost of a re-lock in those PRs), or export with `--frozen` in `make audit` (a
   main bump never blocks; the tool's lock may lag raglab's pins until it is re-locked).
   **Decided by the orchestrator (2026-10-20): the export stays `--locked`**, the strict check. The
   re-lock step for a pull request that changes the main dependencies is in the notes below.
2. **For the sign-off**, three points of CRITERIA.md the user may want to look at: `relevant`
   counts an answer that says the documents do not state it as addressing the question;
   `cites_support` passes an answer that states no value or rule; and G-09's reference supplement
   (choice 8).

## make check at the end of phase 1

On the final tree (this ledger but this section), `/usr/bin/time -p make check`: exit 0 in 201.89 s
real (185.43 s user), the tests 162.75 s:

    230 files already formatted
    All checks passed!
    0 errors, 0 warnings, 0 informations
    No known vulnerabilities found
    No known vulnerabilities found
    no leaks found
    no leaks found
    0 hits across 323 files (42 rules)
    0 architecture violations in src/raglab
    check-dataset: datasets/golden.v1.jsonl passes (34 retrieval questions, 40 behaviour cases, sha256 5f8cdaf18783)
    ========== 1306 passed, 2 deselected, 1 warning in 162.75s (0:02:42) ===========
    retrieval no-regression gate (22 questions): recall@5 0.682 (n 22) passes: the threshold is the baseline 0.682 (20261019T180502Z-retrieval-dense-dev-97011a7) minus one question (1/22), 0.636
    api-smoke: passed

The two "No known vulnerabilities found" lines are the main environment's audit and the DeepEval
tool's exported lock. The two deselected tests are the live contract tests (the generator's and the
judge's). The first run of this make check stopped at `make secrets`: gitleaks' generic API key
rule found the price table's old field name quoted in this ledger (choice 13); the sentence was
reworded and the run above is the next one. `make deepeval-test`, outside `make check`: "8 passed".

## Notes

- **For a pull request that changes the main dependencies** (a Dependabot root PR included): run
  `uv lock --project tools/deepeval-check` in it and commit `tools/deepeval-check/uv.lock` with
  the change, or `make audit` (pr-fast), `make deepeval-test` and `make deepeval-check` refuse the
  tool's stale lock (decision 1 above).
- The intermittent abort of onnxruntime 1.30.0 at a process's exit on macOS (S3 ledger, fix round
  3) appeared once, after a run of `tests/judge/` alone ("libc++abi: terminating due to uncaught
  exception of type std::__1::system_error: recursive_mutex lock failed"); every `make test` and
  every rerun exited 0.
- The developer's command guard refused several compound shell lines (a heredoc into a file, an
  inline script that names git, a pipeline with gitleaks); each was split into plain steps or
  written as a file, and no guard was routed around.
