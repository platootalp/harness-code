"""Tests for utils/hooks_config_manager.py."""

from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import patch

import pytest

from claude_code.utils.hooks_config_manager import (
    HookConfig,
    HooksConfig,
    HooksConfigManager,
    HooksConfigSnapshot,
    create_config_snapshot,
    get_default_hooks_dir,
    get_hooks_config_path,
    load_hooks_config,
    merge_hooks_configs,
    register_hooks_from_config,
    unregister_hooks_from_config,
    validate_hook_config,
)


class TestHookConfig:
    """Tests for HookConfig."""

    def test_basic(self) -> None:
        config = HookConfig(
            name="test-hook",
            event="PreToolUse",
            command="echo hello",
        )
        assert config.name == "test-hook"
        assert config.event == "PreToolUse"
        assert config.enabled is True


class TestHooksConfig:
    """Tests for HooksConfig."""

    def test_empty(self) -> None:
        config = HooksConfig()
        assert config.hooks == []
        assert config.version == "1.0"


class TestLoadHooksConfig:
    """Tests for load_hooks_config."""

    def test_nonexistent_file(self) -> None:
        config = load_hooks_config("/nonexistent/path/hooks.json")
        assert config.hooks == []

    def test_invalid_json(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not json")
            path = f.name
        try:
            config = load_hooks_config(path)
            assert config.hooks == []
        finally:
            os.unlink(path)

    def test_valid_config(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(
                {
                    "version": "1.0",
                    "hooks": [
                        {
                            "name": "my-hook",
                            "event": "PreToolUse",
                            "command": "/bin/echo",
                            "timeout_ms": 5000,
                        }
                    ],
                },
                f,
            )
            path = f.name
        try:
            config = load_hooks_config(path)
            assert len(config.hooks) == 1
            assert config.hooks[0].name == "my-hook"
            assert config.hooks[0].timeout_ms == 5000
        finally:
            os.unlink(path)


class TestMergeHooksConfigs:
    """Tests for merge_hooks_configs."""

    def test_merge_empty(self) -> None:
        result = merge_hooks_configs(HooksConfig(), HooksConfig())
        assert result.hooks == []

    def test_merge_unique(self) -> None:
        config1 = HooksConfig(
            hooks=[
                HookConfig(name="hook1", event="PreToolUse", command="echo 1"),
            ]
        )
        config2 = HooksConfig(
            hooks=[
                HookConfig(name="hook2", event="PostToolUse", command="echo 2"),
            ]
        )
        result = merge_hooks_configs(config1, config2)
        assert len(result.hooks) == 2

    def test_merge_override(self) -> None:
        config1 = HooksConfig(
            hooks=[
                HookConfig(
                    name="hook1", event="PreToolUse", command="echo old", timeout_ms=1000
                ),
            ]
        )
        config2 = HooksConfig(
            hooks=[
                HookConfig(
                    name="hook1", event="PreToolUse", command="echo new", timeout_ms=2000
                ),
            ]
        )
        result = merge_hooks_configs(config1, config2)
        assert len(result.hooks) == 1
        assert result.hooks[0].command == "echo new"
        assert result.hooks[0].timeout_ms == 2000


class TestValidateHookConfig:
    """Tests for validate_hook_config."""

    def test_valid(self) -> None:
        hook = HookConfig(name="valid-hook", event="PreToolUse", command="echo")
        errors = validate_hook_config(hook)
        assert errors == []

    def test_missing_name(self) -> None:
        hook = HookConfig(name="", event="PreToolUse", command="echo")
        errors = validate_hook_config(hook)
        assert any("name" in e for e in errors)

    def test_invalid_name_chars(self) -> None:
        hook = HookConfig(name="hook with space", event="PreToolUse", command="echo")
        errors = validate_hook_config(hook)
        assert any("invalid characters" in e for e in errors)

    def test_invalid_event(self) -> None:
        hook = HookConfig(name="test", event="InvalidEvent", command="echo")
        errors = validate_hook_config(hook)
        assert any("Invalid event" in e for e in errors)

    def test_missing_command(self) -> None:
        hook = HookConfig(name="test", event="PreToolUse", command="")
        errors = validate_hook_config(hook)
        assert any("command" in e for e in errors)

    def test_invalid_timeout(self) -> None:
        hook = HookConfig(name="test", event="PreToolUse", command="echo", timeout_ms=0)
        errors = validate_hook_config(hook)
        assert any("timeout" in e for e in errors)


class TestGetHooksConfigPath:
    """Tests for get_hooks_config_path."""

    def test_no_config(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            result = get_hooks_config_path()
            # Returns None or path if .claude/hooks.json exists
            assert result is None or isinstance(result, str)


class TestGetDefaultHooksDir:
    """Tests for get_default_hooks_dir."""

    def test_returns_path(self) -> None:
        path = get_default_hooks_dir()
        assert "claude" in path
        assert "hooks" in path


class TestCreateConfigSnapshot:
    """Tests for create_config_snapshot."""

    def test_creates_snapshot(self) -> None:
        config = HooksConfig(
            hooks=[HookConfig(name="h", event="PreToolUse", command="echo")]
        )
        snapshot = create_config_snapshot(config, "/tmp/hooks.json")
        assert snapshot.config is config
        assert snapshot.loaded_at != ""
        assert snapshot.config_path == "/tmp/hooks.json"


class TestHooksConfigManager:
    """Tests for HooksConfigManager."""

    def test_load_nonexistent(self) -> None:
        manager = HooksConfigManager()
        config = manager.load("/nonexistent/hooks.json")
        assert config.hooks == []

    def test_reload(self) -> None:
        manager = HooksConfigManager()
        manager.load("/nonexistent/hooks.json")
        manager.reload()

    def test_get_snapshot(self) -> None:
        manager = HooksConfigManager()
        manager.load("/nonexistent/hooks.json")
        snapshot = manager.get_snapshot()
        assert snapshot is not None

    def test_clear(self) -> None:
        manager = HooksConfigManager()
        manager.load("/nonexistent/hooks.json")
        manager.clear()
        assert manager.get_snapshot() is None
