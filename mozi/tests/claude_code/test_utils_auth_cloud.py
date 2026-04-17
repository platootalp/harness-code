"""Tests for utils/auth_cloud.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from claude_code.utils.auth_cloud import (
    check_gcp_credentials_valid,
    clear_aws_credentials_cache,
    clear_gcp_credentials_cache,
    refresh_and_get_aws_credentials,
    refresh_gcp_credentials_if_needed,
)


class TestClearAwsCredentialsCache:
    """Tests for clear_aws_credentials_cache."""

    def test_clears_without_error(self) -> None:
        clear_aws_credentials_cache()


class TestClearGcpCredentialsCache:
    """Tests for clear_gcp_credentials_cache."""

    def test_clears_without_error(self) -> None:
        clear_gcp_credentials_cache()


class TestRefreshAndGetAwsCredentials:
    """Tests for refresh_and_get_aws_credentials."""

    def test_no_aws_returns_none(self) -> None:
        clear_aws_credentials_cache()
        with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError):
            import asyncio
            result = asyncio.run(refresh_and_get_aws_credentials())
            assert result is None

    def test_invalid_credentials_returns_none(self) -> None:
        clear_aws_credentials_cache()
        with patch("asyncio.create_subprocess_exec") as mock_proc:
            mock = AsyncMock()
            mock.return_value.communicate = AsyncMock(return_value=(b"{}", b""))
            mock.return_value.returncode = 1
            mock_proc.return_value = mock()
            import asyncio
            result = asyncio.run(refresh_and_get_aws_credentials())
            assert result is None


class TestCheckGcpCredentialsValid:
    """Tests for check_gcp_credentials_valid."""

    def test_gcloud_not_found_returns_false(self) -> None:
        clear_gcp_credentials_cache()
        with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError):
            import asyncio
            result = asyncio.run(check_gcp_credentials_valid())
            assert result is False


class TestRefreshGcpCredentialsIfNeeded:
    """Tests for refresh_gcp_credentials_if_needed."""

    def test_delegates_to_check_gcp(self) -> None:
        clear_gcp_credentials_cache()
        with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError):
            import asyncio
            result = asyncio.run(refresh_gcp_credentials_if_needed())
            assert result is False
