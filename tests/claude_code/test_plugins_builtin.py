"""
Tests for plugins/builtin.py - Built-in plugin registry and definitions.
"""

from __future__ import annotations

import pytest

from src.claude_code.plugins.builtin import (
    _BUILTIN_PLUGINS,
    BUILTIN_MARKETPLACE_NAME,
    BuiltinPluginDefinition,
    _clear_builtin_plugins,
    builtin_plugins_count,
    get_builtin_plugin_definition,
    get_builtin_plugins,
    is_builtin_plugin_id,
    register_builtin_plugin,
)


class TestBuiltinPluginDefinition:
    """Tests for BuiltinPluginDefinition dataclass."""

    def test_create_minimal_definition(self) -> None:
        """Create a minimal built-in plugin definition."""
        plugin = BuiltinPluginDefinition(name="test-plugin")
        assert plugin.name == "test-plugin"
        assert plugin.description == ""
        assert plugin.version is None
        assert plugin.default_enabled is True

    def test_create_full_definition(self) -> None:
        """Create a full built-in plugin definition."""
        plugin = BuiltinPluginDefinition(
            name="full-plugin",
            description="A full-featured plugin",
            version="2.1.0",
            skills=[{"name": "skill1"}],
            hooks={"before_tool": []},
            mcp_servers={"server1": {}},
            default_enabled=False,
        )
        assert plugin.name == "full-plugin"
        assert plugin.description == "A full-featured plugin"
        assert plugin.version == "2.1.0"
        assert plugin.skills == [{"name": "skill1"}]
        assert plugin.hooks == {"before_tool": []}
        assert plugin.mcp_servers == {"server1": {}}
        assert plugin.default_enabled is False


class TestIsBuiltinPluginId:
    """Tests for is_builtin_plugin_id()."""

    def test_builtin_plugin_id(self) -> None:
        """Plugin ID with builtin suffix returns True."""
        assert is_builtin_plugin_id("my-plugin@builtin") is True

    def test_non_builtin_plugin_id(self) -> None:
        """Plugin ID without builtin suffix returns False."""
        assert is_builtin_plugin_id("my-plugin@marketplace") is False
        assert is_builtin_plugin_id("my-plugin@npm") is False
        assert is_builtin_plugin_id("my-plugin") is False

    def test_empty_plugin_id(self) -> None:
        """Empty plugin ID returns False."""
        assert is_builtin_plugin_id("") is False
        assert is_builtin_plugin_id("@builtin") is True  # Edge case


class TestRegisterBuiltinPlugin:
    """Tests for register_builtin_plugin()."""

    def test_register_single_plugin(self) -> None:
        """Register a single built-in plugin."""
        _clear_builtin_plugins()
        plugin = BuiltinPluginDefinition(name="register-test", description="Test")
        register_builtin_plugin(plugin)
        assert get_builtin_plugin_definition("register-test") is not None

    def test_register_multiple_plugins(self) -> None:
        """Register multiple built-in plugins."""
        _clear_builtin_plugins()
        register_builtin_plugin(
            BuiltinPluginDefinition(name="plugin-a", description="A")
        )
        register_builtin_plugin(
            BuiltinPluginDefinition(name="plugin-b", description="B")
        )
        assert builtin_plugins_count() == 2

    def test_override_existing_plugin(self) -> None:
        """Re-registering a plugin with the same name replaces it."""
        _clear_builtin_plugins()
        register_builtin_plugin(
            BuiltinPluginDefinition(name="override-test", version="1.0.0")
        )
        register_builtin_plugin(
            BuiltinPluginDefinition(name="override-test", version="2.0.0")
        )
        assert get_builtin_plugin_definition("override-test") is not None
        assert get_builtin_plugin_definition("override-test").version == "2.0.0"


class TestGetBuiltinPluginDefinition:
    """Tests for get_builtin_plugin_definition()."""

    def test_get_existing_plugin(self) -> None:
        """Get an existing plugin definition."""
        _clear_builtin_plugins()
        plugin = BuiltinPluginDefinition(
            name="get-test",
            description="Test plugin",
            version="1.0.0",
        )
        register_builtin_plugin(plugin)
        result = get_builtin_plugin_definition("get-test")
        assert result is not None
        assert result.name == "get-test"
        assert result.version == "1.0.0"

    def test_get_nonexistent_plugin(self) -> None:
        """Get a non-existent plugin returns None."""
        _clear_builtin_plugins()
        result = get_builtin_plugin_definition("nonexistent")
        assert result is None


class TestGetBuiltinPlugins:
    """Tests for get_builtin_plugins()."""

    def test_empty_registry(self) -> None:
        """Empty registry returns empty lists."""
        _clear_builtin_plugins()
        enabled, disabled = get_builtin_plugins()
        assert enabled == []
        assert disabled == []

    def test_default_enabled_plugins(self) -> None:
        """Plugins with default_enabled=True are in enabled list."""
        _clear_builtin_plugins()
        register_builtin_plugin(
            BuiltinPluginDefinition(name="enabled-by-default", default_enabled=True)
        )
        enabled, disabled = get_builtin_plugins()
        assert len(enabled) == 1
        assert enabled[0].name == "enabled-by-default"
        assert enabled[0].enabled is True

    def test_disabled_plugins(self) -> None:
        """Plugins with default_enabled=False are in disabled list."""
        _clear_builtin_plugins()
        register_builtin_plugin(
            BuiltinPluginDefinition(name="disabled-by-default", default_enabled=False)
        )
        enabled, disabled = get_builtin_plugins()
        assert len(disabled) == 1
        assert disabled[0].name == "disabled-by-default"
        assert disabled[0].enabled is False

    def test_plugin_manifest_created(self) -> None:
        """Each plugin gets a PluginManifest created from the definition."""
        _clear_builtin_plugins()
        register_builtin_plugin(
            BuiltinPluginDefinition(
                name="manifest-test",
                description="Test manifest",
                version="3.0.0",
                hooks={"before_tool": []},
                mcp_servers={"s1": {}},
            )
        )
        enabled, _ = get_builtin_plugins()
        plugin = enabled[0]
        assert plugin.name == "manifest-test"
        assert plugin.manifest.name == "manifest-test"
        assert plugin.manifest.description == "Test manifest"
        assert plugin.manifest.version == "3.0.0"
        assert plugin.is_builtin is True
        assert plugin.hooks_config == {"before_tool": []}
        assert plugin.mcp_servers == {"s1": {}}

    def test_plugin_id_format(self) -> None:
        """Built-in plugins have plugin ID in format 'name@builtin'."""
        _clear_builtin_plugins()
        register_builtin_plugin(
            BuiltinPluginDefinition(name="id-format-test")
        )
        enabled, _ = get_builtin_plugins()
        assert enabled[0].source == "id-format-test@builtin"
        assert enabled[0].repository == "id-format-test@builtin"


class TestBuiltinMarketplaceName:
    """Tests for BUILTIN_MARKETPLACE_NAME constant."""

    def test_builtin_marketplace_name(self) -> None:
        """Constant equals 'builtin'."""
        assert BUILTIN_MARKETPLACE_NAME == "builtin"
