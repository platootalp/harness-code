"""
Tests for skills/parser.py - SKILL.md parsing utilities.
"""

from __future__ import annotations

import pytest

from src.claude_code.skills.parser import (
    extract_tool_names,
    normalize_paths_for_matching,
    parse_allowed_tools,
    parse_argument_names,
    parse_boolean_frontmatter,
    parse_effort_value,
    parse_frontmatter,
    parse_frontmatter_with_schema,
    split_path_in_frontmatter,
)


class TestParseFrontmatter:
    """Tests for parse_frontmatter function."""

    def test_no_frontmatter(self) -> None:
        """parse_frontmatter returns empty dict for plain markdown."""
        content = "# Just markdown\nSome text."
        fm, body = parse_frontmatter(content)
        assert fm == {}
        assert body == content

    def test_with_frontmatter(self) -> None:
        """parse_frontmatter parses YAML frontmatter correctly."""
        content = """---
name: test
description: A test skill
allowed-tools:
  - Read
  - Glob
---
# Skill Content
This is the skill."""
        fm, body = parse_frontmatter(content)
        assert fm["name"] == "test"
        assert fm["description"] == "A test skill"
        assert fm["allowed-tools"] == ["Read", "Glob"]
        assert "Skill Content" in body

    def test_frontmatter_only(self) -> None:
        """parse_frontmatter handles frontmatter with no body."""
        content = """---
name: test
---
"""
        fm, body = parse_frontmatter(content)
        assert fm["name"] == "test"
        assert body == ""

    def test_empty_frontmatter(self) -> None:
        """parse_frontmatter returns full content when frontmatter is empty."""
        # When --- is immediately followed by --- with no newline between,
        # the regex doesn't match (it expects newline after opening ---).
        # The whole content is returned as body.
        content = """---
---
Content"""
        fm, body = parse_frontmatter(content)
        assert fm == {}
        assert body == content

    def test_empty_frontmatter_with_newline(self) -> None:
        """parse_frontmatter parses empty YAML when properly formatted."""
        # The regex requires a blank line after opening --- for empty frontmatter
        content = "---\n\n---\n\nContent"
        fm, body = parse_frontmatter(content)
        assert fm == {}
        assert body == "Content"

    def test_invalid_yaml(self) -> None:
        """parse_frontmatter handles invalid YAML gracefully."""
        content = """---
name: test
  invalid: [unclosed
---
Content"""
        fm, body = parse_frontmatter(content)
        # Should return empty dict on YAML parse error
        assert body == content

    def test_frontmatter_boolean_parsing(self) -> None:
        """parse_frontmatter parses YAML booleans."""
        content = """---
user-invocable: false
disable-model-invocation: true
---
Content"""
        fm, _ = parse_frontmatter(content)
        assert fm["user-invocable"] is False
        assert fm["disable-model-invocation"] is True

    def test_frontmatter_multiline_string(self) -> None:
        """parse_frontmatter handles multiline strings."""
        content = """---
description: |
  This is a multiline
  description.
---
Content"""
        fm, _ = parse_frontmatter(content)
        assert "multiline" in fm["description"]


class TestParseFrontmatterWithSchema:
    """Tests for parse_frontmatter_with_schema function."""

    def test_with_frontmatter(self) -> None:
        """parse_frontmatter_with_schema returns has_frontmatter=True."""
        content = "---\nname: test\n---\nContent"
        fm, body, has_fm = parse_frontmatter_with_schema(content)
        assert has_fm is True
        assert fm["name"] == "test"

    def test_without_frontmatter(self) -> None:
        """parse_frontmatter_with_schema returns has_frontmatter=False."""
        content = "# Plain markdown"
        fm, body, has_fm = parse_frontmatter_with_schema(content)
        assert has_fm is False
        assert fm == {}

    def test_empty_frontmatter_block(self) -> None:
        """parse_frontmatter_with_schema handles empty frontmatter block."""
        content = "---\n---\nContent"
        fm, body, has_fm = parse_frontmatter_with_schema(content)
        assert has_fm is False


class TestParseAllowedTools:
    """Tests for parse_allowed_tools function."""

    def test_none_input(self) -> None:
        """parse_allowed_tools handles None input."""
        assert parse_allowed_tools(None) == []

    def test_empty_string(self) -> None:
        """parse_allowed_tools handles empty string."""
        assert parse_allowed_tools("") == []

    def test_single_tool_string(self) -> None:
        """parse_allowed_tools parses space-separated tools."""
        assert parse_allowed_tools("Read") == ["Read"]

    def test_multiple_tools_string(self) -> None:
        """parse_allowed_tools parses multiple tools."""
        result = parse_allowed_tools("Read Glob Bash")
        assert result == ["Read", "Glob", "Bash"]

    def test_tool_with_args(self) -> None:
        """parse_allowed_tools parses tool with arguments."""
        result = parse_allowed_tools("Bash(git:*)")
        assert result == ["Bash(git:*)"]

    def test_mixed_tools(self) -> None:
        """parse_allowed_tools parses mixed tool formats."""
        result = parse_allowed_tools("Read Bash(git:*) Glob")
        assert result == ["Read", "Bash(git:*)", "Glob"]

    def test_list_input(self) -> None:
        """parse_allowed_tools handles list input."""
        result = parse_allowed_tools(["Read", "Glob", "Bash(git:*)"])
        assert result == ["Read", "Glob", "Bash(git:*)"]

    def test_list_with_whitespace(self) -> None:
        """parse_allowed_tools trims whitespace in list."""
        result = parse_allowed_tools(["  Read  ", "Glob"])
        assert result == ["Read", "Glob"]

    def test_filters_empty(self) -> None:
        """parse_allowed_tools filters empty strings."""
        result = parse_allowed_tools(["Read", "", "  ", "Glob"])
        assert result == ["Read", "Glob"]

    def test_complex_args(self) -> None:
        """parse_allowed_tools handles complex argument patterns."""
        result = parse_allowed_tools("Bash(git commit -m *)")
        assert result == ["Bash(git commit -m *)"]


class TestExtractToolNames:
    """Tests for extract_tool_names function."""

    def test_simple_tools(self) -> None:
        """extract_tool_names extracts names from simple tools."""
        result = extract_tool_names(["Read", "Glob", "Bash"])
        assert result == {"Read", "Glob", "Bash"}

    def test_tools_with_args(self) -> None:
        """extract_tool_names deduplicates by name."""
        result = extract_tool_names(["Read", "Bash(git:*)", "Bash(npm:*)", "Glob"])
        assert result == {"Read", "Bash", "Glob"}

    def test_empty_list(self) -> None:
        """extract_tool_names handles empty list."""
        assert extract_tool_names([]) == set()


class TestParseArgumentNames:
    """Tests for parse_argument_names function."""

    def test_none_input(self) -> None:
        """parse_argument_names handles None."""
        assert parse_argument_names(None) == []

    def test_empty_string(self) -> None:
        """parse_argument_names handles empty string."""
        assert parse_argument_names("") == []

    def test_space_separated_string(self) -> None:
        """parse_argument_names parses space-separated args."""
        result = parse_argument_names("topic format")
        assert result == ["topic", "format"]

    def test_list_input(self) -> None:
        """parse_argument_names handles list input."""
        result = parse_argument_names(["topic", "format"])
        assert result == ["topic", "format"]

    def test_filters_empty(self) -> None:
        """parse_argument_names filters empty strings."""
        result = parse_argument_names(["topic", "", "  ", "format"])
        assert result == ["topic", "format"]

    def test_trims_whitespace(self) -> None:
        """parse_argument_names trims whitespace."""
        result = parse_argument_names("  topic  format  ")
        assert result == ["topic", "format"]


class TestParseBooleanFrontmatter:
    """Tests for parse_boolean_frontmatter function."""

    def test_true_bool(self) -> None:
        """parse_boolean_frontmatter handles True."""
        assert parse_boolean_frontmatter(True) is True

    def test_false_bool(self) -> None:
        """parse_boolean_frontmatter handles False."""
        assert parse_boolean_frontmatter(False) is False

    def test_string_true_values(self) -> None:
        """parse_boolean_frontmatter handles truthy strings."""
        # Only "true" matches TypeScript behavior
        assert parse_boolean_frontmatter("true") is True

    def test_string_false_values(self) -> None:
        """parse_boolean_frontmatter handles falsy strings."""
        assert parse_boolean_frontmatter("false") is False
        assert parse_boolean_frontmatter("no") is False
        assert parse_boolean_frontmatter("off") is False
        assert parse_boolean_frontmatter("0") is False

    def test_none_value(self) -> None:
        """parse_boolean_frontmatter handles None."""
        assert parse_boolean_frontmatter(None) is False

    def test_other_truthy(self) -> None:
        """parse_boolean_frontmatter only returns True for true/'true'."""
        # Matches TypeScript: only value === true || value === 'true'
        assert parse_boolean_frontmatter("anything") is False


class TestParseEffortValue:
    """Tests for parse_effort_value function."""

    def test_valid_levels(self) -> None:
        """parse_effort_value accepts valid effort levels."""
        assert parse_effort_value("minimal") == "minimal"
        assert parse_effort_value("low") == "low"
        assert parse_effort_value("medium") == "medium"
        assert parse_effort_value("high") == "high"
        assert parse_effort_value("maximum") == "maximum"

    def test_numeric_mapping(self) -> None:
        """parse_effort_value maps numeric levels."""
        assert parse_effort_value("1") == "minimal"
        assert parse_effort_value("2") == "low"
        assert parse_effort_value("3") == "medium"
        assert parse_effort_value("4") == "high"
        assert parse_effort_value("5") == "maximum"

    def test_invalid_numeric(self) -> None:
        """parse_effort_value rejects invalid numeric levels."""
        assert parse_effort_value("0") is None
        assert parse_effort_value("6") is None
        assert parse_effort_value("-1") is None

    def test_invalid_string(self) -> None:
        """parse_effort_value rejects invalid strings."""
        assert parse_effort_value("invalid") is None
        assert parse_effort_value("extreme") is None

    def test_none(self) -> None:
        """parse_effort_value handles None."""
        assert parse_effort_value(None) is None

    def test_case_insensitive(self) -> None:
        """parse_effort_value is case insensitive."""
        assert parse_effort_value("HIGH") == "high"
        assert parse_effort_value("Medium") == "medium"


class TestSplitPathInFrontmatter:
    """Tests for split_path_in_frontmatter function."""

    def test_none_input(self) -> None:
        """split_path_in_frontmatter handles None."""
        assert split_path_in_frontmatter(None) == []

    def test_space_separated_string(self) -> None:
        """split_path_in_frontmatter parses space-separated paths."""
        result = split_path_in_frontmatter("**/*.py **/*.ts")
        assert result == ["**/*.py", "**/*.ts"]

    def test_list_input(self) -> None:
        """split_path_in_frontmatter handles list input."""
        result = split_path_in_frontmatter(["**/*.py", "**/*.ts"])
        assert result == ["**/*.py", "**/*.ts"]

    def test_list_with_spaces(self) -> None:
        """split_path_in_frontmatter splits items with spaces."""
        result = split_path_in_frontmatter(["**/*.py **/*.ts", "*.md"])
        assert result == ["**/*.py", "**/*.ts", "*.md"]


class TestNormalizePathsForMatching:
    """Tests for normalize_paths_for_matching function."""

    def test_removes_trailing_double_star(self) -> None:
        """normalize_paths_for_matching removes trailing /**."""
        result = normalize_paths_for_matching(["src/**", "lib/**"])
        assert result == ["src", "lib"]

    def test_preserves_other_patterns(self) -> None:
        """normalize_paths_for_matching preserves non-trailing patterns."""
        result = normalize_paths_for_matching(["**/*.py", "src/**/*.ts"])
        assert result == ["**/*.py", "src/**/*.ts"]

    def test_empty_list(self) -> None:
        """normalize_paths_for_matching handles empty list."""
        assert normalize_paths_for_matching([]) == []
