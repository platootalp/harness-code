"""Tests for utils/bash/ast_security.py."""

from __future__ import annotations

import pytest

from claude_code.utils.bash.ast_security import (
    COMMAND_INJECTION,
    PARSE_ABORTED,
    ParseResultData,
    check_path_constraints,
    clear_allowed_path_prefixes,
    extract_env_vars_from_command,
    parse_for_security,
    parse_for_security_sync,
    set_allowed_path_prefixes,
)


class TestPARSE_ABORTED:
    """Tests for PARSE_ABORTED marker."""

    def test_is_marker(self) -> None:
        assert PARSE_ABORTED is not None


class TestCOMMAND_INJECTION:
    """Tests for COMMAND_INJECTION marker."""

    def test_is_marker(self) -> None:
        assert COMMAND_INJECTION is not None


class TestExtractEnvVarsFromCommand:
    """Tests for extract_env_vars_from_command."""

    def test_no_vars(self) -> None:
        result = extract_env_vars_from_command("echo hello")
        assert result == []

    def test_leading_env_vars(self) -> None:
        result = extract_env_vars_from_command("FOO=bar BAZ=qux echo hello")
        assert "FOO" in result
        assert "BAZ" in result

    def test_export(self) -> None:
        result = extract_env_vars_from_command("export MY_VAR=value")
        assert "MY_VAR" in result

    def test_mixed(self) -> None:
        result = extract_env_vars_from_command("A=1 B=2 export C=3 echo test")
        assert "A" in result
        assert "B" in result
        assert "C" in result


class TestCheckPathConstraints:
    """Tests for check_path_constraints."""

    def test_no_prefixes(self) -> None:
        assert check_path_constraints("echo hello", []) is True

    def test_allowed_path(self) -> None:
        clear_allowed_path_prefixes()
        set_allowed_path_prefixes(["/tmp"])
        assert check_path_constraints("cat /tmp/file.txt") is True

    def test_disallowed_path(self) -> None:
        clear_allowed_path_prefixes()
        set_allowed_path_prefixes(["/tmp"])
        assert check_path_constraints("cat /etc/passwd") is False

    def test_flag_not_path(self) -> None:
        clear_allowed_path_prefixes()
        set_allowed_path_prefixes(["/tmp"])
        assert check_path_constraints("ls --all") is True

    def test_no_prefixes_uses_default(self) -> None:
        clear_allowed_path_prefixes()
        assert check_path_constraints("echo hello") is True


class TestParseForSecuritySync:
    """Tests for parse_for_security_sync."""

    def test_simple_command(self) -> None:
        result = parse_for_security_sync("echo hello world")
        assert result is not PARSE_ABORTED
        assert result is not COMMAND_INJECTION
        assert result.safe is True

    def test_command_injection(self) -> None:
        result = parse_for_security_sync("echo hello; rm -rf /")
        assert result is COMMAND_INJECTION

    def test_command_substitution(self) -> None:
        result = parse_for_security_sync("echo $(whoami)")
        assert result is COMMAND_INJECTION

    def test_backtick_substitution(self) -> None:
        result = parse_for_security_sync("echo `id`")
        assert result is COMMAND_INJECTION

    def test_pipe_to_command(self) -> None:
        result = parse_for_security_sync("echo hi | cat")
        assert result is COMMAND_INJECTION

    def test_and_chain(self) -> None:
        result = parse_for_security_sync("echo hi && ls")
        assert result is COMMAND_INJECTION

    def test_redirect_absolute(self) -> None:
        result = parse_for_security_sync("echo hi > /tmp/out.txt")
        assert result is COMMAND_INJECTION

    def test_complex_command_ok(self) -> None:
        result = parse_for_security_sync("git status --short")
        assert result is not COMMAND_INJECTION
        assert result is not PARSE_ABORTED

    def test_max_nodes_exceeded(self) -> None:
        result = parse_for_security_sync("echo a b c d e", max_nodes=2)
        assert result is PARSE_ABORTED

    def test_parse_result_data(self) -> None:
        result = parse_for_security_sync("FOO=bar echo test")
        assert isinstance(result, ParseResultData)
        assert result.env_vars == ["FOO"]


class TestParseForSecurity:
    """Tests for parse_for_security (async version)."""

    async def test_simple_command(self) -> None:
        result = await parse_for_security("echo hello")
        assert result is not PARSE_ABORTED
        assert result is not COMMAND_INJECTION

    async def test_injection(self) -> None:
        result = await parse_for_security("echo x; rm -rf /")
        assert result is COMMAND_INJECTION

    async def test_complex_command(self) -> None:
        result = await parse_for_security("npm install --save-dev package")
        assert result is not COMMAND_INJECTION
        assert result is not PARSE_ABORTED
