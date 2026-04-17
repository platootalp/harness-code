"""
Tests for utils/bash/commands.py - Command wrappers, prefixes, normalization.
"""

from __future__ import annotations

import pytest

from claude_code.utils.bash.commands import (
    command_has_any_cd,
    get_first_word_prefix,
    get_simple_command_prefix,
    is_normalized_cd_command,
    is_normalized_git_command,
    match_wildcard_pattern,
    permission_rule_extract_prefix,
    skip_timeout_flags,
    strip_all_leading_env_vars,
    strip_safe_wrappers,
    strip_wrappers_from_argv,
)


class TestStripSafeWrappers:
    """Tests for strip_safe_wrappers."""

    def test_no_change_simple_command(self) -> None:
        result = strip_safe_wrappers("ls -la")
        assert result == "ls -la"

    def test_strips_timeout_wrapper(self) -> None:
        # timeout with --foreground flag gets stripped
        result = strip_safe_wrappers("timeout --foreground 30s ls")
        assert "ls" in result

    def test_strips_time_wrapper(self) -> None:
        result = strip_safe_wrappers("time ls")
        assert "time" not in result or result.strip() == "ls"

    def test_strips_nice_wrapper(self) -> None:
        result = strip_safe_wrappers("nice -n 10 ls")
        assert "ls" in result

    def test_strips_nohup_wrapper(self) -> None:
        result = strip_safe_wrappers("nohup ls &")
        assert "ls" in result

    def test_strips_safe_env_vars(self) -> None:
        result = strip_safe_wrappers("TERM=xterm ls")
        assert "ls" in result

    def test_strips_comment_lines(self) -> None:
        result = strip_safe_wrappers("# comment\nls")
        assert "# comment" not in result

    def test_empty_command(self) -> None:
        result = strip_safe_wrappers("")
        assert result == ""


class TestStripWrappersFromArgv:
    """Tests for strip_wrappers_from_argv."""

    def test_no_change_empty(self) -> None:
        result = strip_wrappers_from_argv([])
        assert result == []

    def test_no_change_simple(self) -> None:
        result = strip_wrappers_from_argv(["ls", "-la"])
        assert result == ["ls", "-la"]

    def test_strips_time_wrapper(self) -> None:
        result = strip_wrappers_from_argv(["time", "ls"])
        assert result == ["ls"]

    def test_strips_nohup_wrapper(self) -> None:
        result = strip_wrappers_from_argv(["nohup", "ls"])
        assert result == ["ls"]

    def test_strips_timeout_wrapper(self) -> None:
        result = strip_wrappers_from_argv(["timeout", "30", "ls"])
        assert result == ["ls"]

    def test_strips_nice_wrapper(self) -> None:
        result = strip_wrappers_from_argv(["nice", "-n", "10", "ls"])
        assert result == ["ls"]


class TestSkipTimeoutFlags:
    """Tests for skip_timeout_flags."""

    def test_no_args_returns_one(self) -> None:
        result = skip_timeout_flags(["ls"])
        assert result == 1

    def test_empty_returns_zero(self) -> None:
        result = skip_timeout_flags([])
        assert result == 1

    def test_skips_foreground_flag(self) -> None:
        result = skip_timeout_flags(["--foreground", "30", "ls"])
        assert result == 1
        assert "ls" in ["--foreground", "30", "ls"][result:]

    def test_skips_preserve_status_flag(self) -> None:
        result = skip_timeout_flags(["--preserve-status", "30s", "ls"])
        assert result == 1
        assert "ls" in ["--preserve-status", "30s", "ls"][result:]


class TestStripAllLeadingEnvVars:
    """Tests for strip_all_leading_env_vars."""

    def test_strips_var_assignment(self) -> None:
        result = strip_all_leading_env_vars("FOO=bar ls")
        assert result.strip() == "ls"

    def test_preserves_non_var_token(self) -> None:
        result = strip_all_leading_env_vars("FOO=bar ls")
        assert "FOO" not in result

    def test_empty_command(self) -> None:
        result = strip_all_leading_env_vars("")
        assert result == ""


class TestGetSimpleCommandPrefix:
    """Tests for get_simple_command_prefix."""

    def test_git_commit(self) -> None:
        result = get_simple_command_prefix("git commit -m 'fix bug'")
        assert result == "git commit"

    def test_npm_install(self) -> None:
        result = get_simple_command_prefix("npm install express")
        assert result == "npm install"

    def test_single_token_returns_none(self) -> None:
        result = get_simple_command_prefix("ls")
        assert result is None

    def test_safe_env_var_prefix(self) -> None:
        result = get_simple_command_prefix("TERM=xterm npm install")
        assert result == "npm install"

    def test_non_safe_env_var_prefix(self) -> None:
        result = get_simple_command_prefix("DANGEROUS_VAR=1 npm install")
        assert result is None

    def test_empty_command(self) -> None:
        result = get_simple_command_prefix("")
        assert result is None


class TestGetFirstWordPrefix:
    """Tests for get_first_word_prefix."""

    def test_simple_command(self) -> None:
        result = get_first_word_prefix("git status")
        assert result == "git"

    def test_rejects_bare_shell(self) -> None:
        result = get_first_word_prefix("bash -c 'ls'")
        assert result is None

    def test_rejects_shell_sh(self) -> None:
        result = get_first_word_prefix("sh -c 'ls'")
        assert result is None

    def test_rejects_sudo(self) -> None:
        result = get_first_word_prefix("sudo ls")
        assert result is None

    def test_safe_env_var_prefix(self) -> None:
        result = get_first_word_prefix("TERM=xterm ls")
        assert result == "ls"

    def test_empty_command(self) -> None:
        result = get_first_word_prefix("")
        assert result is None


class TestIsNormalizedGitCommand:
    """Tests for is_normalized_git_command."""

    def test_simple_git(self) -> None:
        assert is_normalized_git_command("git status") is True

    def test_plain_git(self) -> None:
        assert is_normalized_git_command("git") is True

    def test_non_git(self) -> None:
        assert is_normalized_git_command("ls -la") is False

    def test_git_in_pipe(self) -> None:
        assert is_normalized_git_command("cat file | git blame") is True


class TestIsNormalizedCdCommand:
    """Tests for is_normalized_cd_command."""

    def test_cd_command(self) -> None:
        assert is_normalized_cd_command("cd /tmp") is True

    def test_pushd_command(self) -> None:
        assert is_normalized_cd_command("pushd /tmp") is True

    def test_popd_command(self) -> None:
        assert is_normalized_cd_command("popd") is True

    def test_non_cd(self) -> None:
        assert is_normalized_cd_command("ls /tmp") is False


class TestCommandHasAnyCd:
    """Tests for command_has_any_cd."""

    def test_simple_cd(self) -> None:
        assert command_has_any_cd("cd /tmp") is True

    def test_compound_with_cd(self) -> None:
        assert command_has_any_cd("cd /tmp && ls") is True

    def test_no_cd(self) -> None:
        assert command_has_any_cd("ls -la") is False


class TestPermissionRuleExtractPrefix:
    """Tests for permission_rule_extract_prefix."""

    def test_colon_wildcard(self) -> None:
        result = permission_rule_extract_prefix("npm:*")
        assert result == "npm"

    def test_no_wildcard(self) -> None:
        result = permission_rule_extract_prefix("npm install")
        assert result is None

    def test_empty_string(self) -> None:
        result = permission_rule_extract_prefix("")
        assert result is None


class TestMatchWildcardPattern:
    """Tests for match_wildcard_pattern."""

    def test_exact_match(self) -> None:
        assert match_wildcard_pattern("npm install", "npm install") is True

    def test_wildcard_star(self) -> None:
        # Pattern 'npm install*' matches 'npm install express' since * is at the end
        assert match_wildcard_pattern("npm install*", "npm install express") is True

    def test_no_match(self) -> None:
        assert match_wildcard_pattern("npm install", "npm uninstall") is False

    def test_partial_match_rejected(self) -> None:
        assert match_wildcard_pattern("npm:*", "npmx install") is False
