from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class GlobalConfig(BaseModel):
    """Top-level defaults and entrypoint for a workflow file."""

    model_config = ConfigDict(extra="forbid")

    model: str | None = Field(
        default=None,
        description="Default LLM model for steps that do not override it.",
    )
    temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Default sampling temperature.",
    )
    api_base_url: str = Field(
        default="http://localhost:11434",
        description="Ollama API base URL (default local instance).",
    )
    system_prompt: str | None = Field(
        default=None,
        description="System message for every llm step (Jinja-templated at runtime).",
    )
    entrypoint: str = Field(
        description="Name of the flow in `flows` that runs when the file is executed.",
    )
