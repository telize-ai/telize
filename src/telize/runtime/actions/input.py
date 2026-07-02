from __future__ import annotations

from pathlib import Path

from telize.config.models import InputStep, Step
from telize.exceptions import ExecutionError
from telize.runtime.actions.base import ActionContext, ActionExecutor
from telize.runtime.paths import resolve_under_base
from telize.runtime.state import StepResult


class InputActionExecutor(ActionExecutor):
    uses = "input"

    def execute(self, step: Step, ctx: ActionContext) -> StepResult:
        if not isinstance(step, InputStep):
            raise ExecutionError(f"expected input step, got {step.uses}")

        if step.file is not None:
            path = resolve_under_base(ctx.base_path, step.file)
            if not path.is_file():
                raise ExecutionError(f"input file not found: {path}")
            output = path.read_text(encoding="utf-8")
        else:
            assert step.directory is not None
            dir_path = resolve_under_base(ctx.base_path, step.directory.path)
            if not dir_path.is_dir():
                raise ExecutionError(f"input directory not found: {dir_path}")
            output = _read_directory(dir_path, step.directory.include, step.directory.separator)

        return StepResult(name=step.name, output=output)


def _read_directory(directory: Path, include: str, separator: str = "\n<|separator|>\n") -> str:
    pattern = include if "/" in include or "**" in include else f"**/{include}"
    files = sorted(p for p in directory.glob(pattern) if p.is_file())
    if not files:
        return ""
    parts: list[str] = []
    for file_path in files:
        rel = file_path.relative_to(directory)
        parts.append(f"## {rel}\n\n{file_path.read_text(encoding='utf-8')}")
    return separator.join(parts)
