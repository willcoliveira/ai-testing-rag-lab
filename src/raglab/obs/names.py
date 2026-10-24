"""Span names and attribute keys (S9), as constants: the GenAI semantic conventions pinned by
commit, raglab's own keys, and the allowlist of keys that may leave the process.

The GenAI conventions left the core semantic conventions in 2026; their repository,
open-telemetry/semantic-conventions-genai, has no release and every document says "Status:
Development". The keys below are read from it at commit 9ffc7e00c639 (2026-10-21):
docs/gen-ai/client-inference.md (the inference span) and docs/gen-ai/gen-ai-spans.md (the
embeddings and retrieval spans). error.type, server.address and server.port are the stable core
attributes those pages link to. Nothing here is imported from the opentelemetry-semantic-
conventions package: its 0.66b1 lacks two of these keys (gen_ai.request.reasoning.level and
gen_ai.retrieval.top_k; docs/COMPATIBILITY.md). A rename in the spec is a reviewed pull request
with its own tests; nothing follows the spec's main branch.

This module imports nothing from opentelemetry, so the pipeline can use the names without loading
the SDK (scripts/check_architecture.py, rule 7, keeps opentelemetry inside raglab.obs).
"""

SPEC = "open-telemetry/semantic-conventions-genai@9ffc7e00c639be7712e544e3e54331e885dccf84"
SPEC_DATE = "2026-10-21"

# gen_ai.operation.name values, and the span names built from them: "{operation} {model}" for the
# inference and embeddings spans, "{operation} {data source}" for the retrieval span
CHAT = "chat"
EMBEDDINGS = "embeddings"
RETRIEVAL = "retrieval"
DATA_SOURCE = "policy-pack"  # the in-memory index of corpus/policy, the one data source

# raglab's own span around one request's pipeline (internal, a child of FastAPI's request span)
PIPELINE_SPAN = "raglab.ask"

# ---------------------------------------------------------------- the spec's keys (9ffc7e0)
OPERATION = "gen_ai.operation.name"
PROVIDER = "gen_ai.provider.name"
REQUEST_MODEL = "gen_ai.request.model"
REQUEST_SEED = "gen_ai.request.seed"
REQUEST_TEMPERATURE = "gen_ai.request.temperature"
REQUEST_TOP_P = "gen_ai.request.top_p"
REQUEST_MAX_TOKENS = "gen_ai.request.max_tokens"
REQUEST_REASONING = "gen_ai.request.reasoning.level"
OUTPUT_TYPE = "gen_ai.output.type"
PROMPT_NAME = "gen_ai.prompt.name"
USAGE_INPUT_TOKENS = "gen_ai.usage.input_tokens"
USAGE_OUTPUT_TOKENS = "gen_ai.usage.output_tokens"
EMBEDDING_DIMENSIONS = "gen_ai.embeddings.dimension.count"
DATA_SOURCE_ID = "gen_ai.data_source.id"
RETRIEVAL_TOP_K = "gen_ai.retrieval.top_k"
ERROR_TYPE = "error.type"
SERVER_ADDRESS = "server.address"
SERVER_PORT = "server.port"

# The spec's Opt-In content attributes. raglab never sets them, on any span: the input messages
# hold the framed prompt (every retrieved chunk's text, which no run record holds), the output
# messages the model's raw reply (what the output guard may withhold), the system instructions the
# system text, and the retrieval query and documents the question and the ids before the guards.
NEVER_SET = (
    "gen_ai.input.messages",
    "gen_ai.output.messages",
    "gen_ai.system_instructions",
    "gen_ai.retrieval.query.text",
    "gen_ai.retrieval.documents",
)

# The fixed values of error.type raglab reports (the spec: "Instrumentations SHOULD document the
# list of errors they report"): no reply (unavailable), no reply in time (timeout), a reply outside
# the answer schema (invalid_output)
ERROR_TYPES = ("unavailable", "timeout", "invalid_output")

# ---------------------------------------------------------------- raglab's keys
PROMPT_VERSION = "raglab.prompt.version"
STATUS = "raglab.status"
LABEL = "raglab.label"
TENANT = "raglab.tenant"
RETRIEVED_IDS = "raglab.retrieved.ids"
CITED_IDS = "raglab.cited.ids"
RETRIEVED_COUNT = "raglab.retrieved.count"
GUARD = "raglab.guard.name"
GUARD_STAGE = "raglab.guard.stage"
GUARD_REASON = "raglab.guard.reason"  # the API's fixed key (raglab.core.reasons), never the text
EMBEDDER_REVISION = "raglab.embedder.revision"
MODEL_DIGEST = "raglab.model.digest"

# D4: the content opt-in, on the pipeline span only, and only for an ok answer: the question as the
# pipeline passed it on after the input guards, and the answer's text after the output guards
QUESTION = "raglab.content.question"
ANSWER = "raglab.content.answer"
CONTENT_KEYS = (QUESTION, ANSWER)

# The keys that may leave the process, by the instrumentation scope that made the span
# (raglab.obs.otel.AllowlistExporter); a key nobody reviewed never does, and a span of any other
# scope leaves with no attribute at all.
#
# FastAPI 0.144.0's request span (scope "fastapi") sets server.address and server.port (from the
# request's Host header), url.path, url.query, url.scheme, http.request.method,
# network.protocol.version, http.route, http.response.status_code, and error.type (an escaped
# exception's class name). Only method, route and status code leave: never a header, a query or a
# client address.
FASTAPI_SCOPE = "fastapi"
HTTP_KEYS = frozenset({"http.request.method", "http.route", "http.response.status_code"})

# raglab's spans (scope "raglab"); the content keys leave only while the opt-in is on
RAGLAB_SCOPE = "raglab"
SPAN_KEYS = frozenset(
    {
        OPERATION,
        PROVIDER,
        REQUEST_MODEL,
        REQUEST_SEED,
        REQUEST_TEMPERATURE,
        REQUEST_TOP_P,
        REQUEST_MAX_TOKENS,
        REQUEST_REASONING,
        OUTPUT_TYPE,
        PROMPT_NAME,
        USAGE_INPUT_TOKENS,
        USAGE_OUTPUT_TOKENS,
        EMBEDDING_DIMENSIONS,
        DATA_SOURCE_ID,
        RETRIEVAL_TOP_K,
        ERROR_TYPE,
        SERVER_ADDRESS,
        SERVER_PORT,
        PROMPT_VERSION,
        STATUS,
        LABEL,
        TENANT,
        RETRIEVED_IDS,
        CITED_IDS,
        RETRIEVED_COUNT,
        GUARD,
        GUARD_STAGE,
        GUARD_REASON,
        EMBEDDER_REVISION,
        MODEL_DIGEST,
    }
)
RESOURCE_KEYS = frozenset({"service.name", "service.version"})
