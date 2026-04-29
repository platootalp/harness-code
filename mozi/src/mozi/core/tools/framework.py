"""Tools framework - Base classes for tool implementation."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ToolStatus(Enum):
    """Status of tool execution."""

    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    DENIED = "denied"


@dataclass
class ToolContext:
    """Context passed to tools during execution.

    Attributes:
        tool_name: Name of the tool being executed.
        parameters: Parameters passed to the tool.
        working_directory: Current working directory.
        allowed_paths: List of paths the tool is allowed to access.
        permission_level: Permission level for the execution.
        timeout_seconds: Maximum execution time allowed.
        env_vars: Environment variables available to the tool.
    """

    tool_name: str
    parameters: dict[str, Any] = field(default_factory=dict)
    working_directory: str = ""
    allowed_paths: list[str] = field(default_factory=list)
    permission_level: int = 0
    timeout_seconds: int = 300
    env_vars: dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ToolResult:
    """Result of tool execution.

    Attributes:
        status: Execution status.
        output: Tool output data.
        error: Error message if failed.
        execution_time: Time taken to execute in seconds.
    """

    status: ToolStatus
    output: Any = None
    error: str | None = None
    execution_time: float = 0.0

    @property
    def success(self) -> bool:
        """Check if execution was successful."""
        return self.status == ToolStatus.SUCCESS


class Tool(ABC):
    """Abstract base class for all tools.

    Tools must implement the execute method and provide
    metadata about themselves.
    """

    def __init__(self, name: str, description: str, version: str = "1.0.0"):
        """Initialize the tool.

        Args:
            name: Unique name of the tool.
            description: Human-readable description.
            version: Tool version string.
        """
        self.name = name
        self.description = description
        self.version = version

    @abstractmethod
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute the tool with given context.

        Args:
            context: Execution context with parameters and permissions.

        Returns:
            ToolResult with execution outcome.
        """

    @property
    def schema(self) -> dict[str, Any]:
        """Return the JSON schema for this tool's parameters."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "parameters": {},
        }
