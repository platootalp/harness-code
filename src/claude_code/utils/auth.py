"""Authentication and API key management utilities."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from enum import StrEnum

# =============================================================================
# API Key Source
# =============================================================================


class ApiKeySource(StrEnum):
    """Source of the Anthropic API key."""

    ANTHROPIC_API_KEY = "ANTHROPIC_API_KEY"
    API_KEY_HELPER = "apiKeyHelper"
    LOGIN_MANAGED_KEY = "/login managed key"
    NONE = "none"


# =============================================================================
# API Key Result
# =============================================================================


@dataclass
class ApiKeyResult:
    """Result of API key retrieval with source information."""

    key: str | None
    source: ApiKeySource


# =============================================================================
# Environment Variables
# =============================================================================

_ANTHROPIC_API_KEY_ENV = "ANTHROPIC_API_KEY"
_API_KEY_HELPER_ENV = "ANTHROPIC_API_KEY_HELPER"
_API_KEY_HELPER_CACHE_KEY = "_anthropic_api_key_helper_cache"
_API_KEY_HELPER_EPOCH_KEY = "_anthropic_api_key_helper_epoch"


# =============================================================================
# Helper Cache
# =============================================================================

_helper_cache: dict[str, str | None] = {}
_helper_epoch: int = 0


def _get_helper_cache() -> dict[str, str | None]:
    """Get the shared helper cache."""
    return _helper_cache


def _get_helper_epoch() -> int:
    """Get the current helper epoch."""
    return _helper_epoch


# =============================================================================
# OAuth Detection
# =============================================================================


def is_anthropic_auth_enabled() -> bool:
    """Check if Anthropic OAuth is enabled.

    Returns:
        True if OAuth authentication is enabled.
    """
    return os.environ.get("ANTHROPIC_AUTH_ENABLED", "").lower() in ("1", "true", "yes")


# =============================================================================
# Auth Token Source
# =============================================================================


def get_auth_token_source() -> dict[str, str]:
    """Get where the auth token is being sourced from.

    Returns:
        Dict with 'source' key indicating where the token comes from.
    """
    if is_anthropic_auth_enabled():
        return {"source": "oauth"}
    if os.environ.get(_ANTHROPIC_API_KEY_ENV):
        return {"source": "env"}
    helper = os.environ.get(_API_KEY_HELPER_ENV)
    if helper:
        return {"source": "helper", "helper": helper}
    return {"source": "none"}


# =============================================================================
# API Key Retrieval
# =============================================================================


def get_anthropic_api_key() -> str | None:
    """Get Anthropic API key from any available source.

    Checks in order: OAuth, environment variable, apiKeyHelper.

    Returns:
        The API key string, or None if not found.
    """
    result = get_anthropic_api_key_with_source(skip_retrieving_key_from_helper=False)
    return result.key


def has_anthropic_api_key_auth() -> bool:
    """Check if API key authentication is available.

    Returns:
        True if any API key source is available.
    """
    if is_anthropic_auth_enabled():
        return True
    if os.environ.get(_ANTHROPIC_API_KEY_ENV):
        return True
    helper = os.environ.get(_API_KEY_HELPER_ENV)
    return bool(helper)


def get_anthropic_api_key_with_source(
    skip_retrieving_key_from_helper: bool = False,
) -> ApiKeyResult:
    """Get API key with its source.

    Args:
        skip_retrieving_key_from_helper: If True, skip the apiKeyHelper source.

    Returns:
        ApiKeyResult with the key and its source.
    """
    if is_anthropic_auth_enabled():
        return ApiKeyResult(key=None, source=ApiKeySource.ANTHROPIC_API_KEY)

    env_key = os.environ.get(_ANTHROPIC_API_KEY_ENV)
    if env_key:
        return ApiKeyResult(key=env_key, source=ApiKeySource.ANTHROPIC_API_KEY)

    if not skip_retrieving_key_from_helper:
        helper_cmd = os.environ.get(_API_KEY_HELPER_ENV)
        if helper_cmd:
            # Sync helper call
            try:
                result = asyncio.run(_call_api_key_helper_async(helper_cmd, False))
                if result is not None:
                    return ApiKeyResult(key=result, source=ApiKeySource.API_KEY_HELPER)
            except Exception:
                pass

    return ApiKeyResult(key=None, source=ApiKeySource.NONE)


def get_configured_api_key_helper() -> str | None:
    """Get the configured apiKeyHelper command.

    Returns:
        The configured helper command, or None if not set.
    """
    return os.environ.get(_API_KEY_HELPER_ENV)


# =============================================================================
# API Key Helper Execution
# =============================================================================


async def get_api_key_from_api_key_helper(
    is_non_interactive: bool,
) -> str | None:
    """Execute apiKeyHelper and cache the result.

    Args:
        is_non_interactive: Whether to suppress prompts.

    Returns:
        The API key from the helper, or None if unavailable.
    """
    helper_cmd = os.environ.get(_API_KEY_HELPER_ENV)
    if not helper_cmd:
        return None

    return await _call_api_key_helper_async(helper_cmd, is_non_interactive)


async def _call_api_key_helper_async(
    helper_cmd: str,
    is_non_interactive: bool,
) -> str | None:
    """Call the apiKeyHelper command asynchronously.

    Args:
        helper_cmd: The helper command to execute.
        is_non_interactive: Whether to suppress prompts.

    Returns:
        The API key, or None if unavailable.
    """
    cache = _get_helper_cache()
    epoch = _get_helper_epoch()
    cache_key = f"{helper_cmd}:{epoch}:{is_non_interactive}"

    if cache_key in cache:
        return cache[cache_key]

    try:
        proc = await asyncio.create_subprocess_shell(
            helper_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "CI": "1"} if is_non_interactive else None,
        )
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=30.0
        )
        if proc.returncode == 0:
            key = stdout_bytes.decode("utf-8").strip()
            if key:
                cache[cache_key] = key
                return key
    except (TimeoutError, OSError):
        pass

    cache[cache_key] = None
    return None


# =============================================================================
# Cache Management
# =============================================================================


def clear_api_key_helper_cache() -> None:
    """Clear the apiKeyHelper cache and increment the epoch.

    This forces the next API key lookup to re-run the helper.
    """
    global _helper_epoch
    _helper_cache.clear()
    _helper_epoch += 1
