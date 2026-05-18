# Contributing to Telize

Thank you for your interest in contributing!

## Development setup

1. Fork and clone the repository.
2. Install [uv](https://docs.astral.sh/uv/getting-started/installation/).
3. From the repo root:

```bash
uv sync
uv pip install -e .
```

4. Run checks before opening a PR:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

## Pull requests

- Keep changes focused; one logical change per PR.
- Add or update tests for behavior changes.
- Update [CHANGELOG.md](CHANGELOG.md) under **Unreleased** for user-visible changes.
- Ensure CI passes.

## Code style

- Python 3.12+, type hints on public APIs
- Ruff for linting and formatting (line length 100)
- Strict mypy on `src/telize`

## Reporting issues

Use [GitHub Issues](https://github.com/telize-ai/telize/issues) with a minimal reproduction (YAML file + command + expected vs actual behavior).

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
