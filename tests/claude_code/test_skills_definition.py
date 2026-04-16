"""
Tests for skills/definition.py - SkillDefinition and helpers.
"""

from __future__ import annotations

import pytest

from src.claude_code.skills.definition import (
    SkillDefinition,
    SkillFrontmatter,
    SkillParameter,
    SkillSource,
    ToolUseContext,
    matches_tool_pattern,
    parse_frontmatter_from_content,
    parse_tool_pattern,
    path_matches_glob,
)


class TestSkillSource:
    """Tests for SkillSource enum."""

    def test_skill_source_values(self) -> None:
        """SkillSource has expected values."""
        assert SkillSource.BUNDLED == "bundled"
        assert SkillSource.MANAGED == "managed"
        assert SkillSource.SKILLS == "skills"
        assert SkillSource.PROJECT == "project"
        assert SkillSource.PLUGIN == "plugin"
        assert SkillSource.MCP == "mcp"


class TestSkillParameter:
    """Tests for SkillParameter dataclass."""

    def test_defaults(self) -> None:
        """SkillParameter has correct defaults."""
        param = SkillParameter(name="topic")
        assert param.name == "topic"
        assert param.type == "string"
        assert param.description == ""
        assert param.required is False

    def test_full_initialization(self) -> None:
        """SkillParameter can be fully initialized."""
        param = SkillParameter(
            name="limit",
            type="number",
            description="Max results",
            required=True,
        )
        assert param.name == "limit"
        assert param.type == "number"
        assert param.description == "Max results"
        assert param.required is True


class TestSkillDefinition:
    """Tests for SkillDefinition dataclass."""

    def test_defaults(self) -> None:
        """SkillDefinition has correct defaults."""
        skill = SkillDefinition(name="test")
        assert skill.name == "test"
        assert skill.description == ""
        assert skill.aliases == []
        assert skill.allowed_tools == []
        assert skill.instructions == ""
        assert skill._loaded is False
        assert skill.source == SkillSource.SKILLS
        assert skill.user_invocable is True
        assert skill.context == "inline"
        assert skill.disable_model_invocation is False
        assert skill.is_hidden is False

    def test_full_initialization(self) -> None:
        """SkillDefinition can be fully initialized."""
        skill = SkillDefinition(
            name="simplify",
            description="Simplify code",
            aliases=["improve"],
            when_to_use="When code needs simplification",
            argument_hint="[target]",
            allowed_tools=["Read", "Glob"],
            instructions="Review and simplify code.",
            user_invocable=True,
            model="claude-opus-4-6",
            context="inline",
            agent="general-purpose",
            effort="low",
            source=SkillSource.BUNDLED,
        )
        assert skill.name == "simplify"
        assert skill.description == "Simplify code"
        assert skill.aliases == ["improve"]
        assert skill.when_to_use == "When code needs simplification"
        assert skill.argument_hint == "[target]"
        assert skill.allowed_tools == ["Read", "Glob"]
        assert skill.instructions == "Review and simplify code."
        assert skill.user_invocable is True
        assert skill.model == "claude-opus-4-6"
        assert skill.context == "inline"
        assert skill.agent == "general-purpose"
        assert skill.effort == "low"
        assert skill.source == SkillSource.BUNDLED

    def test_is_loaded_property(self) -> None:
        """is_loaded property reflects _loaded state."""
        skill = SkillDefinition(name="test")
        assert skill.is_loaded is False
        skill._loaded = True
        assert skill.is_loaded is True

    def test_load_full_returns_self(self) -> None:
        """load_full returns self for chaining."""
        skill = SkillDefinition(name="test")
        result = skill.load_full()
        assert result is skill

    def test_load_full_with_no_path(self) -> None:
        """load_full with no _path returns self without loading."""
        skill = SkillDefinition(name="test")
        skill._loaded = False
        skill._path = None
        result = skill.load_full()
        # _loaded stays False when _path is None (nothing to load)
        assert skill._loaded is False
        assert result is skill

    def test_load_full_with_nonexistent_path(self, tmp_path: pytest.TempPathFactory) -> None:
        """load_full handles nonexistent SKILL.md gracefully."""
        skill = SkillDefinition(name="test")
        skill._path = tmp_path / "nonexistent"
        skill._loaded = False
        skill.load_full()
        assert skill._loaded is True
        assert skill.instructions == ""

    def test_load_full_loads_content(self, tmp_path: pytest.TempPathFactory) -> None:
        """load_full reads SKILL.md content."""
        skill_path = tmp_path / "test"
        skill_path.mkdir()
        skill_path.joinpath("SKILL.md").write_text("Test instructions")
        skill = SkillDefinition(name="test")
        skill._path = skill_path
        skill._loaded = False
        skill.load_full()
        assert skill._loaded is True
        assert skill.instructions == "Test instructions"
        assert skill.scripts_path == skill_path / "scripts"
        assert skill.references_path == skill_path / "references"
        assert skill.assets_path == skill_path / "assets"

    def test_check_enabled_no_fn(self) -> None:
        """check_enabled returns True when no is_enabled_fn."""
        skill = SkillDefinition(name="test")
        assert skill.check_enabled() is True

    def test_check_enabled_with_fn_true(self) -> None:
        """check_enabled calls is_enabled_fn when set."""
        skill = SkillDefinition(name="test", is_enabled_fn=lambda: True)
        assert skill.check_enabled() is True

    def test_check_enabled_with_fn_false(self) -> None:
        """check_enabled returns False when is_enabled_fn returns False."""
        skill = SkillDefinition(name="test", is_enabled_fn=lambda: False)
        assert skill.check_enabled() is False

    def test_get_allowed_tools_patterns(self) -> None:
        """get_allowed_tools_patterns parses allowed_tools."""
        skill = SkillDefinition(
            name="test",
            allowed_tools=["Read", "Bash(git:*)", "Glob(*.py)"],
        )
        patterns = skill.get_allowed_tools_patterns()
        assert patterns == [("Read", None), ("Bash", "git:*"), ("Glob", "*.py")]

    def test_get_allowed_tools_patterns_empty(self) -> None:
        """get_allowed_tools_patterns handles empty list."""
        skill = SkillDefinition(name="test")
        patterns = skill.get_allowed_tools_patterns()
        assert patterns == []

    def test_progress_message_default(self) -> None:
        """progress_message defaults to 'running'."""
        skill = SkillDefinition(name="test")
        assert skill.progress_message == "running"


class TestToolUseContext:
    """Tests for ToolUseContext."""

    def test_defaults(self) -> None:
        """ToolUseContext has correct defaults."""
        ctx = ToolUseContext()
        assert ctx.session_id is None
        assert ctx.cwd is None
        assert ctx.get_app_state is None

    def test_initialization(self) -> None:
        """ToolUseContext can be fully initialized."""
        def state_fn() -> dict[str, str]:
            return {"theme": "dark"}
        ctx = ToolUseContext(
            session_id="sess-123",
            cwd="/project",
            get_app_state=state_fn,
        )
        assert ctx.session_id == "sess-123"
        assert ctx.cwd == "/project"
        assert ctx.get_app_state is state_fn

    def test_get_app_state_dict_with_callback(self) -> None:
        """get_app_state_dict calls callback."""
        ctx = ToolUseContext(get_app_state=lambda: {"theme": "dark"})
        assert ctx.get_app_state_dict() == {"theme": "dark"}

    def test_get_app_state_dict_without_callback(self) -> None:
        """get_app_state_dict returns empty dict without callback."""
        ctx = ToolUseContext()
        assert ctx.get_app_state_dict() == {}


class TestParseToolPattern:
    """Tests for parse_tool_pattern helper."""

    def test_simple_tool(self) -> None:
        """parse_tool_pattern handles simple tool names."""
        assert parse_tool_pattern("Read") == ("Read", None)

    def test_tool_with_args(self) -> None:
        """parse_tool_pattern handles tool with args."""
        assert parse_tool_pattern("Bash(git:*)") == ("Bash", "git:*")

    def test_tool_with_args_no_space(self) -> None:
        """parse_tool_pattern handles tool args without spaces."""
        assert parse_tool_pattern("Glob(*.py)") == ("Glob", "*.py")

    def test_empty_string(self) -> None:
        """parse_tool_pattern handles empty string."""
        assert parse_tool_pattern("") == ("", None)

    def test_whitespace(self) -> None:
        """parse_tool_pattern trims whitespace."""
        assert parse_tool_pattern("  Read  ") == ("Read", None)
        assert parse_tool_pattern("Bash( git:* )") == ("Bash", "git:*")

    def test_complex_pattern(self) -> None:
        """parse_tool_pattern handles complex patterns."""
        assert parse_tool_pattern("Bash(git commit -m *)") == (
            "Bash",
            "git commit -m *",
        )


class TestMatchesToolPattern:
    """Tests for matches_tool_pattern helper."""

    def test_name_mismatch(self) -> None:
        """matches_tool_pattern returns False on name mismatch."""
        assert matches_tool_pattern("Read", None, "Write", None) is False

    def test_no_arg_pattern(self) -> None:
        """matches_tool_pattern returns True when no arg pattern."""
        assert matches_tool_pattern("Read", "some text", "Read", None) is True

    def test_arg_pattern_star(self) -> None:
        """matches_tool_pattern matches * pattern."""
        assert matches_tool_pattern("Read", "anything", "Read", "*") is True

    def test_arg_pattern_exact_match(self) -> None:
        """matches_tool_pattern matches exact arg."""
        assert matches_tool_pattern("Bash", "git commit", "Bash", "git commit") is True

    def test_arg_pattern_glob_star(self) -> None:
        """matches_tool_pattern supports * in arg pattern."""
        assert matches_tool_pattern("Bash", "git commit -m 'fix bug'", "Bash", "git *") is True
        assert matches_tool_pattern("Bash", "npm install", "Bash", "git *") is False

    def test_arg_pattern_glob_question(self) -> None:
        """matches_tool_pattern supports ? in arg pattern."""
        assert matches_tool_pattern("Bash", "git c", "Bash", "git ?") is True
        assert matches_tool_pattern("Bash", "git co", "Bash", "git ?") is False

    def test_none_tool_arg(self) -> None:
        """matches_tool_pattern handles None tool_arg."""
        assert matches_tool_pattern("Read", None, "Read", None) is True
        assert matches_tool_pattern("Read", None, "Read", "*") is True
        assert matches_tool_pattern("Read", None, "Read", "specific") is False


class TestPathMatchesGlob:
    """Tests for path_matches_glob helper."""

    def test_exact_match(self) -> None:
        """path_matches_glob matches exact paths."""
        assert path_matches_glob("src/main.py", "src/main.py") is True
        assert path_matches_glob("src/main.py", "src/other.py") is False

    def test_single_star(self) -> None:
        """path_matches_glob matches single star."""
        assert path_matches_glob("src/main.py", "src/*.py") is True
        assert path_matches_glob("src/main.ts", "src/*.py") is False

    def test_double_star_anywhere(self) -> None:
        """path_matches_glob handles ** anywhere."""
        assert path_matches_glob("src/main.py", "**/*.py") is True
        assert path_matches_glob("src/lib/util.py", "**/*.py") is True
        assert path_matches_glob("src/main.ts", "**/*.py") is False

    def test_trailing_double_star(self) -> None:
        """path_matches_glob handles **/ prefix."""
        assert path_matches_glob("src/main.py", "**/src/main.py") is True
        assert path_matches_glob("project/src/main.py", "**/src/main.py") is True

    def test_double_star_prefix(self) -> None:
        """path_matches_glob handles **/ prefix with suffix."""
        assert path_matches_glob("foo/bar/file.py", "**/bar/file.py") is True

    def test_no_match_different_depth(self) -> None:
        """path_matches_glob requires matching depth."""
        assert path_matches_glob("src/a/b.py", "src/b.py") is False

    def test_empty_pattern(self) -> None:
        """path_matches_glob handles empty pattern (returns False)."""
        # Empty pattern doesn't match anything - no pattern to match against
        assert path_matches_glob("anything", "") is False


class TestParseFrontmatterFromContent:
    """Tests for parse_frontmatter_from_content helper."""

    def test_no_frontmatter(self) -> None:
        """parse_frontmatter_from_content returns empty dict if no frontmatter."""
        content = "# Just markdown\nSome text."
        fm, body = parse_frontmatter_from_content(content)
        assert fm == {}
        assert body == content

    def test_with_frontmatter(self) -> None:
        """parse_frontmatter_from_content parses YAML frontmatter."""
        content = """---
name: test
description: A test skill
allowed-tools:
  - Read
  - Glob
---
# Skill Content
This is the skill."""
        fm, body = parse_frontmatter_from_content(content)
        assert fm["name"] == "test"
        assert fm["description"] == "A test skill"
        assert fm["allowed-tools"] == ["Read", "Glob"]
        assert "# Skill Content" in body
        assert "This is the skill." in body

    def test_invalid_yaml(self) -> None:
        """parse_frontmatter_from_content handles invalid YAML gracefully."""
        content = """---
name: test
  invalid: yaml
---
Content"""
        fm, body = parse_frontmatter_from_content(content)
        # Should return empty dict on YAML parse error
        assert body == content
