from __future__ import annotations

import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from telize.config import load_spec
from telize.config.models import Flow, FlowRefStep, Step, WorkflowSpec
from telize.runtime.actions.base import ActionContext, apply_output_to
from telize.runtime.actions.registry import ActionRegistry, default_registry
from telize.runtime.context import build_template_context
from telize.runtime.observer import NullObserver, WorkflowObserver
from telize.runtime.planning import estimate_step_count
from telize.runtime.state import ExecutionState, StepResult
from telize.templating.renderer import TemplateRenderer


def repeat_wait_seconds(repeat: int, elapsed: float) -> float:
    """Return how long to wait before the next workflow iteration."""
    if repeat == 0:
        return 0.0
    return max(0.0, repeat - elapsed)


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
        repeat = self._spec.config.repeat
        if repeat is None or repeat == -1:
            try:
                return self._run_once()
            except KeyboardInterrupt:
                self._observer.on_workflow_interrupted()
                raise

        state: ExecutionState | None = None
        while True:
            try:
                started = time.monotonic()
                state = self._run_once()
                wait = repeat_wait_seconds(repeat, time.monotonic() - started)
                if wait > 0:
                    time.sleep(wait)
            except KeyboardInterrupt:
                self._observer.on_workflow_interrupted()
                if state is not None:
                    return state
                raise
        return state  # unreachable; keeps type checkers happy

    def _run_once(self) -> ExecutionState:
        self._step_counter = 0
        entrypoint = self._spec.config.entrypoint
        estimated = estimate_step_count(self._spec, entrypoint)
        self._observer.on_workflow_start(entrypoint, estimated_steps=estimated)
        state = ExecutionState(
            config=self._spec.config,
            models=dict(self._spec.models),
            base_path=self._base_path,
            workflow_input=dict(self._workflow_input),
        )
        self._run_flow(entrypoint, state)
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

        self._observer.on_step_start(flow_name, step, index=index)
        try:
            if step.loop is None:
                result = self._run_step_core(step, state)
            else:
                result = self._run_step_loop(step, flow_name, state)
            result.uses = step.uses
            result.flow_name = flow_name
            renderer = TemplateRenderer(build_template_context(state))
            ctx = ActionContext(state=state, renderer=renderer, base_path=self._base_path)
            result = apply_output_to(step, result, ctx)
            state.set_step(result)
            self._observer.on_step_complete(flow_name, step, result)
        except KeyboardInterrupt:
            raise
        except BaseException as exc:
            self._observer.on_step_error(flow_name, step, exc)
            raise
        return result.output

    def _run_step_core(self, step: Step, state: ExecutionState) -> StepResult:
        """Run a single (non-looping) execution of a step."""
        if isinstance(step, FlowRefStep):
            output = self._run_flow(step.run, state)
            return StepResult(name=step.name, output=output)

        renderer = TemplateRenderer(build_template_context(state))
        ctx = ActionContext(
            state=state,
            renderer=renderer,
            base_path=self._base_path,
            run_flow=lambda name: self._run_flow(name, state),
            run_workflow_file=self.run_workflow_file,
        )
        return self._registry.execute(step, ctx)

    def _run_step_loop(self, step: Step, flow_name: str, state: ExecutionState) -> StepResult:
        """Run a step once per loop item, exposing each as `{{ item }}`."""
        loop = step.loop
        assert loop is not None

        renderer = TemplateRenderer(build_template_context(state))
        items_raw = renderer.render(loop.items)
        items = [part.strip() for part in items_raw.split(loop.split_by) if part.strip()]
        total = len(items)

        outputs: list[str] = []
        previous_item = state.loop_item
        try:
            for index, item in enumerate(items, start=1):
                self._observer.on_step_loop_progress(flow_name, step, current=index, total=total)
                state.loop_item = item
                outputs.append(self._run_step_core(step, state).output)
        finally:
            state.loop_item = previous_item

        combined = loop.separator.join(outputs)
        return StepResult(name=step.name, output=combined)
