"""
Tests for skills/tool.py - SkillTool wrapper.
"""

from __future__ import annotations

import pytest

from src.claude_code.skills.definition import SkillDefinition, SkillSource, ToolUseContext
from src.claude_code.skills.executor import SkillExecutor
from src.claude_code.skills.registry import SkillRegistry
from src.claude_code.skills.tool import (
    SkillTool,
    SkillToolResult,
    create_skill_tool,
    create_skill_tools_from_registry,
)


@pytest.fixture
def skill() -> SkillDefinition:
    """Create a sample skill."""
    return SkillDefinition(
        name="simplify",
        description="Simplify code",
        aliases=["improve", "clean"],
        argument_hint="[target]",
        allowed_tools=["Read", "Glob"],
        source=SkillSource.BUNDLED,
    )


@pytest.fixture
def skill_tool(skill: SkillDefinition) -> SkillTool:
    """Create a SkillTool."""
    return SkillTool(skill=skill)


class TestSkillToolResult:
    """Tests for SkillToolResult."""

    def test_defaults(self) -> None:
        """SkillToolResult has correct defaults."""
        result = SkillToolResult(skill_name="test", content="hello")
        assert result.success is True
        assert result.error is None
        assert result.tool_calls == []
        assert result.duration_ms == 0.0

    def test_to_content_blocks_success(self) -> None:
        """to_content_blocks returns text block on success."""
        result = SkillToolResult(skill_name="test", content="hello")
        blocks = result.to_content_blocks()
        assert len(blocks) == 1
        assert blocks[0]["type"] == "text"
        assert "hello" in blocks[0]["text"]

    def test_to_content_blocks_error(self) -> None:
        """to_content_blocks returns error message on failure."""
        result = SkillToolResult(
            skill_name="test",
            content="",
            success=False,
            error="skill not found",
        )
        blocks = result.to_content_blocks()
        assert len(blocks) == 1
        assert "error" in blocks[0]["text"].lower()


class TestSkillToolProperties:
    """Tests for SkillTool properties."""

    def test_name(self, skill_tool: SkillTool) -> None:
        """name returns skill name."""
        assert skill_tool.name == "simplify"

    def test_description(self, skill_tool: SkillTool) -> None:
        """description includes base description and argument hint."""
        desc = skill_tool.description
        assert "Simplify code" in desc
        assert "[target]" in desc

    def test_description_without_hint(self, skill: SkillDefinition) -> None:
        """description is just base without argument hint."""
        skill.argument_hint = None
        tool = SkillTool(skill=skill)
        assert "Simplify code" in tool.description

    def test_input_schema(self, skill_tool: SkillTool) -> None:
        """input_schema returns the JSON schema."""
        schema = skill_tool.input_schema
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "skill" in schema["properties"]
        assert "args" in schema["properties"]
        assert "required" in schema
        assert "skill" in schema["required"]

    def test_input_schema_without_args(self, skill: SkillDefinition) -> None:
        """input_schema omits args when no argument_hint."""
        skill.argument_hint = None
        tool = SkillTool(skill=skill)
        schema = tool.input_schema
        assert "args" not in schema["properties"]

    def test_get_schema(self, skill_tool: SkillTool) -> None:
        """get_schema returns tool schema with name, description, and input_schema."""
        schema = skill_tool.get_schema()
        assert schema["name"] == "simplify"
        assert "description" in schema
        assert "input_schema" in schema
        assert schema["input_schema"] == skill_tool.input_schema

    def test_aliases(self, skill_tool: SkillTool) -> None:
        """aliases returns skill aliases."""
        assert "improve" in skill_tool.aliases
        assert "clean" in skill_tool.aliases

    def test_always_load(self, skill_tool: SkillTool) -> None:
        """always_load returns False."""
        assert skill_tool.always_load is False

    def test_repr(self, skill_tool: SkillTool) -> None:
        """__repr__ includes skill name."""
        r = repr(skill_tool)
        assert "simplify" in r


class TestSkillToolExecute:
    """Tests for SkillTool.execute."""

    @pytest.mark.asyncio
    async def test_execute_self_skill(self, skill_tool: SkillTool) -> None:
        """execute uses self.skill when skill_name matches."""
        skill_tool.skill._loaded = True
        skill_tool.skill.instructions = "Review and simplify."
        result = await skill_tool.execute({"skill": "simplify"})
        assert result.success is True
        assert "simplify" in result.content.lower()

    @pytest.mark.asyncio
    async def test_execute_skill_not_found(self, skill_tool: SkillTool) -> None:
        """execute returns error when skill not found in registry."""
        result = await skill_tool.execute({"skill": "__nonexistent__"})
        assert result.success is False
        assert "not found" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_execute_with_args(self, skill: SkillDefinition) -> None:
        """execute passes skill_args to executor."""
        captured_args: dict = {}

        class TestExecutor(SkillExecutor):
            async def execute(
                self, skill: SkillDefinition, args: dict, context: ToolUseContext
            ):
                captured_args.update(args)
                return await super().execute(skill, args, context)

        skill._loaded = True
        skill.instructions = "Test"
        tool = SkillTool(skill=skill, executor=TestExecutor())
        await tool.execute({"skill": "simplify", "args": "main.py"})
        assert captured_args.get("skill_args") == "main.py"


class TestSkillToolExecuteSync:
    """Tests for SkillTool.execute_sync."""

    def test_execute_sync(self, skill_tool: SkillTool) -> None:
        """execute_sync wraps async execute."""
        skill_tool.skill._loaded = True
        skill_tool.skill.instructions = "Test"
        result = skill_tool.execute_sync({"skill": "simplify"})
        assert result.success is True


class TestSkillToolFactory:
    """Tests for SkillTool factory functions."""

    def test_create_skill_tool(self, skill: SkillDefinition) -> None:
        """create_skill_tool creates SkillTool instance."""
        tool = create_skill_tool(skill)
        assert tool.name == "simplify"
        assert tool.skill is skill

    def test_create_skill_tool_with_executor(self, skill: SkillDefinition) -> None:
        """create_skill_tool accepts executor."""
        executor = SkillExecutor()
        tool = create_skill_tool(skill, executor=executor)
        assert tool.executor is executor

    def test_create_skill_tools_from_registry(self) -> None:
        """create_skill_tools_from_registry creates tools for user-invocable skills."""
        from src.claude_code.skills.builtin import (
            clear_bundled_skills,
            init_bundled_skills,
            register_all_bundled_skills_from_registry,
        )

        clear_bundled_skills()
        init_bundled_skills()
        reg = SkillRegistry()

        register_all_bundled_skills_from_registry(reg)

        tools = create_skill_tools_from_registry(reg)
        assert len(tools) > 0
        names = {t.name for t in tools}
        assert "simplify" in names
        assert "verify" in names

        clear_bundled_skills()
