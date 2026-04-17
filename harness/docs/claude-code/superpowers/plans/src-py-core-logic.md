# src_py 核心逻辑文档

这是一个轻量级 Python Agent 引擎，采用模块化架构。

---

## 1. 入口与 CLI (`src_py/cli/cli.py`)

```
main() → CLI.run() → REPL Loop
```

- 使用 **Typer** 构建 CLI，**Rich** 做终端UI
- REPL 循环：解析用户输入 → 判断类型（message/builtin/skill）→ 分发处理
- 支持的命令：`/help`, `/status`, `/tasks`, `/agents`, `/context`, `/budget`, `/exit`
- 优雅关闭：停止输入 → 等待运行中任务 → 刷新检查点 → 关闭连接

---

## 2. 编排器 (`src_py/orchestrator/orchestrator.py`)

**AgentOrchestrator** 是核心调度引擎：

| 职责 | 说明 |
|------|------|
| **Task DAG** | 用 `task_graph.py` 追踪任务依赖关系 |
| **Agent 管理** | 创建/删除/获取 agent，每个 agent 有角色(coordination/executor/reviewer) |
| **并发控制** | per-task lock + per-agent semaphore |
| **消息路由** | agent 间消息传递，经 LLM 处理 |
| **错误恢复** | 5种策略：重试/退避重试/降级模型/恢复输出/标记失败 |
| **熔断器** | 连续失败 N 次后打开熔断器，防止级联故障 |

**主循环** `run()`:
```
while running:
    ready_tasks = graph.get_ready_tasks()  # 依赖已满足
    for task in ready_tasks:
        agent = select_agent(task)  # 选择合适的agent
        execute_task(task)           # 加锁执行
    yield events                     # 推送事件
```

---

## 3. 状态管理 (`src_py/state/store.py`)

**StateStore** 实现 WAL + 检查点机制：

```
写入 → WAL(.wal) → 增量日志(.jl) → 定期快照(.snap.json)
```

- **WAL (Write-Ahead Log)**: 每次变更先写日志，保证持久性
- **增量日志**: 记录每次 checkpoint 的状态差量
- **快照**: 每 N 次 checkpoint 创建一次完整快照，并截断 WAL
- **恢复**: 从最新快照 + 增量日志回放恢复状态
- **订阅机制**: 支持监听任意 key 或全部变更

---

## 4. 会话管理 (`src_py/session/manager.py`)

**SessionManager** 管理会话生命周期：

- **创建**: 生成 UUID，记录创建时间、token 使用量、状态
- **持久化**: 可选磁盘存储（`~/.src_py/sessions/{id}.json`）
- **追踪**: tool_calls 计数、errors 计数、token 消耗
- **列表/归档**: 按状态过滤会话

---

## 5. LLM 客户端 (`src_py/api/client.py`)

**LiteLLMClient** 对接 Anthropic API：

- `chat_complete()`: 同步对话补全
- `stream_complete()`: 流式输出，带 SSE 解析
- `stream_complete_with_backpressure()`: 带背压控制的流式
- **错误处理**: 区分 RateLimitError / AuthenticationError / ContextLengthExceeded
- **工具调用**: 解析 `tool_use` 类型的内容块

---

## 6. 上下文压缩 (`src_py/context/manager.py`)

**ContextManager** 实现 4 级压缩策略：

| 阈值 | 策略 | 行为 |
|------|------|------|
| < 80% | none | 不压缩 |
| 80-90% | snip | 截断长代码块，合并小工具结果 |
| 90-95% | microcompact | 合并工具调用，去重系统消息 |
| > 95% | collapse | 归档旧消息到 Milvus，生成语义摘要 |

**ArchiveStore**: collapse 时将消息存入 Milvus 向量数据库，支持后续检索。

---

## 7. 记忆系统 (`src_py/memory/store.py`)

**MemoryStore** = Mem0 + Milvus：

- **Mem0Client**: 记忆的 CRUD，基于词频的轻量向量化（TF-IDF 风格）
- **MilvusClient**: 向量数据库客户端（当前为内存实现）
- **AgentMemory**: 每个 agent 的记忆接口
  - `recall(query)`: 语义搜索记忆
  - `memorize(content)`: 存储新记忆
- **LRU 驱逐**: 超过 `max_memories_per_user` 时删除最旧记忆

---

## 8. 安全层 (`src_py/security/layer.py`)

**SecurityLayer** 5 级权限模式：

| 级别 | 行为 |
|------|------|
| `BYPASS` | ⚠️ 完全跳过检查（需 `--bypass-confirm`，所有操作记审计日志）|
| `AUTO_ACCEPT` | 自动批准安全操作 |
| `ACCEPT_EDITS` | 自动批准只读操作 |
| `PLAN` | 计划模式下自动批准 |
| `REVIEW` | 需用户确认（默认）|
| `DENY` | 阻止所有操作 |

**检查顺序**: BYPASS → 预算耗尽 → 规则匹配 → 模式默认行为

---

## 9. 工具系统 (`src_py/tools/base.py`)

- **ToolDefinition**: 工具定义（名称/描述/输入 schema/权限级别）
- **ToolRegistry**: 工具注册表，`to_llm_format()` 转为 LLM 可用格式
- **ToolExecutor**: 执行器，带超时控制 + 并发控制 + 权限检查

---

## 10. 数据模型 (`src_py/lib/models.py`)

核心数据结构：
- **Message**: 消息（role/content/tool_calls/tool_results)
- **StreamChunk**: 流式输出块
- **TokenUsage**: token 消耗统计
- **ToolCall / ToolResult**: 工具调用和结果

---

## 系统数据流

```
用户输入 → CLI (命令解析)
    ↓
消息 → Orchestrator (任务编排)
    ↓
LLM Client (调用 API)
    ↓
Tool Executor (权限检查 + 执行工具)
    ↓
StateStore (状态持久化 + 事件通知)
    ↓
ContextManager (上下文压缩)
    ↓
MemoryStore (记忆存储/检索)
    ↓
返回结果 → CLI (输出展示)
```
