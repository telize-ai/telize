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
- **Local LLM ready** — works with [Ollama](https://ollama.com/) out of the box

## Requirements

- **Python 3.12+**
- **[Ollama](https://ollama.com/)** (or another endpoint compatible with the Ollama API) for `uses: llm` steps — defaults to `http://localhost:11434`
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

**1.** Start Ollama and pull a model (if you use LLM steps):

```bash
ollama pull qwen3.5:4b   # or any model you set in config
```

**2.** Create `hello.yaml`:

```yaml
config:
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
telize -f examples/hello_simple.yaml
telize -f examples/hello_agent.yaml
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
| `config` | Global settings: `entrypoint`, `model`, `temperature`, `api_base_url`, `system_prompt` |
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
| [`examples/hello_simple.yaml`](examples/hello_simple.yaml) | Minimal pipeline: shell → LLM |
| [`examples/hello_agent.yaml`](examples/hello_agent.yaml) | Full showcase: input, loops, shell, python, and sub-flows |

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
