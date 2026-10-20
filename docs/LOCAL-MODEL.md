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
| `make gate-local` | The consistency gate (S4, Q-05) in one session with the same guards: the live contract test, then `raglab gate --config config/local-ollama.toml`, which runs the dev suite x3, writes the run record to `runs/tmp/` and prints one line against the published local baseline and the margin of docs/THRESHOLDS.md. Until a baseline is published it refuses (the first run after the golden set's sign-off is published as the baseline, `raglab publish --baseline`), and until the margin is set from the four repeats it refuses to judge; `raglab gate --run <run>` then gates a finished run again without the model. Both are set since S4: the baseline `20261019T172035Z-generation-local-ollama-dev-97011a7` and a margin of one case. A session (the contract test, then the 22 dev retrieval questions and 27 dev behaviour cases x3) took about 4.5 to 5 minutes on the maintainer's Mac in S4 |
| `make nightly-local` | The local nightly (S4): the live contract test, then the generation suite on every split of `config/local-ollama-nightly.toml` with `--gate nightly`. The test split runs only here and at a release |
| `make release-local` | The test slice, once per release (v0.1, `runbooks/release.md`): the default retrieval configuration on the test split with the embedder only, then one session with the live contract test and the generation suite on the test split x3, both with `--gate release` |
| `make ollama-up` | Starts the server for manual work (after the preflight); stop it with `make ollama-down` |
| `make ollama-down` | Unloads every loaded model, stops the server and runs the postcheck |
| `make ollama-status` | This project's server pid, the port, the loaded models, any ollama process, any registered Ollama service, and the memory available |

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
- the memory available is below the model's size plus the margin.

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
will not stop, a leftover process, and a session that fails or is interrupted.

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
