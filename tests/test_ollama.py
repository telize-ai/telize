from __future__ import annotations

import json

import httpx
import pytest

from telize.config.models import GlobalConfig
from telize.exceptions import ExecutionError
from telize.providers.ollama import OllamaClient


def test_chat_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/chat"
        payload = json.loads(request.content)
        assert payload["model"] == "qwen3.5:4b"
        assert payload["messages"] == [{"role": "user", "content": "Hello"}]
        assert payload["options"]["temperature"] == 0.5
        return httpx.Response(
            200,
            json={"message": {"role": "assistant", "content": "Hi there!"}},
        )

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(
        transport=transport,
        base_url="http://ollama.test",
    )
    client = OllamaClient(
        base_url="http://ollama.test",
        model="qwen3.5:4b",
        temperature=0.5,
        client=http_client,
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
        return httpx.Response(
            200,
            json={"message": {"role": "assistant", "content": "Hi!"}},
        )

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport, base_url="http://ollama.test")
    client = OllamaClient("http://ollama.test", "m", client=http_client)
    assert client.chat("Hello", system="You are a helpful assistant.") == "Hi!"
    client.close()


def test_chat_connection_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport, base_url="http://localhost:11434")
    client = OllamaClient("http://localhost:11434", "m", client=http_client)
    with pytest.raises(ExecutionError, match="Could not reach Ollama"):
        client.chat("test")
    client.close()


def test_from_config_requires_model() -> None:
    config = GlobalConfig(entrypoint="main", model=None)
    with pytest.raises(ExecutionError, match=r"config\.model is required"):
        OllamaClient.from_config(config)


def test_from_config_uses_api_base_url() -> None:
    config = GlobalConfig(
        entrypoint="main",
        model="llama3",
        api_base_url="http://custom:11434",
    )
    client = OllamaClient.from_config(config)
    assert str(client._client.base_url).rstrip("/") == "http://custom:11434"
    client.close()
