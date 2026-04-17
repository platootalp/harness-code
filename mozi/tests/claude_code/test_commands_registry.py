"""
Tests for commands/registry.py and commands/loader.py
"""

from __future__ import annotations

import pytest
from claude_code.commands.base import (
    Availability,
    BaseCommand,
    CommandResult,
    CommandType,
)
from claude_code.commands.loader import (
    CommandSource,
    LoadAllOptions,
    LoaderResult,
    MCPServerInfo,
    discover_commands_in_dir,
    load_builtin_commands,
)
from claude_code.commands.registry import (
    CommandFilter,
    CommandRegistry,
    get_builtin_command,
    get_builtin_registry,
    list_builtin_commands,
    register_builtin,
)

# =============================================================================
# Test Helpers
# =============================================================================


class DummyCommand(BaseCommand):
    """Dummy command for testing."""

    def __init__(self) -> None:
        super().__init__(
            name="dummy",
            description="A dummy command",
            source="test",
            command_type=CommandType.PROMPT,
        )

    async def execute(
        self,
        args: str,
        context: dict,
    ) -> CommandResult:
        return CommandResult(type="text", value="dummy executed")


class DummyLocalCommand(BaseCommand):
    """Dummy local command for testing."""

    def __init__(self) -> None:
        super().__init__(
            name="dummy_local",
            description="A dummy local command",
            source="test",
            command_type=CommandType.LOCAL,
            supports_non_interactive=True,
        )

    async def execute(
        self,
        args: str,
        context: dict,
    ) -> CommandResult:
        return CommandResult(type="text", value="local executed")


class DummyPromptCommand(BaseCommand):
    """Dummy prompt command for testing."""

    def __init__(self) -> None:
        super().__init__(
            name="dummy_prompt",
            description="A dummy prompt command",
            source="test",
            command_type=CommandType.PROMPT,
        )

    async def execute(
        self,
        args: str,
        context: dict,
    ) -> CommandResult:
        return CommandResult(type="text", value="prompt executed")


class DummyHiddenCommand(BaseCommand):
    """Dummy hidden command for testing."""

    def __init__(self) -> None:
        super().__init__(
            name="hidden",
            description="A hidden command",
            source="test",
            is_hidden=True,
        )

    async def execute(
        self,
        args: str,
        context: dict,
    ) -> CommandResult:
        return CommandResult(type="text", value="hidden executed")


class DummyAliasedCommand(BaseCommand):
    """Dummy command with aliases for testing."""

    def __init__(self) -> None:
        super().__init__(
            name="aliased",
            description="A command with aliases",
            aliases=["als", "ali"],
            source="test",
        )

    async def execute(
        self,
        args: str,
        context: dict,
    ) -> CommandResult:
        return CommandResult(type="text", value="aliased executed")


class DummyDisabledCommand(BaseCommand):
    """Dummy disabled command for testing."""

    _enabled: bool = False

    def __init__(self) -> None:
        super().__init__(
            name="disabled",
            description="A disabled command",
            source="test",
            is_enabled=lambda: self._enabled,
        )

    async def execute(
        self,
        args: str,
        context: dict,
    ) -> CommandResult:
        return CommandResult(type="text", value="disabled executed")


# =============================================================================
# CommandRegistry Tests
# =============================================================================


class TestCommandRegistry:
    def setup_method(self) -> None:
        """Create a fresh registry for each test."""
        self.registry = CommandRegistry()

    def test_register_single_command(self) -> None:
        """Registering a single command should be findable."""
        cmd = DummyCommand()
        self.registry.register(cmd)
        assert "dummy" in self.registry
        assert self.registry.get("dummy") is cmd
        assert len(self.registry) == 1

    def test_register_multiple_commands(self) -> None:
        """Registering multiple commands should all be findable."""
        cmd1 = DummyCommand()
        cmd2 = DummyLocalCommand()
        cmd3 = DummyPromptCommand()

        self.registry.register(cmd1)
        self.registry.register(cmd2)
        self.registry.register(cmd3)

        assert len(self.registry) == 3
        assert self.registry.get("dummy") is cmd1
        assert self.registry.get("dummy_local") is cmd2
        assert self.registry.get("dummy_prompt") is cmd3

    def test_register_duplicate_raises(self) -> None:
        """Registering a command with the same name should raise ValueError."""
        cmd1 = DummyCommand()
        cmd2 = DummyCommand()
        self.registry.register(cmd1)
        with pytest.raises(ValueError, match="already registered"):
            self.registry.register(cmd2)

    def test_register_alias_collision(self) -> None:
        """Registering commands with conflicting aliases should raise ValueError."""
        # Create commands directly with conflicting names/aliases
        class TestCmd1(BaseCommand):
            def __init__(self) -> None:
                super().__init__(name="test", description="Test cmd", source="test")

            async def execute(self, args: str, context: dict) -> CommandResult:
                return CommandResult(type="text", value="")

        class TestCmd2(BaseCommand):
            def __init__(self) -> None:
                super().__init__(
                    name="test2",
                    description="Test cmd 2",
                    aliases=["test"],  # Alias conflicts with cmd1's name
                    source="test",
                )

            async def execute(self, args: str, context: dict) -> CommandResult:
                return CommandResult(type="text", value="")

        cmd1 = TestCmd1()
        cmd2 = TestCmd2()

        self.registry.register(cmd1)
        with pytest.raises(ValueError, match="name conflict"):
            self.registry.register(cmd2)

    def test_unregister_existing(self) -> None:
        """Unregistering an existing command should remove it."""
        cmd = DummyCommand()
        self.registry.register(cmd)
        assert self.registry.unregister("dummy") is True
        assert "dummy" not in self.registry
        assert len(self.registry) == 0

    def test_unregister_nonexistent(self) -> None:
        """Unregistering a nonexistent command should return False."""
        assert self.registry.unregister("nonexistent") is False

    def test_get_by_alias(self) -> None:
        """Getting a command by alias should return the command."""
        cmd = DummyAliasedCommand()
        self.registry.register(cmd)

        assert self.registry.get("aliased") is cmd
        assert self.registry.get("als") is cmd
        assert self.registry.get("ali") is cmd

    def test_get_by_name_exact(self) -> None:
        """Getting by exact name should not find aliases."""
        cmd = DummyAliasedCommand()
        self.registry.register(cmd)

        assert self.registry.get_by_name("aliased") is cmd
        assert self.registry.get_by_name("als") is None

    def test_has_method(self) -> None:
        """has() should return True for name and aliases."""
        cmd = DummyAliasedCommand()
        self.registry.register(cmd)

        assert self.registry.has("aliased") is True
        assert self.registry.has("als") is True
        assert self.registry.has("nonexistent") is False

    def test_list_all(self) -> None:
        """list_all() should return all registered commands."""
        cmd1 = DummyCommand()
        cmd2 = DummyLocalCommand()
        self.registry.register(cmd1)
        self.registry.register(cmd2)

        all_cmds = self.registry.list_all()
        assert len(all_cmds) == 2
        assert cmd1 in all_cmds
        assert cmd2 in all_cmds

    def test_list_names(self) -> None:
        """list_names() should return only primary names."""
        cmd1 = DummyCommand()
        cmd2 = DummyAliasedCommand()
        self.registry.register(cmd1)
        self.registry.register(cmd2)

        names = self.registry.list_names()
        assert "dummy" in names
        assert "aliased" in names
        assert "als" not in names

    def test_list_filtered_custom(self) -> None:
        """list_filtered() should filter using custom function."""
        cmd1 = DummyPromptCommand()
        cmd2 = DummyLocalCommand()
        self.registry.register(cmd1)
        self.registry.register(cmd2)

        local_only = self.registry.list_filtered(
            lambda c: c.command_type == CommandType.LOCAL
        )
        assert len(local_only) == 1
        assert local_only[0] is cmd2

    def test_filter_by_source(self) -> None:
        """filter_commands with source filter should work."""
        cmd = DummyCommand()
        cmd.source = "plugin"
        self.registry.register(cmd)

        result = self.registry.filter_commands(CommandFilter(source="plugin"))
        assert len(result) == 1
        assert result[0] is cmd

        result = self.registry.filter_commands(CommandFilter(source="builtin"))
        assert len(result) == 0

    def test_filter_by_command_type(self) -> None:
        """filter_commands with command_type filter should work."""
        cmd1 = DummyLocalCommand()
        cmd2 = DummyPromptCommand()
        self.registry.register(cmd1)
        self.registry.register(cmd2)

        result = self.registry.filter_commands(
            CommandFilter(command_type=CommandType.LOCAL)
        )
        assert len(result) == 1
        assert result[0] is cmd1

    def test_filter_include_hidden(self) -> None:
        """filter_commands should exclude hidden by default."""
        cmd1 = DummyCommand()
        cmd2 = DummyHiddenCommand()
        self.registry.register(cmd1)
        self.registry.register(cmd2)

        result = self.registry.filter_commands(CommandFilter(include_hidden=False))
        assert len(result) == 1
        assert result[0] is cmd1

        result = self.registry.filter_commands(CommandFilter(include_hidden=True))
        assert len(result) == 2

    def test_filter_enabled_only(self) -> None:
        """filter_commands should exclude disabled by default."""
        cmd1 = DummyCommand()
        cmd2 = DummyDisabledCommand()
        self.registry.register(cmd1)
        self.registry.register(cmd2)

        result = self.registry.filter_commands(CommandFilter(enabled_only=True))
        assert len(result) == 1
        assert result[0] is cmd1

        result = self.registry.filter_commands(CommandFilter(enabled_only=False))
        assert len(result) == 2

    def test_filter_by_auth_type(self) -> None:
        """filter_commands with auth_type filter should work."""
        cmd = DummyCommand()
        cmd.availability = [Availability.CLAUDE_AI.value]
        self.registry.register(cmd)

        result = self.registry.filter_commands(
            CommandFilter(auth_type=Availability.CLAUDE_AI.value)
        )
        assert len(result) == 1

        result = self.registry.filter_commands(
            CommandFilter(auth_type=Availability.CONSOLE.value)
        )
        assert len(result) == 0

    def test_get_builtin_names(self) -> None:
        """get_builtin_names should return all builtin names and aliases."""
        cmd1 = DummyCommand()
        cmd1.source = "builtin"
        cmd2 = DummyAliasedCommand()
        cmd2.source = "builtin"
        cmd3 = DummyLocalCommand()
        cmd3.source = "plugin"

        self.registry.register(cmd1)
        self.registry.register(cmd2)
        self.registry.register(cmd3)

        names = self.registry.get_builtin_names()
        assert "dummy" in names
        assert "aliased" in names
        assert "als" in names  # aliases included
        assert "dummy_local" not in names  # not builtin

    def test_clear(self) -> None:
        """clear() should remove all commands."""
        cmd1 = DummyCommand()
        cmd2 = DummyLocalCommand()
        self.registry.register(cmd1)
        self.registry.register(cmd2)

        self.registry.clear()
        assert len(self.registry) == 0
        assert "dummy" not in self.registry

    def test_iter(self) -> None:
        """iter should yield command names."""
        cmd1 = DummyCommand()
        cmd2 = DummyLocalCommand()
        self.registry.register(cmd1)
        self.registry.register(cmd2)

        names = list(self.registry)
        assert "dummy" in names
        assert "dummy_local" in names


# =============================================================================
# Global Registry Tests
# =============================================================================


class TestGlobalRegistry:
    def setup_method(self) -> None:
        """Reset the global registry before each test."""
        self.registry = get_builtin_registry()
        self.registry.clear()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        self.registry.clear()

    def test_register_builtin(self) -> None:
        """register_builtin should add to global registry."""
        cmd = DummyCommand()
        cmd.source = "builtin"
        register_builtin(cmd)
        assert "dummy" in self.registry
        assert get_builtin_command("dummy") is cmd

    def test_list_builtin_commands(self) -> None:
        """list_builtin_commands should return all builtin commands."""
        cmd1 = DummyCommand()
        cmd1.source = "builtin"
        cmd2 = DummyLocalCommand()
        cmd2.source = "builtin"
        register_builtin(cmd1)
        register_builtin(cmd2)

        commands = list_builtin_commands()
        assert len(commands) == 2


# =============================================================================
# LoaderResult Tests
# =============================================================================


class TestLoaderResult:
    def test_empty_result(self) -> None:
        """Empty LoaderResult should have no commands or errors."""
        result = LoaderResult()
        assert result.commands == []
        assert result.errors == []
        assert result.source == "unknown"

    def test_merge(self) -> None:
        """merge() should combine commands and errors."""
        cmd1 = DummyCommand()
        cmd2 = DummyLocalCommand()

        result1 = LoaderResult(
            commands=[cmd1],
            errors=["error1"],
            source="builtin",
        )
        result2 = LoaderResult(
            commands=[cmd2],
            errors=["error2"],
            source="plugin",
        )

        merged = result1.merge(result2)
        assert len(merged.commands) == 2
        assert merged.errors == ["error1", "error2"]


# =============================================================================
# Load Builtin Commands Tests
# =============================================================================


class TestLoadBuiltinCommands:
    def test_load_builtin_commands(self) -> None:
        """load_builtin_commands should load and register commands."""
        # Clear registry first
        registry = get_builtin_registry()
        registry.clear()

        result = load_builtin_commands()

        # Should load ClearCommand, CompactCommand, HelpCommand, ModelCommand
        assert len(result.commands) >= 4
        assert len(result.errors) == 0

        # Verify commands are in registry
        assert registry.get("clear") is not None
        assert registry.get("compact") is not None
        assert registry.get("help") is not None
        assert registry.get("model") is not None


# =============================================================================
# CommandSource Tests
# =============================================================================


class TestCommandSource:
    def test_source_constants(self) -> None:
        """CommandSource should have correct values."""
        assert CommandSource.BUILTIN == "builtin"
        assert CommandSource.PLUGIN == "plugin"
        assert CommandSource.SKILL_DIR == "skill_dir"
        assert CommandSource.BUNDLED == "bundled"
        assert CommandSource.MCP == "mcp"


# =============================================================================
# MCPServerInfo Tests
# =============================================================================


class TestMCPServerInfo:
    def test_create_basic(self) -> None:
        """MCPServerInfo should create with required fields."""
        server = MCPServerInfo(
            name="test-server",
            command=["npx", "some-mcp-server"],
        )
        assert server.name == "test-server"
        assert server.command == ["npx", "some-mcp-server"]
        assert server.args == []
        assert server.env == {}

    def test_create_full(self) -> None:
        """MCPServerInfo should create with all fields."""
        server = MCPServerInfo(
            name="full-server",
            command=["npx", "server"],
            args=["--flag"],
            env={"KEY": "value"},
        )
        assert server.name == "full-server"
        assert server.args == ["--flag"]
        assert server.env == {"KEY": "value"}


# =============================================================================
# LoadAllOptions Tests
# =============================================================================


class TestLoadAllOptions:
    def test_defaults(self) -> None:
        """LoadAllOptions should have sensible defaults."""
        opts = LoadAllOptions()
        assert opts.cwd is None
        assert opts.plugin_dirs is None
        assert opts.mcp_servers is None
