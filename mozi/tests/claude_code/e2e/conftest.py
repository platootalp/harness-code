"""E2E 测试配置和 fixtures.

设计文档: docs/superpowers/specs/2026-04-08-src-e2e-acceptance-design.md
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio

# API 超时配置
API_TIMEOUT = 120  # 秒
API_MAX_RETRIES = 3


def _load_settings() -> dict:
    """从 ~/.claude/settings.json 加载配置."""
    settings_path = Path.home() / ".claude" / "settings.json"
    if settings_path.exists():
        with open(settings_path) as f:
            return json.load(f)
    return {}


@pytest.fixture(scope="session")
def api_key() -> str:
    """获取 API key，从 settings.json 或环境变量读取，永不跳过."""
    settings = _load_settings()
    env = settings.get("env", {})
    # 优先使用 settings.json 中的 ANTHROPIC_AUTH_TOKEN
    key = env.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        pytest.skip("ANTHROPIC_API_KEY not set")
    return key


@pytest.fixture(scope="session")
def base_url() -> str:
    """获取 base URL，从 settings.json 或环境变量读取."""
    settings = _load_settings()
    env = settings.get("env", {})
    return env.get("ANTHROPIC_BASE_URL") or os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")


@pytest.fixture
def temp_project(tmp_path: Path):
    """创建临时项目目录，自动清理."""
    project = tmp_path / "test_project"
    project.mkdir()
    # 创建基础 git 仓库
    (project / ".git").mkdir()
    yield project


@pytest_asyncio.fixture
async def cli_process(
    temp_project: Path, api_key: str, base_url: str
) -> AsyncGenerator[asyncio.subprocess.Process, None]:
    """启动 CLI 进程，带自动清理."""
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "claude-code-py.cli.main",
        "--print", "hello",
        cwd=str(temp_project),
        env={**os.environ, "ANTHROPIC_API_KEY": api_key, "ANTHROPIC_BASE_URL": base_url},
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    yield proc
    # Teardown: 确保进程已终止
    if proc.returncode is None:
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except TimeoutError:
            proc.kill()
            await proc.wait()


@pytest.fixture
def session_store(tmp_path: Path):
    """创建临时 session store."""
    from claude_code.services.storage.session import SessionStorage
    store_path = tmp_path / "sessions"
    store_path.mkdir()
    store = SessionStorage(store_path)
    yield store


@pytest_asyncio.fixture
async def http_mock_server():
    """启动 mock HTTP server 用于 MCP/Bridge 测试.

    TODO: 使用 pytest-httpserver 实现
    - MCP 测试: 模拟 MCP server 的 SSE endpoint
    - Bridge 测试: 模拟 IDE 插件的 JSON-RPC endpoint
    """
    pytest.skip("http_mock_server fixture not yet implemented")
