"""Command parsing utilities - splitting, placeholders, redirections."""
from __future__ import annotations

import re
from random import getrandbits
from typing import TYPE_CHECKING, Any

from .heredoc import (
    extract_heredocs,
    restore_heredocs,
)
from .shell_quote import (
    ParseEntry,
    try_parse_shell_command,
    try_quote_shell_args,
)

if TYPE_CHECKING:
    pass

# =============================================================================
# Constants
# =============================================================================

# File descriptor numbers
ALLOWED_FILE_DESCRIPTORS = frozenset(["0", "1", "2"])

# Control operators for splitting
COMMAND_LIST_SEPARATORS = frozenset(["&&", "||", ";", ";;", "|"])
ALL_SUPPORTED_CONTROL_OPERATORS = frozenset([*COMMAND_LIST_SEPARATORS, ">&", ">", ">>"])


# =============================================================================
# Placeholders
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


def _escape_for_parse(text: str, placeholders: dict[str, str]) -> str:
    """Escape quotes, newlines, and escaped parens for shell-quote parsing."""
    result = text
    result = result.replace('"', f'"{placeholders["DOUBLE_QUOTE"]}')
    result = result.replace("'", f"'{placeholders['SINGLE_QUOTE']}")
    result = result.replace("\n", f"\n{placeholders['NEW_LINE']}\n")
    result = result.replace("\\(", placeholders["ESCAPED_OPEN_PAREN"])
    result = result.replace("\\)", placeholders["ESCAPED_CLOSE_PAREN"])
    return result


# =============================================================================
# Line Continuation
# =============================================================================


def _join_line_continuations_simple(command: str) -> str:
    """Simple version using regex for cleaner code."""
    def replacer(match: re.Match[str]) -> str:
        backslash_count = len(match.group(0)) - 1  # -1 for the newline
        if backslash_count % 2 == 1:
            return "\\" * (backslash_count - 1)
        return str(match.group(0))

    return re.sub(r"\\+\n", replacer, command)


# =============================================================================
# Helpers
# =============================================================================


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


# =============================================================================
# Command Splitting
# =============================================================================


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
        if part in (">", ">>", ">&"):
            prev_part = result_parts[i - 1] if i > 0 else None
            next_part = result_parts[i + 1] if i + 1 < len(result_parts) else None
            after_next = result_parts[i + 2] if i + 2 < len(result_parts) else None

            if next_part is None:
                continue

            # Determine effective next part (handle merged FD like /dev/null 2)
            effective_next = next_part
            if (
                part in (">", ">>")
                and next_part
                and len(next_part) >= 3
                and next_part[-2] == " "
                and next_part[-1] in ALLOWED_FILE_DESCRIPTORS
                and after_next in (">", ">>", ">&")
            ):
                effective_next = next_part[:-2]

            should_strip = False
            strip_third = False

            if part == ">&" and next_part in ALLOWED_FILE_DESCRIPTORS:
                should_strip = True
            elif (
                part == ">"
                and next_part == "&"
                and after_next is not None
                and after_next in ALLOWED_FILE_DESCRIPTORS
            ):
                should_strip = True
                strip_third = True
            elif (
                part == ">"
                and isinstance(next_part, str)
                and next_part.startswith("&")
                and len(next_part) > 1
                and next_part[1:] in ALLOWED_FILE_DESCRIPTORS
            ) or part in (">", ">>") and is_static_redirect_target(effective_next or ""):
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


# =============================================================================
# Redirection Extraction
# =============================================================================


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
                    _is_operator(next_entry, ">")
                    or _is_operator(next_entry, ">>")
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
