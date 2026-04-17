"""Built-in plugin registry and definitions.

Built-in plugins ship with the CLI and can be enabled/disabled by users.
The registry maintains a catalog of all built-in plugins with their metadata.

TypeScript equivalent: src/plugins/builtinPlugins.ts
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .base import LoadedPlugin, PluginManifest

if TYPE_CHECKING:
    pass


# =============================================================================
# Constants
# =============================================================================

BUILTIN_MARKETPLACE_NAME = "builtin"


# =============================================================================
# Builtin Plugin Definition
# =============================================================================


@dataclass
class BuiltinPluginDefinition:
    """Definition for a built-in plugin that ships with the CLI.

    Built-in plugins appear in the /plugin UI and can be enabled/disabled
    by users (persisted to user settings).

    Attributes:
        name: Plugin name (used in `{name}@builtin` identifier).
        description: Description shown in the /plugin UI.
        version: Optional version string.
        skills: Skills provided by this plugin.
        hooks: Hooks provided by this plugin.
        mcp_servers: MCP servers provided by this plugin.
        is_available: Whether this plugin is available (e.g. based on system
            capabilities). Unavailable plugins are hidden entirely.
        default_enabled: Default enabled state before the user sets a preference.
    """

    name: str
    description: str = ""
    version: str | None = None
    skills: list[Any] | None = None  # list[BundledSkillDefinition]
    hooks: dict[str, Any] | None = None  # HooksSettings
    mcp_servers: dict[str, Any] | None = None  # dict[str, McpServerConfig]
    is_available: Any = None  # Callable[[], bool] | None
    default_enabled: bool = True


# =============================================================================
# Builtin Plugin Registry
# =============================================================================

# Module-level storage for built-in plugins
_BUILTIN_PLUGINS: dict[str, BuiltinPluginDefinition] = {}


def register_builtin_plugin(definition: BuiltinPluginDefinition) -> None:
    """Register a built-in plugin.

    Args:
        definition: The built-in plugin definition.
    """
    _BUILTIN_PLUGINS[definition.name] = definition


def is_builtin_plugin_id(plugin_id: str) -> bool:
    """Check if a plugin ID represents a built-in plugin (ends with @builtin).

    Args:
        plugin_id: The plugin identifier.

    Returns:
        True if the plugin is built-in.
    """
    return plugin_id.endswith(f"@{BUILTIN_MARKETPLACE_NAME}")


def get_builtin_plugin_definition(name: str) -> BuiltinPluginDefinition | None:
    """Get a specific built-in plugin definition by name.

    Args:
        name: The plugin name.

    Returns:
        The plugin definition, or None if not found.
    """
    return _BUILTIN_PLUGINS.get(name)


def get_builtin_plugins() -> tuple[list[Any], list[Any]]:
    """Get all registered built-in plugins split into enabled/disabled.

    Built-in plugins whose is_available() returns false are omitted entirely.

    Returns:
        Tuple of (enabled, disabled) lists of LoadedPlugin objects.
    """
    enabled: list[Any] = []
    disabled: list[Any] = []

    for name, definition in _BUILTIN_PLUGINS.items():
        # Check availability
        if definition.is_available is not None:
            try:
                if not definition.is_available():
                    continue
            except Exception:
                continue

        plugin_id = f"{name}@{BUILTIN_MARKETPLACE_NAME}"

        # Determine enabled state — user settings would override default_enabled
        is_enabled = definition.default_enabled

        manifest = PluginManifest(
            name=name,
            description=definition.description,
            version=definition.version or "1.0.0",
        )

        plugin: LoadedPlugin = LoadedPlugin(
            name=name,
            manifest=manifest,
            path=BUILTIN_MARKETPLACE_NAME,  # sentinel — no filesystem path
            source=plugin_id,
            repository=plugin_id,
            enabled=is_enabled,
            is_builtin=True,
            hooks_config=definition.hooks,
            mcp_servers=definition.mcp_servers,
        )

        if is_enabled:
            enabled.append(plugin)
        else:
            disabled.append(plugin)

    return enabled, disabled


def builtin_plugins_count() -> int:
    """Return the number of registered built-in plugins."""
    return len(_BUILTIN_PLUGINS)


def _clear_builtin_plugins() -> None:
    """Clear all built-in plugins. For testing only."""
    _BUILTIN_PLUGINS.clear()


# =============================================================================
# Built-in Plugin Registrations
# =============================================================================


def _register_builtin_plugins() -> None:
    """Register all built-in plugins.

    This function is called once at module load time to register
    all plugins that ship with the CLI.
    """
    # Built-in plugins are registered here. Each built-in plugin
    # provides skills, hooks, MCP servers, or other features.
    #
    # Example registrations would look like:
    # register_builtin_plugin(BuiltinPluginDefinition(
    #     name="brainstorm",
    #     description="Structured brainstorming with mind maps and matrices",
    #     version="1.0.0",
    #     skills=[...],
    #     hooks={...},
    #     default_enabled=True,
    # ))
    pass


# Register built-in plugins on module import
_register_builtin_plugins()
