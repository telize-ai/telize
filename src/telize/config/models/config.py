from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class GlobalConfig(BaseModel):
    """Top-level workflow settings."""

    model_config = ConfigDict(extra="forbid")

    entrypoint: str = Field(
        description="Name of the flow in `flows` that runs when the file is executed.",
    )
    repeat: int | None = Field(
        default=None,
        ge=-1,
        description=(
            "Repeat the entrypoint flow on a timer. Omitted, null, or -1: run once. "
            "0: restart immediately after each run finishes. "
            "N>0: restart N seconds after each run started; if a run exceeds N seconds, "
            "restart immediately when it finishes."
        ),
    )


class ModelConfig(BaseModel):
    """LLM connection and generation settings referenced by llm steps."""

    model_config = ConfigDict(extra="forbid")

    provider: str = Field(
        default="openai",
        description="Registered LLM provider id (default: openai).",
    )
    model: str = Field(
        description="Model id passed to the provider (e.g. 'gpt-4o-mini' or 'qwen3.5:4b').",
    )
    temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Sampling temperature.",
    )
    api_url: str = Field(
        default="http://localhost:11434",
        description=(
            "OpenAI-compatible API base URL. For local Ollama use "
            "http://localhost:11434 (/v1 is appended automatically)."
        ),
    )
    api_key: str | None = Field(
        default=None,
        description=(
            "API key for the provider. Use {{ env.OPENAI_API_KEY }} or leave unset "
            "to read OPENAI_API_KEY; local Ollama accepts any placeholder when unset."
        ),
    )
    system_prompt: str | None = Field(
        default=None,
        description="System message for llm steps using this model (Jinja-templated at runtime).",
    )
