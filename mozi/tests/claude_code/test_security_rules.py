"""
Tests for security rules module.
"""

from __future__ import annotations

import pytest
from claude_code.security.rules import (
    DANGEROUS_PATTERNS,
    SAFE_BASH_PATTERNS,
    PermissionBehavior,
    PermissionRule,
    PermissionRuleBuilder,
    PermissionRuleSource,
    PermissionRuleValue,
    RiskLevel,
    RuleSet,
    format_permission_rule_value,
    get_tool_name_from_rule,
    has_wildcards,
    match_shell_rule,
    match_wildcard_pattern,
    parse_permission_rule_value,
)


class TestPermissionBehavior:
    """Tests for PermissionBehavior enum."""

    def test_values(self) -> None:
        """Test that enum has expected values."""
        assert PermissionBehavior.ALLOW.value == "allow"
        assert PermissionBehavior.DENY.value == "deny"
        assert PermissionBehavior.ASK.value == "ask"

    def test_from_string(self) -> None:
        """Test creating from string value."""
        assert PermissionBehavior("allow") == PermissionBehavior.ALLOW
        assert PermissionBehavior("deny") == PermissionBehavior.DENY
        assert PermissionBehavior("ask") == PermissionBehavior.ASK

    def test_is_string(self) -> None:
        """Test that enum values are strings."""
        assert isinstance(PermissionBehavior.ALLOW, str)
        assert PermissionBehavior.ALLOW == "allow"


class TestPermissionRuleSource:
    """Tests for PermissionRuleSource enum."""

    def test_values(self) -> None:
        """Test that enum has expected values."""
        assert PermissionRuleSource.USER_SETTINGS.value == "userSettings"
        assert PermissionRuleSource.PROJECT_SETTINGS.value == "projectSettings"
        assert PermissionRuleSource.LOCAL_SETTINGS.value == "localSettings"
        assert PermissionRuleSource.FLAG_SETTINGS.value == "flagSettings"
        assert PermissionRuleSource.POLICY_SETTINGS.value == "policySettings"
        assert PermissionRuleSource.CLI_ARG.value == "cliArg"
        assert PermissionRuleSource.COMMAND.value == "command"
        assert PermissionRuleSource.SESSION.value == "session"


class TestPermissionRuleValue:
    """Tests for PermissionRuleValue dataclass."""

    def test_create_without_content(self) -> None:
        """Test creating a rule value without content."""
        rv = PermissionRuleValue(tool_name="Bash")
        assert rv.tool_name == "Bash"
        assert rv.rule_content is None

    def test_create_with_content(self) -> None:
        """Test creating a rule value with content."""
        rv = PermissionRuleValue(tool_name="Bash", rule_content="ls")
        assert rv.tool_name == "Bash"
        assert rv.rule_content == "ls"

    def test_to_dict_without_content(self) -> None:
        """Test converting to dict without content."""
        rv = PermissionRuleValue(tool_name="Bash")
        result = rv.to_dict()
        assert result == {"toolName": "Bash", "ruleContent": None}

    def test_to_dict_with_content(self) -> None:
        """Test converting to dict with content."""
        rv = PermissionRuleValue(tool_name="Bash", rule_content="ls")
        result = rv.to_dict()
        assert result == {"toolName": "Bash", "ruleContent": "ls"}

    def test_from_dict_without_content(self) -> None:
        """Test creating from dict without content."""
        data = {"toolName": "Bash", "ruleContent": None}
        rv = PermissionRuleValue.from_dict(data)
        assert rv.tool_name == "Bash"
        assert rv.rule_content is None

    def test_from_dict_with_content(self) -> None:
        """Test creating from dict with content."""
        data = {"toolName": "Bash", "ruleContent": "ls"}
        rv = PermissionRuleValue.from_dict(data)
        assert rv.tool_name == "Bash"
        assert rv.rule_content == "ls"


class TestPermissionRule:
    """Tests for PermissionRule dataclass."""

    def test_create(self) -> None:
        """Test creating a permission rule."""
        rule = PermissionRule(
            source=PermissionRuleSource.USER_SETTINGS,
            rule_behavior=PermissionBehavior.ALLOW,
            rule_value=PermissionRuleValue(tool_name="Bash"),
        )
        assert rule.source == PermissionRuleSource.USER_SETTINGS
        assert rule.rule_behavior == PermissionBehavior.ALLOW
        assert rule.rule_value.tool_name == "Bash"

    def test_matches_tool_true(self) -> None:
        """Test matching a tool name."""
        rule = PermissionRule(
            source=PermissionRuleSource.USER_SETTINGS,
            rule_behavior=PermissionBehavior.ALLOW,
            rule_value=PermissionRuleValue(tool_name="Bash"),
        )
        assert rule.matches_tool("Bash") is True

    def test_matches_tool_false(self) -> None:
        """Test non-matching tool name."""
        rule = PermissionRule(
            source=PermissionRuleSource.USER_SETTINGS,
            rule_behavior=PermissionBehavior.ALLOW,
            rule_value=PermissionRuleValue(tool_name="Bash"),
        )
        assert rule.matches_tool("Agent") is False

    def test_str_without_content(self) -> None:
        """Test string representation without content."""
        rule = PermissionRule(
            source=PermissionRuleSource.USER_SETTINGS,
            rule_behavior=PermissionBehavior.ALLOW,
            rule_value=PermissionRuleValue(tool_name="Bash"),
        )
        assert str(rule) == "Bash"

    def test_str_with_content(self) -> None:
        """Test string representation with content."""
        rule = PermissionRule(
            source=PermissionRuleSource.USER_SETTINGS,
            rule_behavior=PermissionBehavior.ALLOW,
            rule_value=PermissionRuleValue(tool_name="Bash", rule_content="ls"),
        )
        assert str(rule) == "Bash(ls)"

    def test_to_dict(self) -> None:
        """Test converting to dict."""
        rule = PermissionRule(
            source=PermissionRuleSource.USER_SETTINGS,
            rule_behavior=PermissionBehavior.ALLOW,
            rule_value=PermissionRuleValue(tool_name="Bash"),
        )
        result = rule.to_dict()
        assert result["source"] == "userSettings"
        assert result["ruleBehavior"] == "allow"


class TestHasWildcards:
    """Tests for has_wildcards function."""

    def test_no_wildcards(self) -> None:
        """Test string without wildcards."""
        assert has_wildcards("ls") is False
        assert has_wildcards("git commit") is False
        assert has_wildcards("") is False

    def test_has_asterisk(self) -> None:
        """Test string with asterisk."""
        assert has_wildcards("ls *") is True
        assert has_wildcards("*") is True
        assert has_wildcards("npm install *") is True

    def test_has_question_mark(self) -> None:
        """Test string with question mark."""
        assert has_wildcards("test_?.py") is True

    def test_has_brackets(self) -> None:
        """Test string with brackets."""
        assert has_wildcards("file[0-9].txt") is True


class TestMatchWildcardPattern:
    """Tests for match_wildcard_pattern function."""

    def test_no_wildcards_exact_match(self) -> None:
        """Test exact match without wildcards."""
        assert match_wildcard_pattern("ls", "ls") is True
        assert match_wildcard_pattern("ls", "ls -la") is False

    def test_no_wildcards_case_insensitive(self) -> None:
        """Test case insensitive exact match."""
        assert match_wildcard_pattern("LS", "ls", case_insensitive=True) is True
        assert match_wildcard_pattern("ls", "LS", case_insensitive=True) is True

    def test_asterisk_match(self) -> None:
        """Test asterisk wildcard matching."""
        assert match_wildcard_pattern("npm install *", "npm install express") is True
        assert match_wildcard_pattern("npm install *", "npm install") is True
        assert match_wildcard_pattern("npm install *", "npm run build") is False

    def test_asterisk_path_separator(self) -> None:
        """Test that asterisk matches path separators."""
        assert match_wildcard_pattern("ls *", "ls /usr/local/bin") is True

    def test_question_mark_match(self) -> None:
        """Test question mark wildcard matching."""
        assert match_wildcard_pattern("test_?.py", "test_a.py") is True
        assert match_wildcard_pattern("test_?.py", "test_ab.py") is False

    def test_brackets_match(self) -> None:
        """Test bracket character class matching."""
        assert match_wildcard_pattern("file[01].txt", "file0.txt") is True
        assert match_wildcard_pattern("file[01].txt", "file1.txt") is True
        assert match_wildcard_pattern("file[01].txt", "file2.txt") is False


class TestParsePermissionRuleValue:
    """Tests for parse_permission_rule_value function."""

    def test_simple_tool_name(self) -> None:
        """Test parsing simple tool name."""
        rv = parse_permission_rule_value("Bash")
        assert rv.tool_name == "Bash"
        assert rv.rule_content is None

    def test_tool_with_content(self) -> None:
        """Test parsing tool with content."""
        rv = parse_permission_rule_value("Bash(ls)")
        assert rv.tool_name == "Bash"
        assert rv.rule_content == "ls"

    def test_tool_with_complex_content(self) -> None:
        """Test parsing tool with complex content."""
        rv = parse_permission_rule_value("Bash(npm install *)")
        assert rv.tool_name == "Bash"
        assert rv.rule_content == "npm install *"

    def test_agent_rule(self) -> None:
        """Test parsing agent rule."""
        rv = parse_permission_rule_value("Agent(Explore)")
        assert rv.tool_name == "Agent"
        assert rv.rule_content == "Explore"

    def test_legacy_prefix_syntax(self) -> None:
        """Test parsing legacy prefix syntax."""
        rv = parse_permission_rule_value("Bash(ls:*)")
        assert rv.tool_name == "Bash"
        assert rv.rule_content == "ls:*"


class TestFormatPermissionRuleValue:
    """Tests for format_permission_rule_value function."""

    def test_without_content(self) -> None:
        """Test formatting without content."""
        rv = PermissionRuleValue(tool_name="Bash")
        assert format_permission_rule_value(rv) == "Bash"

    def test_with_content(self) -> None:
        """Test formatting with content."""
        rv = PermissionRuleValue(tool_name="Bash", rule_content="ls")
        assert format_permission_rule_value(rv) == "Bash(ls)"


class TestGetToolNameFromRule:
    """Tests for get_tool_name_from_rule function."""

    def test_simple_tool_name(self) -> None:
        """Test extracting tool name from simple rule."""
        assert get_tool_name_from_rule("Bash") == "Bash"

    def test_tool_with_content(self) -> None:
        """Test extracting tool name from rule with content."""
        assert get_tool_name_from_rule("Bash(ls -la)") == "Bash"

    def test_agent_rule(self) -> None:
        """Test extracting tool name from agent rule."""
        assert get_tool_name_from_rule("Agent(Explore)") == "Agent"


class TestMatchShellRule:
    """Tests for match_shell_rule function."""

    def test_tool_no_content(self) -> None:
        """Test matching rule with no content (matches all commands)."""
        rule = PermissionRule(
            source=PermissionRuleSource.USER_SETTINGS,
            rule_behavior=PermissionBehavior.ALLOW,
            rule_value=PermissionRuleValue(tool_name="Bash"),
        )
        assert match_shell_rule(rule, "Bash", "any command") is True

    def test_tool_mismatch(self) -> None:
        """Test non-matching tool name."""
        rule = PermissionRule(
            source=PermissionRuleSource.USER_SETTINGS,
            rule_behavior=PermissionBehavior.ALLOW,
            rule_value=PermissionRuleValue(tool_name="Bash"),
        )
        assert match_shell_rule(rule, "Agent", "any command") is False

    def test_exact_content_match(self) -> None:
        """Test exact content matching."""
        rule = PermissionRule(
            source=PermissionRuleSource.USER_SETTINGS,
            rule_behavior=PermissionBehavior.ALLOW,
            rule_value=PermissionRuleValue(tool_name="Bash", rule_content="ls"),
        )
        assert match_shell_rule(rule, "Bash", "ls") is True
        assert match_shell_rule(rule, "Bash", "ls -la") is False

    def test_wildcard_match(self) -> None:
        """Test wildcard matching."""
        rule = PermissionRule(
            source=PermissionRuleSource.USER_SETTINGS,
            rule_behavior=PermissionBehavior.ALLOW,
            rule_value=PermissionRuleValue(tool_name="Bash", rule_content="npm install *"),
        )
        assert match_shell_rule(rule, "Bash", "npm install express") is True
        assert match_shell_rule(rule, "Bash", "npm install @types/node") is True

    def test_case_insensitive(self) -> None:
        """Test case insensitive matching."""
        rule = PermissionRule(
            source=PermissionRuleSource.USER_SETTINGS,
            rule_behavior=PermissionBehavior.ALLOW,
            rule_value=PermissionRuleValue(tool_name="Bash", rule_content="LS"),
        )
        assert match_shell_rule(rule, "Bash", "ls", case_insensitive=True) is True


class TestPermissionRuleBuilder:
    """Tests for PermissionRuleBuilder."""

    def test_build_allow_rule(self) -> None:
        """Test building an allow rule."""
        rule = (
            PermissionRuleBuilder()
            .with_source(PermissionRuleSource.USER_SETTINGS)
            .with_behavior(PermissionBehavior.ALLOW)
            .for_tool("Bash")
            .with_content("ls")
            .build()
        )
        assert rule.rule_behavior == PermissionBehavior.ALLOW
        assert rule.rule_value.tool_name == "Bash"
        assert rule.rule_value.rule_content == "ls"

    def test_build_without_content(self) -> None:
        """Test building a rule without content."""
        rule = (
            PermissionRuleBuilder()
            .with_source(PermissionRuleSource.USER_SETTINGS)
            .with_behavior(PermissionBehavior.ALLOW)
            .for_tool("Bash")
            .build()
        )
        assert rule.rule_value.rule_content is None

    def test_build_missing_source(self) -> None:
        """Test that missing source raises error."""
        builder = (
            PermissionRuleBuilder()
            .with_behavior(PermissionBehavior.ALLOW)
            .for_tool("Bash")
        )
        with pytest.raises(ValueError, match="source is required"):
            builder.build()


class TestRiskLevel:
    """Tests for RiskLevel enum."""

    def test_values(self) -> None:
        """Test that enum has expected values."""
        assert RiskLevel.LOW.value == "LOW"
        assert RiskLevel.MEDIUM.value == "MEDIUM"
        assert RiskLevel.HIGH.value == "HIGH"


class TestRuleSet:
    """Tests for RuleSet dataclass."""

    def test_add_allow_rule(self) -> None:
        """Test adding an allow rule."""
        rs = RuleSet()
        rule = rs.add_allow("Bash")
        assert rule.rule_behavior == PermissionBehavior.ALLOW
        assert rule.rule_value.tool_name == "Bash"

    def test_add_deny_rule(self) -> None:
        """Test adding a deny rule."""
        rs = RuleSet()
        rule = rs.add_deny("Bash")
        assert rule.rule_behavior == PermissionBehavior.DENY

    def test_add_ask_rule(self) -> None:
        """Test adding an ask rule."""
        rs = RuleSet()
        rule = rs.add_ask("Bash")
        assert rule.rule_behavior == PermissionBehavior.ASK

    def test_get_rules_for_tool(self) -> None:
        """Test getting rules for a specific tool."""
        rs = RuleSet()
        rs.add_allow("Bash")
        rs.add_deny("Bash", "rm -rf")
        rs.add_allow("Agent")

        bash_rules = rs.get_rules_for_tool("Bash")
        assert len(bash_rules) == 2

    def test_get_allow_rules(self) -> None:
        """Test getting all allow rules."""
        rs = RuleSet()
        rs.add_allow("Bash")
        rs.add_deny("Bash")
        rs.add_allow("Agent")

        allow_rules = rs.get_allow_rules()
        assert len(allow_rules) == 2

    def test_get_deny_rules(self) -> None:
        """Test getting all deny rules."""
        rs = RuleSet()
        rs.add_allow("Bash")
        rs.add_deny("Bash")
        rs.add_deny("Agent")

        deny_rules = rs.get_deny_rules()
        assert len(deny_rules) == 2


class TestPredefinedPatterns:
    """Tests for predefined rule patterns."""

    def test_safe_bash_patterns_exist(self) -> None:
        """Test that safe patterns are defined."""
        assert len(SAFE_BASH_PATTERNS) > 0
        assert any("git" in p for p in SAFE_BASH_PATTERNS)
        assert any("ls" in p for p in SAFE_BASH_PATTERNS)

    def test_dangerous_patterns_exist(self) -> None:
        """Test that dangerous patterns are defined."""
        assert len(DANGEROUS_PATTERNS) > 0
        assert any("rm -rf" in p for p in DANGEROUS_PATTERNS)
