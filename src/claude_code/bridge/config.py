"""Bridge configuration and auth utilities.

Shared bridge auth/URL resolution. Consolidates the ant-only
CLAUDE_BRIDGE_* dev overrides that were previously copy-pasted across
a dozen files.

Two layers: *Override() returns the ant-only env var (or None);
the non-Override versions fall through to the real OAuth store/config.

TypeScript equivalent: src/bridge/bridgeConfig.ts
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# =============================================================================
# Constants
# =============================================================================

BRIDGE_LOGIN_INSTRUCTION = (
    "Please run `claude auth login` to sign in with your claude.ai account "
    "to use Remote Control."
)

# =============================================================================
# Types
# =============================================================================


class SpawnMode(StrEnum):
    """How claude remote-control chooses session working directories."""

    SINGLE_SESSION = "single-session"
    WORKTREE = "worktree"
    SAME_DIR = "same-dir"


class WorkerType(StrEnum):
    """Well-known worker_type values."""

    CLAUDE_CODE = "claude_code"
    CLAUDE_CODE_ASSISTANT = "claude_code_assistant"


# =============================================================================
# BridgeConfig
# =============================================================================


@dataclass
class BridgeConfig:
    """Configuration for a bridge environment.

    Attributes:
        dir: Working directory for the bridge.
        machine_name: Name of this machine.
        branch: Current git branch.
        git_repo_url: Git repository URL (if available).
        max_sessions: Maximum number of concurrent sessions.
        spawn_mode: How sessions are spawned (single-session, worktree, same-dir).
        verbose: Enable verbose logging.
        sandbox: Enable sandbox mode.
        bridge_id: Client-generated UUID identifying this bridge instance.
        worker_type: Worker type sent as metadata.worker_type.
        environment_id: Client-generated UUID for idempotent environment registration.
        reuse_environment_id: Backend-issued environment_id to reuse on re-register.
        api_base_url: API base URL the bridge is connected to.
        session_ingress_url: Session ingress base URL for WebSocket connections.
        debug_file: Debug file path passed via --debug-file.
        session_timeout_ms: Per-session timeout in milliseconds.
    """

    dir: str
    machine_name: str
    branch: str
    git_repo_url: str | None
    max_sessions: int
    spawn_mode: SpawnMode
    verbose: bool
    sandbox: bool
    bridge_id: str
    worker_type: str
    environment_id: str
    api_base_url: str
    session_ingress_url: str
    reuse_environment_id: str | None = None
    debug_file: str | None = None
    session_timeout_ms: int | None = None


# =============================================================================
# Stub OAuth helpers (replace with real impl when auth module is ready)
# =============================================================================


def _get_oauth_config() -> dict[str, str]:
    """Get OAuth config. Stub until auth module is ready.

    Returns:
        Dict with BASE_API_URL and other OAuth config values.
    """
    # In production, this would read from the real OAuth keychain/store.
    # Stub returns the production default.
    return {
        "BASE_API_URL": "https://api.claude.ai",
    }


def _get_oauth_tokens() -> dict[str, str] | None:
    """Get OAuth tokens. Stub until auth module is ready.

    Returns:
        Dict with accessToken and refreshToken, or None if not logged in.
    """
    # In production, this would read from the real OAuth keychain/store.
    return None


# =============================================================================
# Dev Override Getters (ANT-only)
# =============================================================================


def get_bridge_token_override() -> str | None:
    """ANT-only dev override: CLAUDE_BRIDGE_OAUTH_TOKEN, else None.

    Returns:
        The CLAUDE_BRIDGE_OAUTH_TOKEN env var value if USER_TYPE is 'ant'.
    """
    user_type = os.environ.get("USER_TYPE", "")
    if user_type == "ant":
        return os.environ.get("CLAUDE_BRIDGE_OAUTH_TOKEN")
    return None


def get_bridge_base_url_override() -> str | None:
    """ANT-only dev override: CLAUDE_BRIDGE_BASE_URL, else None.

    Returns:
        The CLAUDE_BRIDGE_BASE_URL env var value if USER_TYPE is 'ant'.
    """
    user_type = os.environ.get("USER_TYPE", "")
    if user_type == "ant":
        return os.environ.get("CLAUDE_BRIDGE_BASE_URL")
    return None


# =============================================================================
# Public Getters
# =============================================================================


def get_bridge_access_token() -> str | None:
    """Access token for bridge API calls: dev override first, then the OAuth keychain.

    Returns:
        The bridge access token, or None if not logged in.
    """
    override = get_bridge_token_override()
    if override:
        return override
    tokens = _get_oauth_tokens()
    return tokens.get("accessToken") if tokens else None


def get_bridge_base_url() -> str:
    """Base URL for bridge API calls: dev override first, then the production OAuth config.

    Returns:
        The bridge base URL (always returns a URL).
    """
    override = get_bridge_base_url_override()
    if override:
        return override
    return _get_oauth_config().get("BASE_API_URL", "https://api.claude.ai")
