"""The judge model DeepEval calls (S5, AC10): a DeepEvalBaseLLM subclass over raglab's judge adapter
(raglab.judge.build.judge_from_config: the local OpenAI-compatible server, the pinned tag and
digest checked when it starts). Every call DeepEval makes goes through it, so its tokens are
recorded as any judge call's are, and the digest pin holds.

DeepEval 4.3.1's custom-model interface (https://deepeval.com/guides/guides-using-custom-llms,
read 2026-10-20; the abstract methods checked on the installed package): `get_model_name`,
`load_model`, and `generate` and `a_generate`, which take the prompt and an optional pydantic
schema and return an instance of it (or the text, without one). A call with a schema asks the
server for that schema as its response format (the judge config's json_schema); its reply is
validated against the schema, never repaired: a reply off it raises, and DeepEval reports it.
"""

from dataclasses import dataclass

from deepeval.models import DeepEvalBaseLLM
from pydantic import BaseModel, ValidationError

from raglab.core.ports import ChatModel
from raglab.core.types import ChatMessage, ChatRequest


@dataclass(frozen=True)
class Call:
    """One call DeepEval made: the schema it asked for, the tokens the server reported, and
    whether the reply fitted the schema."""

    schema: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    fitted: bool


class RaglabJudgeLLM(DeepEvalBaseLLM):
    """DeepEval's judge: structured calls through the json_schema adapter, plain text through
    the adapter without a response format."""

    def __init__(self, structured: ChatModel, plain: ChatModel, seed: int) -> None:
        self.structured = structured
        self.plain = plain
        self.seed = seed
        self.calls: list[Call] = []
        super().__init__(model=structured.model)

    def load_model(self, *args: object, **kwargs: object) -> "RaglabJudgeLLM":
        return self

    def get_model_name(self, *args: object, **kwargs: object) -> str:
        return f"raglab judge {self.structured.model}"

    def generate(  # type: ignore[override]
        self, prompt: str, schema: type[BaseModel] | None = None, **kwargs: object
    ) -> BaseModel | str:
        chat = self.structured if schema is not None else self.plain
        request = ChatRequest(
            (ChatMessage("user", prompt),),
            schema.__name__ if schema is not None else "text",
            schema.model_json_schema() if schema is not None else {},
            self.seed,
        )
        reply = chat.complete(request)
        if schema is None:
            self.calls.append(Call(None, reply.prompt_tokens, reply.completion_tokens, True))
            return reply.text
        try:
            instance = schema.model_validate_json(reply.text)
        except ValidationError:
            self.calls.append(
                Call(schema.__name__, reply.prompt_tokens, reply.completion_tokens, False)
            )
            raise
        self.calls.append(Call(schema.__name__, reply.prompt_tokens, reply.completion_tokens, True))
        return instance

    async def a_generate(  # type: ignore[override]
        self, prompt: str, schema: type[BaseModel] | None = None, **kwargs: object
    ) -> BaseModel | str:
        return self.generate(prompt, schema)

    def tokens(self) -> dict[str, int]:
        """The calls so far and the tokens their server reported; unreported, never estimated."""
        reported = [
            (c.prompt_tokens, c.completion_tokens)
            for c in self.calls
            if c.prompt_tokens is not None and c.completion_tokens is not None
        ]
        return {
            "calls": len(self.calls),
            "prompt": sum(p for p, _ in reported if p is not None),
            "completion": sum(q for _, q in reported if q is not None),
            "unreported": len(self.calls) - len(reported),
            "off_schema": sum(not c.fitted for c in self.calls),
        }
