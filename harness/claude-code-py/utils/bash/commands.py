"""Command-related utilities - prefix extraction, normalization, wrappers."""
from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING

from .parser import split_command
from .shell_quote import try_parse_shell_command

if TYPE_CHECKING:
    pass

# =============================================================================
# Constants
# =============================================================================

# Maximum subcommands for security check (CC-643)
MAX_SUBCOMMANDS_FOR_SECURITY_CHECK = 50

# Maximum suggested rules for compound commands (GH#11380)
MAX_SUGGESTED_RULES_FOR_COMPOUND = 5

# Env var assignment pattern
ENV_VAR_ASSIGN_RE = re.compile(r"^[A-Za-z_]\w*=")

# Safe environment variables that can be stripped from commands
SAFE_ENV_VARS: frozenset[str] = frozenset([
    # Go
    "GOEXPERIMENT",
    "GOOS",
    "GOARCH",
    "CGO_ENABLED",
    "GO111MODULE",
    # Rust
    "RUST_BACKTRACE",
    "RUST_LOG",
    # Node
    "NODE_ENV",
    # Python
    "PYTHONUNBUFFERED",
    "PYTHONDONTWRITEBYTECODE",
    # Pytest
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
    "PYTEST_DEBUG",
    # API keys
    "ANTHROPIC_API_KEY",
    # Locale
    "LANG",
    "LANGUAGE",
    "LC_ALL",
    "LC_CTYPE",
    "LC_TIME",
    "CHARSET",
    # Terminal
    "TERM",
    "COLORTERM",
    "NO_COLOR",
    "FORCE_COLOR",
    "TZ",
    # Color config
    "LS_COLORS",
    "LSCOLORS",
    "GREP_COLOR",
    "GREP_COLORS",
    "GCC_COLORS",
    # Display
    "TIME_STYLE",
    "BLOCK_SIZE",
    "BLOCKSIZE",
])

# ANT-only safe env vars (for internal use)
ANT_ONLY_SAFE_ENV_VARS: frozenset[str] = frozenset([
    "KUBECONFIG",
    "DOCKER_HOST",
    "AWS_PROFILE",
    "CLOUDSDK_CORE_PROJECT",
    "CLUSTER",
    "COO_CLUSTER",
    "COO_CLUSTER_NAME",
    "COO_NAMESPACE",
    "COO_LAUNCH_YAML_DRY_RUN",
    "SKIP_NODE_VERSION_CHECK",
    "EXPECTTEST_ACCEPT",
    "CI",
    "GIT_LFS_SKIP_SMUDGE",
    "CUDA_VISIBLE_DEVICES",
    "JAX_PLATFORMS",
    "COLUMNS",
    "TMUX",
    "POSTGRESQL_VERSION",
    "FIRESTORE_EMULATOR_HOST",
    "HARNESS_QUIET",
    "TEST_CROSSCHECK_LISTS_MATCH_UPDATE",
    "DBT_PER_DEVELOPER_ENVORIES",
    "STATSIG_FORD_DB_CHECKS",
    "ANT_ENVIRONMENT",
    "ANT_SERVICE",
    "MONOREPO_ROOT_DIR",
    "PYENV_VERSION",
    "PGPASSWORD",
    "GH_TOKEN",
    "GROWTHBOOK_API_KEY",
])

# Bare shell prefixes that should never be suggested
BARE_SHELL_PREFIXES: frozenset[str] = frozenset([
    "sh",
    "bash",
    "zsh",
    "fish",
    "csh",
    "tcsh",
    "ksh",
    "dash",
    "cmd",
    "powershell",
    "pwsh",
    "env",
    "xargs",
    "nice",
    "stdbuf",
    "nohup",
    "timeout",
    "time",
    "sudo",
    "doas",
    "pkexec",
])

# Binary hijack variables
BINARY_HIJACK_VARS = re.compile(r"^(LD_|DYLD_|PATH$)")


# =============================================================================
# Helper Functions
# =============================================================================


def _is_ant_user() -> bool:
    """Check if running as an ANT user."""
    return os.environ.get("USER_TYPE") == "ant"


def _is_safe_env_var(var_name: str) -> bool:
    """Check if an env var is in the safe list."""
    if var_name in SAFE_ENV_VARS:
        return True
    return bool(_is_ant_user() and var_name in ANT_ONLY_SAFE_ENV_VARS)


# =============================================================================
# Safe Wrapper Stripping
# =============================================================================

# Timeout flag value pattern (allowlist)
TIMEOUT_FLAG_VALUE_RE = re.compile(r"^[A-Za-z0-9_.+-]+$")

# Safe wrapper patterns
_TIMEOUT_PATTERN = re.compile(
    r"^timeout[ \t]+(?:(?:--(?:foreground|preserve-status|verbose)"
    r"|--(?:kill-after|signal)=[A-Za-z0-9_.+-]+"
    r"|--(?:kill-after|signal)[ \t]+[A-Za-z0-9_.+-]+"
    r"|-v|-[ks][ \t]+[A-Za-z0-9_.+-]+|-[ks][A-Za-z0-9_.+-]+))"
    r"[ \t]+(?:--[ \t]+)?\d+(?:\.\d+)?[smhd]?[ \t]+",
)
_TIME_PATTERN = re.compile(r"^time[ \t]+(?:--[ \t]+)?")
_NICE_PATTERN = re.compile(
    r"^nice(?:[ \t]+-n[ \t]+-?\d+|[ \t]+-\d+)?[ \t]+(?:--[ \t]+)?",
)
_STDBUF_PATTERN = re.compile(r"^stdbuf(?:[ \t]+-[ioe][LN0-9]+)+[ \t]+(?:--[ \t]+)?")
_NOHUP_PATTERN = re.compile(r"^nohup[ \t]+(?:--[ \t]+)?")

SAFE_WRAPPER_PATTERNS: list[re.Pattern[str]] = [
    _TIMEOUT_PATTERN,
    _TIME_PATTERN,
    _NICE_PATTERN,
    _STDBUF_PATTERN,
    _NOHUP_PATTERN,
]

# Env var pattern for stripping (broader value pattern)
_ENV_VAR_PATTERN = re.compile(
    r"^([A-Za-z_][A-Za-z0-9_]*)"
    r"="
    r"([A-Za-z0-9_./:-]+)"
    r"[ \t]+",
)


def _strip_comment_lines(command: str) -> str:
    """Strip full-line comments from a command."""
    lines = command.split("\n")
    non_comment = [
        line for line in lines if line.strip() != "" and not line.strip().startswith("#")
    ]
    if not non_comment:
        return command
    return "\n".join(non_comment)


def strip_safe_wrappers(command: str) -> str:
    """Strip safe wrapper commands and env vars from a command.

    Strips timeout, time, nice, nohup wrappers and safe env vars
    for permission rule matching.

    Args:
        command: The shell command string.

    Returns:
        Command with safe wrappers and env vars stripped.
    """
    # Phase 1: Strip leading env vars and comments
    stripped = command
    previous = ""
    while stripped != previous:
        previous = stripped
        stripped = _strip_comment_lines(stripped)
        m = _ENV_VAR_PATTERN.match(stripped)
        if m:
            var_name = m.group(1)
            if _is_safe_env_var(var_name):
                stripped = stripped[m.end() :]
        # Also check the safe env var list for phase 1
        for pattern in SAFE_WRAPPER_PATTERNS:
            m = pattern.match(stripped)
            if m:
                stripped = stripped[m.end() :]
                break

    # Phase 2: Strip wrapper commands and comments (NOT env vars)
    stripped = previous
    previous = ""
    while stripped != previous:
        previous = stripped
        stripped = _strip_comment_lines(stripped)
        for pattern in SAFE_WRAPPER_PATTERNS:
            m = pattern.match(stripped)
            if m:
                stripped = stripped[m.end() :]
                break

    return stripped.strip()


def skip_timeout_flags(argv: list[str]) -> int:
    """Parse timeout flags and return the index of the duration token.

    Args:
        argv: Argument list (starting after 'timeout').

    Returns:
        Index of the duration token, or -1 if unparseable.
    """
    i = 1
    while i < len(argv):
        arg = argv[i]
        nxt = argv[i + 1] if i + 1 < len(argv) else None
        if arg in ("--foreground", "--preserve-status", "--verbose") or re.match(
            r"^--(?:kill-after|signal)=[A-Za-z0-9_.+-]+$", arg
        ):
            i += 1
        elif arg in ("--kill-after", "--signal") and nxt and TIMEOUT_FLAG_VALUE_RE.match(nxt):
            i += 2
        elif arg == "--":
            i += 1
            break
        elif arg.startswith("--"):
            return -1
        elif arg == "-v":
            i += 1
        elif arg in ("-k", "-s") and nxt and TIMEOUT_FLAG_VALUE_RE.match(nxt):
            i += 2
        elif re.match(r"^-[ks][A-Za-z0-9_.+-]+$", arg):
            i += 1
        elif arg.startswith("-"):
            return -1
        else:
            break
    return i


def strip_wrappers_from_argv(argv: list[str]) -> list[str]:
    """Strip wrapper commands from an argv list.

    Args:
        argv: Argument list from AST parsing.

    Returns:
        Argv with wrappers stripped.
    """
    a = argv
    while True:
        if not a:
            return a
        if a[0] in ("time", "nohup"):
            skip = 2 if len(a) > 1 and a[1] == "--" else 1
            a = a[skip:]
        elif a[0] == "timeout":
            i = skip_timeout_flags(a)
            if i < 0 or i >= len(a) or not re.match(r"^\d+(?:\.\d+)?[smhd]?$", a[i]):
                return a
            a = a[i + 1 :]
        elif a[0] == "nice" and len(a) > 2 and a[1] == "-n" and re.match(r"^-?\d+$", a[2]):
            skip = 4 if len(a) > 3 and a[3] == "--" else 3
            a = a[skip:]
        else:
            return a


def strip_all_leading_env_vars(
    command: str,
    blocklist: re.Pattern[str] | None = None,
) -> str:
    """Strip ALL leading env var prefixes from a command.

    Used for deny/ask rule matching where even non-safe env vars
    should not circumvent rules.

    Args:
        command: The shell command string.
        blocklist: Optional regex; matching vars are NOT stripped.

    Returns:
        Command with leading env vars stripped.
    """
    # Broader pattern for deny-rule stripping
    env_var_pattern = re.compile(
        r"^([A-Za-z_][A-Za-z0-9_]*)"
        r"="
        r"[^ \t\n\r$`;&|<>()\\']*"
        r"[ \t]+",
    )

    stripped = command
    previous = ""
    while stripped != previous:
        previous = stripped
        stripped = _strip_comment_lines(stripped)
        m = env_var_pattern.match(stripped)
        if not m:
            continue
        var_name = m.group(1) or ""
        if blocklist and blocklist.match(var_name):
            break
        stripped = stripped[m.end() :]

    return stripped.strip()


# =============================================================================
# Command Prefix Extraction
# =============================================================================


def get_simple_command_prefix(command: str) -> str | None:
    """Extract a stable command prefix (command + subcommand) from a command.

    Skips leading env var assignments if they are in SAFE_ENV_VARS.
    Returns None if a non-safe env var is encountered or the second
    token doesn't look like a subcommand.

    Args:
        command: The shell command string.

    Returns:
        Command+subcommand prefix like "git commit", or None.
    """
    tokens = command.strip().split()
    if not tokens:
        return None

    # Skip safe env var assignments
    i = 0
    while i < len(tokens) and ENV_VAR_ASSIGN_RE.match(tokens[i]):
        var_name = tokens[i].split("=")[0]
        if not _is_safe_env_var(var_name):
            return None
        i += 1

    remaining = tokens[i:]
    if len(remaining) < 2:
        return None
    subcmd = remaining[1]
    # Must look like a subcommand: lowercase alphanumeric
    if not re.match(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$", subcmd):
        return None
    return " ".join(remaining[:2])


def get_first_word_prefix(command: str) -> str | None:
    """Extract the first word as prefix, rejecting dangerous commands.

    Args:
        command: The shell command string.

    Returns:
        First word if it looks like a command, or None.
    """
    tokens = command.strip().split()

    # Skip safe env var assignments
    i = 0
    while i < len(tokens) and ENV_VAR_ASSIGN_RE.match(tokens[i]):
        var_name = tokens[i].split("=")[0]
        if not _is_safe_env_var(var_name):
            return None
        i += 1

    cmd = tokens[i] if i < len(tokens) else None
    if not cmd:
        return None
    if not re.match(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$", cmd):
        return None
    if cmd in BARE_SHELL_PREFIXES:
        return None
    return cmd


def _extract_prefix_before_heredoc(command: str) -> str | None:
    """Extract command prefix before heredoc operator."""
    if "<<" not in command:
        return None
    idx = command.index("<<")
    if idx <= 0:
        return None
    before = command[:idx].strip()
    if not before:
        return None
    prefix = get_simple_command_prefix(before)
    if prefix:
        return prefix
    # Fallback: skip safe env vars and take up to 2 tokens
    tokens = before.split()
    i = 0
    while i < len(tokens) and ENV_VAR_ASSIGN_RE.match(tokens[i]):
        var_name = tokens[i].split("=")[0]
        if not _is_safe_env_var(var_name):
            return None
        i += 1
    if i >= len(tokens):
        return None
    return " ".join(tokens[i : i + 2]) or None


# =============================================================================
# Normalized Command Detection
# =============================================================================


def is_normalized_git_command(command: str) -> bool:
    """Check if a command is a git command after normalization.

    SECURITY: Must normalize before matching to prevent bypasses.

    Args:
        command: The shell command string.

    Returns:
        True if it's a git command.
    """
    stripped = command.strip()
    if stripped.startswith("git ") or stripped == "git":
        return True
    stripped = strip_safe_wrappers(stripped)
    parsed = try_parse_shell_command(stripped)
    if parsed.success and parsed.tokens:
        tokens = parsed.tokens
        if tokens and tokens[0] == "git":
            return True
        # "xargs git ..." - xargs runs git in current directory
        return "git" in tokens
    return bool(re.match(r"^git(?:\s|$)", stripped))


def is_normalized_cd_command(command: str) -> bool:
    """Check if a command is a cd/pushd/popd command after normalization.

    Args:
        command: The shell command string.

    Returns:
        True if it's a directory change command.
    """
    stripped = strip_safe_wrappers(command)
    parsed = try_parse_shell_command(stripped)
    if parsed.success and parsed.tokens:
        cmd = parsed.tokens[0]
        return cmd in ("cd", "pushd", "popd")
    return bool(re.match(r"^(?:cd|pushd|popd)(?:\s|$)", stripped))


def command_has_any_cd(command: str) -> bool:
    """Check if a compound command contains any cd command.

    Args:
        command: The shell command string.

    Returns:
        True if any subcommand is a cd command.
    """
    return any(is_normalized_cd_command(subcmd.strip()) for subcmd in split_command(command))


# =============================================================================
# Permission Rule Matching
# =============================================================================


def permission_rule_extract_prefix(rule: str) -> str | None:
    """Extract prefix from legacy :* syntax (e.g., "npm:*" -> "npm").

    Args:
        rule: The permission rule string.

    Returns:
        Extracted prefix, or None.
    """
    if rule.endswith(":*"):
        return rule[:-2]
    return None


def match_wildcard_pattern(pattern: str, command: str) -> bool:
    """Match a command against a wildcard pattern.

    Args:
        pattern: The wildcard pattern (e.g., "npm:*").
        command: The command string.

    Returns:
        True if the command matches the pattern.
    """
    # Convert wildcard pattern to regex
    # * matches anything (shell-style globbing)
    regex_pattern = re.escape(pattern)
    regex_pattern = regex_pattern.replace(r"\*", r".*")
    regex_pattern = "^" + regex_pattern + "$"
    return bool(re.match(regex_pattern, command))
