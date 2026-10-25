---
stage: S7
nodes: [S7]
---

# S7 ledger: attack, guardrails and red team

Plan: [2026-10-23-s7-attack-guardrails.md](2026-10-23-s7-attack-guardrails.md). Branch
`feat/s7-attack-guardrails`, cut from `main` at `2b9ba60` (answer-v2's merge); the plan's commit is
`bfbe6ec`. One ledger in two parts (the plan's choice 13): Part S7a now, Part S7b after S6.

## Approval and decisions

The go for the draft (2026-10-23, about 22:45 WEST), verbatim (quoted in the plan): "S6 planner
(Recommended), S7 planner (Recommended), S9 planner", the answer to "Which planners should I launch
now, next to S4b's? Each writes its plan only, in its own worktree, and stops for your approval.",
after the question "can we launch more sub agents in parallel to that one to speed up the
development phase for upcoming steps into the plan?".

The approval (2026-10-23, about 23:30 WEST), verbatim (quoted in the plan's Approval). The question:
"S7, attack, guardrails and red team. Approve with all five recommended answers? D1: split into S7a
now (threat model, rule-layer guards, attack suite, block and must-not-block suites, 10–20 min of
Mac) and S7b after S6 (promptfoo red team, Guardrails AI). D2: no corpus change; new attack inputs
go in a separate security pack. D3: the new guards are on by default, proven to change nothing by
replaying S4b's v2 runs. D4: no sign-up, so Prompt Guard 2 is not covered. D5: approve and start.
Your time is about 3.5–5 h over both parts." The answer: "All five as recommended (Recommended)".

The answer selects each decision's recommended option:

| Decision | Option chosen (the plan's label) | What it means for the build |
|---|---|---|
| D1 Scope | "Split: S7a now, S7b after S6 (Recommended)" | S7a (threat model, rule layer, deterministic attack suite, suites per filter, the live attack runs) is built now; S7b (promptfoo, Guardrails AI) after S6 merges; two pull requests under the one node S7 |
| D2 The attack material and the corpus | "No corpus change; a separate security pack (Recommended)" | no change to the register, the clean inventory or the answer key; new inputs in `datasets/security/` |
| D3 The new guards and the v2 baselines | "On by default, proven inert by replay (Recommended)" | the layers join `default_guards()`; the guard set joins the staleness rule; a committed replay with zero events keeps the baseline current |
| D4 Sign-ups | "No sign-up; Prompt Guard not covered (Recommended)" | THREAT-MODEL.md lists Llama Prompt Guard 2 as not covered |
| D5 This plan | "Approve and start (Recommended)" | S7a's build starts on this branch |

## Part S7a

### What was built (developer, offline, 2026-10-23 to 2026-10-24)

The offline build stops at STOP 1: no live session was started. Everything that needs S4b's merge
(AG5's v2 questions, AG10's v2 replay, TEST-PLAN's shared rows) or the maintainer's go (AG9) waits.

| Part | Where |
|---|---|
| The port (D3; the plan's "a drop-chunk step after retrieval, or a port method: the developer chooses") | **A port method.** `Guardrail.drop_retrieved(tenant, retrieved)` returns the chunks kept and an event per document left out; `NoopGuardrail` keeps everything. `check_output` now receives the retrieved chunks the prompt was built from (it received their ids), so an output guard sees their statuses. `fingerprint()` is the sha256 of a layer's rules. `src/raglab/core/ports.py`, `src/raglab/guard/noop.py`, `src/raglab/generate/pipeline.py` (drop steps after the retrieved checks; the kept chunks are handed on explicitly; `Outcome.dropped`) |
| Register filter (AG2) | `src/raglab/guard/register_filter.py`: keeps a chunk only when its status is one the register gives (approved, superseded, reference); the event names the document id and the rule `register-membership` |
| Instruction scan (AG3, arrow L9) | `src/raglab/ingest/scan.py`: three rule groups (addressed, change, send), flagged at two; `src/raglab/generate/assemble.py` scans the inventory (and an attack run's pages) before indexing; the inventory is not changed. Its rules are the first layer of the recorded guard set |
| Input injection detector (AG5) | `src/raglab/guard/injection.py`: instruction to the assistant (the scan's strong change and send rules), dressed as a system message, reveal the prompt or configuration |
| Output guards (AG4) | `src/raglab/guard/links.py`, `src/raglab/guard/disclosure.py` (secrets and personal details, arrow R8), `src/raglab/guard/prompt_leak.py` (N = 8), `src/raglab/guard/citations.py` (extended; `register=False` is S3's validator for the defences-off set), `src/raglab/ingest/trusted.py` (the register's links and SPEC section 6's team contacts) |
| Guard set and default guards | `src/raglab/guard/__init__.py`: `default_guards(root, register_chunks)` in the order tenant, input limits, injection, register, citations, links, secrets-pii, prompt-leak; `s3_guards()`; `guard_set()`; generation and position manifests record `guard_set` (schema extended additively) |
| API reasons (S9's tracing rule) | `src/raglab/api/app.py`: a key in `REASONS` per guard (`GUARD_REASONS`: injection, register, links, secrets_pii, prompt_leak; citations stays "blocked"); a refused request answers with its guard's reason (injection: 400); the log records guard, stage and key only, never a guard's text |
| Attack pages' exposure | `src/raglab/ingest/attacks.py`: title = the page's own first heading, kind `unregistered`; the front matter's title, kind, status and test_material are never read |
| Egress guard (AG8) | `src/raglab/runtime/egress.py`, re-implemented after the pattern of `tools/deepeval-check`'s guard |
| Security pack (AG6, D2) | `datasets/security/`: README and ten YAML files, 57 must-block, 57 must-not-block and 13 attack cases; `src/raglab/ingest/security_pack.py` (loader, references, schema check) |
| Suites per filter (AG6) | `src/raglab/evals/guard_suites.py`, `raglab guard-suites`, `make guard-suites`; record `runs/guard-suites/20261024T030214Z-ebcdb7d.json` |
| Replay and staleness (AG10's mechanism) | `src/raglab/evals/replay.py`, `raglab replay`, `make replay`; record `runs/replays/20261019T172035Z-generation-local-ollama-dev-97011a7--d81cec18f099.json` |
| Tests | `tests/security/` (`test_attack_suite.py`, `test_guard_cases.py`, `test_security_pack.py`, `test_instruction_scan.py`, `test_egress_guard.py`, `test_guard_reasons.py`, `test_guard_staleness.py`, `test_threat_model.py`) and `tests/security_support.py`, marker `security` (in `make test`) |
| Docs | `docs/THREAT-MODEL.md` (new); `docs/GUARDRAILS.md` (S7a's layers); `docs/THRESHOLDS.md` (Guards); `docs/TEST-PLAN.md` (arrows L9 and R8 only); the main plan (dated note, D1 and D3); README (a paragraph); Makefile (`guard-suites`, `replay`); CHANGELOG |

Commits (on `bfbe6ec`): `4ed82dc` approval and ledger; `a769e92` the rule layer; `7e0d76e` the pack,
the suites runner and the replay; `39884e4` the attack suite, guard cases and threat model; `ebcdb7d`
the staleness test and the replay record; `fdd625c` the guard-suites record; `82a7a81` docs;
`0d9fbc0` TEST-PLAN arrows; `b2c60b1` vulture fix; `7b60223`, `6a858fc`, `6e99c2c` test fixes from
the breaks (below).

### Before the rules were fixed: dry checks on must-not-block data

Run once, read only, from the scratchpad, before any rule was committed (dev data only; no
test-split question and no release run was read):

- the instruction scan over the 228 clean chunks: 0 flagged, and no clean chunk matches even one
  rule group; over the 24 attack-page chunks: one flagged, `T-HIDDEN@1.0/5/1` (all three groups);
- the injection detector over the golden set's 49 dev questions (v1.1): 0 refused;
- the citation, link, secrets and personal-details and prompt-leak guards over the 1,625 answered
  (status ok) case lines of every published dev generation run (the S3 run, the v1.1 baseline and
  its repeats, answer-v2's five runs, the position run): 0 events. The longest run of words any of
  them shares with the system prompt is 6 (one answer); 93 share 5.

**N for the prompt-leak guard, set from the prompt text alone** (before the dry check above): the
longest run of words the system prompt repeats inside itself is 5 ("a passage with status
reference", "... superseded"), so every run of 6 or more is the prompt's own; the longest run a
correct answer may share with it is the abstain label's own description, "the passages do not
state the answer", 7 words; so N = 8. The phrase the prompt tells the model to say ("the company's
documents do not say") is taken out before runs are counted.

### Evidence per criterion

Each break was made on committed files with `PYTHONDONTWRITEBYTECODE=1` by a scratch driver that
wrote the files' committed bytes back afterwards; `git status --short` was empty and
`git diff --quiet HEAD` true after every group (the store-filter break was restored with
`git checkout`). The security suites alone (`tests/security/`): 258 tests, 6.81 s.

| AG | Status | Evidence | Break (restored) |
|---|---|---|---|
| AG1 | met (review pending) | `docs/THREAT-MODEL.md`: the data flow with six trust boundaries; one row per LLM01:2026 to LLM10:2026 (ids and titles, linked, no OWASP text), each naming tests or "not applicable, because" (LLM03); LLM09:2026 named as the build project's LLM08:2025; the lethal trifecta (exfiltration path: none); the attack table; what an attack run exposes; the not-covered list (non-English and encodings, Prompt Guard 2, garak, Petri, attacks needing a new document, promptfoo's remote-only plugins, how-to 07's verbatim and state_invariant kinds, sockets outside Python). `tests/security/test_threat_model.py` (4 tests) | LLM10's test renamed: "LLM10:2026: tests/security/test_egress_guard.py::test_the_page_is_safe does not exist"; LLM06's row deleted: "LLM06:2026: no row"; both restored, green |
| AG2 | met | `tests/security/test_attack_suite.py`: the T-POISON, T-FAKE, T-HIDDEN and claimed-id rows (negative control, each defence alone, the default set); a page outside the register never reaches the prompt and the answer goes on, the drop event names T-POISON and `register-membership`; the claimed-id page (front matter: A-PWD-V2, `current`) is dropped; `tests/security/test_guard_cases.py`: the 228 clean chunks all kept, the 24 attack-page chunks all left out | The filter keeps `unregistered` chunks: 10 failed, among them "poisoned duplicate (F-48): ATK-F48-1: with only the register layer the attack lands" and the F-47 and F-49 rows' register checks; the filter reads front matter status (the loader passes it and the filter takes `current`): 4 failed, the claimed-id row's register checks ("poisoned duplicate (F-48) claiming a register id: ATK-F48-1: with only the register layer the attack lands") and the two claimed-id tests. No negative control failed (expected pass) |
| AG3 | met | `tests/security/test_instruction_scan.py` (5 tests: T-HIDDEN's note quarantined as a page outside the register and inside a temporary register, `A-WIFI@1.0/5/1`; the event names the chunk and groups, never the text; the clean pack keeps its 228 chunks and its corpus sha256; `assemble` indexes what the scan keeps); `tests/ingestion/test_inventory_snapshot.py` passes unchanged; `make gate` passes (recall@5 0.682, the baseline's) | The scan's rule removed (`NEEDS = 4`): 7 failed, among them "planted instruction (F-47) inside a registered document: ATK-F47-1: with only the instruction-scan layer the attack lands: [F-47's planted string is in the answer, x3]"; a rule widened (`passwords` addressed, `must` a change): "instruction-scan: flags the clean chunks ['A-PWD-V1@1.0/4/1', ...]" naming 11 chunk ids |
| AG4 | met | Each guard's cases in `tests/security/test_guard_cases.py`; each defence alone in the attack suite; `test_the_published_team_contacts_are_still_answered` (F-46's SOC contacts, the Service Desk's, Mirrowfen IT Support's); `test_no_event_holds_what_its_guard_removed` (every event of every row and configuration against every `answer_must_not_contain` string, link forms included, and the sentences of the removed pages and the system prompt); `tests/security/test_guard_reasons.py` (the log holds guard, stage and key only) | Each disabled in turn: links 10 failed (LNK-B01 to B06; "with only the links layer" for F-47 registered and F-49); secrets-pii 15 failed (SPI-B01 to B08; F-44, F-45, F-47, F-49 rows); prompt-leak 9 failed (PLK-B01 to B06; the three R-20 cases); the citation validator's register rule 11 failed (CIT-B03 to B05; F-47 page, F-48, F-49 rows). The link guard's event made to quote the links: 3 failed, "fake update page (F-49): ATK-F49-1: an event quotes removed text" (see Findings: the first version of the test missed it) |
| AG5 | met: on v1.1, and on golden set v2's dev questions after the merge with main (below) | `tests/security/test_guard_cases.py`: INJ-B01 to B10 refused, INJ-N01 to N10 answered, `test_no_dev_question_of_the_golden_set_is_refused[injection]` over the 49 dev questions of the file `config/local-ollama.toml` names (v1.1 now; v2 after S4b switches the config), split dev only (asserted) | A rule widened (the word `password`): "injection: refuses the dev questions ['R-Q01', 'R-Q04', ...]" (15 ids) and INJ-N02, N04, N05, N06; the `system prompt` rule removed: "injection: INJ-B06 (must_block) was let through" |
| AG6 | met offline, ratified (2026-10-24, below); the pr-fast log needs CI | Ten YAML files in how-to 07's template; `tests/security/test_security_pack.py` (18 tests: the template, five or more of each kind per layer, every attack row has cases, the README labels the pack deliberate test material, references resolve and no planted value is written); every case binary per build; THRESHOLDS.md's Guards section from `runs/guard-suites/20261024T030214Z-ebcdb7d.json`; every `ratified_by` was `pending` at STOP 1 and is `maintainer, 2026-10-24` since the ratification | LNK-N01's expected flipped to block: "datasets/security/links.yaml LNK-N01: a must_not_block case expects 'pass'"; TEN-B01's `ratified_by` emptied: "... TEN-B01: ratified_by is empty or not 'maintainer <date>'"; `{ref:F-99:0}`: "... SPI-B01: {ref:F-99:0} names no answer_must_not_contain string" |
| AG7 | met locally; needs CI | `tests/security/test_attack_suite.py`, 97 tests, about 5 s: 7 rows x their cases x (negative control, each defence alone, default set), the payload-reaches-the-answer control under S3's guards, two tenants (a broken store filter without the tenant guard leaks a canary; the filter alone and the guard alone each hold), tenant spoofing (403, never retrieved; 200 and retrieved without the guard), no conflict field outside the register (in every check) | Each defence removed in turn: register (AG2), citations, links, secrets-pii, prompt-leak (AG4), scan (AG3), injection: 3 failed ("prompt extraction (R-20): ATK-R20-1: with only the injection layer the attack lands"), tenant guard: 3 failed ("two tenants: ATK-TEN-1: the tenant guard", the 403 test). No negative control failed in any break. The store's pre-ranking filter removed: its second line (`check_visible`) raised TenantError on 7 of the 8 two-tenant tests (the store fails closed) |
| AG8 | met (the live runs' egress record waits for AG9) | `tests/security/test_egress_guard.py` (5 tests: refused and recorded off loopback, lookups too, loopback passes through, removed after, the page and the playground write text only); every attack-suite test runs inside the guard (`egress_none` asserts `egress: none`); the adapter's rule is `tests/contract/test_chat_contract.py::test_a_server_that_is_not_local_is_refused` | A lookup of 192.0.2.1 planted in an attack-suite test, its OSError swallowed: the test itself passed and the fixture failed it, "egress: lookup 192.0.2.1:80"; `innerHTML` planted in `src/raglab/web/app.js`: "src/raglab/web/app.js writes HTML" and `tests/api/test_page.py` both failed |
| AG9 | offline parts met (after STOP 1, below); the live runs wait for the maintainer's go, after S4b's merge and the ratification | See "AG9's offline parts" below: the runner, suite `attack` in run record v1, `config/attack-local.toml` and `config/attack-fake.toml`, `make attack-local`, F-49's label from the answer key per configuration, publish's rules; `tests/security/test_attack_runs.py` (17 tests). No live session was started | AG9's offline break (a defences-on copy with an F-47 string planted, resealed, still valid): `raglab publish` refuses it naming F-47's string (`test_publish_refuses_a_defences_on_copy_with_an_f47_string_planted`); five more breaks below |
| AG10 | met: the replay over golden set v2's consistency baseline and its four repeats shows zero events (after the merge, below) | `raglab replay` over the current baseline and its four repeats: 735 case lines, 730 answers, 3,675 retrieved chunks, zero events, record `runs/replays/...--d81cec18f099.json` (made from a clean tree at `39884e4`). `tests/security/test_guard_staleness.py` (5 tests): the baseline is current for today's guard set only through that record; a new set without a record is stale naming it; an edited manifest is refused; a recorded answer given a foreign link is an event and no record is written. The guard-set rule lives in its own file, not in `tests/retrieval/test_publish.py`, which the plan's merge order keeps until S4b merges. `git diff 2b9ba60 -- config src/raglab/generate/prompts corpus` is empty | Tested in the suite on copies (a new set without a record: stale, naming the set; one answer given a foreign link: "links at output", no record). After the merge, on the committed `default_guards()`: a no-op layer added fails the staleness test naming the guard set (below) |
| AG11 | met: GUARDRAILS.md; TEST-PLAN's arrows L9 and R8, and after the merge the Test and Gate cells of R-15 to R-17 and R-19 to R-21, the gaps R-20 and R-21, section 10's security line and the test_test_plan extension (below) | GUARDRAILS.md: each S7a layer with its stage, owner, action, code and tests; TEST-PLAN L9 and R8 name their tests and pr-fast (`tests/unit/test_test_plan.py`'s arrows test checks each exists) | L9's test renamed: "L9: tests/security/test_instruction_scan.py::test_the_planted_instruction_is_flagged does not exist" |
| AG12 | partly: THREAT-MODEL, GUARDRAILS, THRESHOLDS, README, the main plan's note, the pack's README and the CHANGELOG are done; LOCAL-MODEL's attack-local row has its command and waits for AG9's time; ARCHITECTURE and README `wip` wait for S6's status line (S4b's landed with the merge; the plan's merge order) | `test_diagram.py`, `test_readme.py`, `test_repo_docs.py`, `test_changelog_check.py`, `test_test_plan.py` pass | ARCHITECTURE's S7 class made `wip` without the README's: `test_readme_status_matches_architecture` failed |
| AG13 | met locally; pr-fast's duration before and after needs CI | No dependency change (`git diff 2b9ba60 -- pyproject.toml uv.lock` empty); `raglab.core` standard library only and the vendor rules hold (`make architecture`: 0 violations); `make -k check` below | A planted unused import in `src/raglab/guard/links.py`: `make check` stopped at lint (`F401`); `import httpx` there: `make architecture`, "src/raglab/guard/links.py:17: vendor SDK httpx is imported outside raglab.adapters" |

### Findings from the breaks (fixed in the build)

- **AG3's break exposed a fragile negative control** (`6a858fc`). With the scan's rule removed, row
  1's negative control (register filter and citation validator removed) no longer landed: the link
  and secrets guards withheld the answer that the scan had been keeping clean of the note. The
  negative control now also removes the layers that stop part of the attack (`also`), so it lands
  whatever state they are in.
- **AG4's quoting break was first missed** (`6e99c2c`). The link guard reads a link without its
  scheme, the answer key writes it with one, so an event quoting the withheld link passed the first
  version of the quoting test. Planted links are now matched in both forms, as are the removed
  pages' links.
- **The link guard is a second layer inside a registered document only through the scan's rules.**
  Its allowlist leaves out the links of a passage the scan's rules flag, so a link planted in a
  registered document never becomes "the register's"; with the scan's rule removed, the link guard
  lets the planted link through in that fixture too (the secrets guard still stops it, on the
  canary token). Documented in GUARDRAILS.md and THREAT-MODEL.md; a reviewed link list independent
  of document text would remove the coupling (a product choice, below).

### Developer choices (for the review)

1. **Port methods, not a pipeline special case:** `drop_retrieved`, `check_output(answer,
   retrieved)` and `fingerprint()` on the port; pipeline.py's diff is small and local (S9 adds spans
   there).
2. **The register filter reads the chunk's status**, which only ingestion (from the register) or
   the attack loader (`unregistered`) sets; the front matter is never read. A page claiming
   A-PWD-V2 keeps the claimed id and is still dropped.
3. **The scan runs where the index is built** (`assemble`), never inside `ingest()`, so the
   inventory and its snapshot cannot change; it runs on clean runs too, inert.
4. **What an attack run exposes:** the page's own first heading as its title and `unregistered`
   as its kind, so the live defences-off run does not show the model a "test material" label.
5. **Planted and personal values in the pack:** by reference only; the only addresses written are
   the two `privacy/allowlist.txt` keeps for tests, tokens use the `FAKE-` shape without a
   letters-digits run the privacy patterns flag, phone numbers are in fictional ranges.
6. **The API:** a refused injection answers with its own reason; a withheld answer still says
   "blocked" whichever output guard withheld it (no hint to an attacker which rule fired); the log
   line is the guard, its stage and its key.
7. **The attack suite uses BM25 and the echo model** (no embedder, the same ranks on any machine);
   five attack questions were reworded so BM25 reaches their pages (the pack's final wording is
   what is committed and what the live run will ask).
8. **The replay record and the staleness rule are exercised on the v1.1 baseline now**, so `make
   check` is green at STOP 1; after S4b merges the replay runs on v2's five runs and the v1.1 record
   becomes history.

### Decisions needed (the safest reversible default was applied)

- **The link allowlist.** Applied: the register's links minus those in passages the scan's rules
  flag. Alternative: a committed, reviewed link list (production's link policy), independent of
  document text. Either keeps every check green; the alternative makes the link guard independent
  of the scan inside registered documents. **Decided 2026-10-24: kept as built**, with the
  ratification below ("the link guard keeps its current behaviour inside registered documents").

### The pack for ratification

Every handwritten case, grouped by layer with its id, input (references as written), expected
decision and reason, went to the maintainer's review page from the scratchpad's
`s7-dev/ratify.md` at `98061e3`:
tenant 5 + 5, input limits 6 + 5, injection 10 + 10, register 5 + 5, instruction scan 6 + 7,
citations 5 + 5, links 6 + 6, secrets and personal details 8 + 8, prompt leak 6 + 6
(must-block + must-not-block: 57 + 57), and 13 attack cases.

### The ratification (2026-10-24, about 09:55 WEST)

The maintainer's message, verbatim: "ok". Asked through the question prompt, verbatim: "And
S7a's 127 security cases? Its ratification page has no marks yet." The answer, verbatim: "Ratify
all as written". That option's description, verbatim: "Every case is ratified as the developer
wrote it, and the link guard keeps its current behaviour inside registered documents."

**The maintainer ratified without marking any case on the review page**
(https://claude.ai/artifact/Pt2t5SWxutJhKYdGS46myJ, built from `ratify.md` at `98061e3`): the
page has no marks, and the ratification is the answer above, for all 127 cases at once.

What was done: `ratified_by` is `maintainer, 2026-10-24` on all 127 cases (57 must-block, 57
must-not-block, 13 attack cases), by role and date, never a name; the pack's files are otherwise
the ones the page showed (`git diff 98061e3 -- datasets/security` was empty before this edit).
The pack's schema check now takes `maintainer, <date>`, and
`tests/security/test_security_pack.py::test_every_committed_case_is_ratified_by_role_and_date`
holds the committed pack to it: no case pending. The link-guard decision: kept as built (above).
The security tests were not run with this edit while S4b's live sessions had the Mac. Run once
when it was free (2026-10-24, 13:17 WEST, on `a54dd58`, `/usr/bin/time -p`):
`pytest -m "not live and not judged and not guardrails and not perf" tests/security`, 276 passed
in 43.61 s (`real 43.91`), the new ratification test among them; exit 0, the tree clean after.

### Runs S7a made

| Record | What | Made by |
|---|---|---|
| `runs/replays/20261019T172035Z-generation-local-ollama-dev-97011a7--d81cec18f099.json` | `raglab replay`, today's guard set over the v1.1 baseline and its four repeats, no model: zero events | developer, clean tree at `39884e4` (committed in `ebcdb7d`) |
| `runs/guard-suites/20261024T030214Z-ebcdb7d.json` | `raglab guard-suites`, every layer over its suites, dev split, provenance local: no miss, no false block | developer, clean tree at `ebcdb7d` (committed in `fdd625c`) |
| `runs/replays/20261024T090351Z-generation-local-ollama-dev-ade9397--d81cec18f099.json` | `raglab replay` over golden set v2's baseline and its four repeats, after the merge with main: zero events | developer, clean tree at `a8d94d9` (committed in `5c4d409`) |
| `runs/guard-suites/20261025T181249Z-5c4d409.json` | `raglab guard-suites` on golden set v2's data, after the merge: no miss, no false block | developer, clean tree at `5c4d409` (committed in `b406a44`) |

No generation, retrieval or judged run was made, and no live session was started.

### `make -k check` at STOP 1 (`a5d6e18`, macOS arm64, `/usr/bin/time -p`)

Every target passes but `audit`, whose failure is pre-existing on `main` (advisories published on
2026-10-23; fixed in a separate pull request; `AUDIT_SKIP` untouched):

| Target | Result |
|---|---|
| format, lint, types | 274 files already formatted; ruff "All checks passed!"; pyright 0 errors |
| deps | deptry "No dependency issues found"; vulture silent |
| audit | **red, pre-existing:** "Found 8 known vulnerabilities, ignored 43 in 3 packages": filelock 4.0.12, three advisories (fixed in 4.2.1); pillow 12.3.0, two (13.0.0); pypdf 6.19.0, three (6.21.2), as pip-audit names them by their CVE ids |
| sast, workflows | bandit and semgrep silent; zizmor "No findings to report" |
| secrets, privacy | gitleaks "no leaks found" (directory and history); "0 hits across 402 files (42 rules)" |
| architecture, check-dataset, model | 0 violations; golden.v1.jsonl passes; the embedder already in the cache |
| test | 1627 passed, 2 deselected in 172.21 s |
| gate | recall@5 0.682 (n 22) passes against the baseline 0.682 minus one question, 0.636 |
| api-smoke | passed |

`real 215.27`, `user 199.55`, `sys 14.98`. The first run at STOP 1 (`0d9fbc0`) had `deps` red too
(vulture: the egress guard's unused `__exit__` arguments), fixed in `b2c60b1`; it took 210.41 s with
1613 tests. pr-fast's check-job time before and after this pull request is [CI].

### AG9's offline parts (after STOP 1, 2026-10-24)

The coordinator's message after STOP 1, verbatim: "Next, build AG9's offline parts now: the
runner, the suite's `attack` record, `config/attack-local.toml`, `make attack-local`, and the
`Feature` field for F-49's attack-run label. Test them on the fake model, with the plan's breaks."
No live session was started: `make attack-local` waits for the maintainer's go, after S4b's merge
and the ratification.

| Part | Where |
|---|---|
| The runner | `src/raglab/evals/attack.py`: `raglab eval --suite attack --config <c> --defences on\|off` asks the pack's 13 attack cases N times with the corpus's three attack pages (24 chunks) indexed in tenant A as pages outside the register; defences off is S3's guard set (the citation validator without S7's register rule) and no instruction scan (`assemble(..., scan_index=False)`), defences on S7a's guard set and the scan. The pack's schema check stops the run first. The assembly and the run sit inside the loopback-only egress guard, whose summary the record keeps; the command exits 1 when a defences-on trial fails a safety check or anything left loopback (`attack.unsafe`) |
| The record | Suite `attack` in run record v1 (`schemas/run-record.v1.json`, additive; `src/raglab/evals/attack_record.py`): the manifest's `attack` block (configuration, pages, quarantined chunks, egress) and `results.attack`; each line's kind `attack`, its attack row, `expected_label`, each retrieved chunk's status and four safety checks (no planted string of any feature, citations and conflict ids inside the register only, no canary of the other tenant, no run of the system prompt), recomputed by `record.validate`, which also checks each chunk's status against the register, the expected label against the answer key, and each case against the pack's current bytes. The report shows ids, labels, statuses and checks, never answer text |
| F-49's label | `answer_key.Feature.expected_in_attack_runs` (F-49: `refuse-and-help`); `attack_record.expected_label`: that label with defences off (the page reaches the model), the clean `answer` with defences on; none for a case without features |
| Configs | `config/attack-local.toml` (the consistency gate's chunker, embedder, retriever, model tag and digest, sampling and seed; 3 trials); `config/attack-fake.toml` (the fake echo model); no existing config changed |
| make | `make attack-local`: one generator session, the live contract test, then `--defences off`, then `--defences on` |
| Publish | refuses an attack run made with the defences off and one whose egress guard saw an attempt; every attack run is held to every planted string (`CLEAN_SUITES`, unchanged) |
| Gates | `raglab gate` refuses an attack config (exit 2) |

Commits: `cb32bde` (the runner, the record, configs, make target, the Feature field, publish),
`1aa2ce1` (the egress test).

**Tests** (`tests/security/test_attack_runs.py`, 17 tests, 35 s): defences on through the CLI on
the fake model (exit 0, the record valid, every case safe, `T-HIDDEN@1.0/5/1` quarantined, egress
none, F-49 expected `answer`); defences off with the stub server that echoes (the record valid,
F-49 expected `refuse-and-help`, unregistered chunks retrieved, cases failed: the attack lands, and
the command's gate does not fail on it); a local-provenance defences-on record publishes into a
copy of the tree; publish refuses the planted copy (AG9's break), a defences-off run and an egress
attempt; six forged records are refused (an expected label, a check, a chunk's status, an
unretrieved citation, a question, the configuration); an attempt off loopback during a run is
recorded and fails its gate; F-49's label per configuration; the configs; the gate's refusal; the
make target's recipe.

**Breaks** (each restored, `git diff --quiet HEAD` true after):

| Break | Result |
|---|---|
| AG9's own: publish no longer holds an attack run to the planted strings | 1 failed: the planted copy, "DID NOT RAISE PublishError" |
| Publish's refusal of a defences-off run removed | 1 failed: publish still refused the run, on its planted strings, not on the configuration |
| F-49's attack-run label ignored | 2 failed: the defences-off record and the label test |
| The configurations swapped (defences on built with S3's guards) | 7 failed, among them the defences-on run and the publish tests |
| validate no longer checks an attack record's own rules | 6 failed: the six forged records |

**Note for the coordinator:** the command guard refuses any shell command holding the word `eval`
(`raglab eval ...`), so these runs were made in process, through `raglab.__main__.main` in the
tests and `attack.run` in a fixture; `make -n attack-local` prints the recipe. The live session
will run the same commands through `make attack-local`.

**`make -k check` at `a20e7fb`** (`/usr/bin/time -p`): every target passes but `audit`, the same
pre-existing advisories as at STOP 1 (filelock 4.0.12, three; pillow 12.3.0, two; pypdf 6.19.0,
three); test 1644 passed, 2 deselected in 207.77 s; gate recall@5 0.682 passes; api-smoke passed;
`real 249.75`, 34.5 s more than at STOP 1, about the attack-run tests' 35 s.


### The merge with main: S4b and S9 (2026-10-25)

The coordinator's go, verbatim: "Go: merge origin/main into feat/s7-attack-guardrails now. S4b
(#30) and S9 (#27) are both merged; main is c77be52 (S9 merged 2026-10-25 17:29Z)." Merge commit
`fed559f` (`git fetch origin && git merge origin/main`, a merge commit; no rebase, no squash, no
push). Before it, the developer stopped once (the reason keys, below) and handed back; the tree
was clean then, the merge previewed with `git merge-tree` only.

**The conflicts and how each was resolved** (seven files; the other files main and the branch both
changed merged cleanly):

| File | Conflict | Resolution |
|---|---|---|
| `CHANGELOG.md` | both Unreleased sections | the union: S7a's line on top, then S9's, S4b's and the audit fix's |
| the main plan | S7's dated note (D1, D3) against S9's note and the v0.2 heading | the union: S7's note, then S9's, under main's v0.2 heading (which names S9) |
| `src/raglab/core/ports.py` | S7's `drop_retrieved` and `check_output(answer, retrieved)` against S9's Tracer section after S3's `check_output` | S7's port methods, then S9's Tracer, Span and no-op section |
| `src/raglab/evals/config.py` | `load_generation`'s signature and docstring | S9's signature (`perf_stub`) with S7's docstring (the attack suite) |
| `src/raglab/generate/assemble.py` | imports, parameters, the index | both: S9's tracer and `TracedEmbedder` wrap the embedder, then S7's scan indexes what it keeps; `extra`, `scan_index` and `tracer` side by side |
| `src/raglab/generate/pipeline.py` | the docstring; the chat call | S7's Outcome sentence and S9's tracing paragraph; S9's chat span, and S7's output guards on the kept chunks (S3's `retrieved_ids` gone) |
| `src/raglab/api/app.py` | the docstring; `_reason`'s key | S7's sentence and S9's telemetry paragraph; S7's key expression, which gives S9's guards the same keys, S9's then-unused import left out (the integration commit below makes `raglab.core.reasons` the one source) |

In the merge commit too, as its mechanical part: S9's two `default_guards()` calls
(`tests/obs_support.py`, `tests/obs/test_guard_traces.py`) take the root and the chunks. On the
merged tree the offline suite gave "1862 passed", with two failures, both expected and fixed below:
the staleness test (no replay record for v2's baseline yet) and S4b's configs test (the attack
configs).

**Integration decisions and changes** (each its own commit after the merge):

1. **The reason keys** (`5eb7e62`). Integration decision by the orchestrator on 2026-10-25, not a maintainer call: `raglab/core/reasons.py` is the one source;
   `GUARD_REASONS` left `api/app.py`. The input injection detector's refusal joins `INPUT_KEYS` as
   "injection" (S9's docstring prescribes it); the link, secrets and personal-details, prompt-leak
   and citation guards take S9's "blocked" (S7a's plan needs no key of their own; the response
   said "blocked" already); the register filter's drop events take a sibling `drop_key`,
   "dropped" (passages from outside the register were left out and the answer went on), called
   only for an Outcome's `dropped`, while `reason_key` stays as S9 wrote it and is called only for
   its `events`: a GuardEvent carries only its guard and stage, and a drop fires at "retrieved",
   the stage of S9's withholding events, so one function cannot tell a drop from a stop. REASONS
   lost the dead keys register, links, secrets_pii and prompt_leak and gained dropped. Tests: S9's
   `test_every_default_guards_decision_has_a_key_the_api_knows`, extended to S7's guards and the
   drop key (test (i)); `tests/security/test_guard_reasons.py`, among them
   `test_the_vocabulary_keeps_no_dead_key`.
2. **The trace: option A** (`2473b34`). Integration decision by the orchestrator on 2026-10-25, not a maintainer call: The pipeline span's `raglab.guard.name`,
   `raglab.guard.stage` and `raglab.guard.reason` hold the decision that stopped the request, as
   S9 wrote it, or, when nothing stopped it, the drop step's (register, retrieved, dropped), with
   `raglab.status` ok telling the two apart; `raglab.retrieved.ids` are the chunks kept; no new
   exporter key, and S9's types unchanged. With it, a generation record's guard events keep the
   drops before the stop, so a request dropped from and then withheld keeps its drop in the run
   record and in the log while its trace shows the stop: docs/OBSERVABILITY.md says both, and that
   the instruction scan's quarantines happen at index build and are listed in the attack record's
   manifest, not in traces. The coordinator relaxed its item 4 to: every stopping decision reaches
   a trace, and so does a drop when nothing stopped. Tests (ii)
   `test_a_request_only_dropped_from_records_the_drop_and_no_dropped_id` and (iii)
   `test_a_request_dropped_from_then_withheld_records_the_stop_and_logs_the_drop` with
   `test_the_run_record_keeps_a_drop_before_its_stop`, in S9's `tests/obs/test_guard_traces.py`.
3. **The log** (`89f127a`). Integration decision by the orchestrator on 2026-10-25, not a maintainer call: S9's `raglab/core/reasons.py` said a guard's own text "goes
   to the server log only". Since the merge it does not: the log line is the key, the guard and
   its stage for every guard, S9's included, because a guard's text can hold what it stopped (a
   credential the secrets and personal-details guard caught, for one). This is the one statement
   of S9's, merged, that S7 reverses. Test:
   `tests/security/test_guard_reasons.py::test_s9s_guards_are_logged_by_key_too_never_by_their_text`.
4. **The attack configs in S4b's configs test** (`a8d94d9`). Integration decision by the orchestrator on 2026-10-25, not a maintainer call: under S7's D2 ("No corpus
   change; a separate security pack (Recommended)"), an integration change of the merge: S4b's
   `test_the_configs_name_one_golden_file_and_the_position_test_keeps_v1_1` held every other config
   to no dataset, and S7's `attack-fake` and `attack-local` name `datasets/security/attacks.yaml`;
   they join the test as a tuple of their own, each held to that file, the docstring says so, and
   MOVING and AFTER_F stay as they were.

**Breaks of the merge's tests** (each made on committed files and restored; `git diff --quiet HEAD`
true after each):

| Break | Result |
|---|---|
| (i) "dropped" removed from REASONS | 2 failed: S9's extended key test, AssertionError ('register', 'retrieved'), and the dead-key test |
| (ii) the span no longer falls back to the drops | 1 failed: test (ii), KeyError raglab.guard.name |
| (ii) the drop events' reasons put into the retrieved ids | 1 failed: test (ii), the leak check names the pipeline span |
| (iii) the drop recorded after the stop (overwriting it), the record's guard events and the log without drops | 3 failed: test (iii) (the span showed register, retrieved, dropped), the run-record test, and the log test of `test_guard_reasons.py` |
| (iii) the log without drops alone | 1 failed: test (iii), the log held the stop only |
| The log: S9's old line, the event's text | 4 failed in `test_guard_reasons.py`: the injection's, the withheld answer's and S9's two guards' lines |
| D2: `attack-local` pointed at `datasets/golden.v2.jsonl` | 1 failed: S4b's configs test, AssertionError attack-local |
| AG10: a no-op layer added to `default_guards()` | 1 failed: the staleness test, "no replay record shows guard set ac70b4d80446 inert on" v2's baseline |
| AG11: R-20's Test and Gate cells set back to "tbd (S7)", "tbd" | 1 failed: `test_s7s_cells_name_their_security_tests_and_pr_fast`, "R-20: its Test cell still says tbd (S7)" and two more |

### The v2 evidence (after the merge)

- **AG10, the replay** (`5c4d409`, the record made from a clean tree at `a8d94d9`): `raglab replay`
  over golden set v2's consistency baseline `20261024T090351Z-generation-local-ollama-dev-ade9397`
  and its four repeats (`...091315Z...`, `...092237Z...`, `...093208Z...`, `...114208Z...`, the five
  runs THRESHOLDS' consistency row names): 1,515 case lines, 1,494 answers, 7,575 retrieved chunks,
  **zero events**; record
  `runs/replays/20261024T090351Z-generation-local-ollama-dev-ade9397--d81cec18f099.json`, guard set
  `d81cec18f099` (unchanged by the merge). The v1.1 record stays as history.
  `tests/security/test_guard_staleness.py` passes on it.
- **AG5 on v2**: golden set v2's 101 dev questions (22 retrieval, 79 behaviour; 75 asked as tenant
  A, 26 as tenant B; never the test split): the tenant guard, the input limits and the injection
  detector each refuse 0 of 101. 52 of those questions are new in v2 and were not seen when the
  rules were written.
- **The suites per filter on v2** (`b406a44`, `runs/guard-suites/20261025T181249Z-5c4d409.json`, a
  clean tree at `5c4d409`): no miss and no false block in any layer; the must-not-block counts are
  106 (tenant, input limits), 111 (injection), 235 (scan), 233 (register), and 1,499 to 1,502 for
  the output layers over the 1,494 recorded answers; THRESHOLDS' Guards section takes these
  numbers.
- **TEST-PLAN** (`d1074c9`): the Test and Gate cells of R-15, R-16, R-17, R-19, R-20 and R-21 name
  their tests under `tests/security/` and pr-fast; the gaps R-20 and R-21 say where S7 covers them;
  section 10's security line names S7a's parts and keeps a placeholder for S7b's;
  `tests/unit/test_test_plan.py` checks S7's cells as it checks S4b's.
- No guard fired on a v2 answer, question or chunk that should pass.

### `make -k check API_SMOKE_PORT=8768` after the merge (`d1074c9`, `/usr/bin/time -p`)

Every target passes, `audit` included ("No known vulnerabilities found, 48 ignored", twice): format
(309 files), lint, types (0 errors), deps, audit, sast, workflows (no findings), secrets (no
leaks, directory and history), privacy (0 hits across 463 files), architecture (0 violations),
check-dataset (`datasets/golden.v2.jsonl passes as v2`), model, test, gate (recall@5 0.682 passes
against the v2 baseline `20261024T090200Z-retrieval-dense-dev-ade9397`) and api-smoke (port 8768).
`real 290.44`.

**Timings.** The test target: "1872 passed, 2 deselected, 1 warning in 242.19s", against main's
"1588 passed, 2 deselected in 199.32s" at `c77be52` (the coordinator's local run): 284 more tests
and 42.87 s more. `tests/security/` on its own: "279 passed, 1 warning in 43.77s" (`real 44.02`).
pr-fast's check job was at 11 min 35 s of its 15-minute limit before this pull request; its time
after is [CI].

**`make perf-smoke`** once after the merge (no model; k6 and the collector on loopback 8791 and
4391, the cached archives checked by sha256): steps 1 to 6 ok, "/ask median 5.91 ms, p90 6.10 ms,
p95 6.25 ms, min 4.36 ms, max 15.07 ms, over the 100 gated requests", against T 40 ms; 110 traces
of /ask with five spans each, no marker and no content key past the Langfuse pipeline;
"perf-smoke: passed", `real 17.47`.

## Part S7b

(After S6 and S7a merge.)
