# Claude Code Python 迁移设计方案

> 日期：2026-04-05
> 状态：已批准
> 目标：用 Python 完整重写 TypeScript `src/` 模块，最终替代原版

---

## 1. 背景

Claude Code 现有 TypeScript 实现（`src/`）约 512,000 行代码，55 个子目录。决定用 Python 完全重写，作为独立版本发布。

**技术栈**

| 类别 | 技术 | 理由 |
|------|------|------|
| 运行时 | Python 3.11+ | async/await 原生支持 |
| 类型检查 | mypy + Pydantic | 运行时类型验证 |
| CLI UI | Textual | 现代 TUI 框架，类似 React 模型 |
| HTTP 客户端 | httpx | async 支持 |
| WebSocket | websockets | async 原生 |
| Schema 验证 | Pydantic | Python 原生类型验证 |
| Shell 解析 | bashlex | Bash AST 解析 |

---

## 2. 代码结构

```
src_py/
├── __init__.py
├── main.py                    # 入口，CLI 参数解析

├── models/                    # 核心数据模型
│   ├── __init__.py
│   ├── message.py             # Message, Role, Content
│   ├── tool.py                # Tool, ToolResult, ToolUse
│   ├── task.py                # Task, TaskStatus
│   └── session.py             # Session, SessionState

├── engine/                    # 查询引擎
│   ├── __init__.py
│   ├── engine.py              # QueryEngine
│   ├── pipeline.py            # 查询管道 AsyncGenerator
│   ├── context.py             # 上下文压缩
│   └── tools/
│       ├── __init__.py
│       ├── registry.py         # 工具注册表
│       └── orchestration.py   # 工具编排

├── tools/                     # 工具实现 (~45 个)
│   ├── __init__.py
│   ├── base.py                # BaseTool 抽象类
│   ├── bash.py                # BashTool
│   ├── file_read.py           # FileReadTool
│   ├── file_edit.py           # FileEditTool
│   ├── glob.py                # GlobTool
│   ├── grep.py                # GrepTool
│   └── ...

├── commands/                  # 命令实现 (~70+)
│   ├── __init__.py
│   ├── base.py                # BaseCommand
│   ├── commit.py
│   ├── branch.py
│   ├── config.py
│   └── ...

├── cli/                        # CLI UI (Textual)
│   ├── __init__.py
│   ├── app.py                 # Textual TUI 应用
│   ├── repl.py                # REPL 界面
│   ├── output.py              # 输出处理
│   └── style.py                # 样式定义

├── bridge/                     # IDE 桥接
│   ├── __init__.py
│   ├── protocol.py             # 桥接协议
│   ├── vscode.py               # VS Code 扩展
│   └── jetbrains.py            # JetBrains 插件

├── services/                   # 服务层
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── claude.py           # Anthropic API 客户端
│   ├── mcp/
│   │   ├── __init__.py
│   │   ├── client.py           # MCP 客户端
│   │   └── server.py           # MCP 服务器
│   └── storage/
│       └── session.py          # 会话存储

├── state/                      # 状态管理
│   ├── __init__.py
│   ├── store.py                # Observable Store
│   └── hooks.py                # State hooks

├── security/                   # 安全层
│   ├── __init__.py
│   ├── rules.py                # 安全规则
│   ├── permissions.py          # 权限检查
│   └── budgets.py              # 预算控制

├── utils/                      # 工具函数
│   ├── __init__.py
│   ├── shell.py                # Shell 解析/验证
│   └── attachments.py          # 附件处理

└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_engine.py
    ├── test_tools.py
    └── test_commands.py
```

---

## 3. 模块映射

| TypeScript | Python | 说明 |
|------------|--------|------|
| `main.tsx` | `main.py` | CLI 入口 |
| `QueryEngine.ts` | `engine/engine.py` | 查询引擎 |
| `query.ts` | `engine/pipeline.py` | 异步查询管道 |
| `Tool.ts` | `models/tool.py` + `tools/base.py` | 工具类型 |
| `commands.ts` | `commands/registry.py` | 命令注册表 |
| `context.ts` | `engine/context.py` | 上下文管理 |
| `Task.ts` | `models/task.py` | 任务模型 |
| `state/store.ts` | `state/store.py` | 状态存储 |
| `bridge/*` | `bridge/*` | IDE 桥接 |
| `services/api/claude.ts` | `services/api/claude.py` | API 客户端 |
| `services/mcp/client.ts` | `services/mcp/client.py` | MCP 客户端 |
| `tools/*` | `tools/*` | 工具实现 |
| `commands/*` | `commands/*` | 命令实现 |
| `components/*` | `cli/` (Textual) | UI 组件 |

---

## 4. 关键技术设计

### 4.1 TUI 框架：Textual

Textual 采用类似 React 的组件模型，支持 async，适合 CLI 应用：

```python
from textual.app import App
from textual.widgets import Header, Footer, Input

class ClaudeApp(App):
    def compose(self):
        yield Header()
        yield Input(placeholder="Enter message...")
        yield Footer()
```

### 4.2 类型验证：Pydantic

TypeScript Zod schema 映射到 Pydantic：

```python
from pydantic import BaseModel, Field

class ToolInput(BaseModel):
    command: str = Field(..., description="The command to execute")
    timeout: int = Field(default=30, description="Timeout in seconds")
```

### 4.3 流式响应：AsyncGenerator

与 TypeScript AsyncGenerator 语义对应：

```python
async def query_stream(prompt: str) -> AsyncGenerator[MessageEvent, None]:
    yield MessageEvent(type="thinking", content="...")
    yield MessageEvent(type="tool_use", name="Bash", input={...})
```

### 4.4 工具注册表

类似 TypeScript `buildTool` 工厂模式：

```python
class ToolRegistry:
    def register(self, tool: type[BaseTool]) -> None: ...
    def get(self, name: str) -> BaseTool | None: ...
    def list(self) -> list[BaseTool]: ...
```

---

## 5. 实施阶段

### Phase 1: 核心基础设施 (~2 周)
- 项目脚手架 + pyproject.toml 配置
- 数据模型 (Message, Tool, Task, Session)
- 状态存储 (Observable Store)
- API 客户端 (httpx + streaming)

### Phase 2: 查询引擎 (~2 周)
- QueryEngine 实现
- 上下文压缩
- 工具注册表 + 编排
- 基础工具 (Bash, FileRead, FileEdit, Glob, Grep)

### Phase 3: CLI + REPL (~2 周)
- Textual TUI 应用
- REPL 界面
- 命令解析器
- 输出渲染

### Phase 4: 命令系统 (~2 周)
- 命令注册表
- 核心命令 (commit, branch, config, add-dir, etc.)
- 帮助系统

### Phase 5: 桥接系统 (~2 周)
- IDE 桥接协议
- VS Code 扩展
- JetBrains 插件

### Phase 6: 服务集成 (~2 周)
- MCP 客户端/服务器
- 会话存储
- 安全规则

### Phase 7: 完善 + 测试 (~2 周)
- 剩余工具 (~40 个)
- 剩余命令 (~60 个)
- 完整测试覆盖
- 文档

---

## 6. 兼容性目标

- 配置文件格式兼容现有 `claude_desktop_config.json`
- 会话格式兼容现有存储
- MCP 协议完全兼容
- IDE 桥接协议兼容现有扩展
