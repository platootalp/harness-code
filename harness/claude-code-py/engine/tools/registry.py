"""
Tool registry for managing and looking up tools.

This module provides the ToolRegistry class which manages all available tools,
supports registration by name/alias, and provides lookup and filtering
capabilities.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..models.tool import BaseTool


# =============================================================================
# Tool Registry
# =============================================================================


class ToolRegistry:
    """Registry for managing available tools.

    The registry maintains a collection of tools indexed by name and alias,
    supporting efficient lookup and filtering operations.

    Attributes:
        _tools: Internal mapping from tool name to tool instance.
        _alias_map: Mapping from alias names to tool names.
    """

    def __init__(self) -> None:
        """Initialize an empty tool registry."""
        self._tools: dict[str, BaseTool] = {}
        self._alias_map: dict[str, str] = {}

    # -------------------------------------------------------------------------
    # Registration
    # -------------------------------------------------------------------------

    def register(self, tool: BaseTool) -> None:
        """Register a tool by its name.

        Args:
            tool: The tool instance to register.

        Raises:
            ValueError: If a tool with the same name is already registered.
        """
        name = tool.name
        if name in self._tools:
            raise ValueError(f"Tool already registered: {name}")
        self._tools[name] = tool
        self._register_aliases(tool)

    def register_alias(self, tool_name: str, alias: str) -> None:
        """Register an alias for an existing tool.

        Args:
            tool_name: The name of the tool to alias.
            alias: The alias name to register.

        Raises:
            KeyError: If the tool name is not registered.
            ValueError: If the alias is already registered.
        """
        if tool_name not in self._tools:
            raise KeyError(f"Tool not found: {tool_name}")
        if alias in self._alias_map:
            existing = self._alias_map[alias]
            raise ValueError(f"Alias already registered: {alias} -> {existing}")
        self._alias_map[alias] = tool_name

    def unregister(self, name: str) -> BaseTool:
        """Unregister a tool by name.

        Args:
            name: The name of the tool to unregister.

        Returns:
            The unregistered tool instance.

        Raises:
            KeyError: If the tool is not registered.
        """
        tool = self._tools.pop(name)
        self._unregister_aliases(name)
        return tool

    def _register_aliases(self, tool: BaseTool) -> None:
        """Register all aliases for a tool."""
        aliases = tool.aliases or []
        for alias in aliases:
            self._alias_map[alias] = tool.name

    def _unregister_aliases(self, tool_name: str) -> None:
        """Remove all aliases for a tool."""
        to_remove = [a for a, n in self._alias_map.items() if n == tool_name]
        for alias in to_remove:
            del self._alias_map[alias]

    # -------------------------------------------------------------------------
    # Lookup
    # -------------------------------------------------------------------------

    def get(self, name: str) -> BaseTool | None:
        """Look up a tool by name or alias.

        Args:
            name: The tool name or alias to look up.

        Returns:
            The tool instance, or None if not found.
        """
        # Direct name lookup
        if name in self._tools:
            return self._tools[name]
        # Alias lookup
        tool_name = self._alias_map.get(name)
        if tool_name is not None:
            return self._tools.get(tool_name)
        return None

    def get_required(self, name: str) -> BaseTool:
        """Look up a tool by name, raising if not found.

        Args:
            name: The tool name or alias to look up.

        Returns:
            The tool instance.

        Raises:
            KeyError: If the tool is not registered.
        """
        tool = self.get(name)
        if tool is None:
            raise KeyError(f"Tool not registered: {name}")
        return tool

    def has(self, name: str) -> bool:
        """Check if a tool is registered by name or alias.

        Args:
            name: The tool name or alias to check.

        Returns:
            True if the tool is registered, False otherwise.
        """
        return self.get(name) is not None

    # -------------------------------------------------------------------------
    # Listing
    # -------------------------------------------------------------------------

    def list_names(self) -> list[str]:
        """List all registered tool names.

        Returns:
            List of tool names (not aliases).
        """
        return list(self._tools.keys())

    def list_all(self) -> list[BaseTool]:
        """List all registered tools.

        Returns:
            List of tool instances.
        """
        return list(self._tools.values())

    def list_aliases(self, name: str | None = None) -> list[str]:
        """List all aliases, optionally filtered by tool name.

        Args:
            name: If provided, only list aliases for this tool.

        Returns:
            List of alias names.
        """
        if name is None:
            return list(self._alias_map.keys())
        return [a for a, n in self._alias_map.items() if n == name]

    # -------------------------------------------------------------------------
    # Filtering
    # -------------------------------------------------------------------------

    def filter(self, predicate: Callable[[BaseTool], bool]) -> list[BaseTool]:
        """Filter tools by a predicate function.

        Args:
            predicate: A function that takes a BaseTool and returns bool.

        Returns:
            List of tools matching the predicate.
        """
        return [tool for tool in self._tools.values() if predicate(tool)]

    def filter_by_names(self, names: Sequence[str]) -> list[BaseTool]:
        """Get tools by a list of names or aliases.

        Args:
            names: Sequence of tool names or aliases.

        Returns:
            List of found tool instances (order preserved, None skipped).
        """
        result = []
        for name in names:
            tool = self.get(name)
            if tool is not None:
                result.append(tool)
        return result

    def get_always_load(self) -> list[BaseTool]:
        """Get all tools that should always be loaded.

        Returns:
            List of always-load tools.
        """
        return [tool for tool in self._tools.values() if tool.always_load]

    def get_with_permission(
        self,
        names: Sequence[str],
        allowed: set[str] | None = None,
        denied: set[str] | None = None,
    ) -> list[BaseTool]:
        """Get tools with permission filtering.

        Args:
            names: Sequence of tool names or aliases.
            allowed: Set of allowed tool names (None = all allowed).
            denied: Set of denied tool names (None = none denied).

        Returns:
            List of permitted tool instances.
        """
        if allowed is None and denied is None:
            return self.filter_by_names(names)

        result = []
        for name in names:
            tool = self.get(name)
            if tool is None:
                continue
            tool_name = tool.name
            if allowed is not None and tool_name not in allowed:
                continue
            if denied is not None and tool_name in denied:
                continue
            result.append(tool)
        return result

    # -------------------------------------------------------------------------
    # Schema Export
    # -------------------------------------------------------------------------

    def get_schemas(self) -> list[dict[str, Any]]:
        """Get JSON schemas for all registered tools.

        Returns:
            List of tool input schemas.
        """
        return [tool.input_schema for tool in self._tools.values()]

    # -------------------------------------------------------------------------
    # Bulk Operations
    # -------------------------------------------------------------------------

    def merge(self, other: ToolRegistry) -> None:
        """Merge another registry into this one.

        Args:
            other: The other registry to merge.

        Raises:
            ValueError: If a tool name conflicts.
        """
        for tool in other.list_all():
            self.register(tool)

    def clear(self) -> None:
        """Clear all registered tools and aliases."""
        self._tools.clear()
        self._alias_map.clear()

    def __len__(self) -> int:
        """Return the number of registered tools."""
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        """Check if a tool is registered."""
        return self.has(name)

    def __iter__(self):
        """Iterate over tool names."""
        return iter(self._tools)

    def __repr__(self) -> str:
        """String representation of the registry."""
        return f"ToolRegistry({len(self._tools)} tools)"


# =============================================================================
# Global Registry
# =============================================================================

# A shared global registry instance for convenience.
_global_registry: ToolRegistry | None = None


def get_global_registry() -> ToolRegistry:
    """Get the global tool registry instance.

    Returns:
        The global ToolRegistry singleton.
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry


def register_tool(tool: BaseTool) -> None:
    """Register a tool with the global registry.

    Args:
        tool: The tool instance to register.
    """
    get_global_registry().register(tool)


def get_tool(name: str) -> BaseTool | None:
    """Look up a tool from the global registry.

    Args:
        name: The tool name or alias.

    Returns:
        The tool instance, or None if not found.
    """
    return get_global_registry().get(name)
