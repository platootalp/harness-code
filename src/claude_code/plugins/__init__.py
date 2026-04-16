"""
Plugins module for Claude Code plugin system.

Provides plugin lifecycle management, registry, and hook system.
"""

from .base import (
    BasePlugin,
    LoadedPlugin,
    PluginAuthor,
    PluginManifest,
    PluginScope,
    PluginSource,
)
from .builtin import (
    BUILTIN_MARKETPLACE_NAME,
    BuiltinPluginDefinition,
    builtin_plugins_count,
    get_builtin_plugin_definition,
    get_builtin_plugins,
    is_builtin_plugin_id,
    register_builtin_plugin,
)
from .cache import (
    CachedVersionInfo,
    CleanupResult,
    cleanup_orphaned_plugin_versions,
    clear_all_cache,
    get_installed_plugins_path,
    get_legacy_cache_path,
    get_orphaned_timestamp,
    get_plugin_cache_dir,
    get_versioned_cache_path,
    is_version_old_enough_to_delete,
    is_version_orphaned,
    list_cached_versions,
    load_installed_plugins,
    mark_version_orphaned,
    resolve_plugin_path,
    save_installed_plugins,
)
from .hooks import (
    HookDefinition,
    HookEventType,
    HookManager,
    HookType,
)
from .loader import (
    ParsedSource,
    PluginLoader,
    parse_source,
)
from .manifest import (
    ManifestParseError,
    parse_manifest,
    validate_manifest,
)
from .operations import (
    PluginOperation,
    PluginOperations,
)
from .registry import (
    HookHandler,
    PluginRegistry,
    get_plugin_registry,
    reset_plugin_registry,
)

__all__ = [
    # base
    "BasePlugin",
    "LoadedPlugin",
    "PluginAuthor",
    "PluginManifest",
    "PluginScope",
    "PluginSource",
    # builtin
    "BUILTIN_MARKETPLACE_NAME",
    "BuiltinPluginDefinition",
    "builtin_plugins_count",
    "get_builtin_plugin_definition",
    "get_builtin_plugins",
    "is_builtin_plugin_id",
    "register_builtin_plugin",
    # cache
    "CachedVersionInfo",
    "CleanupResult",
    "clear_all_cache",
    "cleanup_orphaned_plugin_versions",
    "get_installed_plugins_path",
    "get_legacy_cache_path",
    "get_orphaned_timestamp",
    "get_plugin_cache_dir",
    "get_versioned_cache_path",
    "is_version_old_enough_to_delete",
    "is_version_orphaned",
    "list_cached_versions",
    "load_installed_plugins",
    "mark_version_orphaned",
    "resolve_plugin_path",
    "save_installed_plugins",
    # hooks
    "HookDefinition",
    "HookEventType",
    "HookManager",
    "HookType",
    # loader
    "ParsedSource",
    "PluginLoader",
    "parse_source",
    # manifest
    "ManifestParseError",
    "parse_manifest",
    "validate_manifest",
    # operations
    "PluginOperation",
    "PluginOperations",
    # registry
    "HookHandler",
    "PluginRegistry",
    "get_plugin_registry",
    "reset_plugin_registry",
]
