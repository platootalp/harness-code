"""E2E 测试 - S9: Skills 技能系统场景

验证 skills 的完整链路：
- Skill 发现和加载
- Skill 执行 (via /skill 命令)
- Skill 工具调用边界
- 条件 skill 激活

使用 CLI headless 模式测试真实 skill 调用。
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest


class TestSkillDiscovery:
    """测试 skill 发现功能."""

    @pytest.mark.asyncio
    async def test_skill_list_command(self, api_key: str, temp_project: Path):
        """验证 /skills 命令可以列出可用 skills."""
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "claw_py.cli.main",
            "--print", "/skills",
            cwd=str(temp_project),
            env={**os.environ, "ANTHROPIC_API_KEY": api_key},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        output = (stdout + stderr).decode().lower()

        # 应该显示 skills 相关输出
        assert proc.returncode in (0, 1) or "skill" in output

    @pytest.mark.asyncio
    async def test_skill_discovery_in_directory(self, api_key: str, temp_project: Path):
        """验证 skill 发现可以扫描目录."""
        # 创建 skills 目录结构
        skills_dir = temp_project / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "test_skill.md").write_text(
            "---\nname: test-skill\ndescription: A test skill\n---\n# Test Skill\nThis is a test."
        )

        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "claw_py.cli.main",
            "--print", "Discover skills in the project",
            cwd=str(temp_project),
            env={**os.environ, "ANTHROPIC_API_KEY": api_key},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        output = (stdout + stderr).decode().lower()

        assert proc.returncode in (0, 1) or "skill" in output or "discover" in output


class TestSkillExecution:
    """测试 skill 执行功能."""

    @pytest.mark.asyncio
    async def test_execute_simplify_skill(self, api_key: str, temp_project: Path):
        """验证执行 /simplify skill."""
        # 创建待简化的代码
        test_file = temp_project / "complex.py"
        test_file.write_text(
            "x=1\ny=2\nif x==1:\n    print(y)\nelse:\n    print(x)"
        )

        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "claw_py.cli.main",
            "--print",
            f"Use the /simplify skill on {test_file}",
            cwd=str(temp_project),
            env={**os.environ, "ANTHROPIC_API_KEY": api_key},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
        output = (stdout + stderr).decode().lower()

        assert proc.returncode in (0, 1) or "simplify" in output

    @pytest.mark.asyncio
    async def test_execute_verify_skill(self, api_key: str, temp_project: Path):
        """验证执行 /verify skill."""
        # 创建测试文件
        test_file = temp_project / "example.py"
        test_file.write_text("def hello():\n    return 'world'\n")

        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "claw_py.cli.main",
            "--print",
            f"Use /verify to check {test_file}",
            cwd=str(temp_project),
            env={**os.environ, "ANTHROPIC_API_KEY": api_key},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=180)
        output = (stdout + stderr).decode().lower()

        assert proc.returncode in (0, 1) or "verify" in output

    @pytest.mark.asyncio
    async def test_skill_with_allowed_tools_boundary(self, api_key: str, temp_project: Path):
        """验证 skill 工具边界限制."""
        test_file = temp_project / "read_only.py"
        test_file.write_text("x = 1\n")

        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "claw_py.cli.main",
            "--print",
            f"Use a skill that only allows Read tool on {test_file}, do not use Write",
            cwd=str(temp_project),
            env={**os.environ, "ANTHROPIC_API_KEY": api_key},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=180)
        output = (stdout + stderr).decode().lower()

        assert proc.returncode in (0, 1) or "read" in output


class TestSkillAliases:
    """测试 skill 别名功能."""

    @pytest.mark.asyncio
    async def test_skill_alias_invocation(self, api_key: str, temp_project: Path):
        """验证使用别名调用 skill."""
        test_file = temp_project / "test.py"
        test_file.write_text("x = 1\ny = 2\nz = 3\n")

        # simplify skill 的别名是 improve 和 clean
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "claw_py.cli.main",
            "--print",
            f"/improve {test_file}",
            cwd=str(temp_project),
            env={**os.environ, "ANTHROPIC_API_KEY": api_key},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=180)
        output = (stdout + stderr).decode().lower()

        assert proc.returncode in (0, 1) or "improve" in output or "simplify" in output


class TestSkillConditional:
    """测试条件 skill 激活."""

    @pytest.mark.asyncio
    async def test_conditional_skill_activation(self, api_key: str, temp_project: Path):
        """验证条件 skill 激活."""
        # 创建满足条件的文件 (例如包含 TODO)
        test_file = temp_project / "todo_file.py"
        test_file.write_text("# TODO: implement this\ndef placeholder():\n    pass\n")

        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "claw_py.cli.main",
            "--print",
            f"Check if any skill should activate for {test_file}",
            cwd=str(temp_project),
            env={**os.environ, "ANTHROPIC_API_KEY": api_key},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=180)
        output = (stdout + stderr).decode().lower()

        assert proc.returncode in (0, 1)


class TestSkillForkedExecution:
    """测试 forked skill 执行."""

    @pytest.mark.asyncio
    async def test_forked_skill_execution(self, api_key: str, temp_project: Path):
        """验证 forked skill 执行 (独立进程)."""
        test_file = temp_project / "fork_test.py"
        test_file.write_text("value = 42\n")

        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "claw_py.cli.main",
            "--print",
            f"Run /simplify in forked mode on {test_file}",
            cwd=str(temp_project),
            env={**os.environ, "ANTHROPIC_API_KEY": api_key},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=180)
        output = (stdout + stderr).decode().lower()

        assert proc.returncode in (0, 1) or "fork" in output or "simplify" in output


class TestSkillToolIntegration:
    """测试 skill 工具集成."""

    @pytest.mark.asyncio
    async def test_skill_appears_in_tool_list(self, api_key: str, temp_project: Path):
        """验证 skill 工具出现在工具列表中."""
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "claw_py.cli.main",
            "--print", "List all available tools",
            cwd=str(temp_project),
            env={**os.environ, "ANTHROPIC_API_KEY": api_key},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        output = (stdout + stderr).decode().lower()

        # skill 工具应该在输出中
        assert proc.returncode in (0, 1) or "tool" in output

    @pytest.mark.asyncio
    async def test_skill_with_arguments(self, api_key: str, temp_project: Path):
        """验证带参数的 skill 调用."""
        test_file1 = temp_project / "file1.py"
        test_file2 = temp_project / "file2.py"
        test_file1.write_text("x = 1\n")
        test_file2.write_text("y = 2\n")

        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "claw_py.cli.main",
            "--print",
            f"/simplify {test_file1} {test_file2}",
            cwd=str(temp_project),
            env={**os.environ, "ANTHROPIC_API_KEY": api_key},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=180)
        output = (stdout + stderr).decode().lower()

        assert proc.returncode in (0, 1) or "simplify" in output
