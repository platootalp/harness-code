"""Unit tests for BashTool."""

import pytest

from mozi.core.tools.builtin.bash import BashTool
from mozi.core.tools.framework import ToolContext, ToolStatus


class TestBashTool:
    """Tests for BashTool."""

    def test_bash_tool_initialization(self) -> None:
        """Test BashTool initializes correctly."""
        tool = BashTool()
        assert tool.name == "bash"
        assert tool.description == "Execute shell commands in a controlled environment"

    def test_bash_tool_schema(self) -> None:
        """Test BashTool schema includes command and timeout."""
        tool = BashTool()
        schema = tool.schema
        assert "command" in schema["parameters"]["properties"]
        assert "timeout" in schema["parameters"]["properties"]

    @pytest.mark.asyncio
    async def test_bash_tool_denied_insufficient_permission(self) -> None:
        """Test bash tool is denied with low permission level."""
        tool = BashTool()
        context = ToolContext(
            tool_name="bash",
            parameters={"command": "echo hello"},
            permission_level=2,
        )
        result = await tool.execute(context)
        assert result.status == ToolStatus.DENIED
        assert "Insufficient permission" in result.error

    @pytest.mark.asyncio
    async def test_bash_tool_blocks_dangerous_command(self) -> None:
        """Test bash tool blocks dangerous commands."""
        tool = BashTool()
        context = ToolContext(
            tool_name="bash",
            parameters={"command": "rm -rf /"},
            permission_level=3,
        )
        result = await tool.execute(context)
        assert result.status == ToolStatus.DENIED
        assert "dangerous pattern" in result.error.lower()

    @pytest.mark.asyncio
    async def test_bash_tool_blocks_dangerous_function(self) -> None:
        """Test bash tool blocks dangerous functions."""
        tool = BashTool()
        context = ToolContext(
            tool_name="bash",
            parameters={"command": "python -c 'eval(\"1+1\")'"},
            permission_level=3,
        )
        result = await tool.execute(context)
        assert result.status == ToolStatus.DENIED
        assert "security violations" in result.error.lower()

    @pytest.mark.asyncio
    async def test_bash_tool_executes_safe_command(self) -> None:
        """Test bash tool executes safe commands."""
        tool = BashTool()
        context = ToolContext(
            tool_name="bash",
            parameters={"command": "echo hello"},
            permission_level=3,
            timeout_seconds=30,
        )
        result = await tool.execute(context)
        assert result.status == ToolStatus.SUCCESS
        assert "hello" in result.output
