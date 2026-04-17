"""MCP Server - exposes local capabilities via FastMCP."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable

from .types import MCPTool, MCPResource, MCPResourceResult


class MCPServer:
    """
    MCP Server - exposes local capabilities via FastMCP.

    Provides a decorator-based interface for registering tools, resources,
    and prompts that can be consumed by MCP clients.

    Example:
        mcpserver = MCPServer(name="local")

        @mcpserver.tool()
        async def local_bash(args: dict) -> dict:
            return {"result": "hello"}

        @mcpserver.resource("file://{path}")
        async def file_resource(path: str) -> str:
            return open(path).read()
    """

    def __init__(self, name: str = "local"):
        self.name = name
        self._tools: dict[str, Callable] = {}
        self._resources: dict[str, Callable] = {}
        self._prompts: dict[str, Callable] = {}
        self._running = False

    def tool(
        self,
        name: str | None = None,
        description: str | None = None,
    ) -> Callable:
        """
        Decorator to register a tool.

        Usage:
            @mcpserver.tool(name="local_bash")
            async def local_bash(args: dict) -> dict:
                return {"result": "ok"}
        """
        def decorator(func: Callable) -> Callable:
            tool_name = name or func.__name__
            self._tools[tool_name] = func
            return func
        return decorator

    def resource(self, uri_pattern: str) -> Callable:
        """
        Decorator to register a resource.

        Usage:
            @mcpserver.resource("file://{path}")
            async def file_resource(path: str) -> str:
                return open(path).read()
        """
        def decorator(func: Callable) -> Callable:
            self._resources[uri_pattern] = func
            return func
        return decorator

    def prompt(self, name: str | None = None) -> Callable:
        """
        Decorator to register a prompt template.

        Usage:
            @mcpserver.prompt(name="system_prompt")
            async def system_prompt() -> str:
                return "You are a helpful assistant."
        """
        def decorator(func: Callable) -> Callable:
            prompt_name = name or func.__name__
            self._prompts[prompt_name] = func
            return func
        return decorator

    def list_tools(self) -> list[MCPTool]:
        """List all registered tools as MCPTool definitions."""
        tools: list[MCPTool] = []
        for tool_name, func in self._tools.items():
            doc = (func.__doc__ or "").strip().split("\n")[0]
            # Try to infer input schema from type hints
            schema = self._infer_schema(func)
            tools.append(MCPTool(
                name=tool_name,
                description=doc,
                input_schema=schema,
            ))
        return tools

    def _infer_schema(self, func: Callable) -> dict[str, Any]:
        """Infer JSON Schema from function type hints."""
        schema: dict[str, Any] = {"type": "object", "properties": {}}
        annotations = getattr(func, "__annotations__", {})
        for param_name, param_type in annotations.items():
            if param_name in ("return", "self", "cls"):
                continue
            type_str = str(param_type)
            if "str" in type_str.lower():
                json_type = "string"
            elif "int" in type_str.lower() or "float" in type_str.lower():
                json_type = "number"
            elif "bool" in type_str.lower():
                json_type = "boolean"
            else:
                json_type = "string"
            schema["properties"][param_name] = {"type": json_type}
        return schema

    async def call_tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        """
        Call a registered tool by name.

        Args:
            name: Tool name.
            args: Tool arguments as dict.

        Returns:
            Tool execution result.
        """
        if name not in self._tools:
            raise KeyError(f"Tool not found: {name}")
        func = self._tools[name]
        if asyncio.iscoroutinefunction(func):
            return await func(args)
        return func(args)

    async def read_resource(self, uri: str) -> MCPResourceResult:
        """
        Read a resource by URI, matching against registered resource patterns.

        Args:
            uri: Resource URI (e.g., "file:///path/to/file").

        Returns:
            MCPResourceResult with content.
        """
        import re

        for pattern, handler in self._resources.items():
            # Convert FastMCP pattern to regex
            # e.g., "file://{path}" -> "file://(?P<path>[^/]+)"
            regex_pattern = re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", pattern)
            match = re.fullmatch(regex_pattern, uri)
            if match:
                kwargs = match.groupdict()
                if asyncio.iscoroutinefunction(handler):
                    content = await handler(**kwargs)
                else:
                    content = handler(**kwargs)
                return MCPResourceResult(uri=uri, content=str(content))

        raise KeyError(f"Resource not found: {uri}")

    def list_resources(self) -> list[MCPResource]:
        """List all registered resource patterns."""
        return [
            MCPResource(
                uri=pattern,
                name=pattern.split("/")[-1].split("{")[0] or pattern,
                description=None,
            )
            for pattern in self._resources
        ]

    def list_prompts(self) -> list[str]:
        """List all registered prompt names."""
        return list(self._prompts.keys())

    async def get_prompt(self, name: str, args: dict[str, Any] | None = None) -> str:
        """Get a prompt template by name, optionally with arguments."""
        if name not in self._prompts:
            raise KeyError(f"Prompt not found: {name}")
        func = self._prompts[name]
        args = args or {}
        if asyncio.iscoroutinefunction(func):
            return await func(**args)
        return func(**args)

    def get_tools(self) -> list[MCPTool]:
        """Alias for list_tools()."""
        return self.list_tools()
