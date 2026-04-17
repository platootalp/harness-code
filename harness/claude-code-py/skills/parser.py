"""SKILL.md parsing utilities.

Corresponds to TypeScript's parseFrontmatter and related functions
in src/utils/frontmatterParser.ts and src/skills/loadSkillsDir.ts.
"""

from __future__ import annotations

import re
from typing import Any

import yaml

# =============================================================================
# Frontmatter Regex
# =============================================================================

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?", re.DOTALL)


# =============================================================================
# Parse Frontmatter
# =============================================================================


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter from SKILL.md content.

    Args:
        content: Raw SKILL.md content with optional frontmatter.

    Returns:
        Tuple of (frontmatter_dict, markdown_body).

    Example:
        >>> content = '''
        ... ---
        ... name: test
        ... allowed-tools:
        ...   - Read
        ...   - Glob
        ... ---
        ... # Skill content
        ... '''
        >>> fm, body = parse_frontmatter(content)
        >>> fm['name']
        'test'
        >>> 'Skill content' in body
        True
    """
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return {}, content

    fm_text = match.group(1)
    try:
        frontmatter: dict[str, Any] = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        return {}, content

    markdown_body = content[match.end():]
    if markdown_body.startswith("\n"):
        markdown_body = markdown_body[1:]
    return frontmatter, markdown_body


def parse_frontmatter_with_schema(
    content: str,
) -> tuple[dict[str, Any], str, bool]:
    """Parse frontmatter and validate basic structure.

    Args:
        content: Raw SKILL.md content.

    Returns:
        Tuple of (frontmatter_dict, markdown_body, has_frontmatter).
    """
    fm, body = parse_frontmatter(content)
    return fm, body, bool(fm)


# =============================================================================
# Parse Allowed Tools
# =============================================================================


_TOOL_PATTERN_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)(?:\(([^)]*)\))?")


def parse_allowed_tools(raw: str | list[str] | None) -> list[str]:
    """Parse allowed-tools field into list of tool patterns.

    Supports both string and list input formats.

    Args:
        raw: Space-separated string or list of tool patterns.
            Examples: "Read Glob Bash(git:*)", ["Read", "Glob", "Bash(git:*)"]

    Returns:
        List of tool pattern strings.

    Example:
        >>> parse_allowed_tools("Read Glob Bash(git:*)")
        ['Read', 'Glob', 'Bash(git:*)']
        >>> parse_allowed_tools(["Read", "Glob"])
        ['Read', 'Glob']
    """
    if not raw:
        return []

    if isinstance(raw, list):
        return [str(t).strip() for t in raw if str(t).strip()]

    tools = []
    for match in _TOOL_PATTERN_RE.finditer(raw.strip()):
        tool_name = match.group(1)
        tool_args = match.group(2)
        if tool_args is not None:
            tools.append(f"{tool_name}({tool_args})")
        else:
            tools.append(tool_name)
    return tools


def extract_tool_names(tools: list[str]) -> set[str]:
    """Extract unique tool names from tool patterns.

    Args:
        tools: List of tool patterns (with optional args).

    Returns:
        Set of unique tool names.

    Example:
        >>> extract_tool_names(["Read", "Bash(git:*)", "Bash(npm:*)"])
        {'Read', 'Bash'}
    """
    names: set[str] = set()
    for tool in tools:
        name = tool.rsplit("(", 1)[0] if "(" in tool and tool.endswith(")") else tool
        names.add(name)
    return names


# =============================================================================
# Parse Arguments
# =============================================================================


def parse_argument_names(raw: str | list[str] | None) -> list[str]:
    """Parse arguments field into list of argument names.

    Args:
        raw: Space-separated string or list of argument names.

    Returns:
        List of argument name strings.

    Example:
        >>> parse_argument_names(["topic", "format"])
        ['topic', 'format']
        >>> parse_argument_names("topic format")
        ['topic', 'format']
    """
    if not raw:
        return []

    if isinstance(raw, list):
        return [str(a).strip() for a in raw if str(a).strip()]

    return [a.strip() for a in raw.split() if a.strip()]


# =============================================================================
# Parse Boolean Frontmatter
# =============================================================================


def parse_boolean_frontmatter(value: Any) -> bool:
    """Parse a boolean value from frontmatter.

    Only returns True for literal True or "true" string.
    Matches TypeScript's parseBooleanFrontmatter behavior.

    Args:
        value: Raw value from frontmatter.

    Returns:
        Parsed boolean value.

    Example:
        >>> parse_boolean_frontmatter(True)
        True
        >>> parse_boolean_frontmatter("true")
        True
        >>> parse_boolean_frontmatter("yes")
        False
        >>> parse_boolean_frontmatter("false")
        False
    """
    return value is True or value == "true"


# =============================================================================
# Parse Effort Value
# =============================================================================


_VALID_EFFORT_LEVELS = ("minimal", "low", "medium", "high", "maximum")


def parse_effort_value(raw: str | None) -> str | None:
    """Parse and validate effort value.

    Args:
        raw: Raw effort value string.

    Returns:
        Validated effort value or None if invalid.

    Example:
        >>> parse_effort_value("high")
        'high'
        >>> parse_effort_value("5")
        'high'
        >>> parse_effort_value("invalid") is None
        True
    """
    if not raw:
        return None

    raw_str = str(raw).lower().strip()

    if raw_str in _VALID_EFFORT_LEVELS:
        return raw_str

    # Try numeric mapping
    try:
        level = int(raw_str)
        if 1 <= level <= 5:
            return _VALID_EFFORT_LEVELS[level - 1]
    except ValueError:
        pass

    return None


# =============================================================================
# Path Pattern Utilities
# =============================================================================


def split_path_in_frontmatter(paths: str | list[str]) -> list[str]:
    """Split paths field into list of patterns.

    Args:
        paths: Space-separated string or list of path patterns.

    Returns:
        List of path pattern strings.

    Example:
        >>> split_path_in_frontmatter("**/*.py **/*.ts")
        ['**/*.py', '**/*.ts']
        >>> split_path_in_frontmatter(["**/*.py", "**/*.ts"])
        ['**/*.py', '**/*.ts']
    """
    if not paths:
        return []

    if isinstance(paths, list):
        result = []
        for p in paths:
            result.extend(str(p).split())
        return result

    return paths.split()


def normalize_paths_for_matching(patterns: list[str]) -> list[str]:
    """Normalize path patterns for matching.

    Removes trailing /** suffix since the library treats 'path' as
    matching both the path itself and everything inside it.

    Args:
        patterns: List of glob patterns.

    Returns:
        Normalized patterns with trailing /** removed.

    Example:
        >>> normalize_paths_for_matching(["src/**", "lib/**"])
        ['src', 'lib']
    """
    return [p[:-3] if p.endswith("/**") else p for p in patterns]
