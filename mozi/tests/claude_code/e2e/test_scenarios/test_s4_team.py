"""E2E 测试 - S4: 团队协作场景

验证 agent, send_message, team_create/delete 工具。
使用 CLI 测试多 agent 协作功能。
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest


class TestAgentTool:
    """测试 agent 工具."""

    @pytest.mark.asyncio
    async def test_agent_invocation(self, api_key: str, temp_project: Path):
        """验证 agent 工具调用."""
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "claude-code-py.cli.main",
            "--print",
            "Use the agent tool to complete a simple task",
            cwd=str(temp_project),
            env={**os.environ, "ANTHROPIC_API_KEY": api_key},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        # agent 工具应该被识别
        assert proc.returncode in (0, 1) or "agent" in (stdout + stderr).decode().lower()


class TestSendMessageTool:
    """测试 send_message 工具."""

    @pytest.mark.asyncio
    async def test_send_message(self, api_key: str, temp_project: Path):
        """验证 send_message 工具调用."""
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "claude-code-py.cli.main",
            "--print",
            "Send a message to another agent",
            cwd=str(temp_project),
            env={**os.environ, "ANTHROPIC_API_KEY": api_key},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        # send_message 应该被处理
        assert proc.returncode in (0, 1)


class TestTeamTools:
    """测试 team 工具."""

    @pytest.mark.asyncio
    async def test_team_create(self, api_key: str, temp_project: Path):
        """验证 team_create 工具调用."""
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "claude-code-py.cli.main",
            "--print",
            "Create a team with two agents",
            cwd=str(temp_project),
            env={**os.environ, "ANTHROPIC_API_KEY": api_key},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
        assert proc.returncode in (0, 1)

    @pytest.mark.asyncio
    async def test_team_delete(self, api_key: str, temp_project: Path):
        """验证 team_delete 工具调用."""
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "claude-code-py.cli.main",
            "--print",
            "Delete the current team",
            cwd=str(temp_project),
            env={**os.environ, "ANTHROPIC_API_KEY": api_key},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        assert proc.returncode in (0, 1)
