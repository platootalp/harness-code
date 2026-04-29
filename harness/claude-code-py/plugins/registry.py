"""Plugin registry for managing loaded plugins.

The registry maintains the central catalog of all loaded plugins,
tracks their enabled/disabled state, and provides hook registration
and triggering capabilities.

TypeScript equivalent: src/utils/plugins/registry.ts (PluginLoader)
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .base import BasePlugin, LoadedPlugin

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# =============================================================================
# Hook Registration
# =============================================================================


@dataclass
class HookHandler:
    """A registered hook handler."""

    plugin_name: str
    handler: Callable[..., Any]
    condition: str | None = None


# =============================================================================
# Plugin Registry
# =============================================================================


class PluginRegistry:
    """Registry for managing plugins.

    Tracks all loaded plugins, their state, and provides hook
    registration and triggering.

    TypeScript equivalent: PluginLoader in utils/plugins/

    Attributes:
        plugins: All registered plugins by name.
        enabled_plugins: Currently enabled plugins.
        hooks: Registered hook handlers by event name.
    """

    def __init__(self) -> None:
        """Initialize the plugin registry."""
        self._plugins: dict[str, BasePlugin] = {}
        self._loaded_plugins: dict[str, LoadedPlugin] = {}
        self._hooks: dict[str, list[HookHandler]] = {}
        self._enabled_order: list[str] = []

    # -------------------------------------------------------------------------
    # Plugin Management
    # -------------------------------------------------------------------------

    def register(self, plugin: BasePlugin) -> None:
        """Register a plugin.

        Args:
            plugin: The plugin instance to register.

        Raises:
            ValueError: If a plugin with the same name is already registered.
        """
        if plugin.name in self._plugins:
            raise ValueError(f"Plugin already registered: {plugin.name}")

        self._plugins[plugin.name] = plugin
        logger.debug(f"Registered plugin: {plugin.name}")

    def register_loaded(self, loaded: LoadedPlugin) -> None:
        """Register a loaded plugin descriptor.

        Args:
            loaded: The loaded plugin descriptor.
        """
        self._loaded_plugins[loaded.name] = loaded
        logger.debug(f"Registered loaded plugin: {loaded.name}")

    def unregister(self, name: str) -> bool:
        """Unregister a plugin by name.

        Args:
            name: The plugin name to unregister.

        Returns:
            True if the plugin was found and removed.
        """
        if name in self._plugins:
            del self._plugins[name]
            if name in self._enabled_order:
                self._enabled_order.remove(name)
            # Clean up hooks for this plugin
            for event in self._hooks:
                self._hooks[event] = [
                    h for h in self._hooks[event] if h.plugin_name != name
                ]
            logger.debug(f"Unregistered plugin: {name}")
            return True

        if name in self._loaded_plugins:
            del self._loaded_plugins[name]
            return True

        return False

    def get(self, name: str) -> BasePlugin | None:
        """Get a plugin by name.

        Args:
            name: The plugin name.

        Returns:
            The plugin instance, or None if not found.
        """
        return self._plugins.get(name)

    def get_loaded(self, name: str) -> LoadedPlugin | None:
        """Get a loaded plugin descriptor by name.

        Args:
            name: The plugin name.

        Returns:
            The loaded plugin descriptor, or None if not found.
        """
        return self._loaded_plugins.get(name)

    def list_all(self) -> list[BasePlugin]:
        """List all registered plugins.

        Returns:
            List of all plugins.
        """
        return list(self._plugins.values())

    def list_loaded(self) -> list[LoadedPlugin]:
        """List all loaded plugin descriptors.

        Returns:
            List of all loaded plugins.
        """
        return list(self._loaded_plugins.values())

    def list_enabled(self) -> list[BasePlugin]:
        """List all enabled plugins.

        Returns:
            List of enabled plugins in registration order.
        """
        return [self._plugins[name] for name in self._enabled_order if name in self._plugins]

    def list_disabled(self) -> list[BasePlugin]:
        """List all disabled plugins.

        Returns:
            List of disabled plugins.
        """
        return [
            p for name, p in self._plugins.items() if name not in self._enabled_order
        ]

    def has(self, name: str) -> bool:
        """Check if a plugin is registered.

        Args:
            name: The plugin name.

        Returns:
            True if the plugin is registered.
        """
        return name in self._plugins

    # -------------------------------------------------------------------------
    # Enable / Disable
    # -------------------------------------------------------------------------

    async def enable(self, name: str) -> bool:
        """Enable a plugin.

        Calls the plugin's on_enable lifecycle method.

        Args:
            name: The plugin name.

        Returns:
            True if the plugin was enabled.
        """
        plugin = self._plugins.get(name)
        if plugin is None:
            logger.warning(f"Cannot enable unknown plugin: {name}")
            return False

        if plugin.is_enabled():
            return True

        try:
            await plugin.on_enable()
            plugin.set_enabled(True)
            if name not in self._enabled_order:
                self._enabled_order.append(name)
            logger.info(f"Enabled plugin: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to enable plugin {name}: {e}")
            return False

    async def disable(self, name: str) -> bool:
        """Disable a plugin.

        Calls the plugin's on_disable lifecycle method.

        Args:
            name: The plugin name.

        Returns:
            True if the plugin was disabled.
        """
        plugin = self._plugins.get(name)
        if plugin is None:
            logger.warning(f"Cannot disable unknown plugin: {name}")
            return False

        if not plugin.is_enabled():
            return True

        try:
            await plugin.on_disable()
            plugin.set_enabled(False)
            if name in self._enabled_order:
                self._enabled_order.remove(name)
            logger.info(f"Disabled plugin: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to disable plugin {name}: {e}")
            return False

    async def enable_all(self) -> None:
        """Enable all registered plugins."""
        for name in list(self._plugins.keys()):
            await self.enable(name)

    async def disable_all(self) -> None:
        """Disable all enabled plugins."""
        for name in list(self._enabled_order):
            await self.disable(name)

    # -------------------------------------------------------------------------
    # Hook Registration
    # -------------------------------------------------------------------------

    def register_hook(
        self,
        event: str,
        plugin_name: str,
        handler: Callable[..., Any],
        condition: str | None = None,
    ) -> None:
        """Register a hook handler for an event.

        Args:
            event: The hook event name (e.g. "PreToolUse", "PostToolUse").
            plugin_name: The name of the plugin registering the hook.
            handler: Async callable to invoke when the hook fires.
            condition: Optional condition expression for filtering.
        """
        if event not in self._hooks:
            self._hooks[event] = []

        self._hooks[event].append(
            HookHandler(plugin_name=plugin_name, handler=handler, condition=condition)
        )
        logger.debug(f"Registered hook: {plugin_name}.{event}")

    def unregister_hook(
        self,
        event: str,
        plugin_name: str,
    ) -> bool:
        """Unregister all hook handlers for a plugin and event.

        Args:
            event: The hook event name.
            plugin_name: The plugin name.

        Returns:
            True if any handlers were removed.
        """
        if event not in self._hooks:
            return False

        before = len(self._hooks[event])
        self._hooks[event] = [
            h for h in self._hooks[event] if h.plugin_name != plugin_name
        ]
        removed = before - len(self._hooks[event])
        if removed:
            logger.debug(f"Unregistered {removed} hook(s): {plugin_name}.{event}")
        return removed > 0

    def list_hook_events(self) -> list[str]:
        """List all registered hook event names.

        Returns:
            List of event names with registered handlers.
        """
        return [event for event, handlers in self._hooks.items() if handlers]

    def list_hooks_for_event(self, event: str) -> list[HookHandler]:
        """List all handlers registered for an event.

        Args:
            event: The hook event name.

        Returns:
            List of hook handlers.
        """
        return list(self._hooks.get(event, []))

    # -------------------------------------------------------------------------
    # Hook Triggering
    # -------------------------------------------------------------------------

    async def trigger_hook(
        self,
        event: str,
        context: dict[str, Any],
    ) -> list[Any]:
        """Trigger all handlers for an event.

        Runs all registered handlers for the event. Errors in individual
        handlers are logged and do not prevent other handlers from running.

        Args:
            event: The hook event name.
            context: Context data passed to each handler.

        Returns:
            List of results from handlers (may include None).
        """
        results: list[Any] = []
        handlers = self._hooks.get(event, [])

        for hook in handlers:
            try:
                result = await hook.handler(context)
                results.append(result)
            except Exception as e:
                logger.error(
                    f"Hook error in {hook.plugin_name}.{event}: {e}",
                    exc_info=True,
                )

        return results

    async def trigger_hook_until_blocked(
        self,
        event: str,
        context: dict[str, Any],
    ) -> tuple[bool, list[Any]]:
        """Trigger handlers until one blocks.

        Runs handlers in order until a handler returns a blocking result.
        Used for PreToolUse-style hooks where blocking takes precedence.

        Args:
            event: The hook event name.
            context: Context data passed to each handler.

        Returns:
            Tuple of (allowed, results). allowed is False if a handler blocked.
        """
        results: list[Any] = []
        handlers = self._hooks.get(event, [])

        for hook in handlers:
            try:
                result = await hook.handler(context)
                results.append(result)
                # Check for blocking result
                if isinstance(result, dict) and result.get("blocked"):
                    return False, results
            except Exception as e:
                logger.error(
                    f"Hook error in {hook.plugin_name}.{event}: {e}",
                    exc_info=True,
                )

        return True, results

    # -------------------------------------------------------------------------
    # Utilities
    # -------------------------------------------------------------------------

    def clear(self) -> None:
        """Clear all plugins and hooks from the registry."""
        self._plugins.clear()
        self._loaded_plugins.clear()
        self._hooks.clear()
        self._enabled_order.clear()
        logger.debug("Cleared plugin registry")

    def __len__(self) -> int:
        """Return the number of registered plugins."""
        return len(self._plugins)

    def __contains__(self, name: str) -> bool:
        """Check if a plugin is registered."""
        return name in self._plugins

    def __iter__(self):
        """Iterate over plugin names."""
        return iter(self._plugins)


# =============================================================================
# Global Registry
# =============================================================================


# Global plugin registry instance
_global_registry: PluginRegistry | None = None


def get_plugin_registry() -> PluginRegistry:
    """Get the global plugin registry.

    Returns:
        The global PluginRegistry instance.
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = PluginRegistry()
    return _global_registry


def reset_plugin_registry() -> None:
    """Reset the global plugin registry.

    Clears all plugins and hooks. Primarily used for testing.
    """
    global _global_registry
    if _global_registry is not None:
        _global_registry.clear()
    _global_registry = None
