"""
Tests for commands/base.py - Base command classes.
"""

from __future__ import annotations

import pytest
from claude_code.commands.base import (
    Availability,
    BaseCommand,
    CommandResult,
    CommandType,
    PromptCommand,
)


class TestCommandType:
    """Tests for CommandType enum."""

    def test_values(self) -> None:
        """Test enum values."""
        assert CommandType.PROMPT.value == "prompt"
        assert CommandType.LOCAL.value == "local"
        assert CommandType.LOCAL_JSX.value == "local-jsx"

    def test_from_string(self) -> None:
        """Test creating from string value."""
        assert CommandType("prompt") == CommandType.PROMPT
        assert CommandType("local") == CommandType.LOCAL
        assert CommandType("local-jsx") == CommandType.LOCAL_JSX


class TestAvailability:
    """Tests for Availability enum."""

    def test_values(self) -> None:
        """Test enum values."""
        assert Availability.CLAUDE_AI.value == "claude-ai"
        assert Availability.CONSOLE.value == "console"
        assert Availability.ALL.value == "all"

    def test_from_string(self) -> None:
        """Test creating from string value."""
        assert Availability("claude-ai") == Availability.CLAUDE_AI
        assert Availability("console") == Availability.CONSOLE
        assert Availability("all") == Availability.ALL


class TestCommandResult:
    """Tests for CommandResult dataclass."""

    def test_create_text_result(self) -> None:
        """Test creating a text result."""
        result = CommandResult(type="text", value="Hello world")
        assert result.type == "text"
        assert result.value == "Hello world"
        assert result.content is None
        assert result.node is None

    def test_create_content_result(self) -> None:
        """Test creating a content result."""
        content = [{"type": "text", "text": "Hello"}]
        result = CommandResult(type="content", content=content)
        assert result.type == "content"
        assert result.value is None
        assert result.content == content
        assert result.node is None

    def test_create_jsx_result(self) -> None:
        """Test creating a JSX result."""
        node = {"type": "div", "children": []}
        result = CommandResult(type="jsx", node=node)
        assert result.type == "jsx"
        assert result.value is None
        assert result.content is None
        assert result.node == node

    def test_default_values(self) -> None:
        """Test default values."""
        result = CommandResult(type="text")
        assert result.value is None
        assert result.content is None
        assert result.node is None


class TestBaseCommand:
    """Tests for BaseCommand abstract class."""

    def test_create_concrete_command(self) -> None:
        """Test creating a concrete command implementation."""
        class TestCommand(BaseCommand):
            async def execute(self, args: str, context: dict) -> CommandResult:
                return CommandResult(type="text", value=f"Args: {args}")

        cmd = TestCommand(
            name="test",
            description="A test command",
            aliases=["t", "testing"],
        )

        assert cmd.name == "test"
        assert cmd.description == "A test command"
        assert cmd.aliases == ["t", "testing"]
        assert cmd.command_type == CommandType.LOCAL
        assert cmd.is_hidden is False
        assert cmd.source == "builtin"
        assert cmd._all_names == {"test", "t", "testing"}

    def test_default_availability(self) -> None:
        """Test default availability is ALL."""
        class TestCommand(BaseCommand):
            async def execute(self, args: str, context: dict) -> CommandResult:
                return CommandResult(type="text")

        cmd = TestCommand(name="test", description="Test")
        assert cmd.availability == [Availability.ALL.value]

    def test_get_help(self) -> None:
        """Test get_help returns formatted help text."""
        class TestCommand(BaseCommand):
            async def execute(self, args: str, context: dict) -> CommandResult:
                return CommandResult(type="text")

        cmd = TestCommand(
            name="mycmd",
            description="Does something useful",
            argument_hint="<arg>",
        )
        assert cmd.get_help() == "/mycmd <arg>: Does something useful"

    def test_get_help_no_hint(self) -> None:
        """Test get_help without argument hint."""
        class TestCommand(BaseCommand):
            async def execute(self, args: str, context: dict) -> CommandResult:
                return CommandResult(type="text")

        cmd = TestCommand(name="mycmd", description="Does something")
        assert cmd.get_help() == "/mycmd: Does something"

    def test_check_availability_all(self) -> None:
        """Test availability check with ALL."""
        class TestCommand(BaseCommand):
            async def execute(self, args: str, context: dict) -> CommandResult:
                return CommandResult(type="text")

        cmd = TestCommand(name="test", description="Test")
        assert cmd.check_availability("claude-ai") is True
        assert cmd.check_availability("console") is True
        assert cmd.check_availability("unknown") is True

    def test_check_availability_specific(self) -> None:
        """Test availability check with specific type."""
        class TestCommand(BaseCommand):
            async def execute(self, args: str, context: dict) -> CommandResult:
                return CommandResult(type="text")

        cmd = TestCommand(
            name="test",
            description="Test",
            availability=[Availability.CLAUDE_AI.value],
        )
        assert cmd.check_availability("claude-ai") is True
        assert cmd.check_availability("console") is False

    def test_check_enabled_no_callback(self) -> None:
        """Test check_enabled with no callback returns True."""
        class TestCommand(BaseCommand):
            async def execute(self, args: str, context: dict) -> CommandResult:
                return CommandResult(type="text")

        cmd = TestCommand(name="test", description="Test")
        assert cmd.check_enabled() is True

    def test_check_enabled_with_callback(self) -> None:
        """Test check_enabled with callback."""
        class TestCommand(BaseCommand):
            async def execute(self, args: str, context: dict) -> CommandResult:
                return CommandResult(type="text")

        enabled = True
        cmd = TestCommand(
            name="test",
            description="Test",
            is_enabled=lambda: enabled,
        )
        assert cmd.check_enabled() is True
        enabled = False
        assert cmd.check_enabled() is False

    def test_execute_is_abstract(self) -> None:
        """Test that execute must be implemented."""
        with pytest.raises(TypeError):
            BaseCommand(name="test", description="Test")


class TestPromptCommand:
    """Tests for PromptCommand class."""

    def test_create_prompt_command(self) -> None:
        """Test creating a concrete prompt command."""
        class MyPromptCommand(PromptCommand):
            async def get_prompt_content(
                self,
                args: str,
                context: dict,
            ) -> str:
                return f"Prompt content: {args}"

        cmd = MyPromptCommand(
            name="myprompt",
            description="A prompt command",
        )
        assert cmd.name == "myprompt"
        assert cmd.command_type == CommandType.PROMPT

    def test_execute_returns_content(self) -> None:
        """Test execute returns content-type result."""
        class MyPromptCommand(PromptCommand):
            async def get_prompt_content(
                self,
                args: str,
                context: dict,
            ) -> str:
                return f"Generated: {args}"

        cmd = MyPromptCommand(name="test", description="Test")

        import asyncio

        result = asyncio.run(cmd.execute("hello", {}))
        assert result.type == "content"
        assert result.content is not None
        assert len(result.content) == 1
        assert result.content[0]["type"] == "text"
        assert result.content[0]["text"] == "Generated: hello"

    def test_prompt_command_is_abstract(self) -> None:
        """Test that get_prompt_content must be implemented."""
        with pytest.raises(TypeError):
            PromptCommand(name="test", description="Test")


class TestCommandIntegration:
    """Integration tests for command system."""

    def test_command_with_all_options(self) -> None:
        """Test command with all options configured."""
        class FullCommand(BaseCommand):
            async def execute(self, args: str, context: dict) -> CommandResult:
                return CommandResult(type="text", value=f"Done: {args}")

        enabled = True
        cmd = FullCommand(
            name="full",
            description="Full featured command",
            aliases=["f", "fullcmd"],
            argument_hint="<arg>",
            command_type=CommandType.LOCAL_JSX,
            availability=[Availability.CLAUDE_AI.value],
            is_hidden=True,
            immediate=True,
            supports_non_interactive=True,
            source="plugin",
            is_enabled=lambda: enabled,
        )

        assert cmd.name == "full"
        assert cmd._all_names == {"full", "f", "fullcmd"}
        assert cmd.argument_hint == "<arg>"
        assert cmd.command_type == CommandType.LOCAL_JSX
        assert cmd.check_availability("claude-ai") is True
        assert cmd.check_availability("console") is False
        assert cmd.check_enabled() is True
        assert cmd.is_hidden is True
        assert cmd.immediate is True
        assert cmd.supports_non_interactive is True
        assert cmd.source == "plugin"

    @pytest.mark.asyncio
    async def test_command_execute_with_context(self) -> None:
        """Test command can access context."""
        class ContextCommand(BaseCommand):
            async def execute(self, args: str, context: dict) -> CommandResult:
                model = context.get("model", "unknown")
                return CommandResult(
                    type="text",
                    value=f"Model: {model}, Args: {args}",
                )

        cmd = ContextCommand(name="ctx", description="Context test")
        result = await cmd.execute("test", {"model": "claude-opus-4-6"})

        assert result.type == "text"
        assert "claude-opus-4-6" in (result.value or "")
