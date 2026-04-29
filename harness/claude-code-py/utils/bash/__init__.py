"""Bash utilities module.

Provides shell command parsing, security analysis, quoting, and related utilities.
"""

# bash_command_is_safe and helpers - defined here to avoid module shadowing circular import.
import re
from typing import Any

from .ast_security import (
    check_path_constraints,
    clear_allowed_path_prefixes,
    extract_env_vars_from_command,
    parse_for_security,
    parse_for_security_sync,
    set_allowed_path_prefixes,
)
from .commands import (
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
from .heredoc import (
    HeredocExtractionResult,
    HeredocInfo,
    extract_heredocs,
    restore_heredocs,
    restore_heredocs_in_string,
)
from .parser import (
    extract_output_redirections,
    generate_placeholders,
    is_help_command,
    split_command,
    split_command_with_operators,
)
from .shell_quote import (
    ParseEntry,
    ShellParseResult,
    ShellQuoteResult,
    shell_parse,
    shell_quote,
    try_parse_shell_command,
    try_quote_shell_args,
)

COMMAND_SUBSTITUTION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"<\\\("), "process substitution <()"),
    (re.compile(r">\\\("), "process substitution >()"),
    (re.compile(r"=\\\("), "Zsh process substitution =()"),
    (re.compile(r"(?:^|[\s;&|])=[a-zA-Z_]"), "Zsh equals expansion (=cmd)"),
    (re.compile(r"\\$\\\("), "$() command substitution"),
    (re.compile(r"\\$\\{"), "${} parameter substitution"),
    (re.compile(r"\$\[[^\]]*\]"), "$[] legacy arithmetic expansion"),
    (re.compile(r"~\[[^\]]*\]"), "Zsh-style parameter expansion"),
    (re.compile(r"\\(e:\\)"), "Zsh-style glob qualifiers"),
    (re.compile(r"\\(\\+\\)"), "Zsh glob qualifier with command execution"),
    (re.compile(r"\\}\\s*always\\s*\\{"), "Zsh always block"),
    (re.compile(r"<#"), "PowerShell comment syntax"),
]

ZSH_DANGEROUS_COMMANDS: frozenset[str] = frozenset([
    "zmodload", "emulate", "sysopen", "sysread", "syswrite", "sysseek",
    "zpty", "ztcp", "zsocket", "mapfile",
    "zf_rm", "zf_mv", "zf_ln", "zf_chmod", "zf_chown", "zf_mkdir",
    "zf_rmdir", "zf_chgrp",
])


def _has_malformed_tokens(command: str, parsed: list[ParseEntry]) -> bool:
    in_single = False
    in_double = False
    double_count = 0
    single_count = 0
    i = 0
    while i < len(command):
        c = command[i]
        if c == "\\" and not in_single:
            i += 2
            continue
        if c == '"' and not in_single:
            double_count += 1
            in_double = not in_double
        elif c == "'" and not in_double:
            single_count += 1
            in_single = not in_single
        i += 1
    if double_count % 2 != 0 or single_count % 2 != 0:
        return True
    for entry in parsed:
        if not isinstance(entry, str):
            continue
        for open_pat, close_pat in [
            (r"{", r"}"), (r"\(", r"\)"), (r"\[", r"\]"),
        ]:
            if len(re.findall(open_pat, entry)) != len(re.findall(close_pat, entry)):
                return True
        if len(re.findall(r'(?<!\\)"', entry)) % 2 != 0:
            return True
        if len(re.findall(r"(?<!\\)'", entry)) % 2 != 0:
            return True
    return False


def _has_shell_quote_single_quote_bug(command: str) -> bool:
    idx = 0
    while idx < len(command):
        if command[idx] == "'":
            idx += 1
            while idx < len(command) and command[idx] != "'":
                if command[idx] == "\\" and idx + 1 < len(command):
                    idx += 2
                else:
                    idx += 1
            if idx >= len(command):
                return False
            idx += 1
            if idx < len(command) and command[idx] == "\\":
                return True
    return False


def bash_command_is_safe(command: str) -> dict[str, Any]:
    """Check if a command is safe (legacy regex-based check)."""
    parse_result = try_parse_shell_command(command)
    if not parse_result.success:
        return {
            "behavior": "ask",
            "message": f"Command contains malformed syntax: {parse_result.error}",
            "is_bash_security_check_for_misparsing": False,
        }
    parsed = parse_result.tokens or []
    if _has_malformed_tokens(command, parsed):
        return {
            "behavior": "ask",
            "message": "Command contains patterns that could pose security risks",
            "is_bash_security_check_for_misparsing": True,
        }
    if _has_shell_quote_single_quote_bug(command):
        return {
            "behavior": "ask",
            "message": "Command contains patterns that could pose security risks",
            "is_bash_security_check_for_misparsing": True,
        }
    for pattern, message in COMMAND_SUBSTITUTION_PATTERNS:
        if pattern.search(command):
            return {
                "behavior": "ask",
                "message": f"Command contains {message}",
                "is_bash_security_check_for_misparsing": False,
            }
    if re.search(r"[^\\]&[^\s&]*$", command):
        return {
            "behavior": "ask",
            "message": "Command contains incomplete structure",
            "is_bash_security_check_for_misparsing": True,
        }
    if parsed and isinstance(parsed[0], str):
        base_cmd = parsed[0].split()[0] if parsed else ""
        if base_cmd in ZSH_DANGEROUS_COMMANDS:
            return {
                "behavior": "ask",
                "message": f"Command uses restricted zsh builtin: {base_cmd}",
                "is_bash_security_check_for_misparsing": False,
            }
    return {
        "behavior": "passthrough",
        "message": None,
        "is_bash_security_check_for_misparsing": False,
    }


__all__ = [
    # security (bash_command_is_safe)
    "bash_command_is_safe",
    # security (ast)
    "check_path_constraints",
    "clear_allowed_path_prefixes",
    "extract_env_vars_from_command",
    "parse_for_security",
    "parse_for_security_sync",
    "set_allowed_path_prefixes",
    # parser
    "split_command",
    "split_command_with_operators",
    "extract_output_redirections",
    "is_help_command",
    "generate_placeholders",
    # commands
    "strip_safe_wrappers",
    "strip_wrappers_from_argv",
    "strip_all_leading_env_vars",
    "get_simple_command_prefix",
    "get_first_word_prefix",
    "is_normalized_git_command",
    "is_normalized_cd_command",
    "command_has_any_cd",
    "permission_rule_extract_prefix",
    "match_wildcard_pattern",
    "skip_timeout_flags",
    # heredoc
    "extract_heredocs",
    "restore_heredocs",
    "restore_heredocs_in_string",
    "HeredocInfo",
    "HeredocExtractionResult",
    # shell_quote
    "shell_parse",
    "shell_quote",
    "try_parse_shell_command",
    "try_quote_shell_args",
    "ShellParseResult",
    "ShellQuoteResult",
    "ParseEntry",
]
