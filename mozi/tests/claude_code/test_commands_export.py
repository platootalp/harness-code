"""
Tests for export command.
"""

from __future__ import annotations

import os
import tempfile
from unittest.mock import MagicMock

import pytest

from claude_code.commands.base import CommandResult, CommandType
from claude_code.commands.export import ExportCommand


class MockContentBlock:
    """Mock content block."""

    def __init__(self, text: str = "") -> None:
        self.text = text


class MockMessage:
    """Mock message."""

    def __init__(self, role: str, content: str) -> None:
        self.role = MagicMock()
        self.role.value = role
        self.content_blocks = [MockContentBlock(content)]


class TestExportCommand:
    """Tests for ExportCommand."""

    @pytest.mark.asyncio
    async def test_export_empty_messages(self) -> None:
        """Test export with no messages."""
        cmd = ExportCommand()
        result = await cmd.execute("", {"messages": []})
        assert isinstance(result, CommandResult)
        assert "no conversation content" in result.value.lower()

    @pytest.mark.asyncio
    async def test_export_with_filename(self) -> None:
        """Test export to a specific filename."""
        cmd = ExportCommand()

        messages = [
            MockMessage("user", "Hello, world!"),
            MockMessage("assistant", "Hi there!"),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            result = await cmd.execute(
                "test-export.txt",
                {"messages": messages, "cwd": tmpdir},
            )
            assert isinstance(result, CommandResult)
            assert result.type == "text"
            assert "test-export.txt" in result.value
            assert "exported" in result.value.lower()

            # Verify file was created
            filepath = os.path.join(tmpdir, "test-export.txt")
            assert os.path.exists(filepath)
            with open(filepath, encoding="utf-8") as f:
                content = f.read()
            assert "Hello, world!" in content
            assert "Hi there!" in content

    @pytest.mark.asyncio
    async def test_export_adds_txt_extension(self) -> None:
        """Test that .txt extension is added if missing."""
        cmd = ExportCommand()

        messages = [MockMessage("user", "Test")]

        with tempfile.TemporaryDirectory() as tmpdir:
            result = await cmd.execute(
                "myfile",
                {"messages": messages, "cwd": tmpdir},
            )
            assert isinstance(result, CommandResult)
            assert "myfile.txt" in result.value

    @pytest.mark.asyncio
    async def test_export_generates_filename(self) -> None:
        """Test export generates filename from first prompt."""
        cmd = ExportCommand()

        messages = [MockMessage("user", "Fix the authentication bug")]

        with tempfile.TemporaryDirectory() as tmpdir:
            result = await cmd.execute(
                "",
                {"messages": messages, "cwd": tmpdir},
            )
            assert isinstance(result, CommandResult)
            assert "exported" in result.value.lower()
            # Should contain timestamp
            assert ".txt" in result.value

    @pytest.mark.asyncio
    async def test_export_format_roles(self) -> None:
        """Test that export formats different message roles correctly."""
        cmd = ExportCommand()

        messages = [
            MockMessage("user", "User message"),
            MockMessage("assistant", "Assistant message"),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            _result = await cmd.execute(
                "roles-test.txt",
                {"messages": messages, "cwd": tmpdir},
            )
            filepath = os.path.join(tmpdir, "roles-test.txt")
            with open(filepath, encoding="utf-8") as f:
                content = f.read()
            assert "## You" in content
            assert "## Claude" in content
            assert "User message" in content
            assert "Assistant message" in content

    def test_export_metadata(self) -> None:
        """Test export command metadata."""
        cmd = ExportCommand()
        assert cmd.name == "export"
        assert cmd.argument_hint == "[filename]"
        assert cmd.command_type == CommandType.LOCAL_JSX
        assert cmd.source == "builtin"

    def test_export_get_help(self) -> None:
        """Test get_help() method."""
        cmd = ExportCommand()
        help_text = cmd.get_help()
        assert "/export" in help_text


class TestExportCommandRegistry:
    """Tests for export command registry functions."""

    def test_get_all_commands(self) -> None:
        """Test get_all_commands returns export command."""
        from claude_code.commands.export import get_all_commands

        commands = get_all_commands()
        assert isinstance(commands, list)
        assert len(commands) == 1
        assert commands[0].name == "export"
