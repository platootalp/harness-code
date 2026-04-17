"""
Tests for engine/tools/registry.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest
from claude_code.engine.tools.registry import (
    ToolRegistry,
    _global_registry,
    get_global_registry,
    get_tool,
    register_tool,
)

# -------------------------------------------------------------------------
# Mock Tool Helper
# -------------------------------------------------------------------------


def make_tool(name: str, aliases: list[str] | None = None) -> MagicMock:
    """Create a mock tool with the given name and aliases."""
    tool = MagicMock()
    tool.name = name
    tool.aliases = aliases
    tool.always_load = False
    tool.input_schema = {"type": "object", "properties": {}, "name": name}
    return tool


# -------------------------------------------------------------------------
# ToolRegistry Tests
# -------------------------------------------------------------------------

class TestRegistryRegistration:
    """Tests for tool registration."""

    def test_register_single_tool(self) -> None:
        """Test registering a single tool."""
        registry = ToolRegistry()
        tool = make_tool("Bash")
        registry.register(tool)
        assert "Bash" in registry
        assert registry.get("Bash") is tool

    def test_register_duplicate_raises(self) -> None:
        """Test that registering a duplicate tool raises."""
        registry = ToolRegistry()
        registry.register(make_tool("Bash"))
        with pytest.raises(ValueError, match="Tool already registered"):
            registry.register(make_tool("Bash"))

    def test_register_alias(self) -> None:
        """Test registering an alias for a tool."""
        registry = ToolRegistry()
        tool = make_tool("Bash")
        registry.register(tool)
        registry.register_alias("Bash", "Shell")
        assert registry.get("Shell") is tool
        assert "Shell" in registry

    def test_register_alias_tool_not_found(self) -> None:
        """Test registering alias for non-existent tool raises."""
        registry = ToolRegistry()
        with pytest.raises(KeyError, match="Tool not found"):
            registry.register_alias("Bash", "Shell")

    def test_register_alias_duplicate(self) -> None:
        """Test registering duplicate alias raises."""
        registry = ToolRegistry()
        tool1 = make_tool("Bash")
        registry.register(tool1)
        registry.register_alias("Bash", "cmd")
        with pytest.raises(ValueError, match="Alias already registered"):
            registry.register_alias("Bash", "cmd")

    def test_register_with_aliases(self) -> None:
        """Test that registering a tool also registers its aliases."""
        registry = ToolRegistry()
        tool = make_tool("Glob", aliases=["ls", "find"])
        registry.register(tool)
        assert registry.get("ls") is tool
        assert registry.get("find") is tool

    def test_unregister(self) -> None:
        """Test unregistering a tool."""
        registry = ToolRegistry()
        tool = make_tool("Bash", aliases=["Shell"])
        registry.register(tool)
        result = registry.unregister("Bash")
        assert result is tool
        assert "Bash" not in registry
        assert "Shell" not in registry

    def test_unregister_not_found(self) -> None:
        """Test unregistering non-existent tool raises."""
        registry = ToolRegistry()
        with pytest.raises(KeyError):
            registry.unregister("Bash")


class TestRegistryLookup:
    """Tests for tool lookup."""

    def setup_method(self) -> None:
        """Set up a registry with test tools."""
        self.registry = ToolRegistry()
        self.bash = make_tool("Bash", aliases=["Shell"])
        self.glob = make_tool("Glob")
        self.registry.register(self.bash)
        self.registry.register(self.glob)

    def test_get_by_name(self) -> None:
        """Test getting tool by exact name."""
        assert self.registry.get("Bash") is self.bash
        assert self.registry.get("Glob") is self.glob

    def test_get_by_alias(self) -> None:
        """Test getting tool by alias."""
        assert self.registry.get("Shell") is self.bash

    def test_get_not_found(self) -> None:
        """Test getting non-existent tool returns None."""
        assert self.registry.get("NonExistent") is None

    def test_get_required_found(self) -> None:
        """Test get_required returns tool when found."""
        assert self.registry.get_required("Bash") is self.bash

    def test_get_required_not_found(self) -> None:
        """Test get_required raises when not found."""
        with pytest.raises(KeyError, match="Tool not registered"):
            self.registry.get_required("NonExistent")

    def test_has(self) -> None:
        """Test has() method."""
        assert self.registry.has("Bash") is True
        assert self.registry.has("Shell") is True
        assert self.registry.has("NonExistent") is False


class TestRegistryListing:
    """Tests for listing tools."""

    def setup_method(self) -> None:
        """Set up a registry with test tools."""
        self.registry = ToolRegistry()
        self.registry.register(make_tool("Bash"))
        self.registry.register(make_tool("Glob"))
        self.registry.register(make_tool("Grep", aliases=["Search"]))

    def test_list_names(self) -> None:
        """Test listing all tool names."""
        names = self.registry.list_names()
        assert set(names) == {"Bash", "Glob", "Grep"}

    def test_list_all(self) -> None:
        """Test listing all tool instances."""
        tools = self.registry.list_all()
        assert len(tools) == 3
        names = {t.name for t in tools}
        assert names == {"Bash", "Glob", "Grep"}

    def test_list_aliases_all(self) -> None:
        """Test listing all aliases."""
        aliases = self.registry.list_aliases()
        assert "Search" in aliases

    def test_list_aliases_for_tool(self) -> None:
        """Test listing aliases for a specific tool."""
        aliases = self.registry.list_aliases("Grep")
        assert aliases == ["Search"]

    def test_list_aliases_nonexistent(self) -> None:
        """Test listing aliases for non-existent tool returns empty."""
        assert self.registry.list_aliases("NonExistent") == []


class TestRegistryFiltering:
    """Tests for filtering tools."""

    def setup_method(self) -> None:
        """Set up a registry with test tools."""
        self.registry = ToolRegistry()
        bash = make_tool("Bash")
        bash.always_load = True
        glob = make_tool("Glob")
        glob.always_load = False
        grep = make_tool("Grep")
        self.registry.register(bash)
        self.registry.register(glob)
        self.registry.register(grep)
        self.bash = bash
        self.glob = glob
        self.grep = grep

    def test_filter(self) -> None:
        """Test filter with predicate."""
        tools = self.registry.filter(lambda t: t.name.startswith("Ba") or t.name.startswith("Gl"))
        names = {t.name for t in tools}
        assert names == {"Bash", "Glob"}

    def test_filter_by_names(self) -> None:
        """Test filtering by name list."""
        tools = self.registry.filter_by_names(["Bash", "Grep"])
        names = {t.name for t in tools}
        assert names == {"Bash", "Grep"}

    def test_filter_by_names_missing(self) -> None:
        """Test filtering skips missing names."""
        tools = self.registry.filter_by_names(["Bash", "NonExistent", "Glob"])
        names = {t.name for t in tools}
        assert names == {"Bash", "Glob"}

    def test_get_always_load(self) -> None:
        """Test getting always-load tools."""
        tools = self.registry.get_always_load()
        assert len(tools) == 1
        assert tools[0].name == "Bash"

    def test_get_with_permission_all_allowed(self) -> None:
        """Test permission filtering with all allowed."""
        tools = self.registry.get_with_permission(
            ["Bash", "Glob", "Grep"],
            allowed={"Bash", "Glob"},
        )
        names = {t.name for t in tools}
        assert names == {"Bash", "Glob"}

    def test_get_with_permission_denied(self) -> None:
        """Test permission filtering with denied."""
        tools = self.registry.get_with_permission(
            ["Bash", "Glob", "Grep"],
            denied={"Grep"},
        )
        names = {t.name for t in tools}
        assert names == {"Bash", "Glob"}

    def test_get_with_permission_both(self) -> None:
        """Test permission filtering with both allowed and denied."""
        tools = self.registry.get_with_permission(
            ["Bash", "Glob", "Grep"],
            allowed={"Bash", "Grep"},
            denied={"Grep"},
        )
        names = {t.name for t in tools}
        assert names == {"Bash"}


class TestRegistrySchemaExport:
    """Tests for schema export."""

    def test_get_schemas(self) -> None:
        """Test getting schemas for all tools."""
        registry = ToolRegistry()
        bash = make_tool("Bash")
        glob = make_tool("Glob")
        registry.register(bash)
        registry.register(glob)
        schemas = registry.get_schemas()
        assert len(schemas) == 2
        names = {s["name"] for s in schemas}
        assert names == {"Bash", "Glob"}


class TestRegistryBulkOperations:
    """Tests for bulk operations."""

    def test_merge(self) -> None:
        """Test merging two registries."""
        reg1 = ToolRegistry()
        reg1.register(make_tool("Bash"))
        reg2 = ToolRegistry()
        reg2.register(make_tool("Glob"))
        reg2.register(make_tool("Grep"))
        reg1.merge(reg2)
        names = set(reg1.list_names())
        assert names == {"Bash", "Glob", "Grep"}

    def test_merge_duplicate_raises(self) -> None:
        """Test merging with duplicate tool raises."""
        reg1 = ToolRegistry()
        reg1.register(make_tool("Bash"))
        reg2 = ToolRegistry()
        reg2.register(make_tool("Bash"))
        with pytest.raises(ValueError, match="Tool already registered"):
            reg1.merge(reg2)

    def test_clear(self) -> None:
        """Test clearing the registry."""
        registry = ToolRegistry()
        registry.register(make_tool("Bash"))
        registry.register(make_tool("Glob"))
        registry.clear()
        assert len(registry) == 0
        assert registry.list_names() == []


class TestRegistryDunderMethods:
    """Tests for dunder methods."""

    def test_len(self) -> None:
        """Test __len__."""
        registry = ToolRegistry()
        assert len(registry) == 0
        registry.register(make_tool("Bash"))
        registry.register(make_tool("Glob"))
        assert len(registry) == 2

    def test_contains(self) -> None:
        """Test __contains__."""
        registry = ToolRegistry()
        registry.register(make_tool("Bash"))
        assert "Bash" in registry
        assert "Glob" not in registry

    def test_iter(self) -> None:
        """Test __iter__."""
        registry = ToolRegistry()
        registry.register(make_tool("Bash"))
        registry.register(make_tool("Glob"))
        names = set(registry)
        assert names == {"Bash", "Glob"}

    def test_repr(self) -> None:
        """Test __repr__."""
        registry = ToolRegistry()
        assert repr(registry) == "ToolRegistry(0 tools)"
        registry.register(make_tool("Bash"))
        assert repr(registry) == "ToolRegistry(1 tools)"


class TestGlobalRegistry:
    """Tests for global registry functions."""

    def test_get_global_registry_singleton(self) -> None:
        """Test that get_global_registry returns the same instance."""
        reg1 = get_global_registry()
        reg2 = get_global_registry()
        assert reg1 is reg2

    def test_register_tool_global(self) -> None:
        """Test registering a tool with the global registry."""
        global _global_registry
        original = _global_registry
        _global_registry = None  # Reset
        try:
            tool = make_tool("GlobalTest")
            register_tool(tool)
            assert get_tool("GlobalTest") is tool
            assert "GlobalTest" in get_global_registry()
        finally:
            _global_registry = original  # Restore
