"""Bridge feature gates and entitlement checks.

Runtime checks for bridge mode availability, GrowthBook feature flags,
and version compatibility.

This is a simplified implementation without GrowthBook integration.
In production, these would be backed by GrowthBook feature flags.

TypeScript equivalent: src/bridge/bridgeEnabled.ts
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


# =============================================================================
# Bridge Mode Entitlements
# =============================================================================


def is_bridge_enabled() -> bool:
    """Runtime check for bridge mode entitlement.

    Remote Control requires a claude.ai subscription. This simplified
    implementation returns True unconditionally. In production, this would
    check isClaudeAISubscriber() and GrowthBook's tengu_ccr_bridge flag.

    Returns:
        True if bridge mode is enabled.
    """
    return True


def is_env_less_bridge_enabled() -> bool:
    """Runtime check for the env-less (v2) REPL bridge path.

    Returns False in this simplified implementation (no GrowthBook).
    """
    return False


def is_cse_shim_enabled() -> bool:
    """Kill-switch for the cse_* -> session_* client-side retag shim.

    The shim exists because the server tags with cse_* while the claw
    routes on session_*. Once the server tags by environment_kind and the
    claw accepts cse_* directly, this can be set to False.

    Returns:
        True (shim is active by default).
    """
    return True


def check_bridge_min_version() -> str | None:
    """Check if the current CLI version is below the minimum required for bridge.

    In this simplified implementation, always returns None (version is fine).
    In production, this reads from GrowthBook's tengu_bridge_min_version config.

    Returns:
        None if version is OK, or an error message string.
    """
    return None


def get_ccr_auto_connect_default() -> bool:
    """Default for remoteControlAtStartup when the user hasn't explicitly set it.

    In this simplified implementation, returns False. In production, this would
    check the CCR_AUTO_CONNECT build flag and GrowthBook's tengu_cobalt_harbor gate.

    Returns:
        False (users must explicitly enable auto-connect).
    """
    return False


def is_ccr_mirror_enabled() -> bool:
    """Opt-in CCR mirror mode — every local session spawns an outbound-only
    Remote Control session that receives forwarded events.

    In this simplified implementation, returns False. In production, this would
    check the CCR_MIRROR build flag and CLAUDE_CODE_CCR_MIRROR env var or
    GrowthBook's tengu_ccr_mirror gate.

    Returns:
        False (CCR mirror is disabled by default).
    """
    return False


# =============================================================================
# Async Entitlement Functions
# =============================================================================


async def is_bridge_enabled_blocking() -> bool:
    """Blocking entitlement check for Remote Control.

    Returns the cached value immediately (fast path). In the simplified
    implementation without GrowthBook, this is identical to is_bridge_enabled().

    Returns:
        True if bridge mode is enabled.
    """
    return is_bridge_enabled()


async def get_bridge_disabled_reason() -> str | None:
    """Diagnostic message for why Remote Control is unavailable, or null if enabled.

    In the simplified implementation without GrowthBook, always returns None
    since bridge is considered enabled.

    Returns:
        None if Remote Control is enabled, or a diagnostic string.
    """
    if is_bridge_enabled():
        return None
    return "Remote Control is not available in this build."
