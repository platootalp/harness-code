"""Tool Search utilities for dynamically discovering deferred tools.

Migrated from src/utils/toolSearch.ts.
"""

from __future__ import annotations

import os

from ..services.api.claude import ProviderType, get_api_provider

# =============================================================================
# Tool Search Mode
# =============================================================================


class ToolSearchMode:
    """Tool search mode discriminator."""

    TST = "tst"
    TST_AUTO = "tst-auto"
    STANDARD = "standard"


def _is_env_defined_falsy(value: str | None) -> bool:
    """Check if env var is defined but falsy."""
    if value is None:
        return False
    return value in ("", "0", "false", "no", "off", "none")


def _is_env_truthy(value: str | None) -> bool:
    """Check if env var is truthy."""
    if not value:
        return False
    lower = value.lower()
    return lower in ("1", "true", "yes", "on")


def _is_first_party_anthropic_base_url() -> bool:
    """Check if ANTHROPIC_BASE_URL is set to first-party Anthropic host."""
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "")
    # First-party: api.anthropic.com or no override
    if not base_url:
        return True
    normalized = base_url.lower().rstrip("/")
    return normalized in (
        "https://api.anthropic.com",
        "http://api.anthropic.com",
        "https://api.anthropic.com/v1",
        "http://api.anthropic.com/v1",
    )


def _is_auto_mode(value: str | None) -> bool:
    """Check if ENABLE_TOOL_SEARCH is set to auto mode."""
    if not value:
        return False
    return value == "auto" or value.startswith("auto:")


def _parse_auto_percentage(value: str) -> int | None:
    """Parse auto:N syntax from ENABLE_TOOL_SEARCH env var."""
    if not value.startswith("auto:"):
        return None
    percent_str = value[5:]
    try:
        return int(percent_str)
    except ValueError:
        return None


def get_tool_search_mode() -> str:
    """Determine the tool search mode from ENABLE_TOOL_SEARCH.

    Returns:
        'tst' (always defer), 'tst-auto' (defer when threshold exceeded),
        or 'standard' (all tools exposed inline).
    """
    # Check kill switch
    if _is_env_truthy(os.environ.get("CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS")):
        return ToolSearchMode.STANDARD

    value = os.environ.get("ENABLE_TOOL_SEARCH")

    # Handle auto:N syntax
    if value:
        auto_percent = _parse_auto_percentage(value)
        if auto_percent == 0:
            return ToolSearchMode.TST
        if auto_percent == 100:
            return ToolSearchMode.STANDARD
        if _is_auto_mode(value):
            return ToolSearchMode.TST_AUTO

    if _is_env_truthy(value):
        return ToolSearchMode.TST
    if _is_env_defined_falsy(value):
        return ToolSearchMode.STANDARD
    return ToolSearchMode.TST  # default: always defer MCP and shouldDefer tools


# =============================================================================
# Optimistic Check
# =============================================================================

_logged_optimistic: bool = False


def is_tool_search_enabled_optimistic() -> bool:
    """Check if tool search *might* be enabled (optimistic check).

    Returns True if tool search could potentially be enabled, without checking
    dynamic factors like model support or threshold. Use this for:
    - Including ToolSearchTool in base tools (so it's available if needed)
    - Preserving tool_reference fields in messages (can be stripped later)
    - Checking if ToolSearchTool should report itself as enabled

    Returns False only when tool search is definitively disabled (standard mode).

    For the definitive check that includes model support and threshold,
    use is_tool_search_enabled().
    """
    global _logged_optimistic

    mode = get_tool_search_mode()
    if mode == ToolSearchMode.STANDARD:
        return False

    # tool_reference is a beta content type that third-party API gateways
    # (ANTHROPIC_BASE_URL proxies) typically don't support. When the provider
    # is 'direct' but the base URL points elsewhere, the proxy may reject
    # tool_reference blocks. This gate only applies when ENABLE_TOOL_SEARCH
    # is unset/empty (default behavior).
    enable_tool_search = os.environ.get("ENABLE_TOOL_SEARCH")
    if not enable_tool_search:
        if get_api_provider() == ProviderType.DIRECT and not _is_first_party_anthropic_base_url():
            return False

    return True
