"""AWS and GCP cloud authentication utilities."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from typing import Any

# =============================================================================
# Cache State
# =============================================================================

_aws_credentials_cache: dict[str, Any] | None = None
_aws_credentials_cache_time: datetime | None = None
_aws_credentials_cache_ttl = timedelta(minutes=15)

_gcp_credentials_cache: bool | None = None
_gcp_credentials_cache_time: datetime | None = None
_gcp_credentials_cache_ttl = timedelta(minutes=30)


# =============================================================================
# AWS Credentials
# =============================================================================


def _is_aws_cache_valid() -> bool:
    """Check if AWS credentials cache is still valid."""
    if _aws_credentials_cache is None or _aws_credentials_cache_time is None:
        return False
    return datetime.now(UTC) - _aws_credentials_cache_time < _aws_credentials_cache_ttl


async def refresh_and_get_aws_credentials() -> dict[str, str] | None:
    """Refresh AWS auth and get credentials with caching.

    Uses SWR (stale-while-revalidate) pattern: returns cached
    credentials while fetching fresh ones in the background.

    Returns:
        Dict with access_key, secret_key, session_token, or None if unavailable.
    """
    global _aws_credentials_cache, _aws_credentials_cache_time

    if _is_aws_cache_valid() and _aws_credentials_cache is not None:
        return _aws_credentials_cache

    try:
        result = await _fetch_aws_credentials_async()
        if result is not None:
            _aws_credentials_cache = result
            _aws_credentials_cache_time = datetime.now(UTC)
        return result
    except Exception:
        # Return stale cache if available
        if _aws_credentials_cache is not None:
            return _aws_credentials_cache
        return None


async def _fetch_aws_credentials_async() -> dict[str, str] | None:
    """Fetch AWS credentials via sts get-caller-identity.

    Returns:
        Credentials dict or None if fetch fails.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            "aws",
            "sts",
            "get-caller-identity",
            "--output",
            "json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=15.0
        )
        if proc.returncode == 0:
            data = json.loads(stdout_bytes.decode("utf-8"))
            return {
                "account": data.get("Account", ""),
                "arn": data.get("Arn", ""),
            }
    except (TimeoutError, FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return None


def clear_aws_credentials_cache() -> None:
    """Clear AWS credentials cache."""
    global _aws_credentials_cache, _aws_credentials_cache_time
    _aws_credentials_cache = None
    _aws_credentials_cache_time = None


# =============================================================================
# GCP Credentials
# =============================================================================


def _is_gcp_cache_valid() -> bool:
    """Check if GCP credentials cache is still valid."""
    if _gcp_credentials_cache is None or _gcp_credentials_cache_time is None:
        return False
    return datetime.now(UTC) - _gcp_credentials_cache_time < _gcp_credentials_cache_ttl


async def check_gcp_credentials_valid() -> bool:
    """Check if GCP credentials are valid.

    Returns:
        True if GCP credentials are present and valid.
    """
    global _gcp_credentials_cache, _gcp_credentials_cache_time

    if _is_gcp_cache_valid() and _gcp_credentials_cache is not None:
        return _gcp_credentials_cache

    valid = await _check_gcp_credentials_async()
    _gcp_credentials_cache = valid
    _gcp_credentials_cache_time = datetime.now(UTC)
    return valid


async def _check_gcp_credentials_async() -> bool:
    """Check GCP credentials asynchronously."""
    gcloud_path = None
    for path in ("/usr/bin/gcloud", "/usr/local/bin/gcloud", "gcloud"):
        try:
            proc = await asyncio.create_subprocess_exec(
                path,
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.communicate(), timeout=5.0)
            if proc.returncode == 0:
                gcloud_path = path
                break
        except (TimeoutError, FileNotFoundError, OSError):
            continue

    if gcloud_path is None:
        return False

    try:
        proc = await asyncio.create_subprocess_exec(
            gcloud_path,
            "auth",
            "list",
            "--format=json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, _ = await asyncio.wait_for(
            proc.communicate(), timeout=15.0
        )
        if proc.returncode == 0:
            accounts = json.loads(stdout_bytes.decode("utf-8"))
            return len(accounts) > 0
    except (TimeoutError, FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return False


async def refresh_gcp_credentials_if_needed() -> bool:
    """Refresh GCP credentials if needed.

    Returns:
        True if credentials are valid after refresh.
    """
    return await check_gcp_credentials_valid()


def clear_gcp_credentials_cache() -> None:
    """Clear GCP credentials cache."""
    global _gcp_credentials_cache, _gcp_credentials_cache_time
    _gcp_credentials_cache = None
    _gcp_credentials_cache_time = None
