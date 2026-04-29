"""Command registry for Claude Code slash commands.

This module provides the central command registry that stores and manages
all available commands. It supports:
- Registration of commands by name and aliases
- Lookup by exact name or alias
- Filtering by availability and enabled state
- Source tracking (builtin, plugin, bundled, mcp)

TypeScript equivalent: src/commands.ts Command registry + builtInCommandNames
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .base import BaseCommand, CommandType

if TYPE_CHECKING:
    pass


@dataclass
class CommandFilter:
    """Filter criteria for listing commands."""

    source: str | None = None  # Filter by source (builtin, plugin, bundled, mcp)
    command_type: CommandType | None = None  # Filter by execution type
    include_hidden: bool = False  # Include hidden commands
    enabled_only: bool = True  # Only include enabled commands
    auth_type: str | None = None  # Filter by availability


@dataclass
class CommandRegistry:
    """Central registry for all slash commands.

    Provides registration, lookup, and filtering of commands.

    Attributes:
        _commands: Internal dict mapping command name -> BaseCommand instance.
        _name_index: Secondary index mapping all names (name + aliases) -> command.
    """

    _commands: dict[str, BaseCommand] = field(default_factory=dict)
    _name_index: dict[str, BaseCommand] = field(default_factory=dict)

    def register(self, command: BaseCommand) -> None:
        """Register a command.

        Args:
            command: The command instance to register.

        Raises:
            ValueError: If a command with the same name is already registered.
        """
        # Rebuild _all_names to pick up any post-init changes
        command._all_names = {command.name, *command.aliases}

        if command.name in self._commands:
            raise ValueError(f"Command already registered: {command.name}")

        self._commands[command.name] = command

        # Index all names (name + aliases)
        for name in command._all_names:
            if name in self._name_index:
                raise ValueError(f"Command name conflict: {name}")
            self._name_index[name] = command

    def unregister(self, name: str) -> bool:
        """Unregister a command by name.

        Args:
            name: The command name (not alias) to unregister.

        Returns:
            True if the command was found and removed, False otherwise.
        """
        command = self._commands.pop(name, None)
        if command is None:
            return False

        for n in command._all_names:
            self._name_index.pop(n, None)

        return True

    def get(self, name: str) -> BaseCommand | None:
        """Get a command by name or alias.

        Args:
            name: The command name or alias to look up.

        Returns:
            The command instance, or None if not found.
        """
        return self._name_index.get(name)

    def get_by_name(self, name: str) -> BaseCommand | None:
        """Get a command by exact name (not alias).

        Args:
            name: The command name to look up.

        Returns:
            The command instance, or None if not found.
        """
        return self._commands.get(name)

    def has(self, name: str) -> bool:
        """Check if a command is registered (by name or alias).

        Args:
            name: The command name or alias to check.

        Returns:
            True if the command is registered.
        """
        return name in self._name_index

    def list_all(self) -> list[BaseCommand]:
        """List all registered commands.

        Returns:
            List of all command instances.
        """
        return list(self._commands.values())

    def list_names(self) -> list[str]:
        """List all command names (not aliases).

        Returns:
            List of all primary command names.
        """
        return list(self._commands.keys())

    def list_filtered(self, filter_fn: Callable[[BaseCommand], bool]) -> list[BaseCommand]:
        """List commands matching a filter function.

        Args:
            filter_fn: Function that returns True for commands to include.

        Returns:
            List of matching command instances.
        """
        return [cmd for cmd in self._commands.values() if filter_fn(cmd)]

    def filter_commands(
        self,
        filter: CommandFilter | None = None,
    ) -> list[BaseCommand]:
        """Filter commands by various criteria.

        Args:
            filter: Optional filter criteria. Defaults to CommandFilter().

        Returns:
            List of matching command instances.
        """
        if filter is None:
            filter = CommandFilter()

        result: list[BaseCommand] = []
        for cmd in self._commands.values():
            # Source filter
            if filter.source is not None and cmd.source != filter.source:
                continue

            # Command type filter
            if filter.command_type is not None and cmd.command_type != filter.command_type:
                continue

            # Hidden filter
            if not filter.include_hidden and cmd.is_hidden:
                continue

            # Enabled filter
            if filter.enabled_only and not cmd.check_enabled():
                continue

            # Auth type filter
            if filter.auth_type is not None and not cmd.check_availability(filter.auth_type):
                continue

            result.append(cmd)

        return result

    def get_builtin_names(self) -> set[str]:
        """Get the set of all builtin command names and aliases.

        Returns:
            Set of all builtin command names and aliases.
        """
        result: set[str] = set()
        for cmd in self._commands.values():
            if cmd.source == "builtin":
                result.update(cmd._all_names)
        return result

    def clear(self) -> None:
        """Clear all registered commands."""
        self._commands.clear()
        self._name_index.clear()

    def __len__(self) -> int:
        """Return the number of registered commands."""
        return len(self._commands)

    def __contains__(self, name: str) -> bool:
        """Check if a command is registered (in operator).

        Supports both 'in' operator and 'name in registry'.
        """
        return name in self._name_index

    def __iter__(self):
        """Iterate over command names."""
        return iter(self._commands)


# =============================================================================
# Global Registry Instance
# =============================================================================


# Global registry instance for built-in commands
_builtin_registry: CommandRegistry = CommandRegistry()


def get_builtin_registry() -> CommandRegistry:
    """Get the global builtin command registry.

    Returns:
        The global CommandRegistry instance for builtin commands.
    """
    return _builtin_registry


def register_builtin(command: BaseCommand) -> None:
    """Register a command with the global builtin registry.

    Args:
        command: The command instance to register.
    """
    _builtin_registry.register(command)


def get_builtin_command(name: str) -> BaseCommand | None:
    """Get a builtin command by name or alias.

    Args:
        name: The command name or alias.

    Returns:
        The command instance, or None if not found.
    """
    return _builtin_registry.get(name)


def list_builtin_commands() -> list[BaseCommand]:
    """List all builtin commands.

    Returns:
        List of all builtin command instances.
    """
    return _builtin_registry.list_all()
