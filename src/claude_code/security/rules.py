"""
Security rules module for Claude Code.

This module defines the core security rule types, shell permission rule
matching, and rule parsing for the permission system.

Rule format: ToolName or ToolName(content)
Examples:
- Bash - matches entire Bash tool
- Bash(ls:*) - legacy prefix syntax for ls commands
- Bash(npm install *) - wildcard pattern matching
- Agent(Explore) - agent-specific rule
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from enum import StrEnum

# =============================================================================
# Permission Behavior
# =============================================================================


class PermissionBehavior(StrEnum):
    """The behavior a permission rule specifies for a tool."""

    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


# =============================================================================
# Permission Rule Sources
# =============================================================================


class PermissionRuleSource(StrEnum):
    """The source of a permission rule."""

    USER_SETTINGS = "userSettings"
    PROJECT_SETTINGS = "projectSettings"
    LOCAL_SETTINGS = "localSettings"
    FLAG_SETTINGS = "flagSettings"
    POLICY_SETTINGS = "policySettings"
    CLI_ARG = "cliArg"
    COMMAND = "command"
    SESSION = "session"


# =============================================================================
# Permission Rule Value
# =============================================================================


@dataclass
class PermissionRuleValue:
    """The value/content of a permission rule.

    Attributes:
        tool_name: Name of the tool the rule applies to.
        rule_content: Optional content pattern for the rule.
    """

    tool_name: str
    rule_content: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        """Convert to dictionary representation."""
        return {
            "toolName": self.tool_name,
            "ruleContent": self.rule_content,
        }

    @classmethod
    def from_dict(cls, data: dict[str, str | None]) -> PermissionRuleValue:
        """Create from dictionary representation."""
        tool_name = data["toolName"]
        if tool_name is None:
            raise ValueError("toolName is required in PermissionRuleValue data")
        return cls(
            tool_name=tool_name,
            rule_content=data.get("ruleContent"),
        )


# =============================================================================
# Permission Rule
# =============================================================================


@dataclass
class PermissionRule:
    """A single permission rule.

    Attributes:
        source: Where the rule came from.
        rule_behavior: What the rule allows/denies/asks.
        rule_value: The tool and optional content pattern.
    """

    source: PermissionRuleSource
    rule_behavior: PermissionBehavior
    rule_value: PermissionRuleValue

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary representation."""
        result: dict[str, str] = {
            "source": self.source.value,
            "ruleBehavior": self.rule_behavior.value,
            "ruleValue": str(self),
        }
        return result

    def matches_tool(self, tool_name: str) -> bool:
        """Check if this rule applies to a given tool name."""
        return self.rule_value.tool_name == tool_name

    def __str__(self) -> str:
        """String representation of the rule value.

        Format: ToolName or ToolName(content)
        """
        if self.rule_value.rule_content:
            return f"{self.rule_value.tool_name}({self.rule_value.rule_content})"
        return self.rule_value.tool_name


# =============================================================================
# Shell Permission Rule Types
# =============================================================================


@dataclass
class ShellPermissionRuleExact:
    """Exact command match."""

    type: str = "exact"
    command: str = ""


@dataclass
class ShellPermissionRulePrefix:
    """Prefix match for legacy rules."""

    type: str = "prefix"
    prefix: str = ""


@dataclass
class ShellPermissionRuleWildcard:
    """Wildcard pattern match."""

    type: str = "wildcard"
    pattern: str = ""


ShellPermissionRule = ShellPermissionRuleExact | ShellPermissionRulePrefix | ShellPermissionRuleWildcard


# =============================================================================
# Wildcard Detection
# =============================================================================


_WILDCARD_PATTERN = re.compile(r"[*?\[]")


def has_wildcards(pattern: str) -> bool:
    """Check if a pattern contains wildcard characters.

    Args:
        pattern: The pattern to check.

    Returns:
        True if the pattern contains *, ?, or [ characters.
    """
    return bool(_WILDCARD_PATTERN.search(pattern))


# =============================================================================
# Wildcard Pattern Matching
# =============================================================================


def _escape_glob(pattern: str) -> str:
    """Convert a shell-like glob pattern to fnmatch format.

    Handles:
    - * matches everything including path separators
    - ? matches single character
    - [abc] character classes
    - ** is treated as ** (matched recursively by fnmatch)
    """
    result = []
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c == "*":
            # Check for **
            if i + 1 < len(pattern) and pattern[i + 1] == "*":
                result.append("**")
                i += 2
            else:
                result.append("*")
                i += 1
        elif c == "?":
            result.append("?")
            i += 1
        elif c == "[":
            result.append("[")
            i += 1
            # Handle negation and ranges inside brackets
            while i < len(pattern) and pattern[i] != "]":
                result.append(pattern[i])
                i += 1
            if i < len(pattern):
                result.append("]")
                i += 1
        else:
            result.append(c)
            i += 1
    return "".join(result)


def match_wildcard_pattern(
    pattern: str,
    command: str,
    case_insensitive: bool = False,
) -> bool:
    """Match a command against a wildcard pattern.

    Args:
        pattern: The wildcard pattern to match against.
        command: The command string to test.
        case_insensitive: Whether to do case-insensitive matching.

    Returns:
        True if the command matches the pattern.

    Examples:
        >>> match_wildcard_pattern("npm install *", "npm install express")
        True
        >>> match_wildcard_pattern("npm install *", "npm install")
        True
        >>> match_wildcard_pattern("npm install *", "npm run build")
        False
        >>> match_wildcard_pattern("ls *", "ls /usr/local/bin")
        True
    """
    if not has_wildcards(pattern):
        # No wildcards - use exact match
        if case_insensitive:
            return pattern.lower() == command.lower()
        return pattern == command

    # Strip trailing whitespace from pattern so that "npm install * "
    # matches "npm install express" just like "npm install *".
    # This handles the common case where rules have trailing spaces.
    pattern_stripped = pattern.rstrip()

    # Handle trailing " *" patterns specially.
    # In shell permission rules, "npm install *" means "npm install with any arguments",
    # which should also match just "npm install" (no arguments).
    if pattern_stripped.endswith(" *"):
        base_pattern = pattern_stripped[:-2]
        if case_insensitive:
            if base_pattern.lower() == command.lower():
                return True
        elif base_pattern == command:
            return True

    # Convert to fnmatch pattern
    glob_pattern = _escape_glob(pattern_stripped)

    if case_insensitive:
        return fnmatch.fnmatch(command.lower(), glob_pattern.lower())
    return fnmatch.fnmatch(command, glob_pattern)


# =============================================================================
# Rule String Parsing
# =============================================================================


def parse_permission_rule_value(rule_string: str) -> PermissionRuleValue:
    """Parse a rule string into a PermissionRuleValue.

    Args:
        rule_string: A rule string like "Bash", "Bash(ls:*)", or "Bash(npm install *)"

    Returns:
        A PermissionRuleValue with the parsed tool name and content.

    Examples:
        >>> parse_permission_rule_value("Bash")
        PermissionRuleValue(tool_name='Bash', rule_content=None)
        >>> parse_permission_rule_value("Bash(ls)")
        PermissionRuleValue(tool_name='Bash', rule_content='ls')
        >>> parse_permission_rule_value("Agent(Explore)")
        PermissionRuleValue(tool_name='Agent', rule_content='Explore')
    """
    # Handle legacy prefix syntax: ToolName(prefix:pattern)
    # e.g., Bash(ls:*) -> tool_name=Bash, content=ls:*
    if "(" in rule_string and rule_string.endswith(")"):
        paren_idx = rule_string.index("(")
        tool_name = rule_string[:paren_idx]
        content = rule_string[paren_idx + 1 : -1]
        return PermissionRuleValue(tool_name=tool_name, rule_content=content)

    # Simple tool-only rule
    return PermissionRuleValue(tool_name=rule_string)


def format_permission_rule_value(rule_value: PermissionRuleValue) -> str:
    """Format a PermissionRuleValue back to a string.

    Args:
        rule_value: The rule value to format.

    Returns:
        A string representation of the rule.

    Examples:
        >>> format_permission_rule_value(PermissionRuleValue("Bash", None))
        'Bash'
        >>> format_permission_rule_value(PermissionRuleValue("Bash", "ls"))
        'Bash(ls)'
    """
    if rule_value.rule_content:
        return f"{rule_value.tool_name}({rule_value.rule_content})"
    return rule_value.tool_name


# =============================================================================
# Rule Matching
# =============================================================================


def match_shell_rule(
    rule: PermissionRule,
    tool_name: str,
    command: str,
    case_insensitive: bool = False,
) -> bool:
    """Check if a permission rule matches a shell command.

    Args:
        rule: The permission rule to check.
        tool_name: Name of the tool (e.g., "Bash").
        command: The command string to check.
        case_insensitive: Whether to do case-insensitive matching.

    Returns:
        True if the rule matches the command.

    Examples:
        >>> rule = PermissionRule(
        ...     source=PermissionRuleSource.USER_SETTINGS,
        ...     rule_behavior=PermissionBehavior.ALLOW,
        ...     rule_value=PermissionRuleValue("Bash", "npm install *"),
        ... )
        >>> match_shell_rule(rule, "Bash", "npm install express")
        True
    """
    if not rule.matches_tool(tool_name):
        return False

    content = rule.rule_value.rule_content
    if content is None:
        # Rule applies to all commands for this tool
        return True

    if not has_wildcards(content):
        # Exact match on content
        if case_insensitive:
            return content.lower() == command.lower()
        return content == command

    # Wildcard pattern matching
    return match_wildcard_pattern(content, command, case_insensitive)


def get_tool_name_from_rule(rule_string: str) -> str:
    """Extract the tool name from a rule string.

    Args:
        rule_string: A rule string like "Bash" or "Bash(npm install *)"

    Returns:
        The tool name.

    Examples:
        >>> get_tool_name_from_rule("Bash")
        'Bash'
        >>> get_tool_name_from_rule("Bash(ls -la)")
        'Bash'
        >>> get_tool_name_from_rule("Agent(Explore)")
        'Agent'
    """
    if "(" in rule_string:
        return rule_string[: rule_string.index("(")]
    return rule_string


# =============================================================================
# Rule Builder
# =============================================================================


@dataclass
class PermissionRuleBuilder:
    """Builder for creating permission rules fluently."""

    _source: PermissionRuleSource | None = None
    _behavior: PermissionBehavior | None = None
    _tool_name: str | None = None
    _content: str | None = None

    def with_source(self, source: PermissionRuleSource) -> PermissionRuleBuilder:
        """Set the rule source."""
        self._source = source
        return self

    def with_behavior(self, behavior: PermissionBehavior) -> PermissionRuleBuilder:
        """Set the rule behavior."""
        self._behavior = behavior
        return self

    def for_tool(self, tool_name: str) -> PermissionRuleBuilder:
        """Set the tool name."""
        self._tool_name = tool_name
        return self

    def with_content(self, content: str) -> PermissionRuleBuilder:
        """Set the rule content (pattern)."""
        self._content = content
        return self

    def build(self) -> PermissionRule:
        """Build the permission rule."""
        if self._source is None:
            raise ValueError("source is required")
        if self._behavior is None:
            raise ValueError("behavior is required")
        if self._tool_name is None:
            raise ValueError("tool_name is required")

        return PermissionRule(
            source=self._source,
            rule_behavior=self._behavior,
            rule_value=PermissionRuleValue(
                tool_name=self._tool_name,
                rule_content=self._content,
            ),
        )


# =============================================================================
# Risk Levels
# =============================================================================


class RiskLevel(StrEnum):
    """Risk level for permission requests."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


# =============================================================================
# Predefined Rule Patterns
# =============================================================================


# Common safe commands that are often allowed
SAFE_BASH_PATTERNS = [
    "git *",
    "ls *",
    "pwd",
    "cd *",
    "echo *",
    "cat *",
    "head *",
    "tail *",
    "grep *",
    "find *",
    "npm --version",
    "node --version",
    "python --version",
    "pip --version",
]

# High-risk patterns that should typically be denied
DANGEROUS_PATTERNS = [
    "rm -rf /*",
    "rm -rf /",
    "dd if=* of=/dev/*",
    ":(){:|:&};:",  # Fork bomb
    "mkfs.*",
    "dd if=/dev/zero of=*",
]


@dataclass
class RuleSet:
    """A collection of permission rules."""

    rules: list[PermissionRule] = field(default_factory=list)

    def add_rule(self, rule: PermissionRule) -> None:
        """Add a rule to the set."""
        self.rules.append(rule)

    def add_allow(
        self,
        tool_name: str,
        content: str | None = None,
        source: PermissionRuleSource = PermissionRuleSource.USER_SETTINGS,
    ) -> PermissionRule:
        """Add an allow rule."""
        rule = PermissionRule(
            source=source,
            rule_behavior=PermissionBehavior.ALLOW,
            rule_value=PermissionRuleValue(tool_name=tool_name, rule_content=content),
        )
        self.rules.append(rule)
        return rule

    def add_deny(
        self,
        tool_name: str,
        content: str | None = None,
        source: PermissionRuleSource = PermissionRuleSource.USER_SETTINGS,
    ) -> PermissionRule:
        """Add a deny rule."""
        rule = PermissionRule(
            source=source,
            rule_behavior=PermissionBehavior.DENY,
            rule_value=PermissionRuleValue(tool_name=tool_name, rule_content=content),
        )
        self.rules.append(rule)
        return rule

    def add_ask(
        self,
        tool_name: str,
        content: str | None = None,
        source: PermissionRuleSource = PermissionRuleSource.USER_SETTINGS,
    ) -> PermissionRule:
        """Add an ask rule."""
        rule = PermissionRule(
            source=source,
            rule_behavior=PermissionBehavior.ASK,
            rule_value=PermissionRuleValue(tool_name=tool_name, rule_content=content),
        )
        self.rules.append(rule)
        return rule

    def get_rules_for_tool(self, tool_name: str) -> list[PermissionRule]:
        """Get all rules for a specific tool."""
        return [r for r in self.rules if r.matches_tool(tool_name)]

    def get_allow_rules(self) -> list[PermissionRule]:
        """Get all allow rules."""
        return [r for r in self.rules if r.rule_behavior == PermissionBehavior.ALLOW]

    def get_deny_rules(self) -> list[PermissionRule]:
        """Get all deny rules."""
        return [r for r in self.rules if r.rule_behavior == PermissionBehavior.DENY]

    def get_ask_rules(self) -> list[PermissionRule]:
        """Get all ask rules."""
        return [r for r in self.rules if r.rule_behavior == PermissionBehavior.ASK]
