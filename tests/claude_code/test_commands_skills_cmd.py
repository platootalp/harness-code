"""
Tests for skills command.
"""

from __future__ import annotations

import pytest

from claude_code.commands.base import CommandResult, CommandType
from claude_code.commands.skills_cmd import SkillsCommand


class MockSkill:
    """Mock skill definition."""

    def __init__(
        self,
        name: str,
        description: str = "",
        source: str = "project",
        argument_hint: str | None = None,
    ) -> None:
        self.name = name
        self.description = description
        self.source = source
        self.argument_hint = argument_hint


class MockSkillRegistry:
    """Mock skill registry."""

    def __init__(self, skills: list) -> None:
        self._skills = skills

    def list_user_invocable(self) -> list:
        return self._skills


class TestSkillsCommand:
    """Tests for SkillsCommand."""

    @pytest.mark.asyncio
    async def test_skills_no_skills(self) -> None:
        """Test skills command with no skills."""
        cmd = SkillsCommand()
        result = await cmd.execute("", {})
        assert isinstance(result, CommandResult)
        assert result.type == "text"
        assert "no skills found" in result.value.lower()

    @pytest.mark.asyncio
    async def test_skills_with_skills(self) -> None:
        """Test skills command displays skills."""
        cmd = SkillsCommand()
        skills = [
            MockSkill("refactor", "Refactor code", "project"),
            MockSkill("review", "Review code changes", "user"),
        ]

        result = await cmd.execute(
            "",
            {"skill_registry": MockSkillRegistry(skills)},
        )
        assert isinstance(result, CommandResult)
        assert result.type == "text"
        assert "refactor" in result.value
        assert "review" in result.value
        assert "Project Skills" in result.value
        assert "User Skills" in result.value

    @pytest.mark.asyncio
    async def test_skills_with_filter(self) -> None:
        """Test skills command filters by search term."""
        cmd = SkillsCommand()
        skills = [
            MockSkill("refactor", "Refactor code"),
            MockSkill("review", "Review code changes"),
        ]

        result = await cmd.execute(
            "refactor",
            {"skill_registry": MockSkillRegistry(skills)},
        )
        assert isinstance(result, CommandResult)
        assert "refactor" in result.value
        assert "Review" not in result.value or "refactor" in result.value.lower()

    @pytest.mark.asyncio
    async def test_skills_filter_no_match(self) -> None:
        """Test skills command with no matching filter."""
        cmd = SkillsCommand()
        skills = [
            MockSkill("refactor", "Refactor code"),
        ]

        result = await cmd.execute(
            "nonexistent",
            {"skill_registry": MockSkillRegistry(skills)},
        )
        assert isinstance(result, CommandResult)
        assert "no skills found" in result.value.lower()

    @pytest.mark.asyncio
    async def test_skills_shows_argument_hint(self) -> None:
        """Test that argument hints are shown for skills."""
        cmd = SkillsCommand()
        skills = [
            MockSkill(
                "git-commit",
                "Create a git commit",
                argument_hint="<message>",
            ),
        ]

        result = await cmd.execute(
            "",
            {"skill_registry": MockSkillRegistry(skills)},
        )
        assert isinstance(result, CommandResult)
        assert "<message>" in result.value

    def test_skills_metadata(self) -> None:
        """Test skills command metadata."""
        cmd = SkillsCommand()
        assert cmd.name == "skills"
        assert cmd.description == "List available skills"
        assert cmd.command_type == CommandType.LOCAL_JSX
        assert cmd.source == "builtin"

    def test_skills_get_help(self) -> None:
        """Test get_help() method."""
        cmd = SkillsCommand()
        help_text = cmd.get_help()
        assert "/skills" in help_text


class TestSkillsCommandRegistry:
    """Tests for skills command registry functions."""

    def test_get_all_commands(self) -> None:
        """Test get_all_commands returns skills command."""
        from claude_code.commands.skills_cmd import get_all_commands

        commands = get_all_commands()
        assert isinstance(commands, list)
        assert len(commands) == 1
        assert commands[0].name == "skills"
