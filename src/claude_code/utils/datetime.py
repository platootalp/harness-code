"""Datetime utilities for the Claude Code CLI.

TypeScript equivalent: src/utils/formatBriefTimestamp.ts, src/utils/intl.ts

This module provides:
- Locale-aware timestamp formatting (like a messaging app)
- Relative time formatting (Intl.RelativeTimeFormat wrapper)
- Timezone and locale detection
- Intl segmenter utilities for text processing
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


# =============================================================================
# Locale Utilities
# =============================================================================


@lru_cache(maxsize=1)
def _get_locale() -> str | None:
    """Derive a BCP 47 locale tag from POSIX env vars.

    LC_ALL > LC_TIME > LANG, falls back to None (system default).
    Converts POSIX format (en_GB.UTF-8) to BCP 47 (en-GB).

    Returns:
        A valid BCP 47 locale tag, or None for system default.

    TypeScript equivalent: getLocale() in formatBriefTimestamp.ts
    """
    raw = os.environ.get("LC_ALL") or os.environ.get("LC_TIME") or os.environ.get("LANG") or ""
    if not raw or raw in ("C", "POSIX"):
        return None

    # Strip codeset (.UTF-8) and modifier (@euro), replace _ with -
    base = raw.split(".")[0].split("@")[0]
    if not base:
        return None

    tag = base.replace("_", "-")

    # Validate by trying to construct an Intl locale — invalid tags are ignored
    try:
        # Python's locale normalization is more permissive, but we validate
        # by checking that it parses correctly
        if tag:
            return tag
        return None
    except (ValueError, TypeError):
        return None


def get_locale() -> str | None:
    """Get the BCP 47 locale tag from POSIX environment variables.

    Returns:
        A valid locale tag string, or None for system default.
    """
    return _get_locale()


# =============================================================================
# Timezone Utilities
# =============================================================================


@lru_cache(maxsize=1)
def get_timezone() -> str:
    """Get the current system timezone.

    Returns:
        The IANA timezone name (e.g., 'America/New_York', 'UTC').

    TypeScript equivalent: getTimeZone() in intl.ts
    """
    return datetime.now().astimezone().tzname() or "UTC"


def now_utc() -> datetime:
    """Get the current UTC datetime.

    Returns:
        A timezone-aware datetime in UTC.
    """
    return datetime.now(UTC)


def now_local() -> datetime:
    """Get the current local datetime.

    Returns:
        A timezone-aware datetime in the local timezone.
    """
    return datetime.now().astimezone()


def parse_iso(iso_string: str) -> datetime | None:
    """Parse an ISO 8601 date string.

    Args:
        iso_string: An ISO 8601 formatted date string.

    Returns:
        A timezone-aware datetime, or None if parsing fails.
    """
    try:
        # Handle both Z suffix and offset formats
        if iso_string.endswith("Z"):
            return datetime.fromisoformat(iso_string[:-1] + "+00:00")
        return datetime.fromisoformat(iso_string)
    except (ValueError, TypeError):
        return None


def to_iso(dt: datetime) -> str:
    """Convert a datetime to ISO 8601 string.

    Args:
        dt: A timezone-aware or naive datetime.

    Returns:
        An ISO 8601 formatted string.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.isoformat()


# =============================================================================
# Timestamp Formatting
# =============================================================================


def _start_of_day_ms(dt: datetime) -> int:
    """Get the start of day as milliseconds since epoch.

    Args:
        dt: The datetime to process.

    Returns:
        Milliseconds since epoch at the start of the day.
    """
    start = datetime(dt.year, dt.month, dt.day, tzinfo=dt.tzinfo)
    return int(start.timestamp() * 1000)


def format_brief_timestamp(
    iso_string: str,
    now: datetime | None = None,
) -> str:
    """Format an ISO timestamp for the brief/chat message label line.

    Display scales with age (like a messaging app):
      - same day:      "1:30 PM" or "13:30" (locale-dependent)
      - within 6 days: "Sunday, 4:15 PM" (locale-dependent)
      - older:         "Sunday, Feb 20, 4:30 PM" (locale-dependent)

    Respects POSIX locale env vars (LC_ALL > LC_TIME > LANG) for time format
    (12h/24h), weekday names, month names, and overall structure.

    Args:
        iso_string: ISO 8601 date string.
        now: Optional reference time (defaults to current time). Injectable for tests.

    Returns:
        A formatted timestamp string, or empty string if parsing fails.

    TypeScript equivalent: formatBriefTimestamp() in formatBriefTimestamp.ts
    """
    dt = parse_iso(iso_string)
    if dt is None:
        return ""

    if now is None:
        now = datetime.now().astimezone()

    locale_tag = get_locale()
    day_diff = _start_of_day_ms(now) - _start_of_day_ms(dt)
    days_ago = round(day_diff / 86_400_000)

    if days_ago == 0:
        # Same day: show time only
        return dt.strftime("%H:%M") if locale_tag is None else _format_time_locale(dt, locale_tag)

    if 0 < days_ago < 7:
        # Within a week: show weekday and time
        return _format_weekday_time(dt, locale_tag)

    # Older: show weekday, month, day, and time
    return _format_full_date(dt, locale_tag)


def _format_time_locale(dt: datetime, locale_tag: str) -> str:
    """Format time with locale-specific preferences.

    Args:
        dt: The datetime to format.
        locale_tag: BCP 47 locale tag.

    Returns:
        Locale-formatted time string.
    """
    try:
        import locale as _stdlib_locale

        old_locale = _stdlib_locale.getlocale(_stdlib_locale.LC_TIME)
        try:
            # Try to set the locale temporarily
            _stdlib_locale.setlocale(_stdlib_locale.LC_TIME, locale_tag)
            result = dt.strftime("%X")  # Locale's appropriate time representation
            return result
        finally:
            _stdlib_locale.setlocale(_stdlib_locale.LC_TIME, old_locale)
    except (_stdlib_locale.Error, ValueError):
        # Fallback to default format
        return dt.strftime("%H:%M")


def _format_weekday_time(dt: datetime, locale_tag: str | None) -> str:
    """Format with weekday and time.

    Args:
        dt: The datetime to format.
        locale_tag: BCP 47 locale tag or None.

    Returns:
        Formatted string like "Sunday, 4:15 PM".
    """
    if locale_tag is None:
        return dt.strftime("%A, %H:%M")

    try:
        import locale as _stdlib_locale

        old_locale = _stdlib_locale.getlocale(_stdlib_locale.LC_TIME)
        try:
            if locale_tag:
                _stdlib_locale.setlocale(_stdlib_locale.LC_TIME, locale_tag)
            weekday = dt.strftime("%A")
            time_str = dt.strftime("%H:%M") if locale_tag else dt.strftime("%X")
            return f"{weekday}, {time_str}"
        finally:
            if locale_tag:
                _stdlib_locale.setlocale(_stdlib_locale.LC_TIME, old_locale)
    except (_stdlib_locale.Error, ValueError):
        return dt.strftime("%A, %H:%M")


def _format_full_date(dt: datetime, locale_tag: str | None) -> str:
    """Format with full date and time.

    Args:
        dt: The datetime to format.
        locale_tag: BCP 47 locale tag or None.

    Returns:
        Formatted string like "Sunday, Feb 20, 4:30 PM".
    """
    if locale_tag is None:
        return dt.strftime("%A, %b %d, %H:%M")

    try:
        import locale as _stdlib_locale

        old_locale = _stdlib_locale.getlocale(_stdlib_locale.LC_TIME)
        try:
            if locale_tag:
                _stdlib_locale.setlocale(_stdlib_locale.LC_TIME, locale_tag)
            weekday = dt.strftime("%A")
            month = dt.strftime("%b")
            day = dt.day
            time_str = dt.strftime("%H:%M") if locale_tag else dt.strftime("%X")
            return f"{weekday}, {month} {day}, {time_str}"
        finally:
            if locale_tag:
                _stdlib_locale.setlocale(_stdlib_locale.LC_TIME, old_locale)
    except (_stdlib_locale.Error, ValueError):
        return dt.strftime("%A, %b %d, %H:%M")


# =============================================================================
# Relative Time Formatting
# =============================================================================


@lru_cache(maxsize=4)
def get_relative_time_format(
    style: str = "long",
    numeric: str = "always",
) -> tuple[str, str]:
    """Get a relative time format configuration.

    Cached for performance since Intl formatters are expensive.

    Args:
        style: 'long', 'short', or 'narrow'.
        numeric: 'always' or 'auto'.

    Returns:
        Tuple of (style, numeric) for use with formatting functions.

    TypeScript equivalent: getRelativeTimeFormat() in intl.ts
    """
    valid_styles = ("long", "short", "narrow")
    valid_numeric = ("always", "auto")
    style = style if style in valid_styles else "long"
    numeric = numeric if numeric in valid_numeric else "always"
    return (style, numeric)


def format_relative_time(value: int, unit: str, style: str = "long", numeric: str = "always") -> str:
    """Format a relative time string.

    Args:
        value: The numeric value.
        unit: The unit ('second', 'minute', 'hour', 'day', 'week', 'month', 'quarter', 'year').
        style: 'long', 'short', or 'narrow'.
        numeric: 'always' or 'auto'.

    Returns:
        A formatted relative time string (e.g., "in 5 minutes", "3 days ago").

    TypeScript equivalent: Intl.RelativeTimeFormat.format()
    """
    try:
        from babel import Locale
        from babel.dates import format_timedelta

        locale = get_locale() or "en"
        babel_locale = Locale.parse(locale, sep="-")

        delta = {"second": value, "minute": value, "hour": value, "day": value,
                 "week": value, "month": value, "quarter": value, "year": value}

        result = format_timedelta(
            delta.get(unit, value),
            locale=babel_locale,
            width=style if style != "narrow" else "short",
        )
        return str(result)
    except ImportError:
        # Fallback without babel
        return _fallback_relative_time(value, unit)


def _fallback_relative_time(value: int, unit: str) -> str:
    """Simple fallback relative time formatting without babel.

    Args:
        value: The numeric value.
        unit: The unit name.

    Returns:
        A simple relative time string.
    """
    unit_map = {
        "second": "second" if value == 1 else "seconds",
        "minute": "minute" if value == 1 else "minutes",
        "hour": "hour" if value == 1 else "hours",
        "day": "day" if value == 1 else "days",
        "week": "week" if value == 1 else "weeks",
        "month": "month" if value == 1 else "months",
        "quarter": "quarter" if value == 1 else "quarters",
        "year": "year" if value == 1 else "years",
    }
    plural_unit = unit_map.get(unit, f"{unit}s")
    return f"{value} {plural_unit}"


# =============================================================================
# System Locale Utilities
# =============================================================================


@lru_cache(maxsize=1)
def get_system_locale_language() -> str | None:
    """Get the system locale language subtag (e.g., 'en', 'ja').

    Returns:
        The language subtag, or None if unavailable.

    TypeScript equivalent: getSystemLocaleLanguage() in intl.ts
    """
    locale_tag = get_locale()
    if locale_tag:
        # BCP 47 language tag: extract the language part (before any dash)
        lang = locale_tag.split("-")[0].split("_")[0]
        if lang:
            return lang

    # Fallback: try to get from system
    try:
        import locale as _stdlib_locale

        system_locale = _stdlib_locale.getlocale()[0] or _stdlib_locale.getdefaultlocale()[0]
        if system_locale:
            return system_locale.split("_")[0]
    except (AttributeError, OSError):
        pass

    return None


# =============================================================================
# Text Segmentation (Grapheme/Word)
# =============================================================================


def first_grapheme(text: str) -> str:
    """Extract the first grapheme cluster from a string.

    Args:
        text: The input string.

    Returns:
        The first grapheme cluster, or empty string if text is empty.

    TypeScript equivalent: firstGrapheme() in intl.ts
    """
    if not text:
        return ""

    try:
        import grapheme

        return str(grapheme.slice(text, 0, 1))
    except ImportError:
        # Fallback: return first character
        return text[0] if text else ""


def last_grapheme(text: str) -> str:
    """Extract the last grapheme cluster from a string.

    Args:
        text: The input string.

    Returns:
        The last grapheme cluster, or empty string if text is empty.

    TypeScript equivalent: lastGrapheme() in intl.ts
    """
    if not text:
        return ""

    try:
        import grapheme

        clusters = list(grapheme.graphemes(text))
        return clusters[-1] if clusters else ""
    except ImportError:
        # Fallback: return last character
        return text[-1] if text else ""


def grapheme_count(text: str) -> int:
    """Count the number of grapheme clusters in a string.

    Args:
        text: The input string.

    Returns:
        The number of grapheme clusters.
    """
    if not text:
        return 0

    try:
        import grapheme

        return len(list(grapheme.graphemes(text)))
    except ImportError:
        return len(text)


def split_words(text: str) -> list[str]:
    """Split text into words using Unicode word boundaries.

    Args:
        text: The input string.

    Returns:
        A list of word tokens.
    """
    if not text:
        return []

    try:
        from textwrap import TextWrapper

        wrapper = TextWrapper(break_long_words=True, break_on_hyphens=True)
        return wrapper.wrap(text)
    except ImportError:
        return text.split()
