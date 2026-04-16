"""
Tests for BashTool.
"""

from __future__ import annotations

import asyncio
import tempfile
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from claude_code.tools.bash import (
    BashTool,
    BashToolOutput,
    is_search_or_read_bash_command,
)


@pytest.fixture
def bash_tool() -> BashTool:
    return BashTool()


@pytest.fixture
def mock_context() -> MagicMock:
    loop = asyncio.new_event_loop()
    ctx = MagicMock()
    ctx.abort_controller = loop
    return ctx


class TestBashTool:
    """Tests for BashTool."""

    def test_name(self, bash_tool: BashTool) -> None:
        assert bash_tool.name == "Bash"

    def test_input_schema(self, bash_tool: BashTool) -> None:
        schema = bash_tool.input_schema
        assert schema["type"] == "object"
        assert "command" in schema["required"]
        assert "command" in schema["properties"]
        assert "timeout" in schema["properties"]
        assert "working_directory" in schema["properties"]

    def test_is_concurrency_safe(self, bash_tool: BashTool) -> None:
        assert bash_tool.is_concurrency_safe({}) is False

    def test_to_auto_classifier_input(self, bash_tool: BashTool) -> None:
        result = bash_tool.to_auto_classifier_input({"command": "ls -la"})
        assert result == "ls -la"

    def test_get_path_cd(self, bash_tool: BashTool) -> None:
        path = bash_tool.get_path({"command": "cd /tmp"})
        assert path == "/tmp"

    def test_get_path_ls(self, bash_tool: BashTool) -> None:
        path = bash_tool.get_path({"command": "ls /home"})
        assert path == "/home"

    def test_get_path_relative(self, bash_tool: BashTool) -> None:
        path = bash_tool.get_path({"command": "cat file.txt"})
        assert path is None

    @pytest.mark.asyncio
    async def test_validate_input_missing_command(
        self, bash_tool: BashTool, mock_context: MagicMock
    ) -> None:
        result = await bash_tool.validate_input({}, mock_context)
        assert result is not True
        assert isinstance(result, tuple)
        assert result[2] == 400

    @pytest.mark.asyncio
    async def test_validate_input_empty_command(
        self, bash_tool: BashTool, mock_context: MagicMock
    ) -> None:
        result = await bash_tool.validate_input({"command": "  "}, mock_context)
        assert result is not True
        assert isinstance(result, tuple)
        assert result[2] == 400

    @pytest.mark.asyncio
    async def test_validate_input_non_string_command(
        self, bash_tool: BashTool, mock_context: MagicMock
    ) -> None:
        result = await bash_tool.validate_input({"command": 123}, mock_context)
        assert result is not True

    @pytest.mark.asyncio
    async def test_call_simple_command(
        self, bash_tool: BashTool, mock_context: MagicMock
    ) -> None:
        result = await bash_tool.call(
            {"command": "echo hello"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert isinstance(result.data, BashToolOutput)
        assert result.data.exit_code == 0
        assert "hello" in result.data.stdout

    @pytest.mark.asyncio
    async def test_call_with_timeout(
        self, bash_tool: BashTool, mock_context: MagicMock
    ) -> None:
        result = await bash_tool.call(
            {"command": "sleep 0.1", "timeout": 5000},
            mock_context,
            AsyncMock(),
            None,
        )
        assert isinstance(result.data, BashToolOutput)
        assert result.data.exit_code == 0

    @pytest.mark.asyncio
    async def test_call_duration_reported(
        self, bash_tool: BashTool, mock_context: MagicMock
    ) -> None:
        result = await bash_tool.call(
            {"command": "echo test"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result.data.duration_ms is not None
        assert result.data.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_call_with_working_directory(
        self, bash_tool: BashTool, mock_context: MagicMock
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = await bash_tool.call(
                {"command": "pwd", "working_directory": tmpdir},
                mock_context,
                AsyncMock(),
                None,
            )
            assert isinstance(result.data, BashToolOutput)
            assert result.data.exit_code == 0
            assert tmpdir in result.data.stdout

    @pytest.mark.asyncio
    async def test_call_command_not_found(
        self, bash_tool: BashTool, mock_context: MagicMock
    ) -> None:
        result = await bash_tool.call(
            {"command": "nonexistent_command_xyz"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert isinstance(result.data, BashToolOutput)
        assert result.data.exit_code != 0

    @pytest.mark.asyncio
    async def test_call_description(self, bash_tool: BashTool) -> None:
        desc = await bash_tool.description({"command": "git status"}, {})
        assert "git status" in desc or "execute" in desc.lower()

    @pytest.mark.asyncio
    async def test_call_prompt(self, bash_tool: BashTool) -> None:
        prompt = await bash_tool.prompt({})
        assert "Bash" in prompt
        assert "shell" in prompt.lower()


class TestBashToolHelpers:
    """Tests for BashTool helper functions."""

    def test_is_search_command_grep(self) -> None:
        result = is_search_or_read_bash_command("grep -r 'pattern' .")
        assert result["is_search"] is True

    def test_is_read_command_cat(self) -> None:
        result = is_search_or_read_bash_command("cat file.txt")
        assert result["is_read"] is True

    def test_is_list_command_ls(self) -> None:
        result = is_search_or_read_bash_command("ls -la")
        assert result["is_list"] is True

    def test_is_neutral_echo(self) -> None:
        result = is_search_or_read_bash_command("echo hello")
        assert result["is_search"] is False
        assert result["is_read"] is False
        assert result["is_list"] is False

    def test_mixed_commands(self) -> None:
        result = is_search_or_read_bash_command("ls | grep 'foo'")
        assert result["is_search"] is True
        assert result["is_list"] is True

    def test_invalid_command(self) -> None:
        result = is_search_or_read_bash_command("")
        assert result["is_search"] is False
        assert result["is_read"] is False
        assert result["is_list"] is False
