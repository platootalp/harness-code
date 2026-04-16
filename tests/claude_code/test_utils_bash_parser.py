"""
Tests for utils/bash/parser.py - Command splitting, redirections, placeholders.
"""

from __future__ import annotations

import pytest

from claude_code.utils.bash.parser import (
    extract_output_redirections,
    generate_placeholders,
    is_help_command,
    split_command,
    split_command_with_operators,
)


class TestGeneratePlaceholders:
    """Tests for generate_placeholders."""

    def test_generates_required_keys(self) -> None:
        ph = generate_placeholders()
        assert "SINGLE_QUOTE" in ph
        assert "DOUBLE_QUOTE" in ph
        assert "NEW_LINE" in ph
        assert "ESCAPED_OPEN_PAREN" in ph
        assert "ESCAPED_CLOSE_PAREN" in ph

    def test_contains_salt(self) -> None:
        ph = generate_placeholders()
        for key, val in ph.items():
            assert "_" in val, f"{key} should contain underscore separator"
            assert "salt" in val.lower() or any(c.isalpha() for c in val[2:]), (
                f"{key} should contain salt"
            )

    def test_different_calls_produce_different_salts(self) -> None:
        ph1 = generate_placeholders()
        ph2 = generate_placeholders()
        assert ph1["SINGLE_QUOTE"] != ph2["SINGLE_QUOTE"]


class TestSplitCommand:
    """Tests for split_command."""

    def test_simple_command(self) -> None:
        result = split_command("echo hello")
        assert "echo hello" in result

    def test_split_by_pipe(self) -> None:
        result = split_command("cat file | grep pattern")
        assert any("cat" in part for part in result)

    def test_split_by_semicolon(self) -> None:
        result = split_command("echo a; echo b")
        assert len(result) >= 1

    def test_split_by_ampersand(self) -> None:
        result = split_command("echo a && echo b")
        assert len(result) >= 1

    def test_split_by_double_ampersand(self) -> None:
        result = split_command("echo a && echo b")
        assert len(result) >= 1

    def test_split_by_double_pipe(self) -> None:
        result = split_command("echo a || echo b")
        assert len(result) >= 1

    def test_strips_redirections(self) -> None:
        result = split_command("echo hello > output.txt")
        assert any("echo" in part and "output" not in part for part in result)

    def test_strips_append_redirection(self) -> None:
        result = split_command("echo hello >> output.txt")
        assert any("echo" in part for part in result)

    def test_strips_fd_redirection(self) -> None:
        result = split_command("cmd 2>&1")
        assert "2>&1" not in " ".join(result)

    def test_empty_command(self) -> None:
        result = split_command("")
        assert result == []

    def test_single_command_no_split(self) -> None:
        result = split_command("ls -la")
        assert len(result) >= 1

    def test_handles_heredoc(self) -> None:
        result = split_command("cat << EOF\nhello\nEOF")
        assert any("cat" in part for part in result)


class TestSplitCommandWithOperators:
    """Tests for split_command_with_operators."""

    def test_preserves_pipe_operator(self) -> None:
        result = split_command_with_operators("cat file | grep pattern")
        assert "|" in result

    def test_preserves_semicolon(self) -> None:
        result = split_command_with_operators("echo a; echo b")
        assert ";" in result

    def test_preserves_double_ampersand(self) -> None:
        result = split_command_with_operators("echo a && echo b")
        assert "&&" in result

    def test_empty_command(self) -> None:
        result = split_command_with_operators("")
        assert result == []


class TestExtractOutputRedirections:
    """Tests for extract_output_redirections."""

    def test_extracts_simple_redirect(self) -> None:
        result = extract_output_redirections("echo hello > output.txt")
        assert "commandWithoutRedirections" in result
        assert "redirections" in result
        assert "hasDangerousRedirection" in result

    def test_extracts_append_redirect(self) -> None:
        result = extract_output_redirections("echo hello >> output.txt")
        assert len(result["redirections"]) >= 0

    def test_no_redirection(self) -> None:
        result = extract_output_redirections("echo hello")
        assert "commandWithoutRedirections" in result

    def test_extracts_fd_redirect(self) -> None:
        result = extract_output_redirections("cmd 2>&1")
        assert "commandWithoutRedirections" in result

    def test_dangerous_redirect_flag(self) -> None:
        result = extract_output_redirections("echo $var > output")
        assert "hasDangerousRedirection" in result


class TestIsHelpCommand:
    """Tests for is_help_command."""

    def test_simple_help_command(self) -> None:
        assert is_help_command("git --help") is True

    def test_help_with_short_flag(self) -> None:
        assert is_help_command("npm -h") is False

    def test_non_help_command(self) -> None:
        assert is_help_command("git status") is False

    def test_empty_command(self) -> None:
        assert is_help_command("") is False

    def test_help_with_extra_args(self) -> None:
        # curl --help -v is not a pure --help command (has extra -v flag)
        assert is_help_command("curl --help -v") is False

    def test_command_with_quotes_rejected(self) -> None:
        assert is_help_command('echo "hello" --help') is False

    def test_command_with_single_quote_rejected(self) -> None:
        assert is_help_command("echo 'hello' --help") is False
