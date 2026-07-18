# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Top-level `vars` map in workflow YAML, available in Jinja as `{{ vars.<name> }}`

## [0.1.0] - 2026-05-17

### Added

- Initial project scaffold with `uv` and Hatchling build backend
- `telize` CLI with `--version` and `-f/--file` to run YAML agent flows
- Pydantic-validated agent spec (`agents`, `flow.steps`)
- Stub flow runner with `{{ variable }}` template support between steps
- Example `examples/hello_agent.yaml` and test suite

[Unreleased]: https://github.com/telize-ai/telize/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/telize-ai/telize/releases/tag/v0.1.0
