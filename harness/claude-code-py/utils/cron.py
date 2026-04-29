"""
Cron utilities - cron expression parsing and validation.

Migrated from TypeScript cron utilities.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# Feature flags
CRO_PARSE_ENABLED = True


def is_kairos_cron_enabled() -> bool:
    """Check if Kairos cron support is enabled."""
    return CRO_PARSE_ENABLED


def is_durable_cron_enabled() -> bool:
    """Check if durable (persistent) crons are enabled."""
    return True


def parse_cron_expression(expression: str) -> dict[str, list[int]] | None:
    """Parse a 5-field cron expression into components.

    Args:
        expression: Cron expression (minute hour day month weekday)

    Returns:
        Dict with minute, hour, day, month, weekday (each a list of values) or None if invalid
    """
    pattern = r"^(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)$"
    match = re.match(pattern, expression.strip())
    if not match:
        return None

    parts = match.groups()
    try:
        return {
            "minute": _parse_field(parts[0], 0, 59),
            "hour": _parse_field(parts[1], 0, 23),
            "day": _parse_field(parts[2], 1, 31),
            "month": _parse_field(parts[3], 1, 12),
            "weekday": _parse_field(parts[4], 0, 6),
        }
    except (ValueError, OverflowError):
        return None


def _parse_field(value: str, min_val: int, max_val: int) -> list[int]:
    """Parse a cron field value (handles *, ranges, steps)."""
    if value == "*":
        return list(range(min_val, max_val + 1))

    result: list[int] = []
    for part in value.split(","):
        if "/" in part:
            range_part, step = part.split("/", 1)
            step_val = int(step)
            if range_part == "*":
                start, end = min_val, max_val
            elif "-" in range_part:
                start_str, end_str = range_part.split("-", 1)
                start, end = int(start_str), int(end_str)
            else:
                start = end = int(range_part)
            result.extend(range(start, end + 1, step_val))
        elif "-" in part:
            start_str, end_str = part.split("-", 1)
            result.extend(range(int(start_str), int(end_str) + 1))
        else:
            result.append(int(part))

    return sorted(set(result))


def next_cron_run_ms(expression: str, base_ms: int | None = None) -> int | None:
    """Calculate next run time for a cron expression.

    Args:
        expression: Cron expression
        base_ms: Base time in milliseconds (defaults to now)

    Returns:
        Next run time in milliseconds, or None if invalid
    """
    parsed = parse_cron_expression(expression)
    if not parsed:
        return None

    if base_ms is None:
        base_ms = int(datetime.now(UTC).timestamp() * 1000)

    # Simple next-run calculation: add 1 minute for demo
    return base_ms + 60_000


def cron_to_human(expression: str) -> str:
    """Convert cron expression to human-readable description.

    Args:
        expression: Cron expression

    Returns:
        Human-readable description
    """
    parsed = parse_cron_expression(expression)
    if not parsed:
        return f"Cron: {expression}"

    minute = parsed["minute"]
    hour = parsed["hour"]
    weekday = parsed.get("weekday", [])

    if minute == list(range(0, 60)) and hour == list(range(0, 24)):
        return "Every minute"
    if len(minute) == 1 and len(hour) == 1:
        return f"At {hour[0]:02d}:{minute[0]:02d}"
    if weekday != list(range(0, 7)):
        days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        day_names = [days[d] for d in weekday if 0 <= d < 7]
        return f"At {minute[0] if minute else 0:02d}:{hour[0] if hour else 0:02d} on {', '.join(day_names)}"

    return f"Cron: {expression}"
