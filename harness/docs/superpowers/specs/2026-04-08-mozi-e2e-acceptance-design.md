# Mozi E2E 验收方案设计

## 概述

Mozi E2E 验收测试套件，通过真实 Claude API 调用，验证从 CLI 到引擎的完整链路。

## 测试环境

- **API**: 真实 Claude API (通过 `ANTHROPIC_API_KEY` 环境变量)
- **Python**: 3.11+ (mozi `.venv`)
- **测试框架**: pytest + pytest-asyncio (mode=auto)
- **执行方式**: 独立 `e2e.sh` 脚本，支持本地和 CI 运行

### API 配置

```python
# API 超时和重试配置 (在 conftest.py 或环境变量中)
API_TIMEOUT = 120  # 秒
API_MAX_RETRIES = 3
API_RETRY_DELAY = 5  # 秒

# 速率限制处理
- 429 响应: 等待 Retry-After header 或指数退避
- 5xx 错误: 自动重试最多 API_MAX_RETRIES 次
- Quota 耗尽: 测试 skip 并报告
```

### pytest-asyncio 配置

```toml
# pyproject.toml 新增
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
```

## 验收矩阵：场景 × 层次

### 场景维度 (Scenario)

| # | 场景 | 描述 | 关键验证点 |
|---|------|------|-----------|
| S1 | 项目初始化 | `init` 命令创建新项目 | 目录结构、配置文件、git init |
| S2 | 代码开发 | 读/写/编辑文件，执行 bash | file_read/write/edit, bash 工具 |
| S3 | 工具调用 | grep, glob, task, web_fetch/search | 工具 schema、并行执行、结果解析 |
| S4 | 团队协作 | agent, send_message, team_create/delete | 多 agent 通信、任务分配 |
| S5 | 安全管控 | permissions, budgets, rules 边界 | read-only 限制、危险命令拒绝、budget 限额 |
| S6 | 会话管理 | resume, --continue, session 持久化 | 会话恢复、context 保持 |
| S7 | MCP 集成 | MCP 服务器连接和资源访问 | MCP 协议、resource 读写、tool 调用 |
| S8 | 插件系统 | 插件加载和执行 | 插件发现、生命周期、错误隔离 |

### 层次维度 (Layer)

| # | 层次 | 验证点 |
|---|------|--------|
| L1 | **CLI 层** | 启动参数、TUI/print/ask 模式切换、help |
| L2 | **命令层** | slash commands 注册和执行 |
| L3 | **工具层** | 工具 schema、权限、执行结果 |
| L4 | **引擎层** | QueryEngine、pipeline、tool orchestration |
| L5 | **API 层** | chat_complete 流式响应、错误处理 |
| L6 | **存储层** | session 持久化、context 压缩 |
| L7 | **安全层** | rules 评估、permissions 拒绝、budgets 限制 |
| L8 | **Bridge 层** | IDE 协议通信 (支持 VS Code, JetBrains) |
| L9 | **Hooks 层** | lifecycle hooks 触发 |

### L8 Bridge 层说明

Bridge 层使用基于 JSON-RPC 的 IDE 协议：
- **协议文件**: `src/claude_code/bridge/protocol.py`
- **测试方式**: 使用 `pytest-httpserver` 模拟 IDE 插件端点
- **测试内容**: 协议消息序列化/反序列化、session 关联、tool 结果回传

## E2E 测试结构

```
mozi/
  script/
    e2e.sh                    # 统一入口
  tests/e2e/
    conftest.py               # pytest fixtures
    conftest_report.py        # 自定义报告 hook
    test_scenarios/           # 场景测试
      test_s1_init.py
      test_s2_code_dev.py
      test_s3_tools.py
      test_s4_team.py
      test_s5_security_permissions.py
      test_s5_security_budgets.py
      test_s5_security_rules.py
      test_s6_session.py
      test_s7_mcp.py
      test_s8_plugins.py
    test_layers/              # 层次测试
      test_l1_cli.py
      test_l2_commands.py
      test_l3_tools.py
      test_l4_engine.py
      test_l5_api.py
      test_l6_storage.py
      test_l7_security.py
      test_l8_bridge.py
      test_l9_hooks.py
```

## 关键 Fixtures

```python
# conftest.py

import asyncio
import os
import shutil
from pathlib import Path
from typing import AsyncGenerator

import pytest
import pytest_asyncio

@pytest.fixture(scope="session")
def api_key():
    """获取 API key，skip 如果不存在"""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        pytest.skip("ANTHROPIC_API_KEY not set")
    return key

@pytest.fixture
def temp_project(tmp_path: Path) -> Path:
    """创建临时项目目录，自动清理"""
    project = tmp_path / "test_project"
    project.mkdir()
    # 创建基础 git 仓库
    (project / ".git").mkdir()
    yield project
    # tmp_path 自动清理，但确保进程已结束

@pytest_asyncio.fixture
async def cli_process(
    temp_project: Path, api_key: str
) -> AsyncGenerator[asyncio.subprocess.Process, None]:
    """启动 CLI 进程，带自动清理"""
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "claude-code-py.cli.main",
        "--print", "hello",
        cwd=temp_project,
        env={**os.environ, "ANTHROPIC_API_KEY": api_key},
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    yield proc
    # Teardown: 确保进程已终止
    if proc.returncode is None:
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()

@pytest.fixture
def session_store(tmp_path: Path):
    """创建临时 session store"""
    from claude_code.services.storage.session import SessionStorage
    store_path = tmp_path / "sessions"
    store_path.mkdir()
    store = SessionStorage(store_path)
    yield store
    # Cleanup via tmp_path automatic

@pytest_asyncio.fixture
async def http_mock_server():
    """启动 mock HTTP server 用于 MCP/Bridge 测试

    TODO: 使用 pytest-httpserver 实现
    - MCP 测试: 模拟 MCP server 的 SSE endpoint
    - Bridge 测试: 模拟 IDE 插件的 JSON-RPC endpoint
    示例:
        from pytest_httpserver import HTTPServer

        server = HTTPServer()
        server.start()
        yield f"http://{server.host}:{server.port}"
        server.stop()
    """
    pytest.skip("http_mock_server fixture not yet implemented")
```

### 异步测试模式

```python
# 使用 pytest-asyncio mode=auto，所有 async def 自动识别
async def test_streaming_response(api_key):
    """测试流式响应处理"""
    async with asyncio.timeout(API_TIMEOUT):
        async for event in engine.submit_message(prompt="hello", messages=[]):
            if isinstance(event, MessageStopEvent):
                break

```

## E2E Shell 脚本

```bash
#!/bin/bash
# script/e2e.sh
# 用法: ./e2e.sh [范围] [选项]
# 范围: all | scenarios | layers | <场景名> | <层次名>

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
MOZI_DIR="$PROJECT_DIR"
cd "$MOZI_DIR"

SCOPE="${1:-all}"
REPORT_FORMAT="${2:-text}"  # text | json

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

# 检查 API key
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo -e "${RED}Error: ANTHROPIC_API_KEY not set${NC}"
    exit 1
fi

# 激活虚拟环境
if [ -f "$MOZI_DIR/.venv/bin/activate" ]; then
    source "$MOZI_DIR/.venv/bin/activate"
else
    echo -e "${RED}Error: 虚拟环境不存在${NC}"
    echo -e "${YELLOW}请先运行: ./script/setup.sh${NC}"
    exit 1
fi

export PYTHONPATH="$MOZI_DIR/src"

# 运行测试
run_pytest() {
    local target="$1"
    local extra_args="${2:-}"

    if [ "$REPORT_FORMAT" = "json" ]; then
        pytest "$target" -v --json-report --json-report-file="e2e-report.json" $extra_args
    else
        pytest "$target" -v $extra_args
    fi
}

case "$SCOPE" in
    all)
        run_pytest "tests/e2e/"
        ;;
    scenarios)
        run_pytest "tests/e2e/test_scenarios/"
        ;;
    layers)
        run_pytest "tests/e2e/test_layers/"
        ;;
    *)
        # 区分场景和层次: l[0-9] 开头的是层次
        if [[ "$SCOPE" =~ ^l[0-9]+$ ]]; then
            run_pytest "tests/e2e/test_layers/test_${SCOPE}.py"
        else
            run_pytest "tests/e2e/test_scenarios/test_${SCOPE}.py"
        fi
        ;;
esac

echo ""
echo -e "${GREEN}==> E2E 测试完成${NC}"
```

## 测试用例示例

### S2-L3: 代码开发 - 工具调用

```python
async def test_file_read_and_edit(temp_project: Path, api_key: str):
    """验证文件读写工具的完整链路"""
    # 1. 创建测试文件
    test_file = temp_project / "hello.py"
    test_file.write_text("print('hello world')")

    # 2. 调用 CLI headless
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "claude-code-py.cli.main",
        "--print", f"Read {test_file} and explain it",
        cwd=temp_project,
        env={**os.environ, "ANTHROPIC_API_KEY": api_key},
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)

    # 3. 验证输出
    assert proc.returncode == 0, f"stderr: {stderr.decode()}"
    assert b"hello" in stdout
```

### S5-L7: 安全管控 - 细分测试

```python
# test_s5_security_permissions.py
async def test_permission_mode_readonly_blocks_write(temp_project, api_key):
    """read-only 模式应阻止写操作"""
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "claude-code-py.cli.main",
        "--print", "--permission-mode", "read-only",
        "Create a file called test.txt",
        cwd=temp_project,
        env={**os.environ, "ANTHROPIC_API_KEY": api_key},
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
    output = stdout.decode().lower()
    # 验证被拒绝或安全处理
    assert proc.returncode != 0 or "denied" in output or "not allowed" in output

async def test_permission_mode_deny_blocks_dangerous(temp_project, api_key):
    """deny 模式应阻止危险命令"""
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "claude-code-py.cli.main",
        "--print", "--permission-mode", "deny",
        "rm -rf /",
        cwd=temp_project,
        env={**os.environ, "ANTHROPIC_API_KEY": api_key},
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
    output = (stdout + stderr).decode().lower()
    assert "denied" in output or proc.returncode != 0

# test_s5_security_budgets.py
async def test_budget_enforcement(temp_project, api_key):
    """验证 budget 限额执行

    TODO: 实现 budget 测试
    - 设置 token budget 限制
    - 发送超出 budget 的请求
    - 验证 budget 超出时的行为
    """
    pytest.skip("test_budget_enforcement not yet implemented")

# test_s5_security_rules.py
async def test_custom_rules_evaluation(temp_project, api_key):
    """验证自定义规则文件评估

    TODO: 实现自定义规则测试
    - 创建 .claude/rules.json 规则文件
    - 发送触发规则的请求
    - 验证规则评估结果
    """
    pytest.skip("test_custom_rules_evaluation not yet implemented")
```

### S7-L8: MCP 集成测试

```python
# test_s7_mcp.py

async def test_mcp_server_connection(http_mock_server, api_key):
    """验证 MCP 服务器连接和协议通信"""
    # 1. 启动 mock MCP server (使用 pytest-httpserver)
    # 2. 加载 MCP 配置
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "claude-code-py.cli.main",
        "--print", "--mcp-config", mcp_config_path,
        "List available resources",
        env={**os.environ, "ANTHROPIC_API_KEY": api_key},
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
    assert proc.returncode == 0

async def test_mcp_resource_read(api_key, http_mock_server):
    """验证 MCP resource 读取

    TODO: 实现 MCP resource 读取测试
    - 配置 mock MCP server 提供 test resource
    - 发送读取 resource 的请求
    - 验证返回的 resource 内容
    """
    pytest.skip("test_mcp_resource_read not yet implemented (requires http_mock_server)")

async def test_mcp_tool_invocation(api_key, http_mock_server):
    """验证通过 MCP 协议调用工具

    TODO: 实现 MCP tool 调用测试
    - 配置 mock MCP server 提供 test tool
    - 发送触发 tool 的请求
    - 验证 tool 执行结果
    """
    pytest.skip("test_mcp_tool_invocation not yet implemented (requires http_mock_server)")
```

### L8: Bridge 层测试

```python
# test_l8_bridge.py
from pytest_httpserver import HTTPServer

async def test_bridge_protocol_serialization():
    """验证 Bridge 协议消息序列化"""
    from claude_code.bridge.protocol import BridgeMessage, BridgeMessageType, BridgeProtocol

    protocol = BridgeProtocol()

    # 创建 tool result 消息 (RESULT type with tool data in payload)
    msg = BridgeMessage(
        type=BridgeMessageType.RESULT.value,
        payload={
            "subtype": "success",
            "tool_name": "bash",
            "tool_use_id": "test-123",
            "data": "ok",
        },
        id="test-123",
    )

    # 序列化
    encoded = protocol.serialize_message(msg)
    # 反序列化
    decoded = protocol.parse_message(encoded)
    assert decoded is not None
    assert decoded.type == BridgeMessageType.RESULT.value
    assert decoded.payload.get("tool_name") == "bash"

async def test_ide_protocol_communication(tmp_path):
    """验证与 IDE 插件的协议通信

    TODO: 使用 pytest-httpserver 模拟 IDE 插件端点
    - 设置 JSON-RPC 端点
    - 验证消息往返
    """
    pytest.skip("test_ide_protocol_communication not yet implemented")
```

### L4: 引擎层 - Tool Orchestration

```python
# test_l4_engine.py
async def test_parallel_tool_execution(api_key):
    """验证工具并行执行"""
    from claude_code.engine.engine import QueryEngine
    from claude_code.services.api.claude import create_client

    async with asyncio.timeout(API_TIMEOUT):
        client = create_client()
        engine = QueryEngine(api_client=client)

        results = []
        async for event in engine.submit_message(
            prompt="Run two independent commands: echo hello and echo world",
            messages=[],
        ):
            if isinstance(event, ToolResultEvent):
                results.append(event)

        assert len(results) >= 1  # 至少有一个工具结果
```

## 测试隔离策略

```python
# 1. Session store: 每个测试使用独立 tmp_path
# 2. 并行执行: 使用 pytest-xdist，每个 worker 使用独立端口
#    pytest tests/e2e/ -n auto
# 3. API 状态: 测试间不依赖 API 侧状态，只验证本地输出
# 4. 文件系统: temp_project 每个测试独立
# 5. 环境变量: 子进程继承独立 env，不污染主进程
```

## 报告输出

### text 报告 (默认)

```bash
./e2e.sh all
# E2E Results: 42 passed, 3 failed
# Failed: test_s7_mcp_connection, test_l8_bridge_protocol
```

### JSON 报告

需要添加 `pytest-json-report` 插件：

```toml
# pyproject.toml 新增依赖
[project.optional-dependencies]
e2e = [
    "pytest-json-report>=2.5.0",
]
```

报告 schema：

```json
{
  "version": "1.0",
  "summary": {
    "total": 45,
    "passed": 42,
    "failed": 3,
    "skipped": 0,
    "duration": 120.5
  },
  "failures": [
    {
      "test": "test_s7_mcp_connection",
      "message": "MCP server connection timeout",
      "details": "..."
    }
  ],
  "environment": {
    "python": "3.11.14",
    "api": "real",
    "timestamp": "2026-04-09T10:00:00Z"
  }
}
```

## CI 集成

```yaml
# .github/workflows/e2e.yml
name: E2E Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install deps
        run: |
          ./script/setup.sh
          source .venv/bin/activate
          pip install pytest-json-report
      - name: Run E2E
        run: ./script/e2e.sh all json
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      - name: Upload report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: e2e-report
          path: e2e-report.json
      - name: Check failures
        if: failure()
        run: |
          echo "E2E tests failed. See artifact for details."
          cat e2e-report.json | jq '.failures'
```

## 执行计划

### Phase 1: 基础框架
- [ ] 创建 `script/e2e.sh`
- [ ] 创建 `tests/e2e/conftest.py` (含 fixtures 和 teardown)
- [ ] 添加 `pytest-json-report` 到依赖
- [ ] 实现 L1 (CLI 层) 测试
- [ ] 实现 L5 (API 层) 测试

### Phase 2: 核心场景
- [ ] 实现 S2 (代码开发) 测试
- [ ] 实现 S3 (工具调用) 测试
- [ ] 实现 L3 (工具层) 测试
- [ ] 实现 L4 (引擎层) 测试

### Phase 3: 安全与存储
- [ ] 实现 S5 安全测试 (permissions, budgets, rules 分开)
- [ ] 实现 S6 (会话管理) 测试
- [ ] 实现 L6 (存储层) 测试
- [ ] 实现 L7 (安全层) 测试

### Phase 4: 完整覆盖
- [ ] 实现 S1 (项目初始化) 测试
- [ ] 实现 S4 (团队协作) 测试
- [ ] 实现 S7 (MCP) 测试
- [ ] 实现 S8 (插件) 测试
- [ ] 实现 L8 (Bridge) 测试
- [ ] 实现 L9 (Hooks) 测试
- [ ] CI 集成
- [ ] 报告生成器完善

## 验收标准

每个 E2E 测试必须：

1. **真实 API 调用**: 使用真实 Claude API (或明确 skip)
2. **清晰结构**: setup / execute / verify 三段式
3. **错误信息**: 失败时提供有意义的断言消息
4. **独立运行**: 不依赖其他测试的状态
5. **时间限制**: 单个测试 < 60s
6. **资源清理**: 使用 fixtures 的 teardown 机制
7. **并发安全**: 支持 pytest-xdist 并行执行

## 附录: 报告 Hook 实现

```python
# tests/e2e/conftest_report.py
# 自定义 pytest hook 用于生成 JSON 报告

import json
from pathlib import Path

def pytest_json_runtest_metadata(report):
    """收集测试元数据

    TODO: 实现自定义报告收集
    - 收集测试持续时间
    - 收集失败信息
    - 输出到 e2e-report.json
    """
    raise NotImplementedError("Use pytest-json-report plugin instead")
```

注: 使用 `pytest-json-report` 插件比自定义 hook 更简单，已在 pyproject.toml 中配置。
