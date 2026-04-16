"""
Tests for plugins/operations.py - Plugin install/uninstall/enable/disable operations.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from src.claude_code.plugins.base import PluginScope
from src.claude_code.plugins.registry import PluginRegistry


class TestPluginOperationEnum:
    """Tests for PluginOperation enum values."""

    def test_operation_values(self) -> None:
        """PluginOperation enum has correct values."""
        from src.claude_code.plugins.operations import PluginOperation

        assert PluginOperation.INSTALL.value == "install"
        assert PluginOperation.UNINSTALL.value == "uninstall"
        assert PluginOperation.ENABLE.value == "enable"
        assert PluginOperation.DISABLE.value == "disable"
        assert PluginOperation.UPDATE.value == "update"

    def test_operation_is_string_enum(self) -> None:
        """PluginOperation is a string enum."""
        from src.claude_code.plugins.operations import PluginOperation

        op = PluginOperation.INSTALL
        assert isinstance(op, str)
        assert op == "install"


class TestPluginOperationsInit:
    """Tests for PluginOperations initialization."""

    def test_create_with_default_config_path(self) -> None:
        """Create operations with default config path."""
        from src.claude_code.plugins.operations import PluginOperations

        registry = PluginRegistry()
        ops = PluginOperations(registry=registry)
        assert ops.registry is registry
        # Default config path should be under ~/.claude/settings.json
        expected = Path.home() / ".claude" / "settings.json"
        assert ops.config_path == expected

    def test_create_with_custom_config_path(self) -> None:
        """Create operations with custom config path."""
        from src.claude_code.plugins.operations import PluginOperations

        registry = PluginRegistry()
        custom_path = Path("/tmp/test-plugins.json")
        ops = PluginOperations(registry=registry, config_path=custom_path)
        assert ops.config_path == custom_path


class TestLoadConfig:
    """Tests for configuration loading."""

    @pytest.mark.asyncio
    async def test_load_empty_config(self) -> None:
        """Loading nonexistent config returns empty dict."""
        from src.claude_code.plugins.operations import PluginOperations

        registry = PluginRegistry()
        ops = PluginOperations(registry=registry, config_path=Path("/tmp/nonexistent-config-12345.json"))
        config = await ops._load_config()
        assert config == {}

    @pytest.mark.asyncio
    async def test_load_existing_config(self) -> None:
        """Loading existing config returns parsed JSON."""
        from src.claude_code.plugins.operations import PluginOperations

        registry = PluginRegistry()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"plugins": {"test-plugin": {"source": "npm", "enabled": True}}}, f)
            config_path = Path(f.name)

        try:
            ops = PluginOperations(registry=registry, config_path=config_path)
            config = await ops._load_config()
            assert config["plugins"]["test-plugin"]["source"] == "npm"
        finally:
            config_path.unlink(missing_ok=True)


class TestSaveConfig:
    """Tests for configuration saving."""

    @pytest.mark.asyncio
    async def test_save_config_creates_parent_dirs(self) -> None:
        """Saving config creates parent directories."""
        from src.claude_code.plugins.operations import PluginOperations

        registry = PluginRegistry()
        tmp_dir = Path(tempfile.mkdtemp())
        config_path = tmp_dir / ".claude" / "settings.json"

        try:
            ops = PluginOperations(registry=registry, config_path=config_path)
            await ops._save_config({"plugins": {}})
            assert config_path.exists()
            assert json.loads(config_path.read_text()) == {"plugins": {}}
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_save_config_formats_json(self) -> None:
        """Saving config writes formatted JSON."""
        from src.claude_code.plugins.operations import PluginOperations

        registry = PluginRegistry()
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "settings.json"
            ops = PluginOperations(registry=registry, config_path=config_path)
            await ops._save_config({"plugins": {"test": {"enabled": True}}})
            content = config_path.read_text()
            # Should be readable JSON with indentation
            parsed = json.loads(content)
            assert parsed["plugins"]["test"]["enabled"] is True


class TestInstallPlugin:
    """Tests for plugin installation."""

    @pytest.mark.asyncio
    async def test_install_creates_plugin_entry(self) -> None:
        """Install creates plugin entry in config."""
        from src.claude_code.plugins.operations import PluginOperations

        registry = PluginRegistry()
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "settings.json"
            ops = PluginOperations(registry=registry, config_path=config_path)

            await ops.install_plugin("my-plugin", "npm:my-plugin", scope=PluginScope.USER)

            config = json.loads(config_path.read_text())
            assert "plugins" in config
            assert "my-plugin" in config["plugins"]
            assert config["plugins"]["my-plugin"]["source"] == "npm:my-plugin"
            assert config["plugins"]["my-plugin"]["scope"] == "user"
            assert config["plugins"]["my-plugin"]["enabled"] is True

    @pytest.mark.asyncio
    async def test_install_with_existing_config(self) -> None:
        """Install merges with existing config."""
        from src.claude_code.plugins.operations import PluginOperations

        registry = PluginRegistry()
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "settings.json"
            config_path.write_text(json.dumps({"plugins": {"existing": {"source": "pip:existing", "enabled": False}}}))

            ops = PluginOperations(registry=registry, config_path=config_path)
            await ops.install_plugin("new-plugin", "npm:new-plugin")

            config = json.loads(config_path.read_text())
            assert "existing" in config["plugins"]
            assert "new-plugin" in config["plugins"]
            assert config["plugins"]["existing"]["source"] == "pip:existing"
            assert config["plugins"]["new-plugin"]["source"] == "npm:new-plugin"

    @pytest.mark.asyncio
    async def test_install_creates_plugins_section(self) -> None:
        """Install creates plugins section if missing."""
        from src.claude_code.plugins.operations import PluginOperations

        registry = PluginRegistry()
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "settings.json"
            config_path.write_text(json.dumps({"other": "data"}))

            ops = PluginOperations(registry=registry, config_path=config_path)
            await ops.install_plugin("test", "npm:test")

            config = json.loads(config_path.read_text())
            assert "other" in config
            assert "plugins" in config
            assert "test" in config["plugins"]


class TestUninstallPlugin:
    """Tests for plugin uninstallation."""

    @pytest.mark.asyncio
    async def test_uninstall_removes_plugin(self) -> None:
        """Uninstall removes plugin from config."""
        from src.claude_code.plugins.operations import PluginOperations

        registry = PluginRegistry()
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "settings.json"
            config_path.write_text(json.dumps({"plugins": {"my-plugin": {"source": "npm:my-plugin", "enabled": True}}}))

            ops = PluginOperations(registry=registry, config_path=config_path)
            await ops.uninstall_plugin("my-plugin")

            config = json.loads(config_path.read_text())
            assert "plugins" in config
            assert "my-plugin" not in config["plugins"]

    @pytest.mark.asyncio
    async def test_uninstall_nonexistent_plugin(self) -> None:
        """Uninstalling nonexistent plugin does not error."""
        from src.claude_code.plugins.operations import PluginOperations

        registry = PluginRegistry()
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "settings.json"
            config_path.write_text(json.dumps({"plugins": {}}))

            ops = PluginOperations(registry=registry, config_path=config_path)
            # Should not raise
            await ops.uninstall_plugin("nonexistent")


class TestEnablePlugin:
    """Tests for enabling plugins."""

    @pytest.mark.asyncio
    async def test_enable_sets_enabled_true(self) -> None:
        """Enable sets plugin enabled flag to True."""
        from src.claude_code.plugins.operations import PluginOperations

        registry = PluginRegistry()
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "settings.json"
            config_path.write_text(json.dumps({"plugins": {"my-plugin": {"source": "npm:my-plugin", "enabled": False}}}))

            ops = PluginOperations(registry=registry, config_path=config_path)
            await ops.enable_plugin("my-plugin")

            config = json.loads(config_path.read_text())
            assert config["plugins"]["my-plugin"]["enabled"] is True

    @pytest.mark.asyncio
    async def test_enable_nonexistent_plugin(self) -> None:
        """Enabling nonexistent plugin does not error."""
        from src.claude_code.plugins.operations import PluginOperations

        registry = PluginRegistry()
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "settings.json"
            config_path.write_text(json.dumps({"plugins": {}}))

            ops = PluginOperations(registry=registry, config_path=config_path)
            # Should not raise
            await ops.enable_plugin("nonexistent")


class TestDisablePlugin:
    """Tests for disabling plugins."""

    @pytest.mark.asyncio
    async def test_disable_sets_enabled_false(self) -> None:
        """Disable sets plugin enabled flag to False."""
        from src.claude_code.plugins.operations import PluginOperations

        registry = PluginRegistry()
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "settings.json"
            config_path.write_text(json.dumps({"plugins": {"my-plugin": {"source": "npm:my-plugin", "enabled": True}}}))

            ops = PluginOperations(registry=registry, config_path=config_path)
            await ops.disable_plugin("my-plugin")

            config = json.loads(config_path.read_text())
            assert config["plugins"]["my-plugin"]["enabled"] is False

    @pytest.mark.asyncio
    async def test_disable_nonexistent_plugin(self) -> None:
        """Disabling nonexistent plugin does not error."""
        from src.claude_code.plugins.operations import PluginOperations

        registry = PluginRegistry()
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "settings.json"
            config_path.write_text(json.dumps({"plugins": {}}))

            ops = PluginOperations(registry=registry, config_path=config_path)
            # Should not raise
            await ops.disable_plugin("nonexistent")


class TestPluginOperationsIntegration:
    """Integration tests for full plugin operation workflows."""

    @pytest.mark.asyncio
    async def test_install_enable_disable_uninstall_flow(self) -> None:
        """Full workflow: install, enable, disable, uninstall."""
        from src.claude_code.plugins.operations import PluginOperations

        registry = PluginRegistry()
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "settings.json"
            ops = PluginOperations(registry=registry, config_path=config_path)

            # Install
            await ops.install_plugin("workflow-plugin", "npm:workflow-plugin", scope=PluginScope.USER)
            config = json.loads(config_path.read_text())
            assert config["plugins"]["workflow-plugin"]["enabled"] is True

            # Disable
            await ops.disable_plugin("workflow-plugin")
            config = json.loads(config_path.read_text())
            assert config["plugins"]["workflow-plugin"]["enabled"] is False

            # Enable
            await ops.enable_plugin("workflow-plugin")
            config = json.loads(config_path.read_text())
            assert config["plugins"]["workflow-plugin"]["enabled"] is True

            # Uninstall
            await ops.uninstall_plugin("workflow-plugin")
            config = json.loads(config_path.read_text())
            assert "workflow-plugin" not in config["plugins"]

    @pytest.mark.asyncio
    async def test_install_multiple_plugins(self) -> None:
        """Install multiple plugins without conflict."""
        from src.claude_code.plugins.operations import PluginOperations

        registry = PluginRegistry()
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "settings.json"
            ops = PluginOperations(registry=registry, config_path=config_path)

            await ops.install_plugin("plugin-a", "npm:plugin-a")
            await ops.install_plugin("plugin-b", "pip:plugin-b")
            await ops.install_plugin("plugin-c", "git:https://github.com/c/plugin-c")

            config = json.loads(config_path.read_text())
            assert len(config["plugins"]) == 3
            assert config["plugins"]["plugin-a"]["source"] == "npm:plugin-a"
            assert config["plugins"]["plugin-b"]["source"] == "pip:plugin-b"
            assert config["plugins"]["plugin-c"]["source"] == "git:https://github.com/c/plugin-c"
