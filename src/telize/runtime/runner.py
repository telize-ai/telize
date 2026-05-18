from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from telize.config import load_spec
from telize.config.models import Flow, FlowRefStep, Step, WorkflowSpec
from telize.runtime.actions.base import ActionContext
from telize.runtime.actions.registry import ActionRegistry, default_registry
from telize.runtime.context import build_template_context
from telize.runtime.observer import NullObserver, WorkflowObserver
from telize.runtime.planning import estimate_step_count
from telize.runtime.state import ExecutionState, StepResult
from telize.templating.renderer import TemplateRenderer


def entrypoint_output(spec: WorkflowSpec, state: ExecutionState) -> str:
    """Return the last step output from the workflow entrypoint flow."""
    flow = spec.flows[spec.config.entrypoint]
    if not flow.steps:
        return ""
    last_name = flow.steps[-1].name
    return state.get_output(last_name) or ""


class WorkflowRunner:
    """Execute a validated workflow spec from its configured entrypoint."""

    def __init__(
        self,
        spec: WorkflowSpec,
        spec_path: Path,
        registry: ActionRegistry | None = None,
        observer: WorkflowObserver | None = None,
        workflow_input: Mapping[str, Any] | None = None,
    ) -> None:
        self._spec = spec
        self._spec_path = spec_path.resolve()
        self._base_path = self._spec_path.parent
        self._registry = registry or default_registry()
        self._observer: WorkflowObserver = observer or NullObserver()
        self._workflow_input = dict(workflow_input or ())
        self._step_counter = 0

    def run(self) -> ExecutionState:
        entrypoint = self._spec.config.entrypoint
        estimated = estimate_step_count(self._spec, entrypoint)
        self._observer.on_workflow_start(entrypoint, estimated_steps=estimated)
        state = ExecutionState(
            config=self._spec.config,
            base_path=self._base_path,
            workflow_input=dict(self._workflow_input),
        )
        try:
            self._run_flow(entrypoint, state)
        except BaseException:
            raise
        self._observer.on_workflow_complete()
        return state

    def run_workflow_file(
        self,
        path: Path,
        workflow_input: Mapping[str, Any] | None = None,
    ) -> str:
        """Load and execute another workflow file; return its entrypoint's last output."""
        resolved = path.resolve()
        if not resolved.is_file():
            from telize.exceptions import ExecutionError

            raise ExecutionError(f"workflow file not found: {resolved}")

        child_spec = load_spec(resolved)
        child = WorkflowRunner(
            child_spec,
            resolved,
            registry=self._registry,
            observer=self._observer,
            workflow_input=workflow_input,
        )
        child_state = child.run()
        return entrypoint_output(child_spec, child_state)

    def _run_flow(self, flow_name: str, state: ExecutionState) -> str:
        flow = self._spec.flows[flow_name]
        self._observer.on_flow_start(flow_name)
        try:
            result = self._run_steps(flow, flow_name, state)
        finally:
            self._observer.on_flow_complete(flow_name)
        return result

    def _run_steps(self, flow: Flow, flow_name: str, state: ExecutionState) -> str:
        last_output = ""
        for step in flow.steps:
            last_output = self._run_step(step, flow_name, state)
        return last_output

    def _run_step(self, step: Step, flow_name: str, state: ExecutionState) -> str:
        self._step_counter += 1
        index = self._step_counter

        if isinstance(step, FlowRefStep):
            self._observer.on_step_start(flow_name, step, index=index)
            try:
                output = self._run_flow(step.run, state)
                result = StepResult(
                    name=step.name,
                    output=output,
                    uses=step.uses,
                    flow_name=flow_name,
                )
                state.set_step(result)
                self._observer.on_step_complete(flow_name, step, result)
            except BaseException as exc:
                self._observer.on_step_error(flow_name, step, exc)
                raise
            return output

        self._execute_step(step, flow_name, state, index=index)
        record = state.steps[step.name]
        return record.output

    def _execute_step(
        self,
        step: Step,
        flow_name: str,
        state: ExecutionState,
        *,
        index: int | None = None,
    ) -> None:
        if index is None:
            self._step_counter += 1
            index = self._step_counter

        self._observer.on_step_start(flow_name, step, index=index)
        renderer = TemplateRenderer(build_template_context(state))

        def run_flow(name: str) -> str:
            return self._run_flow(name, state)

        ctx = ActionContext(
            state=state,
            renderer=renderer,
            base_path=self._base_path,
            run_flow=run_flow,
            run_workflow_file=self.run_workflow_file,
        )
        try:
            result = self._registry.execute(step, ctx)
            result.uses = step.uses
            result.flow_name = flow_name
            state.set_step(result)
            self._observer.on_step_complete(flow_name, step, result)
        except BaseException as exc:
            self._observer.on_step_error(flow_name, step, exc)
            raise
