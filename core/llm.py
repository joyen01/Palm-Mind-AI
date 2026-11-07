"""Model clients: OpenAI for embeddings and Anthropic Claude for chat, used through their SDKs."""

from collections.abc import Sequence
from functools import lru_cache
from typing import Literal

from anthropic import Anthropic, transform_schema
from anthropic.types import (
    AssistantMessageParam,
    ContentBlock,
    OutputConfigParam,
    TextBlock,
    UserMessageParam,
)
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from openai import OpenAI
from pydantic import BaseModel

ChatMessage = UserMessageParam | AssistantMessageParam


def chat_message(role: Literal["user", "assistant"], content: str) -> ChatMessage:
    """Build one message for a chat request."""
    if role == "user":
        return {"role": "user", "content": content}
    return {"role": "assistant", "content": content}


class Embedder:
    """Turns text into embedding vectors with an OpenAI embedding model."""

    def __init__(self, client: OpenAI, model: str, dimensions: int) -> None:
        self._client = client
        self._model = model
        self._dimensions = dimensions

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self._client.embeddings.create(
            model=self._model,
            input=list(texts),
            dimensions=self._dimensions,
        )
        # The API returns one item per input; sort by index to keep input order.
        return [item.embedding for item in sorted(response.data, key=lambda item: item.index)]

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]


class ChatModel:
    """Chat completions and schema-constrained extraction with Anthropic Claude."""

    def __init__(self, client: Anthropic, model: str, max_tokens: int) -> None:
        self._client = client
        self._model = model
        self._max_tokens = max_tokens

    def complete(self, system: str, messages: Sequence[ChatMessage]) -> str:
        """Return the model's free-text reply to the conversation."""
        response = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system,
            messages=list(messages),
        )
        return _text_of(response.content)

    def extract[ModelT: BaseModel](
        self,
        system: str,
        messages: Sequence[ChatMessage],
        schema: type[ModelT],
    ) -> ModelT:
        """Return the model's reply parsed into ``schema``.

        Decoding is constrained to the JSON schema generated from ``schema``.
        """
        output_config: OutputConfigParam = {
            "format": {"type": "json_schema", "schema": transform_schema(schema)},
        }
        response = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system,
            messages=list(messages),
            output_config=output_config,
        )
        return schema.model_validate_json(_text_of(response.content))


def _text_of(blocks: Sequence[ContentBlock]) -> str:
    return "".join(block.text for block in blocks if isinstance(block, TextBlock)).strip()


def _require_setting(value: str, name: str) -> str:
    if not value:
        raise ImproperlyConfigured(f"{name} must be set.")
    return value


@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    client = OpenAI(
        api_key=_require_setting(settings.OPENAI_API_KEY, "OPENAI_API_KEY"),
        timeout=settings.LLM_TIMEOUT_SECONDS,
        max_retries=2,
    )
    return Embedder(
        client=client,
        model=settings.EMBEDDING_MODEL,
        dimensions=settings.EMBEDDING_DIMENSIONS,
    )


@lru_cache(maxsize=1)
def get_chat_model() -> ChatModel:
    client = Anthropic(
        api_key=_require_setting(settings.ANTHROPIC_API_KEY, "ANTHROPIC_API_KEY"),
        timeout=settings.LLM_TIMEOUT_SECONDS,
        max_retries=2,
    )
    return ChatModel(
        client=client,
        model=settings.CHAT_MODEL,
        max_tokens=settings.CHAT_MAX_TOKENS,
    )
