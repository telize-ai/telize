from __future__ import annotations

from croniter import croniter
from pydantic import BaseModel, ConfigDict, Field, field_validator


class GlobalConfig(BaseModel):
    """Top-level workflow settings."""

    model_config = ConfigDict(extra="forbid")

    entrypoint: str = Field(
        description="Name of the flow in `flows` that runs when the file is executed.",
    )
    cron: str | None = Field(
        default=None,
        description=(
            "Cron schedule for the entrypoint flow. Omitted or null: run once. "
            "When set, the workflow runs on the given cron expression (standard "
            "five-field syntax, e.g. '0 * * * *' for every hour)."
        ),
    )

    @field_validator("cron")
    @classmethod
    def validate_cron(cls, value: str | None) -> str | None:
        if value is not None and not croniter.is_valid(value):
            msg = f"invalid cron expression: {value!r}"
            raise ValueError(msg)
        return value


class ModelConfig(BaseModel):
    """LLM connection and generation settings referenced by llm steps."""

    model_config = ConfigDict(extra="forbid")

    provider: str = Field(
        default="openai",
        description=(
            "Registered provider id. Use `openai` for LLM chat steps; "
            "use `local` for embedding models on `text_search` steps."
        ),
    )
    model: str = Field(
        description=(
            "Model id passed to the provider. For LLM steps: chat model name "
            "(e.g. 'gpt-4o-mini'). For local embedding steps: HuggingFace model id "
            "(e.g. 'sentence-transformers/all-MiniLM-L6-v2')."
        ),
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
    thinking: bool = Field(
        default=True,
        description=(
            "Enable reasoning/thinking for capable models (e.g. qwen3.5). "
            "When false, sends reasoning_effort=none to the API."
        ),
    )
