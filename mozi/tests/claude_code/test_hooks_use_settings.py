"""
Tests for hooks/use_settings.py - SettingsSlice and use_settings().
"""

from __future__ import annotations

import pytest

from src.claude_code.hooks.app_state_store import AppStateStore
from src.claude_code.hooks.use_settings import SettingsSlice, use_settings


class TestSettingsSlice:
    """Tests for SettingsSlice."""

    def test_get_returns_settings_dict(self) -> None:
        """get() returns the full settings dict."""
        store = AppStateStore({"settings": {"theme": "dark", "model": "claude"}})
        sl = SettingsSlice(store)
        settings = sl.get()
        assert settings == {"theme": "dark", "model": "claude"}

    def test_get_key_returns_value(self) -> None:
        """get_key() returns a specific setting value."""
        store = AppStateStore({"settings": {"theme": "dark"}})
        sl = SettingsSlice(store)
        assert sl.get_key("theme") == "dark"

    def test_get_key_with_default(self) -> None:
        """get_key() returns default when key is missing."""
        store = AppStateStore({"settings": {}})
        sl = SettingsSlice(store)
        assert sl.get_key("missing", "default_value") == "default_value"
        assert sl.get_key("missing") is None

    def test_has_key(self) -> None:
        """has_key() checks for key existence."""
        store = AppStateStore({"settings": {"exists": True}})
        sl = SettingsSlice(store)
        assert sl.has_key("exists") is True
        assert sl.has_key("missing") is False

    def test_settings_updates_reflect(self) -> None:
        """Changes to state are reflected in SettingsSlice."""
        store = AppStateStore({"settings": {"v": 1}})
        sl = SettingsSlice(store)
        store.set(lambda s: {**s, "settings": {**s["settings"], "v": 2}})
        assert sl.get_key("v") == 2

    def test_repr(self) -> None:
        """__repr__ includes the number of keys."""
        store = AppStateStore({"settings": {"a": 1, "b": 2}})
        sl = SettingsSlice(store)
        assert "2 keys" in repr(sl)


class TestUseSettings:
    """Tests for use_settings() function."""

    def test_use_settings_with_explicit_store(self) -> None:
        """use_settings(store) uses the provided store."""
        store = AppStateStore({"settings": {"key": "value"}})
        sl = use_settings(store)
        assert sl.get_key("key") == "value"

    def test_use_settings_empty_store(self) -> None:
        """use_settings() handles missing settings key."""
        store = AppStateStore({})
        sl = use_settings(store)
        assert sl.get() == {}
        assert sl.get_key("anything") is None
