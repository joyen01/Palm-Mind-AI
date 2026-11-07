from collections.abc import Sequence
from functools import lru_cache
from typing import Literal, TypedDict

from django.conf import settings
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
from openai.types.shared_params import ResponseFormatJSONSchema
from pydantic import BaseModel


class ChatMessage(TypedDict):
    role: Literal["user", "assistant", "system"]
    content: str


def chat_message(role: Literal["user", "assistant"], content: str) -> ChatMessage:
    return {"role": role, "content": content}


def _format_messages(
    system: str, messages: Sequence[ChatMessage]
) -> list[ChatCompletionMessageParam]:
    formatted: list[ChatCompletionMessageParam] = [{"role": "system", "content": system}]
    for msg in messages:
        if msg["role"] == "user":
            formatted.append({"role": "user", "content": msg["content"]})
        elif msg["role"] == "assistant":
            formatted.append({"role": "assistant", "content": msg["content"]})
        elif msg["role"] == "system":
            formatted.append({"role": "system", "content": msg["content"]})
    return formatted


class Embedder:
    def __init__(self, client: OpenAI, model: str, dimensions: int) -> None:
        self._client = client
        self._model = model
        self._dimensions = dimensions

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        kwargs: dict[str, object] = {
            "model": self._model,
            "input": list(texts),
        }
        # Ollama returns native model dimensions; OpenAI supports optional dimensions parameter
        if not getattr(settings, "OLLAMA_BASE_URL", ""):
            kwargs["dimensions"] = self._dimensions

        response = self._client.embeddings.create(**kwargs)  # type: ignore[arg-type]
        return [item.embedding for item in sorted(response.data, key=lambda item: item.index)]

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]


class ChatModel:
    def __init__(self, client: OpenAI, model: str, max_tokens: int) -> None:
        self._client = client
        self._model = model
        self._max_tokens = max_tokens

    def complete(self, system: str, messages: Sequence[ChatMessage]) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=self._max_tokens,
            messages=_format_messages(system, messages),
        )
        return (response.choices[0].message.content or "").strip()

    def extract[ModelT: BaseModel](
        self,
        system: str,
        messages: Sequence[ChatMessage],
        schema: type[ModelT],
    ) -> ModelT:
        response_format: ResponseFormatJSONSchema = {
            "type": "json_schema",
            "json_schema": {
                "name": schema.__name__,
                "schema": schema.model_json_schema(),
            },
        }
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=self._max_tokens,
            messages=_format_messages(system, messages),
            response_format=response_format,
        )
        content = response.choices[0].message.content or "{}"
        return schema.model_validate_json(content)


@lru_cache(maxsize=1)
def _get_client() -> OpenAI:
    ollama_url = getattr(settings, "OLLAMA_BASE_URL", "").strip()
    if ollama_url:
        return OpenAI(
            base_url=f"{ollama_url.rstrip('/')}/v1",
            api_key="ollama",  # required by the SDK even when using Ollama
            timeout=settings.LLM_TIMEOUT_SECONDS,
            max_retries=2,
        )
    return OpenAI(
        api_key=settings.OPENAI_API_KEY,
        timeout=settings.LLM_TIMEOUT_SECONDS,
        max_retries=2,
    )


@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    return Embedder(
        client=_get_client(),
        model=settings.EMBEDDING_MODEL,
        dimensions=settings.EMBEDDING_DIMENSIONS,
    )


@lru_cache(maxsize=1)
def get_chat_model() -> ChatModel:
    return ChatModel(
        client=_get_client(),
        model=settings.CHAT_MODEL,
        max_tokens=settings.CHAT_MAX_TOKENS,
    )
