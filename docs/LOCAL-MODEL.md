# The local model: one session at a time

The live generation runs (S3 onwards) use a model on this Mac through Ollama. The server runs only
for a session that needs it, never as a resident service, so the rest of the machine stays usable
for other work. The scope came from the user on 2026-10-18 (S3 ledger, AC15).

**Lab practice.** Production runs the model on a managed endpoint with its own capacity, quotas
and monitoring, not on a laptop. Everything below exists so a laptop can host the lab's live runs
safely.

## Commands

| Command | What it does |
|---|---|
| `make eval-local` | The live run: starts the server, runs the live contract test (`tests/contract/test_chat_contract.py -m live`) and the generation suite on `config/local-ollama.toml`, then unloads the model, stops the server and runs the postcheck, on success, on failure, on Ctrl-C (SIGINT), on `kill` (SIGTERM) and on a closed terminal (SIGHUP). A SIGKILL cannot be caught: the server and a loaded model then stay up (the model until the keep-alive ends), the postcheck does not run, and the pid file in `runs/tmp/ollama/` makes the next `up` or session refuse until `make ollama-down` stops it |
| `make gate-local` | The consistency gate (S4, Q-05) in one session with the same guards: the live contract test, then `raglab gate --config config/local-ollama.toml`, which runs the dev suite x3, writes the run record to `runs/tmp/` and prints one line against the published local baseline and the margin of docs/THRESHOLDS.md. Until a baseline is published it refuses (the first run after the golden set's sign-off is published as the baseline, `raglab publish --baseline`), and until the margin is set from the four repeats it refuses to judge; `raglab gate --run <run>` then gates a finished run again without the model. Both are set since S4, and again on golden set v2 since S4b: the baseline `20261024T090351Z-generation-local-ollama-dev-ade9397` and a margin of one case (docs/THRESHOLDS.md). A session on v2 (the contract test, then the 22 dev retrieval questions and 79 dev behaviour cases x3, 303 case-trials) took about 9 to 9.5 minutes on the maintainer's Mac in S4b (below); on golden set v1.1 (27 dev behaviour cases, 147 case-trials) it took about 4.5 to 5 minutes in S4 |
| `make nightly-local` | The local nightly (S4): the live contract test, then the generation suite on every split of `config/local-ollama-nightly.toml` with `--gate nightly`. The test split runs only here and at a release |
| `make release-local` | The test slice, once per release (v0.1, `runbooks/release.md`): the default retrieval configuration on the test split with the embedder only, then one session with the live contract test and the generation suite on the test split x3 (`config/local-ollama-release.toml`, the local config with split test: a generation run uses its config's split), both with `--gate release` |
| `make ollama-up` | Starts the server for manual work (after the preflight); stop it with `make ollama-down` |
| `make ollama-down` | Unloads every loaded model, stops the server and runs the postcheck |
| `make ollama-status` | This project's server pid, the port, the loaded models, any ollama process, any registered Ollama service, the memory available, and the power source (S5) |
| `make judge-contract` | S5: a judge session (`config/judge-local.toml`): the server serves the judge, `ministral-3:14b-instruct-2512-q4_K_M`, never the generator, and the session runs the judge's live contract test only (`tests/contract/test_judge_contract.py -m live`), on hand-written items, never a golden answer; it probes both response formats and writes each call's format, seconds and tokens to `runs/tmp/judge-contract/`. The first session (2026-10-20) took 31 s from launch to the postcheck: the first call, which loads the model, 6.9 s, each warm call about 3 s (S5 ledger) |
| `make judge-canaries` | S5: a short judge session: the judge's live contract test, then the canary set alone (`raglab canaries`), which prints each item's verdict, seconds and tokens and writes them to `runs/tmp/canaries/`. It measures the judge's seconds per call before a judged run's cap is set; the first one (2026-10-20) took 2 minutes from launch to the postcheck, the 19 canary calls 2.487 to 9.196 s each (S5 ledger) |
| `make judge-local RUN=<run>` | S5: a judge session on a finished generation run: the live contract test, then `raglab judge`, which runs the canaries first and stops the session before any judged call when one is off its side; the judged run's wall-clock cap is `[judging] run_timeout_s` (7,200 s, set from the measured speed). Measured (S5 ledger): on the consistency baseline (147 case-trials, 592 judge calls), 09:18:21 to 10:15:13 on 2026-10-21 from launch to the postcheck, the run itself 3,380.41 s, a judge call's p50 5,522.768 ms and p95 10,373.613 ms; on the position run (90 case-trials, 108 judge calls), 10:27:44 to 10:35:07 |
| `make position-local` | S5: a generator session (`config/position-local.toml`, the local config with a `[position]` table): the generator's live contract test, then the position test (`raglab position`). Measured (S5 ledger): 10:20:02 to 10:25:52 on 2026-10-21 from launch to the postcheck, for 90 generator calls whose contexts are built to a budget of 6,144 prompt tokens (489,933 prompt tokens in all, from the record); the generator needs 17.8 GiB plus the 4 GiB margin |
| `make deepeval-check JUDGED=<run>` | S5: a judge session for DeepEval's checks: the live contract test, `raglab canaries`, then `tools/deepeval-check` with DeepEval's telemetry off and a loopback-only socket guard. Measured (S5 ledger), 2026-10-21: the first session, 10:38:01 to 10:43:10 from launch to the postcheck, exited 2 (its cross-check stopped at its first case, a reply cut off at the judge's 512 output tokens); the second, with DeepEval's own requests capped at 2,048 output tokens (the own judge keeps 512), 11:06:15 to 11:18:58, exit 0, all four checks run (89 DeepEval calls) |
| `make attack-local` | S7 (AG9): a generator session on `config/attack-local.toml` (the consistency gate's pipeline and seed, suite `attack`): the live contract test, then the security pack's 13 attack cases x3 with the corpus's three attack pages indexed in tenant A as pages outside the register, twice: `--defences off` (S3's guards, no instruction scan; a measured result kept in `runs/tmp/`, never published) and `--defences on` (S7a's guards and the scan; the command exits 1 if any safety check of any case and trial fails). Each run sits inside the loopback-only egress guard, and its record says what the guard saw. It runs only with the maintainer's go. Measured (S7 ledger), 2026-10-25: 19:25:51 to 19:50:07 WET from launch to the postcheck, 24 min 16 s on the clock, of which the Mac slept about 20 min 35 s (two maintenance sleeps in `pmset -g log`, 904 s and 331 s: the session started while the Mac was in a dark wake, and `caffeinate -i` held its assertion throughout without keeping the Mac awake); awake, about 3 min 41 s: the contract test 32.98 s, the defences-off run 103.289 s and the defences-on run 49.859 s (the records' durations, which leave the sleep out). The session exited 1: the defences-on run failed its gate (S7 ledger). The second session, at the fix of the maintainer's decision (S7 ledger), 2026-10-25: 20:56:39 to 20:59:29 WET under `caffeinate -s -i`, 2 min 50 s from launch to the postcheck, with no sleep in the power log: the contract test 32.43 s, the defences-off run 69.864 s and the defences-on run 35.031 s; exit 0 |

One model per session: a generator session never serves the judge, and a judge session never
generates; a judge session reads finished records. `raglab ollama ... --config` picks the model
from the config's suite: a generation config's generator, a judge config's judge (S5).

`raglab ollama up|down|status|session --config config/local-ollama.toml` is the same from the CLI
(`src/raglab/runtime/ollama.py`). The server's pid and log are in `runs/tmp/ollama/` (gitignored).
The session flushes each of its lines, and the make targets set `PYTHONUNBUFFERED=1`, so a log of
`make eval-local > log 2>&1` (or CI's) shows each line as it happens, in order with the commands'
own output, and keeps the lines printed before a kill.

## Limits

Set in `config/local-ollama.toml` and recorded in every run's manifest (`ollama` and `generator`).

| Limit | Value | Where |
|---|---|---|
| Interface | `127.0.0.1:11434` only (`OLLAMA_HOST`); the adapter refuses any non-loopback base URL | `[ollama] host`, `raglab.adapters.openai_compat` |
| Models loaded at once | 1 (`OLLAMA_MAX_LOADED_MODELS`) | `[ollama] max_loaded_models` |
| Requests at once | 1 (`OLLAMA_NUM_PARALLEL`) | `[ollama] num_parallel` |
| Context window | 8,192 tokens (`OLLAMA_CONTEXT_LENGTH`), not the server's default (32,768 on this Mac) or the model's maximum | `[ollama] context_length` |
| Keep-alive | 2 minutes after the last request (`OLLAMA_KEEP_ALIVE`); the session also unloads the model explicitly before it stops the server | `[ollama] keep_alive` |
| Free memory to start | the model's size on disk plus 4 GiB, against the memory macOS reports available (free, inactive and speculative pages from `vm_stat`) | `[ollama] memory_margin_gb` |
| Per request | 120 s timeout; 1,024 completion tokens at most | `[generator] timeout_s`, `max_tokens` |
| Sampling | temperature 1.0 and top_p 0.95, the model card's recommended settings (for reasoning on and off), with a seed per trial | `[generator] temperature`, `top_p`; `[generation] seed` |
| Whole run | 3,600 s wall-clock cap; a run that hits it, or has any trial without a reply (a timeout, a connection error or an HTTP error: status `unavailable`), is marked `partial` and is never published | `[generation] run_timeout_s` |
| Server version | at least 0.40.6 (0.40.4 refused the pinned model: "requires a newer version of Ollama") | `raglab.runtime.ollama.MIN_VERSION` |

## Guards

Before the server starts (the preflight), the session refuses, and starts nothing, when:

- the `ollama` binary is not on PATH;
- a launchd job or a LaunchAgent or LaunchDaemon plist for Ollama is registered (`brew services`
  writes one): a resident server would outlive the session;
- port 11434 is held by a process this project did not start;
- the pinned model is not pulled (no manifest under `~/.ollama/models`, or `OLLAMA_MODELS`);
- (S5) the pulled model is not the one the config pins: its local manifest's registry-manifest
  layer, whose digest is the one `/api/tags` reports, names another digest, or no such layer is
  there to check (fails closed). The session checks the model of its config's suite: a generation
  config's generator, a judge config's judge;
- the memory available is below the model's size plus the margin;
- (S5, AC22) the Mac does not draw from AC power: the source `pmset -g batt` names ("Now drawing
  from 'AC Power'") must be `AC Power`, and one it cannot read refuses too (fails closed). Off
  macOS power is not checked, and the session says so; CI runs no live session. The preflight says
  the source in a `power:` line beside its `model:` and `memory:` lines.

**A session runs on AC power only, from start to end (S5, AC22).** On 2026-10-20 a judged run on
battery took the Mac down to 1%, and macOS hibernated it for 36 minutes in the middle of the run
(S5 ledger). While a session's commands run, a watcher reads the power source every 15 s; when
the Mac leaves AC power (or the source cannot be read), the running command's whole process group
is ended (SIGTERM, then SIGKILL after 5 s), no further command starts, the model is unloaded, the
server stopped and the postcheck run, as on any stop. The interrupted command writes no run record
(a record is written when a run ends), and a session never publishes anything. The session's last
line is one `STOPPED:` line that names the source and the time, and it exits 75 (EX_TEMPFAIL):
plug the charger in, then run the target again. `make ollama-up` checks the source when it
starts, but a server started that way is not watched: stop it with `make ollama-down` before
unplugging. `make ollama-status` shows the source (`power`).

The judge's limits are the generator's, from `config/judge-local.toml`'s `[ollama]` table (the
same loopback interface, one model, one request, a context of 8,192, a keep-alive of 2 minutes, a
4 GiB margin on top of the model's 8.5 GiB), with its own per-request settings: temperature 0, a
fixed seed, 512 output tokens, a 180 s timeout (the first request loads the model), and
`json_schema` as the response format.

After every session that ends normally, by an error, by Ctrl-C, by SIGTERM or by SIGHUP, the
postcheck fails loudly (exit 1, `POSTCHECK FAILED`) unless port 11434 is closed and no ollama
process runs. A loaded model lives in the server's runner process, so no process means no model
is resident. A process counts when its executable is `ollama` (the server and its runners), not
when only an argument names it (an editor on the config, a tail of the log, the session's own
`raglab ollama session` command), so the check does not depend on BSD pgrep leaving out the
caller's ancestors.

**Once the stop has begun, it runs to the postcheck.** The first SIGINT, SIGTERM or SIGHUP ends
the session; from then on, until the postcheck, a further one (Ctrl-C pressed twice, a SIGTERM
that both `uv run` and `make` forward) is only said ("a second signal ... arrived; the stop
continues"), and the stop goes on; the signal handlers in place before the session are restored
after it. Ignoring those signals cannot hang the session, because the stop is bounded: the
command's process group gets SIGTERM and at most 5 s, then SIGKILL; each of the unload's HTTP
calls times out after 30 s (one model is loaded at most); the server gets SIGTERM and at most
15 s, then SIGKILL; and the postcheck's own reads time out. Only SIGKILL can cut the stop short.
The wait for the server ends as soon as it has exited: the session reaps its own server child (an
exited, unreaped child is a zombie that `kill(pid, 0)` still finds); `make ollama-down` in a new
process, which is not the server's parent, decides with `kill(pid, 0)`.

**A session command's whole process tree ends with the session.** Each command (the live test,
the eval) runs in a process group of its own; when the session is interrupted (a signal, Ctrl-C,
an error), that group gets SIGTERM, then SIGKILL after 5 s, before the server is stopped, so no
eval runs on against a stopped server. A terminal's Ctrl-C reaches the session, not the command
directly; the session then stops the command's group.

Each guard is tested offline with a fake host (`tests/unit/test_ollama_session.py`): low memory, a
registered service, a held port, a missing binary, an unpulled model, an old server, a server that
will not stop, a leftover process, a session that fails or is interrupted, and (S5) a battery or
an unreadable power source, before the session and while it runs.

## What this Ollama build does (0.40.6, Homebrew, MLX runner; checked 2026-10-18)

- **No structured output.** Any `response_format` (`json_schema` or `json_object`) gets HTTP 501,
  "structured output is unavailable": the server log says the MLX runner's grammar library is
  missing from this build. So `config/local-ollama.toml` sets `response_format = "none"`: the
  prompt asks for the JSON, and the strict parser refuses any reply that does not fit
  (`invalid_output`). Re-test it on every Ollama upgrade (docs/COMPATIBILITY.md).
- **Thinking off.** `reasoning_effort = "none"` gives replies with no reasoning text. `think: false`
  through the OpenAI-compatible endpoint did not: the model still produced reasoning text. The live
  contract test checks this again before every run.

## The live session of the published S3 run (2026-10-18, a 48 GiB Apple M4 Pro, Docker Desktop running)

`make eval-local`, read from its output and the run record
`runs/published/20261018T162604Z-generation-local-ollama-dev-3b66ea3`:

- memory available before the session (the preflight's reading): 30.8 GiB; after: 36.7 GiB;
- the live contract test passed in 29.78 s (its request is the first, so the model's load is in
  it);
- the generation suite: 75 case-trials (25 cases, 3 trials) in 110.896 s, so about 37.0 s per
  trial of 25 cases; per request p50 1,378.811 ms and p95 2,434.308 ms;
- the whole session, server start to postcheck: 2 min 52.1 s;
- afterwards: "postcheck passed: port closed, no ollama process, no model loaded", and
  `lsof -iTCP:11434 -sTCP:LISTEN` found nothing.

## The sessions on golden set v2 (S4b, 2026-10-24, the same Mac, AC power)

Five `make eval-local` sessions at the frozen commit `ade9397` and one `make gate-local` (the live
break), each on golden set v2's dev split: the 22 retrieval questions and the 79 behaviour cases,
x3 (303 case-trials). The Mac times are the shell clock just before the launch and when `make`
returned (after the postcheck); the suite's own time is the record's `totals.duration_s`:

| Session | Clock | Mac time | Memory before | Contract test | Suite |
|---|---|---|---|---|---|
| 1 | 10:02:54 to 10:12:11 | about 9 min 17 s | 23.6 GiB | 42.16 s | 498.731 s |
| 2 | 10:12:30 to 10:21:41 | about 9 min 11 s | 34.5 GiB | 30.21 s | 504.543 s |
| 3 | 10:21:59 to 10:31:13 | about 9 min 14 s | 36.5 GiB | 22.78 s | 515.387 s |
| 4 | 10:31:31 to 10:40:30 | about 8 min 59 s | 36.5 GiB | 21.60 s | 501.241 s |
| 5 | 12:41:18 to 12:50:38 | about 9 min 20 s | 31.1 GiB | 35.13 s | 508.317 s |
| the live break | 12:55:54 to 13:05:35 | about 9 min 41 s | 34.0 GiB | 29.80 s | 534.982 s |

About 1.6 to 1.8 s of suite time per case-trial, against 1.56 to 1.64 s on v1.1 in S4. Session 5
ran about two hours after session 4: the developer agent had stopped on a usage limit between
them. Every session started Ollama 0.40.6, checked the pinned digest and read "the Mac draws from
'AC Power'", and every postcheck passed.
