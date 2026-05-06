# Agent 循环引擎 (Agent Loop Engine)

## 概述

Agent 循环是 OpenHarness 的核心引擎，负责驱动整个 Agent 的运行流程。它实现了一个基于 API 流式响应的异步循环机制，在用户提示和模型响应之间迭代执行工具调用。

## 核心架构

```
┌─────────────────────────────────────────────────────────────┐
│                      QueryEngine                             │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐   │
│  │  messages[]  │  │ tool_registry│  │permission_check│   │
│  └─────────────┘  └──────────────┘  └────────────────┘   │
│         │                │                    │             │
│         └────────────────┴────────────────────┘             │
│                          │                                  │
│                    run_query()                              │
│                          │                                  │
│         ┌────────────────┼────────────────┐                  │
│         ▼                ▼                ▼                  │
│   ┌──────────┐   ┌────────────┐   ┌──────────┐           │
│   │API Stream│   │Tool Execute│   │ Auto     │           │
│   │(Model IO)│   │(43 tools)  │   │ Compact  │           │
│   └──────────┘   └────────────┘   └──────────┘           │
└─────────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. QueryEngine (`engine/query_engine.py`)

`QueryEngine` 是 Agent 循环的高级封装类，管理对话历史和工具感知模型循环。

**关键属性：**
- `_messages: list[ConversationMessage]` — 对话历史
- `_api_client` — API 客户端（支持流式）
- `_tool_registry` — 工具注册表
- `_permission_checker` — 权限检查器
- `_cost_tracker` — 成本追踪器

**核心方法：**

```python
class QueryEngine:
    async def submit_message(
        self,
        prompt: str | ConversationMessage
    ) -> AsyncIterator[StreamEvent]:
        """提交用户消息并执行查询循环"""

    async def continue_pending(
        self,
        *,
        max_turns: int | None = None
    ) -> AsyncIterator[StreamEvent]:
        """在工具结果待处理时继续循环"""

    def has_pending_continuation(self) -> bool:
        """检查是否有待处理的工具调用"""
```

### 2. QueryContext (`engine/query.py`)

`QueryContext` 是查询运行的共享上下文，在整个循环过程中传递。

```python
@dataclass
class QueryContext:
    api_client: SupportsStreamingMessages
    tool_registry: ToolRegistry
    permission_checker: PermissionChecker
    cwd: Path
    model: str
    system_prompt: str
    max_tokens: int
    permission_prompt: PermissionPrompt | None = None
    ask_user_prompt: AskUserPrompt | None = None
    max_turns: int | None = 200
    hook_executor: HookExecutor | None = None
    tool_metadata: dict[str, object] | None = None
```

### 3. 核心循环 `run_query()`

`run_query()` 函数实现了工具感知的查询循环：

```python
async def run_query(
    context: QueryContext,
    messages: list[ConversationMessage],
) -> AsyncIterator[tuple[StreamEvent, UsageSnapshot | None]]:
```

**循环流程：**

```
while max_turns 未达到:
    1. Auto-Compact 检查
       └── 自动压缩旧消息以节省 token

    2. API 流式调用
       └── stream_message() → AssistantTextDelta 事件

    3. 模型响应完成
       └── AssistantTurnComplete 事件

    4. 工具调用处理
       ├── 单工具 → 顺序执行
       └── 多工具 → 并发执行 (asyncio.gather)

    5. 结果反馈
       └── ToolResultBlock → 添加到消息 → 继续循环
```

## 流事件系统 (`stream_events.py`)

Agent 循环通过异步迭代器 yield 多种流事件：

```python
StreamEvent = (
    AssistantTextDelta      # 增量文本
    | AssistantTurnComplete # 助手回合完成
    | ToolExecutionStarted   # 工具执行开始
    | ToolExecutionCompleted  # 工具执行完成
    | ErrorEvent            # 错误事件
    | StatusEvent           # 状态消息
)
```

**事件示例：**

```python
# 文本增量
AssistantTextDelta(text="正在读取文件...")

# 工具执行开始
ToolExecutionStarted(tool_name="file_read", tool_input={"path": "test.py"})

# 工具执行完成
ToolExecutionCompleted(tool_name="file_read", output="file content...", is_error=False)

# 错误事件
ErrorEvent(message="Permission denied", recoverable=True)
```

## 工具执行流程 (`_execute_tool_call`)

```python
async def _execute_tool_call(
    context: QueryContext,
    tool_name: str,
    tool_use_id: str,
    tool_input: dict[str, object],
) -> ToolResultBlock:
```

**执行步骤：**

```
1. Pre-Hook 检查 (HookEvent.PRE_TOOL_USE)
   └── 阻塞性 hook 可取消工具执行

2. 工具查找
   └── tool_registry.get(tool_name)

3. 输入验证
   └── tool.input_model.model_validate(tool_input)

4. 权限检查
   ├── 敏感路径检查 (SENSITIVE_PATH_PATTERNS)
   ├── 显式允许/拒绝列表
   ├── 路径规则匹配
   ├── 命令模式匹配
   └── 权限模式评估 (default/plan/full_auto)

5. 工具执行
   └── tool.execute(parsed_input, ToolExecutionContext)

6. Post-Hook (HookEvent.POST_TOOL_USE)
```

## 并发工具执行

多工具调用时使用 `asyncio.gather` 并发执行：

```python
if len(tool_calls) == 1:
    # 单工具：顺序执行，立即流式输出
    result = await _execute_tool_call(...)
    yield ToolExecutionCompleted(...)
else:
    # 多工具：并发执行，事件在完成后输出
    results = await asyncio.gather(*[
        _execute_tool_call(tc) for tc in tool_calls
    ])
```

## 自动压缩 (Auto-Compact)

在每个回合开始时检查 token 限制，实现上下文自动压缩：

```python
# 位于 services/compact/
auto_compact_if_needed(messages, api_client, model, system_prompt, state)
```

压缩策略：
1. **微压缩** — 清除旧的工具结果内容
2. **完全压缩** — 使用 LLM 对旧消息进行摘要

## 重试机制

API 客户端内置指数退避重试：

```python
ApiRetryEvent(
    message="Rate limit hit",
    delay_seconds=2.0,
    attempt=1,
    max_attempts=5
)
```

## 扩展点

### 1. 自定义权限提示

```python
async def my_permission_prompt(tool_name: str, reason: str) -> bool:
    return await ask_user(f"Allow {tool_name}? {reason}")

engine = QueryEngine(
    permission_prompt=my_permission_prompt,
    ...
)
```

### 2. 自定义用户提示

```python
async def my_ask_user(question: str) -> str:
    return await input(question)

engine = QueryEngine(
    ask_user_prompt=my_ask_user,
    ...
)
```

### 3. Pre/Post Tool Hook 集成

```python
hook_executor = HookExecutor(registry, context)
engine = QueryEngine(
    hook_executor=hook_executor,
    ...
)
```

## 与其他模块的交互

| 模块 | 交互方式 |
|------|----------|
| `tools/` | 通过 `ToolRegistry` 获取和执行工具 |
| `permissions/` | 通过 `PermissionChecker` 进行权限评估 |
| `hooks/` | 通过 `HookExecutor` 执行生命周期钩子 |
| `api/` | 通过 `SupportsStreamingMessages` 接口调用模型 |
| `services/compact/` | 在每个回合前自动压缩消息 |

## 关键文件

| 文件 | 职责 |
|------|------|
| `engine/query_engine.py` | QueryEngine 高级封装 |
| `engine/query.py` | run_query 核心循环实现 |
| `engine/messages.py` | ConversationMessage 数据模型 |
| `engine/stream_events.py` | 流事件类型定义 |
| `engine/cost_tracker.py` | Token 使用量追踪 |
