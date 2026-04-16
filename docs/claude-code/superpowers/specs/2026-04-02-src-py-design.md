# src_py 设计规范

**版本**: 1.4
**日期**: 2026-04-03
**状态**: 设计中

## 概述

src_py 是一个轻量级 Python Agent 引擎，定位为 src (TypeScript) 的独立演进版本。src_py 汲取 src 的核心架构设计，但保持 Python 的简洁性。

**核心目标**：
- 支持 coding agent 的核心功能
- 轻量级、可扩展
- 独立于 src 演进

---

## 一、整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                        REPL / CLI                            │
├─────────────────────────────────────────────────────────────┤
│                    Agent Orchestrator                        │
│         (Task Graph + DAG + State Machine)                   │
├──────────────┬──────────────┬──────────────┬────────────────┤
│ Tools System │ Skills Sys  │ MCP Client   │ Observability  │
│              │ (AgentSkills│ + FastMCP    │ (Phoenix)      │
│              │  Spec)      │ Server       │                │
├──────────────┴──────────────┴──────────────┴────────────────┤
│              Context Manager (4级压缩)                       │
├─────────────────────────────────────────────────────────────┤
│                    LiteLLM Client                            │
├─────────────────────────────────────────────────────────────┤
│          Security Layer (5级权限 + Budget)                   │
├───────────────────────────┬─────────────────────────────────┤
│   Memory Store            │   Session Manager               │
│   (Mem0 + Milvus)        │                                 │
├───────────────────────────┴─────────────────────────────────┤
│              State Store (内存 + Checkpoint)                │
└─────────────────────────────────────────────────────────────┘
```

**依赖说明**：
- Orchestrator 依赖 Tools/Skills/MCP 调用 LLM
- Tools/Skills/MCP 处于 Orchestrator 下方（被调用方）
- Context Manager 位于 LiteLLM Client 上方（管理其输入）

**架构原则**：
- 每层只与上下相邻层通信
- 核心逻辑（Orchestrator）不依赖 UI
- 可独立测试每个组件

---

## 二、CLI 界面与命令系统

**技术选型**: Typer + Rich

### 2.1 CLI 架构

```
┌─────────────────────────────────────────────────────────────┐
│                         CLI UI (Typer + Rich)               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Status Bar  │  │ Output Area │  │  Interactive Input   │  │
│  │ (Rich)      │  │ (Rich Live) │  │  (Typer)            │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                    State Synchronizer                       │
│              (WebSocket / SSE / Polling)                     │
├─────────────────────────────────────────────────────────────┤
│                    Agent Orchestrator                       │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 CLI 组件

```python
import typer
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel

app = typer.Typer()
console = Console()

class CLI:
    """CLI 主入口 - Typer + Rich"""

    def __init__(
        self,
        orchestrator: AgentOrchestrator,
        state_syncer: StateSyncer,
    ):
        self.app = typer.Typer()
        self.console = Console()
        self.live: Live | None = None
        self.orchestrator = orchestrator
        self.state_syncer = state_syncer

    async def run(self) -> None:
        """启动 CLI"""
        await self._setup_commands()
        self.app()

class StatusBar:
    """状态栏 - Rich 渲染"""

    def __init__(self, state_store: StateStore):
        self.state_store = state_store

    def render(self) -> Panel:
        """渲染状态栏"""
        table = Table(show_header=False, box=None)
        table.add_column(style="bold cyan")
        table.add_column()
        table.add_row("Model:", self.state_store.get("model"))
        table.add_row("Tokens:", f"{self.state_store.get('token_usage')}/{self.state_store.get('max_tokens')}")
        table.add_row("Tasks:", f"{self.state_store.get('active_tasks')} active")
        table.add_row("Mode:", self.state_store.get('permission_mode'))
        return Panel(table, title="Status", border_style="blue")

class OutputHandler:
    """Rich 流式输出处理器"""

    def __init__(self, console: Console):
        self.console = console
        self._live: Live | None = None
        self._buffer: list[str] = []

    async def print(self, message: str, style: str = "") -> None:
        """打印消息"""
        self.console.print(message, style=style)

    async def print_stream(self, text: str, is_final: bool = False) -> None:
        """流式打印文本 - 支持实时输出"""
        self._buffer.append(text)
        if self._live:
            self._live.update(Panel(
                "\n".join(self._buffer),
                title="Streaming Output",
                border_style="green"
            ))
        else:
            # 非交互模式，直接打印
            self.console.print(text, end="", soft_wrap=True)

    async def print_tool_call(self, tool_call: ToolCall) -> None:
        """打印 Tool 调用"""
        tool_panel = Panel(
            f"[bold cyan]Tool:[/bold cyan] {tool_call.name}\n"
            f"[bold cyan]Args:[/bold cyan] {json.dumps(tool_call.input, indent=2)}",
            title="Tool Call",
            border_style="yellow"
        )
        self.console.print(tool_panel)

    async def print_tool_result(self, result: ToolResult) -> None:
        """打印 Tool 结果"""
        if result.error:
            style = "bold red"
            content = f"[bold red]Error:[/bold red] {result.error}"
        else:
            style = "bold green"
            content = f"[bold green]Success[/bold green]: {str(result.output)[:200]}"
        self.console.print(Panel(content, title=f"Result ({result.call_id})", border_style=style))

    async def print_task_update(self, task: Task) -> None:
        """打印任务更新"""
        status_color = {
            "pending": "yellow",
            "running": "cyan",
            "completed": "green",
            "failed": "red",
        }.get(task.status, "white")

        self.console.print(
            f"[{status_color}][{task.status.upper()}][/{status_color}] "
            f"{task.id}: {task.description}"
        )

    async def print_task_table(self, tasks: list[Task]) -> None:
        """打印任务表格"""
        table = Table(title="Tasks")
        table.add_column("ID", style="cyan")
        table.add_column("Status", style="yellow")
        table.add_column("Description")
        table.add_column("Agent", style="magenta")
        for task in tasks:
            table.add_row(
                task.id,
                task.status,
                task.description[:50] + "..." if len(task.description) > 50 else task.description,
                task.agent_id or "-"
            )
        self.console.print(table)

    def start_live(self) -> None:
        """启动实时显示模式"""
        self._live = Live(
            Panel("Initializing...", title="Status"),
            console=self.console,
            refresh_per_second=10
        )
        self._live.start()

    def stop_live(self) -> None:
        """停止实时显示模式"""
        if self._live:
            self._live.stop()
            self._live = None
```

### 2.3 Typer 命令定义

```python
@app.command()
def help():
    """显示帮助信息"""
    console.print(Panel.fit("[bold]Available Commands[/bold]\n\n" + HELP_TEXT))

@app.command()
def status():
    """显示当前状态"""
    # 显示状态栏

@app.command()
def tasks(list_all: bool = False):
    """列出所有任务"""
    # 显示任务列表

@app.command()
def agents():
    """列出所有 Agent"""
    # 显示 Agent 列表

@app.command()
def context():
    """显示上下文使用情况"""
    # 显示 token 使用

@app.command()
def budget():
    """显示权限预算"""
    # 显示预算信息

@app.command()
def exit():
    """退出"""
    raise typer.Exit()

@app.callback()
def main():
    """src_py - Lightweight Python Agent Engine"""
    pass
```

### 2.4 命令类型

| 命令 | 类型 | 描述 |
|------|------|------|
| `/help` | 内置 | 显示帮助信息 |
| `/status` | 内置 | 显示当前状态 |
| `/tasks` | 内置 | 列出所有任务 |
| `/agents` | 内置 | 列出所有 Agent |
| `/history` | 内置 | 显示历史消息 |
| `/skill <name>` | Skill | 触发 Skill |
| `/task <description>` | Task | 创建新任务 |
| `/agent <name> <role>` | Agent | 创建新 Agent |
| `/context` | 内置 | 显示上下文使用情况 |
| `/budget` | 内置 | 显示权限预算 |
| `/exit` | 内置 | 退出 |

### 2.5 命令解析器

```python
import shlex

class CommandParser:
    """命令解析器 - 使用 shlex 处理引号"""

    # 保护性命令（不能被 skill 劫持）
    PROTECTED_COMMANDS = {"exit", "quit", "help"}

    # 内置命令集合
    BUILTIN_COMMANDS = {"help", "status", "tasks", "agents", "context", "budget", "exit"}

    # 优先级（数字越大优先级越高）
    BUILTIN_PRIORITY = 100
    SKILL_PRIORITY = 50

    def __init__(self, skill_registry: SkillRegistry):
        self.skill_registry = skill_registry

    def parse(self, input_text: str) -> ParsedCommand:
        """解析命令"""
        if not input_text.startswith("/"):
            return ParsedCommand(type="message", args=input_text)

        # 使用 shlex.split() 处理引号和转义
        parts = shlex.split(input_text[1:])
        cmd = parts[0]

        # 保护性命令优先
        if cmd in self.PROTECTED_COMMANDS:
            return ParsedCommand(
                type="builtin",
                name=cmd,
                args=parts[1:],
                priority=self.BUILTIN_PRIORITY,
            )

        # 内置命令
        if cmd in self.BUILTIN_COMMANDS:
            return ParsedCommand(
                type="builtin",
                name=cmd,
                args=parts[1:],
                priority=self.BUILTIN_PRIORITY,
            )

        # 查找 Skill
        skill = self.skill_registry.find_by_trigger(f"/{cmd}")
        if skill:
            return ParsedCommand(
                type="skill",
                name=cmd,
                args=parts[1:],
                skill=skill,
                priority=self.SKILL_PRIORITY,
            )

        return ParsedCommand(type="unknown", name=cmd)

@dataclass
class ParsedCommand:
    type: Literal["message", "builtin", "skill", "unknown"]
    name: str
    args: list[str]
    skill: SkillDefinition | None = None
    priority: int = 0  # 命令优先级
```

### 2.6 Typer 命令组

```python
# 使用 Typer 子命令组
task_cmd = Typer()
agent_cmd = Typer()
skill_cmd = Typer()

app = Typer()
app.add_typer(task_cmd, name="task")
app.add_typer(agent_cmd, name="agent")
app.add_typer(skill_cmd, name="skill")

@task_cmd.command("create")
def task_create(description: str, depends_on: list[str] = []):
    """创建新任务"""

@task_cmd.command("list")
def task_list(all: bool = False):
    """列出所有任务"""

@task_cmd.command("status")
def task_status(task_id: str):
    """显示任务状态"""

@agent_cmd.command("create")
def agent_create(name: str, role: str):
    """创建新 Agent"""

@agent_cmd.command("list")
def agent_list():
    """列出所有 Agent"""
```

### 2.7 优雅关闭

```python
import signal

class CLI:
    async def run(self) -> None:
        # 设置信号处理器
        loop = asyncio.get_event_loop()

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(
                sig,
                lambda: asyncio.create_task(self._shutdown())
            )

        await self._start_repl()

    async def _shutdown(self) -> None:
        """优雅关闭"""
        # 1. 停止接收新输入
        # 2. 等待正在执行的任务完成
        # 3. 清理资源
        if self.output_handler:
            self.output_handler.stop_live()
        if self.state_syncer:
            await self.state_syncer.disconnect()
        if self.orchestrator:
            await self.orchestrator.checkpoint()
```

## 三、实时状态同步

### 3.1 状态同步架构

```
┌─────────────────────────────────────────────────────────────┐
│                    State Store                              │
│              (单一事实来源 - Single Source of Truth)        │
├─────────────────────────────────────────────────────────────┤
│                    State Publisher                          │
│              (状态变更发布 - 发布/订阅模式)                   │
├─────────────────────────────────────────────────────────────┤
│                    State Syncer                             │
│         ┌─────────────┬─────────────┬─────────────┐          │
│         │  WebSocket  │    SSE     │   Polling   │          │
│         │  (首选)     │  (备选)    │  (回退)    │          │
│         └─────────────┴─────────────┴─────────────┘          │
├─────────────────────────────────────────────────────────────┤
│                      CLI UI                                  │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 状态发布者

```python
class StatePublisher:
    """状态发布者 - 发布/订阅模式"""

    def __init__(self):
        self._subscribers: dict[str, list[Callable[[StateChange], None]]] = defaultdict(list)
        self._change_stream: asyncio.Queue[StateChange] = asyncio.Queue()

    def subscribe(
        self,
        keys: list[str],
        callback: Callable[[StateChange], None],
    ) -> Callable[[], None]:
        """订阅特定 key 的状态变更"""
        for key in keys:
            self._subscribers[key].append(callback)

        def unsubscribe():
            for key in keys:
                self._subscribers[key].remove(callback)

        return unsubscribe

    async def publish(self, change: StateChange) -> None:
        """发布状态变更"""
        await self._change_stream.put(change)

        # 通知订阅者
        for callback in self._subscribers.get(change.key, []):
            await callback(change)

        # 广播到所有订阅者（通配符订阅）
        for callback in self._subscribers.get("*", []):
            await callback(change)

@dataclass
class StateChange:
    key: str                    # "tasks", "agents", "messages"
    change_type: Literal["created", "updated", "deleted"]
    old_value: Any
    new_value: Any
    timestamp: datetime
    source: str                  # "orchestrator", "tool_executor", etc.
```

### 3.3 状态同步器

**架构说明**：StateSyncer 不直接读取 publisher，而是通过订阅机制接收变更，与 CLIStateSubscriber 统一使用同一订阅模式。

```python
class StateSyncer:
    """状态同步器 - 支持多种传输方式（WebSocket/SSE/Polling）"""

    def __init__(
        self,
        publisher: StatePublisher,
        transport: Literal["websocket", "sse", "polling"] = "websocket",
    ):
        self.publisher = publisher
        self.transport = transport
        self._connection: Connection | None = None
        self._reconnect_delay = 1.0
        self._max_reconnect_delay = 30.0
        self._seq: int = 0  # 序列号，用于断线重连
        self._unsubscribe: Callable[[], None] | None = None
        self._pending_updates: asyncio.Queue[StateChange] = asyncio.Queue(maxsize=100)

    async def connect(self, endpoint: str, from_seq: int = 0) -> None:
        """建立连接

        Args:
            endpoint: 服务器地址
            from_seq: 断线重连时传入，用于补发遗漏的更新
        """
        if self.transport == "websocket":
            self._connection = await WebSocketConnection.connect(endpoint)
        elif self.transport == "sse":
            self._connection = await SSEConnection.connect(endpoint)
        else:
            self._connection = await PollingConnection.connect(endpoint)

        # 通过订阅机制接收变更，而非直接读取
        self._unsubscribe = self.publisher.subscribe(
            keys=["*"],  # 订阅所有变更
            callback=self._on_state_change,
        )

        await self._start_sending()

    async def _on_state_change(self, change: StateChange) -> None:
        """接收状态变更，加入发送队列"""
        try:
            self._pending_updates.put_nowait(change)
        except asyncio.QueueFull:
            # 背压处理：队列满时丢弃最旧的更新
            try:
                self._pending_updates.get_nowait()
                self._pending_updates.put_nowait(change)
            except:
                pass

    async def _start_sending(self) -> None:
        """从队列发送状态变更到连接"""
        while True:
            try:
                change = await self._pending_updates.get()
                self._seq += 1
                await self._connection.send(StateUpdate(
                    type="state_change",
                    change=change,
                    seq=self._seq,
                ))
            except Exception as e:
                await self._handle_connection_error(e)

    async def _handle_connection_error(self, error: Exception) -> None:
        """处理连接错误，自动重连"""
        if self._unsubscribe:
            self._unsubscribe()
            self._unsubscribe = None

        self._reconnect_delay = min(
            self._reconnect_delay * 2,
            self._max_reconnect_delay
        )
        await asyncio.sleep(self._reconnect_delay)

        # 重连时带上最后序列号，用于补发遗漏的更新
        await self.connect(self._connection.endpoint, from_seq=self._seq)

    async def disconnect(self) -> None:
        """断开连接"""
        if self._unsubscribe:
            self._unsubscribe()
        if self._connection:
            await self._connection.close()
```

@dataclass
class StateUpdate:
    type: Literal["state_change", "heartbeat", "error", "replay_complete"]
    change: StateChange | None
    seq: int | None = None  # 序列号
    heartbeat_interval: int | None = None
    dropped_count: int | None = None  # 丢弃的更新数

### 3.4 重放协议（from_seq）

**重放 API 契约**：
```python
# 服务端提供重放端点
@app.route("/api/state/replay")
async def replay_state(since_seq: int, limit: int = 1000):
    """
    返回 since_seq 之后的更新，上限 1000 条或 1MB

    返回格式：
    {
        "updates": [StateUpdate],
        "next_seq": int | None,  # None 表示已追平
        "has_more": bool
    }
    """
```

**重放流程**：
```python
async def _reconnect_with_replay(self, endpoint: str, from_seq: int) -> None:
    """重连并补发遗漏的更新"""

    # 1. 尝试重连
    await self._connect(endpoint)

    # 2. 请求重放
    replay_resp = await self._connection.replay(since_seq=from_seq)

    # 3. 按顺序应用重放的更新
    for update in replay_resp.updates:
        self._seq = update.seq
        await self._apply_update(update)

    # 4. 发送确认
    if replay_resp.dropped_count > 0:
        await self._notify_dropped(replay_resp.dropped_count)

    # 5. 继续正常同步
    await self._start_sending()
```

**回退链 + 健康检查**：
```python
TRANSPORTS = ["websocket", "sse", "polling"]
HEALTH_CHECK_INTERVAL = 5  # 秒
MAX_CONSECUTIVE_FAILURES = 3

async def _try_transport_with_fallback(self) -> None:
    """尝试 transports，自动回退"""
    for transport in TRANSPORTS:
        failures = 0
        while failures < MAX_CONSECUTIVE_FAILURES:
            try:
                await self._connect(transport=transport)
                failures = 0
                await self._main_loop()
            except ConnectionError:
                failures += 1
                await asyncio.sleep(HEALTH_CHECK_INTERVAL)

        # 尝试下一个 transport
        continue
```

### 3.5 CLI 状态订阅者（与 StateSyncer 集成）

**架构说明**：CLIStateSubscriber 是 CLI 内部的本地订阅者，不通过网络传输，直接调用 OutputHandler 渲染。StateSyncer 负责网络传输。

```python
class CLIStateSubscriber:
    """CLI 本地状态订阅者 - 直接渲染状态变更"""

    def __init__(
        self,
        publisher: StatePublisher,
        output_handler: OutputHandler,
    ):
        self.publisher = publisher
        self.output_handler = output_handler
        self._unsubscribes: list[Callable[[], None]] = []

    async def start(self) -> None:
        """开始订阅状态变更（本地订阅，不走网络）"""
        # 任务更新
        self._unsubscribes.append(
            self.publisher.subscribe(["tasks"], self._on_task_change)
        )
        # Agent 更新
        self._unsubscribes.append(
            self.publisher.subscribe(["agents"], self._on_agent_change)
        )
        # 消息更新
        self._unsubscribes.append(
            self.publisher.subscribe(["messages"], self._on_message_change)
        )
        # 错误
        self._unsubscribes.append(
            self.publisher.subscribe(["errors"], self._on_error)
        )

    def stop(self) -> None:
        """停止订阅"""
        for unsub in self._unsubscribes:
            unsub()
        self._unsubscribes.clear()

    async def _on_task_change(self, change: StateChange) -> None:
        """处理任务状态变更"""
        task: Task = change.new_value
        if change.change_type == "created":
            await self.output_handler.print(f"[cyan][[Task Created][/cyan] {task.id}: {task.description}")
        elif change.change_type == "updated":
            await self.output_handler.print_task_update(task)
        elif change.change_type == "completed":
            await self.output_handler.print(f"[green][[Task Completed][/green] {task.id}")
        elif change.change_type == "failed":
            await self.output_handler.print(f"[red][[Task Failed][/red] {task.id}: {task.error}")

    async def _on_agent_change(self, change: StateChange) -> None:
        """处理 Agent 状态变更"""
        agent: Agent = change.new_value
        if change.change_type == "created":
            await self.output_handler.print(f"[magenta][[Agent Created][/magenta] {agent.name} ({agent.role})")

    async def _on_message_change(self, change: StateChange) -> None:
        """处理消息变更（流式输出）"""
        message: Message = change.new_value
        if message.role == "assistant" and message.content:
            await self.output_handler.print_stream(message.content)
        elif message.role == "tool" and message.tool_results:
            for result in message.tool_results:
                await self.output_handler.print_tool_result(result)

    async def _on_error(self, change: StateChange) -> None:
        """处理错误"""
        await self.output_handler.print(f"[bold red][[Error][/bold red] {change.new_value}")
```

### 3.6 状态同步协议

```python
# WebSocket/SSE 消息格式
@dataclass
class WSMessage:
    type: Literal["subscribe", "unsubscribe", "state_change", "heartbeat"]
    payload: dict[str, Any]
    seq: int  # 序列号，保证顺序

# 订阅请求
@dataclass
class SubscribePayload:
    keys: list[str]  # ["tasks", "agents", "messages"]

# 状态变更推送
@dataclass
class StateChangePayload:
    key: str
    change_type: str
    value: Any
    timestamp: int  # unix timestamp
```

### 3.7 实时状态显示

**状态栏（实时更新）：**
```
[Model: claude-3-5-sonnet] [Tokens: 12.5K/200K] [Tasks: 3 active, 12 completed] [Agents: 2] [Errors: 0] [Mode: auto]
```

**任务列表（实时更新）：**
```
Tasks:
  [running] task-001  "Implement login API"           [agent: coder]
  [pending] task-002  "Write unit tests"              [depends: task-001]
  [pending] task-003  "Update documentation"          [depends: task-001]
  [completed] task-000 "Setup project structure"
```

**流式输出示例：**
```
> Implement the login API

[Agent: coder] Starting task: Implement login API
[Tool: FileRead] Reading: src/auth/login.py
[Tool: FileEdit] Modifying: src/auth/login.py
[Task: task-001] Status: running
[Agent: coder] Tool result: FileEdit successful
...
```

---

## 四、核心数据类型

### 4.1 基础类型定义

```python
from dataclasses import dataclass, field
from typing import Literal, Any
from datetime import datetime

@dataclass
class ToolContext:
    """Tool 执行上下文"""
    call_id: str
    agent_id: str
    task_id: str | None
    cwd: str
    env: dict[str, str]
    session_id: str
    token_budget: ContextBudget

# SrcEvent、TaskEvent 定义见 Section 十八、通用类型定义
```

### 4.2 Message 协议

```python
@dataclass
class Message:
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    tool_calls: list[ToolCall] | None = None
    tool_results: list[ToolResult] | None = None
    metadata: dict[str, Any] | None = None

@dataclass
class ToolCall:
    id: str
    name: str
    input: dict[str, Any]
    # 与 ToolResult 通过 id 关联

@dataclass
class ToolResult:
    call_id: str  # 对应 ToolCall.id
    output: Any
    error: str | None = None
```

### 4.3 Task DAG 协议

```python
@dataclass
class Task:
    id: str
    description: str
    status: Literal["pending", "running", "completed", "failed"]
    dependencies: list[str]  # task ids
    agent_id: str | None = None  # 分配执行的 agent
    assigned_at: datetime | None = None
    result: Any | None = None
    error: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
```

### 4.4 Agent 协议

```python
@dataclass
class Agent:
    id: str
    name: str
    role: str  # "coordinator", "executor", "reviewer"
    tools: list[str]  # tool names this agent can use
    skills: list[str]  # skill names
    messages: list[Message]  # agent's local context
    session_id: str | None = None  # 关联的 session
    memory_enabled: bool = True  # 是否启用记忆
```

### 4.5 Context Budget 协议

```python
@dataclass
class ContextBudget:
    max_tokens: int
    current_tokens: int
    compression_strategy: Literal["none", "snip", "microcompact", "collapse"]
    # 阈值可配置，默认：snip=80%, microcompact=90%, collapse=95%
```

### 4.6 错误与恢复协议

```python
# ErrorAction 和 ErrorRecoveryConfig 定义见 Section 十七、错误处理与恢复
# 此处仅作引用：
# - ErrorAction(Enum): 重试、指数退避、模型切换、输出恢复、标记失败、请求用户
# - ErrorRecoveryConfig: max_retries, base_backoff_seconds, max_backoff_seconds,
#                       retry_budget, circuit_breaker_threshold, circuit_breaker_timeout
```

### 4.7 StreamEvent 协议

```python
@dataclass
class StreamEvent:
    """流式事件类型"""
    type: Literal["text", "tool_call", "tool_result", "task_update", "agent_update", "error"]
    content: Any
    timestamp: datetime
```

---

## 五、Agent Orchestrator（核心编排器）

### 5.1 职责

- 管理 Task DAG 的执行
- 协调多个 Agent 的消息路由
- 控制 Context 压缩策略
- 处理错误恢复

### 5.2 核心接口

```python
class AgentOrchestrator:
    def __init__(
        self,
        llm_client: LiteLLMClient,
        tool_registry: ToolRegistry,
        skill_registry: SkillRegistry,
        mcp_client: MCPClient,
        security: SecurityLayer,
        state_store: StateStore,
    ):
        self.agents: dict[str, Agent]
        self.tasks: dict[str, Task]
        self.task_graph: DAG[str]  # task id dependencies（详见 16.1）

        # 并发控制
        self._task_locks: dict[str, asyncio.Lock] = {}  # per-task 锁
        self._task_semaphores: dict[str, asyncio.Semaphore] = {}  # per-agent 并发限制
        self._event_buffer: asyncio.Queue[SrcEvent] = asyncio.Queue(maxsize=1000)  # 有界事件缓冲

    async def create_agent(
        self,
        name: str,
        role: str,
        tools: list[str],
        skills: list[str],
        max_concurrent_tasks: int = 3,
    ) -> Agent

    async def submit_task(
        self,
        description: str,
        dependencies: list[str] = [],
        agent_id: str | None = None,  # 可选指定 agent
    ) -> str  # returns task id

    async def assign_task(self, task_id: str, agent_id: str) -> None:
        """显式分配任务到 agent（解决分配不透明问题）"""

    async def run(self) -> AsyncGenerator[Event, None]:
        """Main event loop yielding TaskEvent, AgentEvent, etc.
        包含错误处理流程图"""

    async def execute_task(self, task_id: str) -> Any:
        """执行任务（带锁保护，防止竞争）"""

    async def route_message(self, agent_id: str, message: Message) -> Message

    async def compress_context(self, agent_id: str) -> None

    async def handle_error(self, error: Exception, context: dict) -> ErrorAction:
        """错误恢复决策树：

        ```
        ┌─────────────────┐
        │   Handle Error  │
        └────────┬────────┘
                 ▼
        ┌─────────────────┐
        │ 检查错误类型     │
        └────────┬────────┘
                 ▼
        ┌─────────────────┐    ┌─────────────────┐
        │ is retryable?   │───►│ MARK_FAILED     │
        └────────┬────────┘    └─────────────────┘
                 │ No
                 ▼
        ┌─────────────────┐
        │ 检查重试预算     │
        └────────┬────────┘
                 ▼
        ┌─────────────────┐    ┌─────────────────┐
        │ 预算耗尽?        │───►│ ASK_USER        │
        └────────┬────────┘    └─────────────────┘
                 │ No
                 ▼
        ┌─────────────────┐
        │ 是否需要切换模型  │
        └────────┬────────┘
                 ▼
        ┌─────────────────┐    ┌─────────────────┐
        │ 是 API 错误?     │───►│ FALLBACK_MODEL  │
        └────────┬────────┘    └─────────────────┘
                 │ No
                 ▼
        ┌─────────────────┐    ┌─────────────────┐
        │ 有 partial output?│──►│ RECOVER_OUTPUT │
        └────────┬────────┘    └─────────────────┘
                 │ No
                 ▼
        ┌─────────────────┐
        │   RETRY         │
        │ (with backoff)  │
        └─────────────────┘
        ```
        """
```

### 5.3 事件类型

```python
@dataclass
class TaskStarted(SrcEvent):
    task_id: str
    agent_id: str

@dataclass
class TaskCompleted(SrcEvent):
    task_id: str
    result: Any

@dataclass
class TaskFailed(SrcEvent):
    task_id: str
    error: str

@dataclass
class AgentMessage(SrcEvent):
    agent_id: str
    message: Message
```

---

## 六、Tool 系统

### 6.1 Tool 定义协议

```python
@dataclass
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]  # JSON Schema
    is_read_only: bool = False
    is_concurrency_safe: bool = True
    permission_required: PermissionLevel = PermissionLevel.ASK

class ToolRegistry:
    def register(self, tool: ToolDefinition) -> None
    def get(self, name: str) -> ToolDefinition | None
    def list(self) -> list[ToolDefinition]
    def list_read_only(self) -> list[ToolDefinition]

class ToolExecutor:
    """Tool 执行器 - 支持超时和并发控制"""

    def __init__(self, security_layer: SecurityLayer):
        self.security_layer = security_layer
        self._semaphores: dict[str, asyncio.Semaphore] = {}  # per-tool 锁
        self._default_timeout = 30.0

    async def execute(
        self,
        tool: ToolDefinition,
        args: dict[str, Any],
        context: ToolContext,
        timeout: float | None = None,
        cancellation_token: asyncio.CancellationToken | None = None,
    ) -> ToolResult:
        """执行工具（带超时和并发控制）"""

        # 1. 权限检查
        perm_result = await self.security_layer.check(tool, args, context)
        if not perm_result.allowed:
            return ToolResult(
                call_id=context.call_id,
                output=None,
                error=f"Permission denied: {perm_result.reason}",
            )

        # 2. 并发控制
        if not tool.is_concurrency_safe:
            if tool.name not in self._semaphores:
                self._semaphores[tool.name] = asyncio.Semaphore(1)
            async with self._semaphores[tool.name]:
                return await self._do_execute(tool, args, context, timeout, cancellation_token)
        else:
            return await self._do_execute(tool, args, context, timeout, cancellation_token)

    async def _do_execute(
        self,
        tool: ToolDefinition,
        args: dict[str, Any],
        context: ToolContext,
        timeout: float | None,
        cancellation_token: asyncio.CancellationToken | None,
    ) -> ToolResult:
        """实际执行逻辑"""
        timeout = timeout or self._default_timeout

        try:
            async with asyncio.timeout(timeout):
                result = await tool.execute(args, context)
                return ToolResult(call_id=context.call_id, output=result)
        except asyncio.CancelledError:
            return ToolResult(
                call_id=context.call_id,
                output=None,
                error="Tool execution cancelled",
            )
        except asyncio.TimeoutError:
            return ToolResult(
                call_id=context.call_id,
                output=None,
                error=f"Tool execution timed out after {timeout}s",
            )
        except Exception as e:
            return ToolResult(
                call_id=context.call_id,
                output=None,
                error=f"Tool execution failed: {str(e)}",
            )

    async def check_permission(
        self,
        tool: ToolDefinition,
        args: dict[str, Any],
        context: ToolContext,
    ) -> PermissionResult:
        return await self.security_layer.check(tool, args, context)
```

### 6.2 内置 Tool

| Tool | 描述 | 权限级别 |
|------|------|---------|
| Bash | 执行 shell 命令 | HIGH |
| FileRead | 读取文件 | MEDIUM |
| FileEdit | 编辑文件 | HIGH |
| FileWrite | 写入文件 | HIGH |
| Grep | 搜索文件内容 | LOW |
| Glob | 文件模式匹配 | LOW |
| WebFetch | HTTP 请求 | MEDIUM |
| TaskCreate | 创建子任务 | MEDIUM |
| AgentCall | 调用其他 Agent | HIGH |

### 6.3 Tool 执行流程

```
ToolCall → Permission Check → Rate Limit Check → Execute → Result
                ↓
          Denied? → Raise PermissionError
```

---

## 七、Skills 系统（Agent Skills 规范）

**核心设计**: Skills 注册为 Tools，LLM 可直接调用

### 7.1 Skill 目录结构

```
skill-name/
├── SKILL.md          # Required: YAML frontmatter + Markdown instructions
├── scripts/          # Optional: executable code
├── references/       # Optional: documentation
├── assets/          # Optional: templates, resources
└── ...
```

### 7.2 SKILL.md 格式

```markdown
---
name: skill-name
description: A description of what this skill does and when to use it.
license: Apache-2.0
compatibility: Requires Python 3.11+
metadata:
  author: example-org
  version: "1.0"
allowed-tools: Bash(git:*) Read Glob
---

# Skill Instructions

Step-by-step instructions, examples, common edge cases...

## Examples

See [reference guide](references/REFERENCE.md) for details.
```

### 7.3 核心字段

| 字段 | 必填 | 说明 |
|------|------|------|
| `name` | 是 | 1-64字符，小写+连字符 |
| `description` | 是 | 1-1024字符，描述用途和触发场景 |
| `allowed-tools` | 否 | 预批准工具列表 |
| `license` | 否 | 许可证 |
| `compatibility` | 否 | 环境要求 |

### 7.4 渐进式加载

1. 启动时只加载 `name` + `description`
2. 激活时加载完整 `SKILL.md`（<5000 tokens）
3. 按需加载 `references/`、`scripts/`、`assets/`

### 7.5 Skill 注册为 Tool

```python
class SkillTool:
    """Skill 包装为 Tool，使 LLM 可直接调用"""

    def __init__(self, skill: SkillDefinition, executor: SkillExecutor):
        self.skill = skill
        self.executor = executor

    @property
    def name(self) -> str:
        return f"skill_{self.skill.name}"

    @property
    def description(self) -> str:
        return self.skill.description

    @property
    def input_schema(self) -> dict[str, Any]:
        # 根据 skill parameters 生成 JSON schema
        # 支持简单参数（string, number, boolean）
        properties = {}
        required = []
        for param in self.skill.parameters or []:
            param_type = param.type.lower()
            if param_type in ["string", "number", "boolean"]:
                properties[param.name] = {
                    "type": param_type,
                    "description": param.description,
                }
                if param.required:
                    required.append(param.name)

        # 默认参数
        if not properties:
            properties["input"] = {"type": "string", "description": "Skill input"}

        return {
            "type": "object",
            "properties": properties,
            "required": required or ["input"],
        }

    async def execute(
        self,
        args: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        result = await self.executor.execute(
            skill=self.skill,
            args=args,
            context=context,
        )
        return ToolResult(call_id=context.call_id, output=result)

class SkillExecutor:
    """Skill 执行器 - 包含 allowed-tools 边界检查和资源限制"""

    def __init__(
        self,
        tool_registry: ToolRegistry,
        timeout: float = 30.0,
        max_memory_mb: int = 256,
    ):
        self.tool_registry = tool_registry
        self.timeout = timeout
        self.max_memory_mb = max_memory_mb

    async def execute(
        self,
        skill: SkillDefinition,
        args: dict[str, Any],
        context: ToolContext,
    ) -> Any:
        """执行 Skill，包含安全检查"""

        # 1. 检查 allowed-tools 边界
        if skill.allowed_tools:
            allowed_set = set(skill.allowed_tools)
            # Skill 可能通过 SkillTool 调用其他工具，需要验证
            tool_calls = self._extract_tool_calls(args)
            for tool_call in tool_calls:
                if tool_call.name not in allowed_set:
                    raise SecurityError(
                        f"Skill '{skill.name}' attempted to call "
                        f"tool '{tool_call.name}' which is not in allowed-tools: {allowed_set}"
                    )

        # 2. 执行（带资源限制）
        return await self._sandboxed_execute(
            skill=skill,
            args=args,
            context=context,
            timeout=self.timeout,
            max_memory_mb=self.max_memory_mb,
        )

    def _extract_tool_calls(self, args: dict[str, Any]) -> list[ToolCall]:
        """从 args 中提取工具调用

        已知限制：此实现仅检测直接嵌套在 args 中的 tool_calls。
        通过 SkillTool 间接调用的工具不在此检测范围内，
        由 SkillTool.execute() 层面统一验证 allowed-tools。
        """
        tool_calls = []

        # 直接字段
        if "tool_calls" in args:
            tc = args["tool_calls"]
            if isinstance(tc, list):
                tool_calls.extend(tc)
            elif isinstance(tc, dict):
                tool_calls.append(tc)

        # 嵌套在 input 参数中的 tool_calls
        if "input" in args and isinstance(args["input"], dict):
            nested = args["input"].get("tool_calls", [])
            if isinstance(nested, list):
                tool_calls.extend(nested)

        return tool_calls

    async def _sandboxed_execute(
        self,
        skill: SkillDefinition,
        args: dict[str, Any],
        context: ToolContext,
        timeout: float,
        max_memory_mb: int,
    ) -> Any:
        """沙箱执行 Skill（资源受限）

        使用 subprocess + resource limits 实现隔离执行环境。

        Args:
            skill: Skill 定义
            args: Skill 参数
            context: 执行上下文
            timeout: 执行超时（秒）
            max_memory_mb: 最大内存限制（MB）

        Returns:
            Skill 执行结果

        Raises:
            SkillTimeoutError: 执行超时
            SkillMemoryError: 内存超出限制
            SkillExecutionError: 执行失败
        """
        import resource
        import tempfile
        import json

        # 1. 创建临时目录用于 skill 执行
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_script = Path(tmpdir) / "skill_exec.py"
            args_file = Path(tmpdir) / "args.json"
            result_file = Path(tmpdir) / "result.json"

            # 2. 序列化 skill 参数
            args_file.write_text(json.dumps({
                "skill_name": skill.name,
                "args": args,
                "context": {
                    "cwd": context.cwd,
                    "session_id": context.session_id,
                }
            }))

            # 3. 构建执行脚本（安全地加载和执行 skill）
            exec_script = f'''
import sys
import json
import os

# 设置工作目录
with open("{args_file}") as f:
    params = json.load(f)
os.chdir(params["context"]["cwd"])

# 执行 skill 逻辑（从 skill.scripts 目录）
# 此处为占位实现，实际应加载 skill/SKILL.md 并执行
result = {{"status": "success", "output": "Skill executed"}}

with open("{result_file}", "w") as f:
    json.dump(result, f)
'''
            skill_script.write_text(exec_script)

            # 4. 设置资源限制
            max_memory_bytes = max_memory_mb * 1024 * 1024
            soft, hard = resource.getrlimit(resource.RLIMIT_AS)
            resource.setrlimit(resource.RLIMIT_AS, (max_memory_bytes, hard))

            # 设置子进程超时
            import signal

            def timeout_handler(signum, frame):
                raise TimeoutError(f"Skill execution timed out after {timeout}s")

            # 5. 执行
            try:
                # 使用 asyncio.create_subprocess_exec 创建子进程
                process = await asyncio.create_subprocess_exec(
                    sys.executable,
                    str(skill_script),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=tmpdir,
                )

                # 设置超时
                try:
                    await asyncio.wait_for(
                        process.communicate(),
                        timeout=timeout
                    )
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
                    raise SkillTimeoutError(f"Skill execution timed out after {timeout}s")

                # 6. 读取结果
                if result_file.exists():
                    result = json.loads(result_file.read_text())
                    if result["status"] == "success":
                        return result["output"]
                    else:
                        raise SkillExecutionError(result.get("error", "Unknown error"))
                else:
                    raise SkillExecutionError("Skill execution produced no output")

            except asyncio.TimeoutError:
                raise SkillTimeoutError(f"Skill execution timed out after {timeout}s")
            finally:
                # 恢复资源限制
                resource.setrlimit(resource.RLIMIT_AS, (soft, hard))

class SkillRegistry:
    """Skill 注册表 + 自动注册为 Tool"""

    def __init__(self, tool_registry: ToolRegistry):
        self.skills: dict[str, SkillDefinition] = {}
        self.tool_registry = tool_registry

    def discover(self, skills_dir: Path) -> list[SkillDefinition]:
        """发现并加载 skills"""
        discovered = []
        for skill_path in skills_dir.iterdir():
            if skill_path.is_dir() and (skill_path / "SKILL.md").exists():
                skill = self._load_skill(skill_path)
                self.register(skill)
                discovered.append(skill)
        return discovered

    def register(self, skill: SkillDefinition) -> None:
        """注册 Skill 并注册为 Tool"""
        self.skills[skill.name] = skill

        # 自动注册为 Tool
        # 注意：Skills 执行任意代码，使用 ACCEPT_EDITS 而非 AUTO_ACCEPT
        skill_tool = SkillTool(skill, self.executor)
        tool_def = ToolDefinition(
            name=skill_tool.name,
            description=skill_tool.description,
            input_schema=skill_tool.input_schema,
            is_read_only=False,  # Skills may modify files
            permission_required=PermissionLevel.ACCEPT_EDITS,  # 安全权限
        )
        self.tool_registry.register_tool(tool_def, skill_tool.execute)

    def get(self, name: str) -> SkillDefinition | None:
        return self.skills.get(name)

    def list(self) -> list[SkillDefinition]:
        return list(self.skills.values())

    async def execute(
        self,
        skill_name: str,
        args: dict[str, Any],
        context: ToolContext,  # 统一使用 ToolContext
    ) -> Any:
        """执行 Skill"""
        skill = self.get(skill_name)
        if not skill:
            raise ValueError(f"Skill not found: {skill_name}")

        return await self.executor.execute(skill, args, context)
```

---

## 八、MCP 系统

### 8.1 架构

MCP 采用混合模式：
- **MCP Client**：连接外部 MCP Servers
- **FastMCP Server**：通过 FastMCP 暴露本地能力

### 8.2 核心接口

```python
class MCPClient:
    """MCP Client - 连接外部 MCP Servers"""

    async def connect(self, server_config: MCPServerConfig) -> None
    async def disconnect(self) -> None
    async def list_tools(self) -> list[MCPTool]
    async def call_tool(self, tool: MCPTool, args: dict) -> MCPResourceResult
    async def list_resources(self) -> list[MCPResource]
    async def read_resource(self, uri: str) -> str


class MCPServer(FastMCP):
    """MCP Server - 通过 FastMCP 暴露本地能力"""

    @fastmcp.tool()
    async def local_tool(args: dict) -> dict: ...

    @fastmcp.resource("file://{path}")
    async def file_resource(path: str) -> str: ...

    @fastmcp.prompt()
    async def system_prompt() -> str: ...


class MCPRegistry:
    """MCP 客户端 + 服务端统一管理"""

    def __init__(self):
        self.clients: dict[str, MCPClient] = {}
        self.servers: dict[str, MCPServer] = {}
        self._tool_cache: list[MCPTool] = []

    def add_client(self, name: str, client: MCPClient) -> None:
        self.clients[name] = client
        self._tool_cache.clear()  # invalidate cache

    def add_server(self, name: str, server: MCPServer) -> None:
        self.servers[name] = server

    def get_tools(self) -> list[MCPTool]:
        """合并所有客户端工具，支持工具名冲突解决"""
        all_tools: list[MCPTool] = []
        tool_names: dict[str, str] = {}  # tool_name -> server_name

        for server_name, client in self.clients.items():
            try:
                tools = await client.list_tools()
                for tool in tools:
                    # 冲突解决策略：前缀加上 server_name
                    if tool.name in tool_names:
                        original_server = tool_names[tool.name]
                        # 重命名冲突的工具：server_name__original_name
                        tool.name = f"{server_name}__{tool.name}"
                        warnings.warn(
                            f"Tool name collision: '{tool.name}' from {original_server} "
                            f"renamed to '{tool.name}' due to conflict with {server_name}"
                        )
                    else:
                        tool_names[tool.name] = server_name
                    all_tools.append(tool)
            except Exception as e:
                warnings.warn(f"Failed to list tools from {server_name}: {e}")

        return all_tools

    def list_servers(self) -> list[str]:
        return list(self.clients.keys()) + list(self.servers.keys())
```

### 8.3 MCP 配置格式

```json
{
  "mcp_servers": {
    "filesystem": {
      "command": "fastmcp",
      "args": ["run", "/path/to/filesystem-server.py"]
    },
    "git": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-git"]
    }
  },
  "exposed_tools": ["LocalBash", "LocalRead", "LocalEdit"],
  "exposed_resources": ["file://workspace/*"]
}
```

---

## 九、Context 管理（分级压缩）

### 9.1 ContextManager 类

```python
class ContextManager:
    def __init__(self, budget: ContextBudget):
        self.budget = budget
        self.compression_strategy = "none"

    async def should_compress(self, messages: list[Message]) -> bool
    async def compress(
        self,
        messages: list[Message],
        strategy: CompressionStrategy
    ) -> list[Message]
```

### 9.2 压缩策略（4级）

| 策略 | 触发条件 | 操作 |
|------|---------|------|
| `none` | token < 80% budget | 不压缩 |
| `snip` | token > 80% | 截断长消息/代码块 |
| `microcompact` | token > 90% | 合并相邻 tool messages |
| `collapse` | token > 95% | 折叠旧消息为摘要 |

### 9.3 压缩算法（可逆 + 语义化）

```python
@dataclass
class CompressionAnnotation:
    """压缩注解 - 保留压缩元数据"""
    original_ids: list[str]  # 原始消息 ID
    compressed: bool
    compression_type: Literal["snip", "microcompact", "collapse"]
    archive_ref: str | None = None  # 归档引用（collapse 时）
    original_length: int | None = None

@dataclass
class CollapseSummary:
    """Collapse 摘要结构"""
    summary_text: str
    key_points: list[str]
    preserved_fields: list[str]  # 保留的字段
    original_message_ids: list[str]

async def compress_messages(
    messages: list[Message],
    strategy: CompressionStrategy,
    budget: ContextBudget,
    archive_store: ArchiveStore | None = None,  # 归档存储
) -> tuple[list[Message], CompressionAnnotation]:
    if strategy == "snip":
        # 截断超过 500 行的代码块
        # 合并连续的小 tool result（< 50 chars）
        return snip(messages, budget)

    elif strategy == "microcompact":
        # 将 tool calls 和 results 合并为 "Used X: Y" 格式
        # 删除重复的系统提示
        return microcompact(messages, budget)

    elif strategy == "collapse":
        # Pre-collapse checkpoint：在 90% 触发（与 microcompact 同级），确保压缩前可恢复
        if budget.current_tokens / budget.max_tokens > 0.90:
            await _pre_collapse_checkpoint(messages, archive_store)

        # 语义化归档：原始消息存入归档，用指针引用
        archive_ref = await archive_store.archive(
            messages=middle_messages,
            metadata={"strategy": "collapse", "timestamp": now()}
        )

        # 生成摘要
        summary = await _generate_collapse_summary(messages)

        # 返回包含归档引用的压缩消息
        compressed = [
            *first_messages,
            Message(
                role="system",
                content=f"[Archived {len(middle_messages)} messages - archive_ref: {archive_ref}]",
                metadata={"type": "archive_pointer", "archive_ref": archive_ref}
            ),
            Message(
                role="system",
                content=summary.summary_text,
                metadata={"type": "summary", **asdict(summary)}
            ),
            *last_messages,
        ]
        annotation = CompressionAnnotation(
            original_ids=[m.id for m in middle_messages],
            compressed=True,
            compression_type="collapse",
            archive_ref=archive_ref,
        )
        return compressed, annotation
```

**可逆性保证**：
- `snip` 和 `microcompact`：保留原始消息 ID，可通过 archive_ref 恢复
- `collapse`：原始消息存入归档存储（Milvus 或文件），摘要成为归档的索引
- 90% pre-collapse checkpoint：确保压缩前有完整快照

---

## 十、安全/权限体系

### 10.1 Permission 级别（5级 + 预算）

```python
class PermissionLevel(Enum):
    BYPASS = "bypass"      # ⚠️ 完全跳过权限检查，需要双重确认
    AUTO_ACCEPT = "auto"   # 自动批准安全操作
    ACCEPT_EDITS = "accept_edits"  # 自动批准写操作
    PLAN = "plan"          # plan 模式下自动批准
    REVIEW = "review"      # 始终需要用户确认（默认）
    DENY = "deny"          # 阻止所有操作的严格模式（与 rule deny 不同，DENY 是全局默认安全模式）
```

**BYPASS 模式安全要求**：
- 必须显式传入 `--bypass-confirm` 参数
- 所有绕过操作记录到独立审计日志：`audit.log`
- 审计日志包含：时间戳、会话ID、操作、完整上下文
```python
# BYPASS 使用示例
# 正确：带确认标志
config = PermissionConfig(mode=PermissionLevel.BYPASS, bypass_confirm=True)

# 错误：缺少确认标志会抛出异常
config = PermissionConfig(mode=PermissionLevel.BYPASS)
# → SecurityError: "BYPASS mode requires --bypass-confirm"
```

@dataclass
class PermissionContext:
    command: str
    args: dict[str, Any]
    cwd: str
    env: dict[str, str]
    session_budget: PermissionBudget

@dataclass
class PermissionBudget:
    remaining: int
    total: int
    window: timedelta
    tool_name: str
    on_exhaustion: Literal["block", "ask", "fallback"] = "ask"  # 预算耗尽行为

@dataclass
class PermissionResult:
    """权限检查结果"""
    allowed: bool
    reason: str
    matched_rule: PermissionRule | None = None
    denial_reason: Literal["mode_deny", "rule_deny", "budget_exhausted"] | None = None
    # denial_reason 区分拒绝原因，便于审计

class SecurityLayer:
    """安全层 - 支持横切关注点模式"""
    # SecurityLayer 作为横切关注点，可通过装饰器或中间件集成到 ToolExecutor/SkillExecutor
```

### 10.2 SecurityLayer 类

```python
class SecurityLayer:
    def __init__(
        self,
        mode: PermissionLevel,
        rules: list[PermissionRule],
        budgets: list[PermissionBudget],
    ):
        self.mode = mode
        self.rules = rules
        self.budgets = budgets

    async def check(
        self,
        tool: ToolDefinition,
        args: dict[str, Any],
        context: PermissionContext,
    ) -> PermissionResult

    async def check_pattern(
        self,
        pattern: str,
        value: str,
        pattern_type: Literal["glob", "regex"],
    ) -> bool
```

### 10.3 Rule 格式

```python
@dataclass
class PermissionRule:
    tool: str                    # "Bash", "FileEdit", "*"
    pattern: str                 # glob 或 regex
    pattern_type: Literal["glob", "regex"]
    action: Literal["allow", "deny", "ask"]
    priority: int = 0           # 优先级，数字越大优先级越高
    reason: str | None = None
```

### 10.4 规则匹配优先级

**匹配顺序**：
1. 按 `priority` 从高到低排序
2. 同优先级按注册顺序匹配
3. 第一个匹配的规则决定结果

**特殊规则**：
- `tool="*"` 匹配所有工具
- `pattern="*"` 匹配所有值
- `deny` 规则优先级最高，一旦匹配立即拒绝
- 未匹配任何规则时，使用 PermissionLevel 默认行为

**模式匹配实现**：

```python
import fnmatch  # glob 模式
import re        # regex 模式

def match_pattern(pattern: str, value: str, pattern_type: Literal["glob", "regex"]) -> bool:
    """匹配模式实现"""
    if pattern_type == "glob":
        # glob 使用 fnmatch，* 匹配任意字符
        return fnmatch.fnmatch(value, pattern)
    else:  # regex
        return bool(re.match(pattern, value))
```

**示例**：
```python
rules = [
    # 高优先级 deny 规则
    # regex 模式：精确匹配危险命令
    PermissionRule(tool="Bash", pattern="rm -rf /", pattern_type="regex", action="deny", priority=100),
    PermissionRule(tool="Bash", pattern=".*format.*", pattern_type="regex", action="deny", priority=90),

    # glob 模式：通配符匹配命令族
    PermissionRule(tool="Bash", pattern="git *", pattern_type="glob", action="allow", priority=50),
    PermissionRule(tool="Bash", pattern="npm *", pattern_type="glob", action="allow", priority=50),

    # 低优先级 ask 规则（默认）
    PermissionRule(tool="*", pattern="*", pattern_type="glob", action="ask", priority=0),
]
```

### 10.5 权限检查流程

```
ToolCall → Budget Check → Rule Match → PermissionLevel Mode → Result
                    ↓              ↓
              超出预算?       明确 deny?
                    ↓              ↓
              Ask User       Raise PermissionError
```

---

## 十一、State 持久化（分层架构）

### 11.1 StateStore 类

```python
class StateStore:
    def __init__(
        self,
        checkpoint_path: Path,
        checkpoint_interval: int = 60,
        snapshot_interval: int = 100,  # 每 N 个 checkpoint 做一次快照
    ):
        self._memory: dict[str, Any] = {}
        self._checkpoint_path = checkpoint_path
        self._checkpoint_interval = checkpoint_interval
        self._snapshot_interval = snapshot_interval
        self._checkpoint_count = 0
        self._subscribers: list[Callable[[], None]] = []
        self._wal_path = checkpoint_path.with_suffix(".wal")  # 预写日志

    # 内存操作（同步，线程安全）
    def get(self, key: str) -> Any
    def set(self, key: str, value: Any) -> None
    def update(self, updater: Callable[[dict], dict]) -> None  # 事务性更新

    # 订阅
    def subscribe(self, listener: Callable[[], None]) -> Callable[[], None]

    # Checkpoint（异步，定期）
    async def checkpoint(self) -> None:
        """执行 checkpoint，包含 WAL 机制"""

    async def restore(self) -> None:
        """恢复协议：
        1. 找最新 .snap.json
        2. 加载快照
        3. 找该快照之后的最新 .jl
        4. 重放增量
        """

    async def _create_snapshot(self) -> None:
        """创建快照并截断增量日志"""
        # 每 N 个 checkpoint 写一次完整快照
        pass

    async def _write_wal(self, change: StateChange) -> None:
        """预写日志，确保崩溃可恢复"""
        pass
```

### 11.2 Checkpoint 格式和恢复协议

**文件格式**：
- `state.jl` - 增量 JSON Lines
- `state.snap.json` - 完整快照
- `state.wal` - 预写日志

**恢复算法**：
```python
async def restore(self) -> None:
    # 1. 找最新快照
    snap_files = list(self._checkpoint_path.glob("*.snap.json"))
    if not snap_files:
        return  # 无快照，无法恢复

    latest_snap = max(snap_files)
    snap_ts = self._parse_timestamp(latest_snap)

    # 2. 加载快照
    self._memory = self._load_json(latest_snap)

    # 3. 找快照之后的增量
    jl_files = [
        f for f in self._checkpoint_path.glob("*.jl")
        if self._parse_timestamp(f) > snap_ts
    ]

    # 4. 重放增量（按时间顺序）
    for jl_file in sorted(jl_files):
        for line in jl_file:
            if line:
                change = json.loads(line)
                self._apply_change(change)

    # 5. 清理已合并的增量文件
    for f in jl_files:
        f.unlink()
```

### 11.3 AppState 结构

```python
@dataclass
class AppState:
    # Session 状态
    messages: list[Message]
    current_task_id: str | None
    current_agent_id: str | None

    # 持久化状态
    tasks: dict[str, Task]
    agents: dict[str, Agent]
    session_history: list[Session]
    budgets: dict[str, PermissionBudget]

    # 配置
    settings: Settings
    mcp_config: MCPServersConfig

    # 安全
    permission_mode: PermissionLevel
    permission_rules: list[PermissionRule]
```

---

## 十二、流式输出架构 (Streaming)

> **v1.4 新增** — 基于代码审查反馈全面重构流式输出设计。

### 12.1 设计原则

**抽象选择**：采用 `AsyncGenerator` 作为主要流式输出抽象，辅以 `asyncio.Queue` 作为内部缓冲。

| 方案 | 优势 | 劣势 | 决策 |
|------|------|------|------|
| EventEmitter | 解耦、多订阅者 | 类型不安全、无 yield 语义、emit_to_all 有 bug | 不采用 |
| asyncio.Queue | 天然背压、生产/消费解耦 | 需要单独消费者协程 | 内部缓冲用 |
| **AsyncGenerator** | 原生 async/await、类型安全、backpressure 内置 | 单消费者 | **主抽象** |
| 专用协议 | 外部兼容性好 | 过度工程 | 按需适配器层 |

**Streaming 定位**：Streaming 是 Agent 执行的外层包装（Middleware/Wrapper），而非内嵌于 Agent 核心。这样：
- Agent 核心保持纯同步/异步函数语义
- Streaming 层通过 `run_streaming()` 包装 `run()`，按需启用
- 支持同一 Agent 实例切换流式/非流式模式

### 12.2 StreamEvent 标准 Schema

所有流式事件遵循统一 schema，支持外部消费者（webhooks、web UI）和分布式追踪：

```python
from dataclasses import dataclass, field
from typing import Any, Literal
from datetime import datetime

@dataclass
class StreamEvent:
    """统一流式事件 Schema（v1.4）

    设计目标：
    - 外部消费者兼容（webhooks、web UI、SSE）
    - 分布式追踪支持（agent_id、trace_id、span_id）
    - 可序列化（JSON via dataclasses.asdict）
    """
    # --- 标识字段 ---
    type: str                                   # 事件类型（非 Literal，便于扩展）
    timestamp: datetime = field(default_factory=datetime.now)
    agent_id: str | None = None                 # 来源 Agent ID（分布式追踪）
    trace_id: str | None = None                 # 全局 Trace ID（跨 Agent 关联）
    span_id: str | None = None                  # 当前 Span ID

    # --- 事件负载 ---
    content: Any = None                         # 事件数据（类型依 type 而定）

    # --- 元数据 ---
    seq: int = 0                                # 全局递增序号（保证顺序）
    is_final: bool = False                      # 是否为最终事件

    def to_dict(self) -> dict:
        """序列化为 dict（兼容 JSON，供 SSE/WebSocket 使用）"""
        import dataclasses
        d = dataclasses.asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d


# === 核心事件类型 ===

@dataclass
class TextDeltaEvent(StreamEvent):
    """文本增量事件"""
    type: Literal["text_delta"] = "text_delta"
    content: str = ""                           # 增量文本片段


@dataclass
class ToolCallStartEvent(StreamEvent):
    """Tool 调用开始事件（仅在 Tool 调用发起时发送一次）"""
    type: Literal["tool_call_start"] = "tool_call_start"
    content: dict = field(default_factory=dict)  # {"name": str, "input": dict, "call_id": str}


@dataclass
class ToolCallDeltaEvent(StreamEvent):
    """Tool 调用增量事件（流式 JSON 输入）"""
    type: Literal["tool_call_delta"] = "tool_call_delta"
    content: dict = field(default_factory=dict)  # {"call_id": str, "input_json_delta": str}


@dataclass
class ToolCallEndEvent(StreamEvent):
    """Tool 调用结束事件"""
    type: Literal["tool_call_end"] = "tool_call_end"
    content: dict = field(default_factory=dict)  # {"call_id": str, "name": str}


@dataclass
class ToolResultEvent(StreamEvent):
    """Tool 执行结果事件（必须在 tool_call_end 之后）"""
    type: Literal["tool_result"] = "tool_result"
    content: dict = field(default_factory=dict)  # {"call_id": str, "output": Any, "error": str | None}


@dataclass
class StepStartEvent(StreamEvent):
    """Step 开始事件"""
    type: Literal["step_start"] = "step_start"
    content: dict = field(default_factory=dict)  # {"step": int, "reason": str}


@dataclass
class StepCompleteEvent(StreamEvent):
    """Step 完成事件"""
    type: Literal["step_complete"] = "step_complete"
    content: dict = field(default_factory=dict)  # {"step": int, "tool_calls": list, "token_usage": dict}


@dataclass
class TokenUsageEvent(StreamEvent):
    """Token 使用量事件（每次 LLM 响应结束时发送）"""
    type: Literal["token_usage"] = "token_usage"
    content: dict = field(default_factory=dict)  # {"prompt_tokens": int, "completion_tokens": int, "total_tokens": int}


@dataclass
class HeartbeatEvent(StreamEvent):
    """心跳事件（长任务保活）"""
    type: Literal["heartbeat"] = "heartbeat"
    content: dict = field(default_factory=dict)  # {"alive_seconds": int, "active_agent_id": str | None}


@dataclass
class StreamStartEvent(StreamEvent):
    """流开始事件"""
    type: Literal["stream_start"] = "stream_start"
    content: dict = field(default_factory=dict)  # {"agent_id": str, "trace_id": str, "model": str}


@dataclass
class StreamEndEvent(StreamEvent):
    """流结束事件"""
    type: Literal["stream_end"] = "stream_end"
    content: dict = field(default_factory=dict)  # {"reason": str, "termination_reason": str | None, "total_steps": int}


@dataclass
class ErrorEvent(StreamEvent):
    """错误事件"""
    type: Literal["error"] = "error"
    content: dict = field(default_factory=dict)  # {"error": str, "recoverable": bool, "retry_count": int}
```

**事件顺序保证**：
```
stream_start → step_start → [text_delta...] → tool_call_start → tool_call_delta...
    → tool_call_end → tool_result → ... → step_complete → [下一 step]
    → ... → token_usage → stream_end
```
关键规则：`tool_result` 必须在 `tool_call_end` 之后发送。

### 12.3 AgentStreamer（主抽象）

```python
import asyncio
import uuid
from dataclasses import asdict
from typing import AsyncGenerator, Callable, Any

class AgentStreamer:
    """流式输出包装器（Middleware/Wrapper 模式）

    设计决策：
    - 作为 Agent.run() 的外层包装，不修改 Agent 核心逻辑
    - 使用 AsyncGenerator 作为主输出抽象（内置 backpressure）
    - 内部使用 asyncio.Queue 作为生产者/消费者缓冲
    - 所有事件通过 asyncio.Queue 分发，yield 时触发消费

    使用方式：
        async for event in agent.run_streaming():
            await transport.send(event)

    背压机制：
        生产者（LLM 响应）速率 > 消费者（网络传输）速率时，
        Queue.put() 会阻塞，直到消费者通过 yield 消费了部分事件。
    """

    def __init__(
        self,
        agent: Agent,
        buffer_size: int = 100,      # Queue 缓冲上限（背压阈值）
        heartbeat_interval: float = 30.0,  # 心跳间隔（秒）
        enable_heartbeat: bool = True,
    ):
        self.agent = agent
        self.buffer_size = buffer_size
        self.heartbeat_interval = heartbeat_interval
        self.enable_heartbeat = enable_heartbeat

        # 运行时状态
        self._queue: asyncio.Queue[StreamEvent] = asyncio.Queue(maxsize=buffer_size)
        self._seq: int = 0                        # 全局事件序号
        self._step_count: int = 0
        self._running: bool = False
        self._closed: bool = False
        self._trace_id: str = str(uuid.uuid4())  # 全局 trace ID
        self._start_time: float = 0.0

        # 订阅者（EventEmitter 模式，但简化且正确）
        self._listeners: dict[str, list[Callable[[StreamEvent], None]]] = {}
        self._lock = asyncio.Lock()               # 线程安全保护

    # === AsyncGenerator 接口 ===

    def run_streaming(self) -> AsyncGenerator[StreamEvent, None]:
        """流式运行 Agent（必须是 async generator，用 yield 产出事件）

        Returns:
            AsyncGenerator[StreamEvent, None]: 事件流

        Raises:
            RuntimeError: 如果流已经在运行

        注意：
            这是真正的 async generator，必须用 `async for` 消费。
            错误用法：`result = agent.run_streaming()` — 这样不会产出任何事件。
        """
        if self._running:
            raise RuntimeError("Stream already running")
        if self._closed:
            raise RuntimeError("Stream has been closed")

        self._running = True
        self._start_time = asyncio.get_event_loop().time()
        self._seq = 0
        self._step_count = 0

        try:
            # 启动后台生产者协程（在事件循环中启动）
            producer_task = asyncio.create_task(self._run_agent())

            # 可选：启动心跳协程
            if self.enable_heartbeat:
                heartbeat_task = asyncio.create_task(self._heartbeat_loop())

            # 消费队列中的事件并 yield
            chunk: StreamEvent | None = None
            while not self._closed:
                try:
                    chunk = await asyncio.wait_for(
                        self._queue.get(),
                        timeout=1.0,
                    )
                except asyncio.TimeoutError:
                    # 超时不意味着结束，检查是否真的结束了
                    if self._closed or (producer_task.done() and self._queue.empty()):
                        break
                    continue

                # yield 事件给消费者（触发背压：consumer 消费速度决定吞吐量）
                yield chunk

            # 确保生产者完成
            if not producer_task.done():
                producer_task.cancel()
                try:
                    await producer_task
                except asyncio.CancelledError:
                    pass

            # 取消心跳
            if self.enable_heartbeat and not heartbeat_task.done():
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass

        finally:
            self._running = False

    async def _run_agent(self) -> None:
        """后台协程：运行 Agent 并将事件放入队列"""
        try:
            # stream_start 事件
            await self._emit(StreamStartEvent(
                agent_id=self.agent.id,
                trace_id=self._trace_id,
                content={"model": getattr(self.agent, "model", "unknown")},
            ))

            # 运行 Agent 主循环（伪代码，适配实际 Agent.run()）
            async for chunk in self.agent.run():
                event = self._parse_chunk_to_event(chunk)
                if event:
                    await self._emit(event)

                    # Token 预算检查（仅在 step 结束时）
                    if isinstance(event, StepCompleteEvent):
                        await self._check_token_budget(event)

            # stream_end 事件
            await self._emit(StreamEndEvent(
                is_final=True,
                content={
                    "reason": "completed",
                    "termination_reason": "normal",
                    "total_steps": self._step_count,
                },
            ))

        except Exception as e:
            await self._emit(ErrorEvent(
                content={"error": str(e), "recoverable": False, "retry_count": 0},
            ))
            await self._emit(StreamEndEvent(
                is_final=True,
                content={"reason": "error", "termination_reason": "error", "total_steps": self._step_count},
            ))
        finally:
            self._closed = True

    async def _heartbeat_loop(self) -> None:
        """心跳协程：定期发送心跳事件防止连接超时"""
        while not self._closed:
            await asyncio.sleep(self.heartbeat_interval)
            if not self._closed:
                elapsed = asyncio.get_event_loop().time() - self._start_time
                await self._emit(HeartbeatEvent(
                    content={"alive_seconds": int(elapsed), "active_agent_id": self.agent.id},
                ))

    async def _emit(self, event: StreamEvent) -> None:
        """发送事件到队列（线程安全）"""
        self._seq += 1
        event.seq = self._seq

        # 背压：当队列满时，put 会阻塞直到消费者消费
        try:
            await asyncio.wait_for(
                self._queue.put(event),
                timeout=30.0,  # 防止无限等待
            )
        except asyncio.TimeoutError:
            # 背压超时：记录丢弃事件
            await self._emit(ErrorEvent(
                content={"error": "Backpressure timeout: queue full", "recoverable": True, "retry_count": 0},
            ))

        # 通知订阅者（非阻塞，防止订阅者阻塞主流程）
        asyncio.create_task(self._notify_listeners(event))

    async def _notify_listeners(self, event: StreamEvent) -> None:
        """通知订阅者（带错误隔离）"""
        async with self._lock:
            listeners = list(self._listeners.get(event.type, []))
            wildcard = list(self._listeners.get("*", []))

        for cb in listeners + wildcard:
            try:
                await cb(event)
            except Exception:
                # 错误隔离：一个订阅者异常不影响其他订阅者
                pass

    def _parse_chunk_to_event(self, chunk: Any) -> StreamEvent | None:
        """将 LLM 流式 chunk 转换为 StreamEvent"""
        if chunk is None:
            return None

        if hasattr(chunk, "content") and isinstance(getattr(chunk, "content", ""), str):
            return TextDeltaEvent(content=chunk.content)

        if hasattr(chunk, "tool_calls") and chunk.tool_calls:
            # tool_calls 到达，发送 tool_call_start（仅一次，不在循环外重复发送）
            tc = chunk.tool_calls[0]
            return ToolCallStartEvent(
                content={"name": tc.name, "input": tc.input, "call_id": tc.id},
            )

        if hasattr(chunk, "usage") and chunk.usage:
            return TokenUsageEvent(content=asdict(chunk.usage))

        return None

    async def _check_token_budget(self, step_event: StepCompleteEvent) -> None:
        """Token 预算检查（文档限制：仅 step 结束时检查）"""
        usage = step_event.content.get("token_usage", {})
        total = usage.get("total_tokens", 0)
        budget = getattr(self.agent, "max_tokens", float("inf"))
        if total > budget:
            await self._emit(ErrorEvent(
                content={"error": "Token budget exceeded", "recoverable": False, "retry_count": 0},
            ))

    # === 订阅者管理 ===

    def on(
        self,
        event_type: str,
        callback: Callable[[StreamEvent], None],
    ) -> Callable[[], None]:
        """订阅特定事件类型（返回取消订阅函数）

        Args:
            event_type: 事件类型（如 "text_delta", "*" 表示全部）
            callback: 回调函数（可为 async 或 sync）

        Returns:
            取消订阅函数，调用后移除该订阅

        注意：
            - 订阅者在消费者抛出异常时不会影响流
            - 如果消费者崩溃，订阅者需要自行清理引用以避免内存泄漏
            - 建议在消费流时使用 `async with streamer` 或 try/finally 确保清理
        """
        async with self._lock:
            if event_type not in self._listeners:
                self._listeners[event_type] = []
            self._listeners[event_type].append(callback)

        def unsubscribe():
            async with self._lock:
                if event_type in self._listeners:
                    try:
                        self._listeners[event_type].remove(callback)
                    except ValueError:
                        pass

        return unsubscribe

    def remove_all_listeners(self, event_type: str | None = None) -> None:
        """移除订阅者

        Args:
            event_type: 指定类型则只移除该类型；为 None 则移除所有
        """
        async with self._lock:
            if event_type is None:
                self._listeners.clear()
            elif event_type in self._listeners:
                self._listeners[event_type].clear()

    async def close(self) -> None:
        """关闭流，清理所有资源"""
        self._closed = True
        async with self._lock:
            self._listeners.clear()
        # 清空队列
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    def is_active(self) -> bool:
        """检查流是否正在运行"""
        return self._running and not self._closed
```

**关键修复（对应 reviewer 反馈）**：
- `run_streaming()` 是真正的 `AsyncGenerator`，包含 `yield` 语句
- `tool_call_start` 仅在 `tool_calls` 首次到达时发送一次，不再在循环外重复
- `chunk = None` 在循环前初始化，防止空响应时的 `NameError`
- Token 追踪仅在 `step_complete` 时检查（文档化限制）
- `STEP_COMPLETE` 在 `step_count += 1` **之后**才发送，确保序号正确
- 事件顺序：`tool_call_end` 必定在 `tool_result` 之前
- 添加 `close()`, `remove_all_listeners()`, `is_active()` 方法
- 使用 `asyncio.Lock` 保护 `_listeners` 字典
- 订阅者错误隔离：`try/except` 包裹每个回调调用
- 添加 `TOKEN_USAGE`、`TERMINATION_REASON`、`HEARTBEAT` 事件类型
- `emit_to_all()` 模式已废弃，改为正确的 `on()` 订阅者 API

### 12.4 多 Agent 流式架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    传输层 (Transport)                            │
│         ┌─────────────┬─────────────┬─────────────┐            │
│         │  SSE Adapter │ WS Adapter  │ Polling Adapter│          │
│         └─────────────┴─────────────┴─────────────┘            │
├─────────────────────────────────────────────────────────────────┤
│                  AgentStreamer (每个 Agent 一个)                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Orchestr. │  │ SubAgent1│  │ SubAgent2│  │ SubAgent3│       │
│  │ Streamer  │  │ Streamer │  │ Streamer  │  │ Streamer  │       │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘       │
│        │               │               │               │            │
│        │  aggregate    │  fan_out      │  fan_out      │            │
│        ▼               │               │               │            │
│  ┌─────────────┐       │               │               │            │
│  │ Orchestrator│◄──────┴───────────────┴───────────────┘            │
│  │ Aggregator  │   SubAgent streams 仅流向 Orchestrator              │
│  │ (可选)       │   不直接暴露给外部消费者                              │
│  └──────┬──────┘                                                      │
│         │ filtered events (不含 SubAgent 内部细节)                     │
│         ▼                                                              │
│  ┌─────────────────┐                                                  │
│  │ FanOut Router   │  → 可以将同一个事件发给多个消费者                   │
│  │ (订阅 + 转发)   │    但每个 SubAgent stream 独立路由                │
│  └─────────────────┘                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Orchestrator 聚合策略**：
- Orchestrator 流只暴露**自己的**事件（任务调度、Agent 协调）
- SubAgent 的流通过 `AgentStreamer.on("*", callback)` 内部订阅
- Orchestrator 可选择性地将 SubAgent 事件**转换+转发**为统一事件（不过滤内容）
- 对外部消费者：Orchestrator 的流是主要接口，SubAgent 流仅内部可见

**Fan-out 机制**：
```python
class FanOutRouter:
    """一对多事件路由（支持多个消费者订阅同一流）"""

    def __init__(self, streamer: AgentStreamer):
        self.streamer = streamer
        self._consumers: list[AsyncGenerator[StreamEvent, None]] = []

    def subscribe(self, consumer: AsyncGenerator[StreamEvent, None]) -> None:
        """注册一个消费者（消费者本身负责迭代流）"""
        self._consumers.append(consumer)

    async def broadcast(self, event: StreamEvent) -> None:
        """将事件广播给所有订阅者（fan-out）"""
        # 每个 consumer 通过其自身的 AsyncGenerator 迭代获取事件
        # FanOutRouter 不直接传递事件，而是让消费者自己订阅 streamer
        pass
```

### 12.5 传输层适配器

```python
from abc import ABC, abstractmethod

class StreamTransport(ABC):
    """流式传输抽象（适配 SSE/WebSocket/Webhook）"""

    @abstractmethod
    async def send(self, event: StreamEvent) -> None:
        """发送单个事件"""
        pass

    @abstractmethod
    async def close(self) -> None:
        """关闭连接"""
        pass


class SSETransport(StreamTransport):
    """SSE 传输适配器"""

    def __init__(self, response: Any, buffer_size: int = 50):
        self.response = response
        self.buffer_size = buffer_size
        self._buffer: list[StreamEvent] = []
        self._closed = False

    async def send(self, event: StreamEvent) -> None:
        if self._closed:
            return
        data = f"event: {event.type}\ndata: {json.dumps(event.to_dict())}\n\n"
        await self.response.write(data.encode())

    async def close(self) -> None:
        self._closed = True
        await self.response.write(b"event: close\ndata: {}\n\n")


class WebSocketTransport(StreamTransport):
    """WebSocket 传输适配器"""

    def __init__(self, websocket: Any):
        self.ws = websocket
        self._closed = False

    async def send(self, event: StreamEvent) -> None:
        if self._closed:
            return
        await self.ws.send(json.dumps(event.to_dict()))

    async def close(self) -> None:
        self._closed = True
        await self.ws.close()
```

### 12.6 生命周期与订阅清理

**订阅生命周期**：
```
1. 创建 AgentStreamer
2. 调用 streamer.on(event_type, callback) 注册订阅
3. 使用 async for event in streamer.run_streaming() 消费事件
4. 流结束时（stream_end 事件或异常）：
   - 自动触发 streamer.close()
   - close() 清空队列 + 移除所有订阅者
5. 消费者负责在退出前调用 await streamer.close()（使用 try/finally）
```

**资源清理（推荐用法）**：
```python
streamer = AgentStreamer(agent)

async with streamer:
    async for event in streamer.run_streaming():
        await transport.send(event)
# with 块退出时自动调用 streamer.close()
```

**消费者崩溃时的内存泄漏防护**：
- 订阅者在 `close()` 时被显式清空
- 避免在订阅回调中持有大对象引用
- `remove_all_listener(event_type)` 允许按类型清理

### 12.7 与其他系统的集成

**与 State Sync（Section 3）集成**：
- `StreamEvent` 复用 `StateChange` 的发布订阅基础设施
- 重大状态变更（task_update, agent_update）通过 `StatePublisher` 广播
- 流式输出（text_delta）走独立通道（SSE/WebSocket），避免状态同步通道拥堵
- `stream_end` 事件触发 StateStore 的 checkpoint

**与 Memory（Section 14）集成**：
- `stream_end` 事件触发 `Agent.memorize()` — 保存执行摘要
- `TokenUsageEvent` 用于更新会话级别的 token 预算
- 记忆存储是异步的，不阻塞流式输出

**与 Observability（Section 15）集成**：
- 每个 `StreamEvent` 携带 `trace_id` 和 `span_id`
- 流事件自动创建 Span（`span_create` → `span_end`）
- 关键事件类型自动导出到 OTLP：
  - `step_complete` → 导出 step 耗时
  - `tool_result` → 导出 tool 调用时长
  - `error` → 导出错误 Span
- Phoenix Evaluator 可基于 `StreamEvent` 序列进行实时评估

### 12.8 Review 记录

| Reviewer | 日期 | 主要问题 |
|----------|------|---------|
| Reviewer 1 (Technical) | 2026-04-03 | run_streaming() 非 generator（无 yield）、TOOL_CALL_START 重复发送、空响应 NameError、Token 追踪时机 |
| Reviewer 2 (Architecture) | 2026-04-03 | emit_to_all() 逻辑错误、AsyncGenerator 返回类型错误、STEP_COMPLETE 序号错误、缺少 close()/remove_all_listeners()、事件顺序错误、线程安全问题、订阅生命周期泄漏 |

---

## 十三、Session 管理

### 13.1 Session 定义

```python
@dataclass
class Session:
    id: str                        # UUID
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any]        # user_id, project_path, etc.

    # 状态
    status: Literal["active", "paused", "completed", "archived"]

    # 关联数据
    task_ids: list[str]            # 属于此 session 的 tasks
    agent_ids: list[str]           # 属于此 session 的 agents
    message_thread_id: str | None  # 外部 thread ID（如适用）

    # 统计
    token_usage: TokenUsage
    tool_calls: int
    errors: int

@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0

class SessionManager:
    def __init__(self, state_store: StateStore):
        self.state_store = state_store

    async def create(self, metadata: dict[str, Any]) -> Session
    async def get(self, session_id: str) -> Session | None
    async def update(self, session_id: str, updates: dict) -> Session
    async def list(self, status: str | None = None) -> list[Session]
    async def archive(self, session_id: str) -> None
```

---

## 十四、Memory 系统（Mem0 + Milvus）

### 14.1 Memory 配置

```python
@dataclass
class MemoryConfig:
    provider: Literal["mem0"] = "mem0"
    vector_store: Literal["milvus"] = "milvus"  # 使用 Milvus
    milvus_uri: str = "http://localhost:19530"  # Milvus 连接地址
    collection_name: str = "agent_memory"
    embed_model: str = "all-MiniLM-L6-v2"  # 可配置
    dimensions: int = 384
    # 生命周期配置
    max_memories_per_user: int = 1000
    default_ttl_days: int | None = None  # None = 不过期
    eviction_policy: Literal["lru", "semantic"] = "lru"
    # Chunking 配置
    chunk_size: int = 512
    chunk_overlap: int = 64
```

### 14.2 MemoryStore 类

```python
import re

class MemoryStore:
    def __init__(self, config: MemoryConfig):
        self.config = config
        self.client = Mem0Client(config)
        self.vector_store = MilvusClient(config.milvus_uri)  # 使用 Milvus
        # 生命周期管理
        self._lru_cache: dict[str, datetime] = {}  # memory_id -> last_accessed
        self._eviction_policy = EvictionPolicy.LRU

    async def add(
        self,
        content: str,
        user_id: str,
        metadata: dict[str, Any] | None = None,
        chunk_size: int = 512,  # chunking 配置
        chunk_overlap: int = 64,
    ) -> str:  # returns memory_id
        # 1. 自动 chunking 长内容
        chunks = self._chunk_text(content, chunk_size, chunk_overlap)

        # 2. 存储到向量数据库
        memory_id = await self.client.add(
            text=content,
            user_id=user_id,
            metadata={
                **metadata,
                "embed_model": self.config.embed_model,
                "embed_dimensions": self.config.dimensions,
            }
        )

        # 3. 驱逐检查
        await self._check_eviction(user_id)

        return memory_id

    async def search(
        self,
        query: str,
        user_id: str,
        limit: int = 10,
        filters: dict | None = None,
    ) -> list[MemoryResult]

    async def get(self, memory_id: str) -> MemoryResult | None
    async def update(self, memory_id: str, content: str) -> None
    async def delete(self, memory_id: str) -> None
    async def list_by_user(self, user_id: str, limit: int = 100) -> list[MemoryResult]

    async def _check_eviction(self, user_id: str) -> None:
        """检查并执行驱逐策略"""
        count = await self.client.count(user_id)
        if count > self.config.max_memories_per_user:
            # LRU 驱逐
            victims = await self.client.get_oldest(
                user_id=user_id,
                limit=count - self.config.max_memories_per_user
            )
            for victim in victims:
                await self.client.delete(victim.id)

    def _chunk_text(self, text: str, chunk_size: int, overlap: int) -> list[str]:
        """语义分块

        实现策略：
        1. 优先按段落（空行）分割
        2. 段落过大时按句子分割
        3. 保留重叠区域以维持上下文连续性
        """
        # 按段落分割
        paragraphs = re.split(r'\n\s*\n', text)
        chunks = []
        current = ""
        overlap_text = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # 如果单个段落就超过 chunk_size，需要进一步分割
            if len(para) > chunk_size:
                # 先保存当前 chunk
                if current:
                    chunks.append(current.strip())
                    overlap_text = current[-overlap:] if len(current) > overlap else current
                    current = ""

                # 按句子分割大段落
                sentences = re.split(r'(?<=[.!?])\s+', para)
                for sent in sentences:
                    if len(current) + len(sent) <= chunk_size:
                        current += sent + " "
                    else:
                        if current:
                            chunks.append(current.strip())
                            overlap_text = current[-overlap:] if len(current) > overlap else current
                        current = sent + " "
            else:
                # 普通段落，检查是否需要换 chunk
                if len(current) + len(para) + 1 <= chunk_size:
                    current += para + "\n\n"
                else:
                    if current:
                        chunks.append(current.strip())
                        overlap_text = current[-overlap:] if len(current) > overlap else current
                    current = para + "\n\n"

        # 处理最后一个 chunk
        if current.strip():
            chunks.append(current.strip())

        return chunks if chunks else [text]  # 最小单元：原文返回

@dataclass
class MemoryResult:
    id: str
    content: str
    score: float              # similarity score
    metadata: dict[str, Any]
    created_at: datetime
    # 嵌入兼容性验证
    embed_model: str | None = None  # 验证是否匹配
    embed_dimensions: int | None = None

### 14.3 Memory 与 Agent 的集成

```python
class Agent:
    @property
    def memory(self) -> MemoryStore:
        return self._memory_store

    async def recall(self, query: str, limit: int = 5) -> list[MemoryResult]:
        """根据查询召回相关记忆"""
        return await self._memory_store.search(
            query=query,
            user_id=self.id,
            limit=limit,
        )

    async def memorize(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """存储新记忆"""
        return await self._memory_store.add(
            content=content,
            user_id=self.id,
            metadata=metadata,
        )
```

### 14.4 Agent Memory 调用时机

**何时调用 `recall()`：**
- Agent 收到新任务时，搜索相关历史经验
- 用户提出模糊/不完整需求时，搜索上下文
- 任务失败后，搜索类似成功案例参考
- 每个对话开始时，召回项目相关信息

**何时调用 `memorize()`：**
- 任务完成时，记录成功经验（包含任务描述、解决方案）
- 任务失败时，记录失败原因和教训
- 用户明确提供关键信息时
- 发现重要 bug 或解决方案时
- Session 结束时，汇总重要交互

**Memory Tool**：Agent 也可以通过调用 `RecallMemory` / `StoreMemory` Tool 来操作记忆，这些是内置的系统 Tool。

### 14.5 Memory 与 Context Compression 集成

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
│   Agent      │     │ ContextManager  │     │ MemoryStore  │
└──────┬───────┘     └────────┬─────────┘     └──────┬───────┘
       │                      │                      │
       │ 1. 收到新任务         │                      │
       │──────────────────────►│                      │
       │                      │                      │
       │                      │ 2. recall() 查询相关记忆 │
       │                      │──────────────────────►│
       │                      │                      │
       │                      │ 3. 返回相关记忆        │
       │                      │◄──────────────────────│
       │                      │                      │
       │ 4. 压缩前，memorize() │                      │
       │   重要交互             │                      │
       │◄──────────────────────│                      │
       │                      │                      │
       │                      │ 5. 压缩消息（不含 Memory）│
       │                      │    - snip/microcompact │
       │                      │    - collapse 时归档    │
       │                      │                      │
       │                      │ 6. 压缩不影响 Memory   │
       │                      │    存储                 │
       │                      │                      │
```

**关键点**：
- `recall()` 在压缩前发生，确保 Agent 能访问历史上下文
- `memorize()` 在压缩前调用，保存重要交互
- 压缩只影响 Context 中的 messages，不影响 MemoryStore
- collapse 归档的消息与 Memory 是两个独立存储

#### 14.6 内置 Memory Tools（自动注册）

```python
TOOLS = [
    ToolDefinition(
        name="RecallMemory",
        description="Search past experiences and knowledge",
        input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
        permission_required=PermissionLevel.AUTO_ACCEPT,
    ),
    ToolDefinition(
        name="StoreMemory",
        description="Store important information for later retrieval",
        input_schema={"type": "object", "properties": {"content": {"type": "string"}, "metadata": {"type": "object"}}},
        permission_required=PermissionLevel.AUTO_ACCEPT,
    ),
]
```

---

## 十五、观测与评估系统（Phoenix + OpenTelemetry）

### 15.1 架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Phoenix Server                          │
│  (OTLP Receiver → Trace Store → Span Index → Query API)      │
├─────────────────────────────────────────────────────────────┤
│                    Phoenix Client                            │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │ AutoInstr. │  │ Manual Spans │  │  Eval Runners       │  │
│  │ (OTLP)     │  │ (Phoenix SDK)│  │  (arize-phoenix-evals)│  │
│  └─────────────┘  └──────────────┘  └────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↑
                            │ OTLP (gRPC/HTTP)
                            │
┌─────────────────────────────────────────────────────────────┐
│                   src_py Application                         │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │ Trace Export │  │ Span Manager │  │  Eval Evaluator    │  │
│  └──────────────┘  └──────────────┘  └────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 15.2 核心实现

```python
class ObservabilityManager:
    def __init__(self, phoenix_endpoint: str):
        self.tracer = trace.get_tracer(__name__)
        self.phoenix_client = PhoenixClient(endpoint=phoenix_endpoint)
        self.span_processors: list[SpanProcessor] = []
        self._observers: dict[str, Callable[[dict], None]] = {}

    def observe(self, event_type: str, callback: Callable[[dict], None]) -> Callable[[], None]:
        """注册观察者

        Returns:
            取消订阅的回调函数
        """
        self._observers[event_type] = callback

        def unsubscribe():
            self._observers.pop(event_type, None)

        return unsubscribe

    def _notify_observers(self, event_type: str, data: dict) -> None:
        """通知观察者"""
        if event_type in self._observers:
            self._observers[event_type](data)

    async def trace_agent(self, agent: Agent) -> None
    async def trace_tool_call(
        self,
        tool: ToolDefinition,
        args: dict,
        result: Any,
        duration_ms: float,
    ) -> None
    async def trace_task(self, task: Task) -> None
    async def evaluate(
        self,
        evaluation_name: str,
        input_text: str,
        output_text: str,
        expected_output: str | None = None,
    ) -> EvaluationResult
```

### 15.3 预定义的 Trace Span 类型

| Span 类型 | 说明 |
|----------|------|
| `agent.created` | Agent 创建 |
| `agent.message.sent` | Agent 发送消息 |
| `agent.message.received` | Agent 接收消息 |
| `task.created` | Task 创建 |
| `task.started` | Task 开始执行 |
| `task.completed` | Task 完成 |
| `task.failed` | Task 失败 |
| `task.dependency.wait` | Task 等待依赖 |
| `tool.called` | Tool 被调用 |
| `tool.succeeded` | Tool 执行成功 |
| `tool.failed` | Tool 执行失败 |
| `context.compressed` | Context 被压缩 |
| `context.token_count` | Token 计数 |
| `skill.activated` | Skill 被激活 |
| `skill.completed` | Skill 完成 |

### 15.4 Evaluation 配置

```python
@dataclass
class EvalConfig:
    name: str
    eval_template: str
    model: str  # 用于评判的 LLM
    criteria: list[EvalCriterion]

@dataclass
class EvalCriterion:
    name: str
    prompt_template: str
    passing_score: float
```

---

## 十六、日志与配置规范

### 16.1 日志规范

```python
import logging
from enum import Enum

class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class Logger:
    """统一日志接口"""

    # 日志格式
    FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    # 日志级别环境变量
    LOG_LEVEL_ENV = "SRC_PY_LOG_LEVEL"

    # 日志输出
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._setup()

    def _setup(self) -> None:
        level = os.getenv(self.LOG_LEVEL_ENV, "INFO")
        self.logger.setLevel(getattr(logging, level))

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(self.FORMAT, self.DATE_FORMAT))
            self.logger.addHandler(handler)

    def debug(self, msg: str, **kwargs) -> None: ...
    def info(self, msg: str, **kwargs) -> None: ...
    def warning(self, msg: str, **kwargs) -> None: ...
    def error(self, msg: str, **kwargs) -> None: ...
    def critical(self, msg: str, **kwargs) -> None: ...
```

**日志级别策略**：
| 级别 | 使用场景 |
|------|---------|
| DEBUG | 详细调试信息，工具调用参数 |
| INFO | 常规操作，任务状态变更 |
| WARNING | 潜在问题，权限提示 |
| ERROR | 操作失败，需要关注 |
| CRITICAL | 系统级错误，崩溃风险 |

### 16.2 配置文件格式

**配置路径优先级**（从高到低）：
1. `--config` 命令行参数
2. `~/.src_py/config.yaml`
3. `./src_py.yaml`

**YAML 配置示例**：
```yaml
# src_py.yaml
version: "1.0"

# LLM 配置
llm:
  provider: "anthropic"  # anthropic | openai | azure | local
  model: "claude-3-5-sonnet-20241022"
  api_key: "${ANTHROPIC_API_KEY}"  # 支持环境变量引用
  base_url: null  # 用于代理或本地模型

# 向量数据库配置
vector_store:
  provider: "milvus"
  uri: "http://localhost:19530"
  collection: "src_py_memory"

# MCP 配置
mcp:
  servers: {}
  # 示例:
  # servers:
  #   filesystem:
  #     command: "fastmcp"
  #     args: ["run", "./mcp/filesystem.py"]

# 安全配置
security:
  mode: "review"  # bypass | auto | accept_edits | plan | review | deny
  rules:
    - tool: "Bash"
      pattern: "rm -rf /"
      pattern_type: "regex"
      action: "deny"
      priority: 100
  budgets:
    - tool_name: "Bash"
      total: 100
      window_minutes: 60

# CLI 配置
cli:
  theme: "dark"
  streaming: true
  status_bar: true

# 观测配置
observability:
  phoenix_endpoint: "http://localhost:6006"
  export_traces: true
```

**配置加载**：
```python
from pydantic import BaseModel
from typing import Optional

class LLMConfig(BaseModel):
    provider: str = "anthropic"
    model: str = "claude-3-5-sonnet-20241022"
    api_key: Optional[str] = None
    base_url: Optional[str] = None

class VectorStoreConfig(BaseModel):
    provider: str = "milvus"
    uri: str = "http://localhost:19530"
    collection: str = "src_py_memory"

class Config(BaseModel):
    version: str = "1.0"
    llm: LLMConfig = LLMConfig()
    vector_store: VectorStoreConfig = VectorStoreConfig()
    mcp: dict = {}
    security: dict = {}
    cli: dict = {}
    observability: dict = {}

    @classmethod
    def load(cls, path: str | None = None) -> "Config":
        """加载配置文件"""
        import os
        import yaml

        # 路径优先级
        paths = []
        if path:
            paths.append(path)
        paths.extend([
            os.path.expanduser("~/.src_py/config.yaml"),
            "./src_py.yaml",
        ])

        for p in paths:
            if os.path.exists(p):
                with open(p) as f:
                    data = yaml.safe_load(f)
                    return cls(**data)

        return cls()  # 默认配置
```

---

## 十七、错误处理与恢复

### 17.1 策略

- **简单重试**：失败后指数退避重试 N 次
- **Fallback 模型**：主模型失败自动切换备用模型
- **输出 token 恢复**：API 超时/中断时，从 partial output 恢复
- **错误状态机**：Task/Agent 有明确的错误状态

### 17.2 错误类型（共享定义）

```python
# ErrorAction 和 ErrorRecoveryConfig 定义见 Section 十八、通用类型定义
# 此处仅作引用
```

### 17.3 错误处理决策树

```
┌─────────────────────────────────────────────────────────────────────┐
│                         错误处理决策树                                │
└─────────────────────────────────────────────────────────────────────┘

                            ┌─────────────┐
                            │  发生错误   │
                            └──────┬──────┘
                                   │
                                   ▼
                        ┌──────────────────┐
                        │  检查错误类型     │
                        │  is retryable?   │
                        └────────┬─────────┘
                                 │
                    ┌────────────┴────────────┐
                    │ Yes                      │ No
                    ▼                          ▼
        ┌────────────────────┐       ┌────────────────────┐
        │ 检查重试预算        │       │  ASK_USER          │
        │ retry_budget > 0? │       │  请求用户决策      │
        └────────┬───────────┘       └────────────────────┘
                 │
      ┌──────────┴──────────┐
      │ Yes                  │ No (预算耗尽)
      ▼                      ▼
┌───────────────────┐  ┌───────────────────┐
│ 检查是否需要切换模型 │  │ ASK_USER          │
│ is API error?     │  │ 请求用户决策       │
└────────┬──────────┘  └───────────────────┘
         │
    ┌────┴────┐
    │ Yes     │ No
    ▼         ▼
┌───────────┐  ┌─────────────────┐
│ FALLBACK  │  │ 有 partial      │
│ _MODEL    │  │ output?         │
└───────────┘  └────────┬────────┘
                        │
               ┌────────┴────────┐
               │ Yes              │ No
               ▼                  ▼
       ┌──────────────┐  ┌──────────────┐
       │ RECOVER_     │  │ RETRY_WITH   │
       │ OUTPUT       │  │ _BACKOFF     │
       └──────────────┘  └──────────────┘
                              │
                              ▼
                       ┌────────────┐
                       │  MARK_     │
                       │  FAILED    │
                       │  (超过     │
                       │  最大重试) │
                       └────────────┘
```

### 17.4 熔断器模式

```python
class CircuitBreaker:
    """熔断器 - 防止持续失败调用"""

    def __init__(self, config: ErrorRecoveryConfig):
        self.threshold = config.circuit_breaker_threshold
        self.timeout = config.circuit_breaker_timeout
        self._failure_count = 0
        self._last_failure_time: float | None = None
        self._state: Literal["closed", "open", "half_open"] = "closed"

    def can_execute(self) -> bool:
        """检查是否可以执行"""
        if self._state == "closed":
            return True
        if self._state == "open":
            if time.time() - self._last_failure_time > self.timeout:
                self._state = "half_open"
                return True
            return False
        # half_open: 只允许一个请求
        return True

    def record_success(self) -> None:
        """记录成功"""
        self._failure_count = 0
        self._state = "closed"

    def record_failure(self) -> None:
        """记录失败"""
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self.threshold:
            self._state = "open"
```

---

## 十八、通用类型定义

### 18.1 类型词汇表

所有共享类型在此章节定义，确保跨模块一致性。

```python
# === 核心类型 ===

T = TypeVar("T")

@dataclass
class SrcEvent:
    """事件基类（重命名以避免与 asyncio.Event 冲突）"""
    timestamp: datetime
    source: str

# === 错误恢复类型 ===

class ErrorAction(Enum):
    """错误恢复动作"""
    RETRY = "retry"           # 重试
    RETRY_WITH_BACKOFF = "retry_with_backoff"  # 指数退避重试
    FALLBACK_MODEL = "fallback_model"  # 切换模型
    RECOVER_OUTPUT = "recover_output"  # 恢复 partial output
    MARK_FAILED = "mark_failed"  # 标记为失败
    ASK_USER = "ask_user"  # 请求用户决策

@dataclass
class ErrorRecoveryConfig:
    """错误恢复配置"""
    max_retries: int = 3                     # 最大重试次数
    base_backoff_seconds: float = 1.0       # 基础退避时间（秒）
    max_backoff_seconds: float = 60.0       # 最大退避时间（秒）
    retry_budget: int = 10                  # 每会话最大重试次数
    circuit_breaker_threshold: int = 5      # 熔断器阈值（连续失败次数）
    circuit_breaker_timeout: float = 60.0    # 熔断器超时（秒）

# === DAG 类型 ===

@dataclass
class DAG(Generic[T]):
    """有向无环图 - 用于 Task 依赖管理"""
    _nodes: dict[T, set[T]] = field(default_factory=dict)
    _edges: dict[T, set[T]] = field(default_factory=dict)

    def add_node(self, node: T) -> None:
        """添加节点"""
        if node not in self._nodes:
            self._nodes[node] = set()

    def add_edge(self, from_node: T, to_node: T) -> None:
        """添加边 from_node -> to_node（to_node 依赖 from_node）"""
        if from_node not in self._nodes:
            self.add_node(from_node)
        if to_node not in self._nodes:
            self.add_node(to_node)
        self._edges[from_node].add(to_node)

    def get_dependencies(self, node: T) -> set[T]:
        """获取节点的前置依赖（指向该节点的节点）"""
        dependencies = set()
        for n, edges in self._edges.items():
            if node in edges:
                dependencies.add(n)
        return dependencies

    def get_dependents(self, node: T) -> set[T]:
        """获取节点的依赖项（该节点指向的节点）"""
        return self._nodes.get(node, set()).copy()

    def has_cycle(self) -> tuple[bool, list[T] | None]:
        """检测是否存在环

        Returns:
            (has_cycle, cycle_path): has_cycle=True 时，cycle_path 包含环的节点列表
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[T, int] = {node: WHITE for node in self._nodes}
        parent: dict[T, T | None] = {node: None for node in self._nodes}

        def dfs(node: T) -> list[T] | None:
            color[node] = GRAY
            for neighbor in self._nodes.get(node, set()):
                if color[neighbor] == GRAY:
                    # 找到回边，构建环路径
                    cycle = [neighbor, node]
                    while parent[node] is not None and parent[node] != neighbor:
                        node = parent[node]
                        cycle.append(node)
                    cycle.reverse()
                    return cycle
                if color[neighbor] == WHITE:
                    parent[neighbor] = node
                    result = dfs(neighbor)
                    if result:
                        return result
            color[node] = BLACK
            return None

        for node in self._nodes:
            if color[node] == WHITE:
                result = dfs(node)
                if result:
                    return True, result
        return False, None

    def topological_sort(self) -> list[T]:
        """拓扑排序（Kahn 算法）

        Returns:
            排序后的节点列表

        Raises:
            ValueError: 当图中存在环时
        """
        # 检测环
        has_cycle, cycle_path = self.has_cycle()
        if has_cycle:
            raise ValueError(f"Cannot perform topological sort: cycle detected in {cycle_path}")

        in_degree: dict[T, int] = {node: 0 for node in self._nodes}
        for node in self._nodes:
            for neighbor in self._nodes[node]:
                in_degree[neighbor] += 1

        # 从入度为 0 的节点开始
        queue: list[T] = [node for node, degree in in_degree.items() if degree == 0]
        result: list[T] = []

        while queue:
            node = queue.pop(0)
            result.append(node)
            for neighbor in self._nodes.get(node, set()):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(self._nodes):
            raise ValueError("Topological sort failed: graph modified during iteration")
        return result

@dataclass
class CompressionStrategy:
    """压缩策略类型"""
    name: Literal["none", "snip", "microcompact", "collapse"]
    threshold: float  # 0.0 - 1.0

# === LLM 相关类型 ===

@dataclass
class LiteLLMClient:
    """LiteLLM 客户端接口"""
    model: str
    api_key: str | None = None
    base_url: str | None = None

    async def chat_complete(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
    ) -> Message:
        """同步完成调用"""
        pass  # LiteLLM 实现

    async def stream_complete(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        stream_handler: Callable[["StreamChunk"], None] | None = None,
    ) -> AsyncGenerator[str, None]:
        """流式完成调用

        Args:
            messages: 消息列表
            tools: 工具定义列表
            stream_handler: 可选的流式处理回调，用于实时处理 chunks

        Yields:
            str: 增量文本片段

        Raises:
            RateLimitError: 触发速率限制时
            AuthenticationError: 认证失败时
            ContextLengthExceededError: 上下文超出限制时
        """
        # LiteLLM 流式调用实现
        # 使用 litellm.streaming() 获取流式响应
        pass

    async def stream_complete_with_backpressure(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        buffer_size: int = 100,
    ) -> AsyncGenerator[str, None]:
        """带背压控制的流式调用

        当消费者处理速度慢于生产速度时，使用有界队列缓冲。
        队列满时暂停 LLM 调用，直到消费者消费了部分数据。

        Args:
            messages: 消息列表
            tools: 工具定义列表
            buffer_size: 最大缓冲 chunks 数量

        Yields:
            str: 增量文本片段
        """
        buffer: asyncio.Queue[str] = asyncio.Queue(maxsize=buffer_size)
        done = False

        async def producer():
            nonlocal done
            try:
                async for chunk in self.stream_complete(messages, tools):
                    await buffer.put(chunk)
            finally:
                done = True

        async def consumer() -> AsyncGenerator[str, None]:
            while not done or not buffer.empty():
                try:
                    chunk = await asyncio.wait_for(buffer.get(), timeout=1.0)
                    yield chunk
                except asyncio.TimeoutError:
                    continue

        # 并发运行生产和消费
        producer_task = asyncio.create_task(producer())
        try:
            async for chunk in consumer():
                yield chunk
        finally:
            producer_task.cancel()
            try:
                await producer_task
            except asyncio.CancelledError:
                pass


@dataclass
class StreamChunk:
    """流式响应片段"""
    content: str                    # 增量文本
    is_final: bool = False         # 是否为最后一个片段
    tool_calls: list[ToolCall] | None = None  # 片段中的工具调用
    usage: TokenUsage | None = None  # token 使用量（is_final=True 时）

# === MCP 相关类型 ===

@dataclass
class MCPServerConfig:
    """MCP 服务器配置"""
    name: str
    command: str
    args: list[str]
    env: dict[str, str] | None = None

@dataclass
class MCPTool:
    """MCP 工具定义"""
    name: str
    description: str
    input_schema: dict[str, Any]

@dataclass
class MCPResource:
    """MCP 资源定义"""
    uri: str
    name: str
    description: str | None = None

@dataclass
class MCPResourceResult:
    """MCP 资源读取结果"""
    uri: str
    content: str
    mime_type: str | None = None

# === Archive 相关类型 ===

@dataclass
class ArchiveStore:
    """归档存储接口

    归档存储使用 Milvus 向量数据库存储压缩前的原始消息。
    归档后，原始消息可通过 archive_ref 检索。

    存储设计：
    - 每个 archive 存储为一个 document，包含完整的 messages 列表
    - archive_ref 格式: "{session_id}_{timestamp}_{uuid}"
    - Milvus collection: "message_archives"
    - retention: 默认 30 天后自动删除
    """
    def __init__(
        self,
        milvus_uri: str = "http://localhost:19530",
        collection_name: str = "message_archives",
        retention_days: int = 30,
    ):
        self.milvus_uri = milvus_uri
        self.collection_name = collection_name
        self.retention_days = retention_days
        self._client = None  # 延迟初始化

    async def _get_client(self):
        """获取或创建 Milvus 客户端"""
        if self._client is None:
            from pymilvus import connections, Collection
            connections.connect(uri=self.milvus_uri)
            self._client = Collection(self.collection_name)
        return self._client

    async def archive(
        self,
        messages: list[Message],
        metadata: dict[str, Any],
    ) -> str:
        """归档消息

        Args:
            messages: 要归档的原始消息列表
            metadata: 归档元数据（包含 strategy, timestamp 等）

        Returns:
            archive_ref: 用于检索的引用字符串
        """
        import uuid
        from datetime import datetime

        client = await self._get_client()

        # 生成 archive_ref
        session_id = metadata.get("session_id", "default")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_ref = f"{session_id}_{timestamp}_{uuid.uuid4().hex[:8]}"

        # 序列化消息
        import json
        archived_data = {
            "messages": [msg.__dict__ for msg in messages],
            "metadata": metadata,
            "created_at": datetime.now().isoformat(),
        }

        # 存储到 Milvus
        # 注意：Milvus 主要用于向量搜索，这里我们将其作为文档存储使用
        # 实际实现可能需要结合文件存储或专门的文档数据库
        entity = {
            "archive_ref": archive_ref,
            "content": json.dumps(archived_data),  # 完整归档数据
            "session_id": session_id,
            "message_count": len(messages),
            "created_at": datetime.now().timestamp(),
        }

        # 插入到 collection
        # client.insert(entity)  # 实际 Milvus 插入

        return archive_ref

    async def retrieve(self, archive_ref: str) -> list[Message]:
        """检索归档消息

        Args:
            archive_ref: 归档引用

        Returns:
            原始消息列表
        """
        import json
        client = await self._get_client()

        # 查询 archive_ref 对应的归档
        # results = client.query(expr=f'arhive_ref == "{archive_ref}"')
        results = []  # 占位

        if not results:
            raise KeyError(f"Archive not found: {archive_ref}")

        archived_data = json.loads(results[0]["content"])
        # 反序列化消息
        messages = [Message(**msg_dict) for msg_dict in archived_data["messages"]]
        return messages

    async def delete(self, archive_ref: str) -> None:
        """删除归档

        Args:
            archive_ref: 归档引用
        """
        client = await self._get_client()
        # client.delete(expr=f'arhive_ref == "{archive_ref}"')

    async def cleanup_expired(self) -> int:
        """清理过期归档

        Returns:
            删除的归档数量
        """
        import time
        from datetime import datetime, timedelta

        client = await self._get_client()
        cutoff = (datetime.now() - timedelta(days=self.retention_days)).timestamp()

        # 删除过期归档
        # deleted = client.delete(expr=f"created_at < {cutoff}")
        deleted = 0  # 占位
        return deleted
```

### 18.2 上下文类型统一

所有执行上下文统一使用 `ToolContext`：

```python
# ExecutionContext 不再单独定义，统一使用 ToolContext
# ToolContext 包含：
# - call_id: str          # 本次调用 ID
# - agent_id: str          # 执行 agent
# - task_id: str | None   # 当前任务
# - cwd: str              # 工作目录
# - env: dict[str, str]   # 环境变量
# - session_id: str        # 会话 ID
# - token_budget: ContextBudget  # token 预算
```

---

## 十九、项目结构

```
src_py/
├── __init__.py
├── main.py                     # CLI entry point
├── repl_launcher.py            # REPL launcher
├── run.sh                      # Shell script to run
├── pyproject.toml
├── test_mvp.py
│
├── cli/                        # CLI 界面与命令系统
│   ├── __init__.py
│   ├── cli.py                  # CLI 主入口
│   ├── status_bar.py           # 状态栏组件
│   ├── output_handler.py       # 输出处理器（流式）
│   ├── command_parser.py       # 命令解析器
│   └── builtin_commands.py     # 内置命令实现
│
├── state_sync/                 # 实时状态同步
│   ├── __init__.py
│   ├── publisher.py            # StatePublisher (发布/订阅)
│   ├── syncer.py               # StateSyncer (WebSocket/SSE)
│   └── subscriber.py           # CLI 状态订阅者
│
├── streaming/                  # 流式输出架构 (v1.4)
│   ├── __init__.py
│   ├── events.py              # StreamEvent 定义及 Schema
│   ├── streamer.py            # AgentStreamer (AsyncGenerator 抽象)
│   └── transports.py           # SSE/WebSocket 传输适配器
│
├── commands/                   # Command implementations
│   ├── __init__.py
│   ├── commit_cmd.py
│   └── help_cmd.py
│
├── lib/                        # 核心库（保持向后兼容）
│   ├── __init__.py
│   └── config.py               # Config loading
│
├── orchestrator/               # Agent 编排器
│   ├── __init__.py
│   ├── orchestrator.py        # AgentOrchestrator 主类
│   ├── task_graph.py           # Task DAG 管理
│   ├── task_scheduler.py       # 任务调度器
│   └── agent_manager.py        # Agent 生命周期管理
│
├── context/                    # 上下文管理
│   ├── __init__.py
│   ├── manager.py              # ContextManager
│   └── compression.py          # 4级压缩算法
│
├── session/                    # 会话管理
│   ├── __init__.py
│   ├── manager.py             # SessionManager
│   └── models.py              # Session/TokenUsage 模型
│
├── memory/                     # 记忆系统
│   ├── __init__.py
│   └── store.py               # MemoryStore (Mem0 + Milvus)
│
├── api/                       # API 客户端
│   ├── __init__.py
│   └── client.py              # LiteLLM client
│
├── security/                   # 安全/权限
│   ├── __init__.py
│   ├── layer.py              # SecurityLayer
│   ├── rules.py              # PermissionRule
│   └── budgets.py            # PermissionBudget
│
├── tools/                      # Tool implementations
│   ├── __init__.py
│   ├── base.py                 # Tool definition base
│   ├── bash_tool.py
│   ├── file_read_tool.py
│   ├── file_edit_tool.py
│   ├── grep_tool.py
│   ├── glob_tool.py
│   ├── web_fetch_tool.py
│   ├── task_create_tool.py
│   └── agent_call_tool.py
│
├── skills/                     # Skills directory (Agent Skills spec)
│   ├── brainstorming/
│   │   ├── SKILL.md
│   │   └── scripts/
│   ├── tdd/
│   │   └── SKILL.md
│   └── debug/
│       └── SKILL.md
│
├── mcp/                        # MCP integration
│   ├── __init__.py
│   ├── client.py               # MCP client
│   ├── server.py               # FastMCP server
│   ├── registry.py             # MCP registry
│   └── config.py               # MCP config loader
│
├── state/                      # State management
│   ├── __init__.py
│   ├── store.py                # StateStore
│   ├── app_state.py            # AppState
│   └── hooks.py                # React-style hooks
│
├── screens/                    # UI screens
│   ├── __init__.py
│   └── repl.py                 # REPL screen
│
├── utils/                      # Utilities
│   ├── __init__.py
│   └── dag.py                  # DAG implementation
│
└── observability/              # Phoenix integration
    ├── __init__.py
    ├── tracer.py               # OpenTelemetry tracer
    ├── span_processors.py      # Span processors
    └── evaluator.py            # Eval runners
```

---

## 二十、技术选型

| 组件 | 技术 |
|------|------|
| 语言 | Python 3.11+ |
| 异步运行时 | asyncio + TaskGroup |
| LLM 封装 | LiteLLM |
| 向量数据库 | Milvus |
| Memory | Mem0 |
| MCP | FastMCP |
| 观测 | Phoenix + OpenTelemetry |
| 状态持久化 | SQLite / JSON Lines |
| CLI | Typer + Rich |
| 类型检查 | Pydantic |

---

## 二十一、实现优先级

### Phase 1: 核心基础设施
1. State Store（状态管理基础）
2. LiteLLM Client（LLM 调用）
3. Tool System（工具系统）
4. CLI (Typer + Rich)

### Phase 2: Agent 核心
5. Agent Orchestrator（编排器）
6. Task DAG（任务图）
7. Context Manager（上下文压缩）
8. Security Layer（安全权限）

### Phase 3: 扩展系统
9. Skills System（技能系统）
10. MCP System（MCP 集成）
11. Session Manager（会话管理）

### Phase 4: 高级功能
12. Memory Store（记忆系统）
13. Observability（观测系统）
14. Error Recovery（错误恢复）
