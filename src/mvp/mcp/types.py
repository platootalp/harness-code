"""MCP shared type definitions."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MCPServerConfig:
    """MCP server configuration."""
    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] | None = None


@dataclass
class MCPTool:
    """MCP tool definition."""
    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPResource:
    """MCP resource definition."""
    uri: str
    name: str
    description: str | None = None


@dataclass
class MCPResourceResult:
    """Result from reading an MCP resource."""
    uri: str
    content: str
    mime_type: str | None = None


class MCPError(Exception):
    """MCP protocol error."""
    def __init__(self, code: int, message: str):
        self.code = code
        super().__init__(f"MCP error {code}: {message}")
