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
| `make ollama-up` | Starts the server for manual work (after the preflight); stop it with `make ollama-down` |
| `make ollama-down` | Unloads every loaded model, stops the server and runs the postcheck |
| `make ollama-status` | This project's server pid, the port, the loaded models, any ollama process, any registered Ollama service, and the memory available |

`raglab ollama up|down|status|session --config config/local-ollama.toml` is the same from the CLI
(`src/raglab/runtime/ollama.py`). The server's pid and log are in `runs/tmp/ollama/` (gitignored).

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
| Whole run | 3,600 s wall-clock cap; a run that hits it, or meets a request timeout, is marked `partial` and is never published | `[generation] run_timeout_s` |
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
`runs/published/20261018T145441Z-generation-local-ollama-dev-fa04154`:

- memory available before the session (the preflight's reading): 31.0 GiB; after: 37.1 GiB;
- the live contract test passed in 30.57 s (its request is the first, so the model's load is in
  it);
- the generation suite: 75 case-trials (25 cases, 3 trials) in 112.109 s, so about 37.4 s per
  trial of 25 cases; per request p50 1,470.501 ms and p95 2,487.696 ms;
- the whole session, server start to postcheck: 2 min 54.2 s;
- afterwards: "postcheck passed: port closed, no ollama process, no model loaded", and
  `lsof -iTCP:11434 -sTCP:LISTEN` found nothing.
