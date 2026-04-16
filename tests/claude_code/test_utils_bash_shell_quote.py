"""
Tests for utils/bash/shell_quote.py - Shell quoting re-exports and utilities.
"""

from __future__ import annotations

import pytest

from claude_code.utils.bash.shell_quote import (
    ParseEntry,
    ShellParseResult,
    ShellQuoteResult,
    shell_parse,
    shell_quote,
    try_parse_shell_command,
    try_quote_shell_args,
)


class TestShellParse:
    """Tests for shell_parse (parse function)."""

    def test_simple_command(self) -> None:
        tokens = shell_parse("echo hello")
        assert isinstance(tokens, list)
        assert len(tokens) > 0

    def test_empty_command(self) -> None:
        tokens = shell_parse("")
        assert tokens == []

    def test_command_with_pipe(self) -> None:
        tokens = shell_parse("cat file | grep pattern")
        assert isinstance(tokens, list)

    def test_command_with_quotes(self) -> None:
        tokens = shell_parse("echo 'hello world'")
        assert isinstance(tokens, list)

    def test_command_with_double_quotes(self) -> None:
        tokens = shell_parse('echo "hello world"')
        assert isinstance(tokens, list)


class TestShellQuote:
    """Tests for shell_quote (quote function)."""

    def test_simple_args(self) -> None:
        result = shell_quote(["echo", "hello"])
        assert "echo" in result
        assert "hello" in result

    def test_args_with_spaces(self) -> None:
        result = shell_quote(["hello world"])
        assert "'" in result or '"' in result

    def test_empty_list(self) -> None:
        result = shell_quote([])
        assert result == ""

    def test_args_with_special_chars(self) -> None:
        result = shell_quote(["hello;world"])
        assert "'" in result or '"' in result


class TestTryParseShellCommand:
    """Tests for try_parse_shell_command."""

    def test_success_result(self) -> None:
        result = try_parse_shell_command("echo hello")
        assert isinstance(result, ShellParseResult)
        assert result.success is True
        assert result.tokens is not None
        assert result.error is None

    def test_failure_result_invalid_syntax(self) -> None:
        # A command that bashlex can't parse
        result = try_parse_shell_command("$(invalid")
        assert isinstance(result, ShellParseResult)

    def test_empty_command(self) -> None:
        result = try_parse_shell_command("")
        assert isinstance(result, ShellParseResult)

    def test_tokens_are_list(self) -> None:
        result = try_parse_shell_command("ls -la")
        assert isinstance(result.tokens, list)


class TestTryQuoteShellArgs:
    """Tests for try_quote_shell_args."""

    def test_success_result_strings(self) -> None:
        result = try_quote_shell_args(["echo", "hello"])
        assert isinstance(result, ShellQuoteResult)
        assert result.success is True
        assert result.quoted is not None
        assert result.error is None

    def test_success_result_numbers(self) -> None:
        result = try_quote_shell_args([1, 2, 3])
        assert result.success is True
        assert result.quoted is not None

    def test_success_result_booleans(self) -> None:
        result = try_quote_shell_args([True, False])
        assert result.success is True

    def test_success_result_none(self) -> None:
        result = try_quote_shell_args([None])
        assert result.success is True

    def test_failure_result_unsupported_type(self) -> None:
        result = try_quote_shell_args([{"key": "value"}])
        assert result.success is False
        assert result.error is not None
        assert "not supported" in result.error

    def test_empty_list(self) -> None:
        result = try_quote_shell_args([])
        assert result.success is True


class TestShellParseResult:
    """Tests for ShellParseResult dataclass."""

    def test_success_creation(self) -> None:
        result = ShellParseResult(success=True, tokens=["a", "b"])
        assert result.success is True
        assert result.tokens == ["a", "b"]
        assert result.error is None

    def test_failure_creation(self) -> None:
        result = ShellParseResult(success=False, error="parse error")
        assert result.success is False
        assert result.error == "parse error"
        assert result.tokens is None


class TestShellQuoteResult:
    """Tests for ShellQuoteResult dataclass."""

    def test_success_creation(self) -> None:
        result = ShellQuoteResult(success=True, quoted="echo hello")
        assert result.success is True
        assert result.quoted == "echo hello"
        assert result.error is None

    def test_failure_creation(self) -> None:
        result = ShellQuoteResult(success=False, error="quote error")
        assert result.success is False
        assert result.error == "quote error"
        assert result.quoted is None


class TestParseEntry:
    """Tests for ParseEntry type alias."""

    def test_is_string(self) -> None:
        entry: ParseEntry = "hello"
        assert entry == "hello"

    def test_is_dict(self) -> None:
        entry: ParseEntry = {"op": "|"}
        assert entry == {"op": "|"}
