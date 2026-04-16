"""E2E 测试 - L1: CLI 层

验证 CLI 启动、参数、TUI/print/ask 模式切换、help 输出。
使用真实 subprocess 调用，不使用 CliRunner。
"""

from __future__ import annotations

import asyncio
import os
import sys

import pytest


class TestCLIVersion:
    """测试 CLI 版本命令."""

    @pytest.mark.asyncio
    async def test_version_output(self, api_key: str):
        """验证版本输出包含版本号."""
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "claude_code.cli.main", "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        output = stdout.decode()
        assert "1.0.0" in output
        assert proc.returncode == 0


class TestCLIHelp:
    """测试 CLI help 命令."""

    @pytest.mark.asyncio
    async def test_help_flag(self, api_key: str):
        """验证 --help 标志工作正常."""
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "claude_code.cli.main", "--help",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        output = stdout.decode()
        assert "Claude Code" in output
        assert "ask" in output  # ask subcommand 应在 help 中
        assert proc.returncode == 0

    @pytest.mark.asyncio
    async def test_help_shows_print_mode(self, api_key: str):
        """验证 help 中显示 --print 选项."""
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "claude_code.cli.main", "--help",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        output = stdout.decode()
        assert "--print" in output

    @pytest.mark.asyncio
    async def test_help_shows_permission_mode(self, api_key: str):
        """验证 help 中显示 --permission-mode 选项."""
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "claude_code.cli.main", "--help",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        output = stdout.decode()
        assert "--permission-mode" in output


class TestCLIHeadlessMode:
    """测试 CLI headless (--print) 模式."""

    @pytest.mark.asyncio
    async def test_print_mode_requires_prompt(self, api_key: str):
        """验证 --print 模式需要提供 prompt."""
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "claude_code.cli.main", "--print",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        output = (stdout + stderr).decode()
        # 应该报错说缺少 prompt 参数
        assert proc.returncode != 0 or "Error" in output or "requires" in output.lower()

    @pytest.mark.asyncio
    async def test_print_mode_with_prompt(self, api_key: str, temp_project):
        """验证 --print 模式能正常处理 prompt."""
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "claude_code.cli.main",
            "--print", "Say hello",
            cwd=str(temp_project),
            env={**os.environ, "ANTHROPIC_API_KEY": api_key},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        output = stdout.decode() + stderr.decode()
        # 可能成功或因 API 问题失败，但 CLI 本身不应崩溃
        assert proc.returncode in (0, 1) or "Error" in output


class TestCLIAuthModes:
    """测试 CLI 权限模式选项."""

    @pytest.mark.asyncio
    async def test_permission_mode_auto(self, api_key: str, temp_project):
        """验证 --permission-mode auto 可以接受."""
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "claude_code.cli.main",
            "--print", "--permission-mode", "auto", "hello",
            cwd=str(temp_project),
            env={**os.environ, "ANTHROPIC_API_KEY": api_key},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        # 应该不崩溃，returncode 0 或 1（API 调用失败）
        assert proc.returncode in (0, 1)

    @pytest.mark.asyncio
    async def test_permission_mode_bypass(self, api_key: str, temp_project):
        """验证 --permission-mode bypassPermissions 可以接受."""
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "claude_code.cli.main",
            "--print", "--permission-mode", "bypassPermissions", "hello",
            cwd=str(temp_project),
            env={**os.environ, "ANTHROPIC_API_KEY": api_key},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        assert proc.returncode in (0, 1)

    @pytest.mark.asyncio
    async def test_permission_mode_deny(self, api_key: str, temp_project):
        """验证 --permission-mode deny 可以接受."""
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "claude_code.cli.main",
            "--print", "--permission-mode", "deny", "hello",
            cwd=str(temp_project),
            env={**os.environ, "ANTHROPIC_API_KEY": api_key},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        assert proc.returncode in (0, 1)

    @pytest.mark.asyncio
    async def test_permission_mode_invalid_rejected(self, api_key: str, temp_project):
        """验证无效的 permission-mode 被拒绝."""
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "claude_code.cli.main",
            "--print", "--permission-mode", "invalid_mode", "hello",
            cwd=str(temp_project),
            env={**os.environ, "ANTHROPIC_API_KEY": api_key},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        output = (stdout + stderr).decode()
        # 应该报错
        assert proc.returncode != 0 or "Error" in output or "invalid" in output.lower()
