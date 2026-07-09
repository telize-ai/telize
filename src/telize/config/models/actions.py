from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LoopConfig(BaseModel):
    """Iterate a step over items produced from a prior step's output."""

    model_config = ConfigDict(extra="forbid")

    items: str = Field(
        description="Jinja template resolving to a delimited list (e.g. `{{ steps.foo.output }}`).",
    )
    split_by: str = Field(
        default="\n<|separator|>\n",
        description="Delimiter used to split `items` into separate loop iterations.",
    )
    separator: str = Field(
        default="\n<|separator|>\n",
        description="String inserted between each iteration's output when joining results.",
    )


class DirectoryInput(BaseModel):
    """Read and concatenate files from a directory."""

    model_config = ConfigDict(extra="forbid")

    path: str
    include: str = Field(default="*", description="Glob pattern for files to include.")
    separator: str = Field(
        default="\n<|separator|>\n",
        description="String inserted between each file section when joining.",
    )


class _StepBase(BaseModel):
    """Fields shared by every step in a flow."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        min_length=1,
        description="Unique step id within the flow; referenced as `steps.<name>.output`.",
    )
    output_to: str | None = Field(
        default=None,
        description="Optional path to write raw step output when the step completes.",
    )
    loop: LoopConfig | None = Field(
        default=None,
        description=(
            "Optional loop config; runs the step once per item, exposing the "
            "current value as `{{ item }}` and joining outputs with `separator`."
        ),
    )


class InputStep(_StepBase):
    """Load content from a file or directory."""

    uses: Literal["input"] = "input"
    file: str | None = Field(default=None, description="Path to a single file to read.")
    directory: DirectoryInput | None = None

    @model_validator(mode="after")
    def validate_source(self) -> InputStep:
        has_file = self.file is not None
        has_dir = self.directory is not None
        if has_file == has_dir:
            msg = "input step requires exactly one of 'file' or 'directory'"
            raise ValueError(msg)
        return self


class LlmStep(_StepBase):
    """Call an LLM with a Jinja-templated prompt."""

    uses: Literal["llm"] = "llm"
    model: str = Field(
        description="Name of a model defined in the top-level `models` mapping.",
    )
    prompt: str


class ShellStep(_StepBase):
    """Execute a shell script or command block."""

    uses: Literal["shell"] = "shell"
    run: str = Field(description="Shell commands to execute.")
    envs: dict[str, str] = Field(
        default_factory=dict,
        description="Extra environment variables (values may be Jinja templates).",
    )


class PythonStep(_StepBase):
    """Invoke a Python callable by import path."""

    uses: Literal["python"] = "python"
    call: str = Field(
        description="Dotted import path to a callable, e.g. `package.module.function`.",
    )
    args: dict[str, Any] = Field(
        default_factory=dict,
        description="Keyword arguments passed to the callable (values may be templates).",
    )


class FlowRefStep(_StepBase):
    """Run another flow defined in the same workflow file."""

    uses: Literal["flow"] = "flow"
    run: str = Field(description="Name of the flow to execute.")


class ChatStep(_StepBase):
    """Prompt the user for input interactively in the terminal."""

    uses: Literal["chat"] = "chat"
    message: str = Field(
        default="",
        description="Optional message shown before collecting user input (supports Jinja).",
    )


class YamlStep(_StepBase):
    """Run a workflow defined in an external YAML file."""

    uses: Literal["yaml"] = "yaml"
    file: str = Field(
        description="Path to a Telize workflow YAML file relative to the workflow file.",
    )
    input: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Workflow input for the child file, rendered as Jinja in the parent then "
            "passed as `{{ input.<key> }}` in the child."
        ),
    )


class TextSearchStep(_StepBase):
    """Semantic search over files in a directory using ChromaDB and embedding models."""

    uses: Literal["text_search"] = "text_search"
    path: str = Field(description="Directory to index (relative to the workflow file).")
    model: str = Field(
        description="Name of a local embedding model defined in the top-level `models` mapping.",
    )
    search: str = Field(description="Search query (Jinja-templated).")
    ttl: int = Field(
        default=3600,
        ge=0,
        description=(
            "Seconds before the index is rebuilt. Reindex also runs when source "
            "files change (by modification time)."
        ),
    )
    include: str = Field(
        default="*",
        description="Glob pattern for files to index within `path`.",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        description="Maximum number of matching chunks to return.",
    )
    min_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional minimum cosine similarity (0-1); results below are dropped.",
    )
    chunk_size: int = Field(
        default=1000,
        ge=100,
        description="Target maximum characters per chunk during semantic splitting.",
    )
    chunk_overlap: int = Field(
        default=200,
        ge=0,
        description="Character overlap between consecutive chunks.",
    )
    semantic_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description=(
            "Cosine similarity threshold for semantic chunk boundaries; lower values "
            "produce more, smaller chunks."
        ),
    )


Step = Annotated[
    InputStep
    | LlmStep
    | ShellStep
    | PythonStep
    | FlowRefStep
    | ChatStep
    | YamlStep
    | TextSearchStep,
    Field(discriminator="uses"),
]
