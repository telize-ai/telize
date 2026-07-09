from __future__ import annotations

import json

import httpx
import pytest

from telize.config.models import ModelConfig
from telize.exceptions import ExecutionError
from telize.providers.openai import OpenAILLMClient, normalize_openai_base_url
from telize.providers.registry import get_llm_client, register_provider, registered_providers


def _chat_completion_response(content: str) -> dict[str, object]:
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 0,
        "model": "test",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
    }


def test_normalize_openai_base_url_appends_v1() -> None:
    assert normalize_openai_base_url("http://localhost:11434") == "http://localhost:11434/v1"
    assert normalize_openai_base_url("http://localhost:11434/v1") == "http://localhost:11434/v1"
    assert normalize_openai_base_url("http://localhost:11434/v1/") == "http://localhost:11434/v1"


def test_chat_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        payload = json.loads(request.content)
        assert payload["model"] == "qwen3.5:4b"
        assert payload["messages"] == [{"role": "user", "content": "Hello"}]
        assert payload["temperature"] == 0.5
        return httpx.Response(200, json=_chat_completion_response("Hi there!"))

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport, base_url="http://llm.test")
    client = OpenAILLMClient.from_params(
        base_url="http://llm.test",
        api_key="test",
        model="qwen3.5:4b",
        temperature=0.5,
        http_client=http_client,
    )
    assert client.chat("Hello") == "Hi there!"
    client.close()


def test_chat_with_system_prompt() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["messages"] == [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"},
        ]
        return httpx.Response(200, json=_chat_completion_response("Hi!"))

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport, base_url="http://llm.test")
    client = OpenAILLMClient.from_params(
        base_url="http://llm.test",
        api_key="test",
        model="m",
        http_client=http_client,
    )
    assert client.chat("Hello", system="You are a helpful assistant.") == "Hi!"
    client.close()


def test_chat_connection_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport, base_url="http://localhost:11434")
    client = OpenAILLMClient.from_params(
        base_url="http://localhost:11434",
        api_key="test",
        model="m",
        http_client=http_client,
    )
    with pytest.raises(ExecutionError, match="Could not reach LLM API"):
        client.chat("test")
    client.close()


def test_from_config_uses_api_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    model_config = ModelConfig(
        provider="openai",
        model="llama3",
        api_url="http://custom:11434",
    )
    client = OpenAILLMClient.from_config(model_config)
    assert str(client._client.base_url).rstrip("/") == "http://custom:11434/v1"
    client.close()


def test_get_llm_client_unknown_provider() -> None:
    model_config = ModelConfig(provider="does-not-exist", model="m")
    with pytest.raises(ExecutionError, match="Unknown LLM provider"):
        get_llm_client(model_config)


def test_openai_provider_registered() -> None:
    assert "openai" in registered_providers()


def test_model_config_thinking_defaults_true() -> None:
    model_config = ModelConfig(provider="openai", model="m")
    assert model_config.thinking is True


def test_chat_thinking_disabled_sends_reasoning_effort_none() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["reasoning_effort"] == "none"
        assert "temperature" not in payload
        return httpx.Response(200, json=_chat_completion_response("Fast reply"))

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport, base_url="http://llm.test")
    client = OpenAILLMClient.from_params(
        base_url="http://llm.test",
        api_key="test",
        model="qwen3.5:4b",
        thinking=False,
        http_client=http_client,
    )
    assert client.chat("Hello") == "Fast reply"
    client.close()


def test_chat_thinking_enabled_omits_reasoning_effort() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert "reasoning_effort" not in payload
        return httpx.Response(200, json=_chat_completion_response("Thoughtful reply"))

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport, base_url="http://llm.test")
    client = OpenAILLMClient.from_params(
        base_url="http://llm.test",
        api_key="test",
        model="qwen3.5:4b",
        thinking=True,
        http_client=http_client,
    )
    assert client.chat("Hello") == "Thoughtful reply"
    client.close()


def test_from_config_passes_thinking() -> None:
    model_config = ModelConfig(
        provider="openai",
        model="qwen3.5:4b",
        api_url="http://llm.test",
        thinking=False,
    )
    client = OpenAILLMClient.from_config(model_config)
    assert client._thinking is False
    client.close()


def test_register_custom_provider() -> None:
    class StubClient:
        def chat(self, prompt: str, *, system: str | None = None) -> str:
            return f"stub:{prompt}"

        def close(self) -> None:
            pass

        def __enter__(self) -> StubClient:
            return self

        def __exit__(self, *args: object) -> None:
            pass

    register_provider("stub", lambda _cfg: StubClient())
    model_config = ModelConfig(provider="stub", model="m")
    with get_llm_client(model_config) as client:
        assert client.chat("ping") == "stub:ping"
