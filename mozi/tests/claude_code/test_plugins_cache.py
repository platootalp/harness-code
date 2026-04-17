"""
Tests for plugins/cache.py - Plugin version cache management.
"""

from __future__ import annotations

import json
import os
import time

import pytest

from src.claude_code.plugins.cache import (
    CLEANUP_AGE_SECONDS,
    ORPHANED_AT_FILENAME,
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


class TestGetPluginCacheDir:
    """Tests for get_plugin_cache_dir()."""

    def test_default_cache_dir(self) -> None:
        """Default cache dir is under ~/.claude/plugins/cache/."""
        cache_dir = get_plugin_cache_dir()
        assert cache_dir.endswith(".claude/plugins/cache")
        assert "~" not in cache_dir

    def test_custom_base_dir(self) -> None:
        """Custom base dir appends 'cache' subdirectory."""
        cache_dir = get_plugin_cache_dir("/custom/path")
        assert cache_dir == "/custom/path/cache"


class TestGetVersionedCachePath:
    """Tests for get_versioned_cache_path()."""

    def test_simple_plugin_id(self) -> None:
        """Simple plugin name creates correct path."""
        path = get_versioned_cache_path("my-plugin", "1.0.0")
        assert "my-plugin" in path
        assert "1.0.0" in path
        assert "unknown" in path  # marketplace defaults to unknown

    def test_plugin_id_with_marketplace(self) -> None:
        """Plugin ID with marketplace creates correct path."""
        path = get_versioned_cache_path("my-plugin@npm", "1.0.0")
        assert "npm" in path
        assert "my-plugin" in path
        assert "1.0.0" in path

    def test_special_characters_sanitized(self) -> None:
        """Special characters in plugin ID are sanitized for path safety."""
        path = get_versioned_cache_path("my plugin!@#$%@npm", "v1.0.0+build")
        assert "!" not in path
        assert "@" not in path
        assert "#" not in path


class TestGetLegacyCachePath:
    """Tests for get_legacy_cache_path()."""

    def test_simple_name(self) -> None:
        """Simple plugin name creates correct path."""
        path = get_legacy_cache_path("my-plugin")
        assert "my-plugin" in path

    def test_special_characters_sanitized(self) -> None:
        """Special characters are sanitized."""
        path = get_legacy_cache_path("my plugin!")
        assert "!" not in path
        assert "my" in path


class TestResolvePluginPath:
    """Tests for resolve_plugin_path()."""

    @pytest.mark.asyncio
    async def test_returns_versioned_when_exists(self, tmp_path: pytest.TempPathFactory) -> None:
        """Returns versioned path when it exists."""
        cache = tmp_path / "cache"
        cache.mkdir()
        versioned = cache / "cache" / "npm" / "pkg" / "1.0.0"
        versioned.mkdir(parents=True)

        result = await resolve_plugin_path("pkg@npm", "1.0.0", str(tmp_path))
        assert result.endswith("npm/pkg/1.0.0")

    @pytest.mark.asyncio
    async def test_falls_back_to_legacy(self, tmp_path: pytest.TempPathFactory) -> None:
        """Falls back to legacy path when versioned doesn't exist."""
        cache = tmp_path / "cache"
        cache.mkdir()
        legacy = cache / "cache" / "pkg"
        legacy.mkdir(parents=True)

        result = await resolve_plugin_path("pkg", base_dir=str(tmp_path))
        assert result.endswith("pkg")

    @pytest.mark.asyncio
    async def test_returns_versioned_for_new_install(self, tmp_path: pytest.TempPathFactory) -> None:
        """Returns versioned path for new installations."""
        cache = tmp_path / "cache"
        cache.mkdir()

        result = await resolve_plugin_path("new-pkg@npm", "1.0.0", str(tmp_path))
        assert result.endswith("npm/new-pkg/1.0.0")


class TestOrphanedMarker:
    """Tests for orphaned version tracking."""

    def test_mark_version_orphaned(self, tmp_path: pytest.TempPathFactory) -> None:
        """Marking a version creates the orphaned timestamp file."""
        version_dir = tmp_path / "v1"
        version_dir.mkdir()
        result = mark_version_orphaned(str(version_dir))
        assert result is True
        assert is_version_orphaned(str(version_dir)) is True

    def test_get_orphaned_timestamp(self, tmp_path: pytest.TempPathFactory) -> None:
        """Get orphaned timestamp returns Unix timestamp."""
        version_dir = tmp_path / "v1"
        version_dir.mkdir()
        mark_version_orphaned(str(version_dir))
        timestamp = get_orphaned_timestamp(str(version_dir))
        assert timestamp is not None
        assert timestamp > 0

    def test_not_orphaned_without_marker(self, tmp_path: pytest.TempPathFactory) -> None:
        """Version without marker is not orphaned."""
        version_dir = tmp_path / "v1"
        version_dir.mkdir()
        assert is_version_orphaned(str(version_dir)) is False
        assert get_orphaned_timestamp(str(version_dir)) is None

    def test_is_version_old_enough_to_delete(self, tmp_path: pytest.TempPathFactory) -> None:
        """Version is old enough after CLEANUP_AGE_SECONDS."""
        version_dir = tmp_path / "v1"
        version_dir.mkdir()

        # Not old enough initially
        assert is_version_old_enough_to_delete(str(version_dir)) is False

        # Write old timestamp
        old_timestamp = time.time() - CLEANUP_AGE_SECONDS - 1
        orphaned_file = version_dir / ORPHANED_AT_FILENAME
        orphaned_file.write_text(str(int(old_timestamp)))

        # Now old enough
        assert is_version_old_enough_to_delete(str(version_dir)) is True


class TestCleanupOrphanedPluginVersions:
    """Tests for cleanup_orphaned_plugin_versions()."""

    @pytest.mark.asyncio
    async def test_cleanup_removes_old_orphaned(self, tmp_path: pytest.TempPathFactory) -> None:
        """Old orphaned versions are deleted."""
        cache = tmp_path / "cache"
        cache.mkdir()

        # Create orphaned version directory
        old_dir = cache / "npm" / "old-plugin" / "1.0.0"
        old_dir.mkdir(parents=True)
        mark_version_orphaned(str(old_dir))

        # Make it old enough
        old_file = old_dir / ORPHANED_AT_FILENAME
        old_file.write_text(str(int(time.time() - CLEANUP_AGE_SECONDS - 1)))

        result = await cleanup_orphaned_plugin_versions(
            installed_versions=[], cache_dir=str(cache)
        )
        assert result.deleted_count == 1
        assert not old_dir.exists()

    @pytest.mark.asyncio
    async def test_cleanup_keeps_recent_orphaned(self, tmp_path: pytest.TempPathFactory) -> None:
        """Recent orphaned versions are kept."""
        cache = tmp_path / "cache"
        cache.mkdir()

        recent_dir = cache / "npm" / "recent-plugin" / "1.0.0"
        recent_dir.mkdir(parents=True)
        mark_version_orphaned(str(recent_dir))

        result = await cleanup_orphaned_plugin_versions(
            installed_versions=[], cache_dir=str(cache)
        )
        assert result.deleted_count == 0
        assert recent_dir.exists()

    @pytest.mark.asyncio
    async def test_cleanup_keeps_installed_versions(self, tmp_path: pytest.TempPathFactory) -> None:
        """Installed versions are never deleted."""
        cache = tmp_path / "cache"
        cache.mkdir()

        installed_dir = cache / "npm" / "installed" / "1.0.0"
        installed_dir.mkdir(parents=True)

        result = await cleanup_orphaned_plugin_versions(
            installed_versions=[str(installed_dir)], cache_dir=str(cache)
        )
        assert result.deleted_count == 0
        assert installed_dir.exists()


class TestClearAllCache:
    """Tests for clear_all_cache()."""

    @pytest.mark.asyncio
    async def test_clears_existing_cache(self, tmp_path: pytest.TempPathFactory) -> None:
        """Clearing removes all cached plugins."""
        cache = tmp_path / "cache"
        cache.mkdir()

        plugin_dir = cache / "npm" / "to-clear"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "1.0.0").mkdir()

        result = await clear_all_cache(cache_dir=str(cache))
        assert result.deleted_count == 1
        assert not cache.exists()

    @pytest.mark.asyncio
    async def test_nonexistent_cache_returns_zero(self, tmp_path: pytest.TempPathFactory) -> None:
        """Non-existent cache returns zero deletions."""
        fake_cache = tmp_path / "nonexistent"
        result = await clear_all_cache(cache_dir=str(fake_cache))
        assert result.deleted_count == 0
        assert result.errors == []


class TestInstalledPluginsTracking:
    """Tests for installed plugins JSON tracking."""

    def test_get_installed_plugins_path(self, tmp_path: pytest.TempPathFactory) -> None:
        """Path is under base_dir."""
        base = tmp_path / "plugins"
        path = get_installed_plugins_path(str(base))
        assert path.endswith("installed_plugins.json")

    def test_save_and_load_installed_plugins(self, tmp_path: pytest.TempPathFactory) -> None:
        """Save and load round-trip."""
        base = tmp_path / "plugins"
        plugins = {
            "plugin-a@npm": {"version": "1.0.0", "path": "/a"},
            "plugin-b@builtin": {"version": "2.0.0", "enabled": True},
        }
        result = save_installed_plugins(plugins, str(base))
        assert result is True

        loaded = load_installed_plugins(str(base))
        assert loaded == plugins

    def test_load_nonexistent_returns_empty(self, tmp_path: pytest.TempPathFactory) -> None:
        """Loading non-existent file returns empty dict."""
        result = load_installed_plugins(str(tmp_path / "nonexistent"))
        assert result == {}

    def test_load_corrupted_json_returns_empty(self, tmp_path: pytest.TempPathFactory) -> None:
        """Loading corrupted JSON returns empty dict."""
        plugins_file = tmp_path / "installed_plugins.json"
        plugins_file.write_text("not valid json {")
        result = load_installed_plugins(str(tmp_path))
        assert result == {}


class TestListCachedVersions:
    """Tests for list_cached_versions()."""

    def test_lists_all_versions(self, tmp_path: pytest.TempPathFactory) -> None:
        """Lists all cached versions for a plugin."""
        cache = tmp_path / "cache"
        cache.mkdir()

        plugin_dir = cache / "npm" / "multi-version"
        plugin_dir.mkdir(parents=True)

        v1 = plugin_dir / "1.0.0"
        v1.mkdir()
        v2 = plugin_dir / "2.0.0"
        v2.mkdir()

        # Pass tmp_path as base_dir (get_plugin_cache_dir appends "cache")
        versions = list_cached_versions("multi-version@npm", str(tmp_path))
        assert len(versions) == 2
        versions_by_ver = {v.version: v for v in versions}
        assert "1.0.0" in versions_by_ver
        assert "2.0.0" in versions_by_ver

    def test_marks_orphaned_versions(self, tmp_path: pytest.TempPathFactory) -> None:
        """Orphaned versions are flagged."""
        cache = tmp_path / "cache"
        cache.mkdir()

        plugin_dir = cache / "npm" / "orphaned-test"
        plugin_dir.mkdir(parents=True)

        active = plugin_dir / "1.0.0"
        active.mkdir()

        orphaned = plugin_dir / "0.9.0"
        orphaned.mkdir()
        mark_version_orphaned(str(orphaned))

        versions = list_cached_versions("orphaned-test@npm", str(tmp_path))
        versions_by_ver = {v.version: v for v in versions}

        assert versions_by_ver["1.0.0"].is_orphaned is False
        assert versions_by_ver["0.9.0"].is_orphaned is True

    def test_nonesistent_plugin_returns_empty(self, tmp_path: pytest.TempPathFactory) -> None:
        """Non-existent plugin returns empty list."""
        cache = tmp_path / "cache"
        cache.mkdir()
        versions = list_cached_versions("nonexistent@npm", str(tmp_path))
        assert versions == []
