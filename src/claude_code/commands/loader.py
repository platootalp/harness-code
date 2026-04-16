"""Dynamic command loader for Claude Code.

This module handles dynamic loading of command modules:
- Builtin commands loaded at startup
- Skill directory commands
- Plugin commands
- Bundled skills
- MCP (Model Context Protocol) commands

TypeScript equivalent: src/commands.ts getCommands(), getSkills()
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import logging
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, cast

from .base import BaseCommand
from .registry import get_builtin_registry

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# =============================================================================
# Command Source Classification
# =============================================================================


class CommandSource:
    """Classification of where a command was loaded from."""

    BUILTIN = "builtin"
    PLUGIN = "plugin"
    SKILL_DIR = "skill_dir"
    BUNDLED = "bundled"
    MCP = "mcp"


# =============================================================================
# Loader Result
# =============================================================================


@dataclass
class LoaderResult:
    """Result of loading commands from a source."""

    commands: list[BaseCommand] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    source: str = "unknown"

    def merge(self, other: LoaderResult) -> LoaderResult:
        """Merge another loader result into this one.

        Args:
            other: Another LoaderResult to merge.

        Returns:
            A new LoaderResult with combined commands and errors.
        """
        return LoaderResult(
            commands=self.commands + other.commands,
            errors=self.errors + other.errors,
            source=self.source,
        )


# =============================================================================
# Dynamic Module Loader
# =============================================================================


def load_command_module_from_path(file_path: Path) -> type[BaseCommand] | None:
    """Load a command class from a Python file path.

    Expects the file to define a class named after the file (PascalCase).

    Args:
        file_path: Path to the Python module file.

    Returns:
        The command class, or None if loading failed.
    """
    try:
        module_name = file_path.stem

        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            logger.warning(f"Cannot load spec for {file_path}")
            return None

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        # Look for a class with the PascalCase name
        class_name = "".join(word.capitalize() for word in module_name.split("_"))
        if hasattr(module, class_name):
            return cast("type[BaseCommand]", getattr(module, class_name))

        # Fallback: look for any BaseCommand subclass
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, BaseCommand)
                and attr is not BaseCommand
            ):
                return attr

        logger.warning(f"No command class found in {file_path}")
        return None

    except Exception as e:
        logger.warning(f"Failed to load command from {file_path}: {e}")
        return None


def discover_commands_in_dir(
    directory: Path,
    source: str = "discovered",
) -> LoaderResult:
    """Discover and load command modules from a directory.

    Loads all *.py files (except __init__.py and __main__.py) as command modules.

    Args:
        directory: Directory to scan for command modules.
        source: Source classification for loaded commands.

    Returns:
        LoaderResult with loaded commands and any errors.
    """
    result = LoaderResult(source=source)

    if not directory.is_dir():
        result.errors.append(f"Directory not found: {directory}")
        return result

    for file_path in directory.glob("*.py"):
        if file_path.name.startswith("_"):
            continue

        cmd_class = load_command_module_from_path(file_path)
        if cmd_class is not None:
            try:
                instance = cmd_class()  # type: ignore[call-arg]
                instance.source = source
                result.commands.append(instance)
            except Exception as e:
                result.errors.append(f"Failed to instantiate {cmd_class.__name__}: {e}")

    return result


# =============================================================================
# Builtin Command Loader
# =============================================================================


# Builtin command modules to load at startup
# These are the core commands that ship with Claude Code
_BUILTIN_COMMAND_MODULES: list[str] = [
    "claude_code.commands.clear",
    "claude_code.commands.git",
    "claude_code.commands.exit",
    "claude_code.commands.files",
    "claude_code.commands.rewind",
    "claude_code.commands.vim",
    "claude_code.commands.cost",
    "claude_code.commands.stats",
    "claude_code.commands.status",
    "claude_code.commands.usage",
    "claude_code.commands.plan",
    "claude_code.commands.thinkback",
    "claude_code.commands.output_style",
    "claude_code.commands.privacy_settings",
    "claude_code.commands.rate_limit_options",
    "claude_code.commands.remote_env",
    "claude_code.commands.remote_setup",
    "claude_code.commands.tag",
    "claude_code.commands.sandbox_toggle",
    "claude_code.commands.terminal_setup",
    "claude_code.commands.extra_usage",
    "claude_code.commands.chrome",
    "claude_code.commands.mobile",
    "claude_code.commands.desktop",
    "claude_code.commands.install_github_app",
]


def load_builtin_commands() -> LoaderResult:
    """Load all builtin commands.

    Imports builtin command modules and registers their command classes.

    Returns:
        LoaderResult with loaded commands and any errors.
    """
    result = LoaderResult(source=CommandSource.BUILTIN)
    registry = get_builtin_registry()

    for module_name in _BUILTIN_COMMAND_MODULES:
        try:
            module = importlib.import_module(module_name)

            # Look for command classes in the module
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, BaseCommand)
                    and attr is not BaseCommand
                    # Skip abstract base classes
                    and not inspect.isabstract(attr)
                    # Only instantiate classes defined in this module (not imported)
                    and getattr(attr, "__module__", None) == module.__name__
                ):
                    try:
                        instance = attr()  # type: ignore[call-arg]
                        instance.source = CommandSource.BUILTIN
                        registry.register(instance)
                        result.commands.append(instance)
                    except ValueError as e:
                        # Command already registered (e.g., re-registration)
                        result.errors.append(str(e))
                    except Exception as e:
                        result.errors.append(f"Failed to instantiate {attr_name}: {e}")

        except ImportError as e:
            result.errors.append(f"Failed to import {module_name}: {e}")

    return result


# =============================================================================
# Skill Directory Commands
# =============================================================================


def load_skill_dir_commands(skill_dir: Path) -> LoaderResult:
    """Load commands from a skill directory.

    Args:
        skill_dir: Path to a skills directory containing command modules.

    Returns:
        LoaderResult with loaded commands and any errors.
    """
    return discover_commands_in_dir(skill_dir, CommandSource.SKILL_DIR)


# =============================================================================
# Plugin Commands
# =============================================================================


def load_plugin_commands(plugin_dir: Path) -> LoaderResult:
    """Load commands from a plugin directory.

    Args:
        plugin_dir: Path to a plugin directory containing command modules.

    Returns:
        LoaderResult with loaded commands and any errors.
    """
    return discover_commands_in_dir(plugin_dir, CommandSource.PLUGIN)


# =============================================================================
# MCP Commands
# =============================================================================


@dataclass
class MCPServerInfo:
    """Information about an MCP server providing commands."""

    name: str
    command: list[str]
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)


def load_mcp_commands(
    servers: Sequence[MCPServerInfo],
) -> LoaderResult:
    """Load commands from MCP (Model Context Protocol) servers.

    MCP servers can expose tools that are registered as commands.

    Args:
        servers: List of MCP server configurations.
        registry: Optional registry to register commands into. Uses global
            builtin registry if not provided.

    Returns:
        LoaderResult with loaded commands and any errors.
    """
    result = LoaderResult(source=CommandSource.MCP)

    # MCP command loading would connect to the MCP server and
    # register available tools as commands.
    # This is a placeholder for the MCP integration.
    # Full implementation would use the MCP client to list tools.

    if servers:
        # Placeholder: MCP server tools would be registered here
        # In full implementation, this would:
        # 1. Start or connect to the MCP server
        # 2. List available tools
        # 3. Create command wrappers for each tool
        pass

    return result


# =============================================================================
# Composite Loader
# =============================================================================


@dataclass
class LoadAllOptions:
    """Options for loading all command sources."""

    cwd: Path | None = None  # Working directory for skill loading
    plugin_dirs: list[Path] | None = None  # Additional plugin directories
    mcp_servers: list[MCPServerInfo] | None = None  # MCP server configurations


def load_all_commands(
    options: LoadAllOptions | None = None,
) -> LoaderResult:
    """Load commands from all sources.

    Args:
        options: Optional configuration for loading commands.

    Returns:
        LoaderResult with all loaded commands and accumulated errors.
    """
    if options is None:
        options = LoadAllOptions()

    combined = LoaderResult()

    # Load builtin commands
    builtin_result = load_builtin_commands()
    combined = combined.merge(builtin_result)

    # Load skill directory commands
    if options.cwd is not None:
        skill_dir = options.cwd / ".claude" / "skills"
        if skill_dir.is_dir():
            skill_result = load_skill_dir_commands(skill_dir)
            combined = combined.merge(skill_result)

    # Load plugin commands
    if options.plugin_dirs:
        for plugin_dir in options.plugin_dirs:
            plugin_result = load_plugin_commands(plugin_dir)
            combined = combined.merge(plugin_result)

    # Load MCP commands
    if options.mcp_servers:
        mcp_result = load_mcp_commands(options.mcp_servers)
        combined = combined.merge(mcp_result)

    return combined
