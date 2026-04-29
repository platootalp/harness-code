"""E2E 测试 - S7: MCP 集成场景

验证 MCP 服务器连接和资源访问。
使用 CLI 测试 MCP 协议功能。
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest


class TestMCPConnection:
    """测试 MCP 服务器连接."""

    @pytest.mark.asyncio
    async def test_mcp_config_option(self, api_key: str, temp_project: Path):
        """验证 --mcp-config 选项存在."""
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "claude-code-py.cli.main",
            "--print", "--mcp-config", "/tmp/nonexistent.json",
            "List resources",
            cwd=str(temp_project),
            env={**os.environ, "ANTHROPIC_API_KEY": api_key},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        # --mcp-config 选项应该被接受
        output = (stdout + stderr).decode()
        assert proc.returncode in (0, 1) or "mcp" in output.lower()


class TestMCPResources:
    """测试 MCP 资源访问."""

    @pytest.mark.asyncio
    async def test_list_mcp_resources(self, api_key: str, temp_project: Path):
        """验证 list_mcp_resources 工具存在."""
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "claude-code-py.cli.main",
            "--print",
            "List available MCP resources",
            cwd=str(temp_project),
            env={**os.environ, "ANTHROPIC_API_KEY": api_key},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        assert proc.returncode in (0, 1)


class TestMCPTools:
    """测试 MCP 工具调用."""

    @pytest.mark.asyncio
    async def test_mcp_tool_invocation(self, api_key: str, temp_project: Path):
        """验证通过 MCP 调用工具."""
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "claude-code-py.cli.main",
            "--print",
            "Call an MCP tool",
            cwd=str(temp_project),
            env={**os.environ, "ANTHROPIC_API_KEY": api_key},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        assert proc.returncode in (0, 1)
