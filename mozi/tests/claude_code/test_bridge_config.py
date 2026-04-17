"""
Tests for bridge/config.py - Bridge configuration and auth utilities.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from claude_code.bridge.config import (
    BRIDGE_LOGIN_INSTRUCTION,
    BridgeConfig,
    SpawnMode,
    WorkerType,
    get_bridge_access_token,
    get_bridge_base_url,
    get_bridge_base_url_override,
    get_bridge_token_override,
)


class TestBridgeConfig:
    """Tests for BridgeConfig dataclass."""

    def test_create_minimal(self) -> None:
        """BridgeConfig should create with required fields."""
        config = BridgeConfig(
            dir="/home/user/project",
            machine_name="macbook-pro",
            branch="main",
            git_repo_url=None,
            max_sessions=1,
            spawn_mode=SpawnMode.SINGLE_SESSION,
            verbose=False,
            sandbox=False,
            bridge_id="bridge-123",
            worker_type="claw_py",
            environment_id="env-456",
            api_base_url="https://api.claude.ai",
            session_ingress_url="https://api.claude.ai",
        )
        assert config.dir == "/home/user/project"
        assert config.machine_name == "macbook-pro"
        assert config.branch == "main"
        assert config.git_repo_url is None
        assert config.max_sessions == 1
        assert config.spawn_mode == SpawnMode.SINGLE_SESSION
        assert config.verbose is False
        assert config.sandbox is False
        assert config.bridge_id == "bridge-123"
        assert config.worker_type == "claw_py"
        assert config.environment_id == "env-456"
        assert config.api_base_url == "https://api.claude.ai"
        assert config.session_ingress_url == "https://api.claude.ai"

    def test_create_with_optional_fields(self) -> None:
        """BridgeConfig should accept optional fields."""
        config = BridgeConfig(
            dir="/home/user/project",
            machine_name="macbook-pro",
            branch="main",
            git_repo_url="https://github.com/user/repo",
            max_sessions=4,
            spawn_mode=SpawnMode.WORKTREE,
            verbose=True,
            sandbox=True,
            bridge_id="bridge-123",
            worker_type="claude_code_assistant",
            environment_id="env-456",
            api_base_url="https://api.claude.ai",
            session_ingress_url="https://api.claude.ai",
            reuse_environment_id="reuse-789",
            debug_file="/tmp/bridge-debug.log",
            session_timeout_ms=300000,
        )
        assert config.reuse_environment_id == "reuse-789"
        assert config.debug_file == "/tmp/bridge-debug.log"
        assert config.session_timeout_ms == 300000

    def test_worker_type_enum_values(self) -> None:
        """WorkerType enum should have expected values."""
        assert WorkerType.CLAUDE_CODE.value == "claw_py"
        assert WorkerType.CLAUDE_CODE_ASSISTANT.value == "claude_code_assistant"

    def test_spawn_mode_enum_values(self) -> None:
        """SpawnMode enum should have expected values."""
        assert SpawnMode.SINGLE_SESSION.value == "single-session"
        assert SpawnMode.WORKTREE.value == "worktree"
        assert SpawnMode.SAME_DIR.value == "same-dir"


class TestDevOverrides:
    """Tests for dev override getters (ANT-only)."""

    def test_token_override_not_ant(self) -> None:
        """get_bridge_token_override should return None when USER_TYPE is not ant."""
        with patch.dict(os.environ, {"USER_TYPE": ""}):
            result = get_bridge_token_override()
            assert result is None

    def test_token_override_not_set(self) -> None:
        """get_bridge_token_override should return None when env var not set (even with ant)."""
        with patch.dict(os.environ, {"USER_TYPE": "ant"}):
            result = get_bridge_token_override()
            assert result is None

    def test_token_override_ant_with_token(self) -> None:
        """get_bridge_token_override should return token when USER_TYPE=ant."""
        with patch.dict(os.environ, {
            "USER_TYPE": "ant",
            "CLAUDE_BRIDGE_OAUTH_TOKEN": "ant-dev-token",
        }):
            result = get_bridge_token_override()
            assert result == "ant-dev-token"

    def test_base_url_override_not_ant(self) -> None:
        """get_bridge_base_url_override should return None when USER_TYPE is not ant."""
        with patch.dict(os.environ, {"USER_TYPE": ""}):
            result = get_bridge_base_url_override()
            assert result is None

    def test_base_url_override_not_set(self) -> None:
        """get_bridge_base_url_override should return None when env var not set."""
        with patch.dict(os.environ, {"USER_TYPE": "ant"}):
            result = get_bridge_base_url_override()
            assert result is None

    def test_base_url_override_ant_with_url(self) -> None:
        """get_bridge_base_url_override should return URL when USER_TYPE=ant."""
        with patch.dict(os.environ, {
            "USER_TYPE": "ant",
            "CLAUDE_BRIDGE_BASE_URL": "https://custom.api.com",
        }):
            result = get_bridge_base_url_override()
            assert result == "https://custom.api.com"


class TestPublicGetters:
    """Tests for public getter functions."""

    def test_get_bridge_access_token_override_wins(self) -> None:
        """Override token should take precedence over OAuth tokens."""
        with patch.dict(os.environ, {
            "USER_TYPE": "ant",
            "CLAUDE_BRIDGE_OAUTH_TOKEN": "override-token",
        }):
            result = get_bridge_access_token()
            assert result == "override-token"

    def test_get_bridge_access_token_no_oauth(self) -> None:
        """Should return None when no tokens are available."""
        with patch.dict(os.environ, {"USER_TYPE": ""}, clear=True):
            result = get_bridge_access_token()
            assert result is None

    def test_get_bridge_base_url_override_wins(self) -> None:
        """Override URL should take precedence over OAuth config."""
        with patch.dict(os.environ, {
            "USER_TYPE": "ant",
            "CLAUDE_BRIDGE_BASE_URL": "https://custom.api.com",
        }):
            result = get_bridge_base_url()
            assert result == "https://custom.api.com"

    def test_get_bridge_base_url_default(self) -> None:
        """Should return production default when no overrides."""
        with patch.dict(os.environ, {"USER_TYPE": ""}):
            result = get_bridge_base_url()
            assert result == "https://api.claude.ai"


class TestBridgeLoginInstruction:
    """Tests for BRIDGE_LOGIN_INSTRUCTION constant."""

    def test_is_defined(self) -> None:
        """BRIDGE_LOGIN_INSTRUCTION should be defined."""
        assert BRIDGE_LOGIN_INSTRUCTION is not None
        assert len(BRIDGE_LOGIN_INSTRUCTION) > 0

    def test_mentions_auth_login(self) -> None:
        """BRIDGE_LOGIN_INSTRUCTION should mention auth login."""
        assert "auth login" in BRIDGE_LOGIN_INSTRUCTION or "sign in" in BRIDGE_LOGIN_INSTRUCTION

    def test_mentions_claude_ai(self) -> None:
        """BRIDGE_LOGIN_INSTRUCTION should mention claude.ai."""
        assert "claude.ai" in BRIDGE_LOGIN_INSTRUCTION
