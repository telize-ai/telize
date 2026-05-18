from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LoopConfig(BaseModel):
    """Iterate an LLM step over items produced from a prior step's output."""

    model_config = ConfigDict(extra="forbid")

    items: str = Field(
        description="Jinja template resolving to a delimited list (e.g. `{{ steps.foo.output }}`).",
    )
    split_by: str = Field(
        default=",",
        description="Delimiter used to split `items` into separate loop iterations.",
    )
    execution: Literal["sequential", "parallel"] = Field(
        default="sequential",
        description="How loop iterations are scheduled.",
    )


class DirectoryInput(BaseModel):
    """Read and concatenate files from a directory."""

    model_config = ConfigDict(extra="forbid")

    path: str
    include: str = Field(default="*", description="Glob pattern for files to include.")


class _StepBase(BaseModel):
    """Fields shared by every step in a flow."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        min_length=1,
        description="Unique step id within the flow; referenced as `steps.<name>.output`.",
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
    prompt: str
    output_to: str | None = Field(
        default=None,
        description="Optional path to write raw output after the step completes.",
    )
    loop: LoopConfig | None = None


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


Step = Annotated[
    InputStep | LlmStep | ShellStep | PythonStep | FlowRefStep | YamlStep,
    Field(discriminator="uses"),
]
