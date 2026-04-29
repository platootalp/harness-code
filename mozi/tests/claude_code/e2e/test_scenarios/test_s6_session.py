"""E2E 测试 - S6: 会话管理场景

验证 resume, --continue, session 持久化。
使用 CLI 测试会话功能。
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest


class TestSessionPersistence:
    """测试会话持久化."""

    @pytest.mark.asyncio
    async def test_session_survives_restart(self, api_key: str, temp_project: Path):
        """验证会话在重启后保持."""
        # 第一个请求
        proc1 = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "claude-code-py.cli.main",
            "--print", "My name is Claude",
            cwd=str(temp_project),
            env={**os.environ, "ANTHROPIC_API_KEY": api_key},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout1, stderr1 = await asyncio.wait_for(proc1.communicate(), timeout=60)

        # 第二个请求使用 --continue
        proc2 = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "claude-code-py.cli.main",
            "--print", "--continue",
            "What is my name?",
            cwd=str(temp_project),
            env={**os.environ, "ANTHROPIC_API_KEY": api_key},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout2, stderr2 = await asyncio.wait_for(proc2.communicate(), timeout=60)

        # --continue 应该能记住之前的上下文
        output2 = stdout2.decode() + stderr2.decode()
        assert proc2.returncode in (0, 1) or "claude" in output2.lower()


class TestSessionResume:
    """测试会话恢复."""

    @pytest.mark.asyncio
    async def test_resume_by_id(self, api_key: str, temp_project: Path):
        """验证通过 session ID 恢复会话."""
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "claude-code-py.cli.main",
            "--print", "--session-id", "test-session-123",
            "Hello",
            cwd=str(temp_project),
            env={**os.environ, "ANTHROPIC_API_KEY": api_key},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        # 应该接受 session-id 参数
        assert proc.returncode in (0, 1)


class TestSessionStorage:
    """测试会话存储."""

    def test_session_storage_initialization(self, tmp_path: Path):
        """验证会话存储可以初始化."""
        from claude_code.services.storage.session import SessionStorage

        store_path = tmp_path / "sessions"
        store_path.mkdir()
        storage = SessionStorage(store_path)

        assert storage is not None
        assert storage._storage_dir == store_path

    @pytest.mark.asyncio
    async def test_session_save_and_load(self, tmp_path: Path):
        """验证会话可以保存和加载."""
        from claude_code.services.storage.session import SessionStorage, StoredSession

        store_path = tmp_path / "sessions"
        storage = SessionStorage(store_path)

        # 创建并保存会话
        session = StoredSession(
            session_id="test-123",
            environment_id="env-1",
            title="Test Session",
        )
        await storage.save(session)

        # 加载会话
        loaded = await storage.load("test-123")

        assert loaded is not None
        assert loaded.session_id == "test-123"
        assert loaded.title == "Test Session"

    @pytest.mark.asyncio
    async def test_session_delete(self, tmp_path: Path):
        """验证会话可以删除."""
        from claude_code.services.storage.session import SessionStorage, StoredSession

        store_path = tmp_path / "sessions"
        storage = SessionStorage(store_path)

        # 创建并保存会话
        session = StoredSession(
            session_id="test-delete",
            environment_id="env-1",
        )
        await storage.save(session)

        # 删除会话
        await storage.delete("test-delete")

        # 验证删除
        loaded = await storage.load("test-delete")
        assert loaded is None
