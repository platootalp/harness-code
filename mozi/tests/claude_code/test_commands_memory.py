"""
Tests for memory command.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from claude_code.commands.base import CommandResult, CommandType
from claude_code.commands.memory import MemoryCommand


class TestMemoryCommand:
    """Tests for MemoryCommand."""

    @pytest.mark.asyncio
    async def test_memory_no_memory_paths(self) -> None:
        """Test memory command with no memory paths."""
        cmd = MemoryCommand()
        result = await cmd.execute("", {})
        assert isinstance(result, CommandResult)
        assert result.type == "text"
        assert "no memory files" in result.value.lower()

    @pytest.mark.asyncio
    async def test_memory_file_not_found(self) -> None:
        """Test memory command with non-existent file."""
        cmd = MemoryCommand()
        result = await cmd.execute(
            "",
            {"memory_paths": ["/nonexistent/path.md"]},
        )
        assert isinstance(result, CommandResult)
        assert "file not found" in result.value.lower()

    @pytest.mark.asyncio
    async def test_memory_shows_file_content(self) -> None:
        """Test memory command displays file content."""
        cmd = MemoryCommand()

        with tempfile.TemporaryDirectory() as tmpdir:
            mem_file = os.path.join(tmpdir, "memory.md")
            with open(mem_file, "w", encoding="utf-8") as f:
                f.write("# My Memory\n\nThis is my memory content.")

            result = await cmd.execute(
                "",
                {"memory_paths": [mem_file]},
            )
            assert isinstance(result, CommandResult)
            assert "memory.md" in result.value
            assert "My Memory" in result.value
            assert "This is my memory content" in result.value

    @pytest.mark.asyncio
    async def test_memory_filter_by_target(self) -> None:
        """Test memory command filters by target file."""
        cmd = MemoryCommand()

        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = os.path.join(tmpdir, "memory1.md")
            file2 = os.path.join(tmpdir, "memory2.md")

            with open(file1, "w", encoding="utf-8") as f:
                f.write("# Memory 1")
            with open(file2, "w", encoding="utf-8") as f:
                f.write("# Memory 2")

            result = await cmd.execute(
                "memory1",
                {"memory_paths": [file1, file2]},
            )
            assert isinstance(result, CommandResult)
            assert "Memory 1" in result.value
            assert "Memory 2" not in result.value

    @pytest.mark.asyncio
    async def test_memory_target_not_found(self) -> None:
        """Test memory command with non-matching target."""
        cmd = MemoryCommand()

        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = os.path.join(tmpdir, "memory.md")
            with open(file1, "w", encoding="utf-8") as f:
                f.write("# Memory")

            result = await cmd.execute(
                "nonexistent",
                {"memory_paths": [file1]},
            )
            assert isinstance(result, CommandResult)
            assert "memory file not found" in result.value.lower()

    @pytest.mark.asyncio
    async def test_memory_truncates_long_content(self) -> None:
        """Test that long memory content is truncated."""
        cmd = MemoryCommand()

        with tempfile.TemporaryDirectory() as tmpdir:
            mem_file = os.path.join(tmpdir, "long-memory.md")
            with open(mem_file, "w", encoding="utf-8") as f:
                f.write("A" * 1000)

            result = await cmd.execute(
                "",
                {"memory_paths": [mem_file]},
            )
            assert isinstance(result, CommandResult)
            assert "truncated" in result.value.lower()

    def test_memory_metadata(self) -> None:
        """Test memory command metadata."""
        cmd = MemoryCommand()
        assert cmd.name == "memory"
        assert cmd.description == "Edit Claude memory files"
        assert cmd.command_type == CommandType.LOCAL_JSX
        assert cmd.source == "builtin"

    def test_memory_get_help(self) -> None:
        """Test get_help() method."""
        cmd = MemoryCommand()
        help_text = cmd.get_help()
        assert "/memory" in help_text


class TestMemoryCommandRegistry:
    """Tests for memory command registry functions."""

    def test_get_all_commands(self) -> None:
        """Test get_all_commands returns memory command."""
        from claude_code.commands.memory import get_all_commands

        commands = get_all_commands()
        assert isinstance(commands, list)
        assert len(commands) == 1
        assert commands[0].name == "memory"
