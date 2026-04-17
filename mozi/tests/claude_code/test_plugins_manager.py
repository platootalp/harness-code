"""
Tests for plugins/manager.py - Plugin error types and manager components.
"""

from __future__ import annotations

import pytest

from src.claude_code.plugins.manager import (
    PluginComponent,
    PluginLoadResult,
    PluginRepository,
    get_plugin_error_message,
)


class TestPluginComponent:
    """Tests for PluginComponent constants."""

    def test_component_types(self) -> None:
        """All component types are defined."""
        assert PluginComponent.COMMANDS == "commands"
        assert PluginComponent.AGENTS == "agents"
        assert PluginComponent.SKILLS == "skills"
        assert PluginComponent.HOOKS == "hooks"
        assert PluginComponent.OUTPUT_STYLES == "output-styles"


class TestPluginRepository:
    """Tests for PluginRepository dataclass."""

    def test_create_repository(self) -> None:
        """Create a repository with all fields."""
        repo = PluginRepository(
            url="https://github.com/user/repo",
            branch="main",
            last_updated="2026-04-01",
            commit_sha="abc123",
        )
        assert repo.url == "https://github.com/user/repo"
        assert repo.branch == "main"
        assert repo.last_updated == "2026-04-01"
        assert repo.commit_sha == "abc123"

    def test_repository_optional_fields(self) -> None:
        """Repository with minimal fields."""
        repo = PluginRepository(url="https://github.com/user/repo", branch="main")
        assert repo.last_updated is None
        assert repo.commit_sha is None


class TestPluginLoadResult:
    """Tests for PluginLoadResult dataclass."""

    def test_empty_result(self) -> None:
        """Empty result with no plugins or errors."""
        result = PluginLoadResult()
        assert result.enabled == []
        assert result.disabled == []
        assert result.errors == []

    def test_result_with_plugins(self) -> None:
        """Result with enabled and disabled plugins."""
        result = PluginLoadResult(
            enabled=["plugin-a", "plugin-b"],
            disabled=["plugin-c"],
            errors=[],
        )
        assert len(result.enabled) == 2
        assert len(result.disabled) == 1
        assert result.errors == []


class TestGetPluginErrorMessage:
    """Tests for get_plugin_error_message() with all error types."""

    def test_generic_error(self) -> None:
        """Generic error message."""
        error = {"type": "generic-error", "source": "test", "error": "Something went wrong"}
        msg = get_plugin_error_message(error)
        assert "Something went wrong" in msg

    def test_path_not_found(self) -> None:
        """Path not found error."""
        error = {
            "type": "path-not-found",
            "source": "test",
            "plugin": "test-plugin",
            "path": "/missing/path",
            "component": "hooks",
        }
        msg = get_plugin_error_message(error)
        assert "/missing/path" in msg
        assert "hooks" in msg

    def test_git_auth_failed(self) -> None:
        """Git authentication failed."""
        error = {
            "type": "git-auth-failed",
            "source": "test",
            "plugin": "git-plugin",
            "git_url": "https://github.com/user/repo",
            "auth_type": "ssh",
        }
        msg = get_plugin_error_message(error)
        assert "authentication failed" in msg
        assert "ssh" in msg

    def test_git_timeout(self) -> None:
        """Git timeout error."""
        error = {
            "type": "git-timeout",
            "source": "test",
            "plugin": "git-plugin",
            "git_url": "https://github.com/user/repo",
            "operation": "clone",
        }
        msg = get_plugin_error_message(error)
        assert "timeout" in msg
        assert "clone" in msg

    def test_network_error(self) -> None:
        """Network error."""
        error = {
            "type": "network-error",
            "source": "test",
            "plugin": None,
            "url": "https://example.com/plugin",
            "details": "Connection refused",
        }
        msg = get_plugin_error_message(error)
        assert "Network error" in msg
        assert "example.com" in msg

    def test_network_error_without_details(self) -> None:
        """Network error without details."""
        error = {
            "type": "network-error",
            "source": "test",
            "plugin": None,
            "url": "https://example.com",
            "details": None,
        }
        msg = get_plugin_error_message(error)
        assert "Network error" in msg
        assert "example.com" in msg

    def test_manifest_parse_error(self) -> None:
        """Manifest parse error."""
        error = {
            "type": "manifest-parse-error",
            "source": "test",
            "plugin": "bad-plugin",
            "manifest_path": "/path/to/manifest.json",
            "parse_error": "Unexpected token",
        }
        msg = get_plugin_error_message(error)
        assert "parse error" in msg
        assert "Unexpected token" in msg

    def test_manifest_validation_error(self) -> None:
        """Manifest validation error."""
        error = {
            "type": "manifest-validation-error",
            "source": "test",
            "plugin": "bad-plugin",
            "manifest_path": "/path/to/manifest.json",
            "validation_errors": ["name is required", "version is required"],
        }
        msg = get_plugin_error_message(error)
        assert "validation failed" in msg
        assert "name is required" in msg

    def test_plugin_not_found(self) -> None:
        """Plugin not found in marketplace."""
        error = {
            "type": "plugin-not-found",
            "source": "test",
            "plugin": None,
            "plugin_id": "nonexistent",
            "marketplace": "npm",
        }
        msg = get_plugin_error_message(error)
        assert "nonexistent" in msg
        assert "npm" in msg

    def test_marketplace_not_found(self) -> None:
        """Marketplace not found."""
        error = {
            "type": "marketplace-not-found",
            "source": "test",
            "plugin": None,
            "marketplace": "unknown-market",
            "available_marketplaces": ["npm", "pip"],
        }
        msg = get_plugin_error_message(error)
        assert "unknown-market" in msg

    def test_marketplace_load_failed(self) -> None:
        """Marketplace load failed."""
        error = {
            "type": "marketplace-load-failed",
            "source": "test",
            "plugin": None,
            "marketplace": "bad-market",
            "reason": "Invalid response",
        }
        msg = get_plugin_error_message(error)
        assert "bad-market" in msg
        assert "Invalid response" in msg

    def test_mcp_config_invalid(self) -> None:
        """MCP config invalid error."""
        error = {
            "type": "mcp-config-invalid",
            "source": "test",
            "plugin": "test-plugin",
            "server_name": "my-server",
            "validation_error": "missing command",
        }
        msg = get_plugin_error_message(error)
        assert "my-server" in msg
        assert "invalid" in msg

    def test_mcp_server_suppressed_duplicate(self) -> None:
        """MCP server duplicate suppressed."""
        error = {
            "type": "mcp-server-suppressed-duplicate",
            "source": "test",
            "plugin": "test-plugin",
            "server_name": "dup-server",
            "duplicate_of": "already-configured:s1",
        }
        msg = get_plugin_error_message(error)
        assert "dup-server" in msg
        assert "skipped" in msg

    def test_mcp_server_suppressed_duplicate_plugin(self) -> None:
        """MCP server duplicate from plugin."""
        error = {
            "type": "mcp-server-suppressed-duplicate",
            "source": "test",
            "plugin": "test-plugin",
            "server_name": "dup-server",
            "duplicate_of": "plugin:other-plugin",
        }
        msg = get_plugin_error_message(error)
        assert "other-plugin" in msg

    def test_hook_load_failed(self) -> None:
        """Hook load failed error."""
        error = {
            "type": "hook-load-failed",
            "source": "test",
            "plugin": "test-plugin",
            "hook_path": "/path/to/hook.py",
            "reason": "Syntax error",
        }
        msg = get_plugin_error_message(error)
        assert "load failed" in msg
        assert "Syntax error" in msg

    def test_component_load_failed(self) -> None:
        """Component load failed error."""
        error = {
            "type": "component-load-failed",
            "source": "test",
            "plugin": "test-plugin",
            "component": "skills",
            "path": "/path/to/skills",
            "reason": "Import error",
        }
        msg = get_plugin_error_message(error)
        assert "skills" in msg
        assert "Import error" in msg

    def test_mcpb_download_failed(self) -> None:
        """MCPB download failed."""
        error = {
            "type": "mcpb-download-failed",
            "source": "test",
            "plugin": "test-plugin",
            "url": "https://example.com/plugin.mcpb",
            "reason": "404 Not Found",
        }
        msg = get_plugin_error_message(error)
        assert "download" in msg
        assert "404 Not Found" in msg

    def test_mcpb_extract_failed(self) -> None:
        """MCPB extract failed."""
        error = {
            "type": "mcpb-extract-failed",
            "source": "test",
            "plugin": "test-plugin",
            "mcpb_path": "/path/to/plugin.mcpb",
            "reason": "Corrupted archive",
        }
        msg = get_plugin_error_message(error)
        assert "extract" in msg
        assert "Corrupted archive" in msg

    def test_mcpb_invalid_manifest(self) -> None:
        """MCPB invalid manifest."""
        error = {
            "type": "mcpb-invalid-manifest",
            "source": "test",
            "plugin": "test-plugin",
            "mcpb_path": "/path/to/plugin.mcpb",
            "validation_error": "missing name field",
        }
        msg = get_plugin_error_message(error)
        assert "invalid" in msg
        assert "missing name field" in msg

    def test_lsp_config_invalid(self) -> None:
        """LSP config invalid."""
        error = {
            "type": "lsp-config-invalid",
            "source": "test",
            "plugin": "test-plugin",
            "server_name": "lsp-server",
            "validation_error": "missing command",
        }
        msg = get_plugin_error_message(error)
        assert "lsp-server" in msg
        assert "invalid" in msg

    def test_lsp_server_start_failed(self) -> None:
        """LSP server start failed."""
        error = {
            "type": "lsp-server-start-failed",
            "source": "test",
            "plugin": "test-plugin",
            "server_name": "lsp-server",
            "reason": "binary not found",
        }
        msg = get_plugin_error_message(error)
        assert "failed to start" in msg
        assert "lsp-server" in msg

    def test_lsp_server_crashed_with_signal(self) -> None:
        """LSP server crashed with signal."""
        error = {
            "type": "lsp-server-crashed",
            "source": "test",
            "plugin": "test-plugin",
            "server_name": "lsp-server",
            "exit_code": None,
            "signal": "SIGSEGV",
        }
        msg = get_plugin_error_message(error)
        assert "crashed" in msg
        assert "SIGSEGV" in msg

    def test_lsp_server_crashed_with_exit_code(self) -> None:
        """LSP server crashed with exit code."""
        error = {
            "type": "lsp-server-crashed",
            "source": "test",
            "plugin": "test-plugin",
            "server_name": "lsp-server",
            "exit_code": 1,
            "signal": None,
        }
        msg = get_plugin_error_message(error)
        assert "crashed" in msg
        assert "exit code 1" in msg

    def test_lsp_server_crashed_unknown(self) -> None:
        """LSP server crashed with unknown code."""
        error = {
            "type": "lsp-server-crashed",
            "source": "test",
            "plugin": "test-plugin",
            "server_name": "lsp-server",
            "exit_code": None,
            "signal": None,
        }
        msg = get_plugin_error_message(error)
        assert "crashed" in msg
        assert "unknown" in msg

    def test_lsp_request_timeout(self) -> None:
        """LSP request timeout."""
        error = {
            "type": "lsp-request-timeout",
            "source": "test",
            "plugin": "test-plugin",
            "server_name": "lsp-server",
            "method": "initialize",
            "timeout_ms": 5000,
        }
        msg = get_plugin_error_message(error)
        assert "timed out" in msg
        assert "5000ms" in msg

    def test_lsp_request_failed(self) -> None:
        """LSP request failed."""
        error = {
            "type": "lsp-request-failed",
            "source": "test",
            "plugin": "test-plugin",
            "server_name": "lsp-server",
            "method": "initialize",
            "error": "Server not initialized",
        }
        msg = get_plugin_error_message(error)
        assert "initialize" in msg
        assert "failed" in msg

    def test_marketplace_blocked_by_policy_blocklist(self) -> None:
        """Marketplace blocked by blocklist."""
        error = {
            "type": "marketplace-blocked-by-policy",
            "source": "test",
            "plugin": None,
            "marketplace": "untrusted-market",
            "blocked_by_blocklist": True,
            "allowed_sources": ["npm", "pip"],
        }
        msg = get_plugin_error_message(error)
        assert "blocked by enterprise policy" in msg

    def test_marketplace_blocked_by_policy_allowlist(self) -> None:
        """Marketplace not in allowed list."""
        error = {
            "type": "marketplace-blocked-by-policy",
            "source": "test",
            "plugin": None,
            "marketplace": "other-market",
            "blocked_by_blocklist": False,
            "allowed_sources": ["npm", "pip"],
        }
        msg = get_plugin_error_message(error)
        assert "not in the allowed marketplace list" in msg

    def test_dependency_unsatisfied_not_enabled(self) -> None:
        """Dependency not enabled."""
        error = {
            "type": "dependency-unsatisfied",
            "source": "test",
            "plugin": "test-plugin",
            "dependency": "required-plugin",
            "reason": "not-enabled",
        }
        msg = get_plugin_error_message(error)
        assert "required-plugin" in msg
        assert "disabled" in msg

    def test_dependency_unsatisfied_not_found(self) -> None:
        """Dependency not found."""
        error = {
            "type": "dependency-unsatisfied",
            "source": "test",
            "plugin": "test-plugin",
            "dependency": "missing-plugin",
            "reason": "not-found",
        }
        msg = get_plugin_error_message(error)
        assert "missing-plugin" in msg
        assert "not found" in msg

    def test_plugin_cache_miss(self) -> None:
        """Plugin cache miss."""
        error = {
            "type": "plugin-cache-miss",
            "source": "test",
            "plugin": "test-plugin",
            "install_path": "/path/to/cache",
        }
        msg = get_plugin_error_message(error)
        assert "not cached" in msg
        assert "test-plugin" in msg

    def test_unknown_error_type(self) -> None:
        """Unknown error type falls back to generic message."""
        error = {
            "type": "unknown-error-type",
            "source": "test-source",
            "plugin": None,
        }
        msg = get_plugin_error_message(error)
        assert "unknown-error-type" in msg
        assert "test-source" in msg
