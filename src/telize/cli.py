from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich.console import Console

from telize import __version__
from telize.config import load_spec
from telize.console import RichConsoleObserver, print_validation_ok
from telize.exceptions import ConfigError, ExecutionError, TelizeError
from telize.runtime import WorkflowRunner
from telize.runtime.workflow_input import resolve_cli_workflow_input

_ERR_CONSOLE = Console(stderr=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="telize",
        description="Run agent workflows defined in YAML.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "-f",
        "--file",
        type=Path,
        metavar="FILE",
        help="Path to a workflow YAML file.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Parse and validate the YAML without executing steps.",
    )
    parser.add_argument(
        "--input",
        action="append",
        metavar="KEY=VALUE",
        dest="input_pairs",
        help="Workflow input as key=value (repeatable). Merged with --input-file and --input-stdin.",
    )
    parser.add_argument(
        "--input-file",
        type=Path,
        metavar="FILE",
        help="YAML or JSON file with workflow input (mapping at root).",
    )
    parser.add_argument(
        "--input-stdin",
        action="store_true",
        help="Read workflow input as YAML or JSON from stdin.",
    )
    return parser


def _print_error(message: str) -> None:
    _ERR_CONSOLE.print(f"[bold red]error[/]: {message}")


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.file is None:
        parser.print_help()
        sys.exit(0 if argv is not None else 1)

    try:
        spec = load_spec(args.file)
        workflow_input = resolve_cli_workflow_input(
            pairs=args.input_pairs,
            input_file=args.input_file,
            input_stdin=args.input_stdin,
        )
    except ConfigError as exc:
        _print_error(str(exc))
        sys.exit(1)

    entrypoint = spec.config.entrypoint
    flow = spec.flows[entrypoint]

    if args.validate_only:
        print_validation_ok(
            workflow_file=args.file.resolve(),
            entrypoint=entrypoint,
            step_count=len(flow.steps),
        )
        sys.exit(0)

    observer = RichConsoleObserver(spec, args.file.resolve())
    try:
        WorkflowRunner(
            spec,
            args.file.resolve(),
            observer=observer,
            workflow_input=workflow_input,
        ).run()
    except (ConfigError, ExecutionError) as exc:
        _print_error(str(exc))
        sys.exit(1)
    except TelizeError as exc:
        _print_error(str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
