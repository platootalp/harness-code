"""
Tests for plugins/base.py and plugins/registry.py
"""

from __future__ import annotations

import pytest
from claude_code.plugins.base import (
    BasePlugin,
    LoadedPlugin,
    PluginAuthor,
    PluginManifest,
    PluginScope,
    PluginSource,
)
from claude_code.plugins.registry import (
    HookHandler,
    PluginRegistry,
    get_plugin_registry,
    reset_plugin_registry,
)

# =============================================================================
# Test Helpers
# =============================================================================


class DummyPlugin(BasePlugin):
    """Dummy plugin for testing."""

    def __init__(self, name: str = "dummy", version: str = "1.0.0") -> None:
        super().__init__(
            PluginManifest(name=name, version=version, description="A test plugin")
        )
        self._load_called = False
        self._enable_called = False
        self._disable_called = False

    async def on_load(self) -> None:
        self._load_called = True

    async def on_enable(self) -> None:
        self._enable_called = True

    async def on_disable(self) -> None:
        self._disable_called = True


class DummyCustomPlugin(BasePlugin):
    """Dummy plugin that accepts a custom manifest."""

    def __init__(self, manifest: PluginManifest) -> None:
        super().__init__(manifest)
        self._load_called = False
        self._enable_called = False
        self._disable_called = False

    async def on_load(self) -> None:
        self._load_called = True

    async def on_enable(self) -> None:
        self._enable_called = True

    async def on_disable(self) -> None:
        self._disable_called = True


class BlockingPlugin(BasePlugin):
    """Plugin that blocks PreToolUse hooks."""

    def __init__(self, name: str = "blocking") -> None:
        super().__init__(
            PluginManifest(name=name, version="1.0.0", description="Blocks hooks")
        )

    async def on_load(self) -> None:
        pass

    async def on_enable(self) -> None:
        pass

    async def on_disable(self) -> None:
        pass


# =============================================================================
# PluginScope Tests
# =============================================================================


class TestPluginScope:
    def test_values(self) -> None:
        """PluginScope should have all expected values."""
        assert PluginScope.MANAGED.value == "managed"
        assert PluginScope.USER.value == "user"
        assert PluginScope.PROJECT.value == "project"
        assert PluginScope.LOCAL.value == "local"


# =============================================================================
# PluginSource Tests
# =============================================================================


class TestPluginSource:
    def test_values(self) -> None:
        """PluginSource should have all expected values."""
        assert PluginSource.NPM.value == "npm"
        assert PluginSource.PIP.value == "pip"
        assert PluginSource.GIT.value == "git"
        assert PluginSource.GITHUB.value == "github"
        assert PluginSource.LOCAL.value == "local"
        assert PluginSource.MANAGED.value == "managed"
        assert PluginSource.BUILTIN.value == "builtin"


# =============================================================================
# PluginManifest Tests
# =============================================================================


class TestPluginManifest:
    def test_create_minimal(self) -> None:
        """PluginManifest should create with required fields."""
        manifest = PluginManifest(name="test-plugin")
        assert manifest.name == "test-plugin"
        assert manifest.version == "1.0.0"
        assert manifest.description == ""
        assert manifest.license == "MIT"
        assert manifest.keywords == []
        assert manifest.dependencies == []

    def test_create_full(self) -> None:
        """PluginManifest should create with all fields."""
        manifest = PluginManifest(
            name="full-plugin",
            version="2.0.0",
            description="Full featured plugin",
            author={"name": "Test Author", "email": "test@example.com"},
            homepage="https://example.com",
            repository="https://github.com/example/plugin",
            license="Apache-2.0",
            keywords=["test", "example"],
            dependencies=["other-plugin@marketplace"],
            commands=["commands/*.md"],
            agents=["agents/*.md"],
            skills=["skills/**/*.md"],
            hooks={"PreToolUse": []},
        )
        assert manifest.name == "full-plugin"
        assert manifest.version == "2.0.0"
        assert manifest.author is not None
        assert manifest.author["name"] == "Test Author"
        assert len(manifest.keywords) == 2


# =============================================================================
# LoadedPlugin Tests
# =============================================================================


class TestLoadedPlugin:
    def test_plugin_id_builtin(self) -> None:
        """plugin_id should include @builtin for built-in plugins."""
        plugin = LoadedPlugin(
            name="brainstorm",
            manifest=PluginManifest(name="brainstorm"),
            path="builtin",
            source="brainstorm@builtin",
            is_builtin=True,
        )
        assert plugin.plugin_id == "brainstorm@builtin"

    def test_plugin_id_regular(self) -> None:
        """plugin_id should return source for regular plugins."""
        plugin = LoadedPlugin(
            name="my-plugin",
            manifest=PluginManifest(name="my-plugin"),
            path="/path/to/plugin",
            source="npm:my-plugin",
        )
        assert plugin.plugin_id == "npm:my-plugin"


# =============================================================================
# BasePlugin Tests
# =============================================================================


class TestBasePlugin:
    def test_properties(self) -> None:
        """Plugin should expose manifest properties."""
        plugin = DummyPlugin("test", "3.0.0")
        assert plugin.name == "test"
        assert plugin.version == "3.0.0"
        assert plugin.description == "A test plugin"
        assert not plugin.is_enabled()

    def test_manifest_passed_through(self) -> None:
        """Plugin should expose properties from its manifest."""
        manifest = PluginManifest(
            name="custom",
            version="5.0.0",
            description="Custom description",
        )
        plugin = DummyCustomPlugin(manifest)
        assert plugin.name == "custom"
        assert plugin.version == "5.0.0"
        assert plugin.description == "Custom description"

    def test_set_enabled(self) -> None:
        """set_enabled should update enabled state."""
        plugin = DummyPlugin()
        assert not plugin.is_enabled()
        plugin.set_enabled(True)
        assert plugin.is_enabled()
        plugin.set_enabled(False)
        assert not plugin.is_enabled()

    def test_lifecycle_calls(self) -> None:
        """Lifecycle methods should be callable."""
        import asyncio

        plugin = DummyPlugin()

        async def run():
            await plugin.on_load()
            await plugin.on_enable()
            await plugin.on_disable()

        asyncio.run(run())

        assert plugin._load_called
        assert plugin._enable_called
        assert plugin._disable_called


# =============================================================================
# PluginRegistry Tests
# =============================================================================


class TestPluginRegistry:
    def setup_method(self) -> None:
        """Reset registry before each test."""
        reset_plugin_registry()
        self.registry = PluginRegistry()

    def teardown_method(self) -> None:
        reset_plugin_registry()

    # -- Registration --

    def test_register_single(self) -> None:
        """register should add plugin to registry."""
        plugin = DummyPlugin("alpha")
        self.registry.register(plugin)
        assert "alpha" in self.registry
        assert len(self.registry) == 1

    def test_register_duplicate_raises(self) -> None:
        """register should raise ValueError for duplicate names."""
        plugin1 = DummyPlugin("dup")
        plugin2 = DummyPlugin("dup")
        self.registry.register(plugin1)
        with pytest.raises(ValueError, match="already registered"):
            self.registry.register(plugin2)

    def test_register_loaded(self) -> None:
        """register_loaded should add loaded plugin descriptor."""
        loaded = LoadedPlugin(
            name="loaded-plugin",
            manifest=PluginManifest(name="loaded-plugin"),
            path="/path/to/plugin",
            source="npm:loaded-plugin",
        )
        self.registry.register_loaded(loaded)
        assert "loaded-plugin" in self.registry._loaded_plugins

    def test_unregister_existing(self) -> None:
        """unregister should remove plugin."""
        plugin = DummyPlugin("remove-me")
        self.registry.register(plugin)
        assert self.registry.unregister("remove-me") is True
        assert "remove-me" not in self.registry

    def test_unregister_nonexistent(self) -> None:
        """unregister should return False for unknown plugin."""
        assert self.registry.unregister("unknown") is False

    # -- Get / List --

    def test_get_existing(self) -> None:
        """get should return plugin."""
        plugin = DummyPlugin("get-me")
        self.registry.register(plugin)
        assert self.registry.get("get-me") is plugin

    def test_get_missing(self) -> None:
        """get should return None for unknown."""
        assert self.registry.get("unknown") is None

    def test_list_all(self) -> None:
        """list_all should return all plugins."""
        self.registry.register(DummyPlugin("a"))
        self.registry.register(DummyPlugin("b"))
        self.registry.register(DummyPlugin("c"))
        assert len(self.registry.list_all()) == 3

    def test_list_enabled_empty(self) -> None:
        """list_enabled should return empty list when none enabled."""
        self.registry.register(DummyPlugin("p"))
        assert self.registry.list_enabled() == []

    def test_has_true(self) -> None:
        """has should return True for registered plugin."""
        plugin = DummyPlugin("has-me")
        self.registry.register(plugin)
        assert self.registry.has("has-me") is True

    def test_has_false(self) -> None:
        """has should return False for unknown plugin."""
        assert self.registry.has("unknown") is False

    def test_iter(self) -> None:
        """iter should yield plugin names."""
        self.registry.register(DummyPlugin("x"))
        self.registry.register(DummyPlugin("y"))
        names = list(self.registry)
        assert "x" in names
        assert "y" in names

    def test_len(self) -> None:
        """len should return count of registered plugins."""
        self.registry.register(DummyPlugin("p1"))
        self.registry.register(DummyPlugin("p2"))
        assert len(self.registry) == 2

    def test_contains(self) -> None:
        """in operator should work."""
        plugin = DummyPlugin("contained")
        self.registry.register(plugin)
        assert "contained" in self.registry
        assert "not-contained" not in self.registry


# =============================================================================
# Enable / Disable Tests
# =============================================================================


class TestEnableDisable:
    def setup_method(self) -> None:
        reset_plugin_registry()
        self.registry = PluginRegistry()

    def teardown_method(self) -> None:
        reset_plugin_registry()

    @pytest.mark.asyncio
    async def test_enable_calls_on_enable(self) -> None:
        """enable should call plugin's on_enable."""
        plugin = DummyPlugin("enabler")
        self.registry.register(plugin)
        await self.registry.enable("enabler")
        assert plugin.is_enabled()
        assert plugin._enable_called

    @pytest.mark.asyncio
    async def test_enable_unknown_plugin(self) -> None:
        """enable should return False for unknown plugin."""
        result = await self.registry.enable("unknown-plugin")
        assert result is False

    @pytest.mark.asyncio
    async def test_enable_already_enabled(self) -> None:
        """enable should be idempotent."""
        plugin = DummyPlugin("idempotent")
        self.registry.register(plugin)
        await self.registry.enable("idempotent")
        result = await self.registry.enable("idempotent")
        assert result is True

    @pytest.mark.asyncio
    async def test_disable_calls_on_disable(self) -> None:
        """disable should call plugin's on_disable."""
        plugin = DummyPlugin("disabler")
        self.registry.register(plugin)
        await self.registry.enable("disabler")
        await self.registry.disable("disabler")
        assert not plugin.is_enabled()
        assert plugin._disable_called

    @pytest.mark.asyncio
    async def test_disable_unknown_plugin(self) -> None:
        """disable should return False for unknown plugin."""
        result = await self.registry.disable("unknown-plugin")
        assert result is False

    @pytest.mark.asyncio
    async def test_disable_already_disabled(self) -> None:
        """disable should be idempotent."""
        plugin = DummyPlugin("idempotent-disable")
        self.registry.register(plugin)
        result = await self.registry.disable("idempotent-disable")
        assert result is True

    @pytest.mark.asyncio
    async def test_list_enabled_after_enable(self) -> None:
        """list_enabled should include enabled plugins."""
        p1 = DummyPlugin("enabled-one")
        p2 = DummyPlugin("enabled-two")
        self.registry.register(p1)
        self.registry.register(p2)
        await self.registry.enable("enabled-one")
        await self.registry.enable("enabled-two")
        enabled = self.registry.list_enabled()
        assert p1 in enabled
        assert p2 in enabled
        assert len(enabled) == 2

    @pytest.mark.asyncio
    async def test_list_disabled(self) -> None:
        """list_disabled should exclude enabled plugins."""
        p1 = DummyPlugin("still-disabled")
        p2 = DummyPlugin("will-be-enabled")
        self.registry.register(p1)
        self.registry.register(p2)
        await self.registry.enable("will-be-enabled")
        disabled = self.registry.list_disabled()
        assert p1 in disabled
        assert p2 not in disabled

    @pytest.mark.asyncio
    async def test_enable_all(self) -> None:
        """enable_all should enable all registered plugins."""
        self.registry.register(DummyPlugin("all-1"))
        self.registry.register(DummyPlugin("all-2"))
        self.registry.register(DummyPlugin("all-3"))
        await self.registry.enable_all()
        enabled = self.registry.list_enabled()
        assert len(enabled) == 3

    @pytest.mark.asyncio
    async def test_disable_all(self) -> None:
        """disable_all should disable all enabled plugins."""
        self.registry.register(DummyPlugin("any-1"))
        self.registry.register(DummyPlugin("any-2"))
        await self.registry.enable_all()
        await self.registry.disable_all()
        assert len(self.registry.list_enabled()) == 0


# =============================================================================
# Hook Registration Tests
# =============================================================================


class TestHookRegistration:
    def setup_method(self) -> None:
        reset_plugin_registry()
        self.registry = PluginRegistry()

    def teardown_method(self) -> None:
        reset_plugin_registry()

    def test_register_hook(self) -> None:
        """register_hook should add handler."""
        async def handler(ctx: dict) -> None:
            pass

        self.registry.register_hook("PreToolUse", "test-plugin", handler)
        handlers = self.registry.list_hooks_for_event("PreToolUse")
        assert len(handlers) == 1
        assert handlers[0].plugin_name == "test-plugin"

    def test_register_multiple_hooks_same_event(self) -> None:
        """Multiple handlers can be registered for the same event."""
        async def h1(ctx: dict) -> None:
            pass

        async def h2(ctx: dict) -> None:
            pass

        self.registry.register_hook("PostToolUse", "plugin-a", h1)
        self.registry.register_hook("PostToolUse", "plugin-b", h2)
        handlers = self.registry.list_hooks_for_event("PostToolUse")
        assert len(handlers) == 2

    def test_register_hook_with_condition(self) -> None:
        """register_hook should store condition."""
        async def handler(ctx: dict) -> None:
            pass

        self.registry.register_hook(
            "PreToolUse", "cond-plugin", handler, condition="tool.name == 'Bash'"
        )
        handlers = self.registry.list_hooks_for_event("PreToolUse")
        assert handlers[0].condition == "tool.name == 'Bash'"

    def test_unregister_hook(self) -> None:
        """unregister_hook should remove all handlers for plugin/event."""
        async def handler(ctx: dict) -> None:
            pass

        self.registry.register_hook("PreToolUse", "remove-me", handler)
        self.registry.register_hook("PreToolUse", "remove-me", handler)
        self.registry.register_hook("PostToolUse", "remove-me", handler)

        self.registry.unregister_hook("PreToolUse", "remove-me")
        assert len(self.registry.list_hooks_for_event("PreToolUse")) == 0
        # PostToolUse hooks should still exist
        assert len(self.registry.list_hooks_for_event("PostToolUse")) == 1

    def test_unregister_hook_nonexistent(self) -> None:
        """unregister_hook should return False for unknown."""
        result = self.registry.unregister_hook("UnknownEvent", "unknown-plugin")
        assert result is False

    def test_list_hook_events(self) -> None:
        """list_hook_events should return events with handlers."""
        async def handler(ctx: dict) -> None:
            pass

        self.registry.register_hook("PreToolUse", "p1", handler)
        self.registry.register_hook("SessionStart", "p2", handler)
        self.registry.register_hook("PostToolUse", "p3", handler)

        events = self.registry.list_hook_events()
        assert "PreToolUse" in events
        assert "SessionStart" in events
        assert "PostToolUse" in events

    def test_unregister_plugin_cleans_hooks(self) -> None:
        """unregister should remove all hooks for that plugin."""
        async def handler(ctx: dict) -> None:
            pass

        self.registry.register(DummyPlugin("hook-owner"))
        self.registry.register_hook("PreToolUse", "hook-owner", handler)
        self.registry.register_hook("PostToolUse", "hook-owner", handler)

        self.registry.unregister("hook-owner")
        assert len(self.registry.list_hooks_for_event("PreToolUse")) == 0


# =============================================================================
# Hook Triggering Tests
# =============================================================================


class TestHookTriggering:
    def setup_method(self) -> None:
        reset_plugin_registry()
        self.registry = PluginRegistry()

    def teardown_method(self) -> None:
        reset_plugin_registry()

    @pytest.mark.asyncio
    async def test_trigger_no_handlers(self) -> None:
        """trigger_hook should return empty list when no handlers."""
        results = await self.registry.trigger_hook("UnknownEvent", {})
        assert results == []

    @pytest.mark.asyncio
    async def test_trigger_single_handler(self) -> None:
        """trigger_hook should call and collect handler result."""
        async def handler(ctx: dict) -> str:
            return ctx.get("value", "default")

        self.registry.register_hook("PreToolUse", "single", handler)
        results = await self.registry.trigger_hook("PreToolUse", {"value": "test"})
        assert results == ["test"]

    @pytest.mark.asyncio
    async def test_trigger_multiple_handlers(self) -> None:
        """trigger_hook should run all handlers in order."""
        results: list[str] = []

        async def h1(ctx: dict) -> None:
            results.append("h1")

        async def h2(ctx: dict) -> None:
            results.append("h2")

        self.registry.register_hook("PreToolUse", "p1", h1)
        self.registry.register_hook("PreToolUse", "p2", h2)
        await self.registry.trigger_hook("PreToolUse", {})
        assert results == ["h1", "h2"]

    @pytest.mark.asyncio
    async def test_trigger_error_handled(self) -> None:
        """Errors in handlers should be caught and logged."""
        async def bad_handler(ctx: dict) -> None:
            raise RuntimeError("handler failed")

        self.registry.register_hook("PreToolUse", "bad", bad_handler)
        # Should not raise
        results = await self.registry.trigger_hook("PreToolUse", {})
        assert results == []

    @pytest.mark.asyncio
    async def test_trigger_until_blocked_allowed(self) -> None:
        """trigger_hook_until_blocked should return (True, results) when no block."""
        async def handler(ctx: dict) -> dict:
            return {"allowed": True}

        self.registry.register_hook("PreToolUse", "allow", handler)
        allowed, results = await self.registry.trigger_hook_until_blocked(
            "PreToolUse", {}
        )
        assert allowed is True
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_trigger_until_blocked_stops_on_block(self) -> None:
        """trigger_hook_until_blocked should stop on first blocking result."""
        results: list[str] = []

        async def h1(ctx: dict) -> dict:
            results.append("h1")
            return {"allowed": True}

        async def h2(ctx: dict) -> dict:
            results.append("h2")
            return {"blocked": True, "message": "Access denied"}

        async def h3(ctx: dict) -> None:
            results.append("h3")

        self.registry.register_hook("PreToolUse", "p1", h1)
        self.registry.register_hook("PreToolUse", "p2", h2)
        self.registry.register_hook("PreToolUse", "p3", h3)

        allowed, results = await self.registry.trigger_hook_until_blocked(
            "PreToolUse", {}
        )
        assert allowed is False
        # h3 should NOT have been called (stopped after h2 blocked)
        assert results == [
            {"allowed": True},
            {"blocked": True, "message": "Access denied"},
        ]


# =============================================================================
# Global Registry Tests
# =============================================================================


class TestGlobalRegistry:
    def setup_method(self) -> None:
        reset_plugin_registry()

    def teardown_method(self) -> None:
        reset_plugin_registry()

    def test_get_plugin_registry_returns_same_instance(self) -> None:
        """get_plugin_registry should return singleton."""
        r1 = get_plugin_registry()
        r2 = get_plugin_registry()
        assert r1 is r2

    def test_reset_clears_registry(self) -> None:
        """reset_plugin_registry should clear and reset singleton."""
        registry = get_plugin_registry()
        registry.register(DummyPlugin("will-be-removed"))

        reset_plugin_registry()

        new_registry = get_plugin_registry()
        assert len(new_registry) == 0
        assert new_registry is not registry


# =============================================================================
# Clear Tests
# =============================================================================


class TestClear:
    def setup_method(self) -> None:
        self.registry = PluginRegistry()

    @pytest.mark.asyncio
    async def test_clear_removes_all(self) -> None:
        """clear should remove all plugins and hooks."""
        self.registry.register(DummyPlugin("c1"))
        self.registry.register(DummyPlugin("c2"))

        async def handler(ctx: dict) -> None:
            pass

        self.registry.register_hook("PreToolUse", "c1", handler)

        self.registry.clear()

        assert len(self.registry) == 0
        assert len(self.registry.list_hooks_for_event("PreToolUse")) == 0
