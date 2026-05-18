from __future__ import annotations

from typing import Any

import httpx

from telize.config.models import GlobalConfig
from telize.exceptions import ExecutionError


class OllamaClient:
    """Client for the Ollama HTTP API (/api/chat)."""

    def __init__(
        self,
        base_url: str,
        model: str,
        temperature: float | None = None,
        *,
        timeout: float = 600.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._model = model
        self._temperature = temperature
        self._owns_client = client is None
        self._client = client or httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
        )

    @classmethod
    def from_config(cls, config: GlobalConfig) -> OllamaClient:
        if not config.model:
            raise ExecutionError(
                "config.model is required for llm steps (Ollama model name, e.g. 'qwen3.5:4b')"
            )
        return cls(
            base_url=config.api_base_url,
            model=config.model,
            temperature=config.temperature,
        )

    def chat(self, prompt: str, *, system: str | None = None) -> str:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "stream": False,
        }
        if self._temperature is not None:
            payload["options"] = {"temperature": self._temperature}

        try:
            response = self._client.post("/api/chat", json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text.strip() or str(exc)
            raise ExecutionError(
                f"Ollama returned HTTP {exc.response.status_code}: {detail}"
            ) from exc
        except httpx.HTTPError as exc:
            raise ExecutionError(
                f"Could not reach Ollama at {self._client.base_url}: {exc}"
            ) from exc

        data = response.json()
        content = data.get("message", {}).get("content")
        if not isinstance(content, str) or not content.strip():
            raise ExecutionError(f"Ollama returned an empty response: {data!r}")
        return content.strip()

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> OllamaClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
