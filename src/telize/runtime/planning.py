from __future__ import annotations

from telize.config.models import FlowRefStep, WorkflowSpec


def estimate_step_count(spec: WorkflowSpec, flow_name: str, visited: set[str] | None = None) -> int:
    """Estimate how many leaf steps run (including nested flows)."""
    seen = visited if visited is not None else set()
    if flow_name in seen:
        return 0
    seen.add(flow_name)

    flow = spec.flows[flow_name]
    total = 0
    for step in flow.steps:
        if isinstance(step, FlowRefStep):
            total += 1 + estimate_step_count(spec, step.run, seen)
        else:
            total += 1
    return total
