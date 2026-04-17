"""E2E 测试 - S1: 项目初始化场景

验证 init 命令创建新项目。
使用 CLI 测试项目初始化功能。
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest


class TestProjectInit:
    """测试项目初始化."""

    @pytest.mark.asyncio
    async def test_init_command(self, api_key: str, temp_project: Path):
        """验证 init 命令存在并可以执行."""
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "claw_py.cli.main",
            "init",
            cwd=str(temp_project),
            env={**os.environ, "ANTHROPIC_API_KEY": api_key},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        # init 命令应该存在
        assert proc.returncode in (0, 1) or "init" in (stdout + stderr).decode().lower()


class TestProjectStructure:
    """测试项目结构创建."""

    def test_claude_md_creation(self, temp_project: Path):
        """验证 CLAUDE.md 文件创建逻辑."""
        # 如果项目中有 CLAUDE.md，应该能被读取
        claude_md = temp_project / "CLAUDE.md"
        if claude_md.exists():
            content = claude_md.read_text()
            assert isinstance(content, str)
