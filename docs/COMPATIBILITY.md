# Compatibility

Which model, server and versions each provider adapter has been tested against, and when. A
line is added only from a real run; the run record holds the details.

| Adapter | Model | Server | Tested on | Evidence |
|---|---|---|---|---|
| `raglab.adapters.openai_compat` | `nemotron-3.5-lightning:30b-a3b-mlx@d1e17d7dabacb401dec6440b4ec987ea053b9568b01f89fb3d54f8b2e71397be` | Ollama 0.40.6 (Homebrew, MLX runner) on macOS, Apple M4 Pro | 2026-10-18 | the live contract test (`tests/contract/test_chat_contract.py`, marker `live`) passed, and the published run `20261018T162604Z-generation-local-ollama-dev-3b66ea3` (S3 ledger) |

Tested against nemotron-3.5-lightning:30b-a3b-mlx@d1e17d7dabacb401dec6440b4ec987ea053b9568b01f89fb3d54f8b2e71397be on Ollama 0.40.6 on 2026-10-18.

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
