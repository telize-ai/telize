from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from telize.config.models.actions import Step


class Flow(BaseModel):
    """A named workflow: ordered steps executed sequentially."""

    model_config = ConfigDict(extra="forbid")

    steps: list[Step] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_step_names(self) -> Flow:
        names = [step.name for step in self.steps]
        if len(names) != len(set(names)):
            duplicates = sorted({n for n in names if names.count(n) > 1})
            msg = f"duplicate step name(s) in flow: {', '.join(duplicates)}"
            raise ValueError(msg)
        return self
