"""The judge a judge config names (raglab.evals.config.JudgeConfig): its chat model built by the
adapters' factory, which refuses to start unless the server holds the pinned tag at the pinned
digest, wrapped in the judge over the ChatModel port."""

from raglab.adapters import factory
from raglab.evals.config import JudgeConfig
from raglab.judge.llm import LLMJudge

type Json = dict[str, object]


def judge_from_config(
    config: JudgeConfig, response_format: str | None = None
) -> tuple[LLMJudge, Json, str]:
    """(judge, what the record says about its model, provenance). response_format overrides the
    config's, for the live contract test's probe of the other format only."""
    spec = config.judge
    chat, description, provenance = factory.chat(
        spec.provider,
        spec.model,
        digest=spec.digest,
        base_url=spec.base_url,
        temperature=spec.temperature,
        top_p=spec.top_p,
        max_tokens=spec.max_tokens,
        timeout_s=spec.timeout_s,
        extra=spec.extra(),
        response_format=response_format or spec.response_format or "json_schema",
    )
    return LLMJudge(chat), description, provenance
