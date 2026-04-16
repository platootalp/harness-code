"""
BashTool utilities for command parsing, permission checking, and security validation.

This module is a Python port of the TypeScript BashTool permission system from
src/tools/BashTool/bashPermissions.ts, src/tools/BashTool/bashSecurity.ts,
src/tools/BashTool/bashCommandHelpers.ts, and related files in src/utils/bash/.

It provides:
- Shell quoting and parsing via shell-quote
- Command splitting with operator preservation
- Permission rule matching (exact, prefix, wildcard)
- Security validation for dangerous patterns
- Command normalization for git/cd detection

Security: This module handles command injection detection, shell quoting validation,
and permission rule enforcement for the BashTool.
"""

from __future__ import annotations

import os
import re
from collections.abc import Callable
from dataclasses import dataclass
from random import getrandbits
from typing import TYPE_CHECKING, Any

from . import shell_quote

if TYPE_CHECKING:
    pass

# =============================================================================
# Shell Quoting (shellQuote.ts)
# =============================================================================

# Type aliases matching the TypeScript ParseEntry union
ParseEntry = str | dict[str, Any]
"""A token from shell-quote parse: either a string or an operator dict."""


@dataclass
class ShellParseResult:
    """Result of attempting to parse a shell command."""

    success: bool
    tokens: list[ParseEntry] | None = None
    error: str | None = None


@dataclass
class ShellQuoteResult:
    """Result of attempting to quote shell arguments."""

    success: bool
    quoted: str | None = None
    error: str | None = None


def try_parse_shell_command(
    cmd: str,
    env: dict[str, str] | Callable[[str], str] | None = None,
) -> ShellParseResult:
    """Parse a shell command string into tokens.

    Args:
        cmd: The command string to parse.
        env: Optional environment dict or callable for variable expansion.

    Returns:
        ShellParseResult with tokens on success, or error message on failure.
    """
    try:
        env_dict: dict[str, str] | None = {} if callable(env) else (env if env else {})
        tokens = shell_quote.parse(cmd, env_dict)
        return ShellParseResult(success=True, tokens=tokens)
    except Exception as e:  # noqa: BLE001
        return ShellParseResult(success=False, error=str(e))


def _validate_arg_for_quote(arg: Any, index: int) -> str:
    """Validate and convert an argument to string for quoting."""
    if arg is None:
        return "None"
    if isinstance(arg, bool):
        return str(arg)
    if isinstance(arg, (int, float)):
        return str(arg)
    if isinstance(arg, str):
        return arg
    if isinstance(arg, bytes):
        return arg.decode("utf-8", errors="replace")
    if isinstance(arg, (list, tuple, dict)):
        raise ValueError(
            f"Cannot quote argument at index {index}: "
            f"object values are not supported",
        )
    raise ValueError(
        f"Cannot quote argument at index {index}: unsupported type {type(arg).__name__}",
    )


def try_quote_shell_args(args: list[Any]) -> ShellQuoteResult:
    """Quote shell arguments for safe execution.

    Args:
        args: List of arguments to quote.

    Returns:
        ShellQuoteResult with quoted string on success, or error on failure.
    """
    try:
        validated = [_validate_arg_for_quote(arg, i) for i, arg in enumerate(args)]
        quoted = shell_quote.quote(validated)
        return ShellQuoteResult(success=True, quoted=quoted)
    except Exception as e:  # noqa: BLE001
        return ShellQuoteResult(success=False, error=str(e))


def has_malformed_tokens(command: str, parsed: list[ParseEntry]) -> bool:
    """Check if parsed tokens contain malformed entries suggesting misparsing.

    This detects cases where shell-quote misinterpreted the command due to
    ambiguous patterns (like JSON-like strings with semicolons).

    Also detects unterminated quotes in the original command.

    Args:
        command: The original command string.
        parsed: The parsed tokens from try_parse_shell_command.

    Returns:
        True if the command contains malformed tokens.
    """
    # Check for unterminated quotes in the original command
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

        # Check for unbalanced curly braces
        open_braces = len(re.findall(r"{", entry))
        close_braces = len(re.findall(r"}", entry))
        if open_braces != close_braces:
            return True

        # Check for unbalanced parentheses
        open_parens = len(re.findall(r"\(", entry))
        close_parens = len(re.findall(r"\)", entry))
        if open_parens != close_parens:
            return True

        # Check for unbalanced square brackets
        open_brackets = len(re.findall(r"\[", entry))
        close_brackets = len(re.findall(r"\]", entry))
        if open_brackets != close_brackets:
            return True

        # Check for unbalanced double quotes (unescaped)
        # Match " not preceded by \
        double_quotes = re.findall(r'(?<!\\)"', entry)
        if len(double_quotes) % 2 != 0:
            return True

        # Check for unbalanced single quotes (unescaped)
        single_quotes = re.findall(r"(?<!\\)'", entry)
        if len(single_quotes) % 2 != 0:
            return True

    return False


def has_shell_quote_single_quote_bug(command: str) -> bool:
    """Detect commands exploiting shell-quote's backslash-in-single-quote bug.

    In bash, single quotes preserve all characters literally - backslash has
    no special meaning. But shell-quote incorrectly treats \\ as an escape
    character inside single quotes, causing '\\' to NOT close the quoted string.

    This means patterns like '\\' <payload> '\\' hide <payload> from security
    checks because shell-quote thinks it's all one single-quoted string.

    Args:
        command: The command string to check.

    Returns:
        True if the command exploits the shell-quote single-quote bug.
    """
    in_single_quote = False
    in_double_quote = False

    for i, char in enumerate(command):
        # Handle backslash escaping outside of single quotes
        if char == "\\" and not in_single_quote:
            i += 1  # Skip the next character (it's escaped)
            continue

        if char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            continue

        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote

            # Check if we just closed a single quote and the content ends
            # with trailing backslashes
            if not in_single_quote:
                backslash_count = 0
                j = i - 1
                while j >= 0 and command[j] == "\\":
                    backslash_count += 1
                    j -= 1
                if backslash_count > 0 and backslash_count % 2 == 1:
                    return True
                # Even trailing backslashes: only a bug when a later ' exists
                if (
                    backslash_count > 0
                    and backslash_count % 2 == 0
                    and "'" in command[i + 1 :]
                ):
                    return True

    return False


# =============================================================================
# Heredoc Utilities (heredoc.ts)
# =============================================================================

HEREDOC_PLACEHOLDER_PREFIX = "__HEREDOC_"
HEREDOC_PLACEHOLDER_SUFFIX = "__"


def _generate_placeholder_salt() -> str:
    """Generate a random hex string for placeholder uniqueness."""
    return format(getrandbits(64), "016x")


@dataclass
class HeredocInfo:
    """Information about an extracted heredoc."""

    full_text: str
    delimiter: str
    operator_start_index: int
    operator_end_index: int
    content_start_index: int
    content_end_index: int


@dataclass
class HeredocExtractionResult:
    """Result of extracting heredocs from a command."""

    processed_command: str
    heredocs: dict[str, HeredocInfo]


def extract_heredocs(command: str, *, quoted_only: bool = False) -> HeredocExtractionResult:
    """Extract heredocs from a command and replace with placeholders.

    The shell-quote library parses << as two separate < redirect operators,
    which breaks command splitting for heredoc syntax. This function extracts
    heredocs before parsing and provides a map for restoration.

    Args:
        command: The shell command string potentially containing heredocs.
        quoted_only: If True, only extract quoted heredocs (<<'EOF', <<"EOF").

    Returns:
        HeredocExtractionResult with processed command and heredoc map.
    """
    heredocs: dict[str, HeredocInfo] = {}

    # Quick check: if no << present, skip processing
    if "<<" not in command:
        return HeredocExtractionResult(processed_command=command, heredocs=heredocs)

    # Security: Bail if command contains $'...' or $"..." (ANSI-C quoting)
    if re.search(r"\$['\"]", command):
        return HeredocExtractionResult(processed_command=command, heredocs=heredocs)

    # Security: Bail if backticks appear before the first <<
    first_heredoc_pos = command.find("<<")
    if first_heredoc_pos > 0 and "`" in command[:first_heredoc_pos]:
        return HeredocExtractionResult(processed_command=command, heredocs=heredocs)

    # Security: Bail if arithmetic context before first << is unbalanced
    if first_heredoc_pos > 0:
        before_heredoc = command[:first_heredoc_pos]
        open_arith = len(re.findall(r"\(\(", before_heredoc))
        close_arith = len(re.findall(r"\)\)", before_heredoc))
        if open_arith > close_arith:
            return HeredocExtractionResult(processed_command=command, heredocs=heredocs)

    # Pattern for heredoc start: <<WORD, <<'WORD', <<"WORD", <<-WORD, <<-'WORD'
    # Groups: (1)=dash, (2)=quote char, (3)=quoted delimiter, (4)=unquoted delimiter
    heredoc_pattern = re.compile(
        r"(?<!<)<<(?!<)(-)?[	]*(?:(['\"])(\\?\w+)\2|\\?(\w+))",
    )

    heredoc_matches: list[HeredocInfo] = []
    skipped_ranges: list[tuple[int, int]] = []  # (start, end) of skipped heredoc bodies

    # Incremental quote scanner state
    scan_pos = 0
    scan_in_single = False
    scan_in_double = False
    scan_in_comment = False
    scan_dq_escape_next = False
    scan_pending_backslashes = 0

    def advance_scan(target: int) -> None:
        nonlocal scan_pos, scan_in_single, scan_in_double, scan_in_comment
        nonlocal scan_dq_escape_next, scan_pending_backslashes
        for i in range(scan_pos, target):
            ch = command[i]
            # Any physical newline clears comment state
            if ch == "\n":
                scan_in_comment = False
            if scan_in_single:
                if ch == "'":
                    scan_in_single = False
                continue
            if scan_in_double:
                if scan_dq_escape_next:
                    scan_dq_escape_next = False
                    continue
                if ch == "\\":
                    scan_dq_escape_next = True
                    continue
                if ch == '"':
                    scan_in_double = False
                continue
            # Unquoted context
            if ch == "\\":
                scan_pending_backslashes += 1
                continue
            escaped = scan_pending_backslashes % 2 == 1
            scan_pending_backslashes = 0
            if escaped:
                continue
            if ch == "'":
                scan_in_single = True
            elif ch == '"':
                scan_in_double = True
            elif not scan_in_comment and ch == "#":
                scan_in_comment = True
        scan_pos = target

    for match in heredoc_pattern.finditer(command):
        start_index = match.start()
        advance_scan(start_index)

        # Skip if inside quoted string
        if scan_in_single or scan_in_double:
            continue

        # Skip if inside a comment
        if scan_in_comment:
            continue

        # Skip if preceded by odd backslashes (literal \<\<)
        if scan_pending_backslashes % 2 == 1:
            continue

        # Skip if inside a previously skipped heredoc body
        inside_skipped = False
        for skip_start, skip_end in skipped_ranges:
            if start_index > skip_start and start_index < skip_end:
                inside_skipped = True
                break
        if inside_skipped:
            continue

        full_match = match.group(0)
        is_dash = match.group(1) == "-"
        # Group 3 = quoted delimiter (may include backslash), group 4 = unquoted
        quote_char = match.group(2)
        delimiter = match.group(3) or match.group(4) or ""
        operator_end_index = start_index + len(full_match)

        # Verify closing quote was actually matched
        if quote_char and command[operator_end_index - 1] != quote_char:
            continue

        # Verify next char is a bash word terminator
        if operator_end_index < len(command):
            next_char = command[operator_end_index]
            if not re.match(r"^[ \t\n|&;()<>]$", next_char):
                continue

        # Determine if delimiter is quoted/escaped
        is_escaped_delimiter = "\\" in full_match
        is_quoted_or_escaped = bool(quote_char) or is_escaped_delimiter

        # Find first unquoted newline (start of heredoc content)
        first_newline_offset = -1
        in_single_q = False
        in_double_q = False
        for k in range(operator_end_index, len(command)):
            ch = command[k]
            if in_single_q:
                if ch == "'":
                    in_single_q = False
                continue
            if in_double_q:
                if ch == "\\" and k + 1 < len(command):
                    k += 1  # skip escaped char
                    continue
                if ch == '"':
                    in_double_q = False
                continue
            if ch == "\n":
                first_newline_offset = k - operator_end_index
                break
            if ch == "'":
                in_single_q = True
            elif ch == '"':
                in_double_q = True

        if first_newline_offset == -1:
            continue

        # Check for backslash-newline continuation at end of same-line content
        same_line = command[operator_end_index : operator_end_index + first_newline_offset]
        trailing_backslashes = 0
        for j in range(len(same_line) - 1, -1, -1):
            if same_line[j] == "\\":
                trailing_backslashes += 1
            else:
                break
        if trailing_backslashes % 2 == 1:
            continue

        content_start_index = operator_end_index + first_newline_offset
        after_newline = command[content_start_index + 1 :]
        content_lines = after_newline.split("\n")

        # Find closing delimiter
        closing_line_index = -1
        for i, line in enumerate(content_lines):
            if is_dash:
                stripped = line.replace("\t", "", 1).lstrip("\t")
                if stripped == delimiter:
                    closing_line_index = i
                    break
            else:
                if line == delimiter:
                    closing_line_index = i
                    break
                # Check for PST_EOFTOKEN-like early closure
                eof_check_line = line
                if (
                    len(eof_check_line) > len(delimiter)
                    and eof_check_line.startswith(delimiter)
                ):
                    char_after = eof_check_line[len(delimiter) :]
                    if char_after and char_after[0] in ")}|&;(<>":
                        closing_line_index = -1
                        break

        # Handle quoted_only mode for unquoted heredocs
        if quoted_only and not is_quoted_or_escaped:
            if closing_line_index == -1:
                skip_end = len(command)
            else:
                lines_up_to_closing = content_lines[: closing_line_index + 1]
                skip_content_length = len("\n".join(lines_up_to_closing))
                skip_end = content_start_index + 1 + skip_content_length
            skipped_ranges.append((content_start_index, skip_end))
            continue

        if closing_line_index == -1:
            continue

        # Check for overlapping skipped ranges
        overlaps_skipped = False
        for skip_start, skip_end in skipped_ranges:
            if content_start_index < skip_end and skip_start < operator_end_index + first_newline_offset + len(
                "\n".join(content_lines[: closing_line_index + 1]),
            ):
                overlaps_skipped = True
                break
        if overlaps_skipped:
            continue

        # Calculate content end
        lines_up_to_closing = content_lines[: closing_line_index + 1]
        content_length = len("\n".join(lines_up_to_closing))
        content_end_index = content_start_index + 1 + content_length

        heredoc_matches.append(
            HeredocInfo(
                full_text=command[start_index:content_end_index],
                delimiter=delimiter,
                operator_start_index=start_index,
                operator_end_index=operator_end_index,
                content_start_index=content_start_index,
                content_end_index=content_end_index,
            ),
        )

    if not heredoc_matches:
        return HeredocExtractionResult(processed_command=command, heredocs=heredocs)

    # Filter nested heredocs (operator starts inside another heredoc's content)
    top_level = []
    for candidate in heredoc_matches:
        nested = False
        for other in heredoc_matches:
            if candidate is other:
                continue
            if (
                candidate.operator_start_index > other.content_start_index
                and candidate.operator_start_index < other.content_end_index
            ):
                nested = True
                break
        if not nested:
            top_level.append(candidate)

    if not top_level:
        return HeredocExtractionResult(processed_command=command, heredocs=heredocs)

    # Check for duplicate content start positions
    content_starts = [h.content_start_index for h in top_level]
    if len(content_starts) != len(set(content_starts)):
        return HeredocExtractionResult(processed_command=command, heredocs=heredocs)

    # Sort by content end descending for replacement
    top_level.sort(key=lambda h: h.content_end_index, reverse=True)

    # Generate salt and replace
    salt = _generate_placeholder_salt()
    processed = command
    for idx, info in enumerate(reversed(top_level)):
        ph_idx = len(top_level) - 1 - idx
        placeholder = f"{HEREDOC_PLACEHOLDER_PREFIX}{ph_idx}_{salt}{HEREDOC_PLACEHOLDER_SUFFIX}"
        heredocs[placeholder] = info
        processed = (
            processed[: info.operator_start_index]
            + placeholder
            + processed[info.operator_end_index : info.content_start_index]
            + processed[info.content_end_index :]
        )

    return HeredocExtractionResult(processed_command=processed, heredocs=heredocs)


def restore_heredocs(parts: list[str], heredocs: dict[str, HeredocInfo]) -> list[str]:
    """Restore heredoc placeholders in a list of strings.

    Args:
        parts: List of strings that may contain heredoc placeholders.
        heredocs: Map of placeholders to HeredocInfo.

    Returns:
        New list with placeholders replaced by original heredoc content.
    """
    if not heredocs:
        return parts
    return [restore_heredocs_in_string(part, heredocs) for part in parts]


def restore_heredocs_in_string(
    text: str,
    heredocs: dict[str, HeredocInfo],
) -> str:
    """Restore heredoc placeholders in a single string."""
    result = text
    for placeholder, info in heredocs.items():
        result = result.replace(placeholder, info.full_text)
    return result


# =============================================================================
# Placeholders (bashParser.ts - generatePlaceholders)
# =============================================================================


def generate_placeholders() -> dict[str, str]:
    """Generate placeholder strings with random salt to prevent injection attacks.

    The salt prevents malicious commands from containing literal placeholder
    strings that would be replaced during parsing.

    Returns:
        Dict with placeholder strings for single/double quotes, newlines, parens.
    """
    salt = format(getrandbits(64), "016x")
    return {
        "SINGLE_QUOTE": f"__SINGLE_QUOTE_{salt}__",
        "DOUBLE_QUOTE": f"__DOUBLE_QUOTE_{salt}__",
        "NEW_LINE": f"__NEW_LINE_{salt}__",
        "ESCAPED_OPEN_PAREN": f"__ESCAPED_OPEN_PAREN_{salt}__",
        "ESCAPED_CLOSE_PAREN": f"__ESCAPED_CLOSE_PAREN_{salt}__",
    }


# =============================================================================
# Command Splitting (commands.ts - splitCommandWithOperators)
# =============================================================================

# File descriptor numbers
ALLOWED_FILE_DESCRIPTORS = frozenset(["0", "1", "2"])

# Control operators for splitting
COMMAND_LIST_SEPARATORS = frozenset(["&&", "||", ";", ";;", "|"])
ALL_SUPPORTED_CONTROL_OPERATORS = frozenset([*COMMAND_LIST_SEPARATORS, ">&", ">", ">>"])


def _is_operator(part: ParseEntry | None, op: str) -> bool:
    """Check if a parse entry is an operator with the given name."""
    return isinstance(part, dict) and part.get("op") == op


def is_static_redirect_target(target: str) -> bool:
    """Check if a redirect target is a static file path (no expansions).

    Returns False for targets containing variables, command substitutions,
    globs, or shell expansions.
    """
    if re.search(r"[\s'\"]", target):
        return False
    if len(target) == 0:
        return False
    if target.startswith("#"):
        return False
    return not any(
        ch in target
        for ch in [
            "!",
            "$",
            "`",
            "*",
            "?",
            "[",
            "{",
            "~",
            "(",
            "<",
            "&",
            "=",
        ]
    )


def _join_line_continuations(command: str) -> str:
    """Join backslash-newline line continuations.

    Only joins when there's an odd number of backslashes before the newline
    (last backslash escapes the newline, making it a continuation).
    """
    result = []
    i = 0
    while i < len(command):
        if command[i] == "\\" and i + 1 < len(command) and command[i + 1] == "\n":
            # Count backslashes
            j = i
            while j < len(command) and command[j] == "\\":
                j += 1
            backslash_count = j - i
            next_idx = j + 1  # skip past all backslashes and newline
            if backslash_count % 2 == 1:
                # Odd: last backslash escapes newline, join lines
                result.append("\\" * (backslash_count - 1))
                i = next_idx
                continue
            else:
                # Even: all backslashes are pairs, newline is separator
                result.append("\\" * backslash_count)
                i = j
                continue
        result.append(command[i])
        i += 1
    return "".join(result)


def _join_line_continuations_simple(command: str) -> str:
    """Simple version using regex for cleaner code."""
    def replacer(match: re.Match[str]) -> str:
        backslash_count = len(match.group(0)) - 1  # -1 for the newline
        if backslash_count % 2 == 1:
            return "\\" * (backslash_count - 1)
        return str(match.group(0))

    return re.sub(r"\\+\n", replacer, command)


def _escape_for_parse(text: str, placeholders: dict[str, str]) -> str:
    """Escape quotes, newlines, and escaped parens for shell-quote parsing."""
    result = text
    result = result.replace('"', f'"{placeholders["DOUBLE_QUOTE"]}')
    result = result.replace("'", f"'{placeholders['SINGLE_QUOTE']}")
    result = result.replace("\n", f"\n{placeholders['NEW_LINE']}\n")
    result = result.replace("\\(", placeholders["ESCAPED_OPEN_PAREN"])
    result = result.replace("\\)", placeholders["ESCAPED_CLOSE_PAREN"])
    return result


def split_command_with_operators(command: str) -> list[str]:
    """Split a command string into parts, preserving operators.

    This function uses shell-quote to parse the command and reconstructs
    it with operators intact. It handles heredocs, line continuations, and
    various shell constructs.

    Args:
        command: The shell command string to split.

    Returns:
        List of command segments with operators preserved.
    """
    # Extract heredocs before parsing
    heredoc_result = extract_heredocs(command)
    processed = heredoc_result.processed_command

    # Join line continuations
    processed = _join_line_continuations_simple(processed)

    # Join continuations on original for fallback
    command_joined = _join_line_continuations_simple(command)

    # Generate placeholders
    placeholders = generate_placeholders()

    # Escape for parsing
    escaped = _escape_for_parse(processed, placeholders)

    # Parse with env var preservation
    parse_result = try_parse_shell_command(escaped, lambda v: f"${v}")
    if not parse_result.success:
        return [command_joined]

    parsed = parse_result.tokens or []
    if not parsed:
        return []

    # Phase 1: Collapse adjacent strings and handle operators
    parts: list[ParseEntry | None] = []
    for part in parsed:
        if isinstance(part, str):
            if parts and isinstance(parts[-1], str):
                if part == placeholders["NEW_LINE"]:
                    parts.append(None)
                else:
                    parts[-1] += " " + part
            else:
                parts.append(part)
        elif isinstance(part, dict) and part.get("op") == "glob":
            if parts and isinstance(parts[-1], str):
                parts[-1] += " " + part.get("pattern", "")
            else:
                parts.append(part)
        else:
            parts.append(part)

    # Phase 2: Map tokens to strings
    string_parts: list[str | None] = []
    for part in parts:  # type: ignore[assignment]
        if part is None:
            string_parts.append(None)
        elif isinstance(part, str):
            string_parts.append(part)
        elif isinstance(part, dict):
            part_dict: dict[str, Any] = part
            if "comment" in part_dict:
                comment_text = part_dict["comment"]
                # Strip injected quote markers
                comment_text = comment_text.replace(
                    f'"{placeholders["DOUBLE_QUOTE"]}',
                    placeholders["DOUBLE_QUOTE"],
                )
                comment_text = comment_text.replace(
                    f"'{placeholders['SINGLE_QUOTE']}",
                    placeholders["SINGLE_QUOTE"],
                )
                string_parts.append("#" + comment_text)
            elif part_dict.get("op") == "glob":
                string_parts.append(part_dict.get("pattern", ""))
            elif "op" in part_dict:
                op_val: str = part_dict["op"]
                string_parts.append(op_val)
            else:
                string_parts.append(None)
        else:
            string_parts.append(None)

    # Phase 3: Un-escape quotes and newlines
    quoted_parts: list[str] = []
    for string_part in string_parts:
        if string_part is None:
            continue
        result: str = string_part
        result = result.replace(placeholders["SINGLE_QUOTE"], "'")
        result = result.replace(placeholders["DOUBLE_QUOTE"], '"')
        result = result.replace(f"\n{placeholders['NEW_LINE']}\n", "\n")
        result = result.replace(placeholders["ESCAPED_OPEN_PAREN"], "\\(")
        result = result.replace(placeholders["ESCAPED_CLOSE_PAREN"], "\\)")
        quoted_parts.append(result)

    # Restore heredocs
    return restore_heredocs(quoted_parts, heredoc_result.heredocs)


def filter_control_operators(commands_and_operators: list[str]) -> list[str]:
    """Filter out control operators from a list of command parts."""
    return [part for part in commands_and_operators if part not in ALL_SUPPORTED_CONTROL_OPERATORS]


def _is_simple_target(target: str) -> bool:
    """Check if a redirect target is simple (no dangerous expansions)."""
    if not target or len(target) == 0:
        return False
    if target.startswith("!"):
        return False
    if target.startswith("="):
        return False
    if target.startswith("~"):
        return False
    return not any(
        ch in target
        for ch in ["$", "`", "*", "?", "[", "{"]
    )


def _has_dangerous_expansion(target: str) -> bool:
    """Check if a redirect target contains dangerous shell expansions."""
    if not target or len(target) == 0:
        return False
    return any(
        ch in target
        for ch in [
            "$",
            "%",
            "`",
            "*",
            "?",
            "[",
            "{",
            "!",
            "=",
            "~",
        ]
    )


def _handle_file_descriptor_redirection(
    fd: str,
    operator: str,
    target: str | None,
    redirections: list[dict[str, str]],
    kept: list[ParseEntry],
    skip_count: int = 1,
) -> tuple[int, bool]:
    """Handle file descriptor redirections like 2>/dev/null, 2>&1."""
    is_stdout = fd == "1"
    is_fd_target = target is not None and bool(re.match(r"^\d+$", target.strip()))

    # Check for dangerous expansion first
    if target and not is_fd_target and _has_dangerous_expansion(target):
        return 0, True

    if target and _is_simple_target(target) and not is_fd_target:
        redirections.append({"target": target, "operator": operator})
        if not is_stdout:
            kept.append(fd + operator)
            kept.append(target)
        return skip_count, False

    if not is_stdout:
        kept.append(fd + operator)
        if target:
            kept.append(target)
            return 1, False

    return 0, False


def _handle_redirection(
    part: ParseEntry,
    prev: ParseEntry | None,
    next_entry: ParseEntry | None,
    next_next: ParseEntry | None,
    next_next_next: ParseEntry | None,
    redirections: list[dict[str, str]],
    kept: list[ParseEntry],
) -> tuple[int, bool]:
    """Handle redirection operators (> , >> , >&)."""
    op = part.get("op") if isinstance(part, dict) else None

    if op in (">", ">>"):
        operator = op

        # File descriptor redirect
        if isinstance(prev, str) and re.match(r"^\d+$", prev.strip()):
            fd = prev.strip()

            # 2>! filename
            if next_entry == "!" and _is_simple_target(next_next if isinstance(next_next, str) else ""):
                return _handle_file_descriptor_redirection(
                    fd, operator, next_next if isinstance(next_next, str) else None, redirections, kept, 2,
                )
            if next_entry == "!" and _has_dangerous_expansion(next_next if isinstance(next_next, str) else ""):
                return 0, True

            # 2>| or 2>&
            if _is_operator(next_entry, "|") and _is_simple_target(next_next if isinstance(next_next, str) else ""):
                return _handle_file_descriptor_redirection(
                    fd, operator, next_next if isinstance(next_next, str) else None, redirections, kept, 2,
                )
            if _is_operator(next_entry, "|") and _has_dangerous_expansion(next_next if isinstance(next_next, str) else ""):
                return 0, True

            # 2>!filename (no space) - zsh force clobber
            if (
                isinstance(next_entry, str)
                and next_entry.startswith("!")
                and len(next_entry) > 1
                and next_entry[1] not in "!?-?"
                and not re.match(r"^!\d", next_entry)
            ):
                after_bang = next_entry[1:]
                if _has_dangerous_expansion(after_bang):
                    return 0, True
                redirections.append({"target": after_bang, "operator": operator})
                return 1, False

            return _handle_file_descriptor_redirection(
                fd, operator, next_entry if isinstance(next_entry, str) else None, redirections, kept, 1,
            )

        # >| POSIX force overwrite
        if _is_operator(next_entry, "|") and _is_simple_target(next_next if isinstance(next_next, str) else ""):
            redirections.append({"target": str(next_next), "operator": operator})
            return 2, False
        if _is_operator(next_entry, "|") and _has_dangerous_expansion(next_next if isinstance(next_next, str) else ""):
            return 0, True

        # >! ZSH force clobber
        if next_entry == "!" and _is_simple_target(next_next if isinstance(next_next, str) else ""):
            redirections.append({"target": str(next_next), "operator": operator})
            return 2, False
        if next_entry == "!" and _has_dangerous_expansion(next_next if isinstance(next_next, str) else ""):
            return 0, True

        # >!filename (no space) - filename starts with !
        if (
            isinstance(next_entry, str)
            and next_entry.startswith("!")
            and len(next_entry) > 1
            and next_entry[1] not in "!?-?"
            and not re.match(r"^!\d", next_entry)
        ):
            after_bang = next_entry[1:]
            if _has_dangerous_expansion(after_bang):
                return 0, True
            redirections.append({"target": after_bang, "operator": operator})
            return 1, False

        # >>&! and >>&| combined operators
        if _is_operator(next_entry, "&"):
            if next_next == "!" and _is_simple_target(next_next_next if isinstance(next_next_next, str) else ""):
                redirections.append({"target": str(next_next_next), "operator": operator})
                return 3, False
            if next_next == "!" and _has_dangerous_expansion(next_next_next if isinstance(next_next_next, str) else ""):
                return 0, True
            if _is_operator(next_next, "|") and _is_simple_target(next_next_next if isinstance(next_next_next, str) else ""):
                redirections.append({"target": str(next_next_next), "operator": operator})
                return 3, False
            if _is_operator(next_next, "|") and _has_dangerous_expansion(next_next_next if isinstance(next_next_next, str) else ""):
                return 0, True
            if _is_simple_target(next_next if isinstance(next_next, str) else ""):
                redirections.append({"target": str(next_next), "operator": operator})
                return 2, False
            if _has_dangerous_expansion(next_next if isinstance(next_next, str) else ""):
                return 0, True

        # Standard stdout redirection
        if _is_simple_target(next_entry if isinstance(next_entry, str) else ""):
            redirections.append({"target": str(next_entry), "operator": operator})
            return 1, False
        if _has_dangerous_expansion(next_entry if isinstance(next_entry, str) else ""):
            return 0, True

    if op == ">&":
        # 2>&1 style
        if (
            isinstance(prev, str)
            and re.match(r"^\d+$", prev.strip())
            and isinstance(next_entry, str)
            and re.match(r"^\d+$", next_entry.strip())
        ):
            return 0, False

        # >&| or >&!
        if _is_operator(next_entry, "|") and _is_simple_target(next_next if isinstance(next_next, str) else ""):
            redirections.append({"target": str(next_next), "operator": ">"})
            return 2, False
        if _is_operator(next_entry, "|") and _has_dangerous_expansion(next_next if isinstance(next_next, str) else ""):
            return 0, True
        if next_entry == "!" and _is_simple_target(next_next if isinstance(next_next, str) else ""):
            redirections.append({"target": str(next_next), "operator": ">"})
            return 2, False
        if next_entry == "!" and _has_dangerous_expansion(next_next if isinstance(next_next, str) else ""):
            return 0, True

        # Redirect to file
        if (
            _is_simple_target(next_entry if isinstance(next_entry, str) else "")
            and not isinstance(next_entry, str)
        ) is False and isinstance(next_entry, str):
            pass
        if (
            isinstance(next_entry, str)
            and _is_simple_target(next_entry)
            and not re.match(r"^\d+$", next_entry.strip())
        ):
            redirections.append({"target": next_entry, "operator": ">"})
            return 1, False
        if (
            isinstance(next_entry, str)
            and not re.match(r"^\d+$", next_entry.strip())
            and _has_dangerous_expansion(next_entry)
        ):
            return 0, True

    return 0, False


def _needs_quoting(text: str) -> bool:
    """Check if a string needs shell quoting."""
    # File descriptor redirects
    if re.match(r"^\d+>>?$", text):
        return False
    # Any whitespace
    if re.search(r"\s", text):
        return True
    # Single-char shell operators
    return bool(len(text) == 1 and text in "><|&;()")


def _reconstruct_command(kept: list[ParseEntry], original_cmd: str) -> str:
    """Reconstruct a command string from parsed entries."""
    if not kept:
        return original_cmd

    quote_result = try_quote_shell_args(kept)
    if quote_result.success and quote_result.quoted:
        return quote_result.quoted

    # Fallback: manual reconstruction
    result_parts: list[str] = []
    for i, part in enumerate(kept):
        prev = kept[i - 1] if i > 0 else None
        kept[i + 1] if i + 1 < len(kept) else None

        if isinstance(part, str):
            has_sep = bool(re.search(r"[|&;]", part))
            if has_sep:
                str_val = f'"{part}"'
            elif _needs_quoting(part):
                q_res = try_quote_shell_args([part])
                assert q_res.quoted is not None
                str_val = q_res.quoted
            else:
                str_val = part

            no_space = (
                (isinstance(prev, str) and prev.endswith("("))
                or prev == "$"
                or (isinstance(prev, dict) and prev.get("op") == ")")
            )
            if result_parts and not no_space:
                result_parts.append(" ")
            result_parts.append(str_val)
        elif isinstance(part, dict) and "op" in part:
            op = part["op"]
            if op in ["&&", "||", "|", ";", ">", ">>", "<", "(", ")"]:
                if result_parts:
                    result_parts.append(" ")
                result_parts.append(op)
            elif op == "glob" and "pattern" in part:
                if result_parts:
                    result_parts.append(" ")
                result_parts.append(part["pattern"])

    return " ".join(result_parts) if result_parts else original_cmd


def split_command_DEPRECATED(command: str) -> list[str]:
    """Split a command string into individual commands (legacy).

    This is the deprecated regex/shell-quote path. Only used when tree-sitter
    is unavailable. Prefer split_command_with_operators for new code.

    Args:
        command: The shell command string to split.

    Returns:
        List of individual command strings.
    """
    parts: list[str | None] = list(split_command_with_operators(command))

    # Handle redirections
    result_parts: list[str | None] = list(parts)
    for i in range(len(result_parts)):
        part = result_parts[i]
        if part is None:
            continue

        # Handle > and >> operators
        if part in ("<&gt;", "&gt;", "&gt;&gt;"):  # noqa: RUF001
            prev_part = result_parts[i - 1] if i > 0 else None
            next_part = result_parts[i + 1] if i + 1 < len(result_parts) else None
            after_next = result_parts[i + 2] if i + 2 < len(result_parts) else None

            if next_part is None:
                continue

            # Determine effective next part (handle merged FD like /dev/null 2)
            effective_next = next_part
            if (
                part in ("&gt;", "&gt;&gt;")  # noqa: RUF001
                and next_part
                and len(next_part) >= 3
                and next_part[-2] == " "
                and next_part[-1] in ALLOWED_FILE_DESCRIPTORS
                and after_next in ("&gt;", "&gt;&gt;", "&gt;&&gt;")  # noqa: RUF001
            ):
                effective_next = next_part[:-2]

            should_strip = False
            strip_third = False

            if part == "&gt;&&gt;" and next_part in ALLOWED_FILE_DESCRIPTORS:  # noqa: RUF001
                should_strip = True
            elif (
                part == "&gt;"
                and next_part == "&"
                and after_next is not None
                and after_next in ALLOWED_FILE_DESCRIPTORS
            ):
                should_strip = True
                strip_third = True
            elif (
                part == "&gt;"
                and isinstance(next_part, str)
                and next_part.startswith("&")
                and len(next_part) > 1
                and next_part[1:] in ALLOWED_FILE_DESCRIPTORS
            ) or part in ("&gt;", "&gt;&gt;") and is_static_redirect_target(effective_next or ""):
                should_strip = True

            if should_strip:
                # Strip trailing FD from previous part
                if (
                    prev_part
                    and isinstance(prev_part, str)
                    and len(prev_part) >= 3
                    and prev_part[-1] in ALLOWED_FILE_DESCRIPTORS
                    and prev_part[-2] == " "
                ):
                    result_parts[i - 1] = prev_part[:-2]
                result_parts[i] = None
                result_parts[i + 1] = None
                if strip_third and i + 2 < len(result_parts):
                    result_parts[i + 2] = None

    # Filter out None entries and empty strings
    return [p for p in result_parts if p is not None and p != ""]


def split_command(command: str) -> list[str]:
    """Split a command string into individual commands.

    Args:
        command: The shell command string to split.

    Returns:
        List of individual command strings.
    """
    return split_command_DEPRECATED(command)


def extract_output_redirections(cmd: str) -> dict[str, Any]:
    """Extract output redirections from a command.

    Args:
        cmd: The shell command string.

    Returns:
        Dict with commandWithoutRedirections, redirections list, and
        hasDangerousRedirection flag.
    """
    redirections: list[dict[str, str]] = []
    has_dangerous = False

    # Extract heredocs first
    heredoc_result = extract_heredocs(cmd)
    processed = heredoc_result.processed_command

    # Join line continuations
    processed = _join_line_continuations_simple(processed)

    # Parse
    parse_result = try_parse_shell_command(processed, lambda v: f"${v}")
    if not parse_result.success:
        return {
            "commandWithoutRedirections": cmd,
            "redirections": [],
            "hasDangerousRedirection": True,
        }

    parsed = parse_result.tokens or []

    # Find redirected subshells
    redirected_subshells: set[int] = set()
    paren_stack: list[tuple[int, bool]] = []

    for i, part in enumerate(parsed):
        if isinstance(part, dict) and part.get("op") == "(":
            prev = parsed[i - 1] if i > 0 else None
            is_start = (
                i == 0
                or (
                    isinstance(prev, dict)
                    and prev.get("op") in ["&&", "||", ";", "|"]
                )
            )
            paren_stack.append((i, bool(is_start)))
        elif isinstance(part, dict) and part.get("op") == ")":
            if paren_stack:
                opening_idx, _ = paren_stack.pop()
                next_entry = parsed[i + 1] if i + 1 < len(parsed) else None
                if (
                    _is_operator(next_entry, "&gt;")  # noqa: RUF001
                    or _is_operator(next_entry, "&gt;&gt;")  # noqa: RUF001
                ):
                    redirected_subshells.add(opening_idx)
                    redirected_subshells.add(i)

    # Process command and extract redirections
    kept: list[ParseEntry] = []
    cmd_sub_depth = 0

    i = 0
    while i < len(parsed):
        part = parsed[i]
        prev = parsed[i - 1] if i > 0 else None
        next_entry = parsed[i + 1] if i + 1 < len(parsed) else None
        next_next = parsed[i + 2] if i + 2 < len(parsed) else None
        next_next_next = parsed[i + 3] if i + 3 < len(parsed) else None

        # Skip redirected subshell parens
        if (
            (isinstance(part, dict) and part.get("op") in ["(", ")"])
            and i in redirected_subshells
        ):
            i += 1
            continue

        # Track command substitution depth
        if (
            isinstance(part, dict)
            and part.get("op") == "("
            and isinstance(prev, str)
            and prev.endswith("$")
        ):
            cmd_sub_depth += 1
        elif isinstance(part, dict) and part.get("op") == ")" and cmd_sub_depth > 0:
            cmd_sub_depth -= 1

        if cmd_sub_depth == 0:
            skip, dangerous = _handle_redirection(
                part, prev, next_entry, next_next, next_next_next, redirections, kept,
            )
            if dangerous:
                has_dangerous = True
            if skip > 0:
                i += skip
                continue

        kept.append(part)
        i += 1

    # Reconstruct command without redirections
    reconstructed = _reconstruct_command(kept, cmd)

    # Restore heredocs
    restored_parts = restore_heredocs([reconstructed], heredoc_result.heredocs)
    command_without = restored_parts[0] if restored_parts else reconstructed

    return {
        "commandWithoutRedirections": command_without,
        "redirections": redirections,
        "hasDangerousRedirection": has_dangerous,
    }


def is_help_command(command: str) -> bool:
    """Check if a command is a help command (e.g., "foo --help").

    Args:
        command: The shell command string.

    Returns:
        True if it's a help command, False otherwise.
    """
    trimmed = command.strip()

    if not trimmed.endswith("--help"):
        return False

    # Reject commands with quotes
    if '"' in trimmed or "'" in trimmed:
        return False

    parse_result = try_parse_shell_command(trimmed)
    if not parse_result.success:
        return False

    tokens = parse_result.tokens or []
    found_help = False

    alphanumeric_pattern = re.compile(r"^[a-zA-Z0-9]+$")

    for token in tokens:
        if isinstance(token, str):
            if token.startswith("-"):
                if token == "--help":
                    found_help = True
                else:
                    return False
            else:
                if not alphanumeric_pattern.match(token):
                    return False

    return found_help


# =============================================================================
# Bash Permissions Constants (bashPermissions.ts)
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


def _is_ant_user() -> bool:
    """Check if running as an ANT user."""
    return os.environ.get("USER_TYPE") == "ant"


def _is_safe_env_var(var_name: str) -> bool:
    """Check if an env var is in the safe list."""
    if var_name in SAFE_ENV_VARS:
        return True
    return bool(_is_ant_user() and var_name in ANT_ONLY_SAFE_ENV_VARS)


# =============================================================================
# Safe Wrapper Stripping (bashPermissions.ts - stripSafeWrappers)
# =============================================================================

# Timeout flag value pattern (allowlist)
TIMEOUT_FLAG_VALUE_RE = re.compile(r"^[A-Za-z0-9_.+-]+$")

# Safe wrapper patterns
_TIMEOUT_PATTERN = re.compile(
    r"^timeout[	]+(?:(?:--(?:foreground|preserve-status|verbose)"
    r"|--(?:kill-after|signal)=[A-Za-z0-9_.+-]+"
    r"|--(?:kill-after|signal)[	]+[A-Za-z0-9_.+-]+"
    r"|-v|-[ks][	]+[A-Za-z0-9_.+-]+|-[ks][A-Za-z0-9_.+-]+))"
    r"[	]+(?:--[	]+)?\d+(?:\.\d+)?[smhd]?[	]+",
)
_TIME_PATTERN = re.compile(r"^time[	]+(?:--[	]+)?")
_NICE_PATTERN = re.compile(
    r"^nice(?:[	]+-n[	]+-?\d+|[	]+-\d+)?[	]+(?:--[	]+)?",
)
_STDBUF_PATTERN = re.compile(r"^stdbuf(?:[	]+-[ioe][LN0-9]+)+[	]+(?:--[	]+)?")
_NOHUP_PATTERN = re.compile(r"^nohup[	]+(?:--[	]+)?")

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
    r"[	]+",
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
        if arg in ("--foreground", "--preserve-status", "--verbose") or re.match(r"^--(?:kill-after|signal)=[A-Za-z0-9_.+-]+$", arg):
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
        r"[	]+",
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
# Command Prefix Extraction (bashPermissions.ts - getSimpleCommandPrefix)
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
# Normalized Command Detection (bashPermissions.ts)
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
# Bash Security Validation (bashSecurity.ts)
# =============================================================================

# Command substitution patterns to detect
COMMAND_SUBSTITUTION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"<\\\("), "process substitution <()"),
    (re.compile(r">\\\("), "process substitution >()"),
    (re.compile(r"=\\\("), "Zsh process substitution =()"),
    (re.compile(r"(?:^|[\s;&|])=[a-zA-Z_]"), "Zsh equals expansion (=cmd)"),
    (re.compile(r"\\$\\\("), "$() command substitution"),
    (re.compile(r"\\$\\{"), "${} parameter substitution"),
    (re.compile(r"$\[\]"), "$[] legacy arithmetic expansion"),
    (re.compile(r"~\[[]]"), "Zsh-style parameter expansion"),
    (re.compile(r"\\(e:\\)"), "Zsh-style glob qualifiers"),
    (re.compile(r"\\(\\+\\)"), "Zsh glob qualifier with command execution"),
    (re.compile(r"\\}\\s*always\\s*\\{"), "Zsh always block"),
    (re.compile(r"<#"), "PowerShell comment syntax"),
]

# Zsh dangerous commands
ZSH_DANGEROUS_COMMANDS: frozenset[str] = frozenset([
    "zmodload",
    "emulate",
    "sysopen",
    "sysread",
    "syswrite",
    "sysseek",
    "zpty",
    "ztcp",
    "zsocket",
    "mapfile",
    "zf_rm",
    "zf_mv",
    "zf_ln",
    "zf_chmod",
    "zf_chown",
    "zf_mkdir",
    "zf_rmdir",
    "zf_chgrp",
])

HEREDOC_IN_SUBSTITUTION = re.compile(r"\\$\\\(.*<<\)")


def _extract_quoted_content(command: str) -> tuple[str, str, str]:
    """Extract quoted content from a command.

    Returns:
        Tuple of (with_double_quotes, fully_unquoted, unquoted_keep_quote_chars).
    """
    with_double = ""
    fully_unquoted = ""
    unquoted_keep = ""
    in_single = False
    in_double = False
    escaped = False

    for char in command:
        if escaped:
            escaped = False
            if not in_single:
                with_double += char
                fully_unquoted += char
                unquoted_keep += char
            continue

        if char == "\\" and not in_single:
            escaped = True
            if not in_single:
                with_double += char
                fully_unquoted += char
                unquoted_keep += char
            continue

        if char == "'" and not in_double:
            in_single = not in_single
            unquoted_keep += char
            continue

        if char == '"' and not in_single:
            in_double = not in_double
            unquoted_keep += char
            continue

        if not in_single:
            with_double += char
        if not in_single and not in_double:
            fully_unquoted += char
        if not in_single and not in_double:
            unquoted_keep += char

    return with_double, fully_unquoted, unquoted_keep


def _strip_safe_redirections(content: str) -> str:
    """Strip safe redirection patterns from content."""
    return (
        content.replace(" 2>&1", "", 1).replace("2 >&1", "", 1)
        # .replace(...) etc - simplified version
    )


def _has_unescaped_char(content: str, char: str) -> bool:
    """Check if content contains an unescaped occurrence of a character."""
    in_single = False
    in_double = False
    escaped = False
    i = 0
    while i < len(content):
        c = content[i]
        if escaped:
            escaped = False
            i += 1
            continue
        if c == "\\" and not in_single:
            escaped = True
            i += 1
            continue
        if c == "'" and not in_double:
            in_single = not in_single
            i += 1
            continue
        if c == '"' and not in_single:
            in_double = not in_double
            i += 1
            continue
        if c == char and not in_single and not in_double:
            return True
        i += 1
    return False


def _check_security_patterns(command: str) -> str | None:
    """Check for dangerous security patterns in a command.

    Args:
        command: The shell command string.

    Returns:
        Error message if dangerous pattern found, None otherwise.
    """
    # Check command substitution patterns
    for pattern, message in COMMAND_SUBSTITUTION_PATTERNS:
        if pattern.search(command):
            return f"Command contains {message}"
        # Check heredoc in substitution
        if pattern == re.compile(r"\\$\\(") and HEREDOC_IN_SUBSTITUTION.search(command):
            pass  # Already handled

    # Check for unescaped shell operators
    dangerous_ops = [
        (r"(?<!\\)(?:^|[^\\])\|(?![|=])", "pipe operator"),
        (r"(?<!\\);;", "sequential operator"),
        (r"(?<!\\)&(?!&)", "background operator"),
    ]
    for dangerous_pattern, name in dangerous_ops:
        if re.search(dangerous_pattern, command):
            return f"Command contains dangerous {name}"

    # Check for incomplete commands
    if re.search(r"[^\\]&$", command):
        return "Command ends with unescaped &"

    return None


def bash_command_is_safe(command: str) -> dict[str, Any]:
    """Check if a command is safe (legacy regex-based check).

    This is the deprecated shell-quote-based security check. It has known
    limitations and misparses certain patterns. Prefer tree-sitter parsing
    when available.

    Args:
        command: The shell command string.

    Returns:
        Dict with behavior ('passthrough', 'ask', 'deny'), message, and flags.
    """
    # Quick parse check
    parse_result = try_parse_shell_command(command)
    if not parse_result.success:
        return {
            "behavior": "ask",
            "message": f"Command contains malformed syntax: {parse_result.error}",
            "is_bash_security_check_for_misparsing": False,
        }

    parsed = parse_result.tokens or []

    # Check for malformed tokens
    if has_malformed_tokens(command, parsed):
        return {
            "behavior": "ask",
            "message": "Command contains patterns that could pose security risks",
            "is_bash_security_check_for_misparsing": True,
        }

    # Check for shell-quote single quote bug
    if has_shell_quote_single_quote_bug(command):
        return {
            "behavior": "ask",
            "message": "Command contains patterns that could pose security risks",
            "is_bash_security_check_for_misparsing": True,
        }

    # Check for command substitution patterns
    for pattern, message in COMMAND_SUBSTITUTION_PATTERNS:
        if pattern.search(command):
            return {
                "behavior": "ask",
                "message": f"Command contains {message}",
                "is_bash_security_check_for_misparsing": False,
            }

    # Check for incomplete commands (ends with |, &, etc.)
    if re.search(r"[^\\]&[^\s&]*$", command):
        return {
            "behavior": "ask",
            "message": "Command contains incomplete structure",
            "is_bash_security_check_for_misparsing": True,
        }

    # Check base command for zsh dangerous commands
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


# =============================================================================
# Command Operator Permissions (bashCommandHelpers.ts)
# =============================================================================


def check_command_operator_permissions(
    command: str,
    checkers: dict[str, Callable[[str], bool]],
) -> dict[str, Any]:
    """Check if a command has special operators requiring approval.

    Args:
        command: The shell command string.
        checkers: Dict with is_normalized_cd_command and is_normalized_git_command.

    Returns:
        Dict with behavior, message, and optionally subcommand results.
    """
    # Split into pipe segments
    pipe_result = split_command_with_operators(command)
    segments: list[str] = []
    current = ""

    for part in pipe_result:
        if part == "|":
            if current.strip():
                segments.append(current.strip())
            current = ""
        else:
            current += " " + part if current else part

    if current.strip():
        segments.append(current.strip())

    # Single segment - passthrough
    if len(segments) <= 1:
        return {"behavior": "passthrough", "message": "No pipes found"}

    # Check for multiple cd commands
    cd_commands = [s for s in segments if checkers.get("is_normalized_cd_command", is_normalized_cd_command)(s.strip())]
    if len(cd_commands) > 1:
        return {
            "behavior": "ask",
            "message": "Multiple directory changes in one command require approval for clarity",
        }

    # Check for cd+git across pipe segments
    has_cd = False
    has_git = False
    for segment in segments:
        subcommands = split_command(segment)
        for sub in subcommands:
            trimmed = sub.strip()
            if checkers.get("is_normalized_cd_command", is_normalized_cd_command)(trimmed):
                has_cd = True
            if checkers.get("is_normalized_git_command", is_normalized_git_command)(trimmed):
                has_git = True
    if has_cd and has_git:
        return {
            "behavior": "ask",
            "message": "Compound commands with cd and git require approval to prevent bare repository attacks",
        }

    return {
        "behavior": "passthrough",
        "message": "Piped command processed",
    }


# =============================================================================
# Permission Rule Matching (bashPermissions.ts - simplified)
# =============================================================================

# Note: Full permission rule matching requires integration with the
# permission store and permission rules from the broader security system.
# The functions below provide the core bash-specific utilities.


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
    # * matches anything except space
    regex_pattern = re.escape(pattern)
    regex_pattern = regex_pattern.replace(r"\*", r"[^ ]*")
    regex_pattern = "^" + regex_pattern + "$"
    return bool(re.match(regex_pattern, command))
