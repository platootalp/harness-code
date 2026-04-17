"""Skill definition types and data structures.

Corresponds to TypeScript's BundledSkillDefinition and related types
in src/skills/types.ts and src/types/command.ts.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..models.message import ContentBlock


# =============================================================================
# Skill Source
# =============================================================================


class SkillSource(str, Enum):  # noqa: UP042
    """Skill loading source/location."""

    BUNDLED = "bundled"  # Compiled into CLI
    MANAGED = "managed"  # Enterprise-managed skills
    SKILLS = "skills"  # ~/.claude/skills/
    PROJECT = "project"  # .claude/skills/
    PLUGIN = "plugin"  # Bundled with plugins
    MCP = "mcp"  # From MCP servers


# =============================================================================
# Skill Parameter
# =============================================================================


@dataclass
class SkillParameter:
    """A named parameter for a skill."""

    name: str
    type: str = "string"  # string, number, boolean
    description: str = ""
    required: bool = False


# =============================================================================
# Skill Frontmatter
# =============================================================================


@dataclass
class SkillFrontmatter:
    """Parsed frontmatter fields from SKILL.md."""

    name: str | None = None
    description: str | None = None
    when_to_use: str | None = None
    argument_hint: str | None = None
    allowed_tools: list[str] | None = None
    model: str | None = None
    disable_model_invocation: bool = False
    user_invocable: bool | None = None
    is_enabled: bool | None = None
    context: str | None = None
    agent: str | None = None
    effort: str | None = None
    paths: list[str] | None = None
    version: str | None = None
    hooks: dict[str, Any] | None = None
    arguments: list[str] | None = None


# =============================================================================
# Skill Definition
# =============================================================================


@dataclass
class SkillDefinition:
    """Skill definition with progressive loading support.

    Corresponds to the TypeScript Command type (prompt variant) and
    BundledSkillDefinition. Supports lazy loading of full content.

    Attributes:
        name: Unique skill identifier.
        description: One-line description for typeahead.
        aliases: Alternative invocation names.
        when_to_use: Detailed usage scenarios for auto-invocation hints.
        argument_hint: Hint text shown for arguments (e.g., "[topic]").
        allowed_tools: List of permitted tools with optional glob patterns.
            Format: "Read Glob Bash(git:*)"
        instructions: Full skill markdown content (loaded lazily).
        _loaded: Whether full content has been loaded.
        parameters: Named parameters for substitution.
        scripts_path: Path to skill's scripts directory.
        references_path: Path to skill's references directory.
        assets_path: Path to skill's assets directory.
        _path: Path to skill's root directory.
        source: Where this skill was loaded from.
        skill_root: Base directory for the skill.
        user_invocable: Whether user can invoke via slash command.
        is_enabled_fn: Function to check if skill is currently enabled.
        model: Model override for this skill.
        disable_model_invocation: Prevent model from auto-invoking this skill.
        context: Execution context ('inline' or 'fork').
        agent: Agent type for forked execution.
        effort: Effort level for execution.
        paths: Glob patterns for conditional activation.
        hooks: Hook definitions.
        progress_message: Message shown during execution.
        loaded_from: Specific source sub-type.
        is_hidden: Whether skill is hidden from typeahead.
    """

    # Core identity
    name: str
    description: str = ""
    aliases: list[str] = field(default_factory=list)
    when_to_use: str | None = None
    argument_hint: str | None = None

    # Tool restrictions
    allowed_tools: list[str] = field(default_factory=list)

    # Content (progressive loading)
    instructions: str = ""
    _loaded: bool = False
    _path: Path | None = None

    # Named parameters
    parameters: list[SkillParameter] = field(default_factory=list)

    # Resource paths
    scripts_path: Path | None = None
    references_path: Path | None = None
    assets_path: Path | None = None

    # Source tracking
    source: SkillSource = SkillSource.SKILLS
    skill_root: str | None = None
    loaded_from: str | None = None

    # Invocation control
    user_invocable: bool = True
    is_enabled_fn: Callable[[], bool] | None = None
    disable_model_invocation: bool = False

    # Model control
    model: str | None = None

    # Execution context
    context: str = "inline"  # 'inline' or 'fork'
    agent: str | None = None
    effort: str | None = None

    # Conditional activation
    paths: list[str] | None = None

    # Lifecycle hooks
    hooks: dict[str, Any] | None = None

    # Version tracking
    version: str | None = None

    # UI metadata
    progress_message: str = "running"
    is_hidden: bool = False
    content_length: int = 0

    # Arguments
    arguments: list[str] | None = None

    # Callbacks
    get_prompt_for_command: Callable[
        [str, ToolUseContext], list[ContentBlock]
    ] | None = None

    @property
    def is_loaded(self) -> bool:
        """Whether full content has been loaded."""
        return self._loaded

    def load_full(self) -> SkillDefinition:
        """Load full content (instructions + references) on activation.

        Returns:
            Self for chaining.
        """
        if self._loaded or self._path is None:
            return self

        skill_md = self._path / "SKILL.md"
        if skill_md.exists():
            try:
                raw_content = skill_md.read_text()
                _, markdown = parse_frontmatter_from_content(raw_content)
                self.instructions = markdown.strip()
                self.content_length = len(self.instructions)
            except OSError:
                pass

        # Set up resource paths
        self.scripts_path = self._path / "scripts"
        self.references_path = self._path / "references"
        self.assets_path = self._path / "assets"

        self._loaded = True
        return self

    def check_enabled(self) -> bool:
        """Check if skill is currently enabled."""
        if self.is_enabled_fn is not None:
            return self.is_enabled_fn()
        return True

    def get_allowed_tools_patterns(self) -> list[tuple[str, str | None]]:
        """Parse allowed_tools into (tool_name, arg_pattern) pairs.

        Returns:
            List of (tool_name, arg_pattern_or_None) tuples.
            E.g., "Bash(git:*)" -> ("Bash", "git:*")
            E.g., "Read" -> ("Read", None)
        """
        return [
            parse_tool_pattern(t) for t in self.allowed_tools if t.strip()
        ]


# =============================================================================
# Tool Use Context
# =============================================================================


@dataclass
class ToolUseContext:
    """Context passed to skill tool execution.

    Corresponds to TypeScript's ToolUseContext.
    """

    session_id: str | None = None
    cwd: str | None = None
    get_app_state: Callable[[], dict[str, Any]] | None = None

    def get_app_state_dict(self) -> dict[str, Any]:
        """Get app state dict, safely handling None callback."""
        if self.get_app_state is not None:
            return self.get_app_state()
        return {}


# =============================================================================
# Helpers
# =============================================================================

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?", re.DOTALL)


def parse_frontmatter_from_content(content: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter from skill markdown content.

    Args:
        content: Raw SKILL.md content.

    Returns:
        Tuple of (frontmatter_dict, markdown_body).
    """
    import yaml

    match = _FRONTMATTER_RE.match(content)
    if not match:
        return {}, content
    fm_text = match.group(1)
    try:
        frontmatter = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        return {}, content
    markdown_body = content[match.end() :]
    return frontmatter, markdown_body


def parse_tool_pattern(tool_str: str) -> tuple[str, str | None]:
    """Parse a tool pattern string into name and optional arg pattern.

    Args:
        tool_str: Tool string like "Read", "Bash(git:*)", "Glob(*.py)".

    Returns:
        Tuple of (tool_name, arg_pattern_or_None).
    """
    tool_str = tool_str.strip()
    if not tool_str:
        return "", None

    if "(" in tool_str and tool_str.endswith(")"):
        name, args = tool_str.rsplit("(", 1)
        return name.strip(), args[:-1].strip()
    return tool_str, None


def matches_tool_pattern(
    tool_name: str,
    tool_arg: str | None,
    pattern_name: str,
    pattern_arg: str | None,
) -> bool:
    """Check if a tool call matches a tool pattern.

    Args:
        tool_name: The called tool name.
        tool_arg: The argument used (e.g., "git commit").
        pattern_name: The pattern tool name.
        pattern_arg: The pattern argument (e.g., "git:*").

    Returns:
        True if the tool call matches the pattern.
    """
    if tool_name != pattern_name:
        return False

    if pattern_arg is None:
        return True

    if tool_arg is None:
        return pattern_arg == "*"

    # Simple glob matching for arguments
    return _glob_match(tool_arg, pattern_arg)


def _glob_match(text: str, pattern: str) -> bool:
    """Match text against a simple glob pattern.

    Supports: * (any chars), ? (single char).
    """
    # Convert glob pattern to regex
    regex = ""
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c == "*":
            regex += ".*"
        elif c == "?":
            regex += "."
        else:
            regex += re.escape(c)
        i += 1

    return bool(re.match(f"^{regex}$", text))


def path_matches_glob(path: str, pattern: str) -> bool:
    """Check if a path matches a glob pattern.

    Supports: ** for directory matching, * for single path component.

    Args:
        path: The file path to match.
        pattern: Glob pattern (e.g., "**/*.py", "*.ts").

    Returns:
        True if the path matches the pattern.
    """
    # Normalize: ** matches any sequence of path separators + components
    # * matches any sequence of chars within a path segment

    # Handle ** prefix
    if pattern.startswith("**/"):
        # Match anywhere in path
        sub_pattern = pattern[3:]
        # Try matching at each position
        parts = path.split("/")
        for i in range(len(parts)):
            remainder = "/".join(parts[i:])
            if _path_glob_match(remainder, sub_pattern):
                return True
        return False

    return _path_glob_match(path, pattern)


def _path_glob_match(path: str, pattern: str) -> bool:
    """Match path against pattern (no ** prefix handling)."""
    if "**" in pattern:
        # Handle embedded **
        parts = pattern.split("**")
        if len(parts) == 2 and parts[0] == "" and parts[1] != "":
            # Pattern is **something - match trailing part
            suffix = parts[1].lstrip("/")
            return path.endswith(suffix.lstrip("*"))

    path_parts = path.split("/")
    pattern_parts = pattern.split("/")

    pi = 0
    for pp in path_parts:
        if pi >= len(pattern_parts):
            return False
        pat = pattern_parts[pi]
        if pat == "*":
            pi += 1
            continue
        if not _glob_match(pp, pat):
            return False
        pi += 1

    # Match if we've consumed all pattern parts, or remaining are empty
    while pi < len(pattern_parts):
        if pattern_parts[pi] not in ("", "*"):
            return False
        pi += 1

    return True
