# Compatibility

Which model, server and versions each provider adapter has been tested against, and when. A
line is added only from a real run; the run record holds the details.

| Adapter | Model | Server | Tested on | Evidence |
|---|---|---|---|---|
| `raglab.adapters.openai_compat` | `nemotron-3.5-lightning:30b-a3b-mlx@d1e17d7dabacb401dec6440b4ec987ea053b9568b01f89fb3d54f8b2e71397be` | Ollama 0.40.6 (Homebrew, MLX runner) on macOS, Apple M4 Pro | 2026-10-18 | the live contract test (`tests/contract/test_chat_contract.py`, marker `live`) passed, and the published run `20261018T162604Z-generation-local-ollama-dev-3b66ea3` (S3 ledger) |
| `raglab.adapters.openai_compat`, as the judge (`config/judge-local.toml`, S5) | `ministral-3:14b-instruct-2512-q4_K_M@4760c35aeb9d9e9c6174c2492562c0b999e80a222804fd96b1915ab72bbcdcf7` | Ollama 0.40.6 (Homebrew; GGUF, runner ggml) on macOS, Apple M4 Pro | 2026-10-20 | the judge's live contract test (`tests/contract/test_judge_contract.py`, marker `live`, `make judge-contract`) passed with `response_format = "json_schema"` (S5 ledger) |

Tested against nemotron-3.5-lightning:30b-a3b-mlx@d1e17d7dabacb401dec6440b4ec987ea053b9568b01f89fb3d54f8b2e71397be on Ollama 0.40.6 on 2026-10-18.

Tested against ministral-3:14b-instruct-2512-q4_K_M@4760c35aeb9d9e9c6174c2492562c0b999e80a222804fd96b1915ab72bbcdcf7 on Ollama 0.40.6 on 2026-10-20.

Known limits of the judge's combination: none found so far. Its runner accepts a JSON schema
response format (four of four calls in the live contract test returned a verdict in the schema);
without one, the prompt alone gave three of three replies the strict parser refused, so the judge
config keeps `json_schema`, and its live contract test records both formats in every judge session.

## DeepEval (S5)

DeepEval 4.3.1 is pinned in `tools/deepeval-check` (its own uv project and lock; the main
environment never installs it). Checked at 4.3.1 so far, offline (`make deepeval-test`,
2026-10-20): the custom-LLM interface (`DeepEvalBaseLLM` with `get_model_name`, `load_model`,
`generate` and `a_generate`; called with a pydantic schema, the subclass returns its instance), a
whole `FaithfulnessMetric` in eval mode `llm` through raglab's adapter against a stub server, and
the telemetry opt-out: with `DEEPEVAL_TELEMETRY_OPT_OUT` unset, DeepEval's PostHog client tried to
reach `us.i.posthog.com:443` at the interpreter's exit, and the loopback-only socket guard caught
every attempt; with it set to `1` before the import, there was none (S5 ledger). The checks against
the local judge (the metric canary, the hallucination direction, the cross-check) run in a judge
session after the sign-off of docs/CRITERIA.md, and are written here then.

Known limits of that combination (docs/LOCAL-MODEL.md):

- **No structured output (JSON schema mode).** On Ollama 0.40.6 (Homebrew, MLX runner) with
  `nemotron-3.5-lightning:30b-a3b-mlx@d1e17d7dabacb401dec6440b4ec987ea053b9568b01f89fb3d54f8b2e71397be`,
  any `response_format` (`json_schema` or `json_object`) gets HTTP 501, "structured output is
  unavailable" (the server log: the MLX runner's grammar library is not in this build), checked
  2026-10-18. So `config/local-ollama.toml` sets `response_format = "none"`: the prompt asks for
  the JSON and the strict parser refuses any reply off the answer schema (`invalid_output`). The
  user's decision of 2026-10-18, verbatim: "Accept, record the limit (Recommended)".
  **Re-test schema mode on every Ollama upgrade**: copy `config/local-ollama.toml` with
  `response_format = "json_schema"`, then run
  `RAGLAB_LIVE_CONFIG=<the copy> uv run raglab ollama session --config config/local-ollama.toml --run "uv run pytest -m live tests/contract/test_chat_contract.py"`;
  if it passes, switch the config back to `json_schema` and add a line here;
- thinking is switched off with `reasoning_effort: "none"`; `think: false` is not honoured
  through the OpenAI-compatible endpoint;
- Ollama 0.40.4 refuses the model ("requires a newer version of Ollama"); the session needs
  0.40.6 or later.

The fake chat model (`raglab.adapters.fake.FakeChat`) runs in the tests, pr-fast and the
container; it is not a provider and has no line here.
