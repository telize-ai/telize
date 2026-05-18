import pytest

from telize.exceptions import ConfigError
from telize.runtime.workflow_input import (
    merge_workflow_input,
    parse_key_value_pairs,
    resolve_cli_workflow_input,
)


def test_parse_key_value_pairs() -> None:
    assert parse_key_value_pairs(["a=1", "b=two"]) == {"a": "1", "b": "two"}


def test_parse_key_value_pairs_rejects_invalid() -> None:
    with pytest.raises(ConfigError):
        parse_key_value_pairs(["nopequals"])


def test_merge_workflow_input_later_overrides() -> None:
    merged = merge_workflow_input({"a": 1}, {"a": 2, "b": 3})
    assert merged == {"a": 2, "b": 3}


def test_resolve_cli_workflow_input(tmp_path) -> None:
    path = tmp_path / "in.yaml"
    path.write_text("from: file\n", encoding="utf-8")
    result = resolve_cli_workflow_input(
        pairs=["from=cli"],
        input_file=path,
        input_stdin=False,
    )
    assert result == {"from": "cli"}
