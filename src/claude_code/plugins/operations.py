"""
Plugin operations - install, uninstall, enable, disable.

Handles plugin lifecycle management through configuration changes
in the user's settings file.

TypeScript equivalent: src/plugins/operations.ts
"""

from __future__ import annotations

import json
import shutil
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from .base import PluginScope
from .registry import PluginRegistry

if TYPE_CHECKING:
    pass


# =============================================================================
# Enums
# =============================================================================


class PluginOperation(StrEnum):
    """Plugin lifecycle operations."""

    INSTALL = "install"
    UNINSTALL = "uninstall"
    ENABLE = "enable"
    DISABLE = "disable"
    UPDATE = "update"


# =============================================================================
# Plugin Operations
# =============================================================================


class PluginOperations:
    """Handles plugin lifecycle operations.

    Manages install, uninstall, enable, and disable operations
    by reading and writing the plugin configuration file.

    TypeScript equivalent: pluginOperations.ts

    Attributes:
        registry: The plugin registry instance.
        config_path: Path to the settings JSON file.
    """

    def __init__(
        self,
        registry: PluginRegistry,
        config_path: Path | None = None,
    ) -> None:
        """Initialize plugin operations.

        Args:
            registry: The plugin registry to manage.
            config_path: Path to settings.json. Defaults to ~/.claude/settings.json.
        """
        self.registry = registry
        self.config_path = config_path or (Path.home() / ".claude" / "settings.json")

    # -------------------------------------------------------------------------
    # Config I/O
    # -------------------------------------------------------------------------

    async def _load_config(self) -> dict[str, Any]:
        """Load configuration from disk.

        Returns:
            The parsed JSON config, or empty dict if file doesn't exist.
        """
        if self.config_path.exists():
            return cast(dict[str, Any], json.loads(self.config_path.read_text()))
        return {}

    async def _save_config(self, config: dict[str, Any]) -> None:
        """Save configuration to disk.

        Creates parent directories if they don't exist.

        Args:
            config: The configuration dict to save.
        """
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(json.dumps(config, indent=2))
        return

    # -------------------------------------------------------------------------
    # Install
    # -------------------------------------------------------------------------

    async def install_plugin(
        self,
        plugin_id: str,
        source: str,
        scope: PluginScope = PluginScope.USER,
    ) -> None:
        """Install a plugin.

        Writes the plugin declaration to the settings file. Does not
        actually materialize the plugin — that happens during loading.

        Args:
            plugin_id: The unique plugin identifier.
            source: The plugin source (e.g. "npm:my-plugin", "pip:my-plugin").
            scope: The installation scope (default USER).
        """
        config = await self._load_config()
        if "plugins" not in config:
            config["plugins"] = {}

        config["plugins"][plugin_id] = {
            "source": source,
            "scope": scope.value,
            "enabled": True,
        }

        await self._save_config(config)

    # -------------------------------------------------------------------------
    # Uninstall
    # -------------------------------------------------------------------------

    async def uninstall_plugin(
        self,
        plugin_id: str,
        remove_data: bool = False,
    ) -> None:
        """Uninstall a plugin.

        Removes the plugin declaration from the settings file.

        Args:
            plugin_id: The plugin identifier to uninstall.
            remove_data: If True, also removes plugin data directory.
        """
        config = await self._load_config()
        if "plugins" in config and plugin_id in config["plugins"]:
            del config["plugins"][plugin_id]
            await self._save_config(config)

        if remove_data:
            data_dir = Path.home() / ".claude" / "plugins" / "data" / plugin_id
            if data_dir.exists():
                shutil.rmtree(data_dir)

    # -------------------------------------------------------------------------
    # Enable / Disable
    # -------------------------------------------------------------------------

    async def enable_plugin(self, plugin_id: str) -> None:
        """Enable a plugin.

        Sets the plugin's enabled flag to True in the settings file.

        Args:
            plugin_id: The plugin identifier to enable.
        """
        config = await self._load_config()
        if "plugins" in config and plugin_id in config["plugins"]:
            config["plugins"][plugin_id]["enabled"] = True
            await self._save_config(config)

    async def disable_plugin(self, plugin_id: str) -> None:
        """Disable a plugin.

        Sets the plugin's enabled flag to False in the settings file.

        Args:
            plugin_id: The plugin identifier to disable.
        """
        config = await self._load_config()
        if "plugins" in config and plugin_id in config["plugins"]:
            config["plugins"][plugin_id]["enabled"] = False
            await self._save_config(config)
