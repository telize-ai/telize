from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from telize.config.models import GlobalConfig, ModelConfig


@dataclass
class StepResult:
    """Output produced by a single step execution."""

    name: str
    output: str
    output_path: Path | None = None
    uses: str = ""
    flow_name: str = ""


@dataclass
class ExecutionState:
    """Mutable runtime state shared across steps in a workflow run."""

    config: GlobalConfig
    base_path: Path
    models: dict[str, ModelConfig] = field(default_factory=dict)
    vars: dict[str, Any] = field(default_factory=dict)
    workflow_input: dict[str, Any] = field(default_factory=dict)
    steps: dict[str, StepResult] = field(default_factory=dict)
    loop_item: str | None = None

    def set_step(self, result: StepResult) -> None:
        self.steps[result.name] = result

    def get_output(self, step_name: str) -> str | None:
        record = self.steps.get(step_name)
        return record.output if record else None

    def steps_view(self) -> dict[str, dict[str, Any]]:
        """Nested view exposed to Jinja as `steps.<name>.output`."""
        return {
            name: {
                "name": name,
                "output": result.output,
                "output_path": str(result.output_path) if result.output_path else None,
            }
            for name, result in self.steps.items()
        }

    def fork(self) -> ExecutionState:
        """Copy state for sub-flow execution while preserving parent step outputs."""
        return ExecutionState(
            config=self.config,
            models=dict(self.models),
            base_path=self.base_path,
            vars=dict(self.vars),
            workflow_input=dict(self.workflow_input),
            steps=dict(self.steps),
        )
