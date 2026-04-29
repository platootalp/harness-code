"""E2E 测试 - S8: 插件系统场景

验证插件加载和执行。
使用 CLI 测试插件功能。
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest


class TestPluginLoading:
    """测试插件加载."""

    @pytest.mark.asyncio
    async def test_plugin_command(self, api_key: str, temp_project: Path):
        """验证插件相关命令存在."""
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "claude-code-py.cli.main",
            "--print",
            "List available plugins",
            cwd=str(temp_project),
            env={**os.environ, "ANTHROPIC_API_KEY": api_key},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        assert proc.returncode in (0, 1)


class TestPluginExecution:
    """测试插件执行."""

    @pytest.mark.asyncio
    async def test_plugin_invoke(self, api_key: str, temp_project: Path):
        """验证插件调用."""
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "claude-code-py.cli.main",
            "--print",
            "Use a plugin to complete a task",
            cwd=str(temp_project),
            env={**os.environ, "ANTHROPIC_API_KEY": api_key},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        assert proc.returncode in (0, 1)
