"""Base command classes and types for Claude Code commands.

This module provides the foundation for all slash commands:
- CommandType: Execution type enum (prompt, local, local-jsx)
- Availability: Where commands are available
- CommandResult: Result from command execution
- BaseCommand: Abstract base class for all commands
- PromptCommand: Command that expands to prompt content

TypeScript equivalent: src/commands.ts Command type
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class CommandType(StrEnum):
    """Command execution type."""

    PROMPT = "prompt"  # Expands to text sent to model
    LOCAL = "local"  # Executes locally, returns text
    LOCAL_JSX = "local-jsx"  # Renders UI component


class Availability(StrEnum):
    """Where command is available."""

    CLAUDE_AI = "claude-ai"  # Claude.ai subscriber only
    CONSOLE = "console"  # CLI console only
    ALL = "all"  # Everywhere


@dataclass
class CommandResult:
    """Result from command execution.

    Attributes:
        type: Result type - "text", "content", or "jsx".
        value: Text value or None for content/jsx results.
        content: Content blocks for content-type results.
        node: React node for JSX commands.
    """

    type: str  # "text", "content", "jsx"
    value: str | None = None
    content: list[dict[str, Any]] | None = None
    node: Any = None  # For JSX commands


@dataclass
class BaseCommand(ABC):
    """Base class for all commands.

    TypeScript equivalent: src/commands.ts Command interface

    Can be used either as:
    1. An ABC with explicit __init__ for complex initialization
    2. A dataclass with field defaults for simple commands

    Attributes:
        name: Command name (without leading slash).
        description: Human-readable description for help.
        aliases: Alternative names for the command.
        argument_hint: Hint for arguments shown in help.
        command_type: How the command executes.
        availability: List of availability contexts.
        is_hidden: Whether command is hidden from help.
        immediate: Execute without waiting for stop point.
        supports_non_interactive: Works in non-interactive mode.
        source: Source of the command (builtin, plugin, bundled, mcp).
        is_enabled: Optional callback to check if command is enabled.
    """

    # Basic metadata
    name: str
    description: str
    aliases: list[str] = field(default_factory=list)
    argument_hint: str | None = None

    # Execution type
    command_type: CommandType = CommandType.LOCAL

    # Availability
    availability: list[str] | None = None

    # Flags
    is_hidden: bool = False
    immediate: bool = False  # Execute without waiting for stop point
    supports_non_interactive: bool = False

    # Source tracking
    source: str = "builtin"  # builtin, plugin, bundled, mcp

    # Dynamic enable check
    is_enabled: Callable[[], bool] | None = None

    def __post_init__(self) -> None:
        # Build lookup set for aliases
        self._all_names: set[str] = {self.name, *self.aliases}
        # Normalize availability to [ALL.value] if None
        if self.availability is None:
            object.__setattr__(self, "availability", [Availability.ALL.value])

    @abstractmethod
    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the command with given arguments.

        Args:
            args: Raw argument string.
            context: Execution context (settings, state, etc.).

        Returns:
            CommandResult with output.
        """
        ...

    def get_help(self) -> str:
        """Get help text for this command."""
        hint = f" {self.argument_hint}" if self.argument_hint else ""
        return f"/{self.name}{hint}: {self.description}"

    def check_availability(self, auth_type: str) -> bool:
        """Check if command is available for given auth type.

        Args:
            auth_type: The auth type to check against.

        Returns:
            True if command is available.
        """
        if self.availability is None:
            return True
        if Availability.ALL.value in self.availability:
            return True
        return auth_type in self.availability

    def check_enabled(self) -> bool:
        """Check if command is enabled.

        Returns:
            True if command is enabled or no check is configured.
        """
        if self.is_enabled:
            return self.is_enabled()
        return True


@dataclass
class PromptCommand(BaseCommand, ABC):
    """Command that expands to prompt content sent to model.

    Prompt commands generate text that is sent to the AI model
    rather than executing locally or rendering a UI.
    """

    command_type: CommandType = field(default=CommandType.PROMPT, init=False)

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the prompt command.

        Generates prompt content and wraps it in a CommandResult
        with content type.
        """
        content = await self.get_prompt_content(args, context)
        return CommandResult(
            type="content",
            content=[{"type": "text", "text": content}],
        )

    @abstractmethod
    async def get_prompt_content(
        self,
        args: str,
        context: dict[str, Any],
    ) -> str:
        """Generate the prompt content.

        Args:
            args: Raw argument string.
            context: Execution context.

        Returns:
            The prompt content string to send to the model.
        """
        ...
