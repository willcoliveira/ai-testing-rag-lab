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
every attempt; with it set to `1` before the import, there was none (S5 ledger).

Checked live at 4.3.1 against the local judge
(`ministral-3:14b-instruct-2512-q4_K_M@4760c35aeb9d9e9c6174c2492562c0b999e80a222804fd96b1915ab72bbcdcf7`,
Ollama 0.40.6, its judge config: temperature 0, 512 output tokens, `json_schema`) on 2026-10-21,
in one judge session (`make deepeval-check`, the telemetry opt-out set before the import, the
loopback-only guard on: it caught 0 attempts). Results, from
`runs/tmp/deepeval-check/20261021T094309Z.json` (S5 ledger):

- **The custom-LLM interface works:** called with a schema, the subclass returned its instance
  (1 call); every one of the 20 calls of the next two checks fitted the schema DeepEval asked for.
- **The metric canary separates nothing:** `FaithfulnessMetric` gave 0.0 to the honest twin and
  to the invented answer, with `penalize_ambiguous_claims` off and on (4 scores, 4 calls each);
  none passes the default threshold of 0.5. Since the honest answer, which states no value, also
  scored 0.0, the run supports no reading of how an unsupported claim is counted.
- **The hallucination direction is undecided:** `HallucinationMetric` gave 0.0 to both the output
  consistent with G-01's passage and the one that contradicts it (2 calls each). At the default
  threshold of 0.5 a score of 0.0 does not pass (`is_successful()` false), so this version treats
  the threshold as a minimum, as the page read on 2026-10-20 says ("Higher is better").
- **The cross-check did not run:** its first `FaithfulnessMetric` call asked for DeepEval's
  `Truths` schema over a case's five passages, and the judge's reply was cut off mid-string
  ("EOF while parsing a string": the judge config caps a reply at 512 tokens), so the reply did
  not fit the schema, DeepEval raised, and the check reported the error (the session exited 2).

That session recorded each metric's score and calls only, not DeepEval's intermediate steps.

**A second and last session** (the user's choice, "One more session (Recommended)"), 2026-10-21,
11:06 to 11:18 WEST, exit 0, the guard catching 0 attempts. DeepEval's own requests asked for up
to 2,048 output tokens (the own judge's config keeps 512), and each metric's truths, claims,
verdicts and reason were recorded after `measure`. Results, from
`runs/tmp/deepeval-check/20261021T101857Z.json` (S5 ledger):

- **The metric canary still separates nothing, and the steps show why.** The four scores are 0.0
  again. The invented answer's one claim, "Five password reset attempts are allowed per day
  (Identity and Access FAQ, Q2).", got the verdict "no": rightly. The honest twin's two claims
  ("The company's documents do not set a limit on password reset attempts per day", "I cannot
  give a number") got one verdict back, a "no": the judge read the reference passage's 5 to 10
  login attempts before an account freezes as a company limit that "no limit" contradicts. So
  the honest twin fails on the model's misreading inside DeepEval's verdict step (and a verdict
  list shorter than the claims), not on how DeepEval counts claims: the run supports no reading of
  that, as the corrected reading now says ("not separated").
- **The hallucination direction stays undecided by the live run:** both outputs scored 0.0 again,
  neither passing. Their verdicts and reasons were computed but not written (the direction report
  kept only the scores; fixed since). DeepEval 4.3.1 itself, run offline against a stub server on
  2026-10-21, warns: "'HallucinationMetric' now scores in the same direction as every other
  deepeval metric: 1 is a pass, 0 is a failure, and 'threshold' is the MINIMUM passing score".
  That is the page's "Higher is better", and it is why 0.0 does not pass.
- **The cross-check ran** on trial 1 of the 17 dev `answer` cases (68 calls: 72,060 prompt and
  10,223 completion tokens, every reply fitting its schema; the longest list, G-12's, held 33
  truths), against the own judge's `grounded` on the judge-v2 baseline: both pass 12, both fail 1
  (G-01), the own judge passing and DeepEval failing 2 (G-11, G-31), the own judge failing and
  DeepEval passing 2 (G-12 at 0.5, G-17): they agree on 13 of 17. On G-31 ("64" for the length a
  password must have), DeepEval failed a value a passage does state, reading it against a
  12-character minimum. In 4.3.1 a verdict can be "borderline", which counted as truthful: G-08,
  G-14 and G-36 scored 1.0 on a single "borderline" verdict.

So the scores are degenerate on the canary and the hallucination check only: on the cross-check
DeepEval gave 1.0, 0.5 and 0.0. DeepEval's scores are never the judged numbers (D4); the own
judge's verdicts are.

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

## Observability and performance (S9)

Tested on 2026-10-24 on macOS (Apple silicon), offline (`make test`, `make perf-smoke`; the S9
ledger), and on GitHub's `ubuntu-24.04` runner the same day: the pull request's perf job passed
ten times at one commit (pr-fast run 40074154534, attempts 1 to 10), with the linux amd64 archives
of k6 and the collector checked against their pins.

| Piece | Version | What was checked |
|---|---|---|
| OpenTelemetry Python: `opentelemetry-api`, `-sdk`, `-exporter-otlp-proto-http` | 1.45.1 (uploaded 2026-10-06) | The tracer behind the `Tracer` port, the allowlist exporter, the OTLP/HTTP exporter to the collector (`tests/obs/`, `make perf-smoke`) |
| GenAI semantic conventions | `open-telemetry/semantic-conventions-genai` at `9ffc7e00c639` (2026-10-21; status Development, no release) | The span names and attribute keys of `src/raglab/obs/names.py`, read from `docs/gen-ai/client-inference.md` and `docs/gen-ai/gen-ai-spans.md` at that commit. The `opentelemetry-semantic-conventions` 0.66b1 package was checked against them and is not used: its incubating constants lack `gen_ai.request.reasoning.level` and `gen_ai.retrieval.top_k` |
| FastAPI's telemetry | FastAPI 0.146.0 (0.144.0 when first checked, on 2026-10-24; 0.146.0 re-checked by the same tests on 2026-10-31) | The `telemetry` settings (`tracing`, `operation_spans`, `logs`, `metrics`, `auto_configure`, `exclude`, `tracer_provider`); its request span's attributes, listed in `src/raglab/obs/names.py`, of which three leave |
| k6 | 2.3.0 (published 2026-09-21) | `--no-usage-report`, `--include-system-env-vars=false`, `--summary-export` (the legacy flat format), thresholds on `checks`, `http_req_failed` and a custom trend (`perf/smoke.js`) |
| OpenTelemetry Collector | core `otelcol` 0.162.0 (published 2026-09-29) | The components `otlp` (receiver), `attributes` and `batch` (processors), `file` and `otlp_http` (exporters); `validate` on the three configurations of `deploy/otel/`; `service.telemetry.metrics.level: none` |
