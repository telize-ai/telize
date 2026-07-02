from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich.console import Console

from telize import __version__
from telize.config import load_spec
from telize.console import RichConsoleObserver, get_console, print_validation_ok
from telize.exceptions import ConfigError, ExecutionError, TelizeError
from telize.runtime import WorkflowRunner
from telize.runtime.workflow_input import resolve_cli_workflow_input
from telize.scaffold import create_starter_project

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
        help=(
            "Workflow input as key=value (repeatable). Merged with --input-file and --input-stdin."
        ),
    )
    parser.add_argument(
        "--input-file",
        type=Path,
        metavar="FILE",
        help=(
            "Workflow input file: YAML/JSON mapping, a .txt file (as {{ input.text }}), "
            "or other text parsed like --input-stdin."
        ),
    )
    parser.add_argument(
        "--input-stdin",
        action="store_true",
        help=(
            "Read workflow input from stdin: a YAML/JSON mapping, or plain text "
            "(exposed as {{ input.text }})."
        ),
    )
    parser.add_argument(
        "--init",
        metavar="FLOW_NAME",
        help=(
            "Create a starter workflow (<flow_name>.yaml), README.md, and scripts/ "
            "in the current directory (no LLM required)."
        ),
    )
    return parser


def _print_error(message: str) -> None:
    _ERR_CONSOLE.print(f"[bold red]error[/]: {message}")


def _run_init(flow_name: str) -> None:
    result = create_starter_project(flow_name)
    console = get_console()
    console.print("[bold green]Created starter workflow[/]")
    console.print(f"  [cyan]{result.workflow.name}[/]")
    console.print(f"  [cyan]{result.readme.name}[/]")
    console.print(f"  [cyan]{result.process_module.relative_to(result.workflow.parent)}[/]")
    console.print()
    console.print("Next steps:")
    console.print(f"  telize -f {result.workflow.name}")
    console.print(f"  telize -f {result.workflow.name} --validate-only")


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.init is not None:
        if args.file is not None:
            _print_error("cannot use --init together with -f/--file")
            sys.exit(1)
        try:
            _run_init(args.init)
        except ConfigError as exc:
            _print_error(str(exc))
            sys.exit(1)
        sys.exit(0)

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
    except KeyboardInterrupt:
        sys.exit(130)
    except (ConfigError, ExecutionError) as exc:
        _print_error(str(exc))
        sys.exit(1)
    except TelizeError as exc:
        _print_error(str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
