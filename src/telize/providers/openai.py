from __future__ import annotations

import os

import httpx
from openai import APIConnectionError, APIStatusError, OpenAI
from openai.types.chat import ChatCompletionMessageParam

from telize.config.models import ModelConfig
from telize.exceptions import ExecutionError


def normalize_openai_base_url(base_url: str) -> str:
    """Ensure base URL targets an OpenAI-compatible API (``/v1`` suffix)."""
    base = base_url.rstrip("/")
    if base.endswith("/v1"):
        return base
    return f"{base}/v1"


def resolve_api_key(model_config: ModelConfig) -> str:
    """Resolve API key from model config, then env; use a placeholder for local Ollama."""
    if model_config.api_key:
        return model_config.api_key
    env_key = os.environ.get("OPENAI_API_KEY")
    if env_key:
        return env_key
    # Ollama's OpenAI-compatible endpoint accepts any non-empty key.
    return "ollama"


class OpenAILLMClient:
    """LLM client backed by the official OpenAI Python SDK.

      Works with OpenAI and any OpenAI-compatible endpoint (e.g. local Ollama at
    ``http://localhost:11434/v1``).
    """

    def __init__(
        self,
        client: OpenAI,
        model: str,
        temperature: float | None = None,
    ) -> None:
        self._client = client
        self._model = model
        self._temperature = temperature

    @classmethod
    def from_config(cls, model_config: ModelConfig) -> OpenAILLMClient:
        return cls(
            client=OpenAI(
                base_url=normalize_openai_base_url(model_config.api_url),
                api_key=resolve_api_key(model_config),
            ),
            model=model_config.model,
            temperature=model_config.temperature,
        )

    @classmethod
    def from_params(
        cls,
        *,
        base_url: str,
        api_key: str,
        model: str,
        temperature: float | None = None,
        http_client: httpx.Client | None = None,
    ) -> OpenAILLMClient:
        """Build a client with explicit parameters (used in tests)."""
        client = OpenAI(
            base_url=normalize_openai_base_url(base_url),
            api_key=api_key,
            http_client=http_client,
        )
        return cls(client=client, model=model, temperature=temperature)

    def chat(self, prompt: str, *, system: str | None = None) -> str:
        messages: list[ChatCompletionMessageParam] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            if self._temperature is not None:
                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    temperature=self._temperature,
                )
            else:
                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                )
        except APIStatusError as exc:
            detail = exc.message or str(exc)
            raise ExecutionError(f"LLM API returned HTTP {exc.status_code}: {detail}") from exc
        except APIConnectionError as exc:
            raise ExecutionError(f"Could not reach LLM API: {exc}") from exc

        if not response.choices:
            raise ExecutionError(f"LLM API returned no choices: {response!r}")

        content = response.choices[0].message.content
        if not isinstance(content, str) or not content.strip():
            raise ExecutionError(f"LLM API returned an empty response: {response!r}")
        return content.strip()

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> OpenAILLMClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
