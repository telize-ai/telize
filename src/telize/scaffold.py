# ruff: noqa: E501
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from telize.exceptions import ConfigError

_FLOW_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")

_WORKFLOW_TEMPLATE = """\
# Starter Telize workflow — shell and Python only (no LLM required).
#
# Run:
#   telize -f {workflow_name}.yaml
#
# Validate without running:
#   telize -f {workflow_name}.yaml --validate-only

config:
  entrypoint: main

flows:
  main:
    steps:
      - name: simple_shell
        uses: shell
        run: echo "Some text"

      - name: process_in_python
        uses: python
        call: scripts.process.process_func
        args:
          input: "{{{{ steps.simple_shell.output }}}}"

      - name: process_shell
        uses: shell
        run: echo "{{{{ steps.process_in_python.output }}}}" | tr a-z A-Z
"""

_PROCESS_PY = '''\
"""Example Python helpers for Telize workflows."""


def process_func(input: str) -> str:
    """Summarize text received from a prior step."""
    text = input.strip()
    return f"Received text of length: {len(text)}"
'''

_PROJECT_README = """\
# {workflow_name}

Starter [Telize](https://github.com/telize-ai/telize) workflow — shell and Python only, no LLM or API keys required.

## Quick start

```bash
telize -f {workflow_name}.yaml
```

Validate the workflow without running steps:

```bash
telize -f {workflow_name}.yaml --validate-only
```

## What this project does

The workflow in `{workflow_name}.yaml` runs three steps in order:

1. **simple_shell** — runs `echo` and produces some text
2. **process_in_python** — passes that text to `scripts.process.process_func`
3. **process_shell** — prints the Python step's output (uppercased via `tr`)

Steps pass data with Jinja templates, for example `{{{{ steps.simple_shell.output }}}}`.

## Project layout

```
{workflow_name}.yaml   # workflow definition (config, flows, steps)
scripts/
  process.py           # Python helpers called with `uses: python`
```

Telize adds this directory to the Python import path, so `call: scripts.process.process_func` resolves from the workflow file's location.

## Python steps

Reference a function by import path and pass arguments that match its parameters:

```yaml
- name: my_step
  uses: python
  call: scripts.process.process_func
  args:
    input: "{{{{ steps.some_prior_step.output }}}}"
```

Return values are converted to strings and become `{{{{ steps.<name>.output }}}}` for later steps.

To add your own helper, create `scripts/<module>.py` and use `call: scripts.<module>.<function>`.

## Next steps

- Add more steps to `{workflow_name}.yaml` (`shell`, `python`, `input`, and more)
- See the [Telize workflow reference](https://github.com/telize-ai/telize#-workflow-reference) for LLM steps, loops, and sub-flows
- Browse [examples](https://github.com/telize-ai/telize/tree/main/examples) in the Telize repository
"""


@dataclass(frozen=True)
class ScaffoldResult:
    """Paths created by :func:`create_starter_project`."""

    workflow: Path
    readme: Path
    scripts_dir: Path
    process_module: Path


def normalize_flow_name(flow_name: str) -> str:
    """Return a safe workflow basename without a YAML extension."""
    name = flow_name.strip()
    if not name:
        msg = "flow name cannot be empty"
        raise ConfigError(msg)

    if name.endswith((".yaml", ".yml")):
        name = Path(name).stem

    if name in {".", ".."} or "/" in name or "\\" in name:
        msg = f"invalid flow name '{flow_name}'"
        raise ConfigError(msg)

    if not _FLOW_NAME_RE.fullmatch(name):
        msg = (
            f"invalid flow name '{flow_name}'; use letters, numbers, hyphens, "
            "and underscores (must start with a letter or number)"
        )
        raise ConfigError(msg)

    return name


def create_starter_project(
    flow_name: str,
    *,
    target_dir: Path | None = None,
) -> ScaffoldResult:
    """Create a minimal runnable workflow and supporting files."""
    name = normalize_flow_name(flow_name)
    root = (target_dir or Path.cwd()).resolve()

    workflow_path = root / f"{name}.yaml"
    readme_path = root / "README.md"
    scripts_dir = root / "scripts"
    process_module = scripts_dir / "process.py"

    planned = (workflow_path, readme_path, process_module)
    existing = [path for path in planned if path.exists()]
    if existing:
        paths = ", ".join(str(path.relative_to(root)) for path in existing)
        msg = f"refusing to overwrite existing file(s): {paths}"
        raise ConfigError(msg)

    scripts_dir.mkdir(parents=True, exist_ok=True)
    workflow_path.write_text(_WORKFLOW_TEMPLATE.format(workflow_name=name), encoding="utf-8")
    readme_path.write_text(_PROJECT_README.format(workflow_name=name), encoding="utf-8")
    process_module.write_text(_PROCESS_PY, encoding="utf-8")

    return ScaffoldResult(
        workflow=workflow_path,
        readme=readme_path,
        scripts_dir=scripts_dir,
        process_module=process_module,
    )
