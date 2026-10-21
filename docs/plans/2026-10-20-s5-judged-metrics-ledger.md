---
stage: S5
nodes: [S5]
---

# S5 ledger: judged metrics on local models, token measurement and the provider decision

Plan: [2026-10-20-s5-judged-metrics.md](2026-10-20-s5-judged-metrics.md).

This ledger covers **phase 1, the offline build, up to the user's sign-off of docs/CRITERIA.md and
the canary set**, the sign-off itself, **phase 2 as far as its step 2** (the short judge session
that set the judged run's cap, and the judged run on the consistency baseline, published), the
user's three answers after it, AC22 (the power guard), the second sign-off (`correct` reworded,
judge-v2), and the baseline judged again under judge-v2, published. The
position test (step 3), DeepEval's checks (step 4), `raglab cost` and ADR-002 (step 5), D6 and the
hosted half add their sections below.

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

**After the judged run (asked 2026-10-20 at about 22:05 WEST, answered by 2026-10-21 08:43 WEST;
the prompt does not record the minute).** The developer stopped after phase 2's step 2 and
reported three things (the step 2 section below); through the orchestrator's question prompt the
user answered all three:

| Question | Answer, verbatim | What was done |
|---|---|---|
| "Should local model sessions get a power guard, given the judged run drained the Mac to 1%?" | "Add it in S5 now (Recommended)". The option said: "Before the next live session: a session refuses to start unless the Mac is on AC power, and stops cleanly (model unloaded, Ollama down, nothing published) if it goes on battery mid-run. One new S5 criterion with tests; about 30 to 60 min of developer time." | A new criterion, AC22, in the plan's table with this quote; built before the next live session (the AC22 section below) |
| "The `correct` rule: reword it as above (second sign-off) and judge the baseline again before the position test?" (2026-10-21, 08:43 WEST) | "Reword and re-judge (Recommended)" | The second sign-off (below), then the baseline judged again |
| The `make audit` failure (new certifi and pillow advisories) | A dependency pull request from main: certifi to 2026.10.19, and Pillow's eight advisories skipped in `make audit` with a written reason and a review date | No dependency change in S5. The orchestrator builds that pull request and the user merges it; S5 then merges main and re-locks the DeepEval tool. Until then `make -k check`'s only failure is the known audit one |

**The second sign-off of docs/CRITERIA.md (2026-10-21).** At 08:43 WEST, through the
orchestrator's question prompt ("The `correct` rule: reword it as above (second sign-off) and
judge the baseline again before the position test?"), the user chose, verbatim: "Reword and
re-judge (Recommended)". The preview the user saw showed the old and the new pass rule. The
reason: in the first judged record (`20261020T195341Z-judge-local-dev-25ccc0d`), 17 of the 42
`correct` fails gave the missing document and section as their reason, when the signed-off rule
listed "the governing rule" among a reference answer's decisive facts and the judge sees the
answer's text, not its citations (the step 2 section below). The new pass rule, word for word in
CRITERIA.md and in the prompt: "the answer gives every decisive fact of the reference answer
(each value with its unit, each rule the reference states, an exception with its end date, both
sides of a conflict, the route) and contradicts none of them; the document and section a
reference names are its sources, not decisive facts". The fail rule did not change. No canary
changed side (C-09 and C-10 keep theirs), and the canary file did not change.

**A new prompt version, judge-v2, not judge-v1 edited in place (a deviation from the
orchestrator's wording, "judge_v1.RULES["correct"].passes").** The validator checks a judged
record's prompt fingerprint against its version's (`judged_record.PROMPTS[version]`), so judge-v1
edited in place would have made the first judged record invalid, when it stays published as
history; and AC2 (and `tests/judge/test_judge_prompt.py`) say a changed prompt is a new version.
So `src/raglab/judge/prompts/judge_v2.py` is judge-v1 with `correct`'s pass rule replaced and
nothing else (its system prompt, frames, schema, parser and other rules are judge-v1's, imported);
judge-v1 is unchanged (its helpers now take a version's rules as an argument; its fingerprint and
snapshot are the same, and the tests pin both versions). The model reads no version name, so a
judge-v2 call differs from a judge-v1 call only in `correct`'s pass rule (a test holds that). The
judge, the canary loader and the judged run use judge-v2; the validator keeps both. The one edit
to CRITERIA.md beyond the rule and the status paragraph follows from it: the prompt it names, in
its introduction and in the seven Grader lines, is now `judge-v2`.

**Frozen, in the commit of the second sign-off:** docs/CRITERIA.md sha256
`8c8f973a3306392fa1e2049ca41bcdb23d7a96d17f804af8ac84a0ca3edd9e0e`; the canary set sha256
`4ca54c3ced557118f26306543164dc01c7509d1866e9e77f6cd4f2d3284b328f` (unchanged); judge-v2's
fingerprint `e90d9d8d8bcbeca8cc4f3ea73a46ca486f20b1f750506185c3dd8952ec4dd90a`, with its
reviewed snapshot `tests/snapshots/judge-v2.txt` (one line differs from judge-v1's: `correct`'s
pass rule); judge-v1's stays `10d96ed31467c42c13e2b037956fef94e9a011b47156ffb88d095a40c3955368`.
Both published records validate after the change.

**A deviation from AC11's wording (the orchestrator's instruction, 2026-10-21).** AC11 says
DeepEval's checks are "recorded in CRITERIA.md, COMPATIBILITY.md and the ledger". CRITERIA.md is
frozen from each sign-off, and neither sign-off covered DeepEval's results, so its "Checked at
DeepEval 4.3.1" section stays as signed off ("Not run yet") and the results go to
docs/COMPATIBILITY.md and this ledger only; THRESHOLDS.md's DeepEval row points there. Writing
them into CRITERIA.md would need a third sign-off; the pull request reports the deviation.

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

| AC | Status (phase 1, then phase 2 as far as step 2) | Evidence | Break (restored from git) |
|---|---|---|---|
| AC1 | met at the judge-v2 record: signed off twice (2026-10-20 with the clause; 2026-10-21 with `correct` reworded, above); the judged record `20261021T081852Z-judge-local-dev-5aa0ec5` (created 2026-10-21T08:18:52Z) is 3 minutes after the second sign-off's commit `5aa0ec5`. The first record (2026-10-20T19:53:41Z) was 13 minutes after the first freeze `f68c37b` | `docs/CRITERIA.md` and `datasets/canaries.judge.jsonl` (`78d32e0`). `tests/unit/test_criteria.py`, 9 tests: every criterion has every field (applies to, the judge sees, passes, fails, requirements, grader, status); its pass and fail rules are judge-v1's words exactly; what the judge sees is judge-v1's inputs; every requirement named is one of TEST-PLAN's; every criterion is graded by judge-v1 and reported; the canary table is the canary file; every canary names a criterion and a side, and every criterion has an item on each side; the metric canary, its honest twin and the two injection canaries are there; every corpus passage a canary names is in the committed inventory. A judged manifest carries the sha256 of both files, and publish refuses a judged run made under another version of either (`tests/judge/test_judged_run.py`). The date check against the first judged manifest waits for that manifest | (1) context_sufficient's "Fails when" line removed from docs/CRITERIA.md: "2 failed, 7 passed" ("context_sufficient has no ['Fails when']"), restored "9 passed". (2) publish's stale check disabled (`if False:` in `publish.judged_problems`): the edited-CRITERIA and flipped-side tests "2 failed" ("DID NOT RAISE PublishError"), restored "2 passed". The plan's live form of this break (a published judged record) waits for one |
| AC2 | met offline; judge-v2 since the second sign-off, judge-v1 kept and pinned | `tests/judge/test_judge_prompt.py` (22 tests since judge-v2: the snapshot and the fingerprint of each version, the judge on the newest, judge-v2 differs from judge-v1 only in `correct`'s pass rule; first 18 tests: the snapshot of all seven criteria's prompts; the reviewed fingerprint, `10d96ed31467...` since the sign-off (the draft's was `481783ef7361...`); every criterion has rules; a criterion is shown exactly the inputs it sees, and an item showing more or less is refused; no passages is said plainly; no input can close its frame or open another, in any letter case; a passage attribute cannot break out of its tag; no developer comments; the schema puts the evidence before the verdict) and `tests/judge/test_verdict_parser.py` (22 tests: a reply in the schema parses; thirteen replies off the schema are refused, an extra field, a missing one, a verdict outside the enum, a code fence, text after the JSON, a repeated field among them; an off-schema reply is unable_to_verify with status invalid_output and the reply kept; no reply is unavailable; the quote is checked against the answer and reported; passage ids not shown are reported; a verdict's seed, schema and system prompt; an off-schema or unavailable verdict is never a pass). `make architecture`: 0 violations (`raglab.core` imports the standard library only) | (1) one word of SYSTEM changed ("given" to "shown"): "2 failed, 16 passed" (snapshot and fingerprint), restored "18 passed". (2) the parser made to accept extra fields (`not FIELDS <= frozenset(data)`): "2 failed, 20 passed", restored "22 passed". (3) `as_data` made a no-op: "5 failed, 13 passed" (the four frames and the attribute), restored "18 passed" |
| AC3 | met: the live contract test passed in every judge session (seven: 2026-10-20 at 17:28, 20:42 and 20:53; 2026-10-21 at 09:16, 09:18, 10:27 and 10:38) | `tests/unit/test_ollama_session.py` additions: a judge config's session checks the judge, never the generator (with only the generator pulled it refuses, naming the judge); it starts with its pinned model and says its size and digest; a replaced digest refuses before the server starts, for the judge and for the generator; a manifest without a registry digest refuses; an unpinned generator digest is not checked and the session says so; the CLI builds the judge's session; the make targets run one model per session. `tests/unit/test_eval_config.py` additions: the committed judge config (tag, digest, temperature 0, the generator's session limits) and eight wrong judge configs refused. `tests/contract/test_judge_contract.py`: the stub contract in pr-fast (the config's temperature, cap, seed and schema sent; a reply off the schema is invalid_output with its tokens; an HTTP error is unavailable; another digest refuses to start); the live test in the session. COMPATIBILITY.md: "Tested against ministral-3:14b-instruct-2512-q4_K_M@4760c35aeb9d9e9c6174c2492562c0b999e80a222804fd96b1915ab72bbcdcf7 on Ollama 0.40.6 on 2026-10-20" | (1) the preflight given the generator's model for a judge config (in `session_for`): "4 failed, 6 passed", restored "10 passed". (2) the digest replaced in `config/judge-local.toml` (`4760...` to `5760...`): the judge tests "5 failed, 11 passed"; and `make judge-contract` against this Mac's real manifest: "ollama session: the session may not start: - ministral-3:14b-instruct-2512-q4_K_M on this Mac has digest sha256:4760c35aeb9d9e9c6174c2492562c0b999e80a222804fd96b1915ab72bbcdcf7, not the pinned sha256:5760c35aeb9d9e9c6174c2492562c0b999e80a222804fd96b1915ab72bbcdcf7: a session never serves other weights than its config pins", `make` error 1, no server started; restored "16 passed", and `make ollama-status` showed no pid, the port closed, no process, nothing loaded |
| AC4 | met offline and live: all 19 on their side in every session that ran them (six: two under judge-v1, four under judge-v2), their results in the three published judged manifests; the live flipped canary is the criteria judge's break | `tests/judge/test_canaries.py` (17 tests: a judge with every committed canary on its side passes them; one canary off its side stops the judge, naming it, whether the verdict is the other side, unable_to_verify, off the schema or missing; every item off its side is named, not only the first; the results name each item, its side and its verdict, never a passage's text; corpus passages are read from the corpus and a written one is kept; a wrong canary is refused, naming the line). `tests/judge/test_judged_run.py`: the canaries run before every answer, a miss stops the run before any judged call (the chat saw the canary calls only), and the CLI writes no record then | The stop removed (`off_side(results)[:0]`): "6 failed, 33 passed" (the four stop cases, the run and the CLI), restored "39 passed" |
| AC5 | met: the judged records `20261020T195341Z-judge-local-dev-25ccc0d` (judge-v1, history) and `20261021T081852Z-judge-local-dev-5aa0ec5` (judge-v2) validated and published; both still validate | `tests/judge/test_judged_run.py` (22 tests): a judged run writes a valid record tied to its source (case-trials in the source's order, the answer's sha256, the copied retrieval, the source's chunker, embedder, retriever, corpus and dataset); each answer takes its criteria, context_sufficient once per case; a cited answer is shown its cited passages; a withheld trial is not judged but its retrieval is; the run stops at its cap and is partial; a resealed line whose answer sha256 differs, edited results, a flipped verdict, dropped completion tokens, other shown passages, a missing line, a changed source, a forged quote check and a canary off its side are refused; publish requires the source published and refuses a stale run; judged runs are held to their source's planted strings. The committed-runs test validates every published record unchanged | (1) the answer-sha256 tie skipped in `line_problems`: "1 failed, 21 passed", restored "22 passed". (2) the judged results trusted as recorded instead of recomputed (in `record.expected_results`): "2 failed, 20 passed", restored "22 passed" |
| AC6 | met for the three judged records and the position run (every call reported its tokens: unreported 0 in every role); DeepEval's wait for step 4 | Every call's tokens: the generator's per case-trial from the source lines (`source_tokens`, `source_called`), the judge's per verdict, the checks' and the canaries', totalled by role in `results.judged.tokens` (calls, prompt, completion, unreported); with the stub's usage (`test_every_calls_tokens_are_totalled_by_role`: generator 14 calls, 1400 and 280; the judge's 300 and 40 a call) and without (FakeChat: every judge call unreported). The DeepEval wrapper records every call's tokens (`RaglabJudgeLLM.tokens`); the position run is a generation record, whose tokens S3 records | The judge's completion tokens dropped from the totals (`"completion": 0` in `judged_record._role`): "3 failed, 34 passed", restored "37 passed" |
| AC7 | met at `20261021T081852Z-judge-local-dev-5aa0ec5` (judge-v2): the consistency baseline judged and published, every number in the ledger copied from the record; the first record, under judge-v1, stays published as history | `raglab judge`, `make judge-local RUN=`; THRESHOLDS.md marks every judged criterion reported with the reason (`57f6fad`) | The verdict no longer read again from its reply (only the quote, ids and reason compared): the flipped-verdict test "1 failed, 21 passed", restored "22 passed". The plan's break on the published record waits for it |
| AC8 | met: repeatability 92 of 92 pairs agree, order 46 of 48, in both published records | The repeatability pass (trial 1 of every behaviour case judged again) and the order pass (grounded on trial 1 of every case with the passages reversed), both after every answer is judged, both in the record and validated (`tests/judge/test_order_check.py`, 4 tests) | The order check given the passages in their original order (`reverse=False` in `judged.run`): "2 failed, 2 passed", restored "4 passed" |
| AC9 | met: the position run `20261021T092047Z-generation-local-ollama-position-dev-f309594` (one generator session, scored by code) and the judge's `correct` on it `20261021T092819Z-judge-local-dev-9fa9004`, both published (the position section below) | `tests/generation/test_position_contexts.py` (20 tests): first, middle (n // 2) and last; the fillers are the tenant's other chunks in rank order, never a labelled section or a group member, nor another tenant's or a shared chunk; the fit to the budget; the measured characters per token are the fewest; a value is stated as the answer key writes it or by its numbers and units (11 cases); the committed config names the ten cases, derived from the golden file; a position run writes a valid generation record; a moved answering chunk, a labelled filler and forged checks are refused; the judge's `correct` runs on a position run | (1) the answering chunk put first at every position (`index = 0` in `place`): "3 failed, 17 passed", restored "20 passed". (2) a group member allowed as filler (only plain labels excluded in `fillers`): "1 failed, 19 passed", restored "20 passed" |
| AC10 | met offline and live (the opt-out set before the import, the guard on and catching 0 attempts, every metric in mode `llm`, every call through raglab's adapter: the DeepEval section below); needs CI for `make audit`, red until the dependency pull request (Notes) | `tools/deepeval-check` locks `deepeval==4.3.1` (94 packages resolved); the main environment never installs it (`uv sync --locked` unchanged, the main `uv.lock` holds no deepeval, `find_spec("deepeval")` is None and no `deepeval` pytest plugin is registered: `test_the_main_environment_never_installs_deepeval`); rule 6 forbids a deepeval import anywhere under `src/` (`test_deepeval_is_imported_nowhere_in_the_package_adapters_included`, 12 cases); `make audit` exports its 92 pinned requirements with their hashes and audits them without installing ("No known vulnerabilities found"); deptry leaves `tools/` to its own lock; Dependabot watches it, a DeepEval bump in a PR of its own. `make deepeval-test`: "8 passed" (the opt-out set before the first DeepEval import, recorded by an import hook; the guard lets nothing but the loopback Ollama port through; the custom-LLM API returns the schema's instance and records tokens; a whole FaithfulnessMetric in mode llm through the wrapper against a stub, with no connection attempted; the direction report; the canary reading) | (1) `import deepeval` added to `src/raglab/adapters/openai_compat.py`: `make architecture` "1 architecture violations" ("src/raglab/adapters/openai_compat.py:28: deepeval is fenced in tools/deepeval-check and imported nowhere in raglab, adapters included"), restored "0 architecture violations". (2) The opt-out unset with the guard on (a probe outside the repository: DeepEval imported and a FaithfulnessMetric run against a stub judge, the guard installed before the import and kept until the interpreter exits): no attempt during the import or the metric, then at exit "[PostHog] error uploading: HTTPSConnectionPool(host='us.i.posthog.com', port=443)": 12 lookups of `us.i.posthog.com:443`, every one caught. With the opt-out set to 1 before the import: no attempt at all, exit included |
| AC11 | partly met: the live checks ran at 4.3.1 (the DeepEval section below): the custom-LLM API works; the metric canary and the hallucination direction scored 0.0 throughout, so they read nothing; the cross-check did not run (a reply cut off at 512 tokens); a second session is the orchestrator's call. Deviation from its wording: the results go to COMPATIBILITY.md and this ledger, not CRITERIA.md, which is frozen (a third sign-off would be needed; the pull request reports it) | The checks are code (`tools/deepeval-check/src/deepeval_check/checks.py`): the custom-LLM API, the metric canary (C-01 and C-03 with penalize_ambiguous_claims off and on), the hallucination direction (G-01's labelled passage, a consistent and a contradicting output, the page's sentence and its read date), the cross-check against the own judge's grounded on trial 1 of the dev answer cases; every metric in mode llm. Offline: `test_the_direction_report_names_the_output_that_scored_higher` (3 cases) and `test_the_canary_reading_follows_the_invented_answers_verdict` | The direction report's scores swapped (`x, c = ...`): `make deepeval-test` "2 failed, 6 passed", restored "8 passed" |
| AC12 | met: `make cost` over the judge-v2 baseline (step 5 below), the table read again on 2026-10-21 (unchanged), THRESHOLDS.md's cost section and Q-01 from the output and the records | `config/prices.toml` (seven rows, each with its source URL and read date 2026-10-20; the table's date is its latest read date); `config/cost-assumptions.toml`; `raglab cost --judged` (`tests/unit/test_cost.py`, 15 tests: a call's cost by hand; the estimate by hand, per call, per case-trial, per run and per month; a prompt above a price's tier refused; the committed table's rows and dates; eight wrong tables refused; the committed options keep the judge's family apart; an option naming no price refused; the CLI on a judged record). THRESHOLDS.md states the formula | (1) the output price applied to prompt tokens (`prompt * price.output` in `call_cost`): "2 failed, 13 passed" (`0.0022 == 0.0012`), restored "15 passed". (2) one price's `source` line removed from `config/prices.toml`: "7 failed, 8 passed" ("price 5 (openai-gpt-5-nano): missing ['source']"), restored "15 passed" |
| AC13 | ADR-002 written from `raglab cost`'s output (`91a9a16`), with its test; not met until the user's choice (D6) is quoted in it | `docs/decisions/ADR-002-providers.md`; `tests/unit/test_adr.py` (2 tests) | a cost edited by hand in the ADR ($1.21 to $0.99): the test failed; restored from git |
| AC14 | met but for ARCHITECTURE and README marking S5 `done`, which waits for the pull request; LOCAL-MODEL now has the judge sessions' measured times and the power rule | TEST-PLAN R5 names its tests (nine) and its gate ("local until keys (`make judge-local`); reported, not gated, until S6 calibrates the judge"), its oracle says what is judged and what stays label-based; section 10's judges line and the metric canary line; Q-01 and Q-02 point at THRESHOLDS.md; the Test column names the judged criteria (reported) for R-01, R-03 to R-07, R-10, R-11, R-14 and R-18 (`tests/unit/test_test_plan.py`, two new tests); LOCAL-MODEL, COMPATIBILITY, ONBOARDING (current as of S5, in progress), ARCHITECTURE and README (S5 `wip`; S5 before S4b), a CHANGELOG line. The measured numbers (THRESHOLDS cost and Q-01, the judge's session time on the judged run, COMPATIBILITY's DeepEval lines) wait for the runs | |
| AC15 | met locally (the tail below); needs CI (pr-fast) | No new runtime dependency in the main project (`pyproject.toml` changed only in tool settings: deptry's `extend_exclude`, ruff's per-file ignores for the tool's tests); `make gate` passes; every published record validates | |
| AC16 to AC21 | not started: after the sign-up (D5), if D6 picks a provider | | |
| AC22 | met offline (the live power line follows with the next session) | The preflight's power check and the watcher in `raglab.runtime.ollama`; 16 tests in `tests/unit/test_ollama_session.py` with a fake power reader (the AC22 section below) | the preflight's check removed: 9 of the 16 power tests fail; the watcher never started: all 5 mid-session tests fail (restored from git) |

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

Published: the judged baseline under judge-v2, `runs/published/20261021T081852Z-judge-local-dev-5aa0ec5/`, and the first one,
under judge-v1, `runs/published/20261020T195341Z-judge-local-dev-25ccc0d/`, kept as history. Under `runs/tmp`
(gitignored): the judge contract logs `runs/tmp/judge-contract/20261020T162848Z.jsonl`,
`20261020T194209Z.jsonl`, `20261020T195309Z.jsonl`, `20261021T081602Z.jsonl` and
`20261021T081822Z.jsonl`, the canary logs `runs/tmp/canaries/20261020T194409Z.jsonl` and
`20261021T081802Z.jsonl`, and the exported requirements of the tool's lock that
`make audit` writes. The runs pytest makes are fake or stub-server records in temporary
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

## Phase 2, step 1: the short judge session (2026-10-20, after the sign-off)

`make judge-canaries` at `68f95bf` (the freeze is `f68c37b`): one guarded session, 20:42:08 to
20:44:10 WEST by the shell's clock, exit 0. The preflight said "model:
ministral-3:14b-instruct-2512-q4_K_M at the pinned digest 4760c35aeb9d" and "memory: 23.1 GiB
available; the model needs 8.5 GiB plus a margin of 4 GiB"; Ollama 0.40.6 started on
127.0.0.1:11434; after the two commands, the model was unloaded, the server stopped and the
postcheck passed (port closed, no ollama process, no model loaded). `make ollama-status` after:
down, 21.3 GiB available.

1. **The judge's live contract test** (its second run; log `runs/tmp/judge-contract/20261020T194209Z.jsonl`):
   1 passed. With `json_schema`, 4 of 4 replies were valid verdicts: 10.546 s (the cold call,
   model load included), 3.327, 2.976 and 2.591 s. Prompt-only (`none`), 3 of 3 were
   invalid_output, as in the first run: the judge keeps `json_schema`.
2. **The canaries, alone** (`raglab canaries`; log `runs/tmp/canaries/20261020T194409Z.jsonl`, each
   item's verdict, reply, seconds and tokens): **all 19 on their side**, every one with status ok;
   the quote check found every quote (C-16 and C-17, `context_sufficient`, see no answer and quote
   none). Seconds per call: 2.487 to 9.196 (C-14, `refuses_and_helps`, 182 completion tokens), median
   3.790, mean 4.519, 85.854 in all. Tokens: prompt 330 to 1,174 a call (14,190 in all),
   completion 59 to 182 (1,688 in all).

| Item | Criterion | Must | Judged | Seconds | Prompt | Completion |
|---|---|---|---|---|---|---|
| C-01 | grounded | fail | fail | 5.652 | 1095 | 60 |
| C-02 | abstains | fail | fail | 6.392 | 1095 | 82 |
| C-03 | grounded | pass | pass | 2.931 | 1101 | 75 |
| C-04 | abstains | pass | pass | 3.014 | 1101 | 77 |
| C-05 | grounded | pass | pass | 5.702 | 706 | 114 |
| C-06 | grounded | fail | fail | 5.331 | 600 | 115 |
| C-07 | cites_support | pass | pass | 4.173 | 424 | 94 |
| C-08 | cites_support | fail | fail | 3.790 | 437 | 90 |
| C-09 | correct | pass | pass | 3.660 | 420 | 80 |
| C-10 | correct | fail | fail | 2.553 | 420 | 66 |
| C-11 | relevant | pass | pass | 2.526 | 330 | 59 |
| C-12 | relevant | fail | fail | 2.681 | 340 | 70 |
| C-13 | abstains | fail | fail | 7.444 | 1105 | 108 |
| C-14 | refuses_and_helps | pass | pass | 9.196 | 847 | 182 |
| C-15 | refuses_and_helps | fail | fail | 3.681 | 819 | 96 |
| C-16 | context_sufficient | pass | pass | 5.346 | 509 | 115 |
| C-17 | context_sufficient | fail | fail | 3.185 | 554 | 67 |
| C-18 | grounded | fail | fail | 2.487 | 1113 | 60 |
| C-19 | grounded | fail | fail | 6.109 | 1174 | 78 |

**The judged run's wall-clock cap, set from it:** `run_timeout_s = 7200` in
`config/judge-local.toml` (it was 14,400, the plan's ceiling, until this session). The baseline's
judged run makes 592 calls (the dry run's count); 592 times 9.196 s, the slowest canary call, is
5,444 s. The baseline's answers are longer than the canaries' (ok answers: median 160 characters,
the longest 662; the canaries': median 98, the longest 238), and the judge quotes from them, so the
cap is rounded up to 2 hours, about 1.3 times that product. The time outside the judge's calls is
under a second: the dry run took 0.546 s in all, ingest included. At the canaries' mean the 592
calls would take about 45 minutes (a projection, not a measurement); the judged run measures its
own. The Mac time so far is far under the plan's 4 hours for the judge sessions.

## Phase 2, step 2: the judged run on the consistency baseline (2026-10-20)

`make judge-local RUN=20261019T172035Z-generation-local-ollama-dev-97011a7` at `25ccc0d` (the cap's
commit; the tree clean): one guarded session, 20:53:08 to 22:34:02 WEST by the shell's clock, exit
0. The preflight said "model: ministral-3:14b-instruct-2512-q4_K_M at the pinned digest
4760c35aeb9d" and "memory: 21.6 GiB available; the model needs 8.5 GiB plus a margin of 4 GiB".
The judge's live contract test passed again (log
`runs/tmp/judge-contract/20261020T195309Z.jsonl`: `json_schema` 4 of 4 valid verdicts, `none` 3 of
3 invalid_output). Then `raglab judge`: "canaries: all 19 on their side", "judged 147 case-trials",
the checks on the judge, and the record, validated as it was written. After it: the model
unloaded, the server stopped, "postcheck passed: port closed, no ollama process, no model loaded";
`make ollama-status`: down, 27.7 GiB available.

**The Mac hibernated during the judged run.** The session started at 20:53:01 WEST with the Mac on
battery (the power log's last reading before it, at 20:30:25, was "Using BATT (Charge:43%)"). The
power log (`pmset -g log`), verbatim:

```
2026-10-20 21:19:14 +0100 Sleep  Entering Sleep state due to 'Low Power Sleep':TCPKeepAlive=inactive Using Batt (Charge:1%) 2188 secs
2026-10-20 21:55:42 +0100 Wake   Wake from Hibernate [CDNVA] : due to acattach rtc IOPortFeatureLDCM.measurement/UserActivity Assertion Using AC (Charge:1%)
```

The battery ran down to 1% under the judge's load and macOS hibernated the Mac for 2,188 s (36.5
minutes); it woke when the 140 W adapter was attached. Every process, the server and the run
included, was frozen in between, and the run went on after the wake. From the server's request log
(Ollama's GIN lines, all HTTP 200): before the sleep, 213 judged calls at a mean of 6.80 s (median
6.23, the longest 19.44); the call in flight at the sleep returned 1m1s of awake time after the
wake; the next 8 calls took 22.49 s on average; by 22:01 the last 10 calls were back to a mean of
4.04 s (median 3.51). Why the calls after the wake were slow was not measured; the developer's
reading, not a measurement, is that the model's memory was being read back from the hibernation
image.

**The clock.** The run's cap, its `duration_s` and each verdict's `latency_ms` are measured with
Python's `time.monotonic()` and `time.perf_counter()`, which on macOS are `mach_absolute_time()`
(checked with `time.get_clock_info`): they do not advance while the Mac sleeps. So the cap counted
awake time only, the record's `duration_s` is about 36.5 minutes shorter than the session's span
by the wall clock, and the judge's latency p50 and p95 in the record include the calls made just
after the wake.

**For the pull request (a decision, not built):** the session's preflight checks memory and the
model's digest, not the power source. A judge session on battery can run the Mac down, as this one
did; a preflight could refuse to start on battery, or below a charge, or the docs could say to run
on AC.

**The record, published:** `runs/published/20261020T195341Z-judge-local-dev-25ccc0d/` (`raglab publish`, exit 0: valid, not partial,
provenance local, made from a clean tree, its source published with the manifest it names,
docs/CRITERIA.md and the canary set current, no planted string, the privacy check clean). Created
2026-10-20T19:53:41Z, 13 minutes after the freeze commit `f68c37b` (2026-10-20T20:40:21+01:00):
AC1's date check. The judge block: `ministral-3:14b-instruct-2512-q4_K_M`, digest
`4760c35aeb9d9e9c6174c2492562c0b999e80a222804fd96b1915ab72bbcdcf7`, server 0.40.6, temperature 0.0,
max_tokens 512, timeout_s 180.0, response_format `json_schema`; judge-v1 `10d96ed31467...`;
CRITERIA.md `7e3a522335c7...`; the canary set `4ca54c3ced55...`; the source
`20261019T172035Z-generation-local-ollama-dev-97011a7` (manifest sha256 `29b4ba03b84d...`). 49
cases, 147 case-trials; 592 judge calls (19 canaries, 433 verdicts, 140 checks), none unavailable,
none invalid_output, none unable_to_verify; `duration_s` 3869.275 (awake
time, above). `make gate` passes after the publish, and the publish, record, judge and cost tests
pass over the published records (200 passed).

The judged criteria, as the record's report gives them (reported, not gated: the judge is
uncalibrated until S6):

| Metric | Rate | 95% interval | n (cases) |
|---|---|---|---|
| grounded | 0.868 | 0.746 to 0.936 | 49 |
| grounded[answer] | 0.882 | 0.657 to 0.967 | 17 |
| grounded[flag-conflict] | 0.600 | 0.132 to 0.937 | 2 |
| grounded[refuse-and-help] | 0.833 | 0.241 to 0.987 | 2 |
| grounded[abstain] | 0.706 | 0.330 to 0.921 | 6 |
| grounded[retrieval] | 0.923 | 0.740 to 0.981 | 22 |
| grounded_pass^3 | 0.714 | 0.576 to 0.822 | 49 |
| cites_support | 0.839 | 0.621 to 0.943 | 19 |
| cites_support[answer] | 0.882 | 0.657 to 0.967 | 17 |
| cites_support[flag-conflict] | 0.400 | 0.063 to 0.868 | 2 |
| cites_support_pass^3 | 0.684 | 0.460 to 0.846 | 19 |
| correct | 0.323 | 0.164 to 0.536 | 21 |
| correct[answer] | 0.392 | 0.201 to 0.623 | 17 |
| correct[flag-conflict] | 0.000 | 0.000 to 0.658 | 2 |
| correct[refuse-and-help] | 0.000 | 0.000 to 0.658 | 2 |
| correct_pass^3 | 0.190 | 0.077 to 0.400 | 21 |
| relevant | 0.819 | 0.679 to 0.906 | 43 |
| relevant[answer] | 0.824 | 0.590 to 0.938 | 17 |
| relevant[flag-conflict] | 1.000 | 0.342 to 1.000 | 2 |
| relevant[refuse-and-help] | 0.667 | 0.159 to 0.955 | 2 |
| relevant[retrieval] | 0.815 | 0.612 to 0.925 | 22 |
| relevant_pass^3 | 0.674 | 0.525 to 0.795 | 43 |
| abstains | 0.353 | 0.106 to 0.714 | 6 |
| abstains[abstain] | 0.353 | 0.106 to 0.714 | 6 |
| abstains_pass^3 | 0.167 | 0.030 to 0.564 | 6 |
| refuses_and_helps | 1.000 | 0.342 to 1.000 | 2 |
| refuses_and_helps[refuse-and-help] | 1.000 | 0.342 to 1.000 | 2 |
| refuses_and_helps_pass^3 | 1.000 | 0.342 to 1.000 | 2 |
| context_sufficient | 0.619 | 0.409 to 0.792 | 21 |
| context_sufficient[answer] | 0.765 | 0.527 to 0.904 | 17 |
| context_sufficient[flag-conflict] | 0.000 | 0.000 to 0.658 | 2 |
| context_sufficient[refuse-and-help] | 0.000 | 0.000 to 0.658 | 2 |

| Criterion | Cases | Judged | pass | fail | unable_to_verify | invalid_output | unavailable | Quote found | Quote missing | Passages not shown |
|---|---|---|---|---|---|---|---|---|---|---|
| grounded | 49 | 144 | 125 | 19 | 0 | 0 | 0 | 140 | 4 | 0 |
| cites_support | 19 | 56 | 47 | 9 | 0 | 0 | 0 | 49 | 7 | 0 |
| correct | 21 | 62 | 20 | 42 | 0 | 0 | 0 | 55 | 7 | 3 |
| relevant | 43 | 127 | 104 | 23 | 0 | 0 | 0 | 123 | 4 | 0 |
| abstains | 6 | 17 | 6 | 11 | 0 | 0 | 0 | 16 | 1 | 0 |
| refuses_and_helps | 2 | 6 | 6 | 0 | 0 | 0 | 0 | 6 | 0 | 0 |
| context_sufficient | 21 | 21 | 13 | 8 | 0 | 0 | 0 | 0 | 0 | 0 |

The checks on the judge (AC8). The two order-check pairs that disagree are P-01 trial 1 and G-01
trial 1: `grounded` fail with the passages in their order, pass reversed.

| Check | Pairs | Agree |
|---|---|---|
| repeat: grounded | 26 | 26 |
| repeat: cites_support | 18 | 18 |
| repeat: correct | 20 | 20 |
| repeat: relevant | 20 | 20 |
| repeat: abstains | 6 | 6 |
| repeat: refuses_and_helps | 2 | 2 |
| order: grounded reversed | 48 | 46 |

Tokens and time (AC6):

| Role | Calls | Prompt | Completion | Unreported |
|---|---|---|---|---|
| generator | 147 | 153210 | 16138 | 0 |
| judge | 433 | 315104 | 51385 | 0 |
| judge_checks | 140 | 115648 | 16807 | 0 |
| canaries | 19 | 14190 | 1688 | 0 |

- Judge calls' latency: p50 5865.893 ms, p95 12957.615 ms (n 592); the run took 3869.275 s.

**What the judged numbers show (read from the record; reported).**

1. **`correct` is low: 0.323 (0.164 to 0.536, n 21).** The signed-off rule lists "the governing
   rule" among a reference answer's decisive facts, and the judge sees the answer's text, never its
   citations. The generator often answers with a bare value, and the judge then fails it for not
   naming the document and section. G-08 trial 1 answered "5 minutes" to "After how much idle time
   does a kiosk session end on its own?"; the reference is "Kiosk sessions sign out automatically
   after 5 minutes of inactivity (Device Policy Annex B: Shared Kiosk Devices, section 1, the
   scanned page)."; the judge's reason: "The answer omits the governing rule ('Device Policy Annex
   B: Shared Kiosk Devices, section 1') and the unit ('minutes') is implied but not explicitly
   stated as part of the policy context." Trials 2 and 3 answered "After 5 minutes of inactivity."
   and failed with "The answer omits the governing rule ('Device Policy Annex B: Shared Kiosk
   Devices, section 1') but matches the decisive fact (5 minutes of inactivity)." Of the 42
   `correct` fails, 17 give "governing rule" in their reason (a search of the reasons for the
   words), across G-01, G-05, G-08, G-09, G-11, G-17, G-19, G-21, G-34 and G-36. Other fails are on
   the value itself: G-31 answered "64" to "How many characters must a Halvenroot password have
   under the standard in force today?", whose reference is "at least 15 characters". Whether "the
   governing rule" means the document's name or the rule's substance is the user's to decide (the user
   decided it on 2026-10-21: the second sign-off, above); the
   rule is frozen, and this ledger does not change it.
2. **`abstains` is 0.353 (0.106 to 0.714, n 6):** 11 of the 17 judged abstain answers fail. On
   P-03 ("When is a leaver's account disabled?"), an abstain case, trial 1 answered "24 hours".
3. **The checks:** the 92 repeated verdicts agree with the first in every pair; the order check
   agrees in 46 of 48.

## AC22: the power guard (developer, 2026-10-21)

Built in `1c20e08`, before any further live session, by the user's choice above.

- **The preflight** (`raglab.runtime.ollama`, `Session.power_problems`): on macOS it reads the
  source `pmset -g batt` names ("Now drawing from 'AC Power'") and says it in a `power:` line after
  the `model:` and `memory:` lines. It refuses the session, and starts nothing, unless the source
  is `AC Power` (on battery, 'Battery Power'; on a UPS, 'UPS Power'), and when it cannot read one
  (fails closed). Off macOS it says "power: not checked (not macOS)"; CI runs no live session.
  `make ollama-up` goes through the same preflight; `make ollama-status` shows the source.
- **While the commands run:** a watcher thread reads the source every 15 s (`POWER_INTERVAL_S`).
  The first reading that is not AC power, or none, halts the session. The session's default
  runner (`run_command` with the halt) looks at it every 0.5 s and ends the running command's
  whole process group (SIGTERM, then SIGKILL after 5 s), and no further command starts. The stop
  then runs as on any interruption: the model unloaded, the server stopped, the postcheck. The
  interrupted command writes no run record, because a record is written when a run ends, and a
  session never publishes. The last line is one `STOPPED:` line naming the source and the time,
  and the exit is 75 (EX_TEMPFAIL). The watcher raises nothing in the main thread: the halt is an
  event the runner polls, so the stop's own finally block cannot be cut short.
- **Tests** (`tests/unit/test_ollama_session.py`, 16 new, with a fake power reader):
  - AC power proceeds, with the `power:` line beside the model and memory lines;
  - 'Battery Power' and 'UPS Power' refuse, and nothing starts;
  - an unreadable source refuses on macOS;
  - off macOS: not checked, no watcher;
  - the real host's reading of `pmset -g batt` (AC, battery, empty and unexpected output, Linux);
  - on battery mid-session, with a fake runner: the command halted and its record never
    written, no second command, the model unloaded, the server stopped, the postcheck, one
    STOPPED line last, exit 75;
  - an unreadable source mid-session stops it too;
  - a session that stays on AC power is not stopped;
  - `run_command` with a halt ends a command's whole process tree (a grandchild `sleep 30`);
  - the session's default runner halts a real command (30 s, then its record): the record is
    never written;
  - `raglab ollama session` through the CLI: exit 75, no traceback, the postcheck, one STOPPED
    line last, no record.
- **Breaks, each restored from git:**
  - the preflight's power check removed (`return problems` instead of `return problems +
    self.power_problems()`): 9 of the 16 power tests failed (the `power:` line, the battery,
    UPS and unreadable refusals, the not-macOS line, and the four mid-session tests, since
    without the check no watcher starts);
  - the watcher never started (`if False:` for `if self.power_watched:`): all 5 mid-session
    tests failed;
  - restored: 64 of 64 session tests pass.
- `make -k check` after it: 1323 passed; the only failure is `audit`, the known advisories
  (Notes).
- **Docs:** LOCAL-MODEL.md's guards (the rule, the watcher, exit 75, `make ollama-up` is not
  watched) and its commands table (`make judge-canaries`; `make ollama-status` shows the power).
- **Live evidence:** the `power:` line of the next session's log (below).

## Phase 2 again under judge-v2 (2026-10-21)

### The short judge session under judge-v2, and AC22's live evidence

`make judge-canaries` at `5aa0ec5` (the second sign-off): one guarded session, 09:16:01 to
09:18:03 WEST by the shell's clock, exit 0. The preflight's lines, verbatim:

```
model: ministral-3:14b-instruct-2512-q4_K_M at the pinned digest 4760c35aeb9d
memory: 23.9 GiB available; the model needs 8.5 GiB plus a margin of 4 GiB
power: the Mac draws from 'AC Power'
```

The `power:` line is AC22's live evidence: the session read the source before it started, and
the watcher read it while the commands ran (the session was not stopped). The judge's live
contract test passed (log `runs/tmp/judge-contract/20261021T081602Z.jsonl`: `json_schema` 4 of 4
valid verdicts, 10.316 s cold then 3.311, 2.971 and 2.623 s; `none` 3 of 3 invalid_output). The
canaries under judge-v2 (log `runs/tmp/canaries/20261021T081802Z.jsonl`): **all 19 on their
side**, every one with status ok, C-09 and C-10 (`correct`) among them; 2.503 to 9.432 s a call,
median 3.791, mean 4.556, 86.571 s in all. C-09 and C-10's prompts are 437 tokens (420 under
judge-v1: `correct`'s longer pass rule). After it: the model unloaded, the server stopped,
"postcheck passed"; `make ollama-status`: down, power 'AC Power'.

The judged run's cap stays 7,200 s: the first judged run took 3,869.275 s of awake time.

### The judged baseline under judge-v2, published

`make judge-local RUN=20261019T172035Z-generation-local-ollama-dev-97011a7` at `5aa0ec5` (the
tree clean): one guarded session, 09:18:21 to 10:15:13 WEST by the shell's clock, on AC power
throughout, exit 0. The preflight said "memory: 22.7 GiB available; the model needs 8.5 GiB plus
a margin of 4 GiB" and "power: the Mac draws from 'AC Power'". The judge's live contract test
passed (log `runs/tmp/judge-contract/20261021T081822Z.jsonl`: `json_schema` 4 of 4 valid
verdicts, `none` 3 of 3 invalid_output); then "canaries: all 19 on their side", "judged 147
case-trials", the checks on the judge, and the record, validated as it was written; the model
unloaded, the server stopped, "postcheck passed". `make ollama-status` after: down, 23.2 GiB
available, power 'AC Power'.

**The record:** `runs/published/20261021T081852Z-judge-local-dev-5aa0ec5/` (`raglab publish`, exit 0: valid, not partial,
provenance local, from a clean tree, its source published with the manifest it names,
docs/CRITERIA.md and the canary set current, no planted string, the privacy check clean). Created
2026-10-21T08:18:52Z, 3 minutes after the second sign-off's commit `5aa0ec5`
(2026-10-21T09:15:44+01:00): AC1's date check. judge-v2 `e90d9d8d8bcb...`; CRITERIA.md
`8c8f973a3306...`; the canary set `4ca54c3ced55...`; the source as before. 49 cases, 147
case-trials; 592 judge calls (19 canaries, 433 verdicts, 140 checks), none unavailable, none
invalid_output, none unable_to_verify; `duration_s` 3380.41. `make
gate` passes after the publish, and the publish, record, judge and cost tests pass (195).

The judged criteria, as the record's report gives them (reported, not gated):

| Metric | Rate | 95% interval | n (cases) |
|---|---|---|---|
| grounded | 0.868 | 0.746 to 0.936 | 49 |
| grounded[answer] | 0.882 | 0.657 to 0.967 | 17 |
| grounded[flag-conflict] | 0.600 | 0.132 to 0.937 | 2 |
| grounded[refuse-and-help] | 0.833 | 0.241 to 0.987 | 2 |
| grounded[abstain] | 0.706 | 0.330 to 0.921 | 6 |
| grounded[retrieval] | 0.923 | 0.740 to 0.981 | 22 |
| grounded_pass^3 | 0.714 | 0.576 to 0.822 | 49 |
| cites_support | 0.839 | 0.621 to 0.943 | 19 |
| cites_support[answer] | 0.882 | 0.657 to 0.967 | 17 |
| cites_support[flag-conflict] | 0.400 | 0.063 to 0.868 | 2 |
| cites_support_pass^3 | 0.684 | 0.460 to 0.846 | 19 |
| correct | 0.419 | 0.237 to 0.626 | 21 |
| correct[answer] | 0.510 | 0.293 to 0.723 | 17 |
| correct[flag-conflict] | 0.000 | 0.000 to 0.658 | 2 |
| correct[refuse-and-help] | 0.000 | 0.000 to 0.658 | 2 |
| correct_pass^3 | 0.286 | 0.138 to 0.500 | 21 |
| relevant | 0.819 | 0.679 to 0.906 | 43 |
| relevant[answer] | 0.824 | 0.590 to 0.938 | 17 |
| relevant[flag-conflict] | 1.000 | 0.342 to 1.000 | 2 |
| relevant[refuse-and-help] | 0.667 | 0.159 to 0.955 | 2 |
| relevant[retrieval] | 0.815 | 0.612 to 0.925 | 22 |
| relevant_pass^3 | 0.674 | 0.525 to 0.795 | 43 |
| abstains | 0.353 | 0.106 to 0.714 | 6 |
| abstains[abstain] | 0.353 | 0.106 to 0.714 | 6 |
| abstains_pass^3 | 0.167 | 0.030 to 0.564 | 6 |
| refuses_and_helps | 1.000 | 0.342 to 1.000 | 2 |
| refuses_and_helps[refuse-and-help] | 1.000 | 0.342 to 1.000 | 2 |
| refuses_and_helps_pass^3 | 1.000 | 0.342 to 1.000 | 2 |
| context_sufficient | 0.619 | 0.409 to 0.792 | 21 |
| context_sufficient[answer] | 0.765 | 0.527 to 0.904 | 17 |
| context_sufficient[flag-conflict] | 0.000 | 0.000 to 0.658 | 2 |
| context_sufficient[refuse-and-help] | 0.000 | 0.000 to 0.658 | 2 |

| Criterion | Cases | Judged | pass | fail | unable_to_verify | invalid_output | unavailable | Quote found | Quote missing | Passages not shown |
|---|---|---|---|---|---|---|---|---|---|---|
| grounded | 49 | 144 | 125 | 19 | 0 | 0 | 0 | 140 | 4 | 0 |
| cites_support | 19 | 56 | 47 | 9 | 0 | 0 | 0 | 49 | 7 | 0 |
| correct | 21 | 62 | 26 | 36 | 0 | 0 | 0 | 54 | 8 | 0 |
| relevant | 43 | 127 | 104 | 23 | 0 | 0 | 0 | 123 | 4 | 0 |
| abstains | 6 | 17 | 6 | 11 | 0 | 0 | 0 | 16 | 1 | 0 |
| refuses_and_helps | 2 | 6 | 6 | 0 | 0 | 0 | 0 | 6 | 0 | 0 |
| context_sufficient | 21 | 21 | 13 | 8 | 0 | 0 | 0 | 0 | 0 | 0 |

The checks on the judge; the two order-check pairs that disagree are again P-01 trial 1 and G-01
trial 1:

| Check | Pairs | Agree |
|---|---|---|
| repeat: grounded | 26 | 26 |
| repeat: cites_support | 18 | 18 |
| repeat: correct | 20 | 20 |
| repeat: relevant | 20 | 20 |
| repeat: abstains | 6 | 6 |
| repeat: refuses_and_helps | 2 | 2 |
| order: grounded reversed | 48 | 46 |

Tokens and time:

| Role | Calls | Prompt | Completion | Unreported |
|---|---|---|---|---|
| generator | 147 | 153210 | 16138 | 0 |
| judge | 433 | 316158 | 51092 | 0 |
| judge_checks | 140 | 115988 | 16691 | 0 |
| canaries | 19 | 14224 | 1688 | 0 |

- Judge calls' latency: p50 5522.768 ms, p95 10373.613 ms (n 592); the run took 3380.41 s.

**Against the first judged record** (`20261020T195341Z-judge-local-dev-25ccc0d`, judge-v1), read
from the two records' lines: only `correct` changed. Seven `correct` verdicts went from fail to
pass (G-01 trial 1, G-08 trials 1 to 3, G-11 trial 2, G-36 trials 1 and 2) and one from pass to
fail (G-06 trial 2). Every verdict of every other criterion is the same, in the first pass, in
the repeats and in the reversed order, as at temperature 0 with the same seed and the same
prompts; `correct`'s repeats changed with its first verdicts (G-01, G-08 and G-36 trial 1: fail to
pass), and the repeat and order agreement counts are the same. `correct` is 0.419 (0.237
to 0.626, n 21), from 0.323. No `correct` fail gives "governing rule" in its reason (0 of 36;
17 of 42 in the first record). G-08 trial 1 ("5 minutes") now passes: "The answer provides the
exact decisive fact (5 minutes) without missing, contradicting, or omitting units or context."
G-06 trial 2 now fails for what it adds: the answer is "Halvenroot SSO asks for MFA again after 12
hours, and also after you sign out and when you sign in from a new device or browser.", and the
reason "The answer includes the decisive fact of the 12-hour MFA re-authentication requirement
from the reference but adds non-decisive facts (sign-out, new device/browser) that are not
contradicted." The rule fails a missing, wrong or contradicted fact, not an added one: the judge
misapplies it there.

**Both records stay published.** The first, under judge-v1 and CRITERIA.md `7e3a522335c7...`, is
history: the evidence for the second sign-off. It still validates, and a re-publish of it would be
refused as stale. THRESHOLDS.md points at the new one, and AC1 and AC7 are met at the new one.

**Caveats on the new record (counted from it and its source; reported, for S6).** Both criteria
read correctly; the judge misapplies them, and S6's human labels calibrate it. No rule changed.

1. **`relevant` fails short right answers.** Of the 23 `relevant` fails, 16 are on answers that
   state a value the answer key writes for the case's labelled section (the position test's code
   check, R-11), and 10 of the 16 are two words long: "64 characters" (R-Q01 trials 1 and 3),
   "45 days" (R-Q02 trial 1), "5 minutes" (R-Q16, all three trials), "2 hours" (R-Q29 trials 1 and
   3), "10 minutes" (G-36 trials 1 and 2). R-Q16 trial 1's reason: "The answer does not address
   the question about the duration before a warehouse floor terminal signs a worker out, nor does
   it state the documents do not provide this information."
2. **`grounded` fails some "the documents don't say" answers.** Of the 19 `grounded` fails, 4 are
   on answers that say the documents do not state the value (a search of the answers for "do not
   say", "do not specify", "not mentioned" and the like, each read): G-26 trials 1 and 3 state no
   value at all ("Mirrowfen's documents do not specify an upper limit on password length."; "No,
   there is no upper limit mentioned in the Mirrowfen Password Standard."), which the first
   sign-off's clause passes, and the judge failed them as stating a value (G-26 trial 1: "The
   answer states a fact (no upper limit) that is not contradicted by any passage, but it also does
   not derive from any stated value or rule in the provided passages."); R-Q04 trial 2 and G-17
   trial 1 also state values, so their fails rest on more than that.

### The position test (phase 2, step 3)

**The generator session.** `make position-local` at `f309594` (the tree clean): one guarded
session, 10:20:02 to 10:25:52 WEST by the shell's clock, exit 0. The preflight, verbatim:
"model: nemotron-3.5-lightning:30b-a3b-mlx at the pinned digest d1e17d7dabac", "memory: 23.1 GiB
available; the model needs 17.8 GiB plus a margin of 4 GiB", "power: the Mac draws from 'AC
Power'". The generator's live contract test passed; then `raglab position` ran the 10 cases at
the three positions x3: 90 calls. The model unloaded, the server stopped, "postcheck passed".

**The record, published:** `runs/published/20261021T092047Z-generation-local-ollama-position-dev-f309594/` (`raglab publish`, exit 0), a generation
record with the `position` case kind, provenance local, `duration_s`
304.355. From its report:

- Status counts: ok 89, refused 0, blocked 1, unavailable 0, invalid_output 0
- Label agreement: 29 of 30 cases gave the same label in every trial
- Latency: p50 1402.959 ms, p95 8431.681 ms (n 90)
- Tokens: 489933 prompt and 9610 completion, from the 90 case-trials whose server reported them

Scored by code (label `answer`, the answering chunk cited, the section's values stated as the
answer key writes them), each position's rate with a Wilson interval at n = cases, and the paired
differences with a seeded bootstrap over cases (2,000 resamples):

| Metric | Rate | 95% interval | n (cases) |
|---|---|---|---|
| position[first] | 0.700 | 0.397 to 0.892 | 10 |
| position[middle] | 0.800 | 0.490 to 0.943 | 10 |
| position[last] | 0.733 | 0.427 to 0.910 | 10 |
| position[middle-first] | 0.100 | 0.000 to 0.200 | 10 |
| position[middle-last] | 0.067 | 0.000 to 0.167 | 10 |

| Case | Fillers | First | Middle | Last |
|---|---|---|---|---|
| G-01 | 43 | 3 of 3 | 3 of 3 | 3 of 3 |
| G-03 | 42 | 2 of 3 | 2 of 3 | 2 of 3 |
| G-05 | 43 | 0 of 3 | 0 of 3 | 0 of 3 |
| G-06 | 48 | 3 of 3 | 3 of 3 | 3 of 3 |
| G-08 | 48 | 3 of 3 | 3 of 3 | 3 of 3 |
| G-09 | 46 | 2 of 3 | 3 of 3 | 3 of 3 |
| G-10 | 38 | 2 of 3 | 3 of 3 | 2 of 3 |
| G-11 | 48 | 3 of 3 | 3 of 3 | 3 of 3 |
| G-12 | 41 | 0 of 3 | 1 of 3 | 0 of 3 |
| G-14 | 17 | 3 of 3 | 3 of 3 | 3 of 3 |

The fillers per case are the counts estimated offline (above). The middle is not the worst
position here: middle minus first is 0.100 and middle minus last 0.067, each interval reaching 0;
on ten cases the intervals are wide, and this is reported, not gated.

**The judge's `correct` on it.** `make judge-local RUN=20261021T092047Z-generation-local-ollama-position-dev-f309594` at `9fa9004` (the tree clean):
one guarded judge session, 10:27:44 to 10:35:07 WEST, exit 0; the preflight said "memory: 32.7
GiB available" and "power: the Mac draws from 'AC Power'"; the judge's live contract test passed
(log `runs/tmp/judge-contract/20261021T092745Z.jsonl`), "canaries: all 19 on their side", "judged
90 case-trials", "postcheck passed". Published: `runs/published/20261021T092819Z-judge-local-dev-9fa9004/` (judge-v2, provenance
local, `duration_s` 407.474). From its report, at n = the 30
position-cases (a case at one position):

| Metric | Rate | 95% interval | n (cases) |
|---|---|---|---|
| correct | 0.708 | 0.529 to 0.839 | 30 |
| correct[position] | 0.708 | 0.529 to 0.839 | 30 |
| correct_pass^3 | 0.433 | 0.274 to 0.608 | 30 |

| Criterion | Cases | Judged | pass | fail | unable_to_verify | invalid_output | unavailable | Quote found | Quote missing | Passages not shown |
|---|---|---|---|---|---|---|---|---|---|---|
| correct | 30 | 89 | 63 | 26 | 0 | 0 | 0 | 84 | 5 | 0 |

The one trial not judged, G-09 at the first position, trial 1, was blocked by the citation guard
(it cited an id that was not retrieved), so its answer was withheld and never judged. By
position, counted from the record's lines: first 20 of 29 judged trials pass, middle 20 of 30,
last 23 of 30. The judge's `correct` and the code's score disagree in places (the code passes
middle most often, the judge last); both are reported. Tokens (from the manifest): judge
89 calls, 43091 prompt and
7981 completion; canaries 19 calls,
14224 and 1688; none unreported. The judge's
latency: p50 3465.03 ms, p95 6335.938 ms (n 108).

### DeepEval's checks (phase 2, step 4)

`make deepeval-check JUDGED=20261021T081852Z-judge-local-dev-5aa0ec5` at `826ab69`: one guarded
judge session, 10:38:01 to 10:43:10 WEST, **exit 2**. The preflight said "memory: 29.1 GiB
available" and "power: the Mac draws from 'AC Power'"; the judge's live contract test passed (log
`runs/tmp/judge-contract/20261021T093802Z.jsonl`); "canaries: all 19 on their side"; then
`tools/deepeval-check`, which wrote `runs/tmp/deepeval-check/20261021T094309Z.json` and exited 1
because a check could not run; the model unloaded, the server stopped, "postcheck passed". From
that file:

- DeepEval `4.3.1`; `DEEPEVAL_TELEMETRY_OPT_OUT` `1`, set before the import
  (`opted_out_before_import`: true); the loopback-only guard caught **0** attempts.
- **The custom-LLM API:** called with a schema, `RaglabJudgeLLM` returned an instance of it
  (`Probe`, `is_instance` true); 1 call, 586 prompt and 26 completion tokens.
- **The metric canary** (`FaithfulnessMetric`, eval mode `llm`, on C-03, the honest twin, and
  C-01, the invented answer, with `penalize_ambiguous_claims` off and on): all four scores **0.0**,
  none passing the default threshold of 0.5, 4 calls each (16 calls, 16,856 prompt and 1,974
  completion tokens, every reply fitting its schema). The tool's automatic reading, "only
  supported claims count: the invented value failed", is not what the run supports: the honest
  twin, which states no value, also scored 0.0, so the canary separated nothing.
- **The hallucination direction** (`HallucinationMetric` with G-01's labelled passage): the
  consistent output **0.0** and the contradicting output **0.0**, "undecided: both outputs scored
  the same"; neither passes the default threshold (`is_successful()` false at 0.0), so 4.3.1
  treats the threshold as a minimum, as the page read on 2026-10-20 says ("Higher is better"). 4
  calls, 3,802 prompt and 288 completion tokens, every reply fitting its schema.
- **The cross-check did not run.** Its first `FaithfulnessMetric` call asked for DeepEval's
  `Truths` schema over a case's five passages; the reply was cut off ("ValidationError: 1
  validation error for Truths / Invalid JSON: EOF while parsing a string at line 20 column 95"),
  at the judge config's cap of 512 output tokens. The wrapper never repairs a reply, so DeepEval
  raised and the check reported it. 5 calls, 5,687 prompt and 1,195 completion tokens, 1 off the
  schema.

Why every score was 0.0 is not known: the check records each metric's score and calls, not
DeepEval's intermediate claims, truths and verdicts. Recorded in docs/COMPATIBILITY.md and here,
not in CRITERIA.md (the deviation from AC11's wording, above). **For the orchestrator, not done:**
a second DeepEval session with a larger output cap for DeepEval's calls (the wrapper's requests,
not the own judge's) and the metrics' intermediate verdicts recorded would let the cross-check run
and might explain the zeros, at about 30 minutes of Mac time; or the cross-check is cut, the
plan's first cut, and AC11 stays partly met.

### `raglab cost` and ADR-002 (phase 2, step 5)

The price pages were read again on 2026-10-21 for the ADR: Anthropic's pricing page (Claude Haiku
5.5 for prompts up to 100,000 tokens $0.10 and $0.50, batch $0.05 and $0.25; Sonnet 5.5 $2 and
$10, batch $1 and $5; Opus 5.5 $4 and $20, batch $2 and $10; Haiku 4.5 $1 and $5, batch $0.50 and
$2.50), Claude Haiku 5.5's overview (the model id `claude-haiku-5-5`; the tokenizer sentence
quoted in the ADR; "Omit `temperature`, `top_p`, and `top_k`"), and OpenAI's pricing page
(gpt-5-nano $0.05 and $0.40, batch $0.025 and $0.20; gpt-5-mini $0.25 and $2.00, batch $0.125 and
$1.00; gpt-6-luna up to 272K input tokens $0.10 and $0.50, batch $0.05 and $0.25). Every row was
unchanged, so `config/prices.toml` keeps its prices and its read dates became 2026-10-21
(`f27238d`).

`raglab cost` now names its inputs relative to the repository (`3b31621`), so its output is the
same on any machine, and prints each role's tokens per case-trial (`f27238d`), which AC12 asks
for. `make cost JUDGED=20261021T081852Z-judge-local-dev-5aa0ec5` (exit 0) is quoted word for word
in docs/decisions/ADR-002-providers.md (`91a9a16`), and THRESHOLDS.md copies its tokens per
case-trial by role and the monthly estimate per option (each of their 32 numbers checked against
the output), with Q-01's local p50 and p95 from the consistency baseline's record (1510.180 ms,
2743.227 ms, n 147) and the judge's per call from the judged baseline's (5522.768 ms, 10373.613
ms, n 592). The monthly estimate per option: local only $0.0000; the local generator with a Claude
Haiku 5.5 judge $1.21, a gpt-5-mini judge $3.83, a Claude Sonnet 5.5 judge $24.21; Claude Haiku
5.5 with a gpt-5-mini judge $4.60; gpt-5-mini with a Claude Haiku 5.5 judge $3.53.

The ADR's recommendation: the local generator with a Claude Haiku 5.5 judge, the local judge kept
for offline work and as the fallback; local only stays a sound choice if S6 should calibrate the
local judge first. Its decision section waits for D6. `tests/unit/test_adr.py` renders `raglab
cost`'s output again from the committed record, table and assumptions and finds it in the ADR.
**AC13's break:** the Haiku 5.5 option's monthly cost edited by hand in the ADR, from $1.21 to
$0.99: the test failed ("ADR-002's estimate is not raglab cost's output: run make cost and copy
it word for word"); restored from git: 2 passed.

**Mac time, phase 2:** the sessions ran 2026-10-20 20:42 to 22:34 (judged run 1, with the 36.5
minutes of hibernation) and 2026-10-21 09:16 to 10:43 (the judge-v2 canaries, the judged run 2,
the position test's two sessions and DeepEval's): about 3 hours 20 minutes of wall-clock time in
all, under the plan's 4 hours.

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

- **`make audit` turned red on 2026-10-20 between 20:49 and 22:50 WEST, with no change of ours:**
  new advisories against two locked packages of the main project. `pip-audit` found 9: certifi
  2026.7.22 (GHSA-6q48-6c7w-9gw2, fixed in 2026.10.19; it comes in through httpx and requests)
  and pillow 12.3.0 (eight CVEs, fixed in 13.0.0, a major version; it comes in through fastembed
  and pytesseract, and fpdf2 and the dev group). Every other step of `make -k check` passed (1307
  tests, the gate, the API smoke test). Bumping them is a dependency change for the user or a
  Dependabot pull request, not part of this stage; until then pr-fast's audit fails too, and the
  bump needs the tool's re-lock (next note).
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
