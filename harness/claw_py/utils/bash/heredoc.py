"""Heredoc extraction and restoration utilities."""
from __future__ import annotations

import re
from dataclasses import dataclass
from random import getrandbits
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

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
        r"(?<!<)<<(?!<)(-)?[ \t]*(?:(['\"])(\\?\w+)\2|\\?(\w+))",
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
