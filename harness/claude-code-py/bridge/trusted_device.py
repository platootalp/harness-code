"""Trusted device enrollment for bridge (Remote Control) sessions.

Trusted device tokens are required for CCR v2 sessions with SecurityTier=ELEVATED.
Enrollment (POST /auth/trusted_devices) is gated server-side by
account_session.created_at < 10min, so it must happen during /login.

Simplified implementation without GrowthBook integration or keychain access.

TypeScript equivalent: src/bridge/trustedDevice.ts
"""

from __future__ import annotations

# =============================================================================
# Token Access
# =============================================================================


def get_trusted_device_token() -> str | None:
    """Get the trusted device token if available.

    In the simplified implementation without GrowthBook gate or keychain access,
    always returns None. In production, this would check the GrowthBook gate,
    the env var, and the keychain.

    Returns:
        The trusted device token, or None.
    """
    # Simplified: no GrowthBook gate, no keychain access
    return None


def clear_trusted_device_token_cache() -> None:
    """Clear the memoized token cache.

    In the simplified implementation, this is a no-op.
    """
    pass


# =============================================================================
# Token Storage Management
# =============================================================================


def clear_trusted_device_token() -> None:
    """Clear the stored trusted device token from secure storage and cache.

    In the simplified implementation, this is a no-op since there's no
    keychain access available.
    """
    pass


# =============================================================================
# Device Enrollment
# =============================================================================


async def enroll_trusted_device() -> None:
    """Enroll this device via POST /auth/trusted_devices.

    Best-effort — logs and returns on failure so callers (post-login hooks)
    don't block the login flow. In the simplified implementation without
    GrowthBook or keychain access, this is a no-op.
    """
    pass
