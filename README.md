# Telize

**Unleash orchestrated AI agents with superhuman reach—build intricate, multi-stage workflows in YAML and command their power from your terminal, under your complete control.**

Telize is a low-code framework for building agent-style pipelines: chain shell commands, file I/O, LLM calls, Python functions, and nested flows in a single workflow file. Configuration is validated before execution, and the CLI shows live progress as each step completes.

[CI](https://github.com/telize-ai/telize/actions/workflows/ci.yml) · [Python 3.12+](https://www.python.org/downloads/) · [License](LICENSE)

---

## Table of contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick start](#quick-start)
- [How it works](#how-it-works)
- [Workflow reference](#workflow-reference)
- [Examples](#examples)
- [CLI](#cli)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

## Features

- **YAML workflows** — one file defines global config, named flows, and steps
- **Composable steps** — `input`, `llm`, `shell`, `python`, `flow`, and `yaml` actions
- **Jinja templating** — wire step outputs together with `{{ steps.name.output }}`
- **Loops and sub-flows** — iterate LLM steps over split lists; call nested flows with `uses: flow`
- **Validated upfront** — Pydantic models catch schema errors before any step runs
- **Rich CLI output** — progress, step panels, and errors in the terminal
- **OpenAI-compatible LLMs** — official OpenAI API or local [Ollama](https://ollama.com/) via the same client

## Requirements

- **Python 3.12+**
- **LLM endpoint** for `uses: llm` steps — [OpenAI](https://platform.openai.com/) or [Ollama](https://ollama.com/) (OpenAI-compatible at `http://localhost:11434` by default)
- Optional: [uv](https://docs.astral.sh/uv/) for fast local development

## Installation

```bash
pip install telize
```

From source:

```bash
git clone https://github.com/telize-ai/telize.git
cd telize
uv sync
uv pip install -e .
```

Check the install:

```bash
telize --version
```

## Quick start

**1.** For local models, start [Ollama](https://ollama.com/) and pull a model:

```bash
ollama pull qwen3.5:4b   # or any model you set in config
```

For OpenAI Cloud, set `OPENAI_API_KEY` and use `api_base_url: https://api.openai.com/v1` (or omit `api_base_url` to use the SDK default).

**2.** Create `hello.yaml`:

```yaml
config:
  provider: openai
  model: qwen3.5:4b
  api_base_url: http://localhost:11434
  entrypoint: main

flows:
  main:
    steps:
      - name: greet
        uses: llm
        prompt: Say hello in one friendly sentence.
```

**3.** Run it:

```bash
telize -f hello.yaml
```

Validate the file without executing steps:

```bash
telize -f hello.yaml --validate-only
```

Run the bundled examples:

```bash
telize -f examples/minimal_llm.yaml
telize -f examples/spec_reference.yaml --validate-only
```

## How it works

```
┌─────────────┐      ┌──────────────┐     ┌─────────────────┐
│  workflow   │─────>│  load +      │────>│  WorkflowRunner │
│  .yaml      │      │  validate    │     │  (entrypoint)   │
└─────────────┘      └──────────────┘     └────────┬────────┘
                                                   │
                     ┌─────────────────────────────┼────────────────────────────┐
                     ▼                             ▼                            ▼
                   steps                         loops                       sub-flow
              (step → step)                (split & iterate)               (uses: flow)
```

1. Telize loads your YAML and validates it against typed models.
2. The flow named in `config.entrypoint` runs first.
3. Each step executes through a registered action (`input`, `llm`, `shell`, …).
4. Later steps can reference earlier outputs via Jinja templates.
5. The CLI prints progress and results as the workflow runs.

## Workflow reference

### Top-level structure

| Key | Description |
|-----|-------------|
| `config` | Global settings: `entrypoint`, `provider`, `model`, `temperature`, `api_base_url`, `api_key`, `system_prompt` |
| `flows` | Named flows; `config.entrypoint` must match one of these keys |

### Flow

| Field | Description |
|-------|-------------|
| `steps` | List of steps (unique `name` per flow), executed in order |

### Steps (`uses`)

| `uses` | Description |
|--------|-------------|
| `input` | Read a `file` or a `directory` (with glob `include`) |
| `llm` | Send a `prompt` to the configured model; optional `output_to`, `loop` |
| `shell` | Run `run` commands; optional `envs` (supports templates) |
| `python` | Call `call` (`module.function`) with `args` |
| `flow` | Run another flow via `run` |
| `yaml` | Run an external workflow from `file` (own `config` and `flows`); optional `input` map passed to the child as `{{ input.key }}` |

### Templating

Telize uses [Jinja2](https://jinja.palletsprojects.com/) in step fields.

| When | What you can use |
|------|------------------|
| **Load time** | `{{ env.VAR }}` — expanded when the file is parsed |
| **Runtime** | `{{ steps.<name>.output }}`, `{{ config.model }}`, `{{ input.<key> }}`, `{{ item }}` (inside loops) |

Workflow **input** is provided when invoking Telize from the shell (`--input`, `--input-file`, `--input-stdin`) or by a parent `yaml` step's `input` map when running a nested workflow.

Example — chain a shell step into an LLM step:

```yaml
- name: fetch_data
  uses: shell
  run: cat ./data.txt

- name: summarize
  uses: llm
  prompt: |
    Summarize this:
    {{ steps.fetch_data.output }}
```

## Examples

| File | What it demonstrates |
|------|----------------------|
| [`examples/spec_reference.yaml`](examples/spec_reference.yaml) | Full specification reference (all step types and fields) |
| [`examples/minimal_llm.yaml`](examples/minimal_llm.yaml) | Smallest runnable LLM workflow |
| [`examples/shell_to_llm.yaml`](examples/shell_to_llm.yaml) | Shell → LLM with `{{ steps.*.output }}` |
| [`examples/read_file.yaml`](examples/read_file.yaml) | `uses: input` — single file |
| [`examples/read_directory.yaml`](examples/read_directory.yaml) | `uses: input` — directory glob |
| [`examples/llm_save_output.yaml`](examples/llm_save_output.yaml) | `output_to` — persist LLM text to disk |
| [`examples/llm_loop.yaml`](examples/llm_loop.yaml) | `loop` — split output and iterate |
| [`examples/call_subflow.yaml`](examples/call_subflow.yaml) | `uses: flow` — sub-flow in the same file |
| [`examples/nested_workflow.yaml`](examples/nested_workflow.yaml) | `uses: yaml` — external workflow + `input` |
| [`examples/python_step.yaml`](examples/python_step.yaml) | `uses: python` — call a Python function |
| [`examples/multi_model.yaml`](examples/multi_model.yaml) | Multiple named `models` profiles |
| [`examples/shell_with_env.yaml`](examples/shell_with_env.yaml) | Shell `envs` and load-time `{{ env.* }}` |
| [`examples/env_config.yaml`](examples/env_config.yaml) | `{{ env.VAR }}` in the `models` section at load time |

## CLI

```
usage: telize [-h] [--version] [-f FILE] [--validate-only]

options:
  -h, --help         show help
  --version          show version
  -f, --file FILE    path to workflow YAML
  --validate-only    parse and validate without running steps
```

## Development

```bash
uv sync
uv run pytest
uv run ruff check .
uv run ruff format .
uv run mypy
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for pull request guidelines and [CHANGELOG.md](CHANGELOG.md) for release notes.

## Contributing

Contributions are welcome — bug reports, docs, and pull requests. Please read [CONTRIBUTING.md](CONTRIBUTING.md) and open an [issue](https://github.com/telize-ai/telize/issues) before large changes.

## License

Apache License 2.0 — see [LICENSE](LICENSE).

---

<p align="center">
  <a href="https://github.com/telize-ai/telize">GitHub</a> ·
  <a href="https://github.com/telize-ai/telize/issues">Issues</a> ·
  <a href="CHANGELOG.md">Changelog</a>
</p>
