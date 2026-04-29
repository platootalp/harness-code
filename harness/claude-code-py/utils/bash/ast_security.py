"""Security-focused AST analysis for shell commands.

Provides security checks for shell commands including:
- Parse timeout detection
- Command injection detection
- Path constraint validation
- Environment variable extraction
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Union

from .shell_quote import try_parse_shell_command

if TYPE_CHECKING:
    pass

# =============================================================================
# Result Types
# =============================================================================


class PARSE_ABORTED:
    """Marker indicating parse was aborted due to timeout or complexity."""

    pass


class COMMAND_INJECTION:
    """Marker indicating command injection was detected."""

    pass


ParseResult = Union["ParseResultData", type[PARSE_ABORTED], type[COMMAND_INJECTION]]


@dataclass
class ParseResultData:
    """Result of successful security-parsed command."""

    root_node: Any
    env_vars: list[str]
    command_node: Any | None
    original_command: str
    safe: bool = True
    injection_detected: bool = False
    blocked_reason: str | None = None


# =============================================================================
# Security Constants
# =============================================================================

MAX_NODES_DEFAULT = 50_000
DEFAULT_TIMEOUT_MS = 50

# Dangerous patterns
INJECTION_PATTERNS = [
    re.compile(r"\$\([^)]+\)"),  # Command substitution $()
    re.compile(r"`[^`]+`"),  # Backtick command substitution
    re.compile(r"\$\{[^}]+\}"),  # Parameter expansion with command
    re.compile(r";\s*\w"),  # Command chaining with semicolon
    re.compile(r"\|\s*\w"),  # Pipe to command
    re.compile(r"&&\s*\w"),  # AND chain
    re.compile(r"\|\|\s*\w"),  # OR chain
    re.compile(r">\s*/"),  # Redirect to absolute path
    re.compile(r"<\s*/"),  # Input from absolute path
]

# Allowed path patterns for constrained environments
ALLOWED_PATH_PREFIXES: list[str] = []


# =============================================================================
# Command Injection Detection
# =============================================================================


def _check_command_injection(command: str) -> tuple[bool, str | None]:
    """Check for command injection patterns in a command.

    Args:
        command: The shell command string.

    Returns:
        Tuple of (is_injection, reason).
    """
    for pattern in INJECTION_PATTERNS:
        if pattern.search(command):
            return True, f"Dangerous pattern detected: {pattern.pattern}"
    return False, None


# =============================================================================
# Path Constraint Checking
# =============================================================================


def check_path_constraints(command: str, allowed_prefixes: list[str] | None = None) -> bool:
    """Check if command paths are within allowed paths.

    Args:
        command: The shell command string.
        allowed_prefixes: List of allowed path prefixes. Uses env var if not provided.

    Returns:
        True if all paths are within constraints, or no paths found.
    """
    prefixes = allowed_prefixes or ALLOWED_PATH_PREFIXES
    if not prefixes:
        return True

    path_pattern = re.compile(r"(?:^|[\s])([/-][^\s\"\'`;|&$<>]+)")
    for match in path_pattern.finditer(command):
        path = match.group(1)
        if path.startswith("-") or path.startswith("-"):
            continue
        if not any(path.startswith(prefix) for prefix in prefixes):
            return False
    return True


# =============================================================================
# Environment Variable Extraction
# =============================================================================


def extract_env_vars_from_command(command: str) -> list[str]:
    """Extract environment variables without full parsing.

    Args:
        command: The shell command string.

    Returns:
        List of environment variable names.
    """
    env_vars: list[str] = []

    # Leading env var assignments: VAR=value command
    leading_pattern = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=")
    for part in command.split():
        m = leading_pattern.match(part)
        if m:
            env_vars.append(m.group(1))
        elif "=" not in part:
            break

    # export VAR=value
    export_pattern = re.compile(r"\bexport\s+([A-Za-z_][A-Za-z0-9_]*)")
    for m in export_pattern.finditer(command):
        if m.group(1) not in env_vars:
            env_vars.append(m.group(1))

    return env_vars


# =============================================================================
# Complexity Analysis
# =============================================================================


def _estimate_command_complexity(command: str) -> int:
    """Estimate the complexity of a command by counting tokens.

    Args:
        command: The shell command string.

    Returns:
        Estimated node count.
    """
    tokens = command.split()
    return len(tokens)


# =============================================================================
# Security Parse
# =============================================================================


async def parse_for_security(
    command: str,
    check_timeout_ms: int = DEFAULT_TIMEOUT_MS,
    max_nodes: int = MAX_NODES_DEFAULT,
) -> ParseResultData | type[PARSE_ABORTED] | type[COMMAND_INJECTION]:
    """Parse command with security checks.

    Args:
        command: The shell command to parse.
        check_timeout_ms: Maximum time for parsing in milliseconds.
        max_nodes: Maximum allowed AST nodes.

    Returns:
        ParseResultData on success, PARSE_ABORTED on timeout/complexity,
        or COMMAND_INJECTION on injection detection.
    """
    # Step 1: Quick injection check (fast path)
    is_injection, reason = _check_command_injection(command)
    if is_injection:
        return COMMAND_INJECTION

    # Step 2: Complexity check
    node_count = _estimate_command_complexity(command)
    if node_count > max_nodes:
        return PARSE_ABORTED

    # Step 3: Timeout-controlled parsing using shell-quote
    timeout_sec = check_timeout_ms / 1000.0

    try:
        result = await asyncio.wait_for(
            _parse_command_async(command),
            timeout=timeout_sec,
        )
        return result
    except TimeoutError:
        return PARSE_ABORTED


async def _parse_command_async(command: str) -> ParseResultData:
    """Parse a command asynchronously.

    Args:
        command: The command to parse.

    Returns:
        ParseResultData with parsed information.
    """
    # Use shell-quote for parsing
    parse_result = try_parse_shell_command(command)

    env_vars = extract_env_vars_from_command(command)

    if not parse_result.success:
        return ParseResultData(
            root_node=None,
            env_vars=env_vars,
            command_node=None,
            original_command=command,
            safe=False,
            blocked_reason="Parse failed",
        )

    return ParseResultData(
        root_node=None,
        env_vars=env_vars,
        command_node=None,
        original_command=command,
        safe=True,
        injection_detected=False,
    )


def parse_for_security_sync(
    command: str,
    check_timeout_ms: int = DEFAULT_TIMEOUT_MS,
    max_nodes: int = MAX_NODES_DEFAULT,
) -> ParseResultData | type[PARSE_ABORTED] | type[COMMAND_INJECTION]:
    """Synchronous version of parse_for_security.

    Args:
        command: The shell command to parse.
        check_timeout_ms: Maximum time for parsing in milliseconds.
        max_nodes: Maximum allowed AST nodes.

    Returns:
        Same as parse_for_security.
    """
    # Quick injection check
    is_injection, reason = _check_command_injection(command)
    if is_injection:
        return COMMAND_INJECTION

    # Complexity check
    node_count = _estimate_command_complexity(command)
    if node_count > max_nodes:
        return PARSE_ABORTED

    # Shell-quote parsing (sync)
    parse_result = try_parse_shell_command(command)
    env_vars = extract_env_vars_from_command(command)

    if not parse_result.success:
        return ParseResultData(
            root_node=None,
            env_vars=env_vars,
            command_node=None,
            original_command=command,
            safe=False,
            blocked_reason="Parse failed",
        )

    return ParseResultData(
        root_node=None,
        env_vars=env_vars,
        command_node=None,
        original_command=command,
        safe=True,
    )


# =============================================================================
# Allowed Paths Configuration
# =============================================================================


def set_allowed_path_prefixes(prefixes: list[str]) -> None:
    """Set the allowed path prefixes for security checking.

    Args:
        prefixes: List of allowed path prefixes.
    """
    global ALLOWED_PATH_PREFIXES
    ALLOWED_PATH_PREFIXES = list(prefixes)


def clear_allowed_path_prefixes() -> None:
    """Clear the allowed path prefixes."""
    global ALLOWED_PATH_PREFIXES
    ALLOWED_PATH_PREFIXES = []
