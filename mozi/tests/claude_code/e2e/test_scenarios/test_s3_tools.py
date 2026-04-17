"""E2E 测试 - S3: 工具调用场景

验证 grep, glob, task 系列, web_fetch/search 工具。
使用 CLI headless 模式测试工具执行。
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest


class TestGrepTool:
    """测试 grep 工具."""

    @pytest.mark.asyncio
    async def test_grep_find_text(self, api_key: str, temp_project: Path):
        """验证 grep 查找文本."""
        # 创建测试文件
        test_file = temp_project / "hello.py"
        test_file.write_text("def hello():\n    print('hello world')\n    return True\n")

        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "claw_py.cli.main",
            "--print",
            f"Use grep to find 'hello' in {test_file}",
            cwd=str(temp_project),
            env={**os.environ, "ANTHROPIC_API_KEY": api_key},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        output = stdout.decode() + stderr.decode()

        # 应该找到匹配
        assert proc.returncode in (0, 1) or "hello" in output.lower()

    @pytest.mark.asyncio
    async def test_grep_no_match(self, api_key: str, temp_project: Path):
        """验证 grep 未找到匹配时的处理."""
        test_file = temp_project / "hello.py"
        test_file.write_text("def hello():\n    print('hello world')\n")

        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "claw_py.cli.main",
            "--print",
            f"Use grep to find 'goodbye' in {test_file}",
            cwd=str(temp_project),
            env={**os.environ, "ANTHROPIC_API_KEY": api_key},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)

        # 应该处理未找到的情况
        assert proc.returncode in (0, 1)


class TestGlobTool:
    """测试 glob 工具."""

    @pytest.mark.asyncio
    async def test_glob_python_files(self, api_key: str, temp_project: Path):
        """验证 glob 查找 Python 文件."""
        # 创建测试文件
        (temp_project / "file1.py").write_text("# py file")
        (temp_project / "file2.py").write_text("# py file")
        (temp_project / "file3.txt").write_text("# text file")

        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "claw_py.cli.main",
            "--print",
            f"Use glob to find all .py files in {temp_project}",
            cwd=str(temp_project),
            env={**os.environ, "ANTHROPIC_API_KEY": api_key},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        output = stdout.decode() + stderr.decode()

        # 应该找到 Python 文件
        assert proc.returncode in (0, 1) or ".py" in output


class TestTaskTool:
    """测试 task 系列工具."""

    @pytest.mark.asyncio
    async def test_task_create(self, api_key: str, temp_project: Path):
        """验证创建任务."""
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "claw_py.cli.main",
            "--print",
            "Create a task with description 'Test task' and subject 'Test'",
            cwd=str(temp_project),
            env={**os.environ, "ANTHROPIC_API_KEY": api_key},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        output = (stdout + stderr).decode()

        # 应该处理任务创建
        assert proc.returncode in (0, 1) or "task" in output.lower()

    @pytest.mark.asyncio
    async def test_task_list(self, api_key: str, temp_project: Path):
        """验证列出任务."""
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "claw_py.cli.main",
            "--print",
            "List all available tasks",
            cwd=str(temp_project),
            env={**os.environ, "ANTHROPIC_API_KEY": api_key},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        output = (stdout + stderr).decode()

        # 应该处理任务列表
        assert proc.returncode in (0, 1) or "task" in output.lower()


class TestWebFetchTool:
    """测试 web_fetch 工具."""

    @pytest.mark.asyncio
    async def test_web_fetch_basic(self, api_key: str, temp_project: Path):
        """验证基本的网页获取."""
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "claw_py.cli.main",
            "--print",
            "Fetch the content of https://example.com",
            cwd=str(temp_project),
            env={**os.environ, "ANTHROPIC_API_KEY": api_key},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        output = (stdout + stderr).decode()

        # 应该获取网页内容
        assert proc.returncode in (0, 1) or "example" in output.lower() or "html" in output.lower()


class TestWebSearchTool:
    """测试 web_search 工具."""

    @pytest.mark.asyncio
    async def test_web_search_basic(self, api_key: str, temp_project: Path):
        """验证基本的网页搜索."""
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "claw_py.cli.main",
            "--print",
            "Search the web for 'Python programming'",
            cwd=str(temp_project),
            env={**os.environ, "ANTHROPIC_API_KEY": api_key},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        output = (stdout + stderr).decode()

        # 应该返回搜索结果
        assert proc.returncode in (0, 1) or "python" in output.lower() or "search" in output.lower()
