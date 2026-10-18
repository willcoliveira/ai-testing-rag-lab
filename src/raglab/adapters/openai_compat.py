"""A chat model behind an OpenAI-compatible chat completions endpoint, over httpx (S3: Ollama on
this machine; the same API serves LM Studio, vLLM and hosted providers, which come in S5).

At start it reads the server's model list (Ollama's /api/tags) and refuses to run when the pinned
tag is not there, or is there with another digest: Ollama tags are not dated, so the config pins
the tag and its digest, and a run never uses other weights than the ones it records. It also reads
the server's version (/api/version) for the manifest.

Each request carries the config's temperature, the trial's seed, a max-tokens cap and a
per-request timeout, and asks for the answer schema as a JSON schema response format unless the
config says `response_format = "none"`: Ollama 0.40.6's MLX runner answers any response format
with HTTP 501 ("structured output is unavailable": its build has no grammar library), so the local
config relies on the prompt's instruction and the strict parser, which refuses every reply that
does not fit the schema (status invalid_output). Optional extra
fields (`reasoning_effort`, which switches the model's thinking off where the server supports it)
are sent only because the config says so, and recorded with the model. A reply that does not
come (timeout, connection error, HTTP error status) raises ChatUnavailable; a reply that comes is
returned as it is, and the caller parses it.

S3 runs local models only: a base URL whose host is not the loopback interface is refused.
"""

import ipaddress
from collections.abc import Mapping
from typing import cast
from urllib.parse import urlsplit

import httpx

from raglab.core.types import ChatReply, ChatRequest, ChatTimeout, ChatUnavailable

CHAT_PATH = "/v1/chat/completions"
TAGS_PATH = "/api/tags"
VERSION_PATH = "/api/version"
RESPONSE_FORMATS = ("json_schema", "none")


class ChatConfigError(ValueError):
    """The adapter refuses to start: the model is not pulled, its digest differs, or the server
    is not a local one."""


def is_loopback(base_url: str) -> bool:
    host = urlsplit(base_url).hostname or ""
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _json(response: httpx.Response) -> dict[str, object]:
    data: object = response.json()
    if not isinstance(data, dict):
        raise ValueError("not a JSON object")
    return {str(k): v for k, v in cast(dict[object, object], data).items()}


def _int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


class OpenAICompatChat:
    def __init__(
        self,
        base_url: str,
        model: str,
        digest: str,
        *,
        temperature: float,
        max_tokens: int,
        timeout_s: float,
        extra: Mapping[str, str] | None = None,
        response_format: str = "json_schema",
        client: httpx.Client | None = None,
    ) -> None:
        if not is_loopback(base_url):
            raise ChatConfigError(
                f"{base_url}: S3 runs a local model only; hosted providers come in S5 (ADR-002)"
            )
        if response_format not in RESPONSE_FORMATS:
            raise ChatConfigError(
                f"response_format {response_format!r} is not one of {RESPONSE_FORMATS}"
            )
        self._response_format = response_format
        self._model = model
        self._digest = digest
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._timeout_s = timeout_s
        self._extra = dict(extra or {})
        self._base_url = base_url.rstrip("/")
        self._client = client or httpx.Client(base_url=self._base_url, timeout=timeout_s)
        self._server_version = self._check_model()

    def _get(self, path: str) -> dict[str, object]:
        try:
            response = self._client.get(path, timeout=self._timeout_s)
            response.raise_for_status()
            return _json(response)
        except (httpx.HTTPError, ValueError) as error:
            raise ChatConfigError(
                f"cannot read {path} from {self._base_url}: {error} (is the server up?)"
            ) from error

    def _check_model(self) -> str:
        tags = self._get(TAGS_PATH).get("models")
        models = [
            {str(k): v for k, v in cast(dict[object, object], m).items()}
            for m in (cast(list[object], tags) if isinstance(tags, list) else [])
            if isinstance(m, dict)
        ]
        entry = next((m for m in models if self._model in (m.get("name"), m.get("model"))), None)
        if entry is None:
            raise ChatConfigError(
                f"{self._model} is not on {self._base_url}: pull it (`ollama pull {self._model}`)"
            )
        if entry.get("digest") != self._digest:
            raise ChatConfigError(
                f"{self._model} on {self._base_url} has digest {entry.get('digest')}, not the "
                f"pinned {self._digest}: a run never uses other weights than it records"
            )
        version = self._get(VERSION_PATH).get("version")
        return str(version) if version else "unknown"

    @property
    def model(self) -> str:
        return self._model

    def describe(self) -> dict[str, object]:
        return {
            "provider": "openai-compat",
            "model": self._model,
            "digest": self._digest,
            "base_url": self._base_url,
            "server_version": self._server_version,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
            "timeout_s": self._timeout_s,
            "response_format": self._response_format,
            "extra": dict(sorted(self._extra.items())),
        }

    def complete(self, request: ChatRequest) -> ChatReply:
        body: dict[str, object] = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "temperature": self._temperature,
            "seed": request.seed,
            "max_tokens": self._max_tokens,
            "stream": False,
            **self._extra,
        }
        if self._response_format == "json_schema":
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": request.schema_name,
                    "schema": request.schema,
                    "strict": True,
                },
            }
        try:
            response = self._client.post(CHAT_PATH, json=body, timeout=self._timeout_s)
        except httpx.TimeoutException as error:
            raise ChatTimeout(
                f"timeout after {self._timeout_s} s ({type(error).__name__})"
            ) from error
        except httpx.TransportError as error:
            raise ChatUnavailable(f"connection error ({type(error).__name__}: {error})") from error
        if response.status_code >= 400:
            raise ChatUnavailable(f"HTTP {response.status_code} from {CHAT_PATH}")
        try:
            data = _json(response)
            choices = cast(list[object], data["choices"])
            first = {str(k): v for k, v in cast(dict[object, object], choices[0]).items()}
            message = {str(k): v for k, v in cast(dict[object, object], first["message"]).items()}
        except (ValueError, KeyError, IndexError, TypeError, AttributeError):
            return ChatReply("")  # a reply that came but is not a completion: invalid output
        content = message.get("content")
        usage_raw = data.get("usage")
        usage = (
            {str(k): v for k, v in cast(dict[object, object], usage_raw).items()}
            if isinstance(usage_raw, dict)
            else {}
        )
        reasoning = any(
            isinstance(message.get(key), str) and str(message.get(key)).strip()
            for key in ("reasoning", "reasoning_content", "thinking")
        )
        return ChatReply(
            content if isinstance(content, str) else "",
            _int(usage.get("prompt_tokens")),
            _int(usage.get("completion_tokens")),
            reasoning,
        )
