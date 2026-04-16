"""Plugin base classes and data structures.

Provides the foundational types for the plugin system:
- PluginManifest: plugin metadata from plugin.json
- PluginScope: plugin installation scope
- BasePlugin: abstract base class for all plugins

TypeScript equivalent: src/types/plugin.ts, src/utils/plugins/schemas.ts
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


# =============================================================================
# Enums
# =============================================================================


class PluginScope(StrEnum):
    """Plugin installation scope.

    Determines where a plugin is installed and who can access it.
    """

    #: System-wide managed plugins (read-only)
    MANAGED = "managed"
    #: User-global plugins (~/.claude/settings.json)
    USER = "user"
    #: Shared project plugins ($project/.claude/settings.json)
    PROJECT = "project"
    #: Local personal project overrides
    LOCAL = "local"


class PluginSource(StrEnum):
    """Plugin source type (where the plugin comes from)."""

    NPM = "npm"
    PIP = "pip"
    GIT = "git"
    GITHUB = "github"
    LOCAL = "local"
    MANAGED = "managed"
    BUILTIN = "builtin"


# =============================================================================
# Plugin Manifest
# =============================================================================


@dataclass
class PluginManifest:
    """Plugin manifest data loaded from plugin.json.

    Attributes:
        name: Unique plugin name.
        version: Semantic version string.
        description: Human-readable description.
        author: Author information (name, email, url).
        homepage: Plugin homepage URL.
        repository: Source repository URL.
        license: License identifier (default MIT).
        keywords: Searchable keywords.
        dependencies: Other plugin dependencies.
        commands: Glob patterns for command files.
        agents: Glob patterns for agent definition files.
        skills: Glob patterns for skill files.
        hooks: Hook configuration dictionary.
        output_styles: Glob patterns for output style files.
        mcp_servers: MCP server configurations.
        lsp_servers: LSP server configurations.
        user_config: User-facing configuration schema.
    """

    name: str
    version: str = "1.0.0"
    description: str = ""
    author: dict[str, str] | None = None
    homepage: str | None = None
    repository: str | None = None
    license: str = "MIT"
    keywords: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    commands: list[str] | None = None
    agents: list[str] | None = None
    skills: list[str] | None = None
    hooks: dict[str, Any] | None = None
    output_styles: list[str] | None = None
    mcp_servers: dict[str, Any] | None = None
    lsp_servers: dict[str, Any] | None = None
    user_config: dict[str, Any] | None = None


# =============================================================================
# Plugin Author
# =============================================================================


@dataclass
class PluginAuthor:
    """Plugin author information."""

    name: str
    email: str | None = None
    url: str | None = None


# =============================================================================
# Loaded Plugin
# =============================================================================


@dataclass
class LoadedPlugin:
    """A plugin that has been loaded into the system.

    Attributes:
        name: Plugin name.
        manifest: Plugin metadata.
        path: Filesystem path to the plugin.
        source: Source identifier (e.g. npm package name, git URL).
        repository: Repository identifier (usually same as source).
        enabled: Whether the plugin is currently enabled.
        is_builtin: True for built-in plugins that ship with the CLI.
        sha: Git commit SHA for version pinning.
        commands_path: Path to commands directory.
        commands_paths: Additional command paths from manifest.
        agents_path: Path to agents directory.
        agents_paths: Additional agent paths from manifest.
        skills_path: Path to skills directory.
        skills_paths: Additional skill paths from manifest.
        output_styles_path: Path to output-styles directory.
        output_styles_paths: Additional output style paths.
        hooks_config: Hook configuration.
        mcp_servers: MCP server configurations.
        lsp_servers: LSP server configurations.
        settings: Plugin-specific settings.
        scope: Installation scope.
        source_type: Where the plugin was loaded from.
    """

    name: str
    manifest: PluginManifest
    path: str
    source: str
    repository: str | None = None
    enabled: bool = False
    is_builtin: bool = False
    sha: str | None = None
    commands_path: str | None = None
    commands_paths: list[str] | None = None
    agents_path: str | None = None
    agents_paths: list[str] | None = None
    skills_path: str | None = None
    skills_paths: list[str] | None = None
    output_styles_path: str | None = None
    output_styles_paths: list[str] | None = None
    hooks_config: dict[str, Any] | None = None
    mcp_servers: dict[str, Any] | None = None
    lsp_servers: dict[str, Any] | None = None
    settings: dict[str, Any] | None = None
    scope: PluginScope = PluginScope.USER
    source_type: PluginSource = PluginSource.LOCAL

    @property
    def plugin_id(self) -> str:
        """Full plugin identifier including marketplace suffix."""
        if self.is_builtin:
            return f"{self.name}@builtin"
        return self.source


# =============================================================================
# Base Plugin
# =============================================================================


class BasePlugin(ABC):
    """Abstract base class for all plugins.

    Plugins must implement on_load, on_enable, and on_disable lifecycle methods.

    TypeScript equivalent: Plugin interface in types/plugin.ts

    Example:
        @dataclass
        class MyPlugin(BasePlugin):
            async def on_load(self) -> None:
                # Set up plugin resources
                pass

            async def on_enable(self) -> None:
                # Register commands, hooks, etc.
                pass

            async def on_disable(self) -> None:
                # Clean up resources
                pass
    """

    def __init__(self, manifest: PluginManifest) -> None:
        """Initialize the plugin with its manifest.

        Args:
            manifest: The plugin's metadata.
        """
        self._manifest = manifest
        self._enabled = False

    @property
    def manifest(self) -> PluginManifest:
        """The plugin's manifest."""
        return self._manifest

    @property
    def name(self) -> str:
        """The plugin's name."""
        return self._manifest.name

    @property
    def version(self) -> str:
        """The plugin's version string."""
        return self._manifest.version

    @property
    def description(self) -> str:
        """The plugin's description."""
        return self._manifest.description

    def is_enabled(self) -> bool:
        """Check if the plugin is currently enabled."""
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        """Set the enabled state."""
        self._enabled = enabled

    @abstractmethod
    async def on_load(self) -> None:
        """Called when the plugin is first loaded.

        Use this to initialize plugin resources that don't require
        the plugin to be enabled (e.g. loading configuration).
        """
        ...

    @abstractmethod
    async def on_enable(self) -> None:
        """Called when the plugin is enabled.

        Use this to register commands, hooks, tools, etc.
        """
        ...

    @abstractmethod
    async def on_disable(self) -> None:
        """Called when the plugin is disabled.

        Use this to unregister commands, hooks, tools, etc.
        """
        ...
