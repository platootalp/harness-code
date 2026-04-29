"""Plugin version cache management.

Handles caching of downloaded plugins with version tracking,
orphaned version cleanup, and cache path resolution.

TypeScript equivalent: src/utils/plugins/cacheUtils.ts
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Constants
ORPHANED_AT_FILENAME = ".orphaned_at"
CLEANUP_AGE_SECONDS = 7 * 24 * 60 * 60  # 7 days


# =============================================================================
# Cache Path Resolution
# =============================================================================


def get_plugin_cache_dir(base_dir: str | None = None) -> str:
    """Get the base plugin cache directory.

    Args:
        base_dir: Base directory. Defaults to ~/.claude/plugins/cache/.

    Returns:
        Absolute path to the plugin cache directory.
    """
    if base_dir:
        return os.path.join(base_dir, "cache")

    return os.path.join(
        os.path.expanduser("~"),
        ".claude",
        "plugins",
        "cache",
    )


def get_versioned_cache_path(
    plugin_id: str,
    version: str,
    base_dir: str | None = None,
) -> str:
    """Compute the versioned cache path for a plugin.

    Format: {cache_dir}/{marketplace}/{plugin}/{version}/

    Args:
        plugin_id: Plugin identifier in format "name@marketplace" or just "name".
        version: Version string (semver, git SHA, etc.).
        base_dir: Base plugins directory. Defaults to ~/.claude/plugins/.

    Returns:
        Absolute path to the versioned plugin directory.
    """
    cache_dir = get_plugin_cache_dir(base_dir)

    # Parse plugin identifier
    if "@" in plugin_id:
        name, marketplace = plugin_id.rsplit("@", 1)
    else:
        name = plugin_id
        marketplace = "unknown"

    # Sanitize components for path safety
    safe_marketplace = re.sub(r"[^a-zA-Z0-9\-_]", "-", marketplace)
    safe_name = re.sub(r"[^a-zA-Z0-9\-_]", "-", name)
    safe_version = re.sub(r"[^a-zA-Z0-9\-_.]", "-", version)

    return os.path.join(cache_dir, safe_marketplace, safe_name, safe_version)


def get_legacy_cache_path(
    plugin_name: str,
    base_dir: str | None = None,
) -> str:
    """Get legacy (non-versioned) cache path for a plugin.

    Format: {cache_dir}/{plugin-name}/

    Used for backward compatibility with existing installations
    that don't use versioned paths.

    Args:
        plugin_name: Plugin name (without marketplace suffix).
        base_dir: Base plugins directory.

    Returns:
        Absolute path to the legacy plugin directory.
    """
    cache_dir = get_plugin_cache_dir(base_dir)
    safe_name = re.sub(r"[^a-zA-Z0-9\-_]", "-", plugin_name)
    return os.path.join(cache_dir, safe_name)


async def resolve_plugin_path(
    plugin_id: str,
    version: str | None = None,
    base_dir: str | None = None,
) -> str:
    """Resolve the plugin path with fallback to legacy location.

    Resolution order:
    1. Try versioned path first if version is provided
    2. Fall back to legacy path for existing installations
    3. Return versioned path for new installations

    Args:
        plugin_id: Plugin identifier.
        version: Optional version string.
        base_dir: Base plugins directory.

    Returns:
        Absolute path to the plugin directory.
    """
    # Try versioned path first
    if version:
        versioned_path = get_versioned_cache_path(plugin_id, version, base_dir)
        if os.path.exists(versioned_path):
            return versioned_path

    # Fall back to legacy path
    name = plugin_id.rsplit("@", 1)[0] if "@" in plugin_id else plugin_id
    legacy_path = get_legacy_cache_path(name, base_dir)
    if os.path.exists(legacy_path):
        return legacy_path

    # Return versioned path for new installations
    if version:
        return versioned_path
    return legacy_path


# =============================================================================
# Orphaned Version Cleanup
# =============================================================================


def mark_version_orphaned(version_path: str) -> bool:
    """Mark a plugin version as orphaned by writing a timestamp file.

    Called when a plugin is uninstalled or updated to a new version.
    Orphaned versions are eligible for cleanup after CLEANUP_AGE_SECONDS.

    Args:
        version_path: Absolute path to the orphaned plugin version directory.

    Returns:
        True if the file was written successfully.
    """
    orphaned_path = os.path.join(version_path, ORPHANED_AT_FILENAME)
    try:
        with open(orphaned_path, "w", encoding="utf-8") as f:
            f.write(str(int(time.time())))
        return True
    except OSError as e:
        logger.debug(f"Failed to write {ORPHANED_AT_FILENAME} at {version_path}: {e}")
        return False


def get_orphaned_timestamp(version_path: str) -> float | None:
    """Get the timestamp when a version was marked orphaned.

    Args:
        version_path: Path to the plugin version directory.

    Returns:
        Unix timestamp as float, or None if not orphaned.
    """
    orphaned_path = os.path.join(version_path, ORPHANED_AT_FILENAME)
    try:
        with open(orphaned_path, encoding="utf-8") as f:
            return float(f.read().strip())
    except (OSError, ValueError):
        return None


def is_version_orphaned(version_path: str) -> bool:
    """Check if a plugin version is marked as orphaned.

    Args:
        version_path: Path to the plugin version directory.

    Returns:
        True if the version is orphaned.
    """
    return os.path.exists(os.path.join(version_path, ORPHANED_AT_FILENAME))


def is_version_old_enough_to_delete(version_path: str) -> bool:
    """Check if an orphaned version is old enough to be deleted.

    Versions older than CLEANUP_AGE_SECONDS (7 days) are eligible
    for cleanup.

    Args:
        version_path: Path to the plugin version directory.

    Returns:
        True if the version should be deleted.
    """
    timestamp = get_orphaned_timestamp(version_path)
    if timestamp is None:
        return False

    return time.time() - timestamp >= CLEANUP_AGE_SECONDS


# =============================================================================
# Cache Cleanup
# =============================================================================


@dataclass
class CleanupResult:
    """Result of a cache cleanup operation.

    Attributes:
        deleted_count: Number of plugin versions deleted.
        errors: Any errors encountered during cleanup.
    """

    deleted_count: int
    errors: list[str]


async def cleanup_orphaned_plugin_versions(
    installed_versions: list[str],
    cache_dir: str | None = None,
) -> CleanupResult:
    """Clean up orphaned plugin versions in the cache.

    Iterates through cached plugin versions. If a version is not in
    the installed_versions list and has been orphaned for more than
    7 days, it is deleted.

    Args:
        installed_versions: List of installed version paths.
            Versions not in this list are considered orphaned.
        cache_dir: Cache directory to clean. Defaults to plugin cache dir.

    Returns:
        CleanupResult with deletion count and any errors.
    """
    cache = cache_dir or get_plugin_cache_dir()
    deleted_count = 0
    errors: list[str] = []

    if not os.path.exists(cache):
        return CleanupResult(deleted_count=0, errors=[])

    installed_set = set(installed_versions)

    try:
        for marketplace in os.listdir(cache):
            marketplace_path = os.path.join(cache, marketplace)
            if not os.path.isdir(marketplace_path):
                continue

            for plugin in os.listdir(marketplace_path):
                plugin_path = os.path.join(marketplace_path, plugin)
                if not os.path.isdir(plugin_path):
                    continue

                for version in os.listdir(plugin_path):
                    version_path = os.path.join(plugin_path, version)
                    if not os.path.isdir(version_path):
                        continue

                    # Skip installed versions
                    if version_path in installed_set:
                        continue

                    # Check if orphaned and old enough
                    if is_version_old_enough_to_delete(version_path):
                        try:
                            import shutil
                            shutil.rmtree(version_path)
                            deleted_count += 1
                            logger.debug(f"Cleaned up orphaned plugin: {version_path}")
                        except OSError as e:
                            errors.append(f"Failed to delete {version_path}: {e}")
                    else:
                        # Mark as orphaned if not already
                        mark_version_orphaned(version_path)

    except OSError as e:
        errors.append(f"Cache cleanup error: {e}")

    return CleanupResult(deleted_count=deleted_count, errors=errors)


async def clear_all_cache(cache_dir: str | None = None) -> CleanupResult:
    """Clear the entire plugin cache.

    Args:
        cache_dir: Cache directory to clear. Defaults to plugin cache dir.

    Returns:
        CleanupResult with deletion count.
    """
    import shutil

    cache = cache_dir or get_plugin_cache_dir()
    deleted_count = 0
    errors: list[str] = []

    if os.path.exists(cache):
        try:
            # Count entries before deleting
            for marketplace in os.listdir(cache):
                marketplace_path = os.path.join(cache, marketplace)
                if os.path.isdir(marketplace_path):
                    for plugin in os.listdir(marketplace_path):
                        plugin_path = os.path.join(marketplace_path, plugin)
                        if os.path.isdir(plugin_path):
                            deleted_count += 1

            shutil.rmtree(cache, ignore_errors=True)
        except OSError as e:
            errors.append(f"Failed to clear cache: {e}")

    return CleanupResult(deleted_count=deleted_count, errors=errors)


# =============================================================================
# Installed Plugins Tracking
# =============================================================================


def get_installed_plugins_path(base_dir: str | None = None) -> str:
    """Get the path to the installed plugins JSON file.

    Args:
        base_dir: Base plugins directory.

    Returns:
        Absolute path to installed_plugins.json.
    """
    base = base_dir or os.path.join(os.path.expanduser("~"), ".claude", "plugins")
    return os.path.join(base, "installed_plugins.json")


def load_installed_plugins(base_dir: str | None = None) -> dict[str, Any]:
    """Load the installed plugins registry from disk.

    Args:
        base_dir: Base plugins directory.

    Returns:
        Dictionary mapping plugin IDs to installation metadata.
    """
    path = get_installed_plugins_path(base_dir)
    try:
        with open(path, encoding="utf-8") as f:
            return cast("dict[str, Any]", json.load(f))
    except (OSError, json.JSONDecodeError):
        return {}


def save_installed_plugins(
    plugins: dict[str, Any],
    base_dir: str | None = None,
) -> bool:
    """Save the installed plugins registry to disk.

    Args:
        plugins: Dictionary mapping plugin IDs to installation metadata.
        base_dir: Base plugins directory.

    Returns:
        True if saved successfully.
    """
    path = get_installed_plugins_path(base_dir)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(plugins, f, indent=2)
        return True
    except OSError as e:
        logger.error(f"Failed to save installed plugins: {e}")
        return False


# =============================================================================
# Version Cache Info
# =============================================================================


@dataclass
class CachedVersionInfo:
    """Information about a cached plugin version.

    Attributes:
        path: Absolute path to the cached version.
        version: Version string.
        is_orphaned: Whether this version is marked as orphaned.
        orphaned_at: Unix timestamp when orphaned, or None.
    """

    path: str
    version: str
    is_orphaned: bool
    orphaned_at: float | None


def list_cached_versions(
    plugin_id: str,
    base_dir: str | None = None,
) -> list[CachedVersionInfo]:
    """List all cached versions for a plugin.

    Args:
        plugin_id: Plugin identifier.
        base_dir: Base plugins directory.

    Returns:
        List of CachedVersionInfo for each cached version.
    """
    versions: list[CachedVersionInfo] = []

    # Try marketplace subdir first
    if "@" in plugin_id:
        name, marketplace = plugin_id.rsplit("@", 1)
    else:
        name = plugin_id
        marketplace = "unknown"

    cache = get_plugin_cache_dir(base_dir)
    plugin_path = os.path.join(cache, marketplace, name)

    if not os.path.exists(plugin_path):
        return versions

    try:
        for version in os.listdir(plugin_path):
            version_path = os.path.join(plugin_path, version)
            if not os.path.isdir(version_path):
                continue

            orphaned_at = get_orphaned_timestamp(version_path)

            versions.append(CachedVersionInfo(
                path=version_path,
                version=version,
                is_orphaned=orphaned_at is not None,
                orphaned_at=orphaned_at,
            ))
    except OSError:
        pass

    return versions
