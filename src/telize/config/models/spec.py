from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator

from telize.config.models.actions import FlowRefStep, Step
from telize.config.models.config import GlobalConfig
from telize.config.models.flow import Flow


class WorkflowSpec(BaseModel):
    """Root document loaded from a Telize workflow YAML file."""

    model_config = ConfigDict(extra="forbid")

    config: GlobalConfig
    flows: dict[str, Flow]

    @model_validator(mode="after")
    def validate_entrypoint(self) -> WorkflowSpec:
        if self.config.entrypoint not in self.flows:
            known = ", ".join(sorted(self.flows))
            msg = (
                f"config.entrypoint '{self.config.entrypoint}' not found in flows. "
                f"Known flows: {known or '(none)'}"
            )
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def validate_flow_references(self) -> WorkflowSpec:
        for flow_name, flow in self.flows.items():
            for step in flow.steps:
                if isinstance(step, FlowRefStep) and step.run not in self.flows:
                    msg = (
                        f"flow '{flow_name}' step '{step.name}' references unknown flow "
                        f"'{step.run}'"
                    )
                    raise ValueError(msg)
        return self

    def get_step(self, flow_name: str, step_name: str) -> Step | None:
        flow = self.flows.get(flow_name)
        if flow is None:
            return None
        for step in flow.steps:
            if step.name == step_name:
                return step
        return None
