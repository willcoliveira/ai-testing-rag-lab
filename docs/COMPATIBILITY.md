# Compatibility

Which model, server and versions each provider adapter has been tested against, and when. A
line is added only from a real run; the run record holds the details.

| Adapter | Model | Server | Tested on | Evidence |
|---|---|---|---|---|
| `raglab.adapters.openai_compat` | `nemotron-3.5-lightning:30b-a3b-mlx@d1e17d7dabacb401dec6440b4ec987ea053b9568b01f89fb3d54f8b2e71397be` | Ollama 0.40.6 (Homebrew, MLX runner) on macOS, Apple M4 Pro | 2026-10-18 | the live contract test (`tests/contract/test_chat_contract.py`, marker `live`) passed, and the run `20261018T134910Z-generation-local-ollama-dev-d897052` (S3 ledger) |

Tested against nemotron-3.5-lightning:30b-a3b-mlx@d1e17d7dabacb401dec6440b4ec987ea053b9568b01f89fb3d54f8b2e71397be on Ollama 0.40.6 on 2026-10-18.

Known limits of that combination (docs/LOCAL-MODEL.md):

- no structured output: any `response_format` gets HTTP 501 on this build, so the config sends
  none and the parser checks the reply against the answer schema;
- thinking is switched off with `reasoning_effort: "none"`; `think: false` is not honoured
  through the OpenAI-compatible endpoint;
- Ollama 0.40.4 refuses the model ("requires a newer version of Ollama"); the session needs
  0.40.6 or later.

The fake chat model (`raglab.adapters.fake.FakeChat`) runs in the tests, pr-fast and the
container; it is not a provider and has no line here.
