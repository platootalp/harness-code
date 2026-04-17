"""Plugin manager for plugin lifecycle, errors, and built-in plugin registry.

Provides:
- PluginError: Discriminated union of all plugin error types
- PluginLoadResult: Result of loading plugins
- Manifest parsing and validation helpers
- PluginRepository: Repository metadata

TypeScript equivalent: src/types/plugin.ts, src/plugins/builtinPlugins.ts
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, TypedDict, cast

if TYPE_CHECKING:
    pass

from .builtin import (
    BUILTIN_MARKETPLACE_NAME,
    BuiltinPluginDefinition,
    builtin_plugins_count,
    get_builtin_plugin_definition,
    get_builtin_plugins,
    is_builtin_plugin_id,
    register_builtin_plugin,
)

# Re-export from builtin for backwards compatibility

# =============================================================================
# Plugin Component
# =============================================================================


class PluginComponent:
    """Plugin component types that can fail to load."""

    COMMANDS = "commands"
    AGENTS = "agents"
    SKILLS = "skills"
    HOOKS = "hooks"
    OUTPUT_STYLES = "output-styles"


# =============================================================================
# Plugin Error Types (Discriminated Union via TypedDict)
# =============================================================================


class PluginErrorPathNotFound(TypedDict):
    """Path not found error."""

    type: str
    source: str
    plugin: str | None
    path: str
    component: str


class PluginErrorGitAuthFailed(TypedDict):
    """Git authentication failed error."""

    type: str
    source: str
    plugin: str | None
    git_url: str
    auth_type: str  # 'ssh' | 'https'


class PluginErrorGitTimeout(TypedDict):
    """Git operation timeout error."""

    type: str
    source: str
    plugin: str | None
    git_url: str
    operation: str  # 'clone' | 'pull'


class PluginErrorNetworkError(TypedDict):
    """Network error."""

    type: str
    source: str
    plugin: str | None
    url: str
    details: str | None


class PluginErrorManifestParseError(TypedDict):
    """Manifest parse error."""

    type: str
    source: str
    plugin: str | None
    manifest_path: str
    parse_error: str


class PluginErrorManifestValidationError(TypedDict):
    """Manifest validation error."""

    type: str
    source: str
    plugin: str | None
    manifest_path: str
    validation_errors: list[str]


class PluginErrorPluginNotFound(TypedDict):
    """Plugin not found in marketplace."""

    type: str
    source: str
    plugin: str | None
    plugin_id: str
    marketplace: str


class PluginErrorMarketplaceNotFound(TypedDict):
    """Marketplace not found."""

    type: str
    source: str
    plugin: str | None
    marketplace: str
    available_marketplaces: list[str]


class PluginErrorMarketplaceLoadFailed(TypedDict):
    """Marketplace load failed."""

    type: str
    source: str
    plugin: str | None
    marketplace: str
    reason: str


class PluginErrorMcpConfigInvalid(TypedDict):
    """MCP server configuration invalid."""

    type: str
    source: str
    plugin: str
    server_name: str
    validation_error: str


class PluginErrorMcpServerSuppressedDuplicate(TypedDict):
    """MCP server duplicate suppressed."""

    type: str
    source: str
    plugin: str
    server_name: str
    duplicate_of: str


class PluginErrorLspConfigInvalid(TypedDict):
    """LSP server configuration invalid."""

    type: str
    source: str
    plugin: str
    server_name: str
    validation_error: str


class PluginErrorLspServerStartFailed(TypedDict):
    """LSP server failed to start."""

    type: str
    source: str
    plugin: str
    server_name: str
    reason: str


class PluginErrorLspServerCrashed(TypedDict):
    """LSP server crashed."""

    type: str
    source: str
    plugin: str
    server_name: str
    exit_code: int | None
    signal: str | None


class PluginErrorLspRequestTimeout(TypedDict):
    """LSP request timed out."""

    type: str
    source: str
    plugin: str
    server_name: str
    method: str
    timeout_ms: int


class PluginErrorLspRequestFailed(TypedDict):
    """LSP request failed."""

    type: str
    source: str
    plugin: str
    server_name: str
    method: str
    error: str


class PluginErrorHookLoadFailed(TypedDict):
    """Hook load failed."""

    type: str
    source: str
    plugin: str
    hook_path: str
    reason: str


class PluginErrorComponentLoadFailed(TypedDict):
    """Component load failed."""

    type: str
    source: str
    plugin: str
    component: str
    path: str
    reason: str


class PluginErrorMcpbDownloadFailed(TypedDict):
    """MCPB download failed."""

    type: str
    source: str
    plugin: str
    url: str
    reason: str


class PluginErrorMcpbExtractFailed(TypedDict):
    """MCPB extract failed."""

    type: str
    source: str
    plugin: str
    mcpb_path: str
    reason: str


class PluginErrorMcpbInvalidManifest(TypedDict):
    """MCPB invalid manifest."""

    type: str
    source: str
    plugin: str
    mcpb_path: str
    validation_error: str


class PluginErrorMarketplaceBlockedByPolicy(TypedDict):
    """Marketplace blocked by enterprise policy."""

    type: str
    source: str
    plugin: str | None
    marketplace: str
    blocked_by_blocklist: bool | None
    allowed_sources: list[str]


class PluginErrorDependencyUnsatisfied(TypedDict):
    """Dependency not satisfied."""

    type: str
    source: str
    plugin: str
    dependency: str
    reason: str  # 'not-enabled' | 'not-found'


class PluginErrorPluginCacheMiss(TypedDict):
    """Plugin not cached."""

    type: str
    source: str
    plugin: str
    install_path: str


class PluginErrorGeneric(TypedDict):
    """Generic plugin error."""

    type: str
    source: str
    plugin: str | None
    error: str


# Union type alias for all plugin errors
PluginError = (
    PluginErrorGeneric
    | PluginErrorPathNotFound
    | PluginErrorGitAuthFailed
    | PluginErrorGitTimeout
    | PluginErrorNetworkError
    | PluginErrorManifestParseError
    | PluginErrorManifestValidationError
    | PluginErrorPluginNotFound
    | PluginErrorMarketplaceNotFound
    | PluginErrorMarketplaceLoadFailed
    | PluginErrorMcpConfigInvalid
    | PluginErrorMcpServerSuppressedDuplicate
    | PluginErrorLspConfigInvalid
    | PluginErrorLspServerStartFailed
    | PluginErrorLspServerCrashed
    | PluginErrorLspRequestTimeout
    | PluginErrorLspRequestFailed
    | PluginErrorHookLoadFailed
    | PluginErrorComponentLoadFailed
    | PluginErrorMcpbDownloadFailed
    | PluginErrorMcpbExtractFailed
    | PluginErrorMcpbInvalidManifest
    | PluginErrorMarketplaceBlockedByPolicy
    | PluginErrorDependencyUnsatisfied
    | PluginErrorPluginCacheMiss
    | PluginErrorGeneric
)


def get_plugin_error_message(error: PluginError) -> str:
    """Get a display message from any PluginError.

    Args:
        error: The plugin error.

    Returns:
        Human-readable error message.
    """
    etype = error["type"]

    if etype == "generic-error":
        return cast(PluginErrorGeneric, error)["error"]
    if etype == "path-not-found":
        return f"Path not found: {cast(PluginErrorPathNotFound, error)['path']} ({cast(PluginErrorPathNotFound, error)['component']})"
    if etype == "git-auth-failed":
        return f"Git authentication failed ({cast(PluginErrorGitAuthFailed, error)['auth_type']}): {cast(PluginErrorGitAuthFailed, error)['git_url']}"
    if etype == "git-timeout":
        return f"Git {cast(PluginErrorGitTimeout, error)['operation']} timeout: {cast(PluginErrorGitTimeout, error)['git_url']}"
    if etype == "network-error":
        ne = cast(PluginErrorNetworkError, error)
        details = f" - {ne['details']}" if ne.get("details") else ""
        return f"Network error: {ne['url']}{details}"
    if etype == "manifest-parse-error":
        return f"Manifest parse error: {cast(PluginErrorManifestParseError, error)['parse_error']}"
    if etype == "manifest-validation-error":
        return f"Manifest validation failed: {', '.join(cast(PluginErrorManifestValidationError, error)['validation_errors'])}"
    if etype == "plugin-not-found":
        return f"Plugin {cast(PluginErrorPluginNotFound, error)['plugin_id']} not found in marketplace {cast(PluginErrorPluginNotFound, error)['marketplace']}"
    if etype == "marketplace-not-found":
        return f"Marketplace {cast(PluginErrorMarketplaceNotFound, error)['marketplace']} not found"
    if etype == "marketplace-load-failed":
        return f"Marketplace {cast(PluginErrorMarketplaceLoadFailed, error)['marketplace']} failed to load: {cast(PluginErrorMarketplaceLoadFailed, error)['reason']}"
    if etype == "mcp-config-invalid":
        return f"MCP server {cast(PluginErrorMcpConfigInvalid, error)['server_name']} invalid: {cast(PluginErrorMcpConfigInvalid, error)['validation_error']}"
    if etype == "mcp-server-suppressed-duplicate":
        dup = cast(PluginErrorMcpServerSuppressedDuplicate, error)["duplicate_of"]
        server_name = cast(PluginErrorMcpServerSuppressedDuplicate, error)["server_name"]
        if dup.startswith("plugin:"):
            parts = dup.split(":", 1)
            dup = f'server provided by plugin "{parts[1] if len(parts) > 1 else "?"}"'
        else:
            dup = f'already-configured "{dup}"'
        return f'MCP server "{server_name}" skipped — same command/URL as {dup}'
    if etype == "hook-load-failed":
        return f"Hook load failed: {cast(PluginErrorHookLoadFailed, error)['reason']}"
    if etype == "component-load-failed":
        return f"{cast(PluginErrorComponentLoadFailed, error)['component']} load failed from {cast(PluginErrorComponentLoadFailed, error)['path']}: {cast(PluginErrorComponentLoadFailed, error)['reason']}"
    if etype == "mcpb-download-failed":
        return f"Failed to download MCPB from {cast(PluginErrorMcpbDownloadFailed, error)['url']}: {cast(PluginErrorMcpbDownloadFailed, error)['reason']}"
    if etype == "mcpb-extract-failed":
        return f"Failed to extract MCPB {cast(PluginErrorMcpbExtractFailed, error)['mcpb_path']}: {cast(PluginErrorMcpbExtractFailed, error)['reason']}"
    if etype == "mcpb-invalid-manifest":
        return f"MCPB manifest invalid at {cast(PluginErrorMcpbInvalidManifest, error)['mcpb_path']}: {cast(PluginErrorMcpbInvalidManifest, error)['validation_error']}"
    if etype == "lsp-config-invalid":
        return f'Plugin "{cast(PluginErrorLspConfigInvalid, error)["plugin"]}" has invalid LSP server config for "{cast(PluginErrorLspConfigInvalid, error)["server_name"]}": {cast(PluginErrorLspConfigInvalid, error)["validation_error"]}'
    if etype == "lsp-server-start-failed":
        return f'Plugin "{cast(PluginErrorLspServerStartFailed, error)["plugin"]}" failed to start LSP server "{cast(PluginErrorLspServerStartFailed, error)["server_name"]}": {cast(PluginErrorLspServerStartFailed, error)["reason"]}'
    if etype == "lsp-server-crashed":
        sig = cast(PluginErrorLspServerCrashed, error).get("signal")
        if sig:
            return f'Plugin "{cast(PluginErrorLspServerCrashed, error)["plugin"]}" LSP server "{cast(PluginErrorLspServerCrashed, error)["server_name"]}" crashed with signal {sig}'
        code = cast(PluginErrorLspServerCrashed, error).get("exit_code")
        return f'Plugin "{cast(PluginErrorLspServerCrashed, error)["plugin"]}" LSP server "{cast(PluginErrorLspServerCrashed, error)["server_name"]}" crashed with exit code {code if code is not None else "unknown"}'
    if etype == "lsp-request-timeout":
        return f'Plugin "{cast(PluginErrorLspRequestTimeout, error)["plugin"]}" LSP server "{cast(PluginErrorLspRequestTimeout, error)["server_name"]}" timed out on {cast(PluginErrorLspRequestTimeout, error)["method"]} request after {cast(PluginErrorLspRequestTimeout, error)["timeout_ms"]}ms'
    if etype == "lsp-request-failed":
        return f'Plugin "{cast(PluginErrorLspRequestFailed, error)["plugin"]}" LSP server "{cast(PluginErrorLspRequestFailed, error)["server_name"]}" {cast(PluginErrorLspRequestFailed, error)["method"]} request failed: {cast(PluginErrorLspRequestFailed, error)["error"]}'
    if etype == "marketplace-blocked-by-policy":
        if cast(PluginErrorMarketplaceBlockedByPolicy, error).get("blocked_by_blocklist"):
            return f"Marketplace '{cast(PluginErrorMarketplaceBlockedByPolicy, error)['marketplace']}' is blocked by enterprise policy"
        return f"Marketplace '{cast(PluginErrorMarketplaceBlockedByPolicy, error)['marketplace']}' is not in the allowed marketplace list"
    if etype == "dependency-unsatisfied":
        e = cast(PluginErrorDependencyUnsatisfied, error)
        if e["reason"] == "not-enabled":
            hint = "disabled — enable it or remove the dependency"
        else:
            hint = "not found in any configured marketplace"
        return f'Dependency "{e["dependency"]}" is {hint}'
    if etype == "plugin-cache-miss":
        return f'Plugin "{cast(PluginErrorPluginCacheMiss, error)["plugin"]}" not cached at {cast(PluginErrorPluginCacheMiss, error)["install_path"]} — run /plugins to refresh'

    # Fallback for unknown error types
    return f"Plugin error [{etype}]: {error['source']}"


# =============================================================================
# Plugin Repository
# =============================================================================


@dataclass
class PluginRepository:
    """Repository metadata for a plugin source."""

    url: str
    branch: str
    last_updated: str | None = None
    commit_sha: str | None = None


# =============================================================================
# Plugin Config
# =============================================================================


@dataclass
class PluginConfig:
    """Plugin configuration containing marketplace sources."""

    repositories: dict[str, PluginRepository] = field(default_factory=dict)


# =============================================================================
# Plugin Load Result
# =============================================================================


@dataclass
class PluginLoadResult:
    """Result of loading plugins from all sources.

    Attributes:
        enabled: Plugins that are currently enabled.
        disabled: Plugins that are registered but disabled.
        errors: Errors encountered during plugin loading.
    """

    enabled: list[Any] = field(default_factory=list)  # list[LoadedPlugin]
    disabled: list[Any] = field(default_factory=list)  # list[LoadedPlugin]
    errors: list[PluginError] = field(default_factory=list)


__all__ = [
    # Re-exports from builtin
    "BUILTIN_MARKETPLACE_NAME",
    "BuiltinPluginDefinition",
    "builtin_plugins_count",
    "get_builtin_plugin_definition",
    "get_builtin_plugins",
    "is_builtin_plugin_id",
    "register_builtin_plugin",
    # Error types
    "PluginError",
    "PluginErrorComponentLoadFailed",
    "PluginErrorDependencyUnsatisfied",
    "PluginErrorGeneric",
    "PluginErrorGitAuthFailed",
    "PluginErrorGitTimeout",
    "PluginErrorHookLoadFailed",
    "PluginErrorLspConfigInvalid",
    "PluginErrorLspRequestFailed",
    "PluginErrorLspRequestTimeout",
    "PluginErrorLspServerCrashed",
    "PluginErrorLspServerStartFailed",
    "PluginErrorMcpbDownloadFailed",
    "PluginErrorMcpbExtractFailed",
    "PluginErrorMcpbInvalidManifest",
    "PluginErrorMcpConfigInvalid",
    "PluginErrorMcpServerSuppressedDuplicate",
    "PluginErrorManifestParseError",
    "PluginErrorManifestValidationError",
    "PluginErrorMarketplaceBlockedByPolicy",
    "PluginErrorMarketplaceLoadFailed",
    "PluginErrorMarketplaceNotFound",
    "PluginErrorNetworkError",
    "PluginErrorPathNotFound",
    "PluginErrorPluginCacheMiss",
    "PluginErrorPluginNotFound",
    # Utilities
    "PluginComponent",
    "PluginLoadResult",
    "PluginRepository",
    "get_plugin_error_message",
]
