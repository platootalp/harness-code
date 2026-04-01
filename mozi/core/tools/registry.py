"""Tool registry - Central registration and execution management for tools."""

from typing import Any

from mozi.core.tools.framework import Tool, ToolContext, ToolResult


class ToolNotFoundError(Exception):
    """Raised when a requested tool is not found in the registry."""

    pass


class ToolExecutionError(Exception):
    """Raised when tool execution fails."""

    pass


class ToolRegistry:
    """Central registry for managing and executing tools.

    The registry maintains a collection of tools and provides
    methods to register, unregister, and execute them.
    """

    def __init__(self) -> None:
        """Initialize an empty tool registry."""
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool in the registry.

        Args:
            tool: Tool instance to register.

        Raises:
            ValueError: If a tool with the same name is already registered.
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")
        self._tools[tool.name] = tool

    def unregister(self, tool_name: str) -> None:
        """Unregister a tool from the registry.

        Args:
            tool_name: Name of the tool to unregister.

        Raises:
            ToolNotFoundError: If the tool is not found.
        """
        if tool_name not in self._tools:
            raise ToolNotFoundError(f"Tool '{tool_name}' is not registered")
        del self._tools[tool_name]

    def get(self, tool_name: str) -> Tool:
        """Get a tool by name.

        Args:
            tool_name: Name of the tool to retrieve.

        Returns:
            The requested tool.

        Raises:
            ToolNotFoundError: If the tool is not found.
        """
        if tool_name not in self._tools:
            raise ToolNotFoundError(f"Tool '{tool_name}' is not registered")
        return self._tools[tool_name]

    def list_tools(self) -> list[dict[str, Any]]:
        """List all registered tools.

        Returns:
            List of tool metadata dictionaries.
        """
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "version": tool.version,
                "schema": tool.schema,
            }
            for tool in self._tools.values()
        ]

    async def execute(
        self, tool_name: str, context: ToolContext
    ) -> ToolResult:
        """Execute a tool by name.

        Args:
            tool_name: Name of the tool to execute.
            context: Execution context.

        Returns:
            ToolResult from the execution.

        Raises:
            ToolNotFoundError: If the tool is not found.
            ToolExecutionError: If execution fails.
        """
        tool = self.get(tool_name)
        try:
            return await tool.execute(context)
        except Exception as e:
            raise ToolExecutionError(f"Tool '{tool_name}' execution failed: {e}") from e
