"""Unit tests for tool registry module."""

import pytest

from mozi.core.tools.framework import Tool, ToolContext, ToolResult, ToolStatus
from mozi.core.tools.registry import (
    ToolNotFoundError,
    ToolRegistry,
)


class DummyTool(Tool):
    """Concrete implementation of Tool for testing."""

    def __init__(self, name: str = "dummy") -> None:
        super().__init__(name=name, description="A dummy tool")
        self.execute_called = False

    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute the dummy tool."""
        self.execute_called = True
        return ToolResult(status=ToolStatus.SUCCESS, output="done")


class TestToolRegistry:
    """Tests for ToolRegistry class."""

    def test_registry_starts_empty(self) -> None:
        """Test registry starts with no tools."""
        registry = ToolRegistry()
        assert registry.list_tools() == []

    def test_register_tool(self) -> None:
        """Test registering a tool."""
        registry = ToolRegistry()
        tool = DummyTool(name="test_tool")
        registry.register(tool)
        assert len(registry.list_tools()) == 1
        assert registry.list_tools()[0]["name"] == "test_tool"

    def test_register_duplicate_raises_error(self) -> None:
        """Test registering duplicate tool raises error."""
        registry = ToolRegistry()
        tool = DummyTool(name="test_tool")
        registry.register(tool)
        with pytest.raises(ValueError, match="already registered"):
            registry.register(tool)

    def test_unregister_tool(self) -> None:
        """Test unregistering a tool."""
        registry = ToolRegistry()
        tool = DummyTool(name="test_tool")
        registry.register(tool)
        registry.unregister("test_tool")
        assert len(registry.list_tools()) == 0

    def test_unregister_nonexistent_raises_error(self) -> None:
        """Test unregistering nonexistent tool raises error."""
        registry = ToolRegistry()
        with pytest.raises(ToolNotFoundError, match="not registered"):
            registry.unregister("nonexistent")

    def test_get_tool(self) -> None:
        """Test getting a tool by name."""
        registry = ToolRegistry()
        tool = DummyTool(name="test_tool")
        registry.register(tool)
        retrieved = registry.get("test_tool")
        assert retrieved is tool

    def test_get_nonexistent_raises_error(self) -> None:
        """Test getting nonexistent tool raises error."""
        registry = ToolRegistry()
        with pytest.raises(ToolNotFoundError, match="not registered"):
            registry.get("nonexistent")

    def test_list_tools_empty(self) -> None:
        """Test listing tools when registry is empty."""
        registry = ToolRegistry()
        assert registry.list_tools() == []

    def test_list_tools_multiple(self) -> None:
        """Test listing multiple tools."""
        registry = ToolRegistry()
        registry.register(DummyTool(name="tool1"))
        registry.register(DummyTool(name="tool2"))
        tools = registry.list_tools()
        assert len(tools) == 2
        assert {t["name"] for t in tools} == {"tool1", "tool2"}

    @pytest.mark.asyncio
    async def test_execute_tool(self) -> None:
        """Test executing a tool through registry."""
        registry = ToolRegistry()
        tool = DummyTool(name="test_tool")
        registry.register(tool)
        context = ToolContext(tool_name="test_tool")
        result = await registry.execute("test_tool", context)
        assert result.success is True
        assert tool.execute_called is True

    @pytest.mark.asyncio
    async def test_execute_nonexistent_raises_error(self) -> None:
        """Test executing nonexistent tool raises error."""
        registry = ToolRegistry()
        context = ToolContext(tool_name="nonexistent")
        with pytest.raises(ToolNotFoundError, match="not registered"):
            await registry.execute("nonexistent", context)
