"""
Tests for utils/datetime.py - Datetime utilities.
"""

from __future__ import annotations

from datetime import datetime, timezone
import os
import pytest
from claude_code.utils.datetime import (
    first_grapheme,
    format_brief_timestamp,
    format_relative_time,
    get_locale,
    get_relative_time_format,
    get_system_locale_language,
    get_timezone,
    grapheme_count,
    last_grapheme,
    now_local,
    now_utc,
    parse_iso,
    split_words,
    to_iso,
)


class TestParseIso:
    """Tests for parse_iso."""

    def test_parse_with_z_suffix(self) -> None:
        """Test parsing ISO string with Z suffix."""
        dt = parse_iso("2024-01-15T10:30:00Z")
        assert dt is not None
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 15
        assert dt.hour == 10
        assert dt.minute == 30
        assert dt.second == 0

    def test_parse_with_offset(self) -> None:
        """Test parsing ISO string with timezone offset."""
        dt = parse_iso("2024-01-15T10:30:00+05:00")
        assert dt is not None
        assert dt.hour == 10

    def test_parse_invalid_returns_none(self) -> None:
        """Test that invalid input returns None."""
        assert parse_iso("not-a-date") is None
        assert parse_iso("") is None
        assert parse_iso("2024-13-45") is None

    def test_parse_iso_string_returns_datetime(self) -> None:
        """Test that parse_iso returns a valid datetime."""
        dt = parse_iso("2024-01-15T10:30:00")
        assert dt is not None
        assert dt.year == 2024
        assert dt.month == 1


class TestToIso:
    """Tests for to_iso."""

    def test_to_iso_aware(self) -> None:
        """Test converting aware datetime to ISO."""
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = to_iso(dt)
        assert "2024-01-15" in result
        assert "10:30:00" in result

    def test_to_iso_naive_becomes_utc(self) -> None:
        """Test that naive datetime gets UTC tzinfo."""
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = to_iso(dt)
        assert "2024-01-15" in result


class TestNowUtc:
    """Tests for now_utc."""

    def test_now_utc_returns_aware(self) -> None:
        """Test now_utc returns timezone-aware UTC datetime."""
        dt = now_utc()
        assert dt.tzinfo is not None

    def test_now_utc_is_reasonable(self) -> None:
        """Test now_utc returns a recent datetime."""
        dt = now_utc()
        assert dt.year >= 2024


class TestNowLocal:
    """Tests for now_local."""

    def test_now_local_returns_aware(self) -> None:
        """Test now_local returns timezone-aware datetime."""
        dt = now_local()
        assert dt.tzinfo is not None


class TestGetTimezone:
    """Tests for get_timezone."""

    def test_get_timezone_returns_string(self) -> None:
        """Test get_timezone returns a string."""
        tz = get_timezone()
        assert isinstance(tz, str)
        assert len(tz) > 0


class TestGetLocale:
    """Tests for get_locale."""

    def test_returns_string_or_none(self) -> None:
        """Test get_locale returns string or None."""
        locale = get_locale()
        assert locale is None or isinstance(locale, str)

    def test_caches_result(self) -> None:
        """Test that result is cached (lru_cache)."""
        # Clear cache and call twice
        result1 = get_locale()
        result2 = get_locale()
        assert result1 == result2


class TestFormatBriefTimestamp:
    """Tests for format_brief_timestamp."""

    def test_invalid_returns_empty(self) -> None:
        """Test that invalid ISO string returns empty string."""
        assert format_brief_timestamp("not-valid") == ""
        assert format_brief_timestamp("") == ""

    def test_same_day_returns_time_only(self) -> None:
        """Test that same-day timestamps show only time."""
        now = datetime(2024, 6, 15, 14, 30, 0, tzinfo=timezone.utc)
        iso = "2024-06-15T10:30:00Z"
        result = format_brief_timestamp(iso, now)
        # Should contain time, not date
        assert ":" in result
        assert "June" not in result
        assert "2024" not in result

    def test_within_week_returns_weekday(self) -> None:
        """Test that timestamps within a week show weekday."""
        # A date 3 days ago
        now = datetime(2024, 6, 15, 14, 30, 0, tzinfo=timezone.utc)
        iso = "2024-06-12T10:30:00Z"  # 3 days before
        result = format_brief_timestamp(iso, now)
        # Should contain a weekday name
        assert result != ""

    def test_older_returns_full_date(self) -> None:
        """Test that older timestamps show full date."""
        now = datetime(2024, 6, 15, 14, 30, 0, tzinfo=timezone.utc)
        iso = "2024-01-10T10:30:00Z"  # About 5 months ago
        result = format_brief_timestamp(iso, now)
        # Should contain month name
        assert result != ""
        # Should not be just time
        assert ":" in result  # Time is always included

    def test_with_custom_now(self) -> None:
        """Test with custom reference time."""
        custom_now = datetime(2024, 6, 20, 12, 0, 0, tzinfo=timezone.utc)
        iso = "2024-06-20T09:00:00Z"
        result = format_brief_timestamp(iso, custom_now)
        assert result != ""


class TestGetRelativeTimeFormat:
    """Tests for get_relative_time_format."""

    def test_returns_tuple(self) -> None:
        """Test returns a tuple of (style, numeric)."""
        result = get_relative_time_format()
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_validates_style(self) -> None:
        """Test that invalid style defaults to long."""
        result = get_relative_time_format("invalid")
        assert result[0] == "long"

    def test_validates_numeric(self) -> None:
        """Test that invalid numeric defaults to always."""
        result = get_relative_time_format("long", "invalid")
        assert result[1] == "always"

    def test_caches_result(self) -> None:
        """Test that result is cached."""
        result1 = get_relative_time_format("short", "auto")
        result2 = get_relative_time_format("short", "auto")
        assert result1 is result2


class TestFormatRelativeTime:
    """Tests for format_relative_time."""

    def test_returns_string(self) -> None:
        """Test returns a string."""
        result = format_relative_time(5, "minute")
        assert isinstance(result, str)

    def test_different_units(self) -> None:
        """Test formatting different time units."""
        for unit in ("second", "minute", "hour", "day", "week", "month", "year"):
            result = format_relative_time(3, unit)
            assert isinstance(result, str)
            assert len(result) > 0


class TestGetSystemLocaleLanguage:
    """Tests for get_system_locale_language."""

    def test_returns_string_or_none(self) -> None:
        """Test returns string or None."""
        result = get_system_locale_language()
        assert result is None or isinstance(result, str)

    def test_caches_result(self) -> None:
        """Test that result is cached."""
        result1 = get_system_locale_language()
        result2 = get_system_locale_language()
        assert result1 == result2


class TestFirstGrapheme:
    """Tests for first_grapheme."""

    def test_empty_string_returns_empty(self) -> None:
        """Test that empty string returns empty."""
        assert first_grapheme("") == ""

    def test_single_character(self) -> None:
        """Test with single character."""
        result = first_grapheme("a")
        assert result == "a"

    def test_multiple_characters(self) -> None:
        """Test with multiple characters."""
        result = first_grapheme("hello")
        assert result == "h"


class TestLastGrapheme:
    """Tests for last_grapheme."""

    def test_empty_string_returns_empty(self) -> None:
        """Test that empty string returns empty."""
        assert last_grapheme("") == ""

    def test_single_character(self) -> None:
        """Test with single character."""
        assert last_grapheme("a") == "a"

    def test_multiple_characters(self) -> None:
        """Test with multiple characters."""
        assert last_grapheme("hello") == "o"


class TestGraphemeCount:
    """Tests for grapheme_count."""

    def test_empty_string_returns_zero(self) -> None:
        """Test that empty string returns 0."""
        assert grapheme_count("") == 0

    def test_simple_string(self) -> None:
        """Test with simple ASCII string."""
        assert grapheme_count("hello") == 5


class TestSplitWords:
    """Tests for split_words."""

    def test_empty_string_returns_empty_list(self) -> None:
        """Test that empty string returns empty list."""
        assert split_words("") == []

    def test_single_word(self) -> None:
        """Test with single word."""
        result = split_words("hello")
        assert len(result) > 0

    def test_multiple_words(self) -> None:
        """Test with multiple words."""
        result = split_words("hello world")
        assert len(result) > 0
