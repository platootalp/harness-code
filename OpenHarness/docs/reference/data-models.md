# 数据模型参考

## 摘要

OpenHarness 的核心数据类型按功能分层为 Engine 层、Config 层、MCP 层、Swarm 层、Coordinator 层、Plugin 层和 Channel 层。本页按层级整理所有 Pydantic / dataclass 模型及其字段含义。

## 你将了解

- Engine 层：消息、工具执行、流事件
- Config 层：配置、认证、Provider Profile、权限、沙箱、记忆
- MCP 层：MCP 服务器配置和运行时状态
- Swarm 层：团队协作、Pane 管理、Teammate 执行
- Coordinator 层：Agent 定义、Worker 配置、任务通知
- Plugin 层：插件命令定义和加载插件
- Channel 层：消息总线事件和通道桥接

## 范围

覆盖 `src/openharness/engine/`、`src/openharness/config/`、`src/openharness/mcp/`、`src/openharness/swarm/`、`src/openharness/coordinator/`、`src/openharness/plugins/`、`src/openharness/channels/` 下所有核心数据模型。

---

## Engine 层

Engine 层是查询引擎的核心数据模型，处理消息构建、工具执行和流事件。

### ConversationMessage

单条用户或助手消息。

```python
class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: list[ContentBlock] = Field(default_factory=list)
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `role` | `Literal["user", "assistant"]` | 消息角色：`user`（用户）或 `assistant`（助手） |
| `content` | `list[ContentBlock]` | 内容块列表，包含 `TextBlock`、`ImageBlock`、`ToolUseBlock`、`ToolResultBlock` |

**属性：**
- `text: str`：连接所有文本块返回的纯文本
- `tool_uses: list[ToolUseBlock]`：消息中包含的所有工具调用

**工厂方法：**
- `ConversationMessage.from_user_text(text: str)`：从纯文本构造用户消息
- `ConversationMessage.from_user_content(content: list[ContentBlock])`：从显式内容块构造用户消息

**转换方法：**
- `to_api_param() -> dict[str, Any]`：转换为 Provider API 参数格式

> 证据来源：`src/openharness/engine/messages.py` -> `ConversationMessage`（行 64-97）

### ContentBlock

内容块的联合类型，通过 `type` 字段区分：

```python
ContentBlock = Annotated[
    TextBlock | ImageBlock | ToolUseBlock | ToolResultBlock,
    Field(discriminator="type"),
]
```

### TextBlock

纯文本内容块。

```python
class TextBlock(BaseModel):
    type: Literal["text"] = "text"
    text: str
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | `Literal["text"]` | 固定为 `"text"` |
| `text` | `str` | 文本内容 |

> 证据来源：`src/openharness/engine/messages.py` -> `TextBlock`（行 14-18）

### ImageBlock

内联图片内容块（用于多模态 Provider）。

```python
class ImageBlock(BaseModel):
    type: Literal["image"] = "image"
    media_type: str
    data: str
    source_path: str = ""
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | `Literal["image"]` | 固定为 `"image"` |
| `media_type` | `str` | MIME 类型（如 `"image/png"`） |
| `data` | `str` | Base64 编码的图片数据 |
| `source_path` | `str` | 原始文件路径 |

**工厂方法：**
- `ImageBlock.from_path(path: str | Path)`：从本地文件路径加载图片

> 证据来源：`src/openharness/engine/messages.py` -> `ImageBlock`（行 21-37）

### ToolUseBlock

模型请求执行工具的调用块。

```python
class ToolUseBlock(BaseModel):
    type: Literal["tool_use"] = "tool_use"
    id: str = Field(default_factory=lambda: f"toolu_{uuid4().hex}")
    name: str
    input: dict[str, Any] = Field(default_factory=dict)
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | `Literal["tool_use"]` | 固定为 `"tool_use"` |
| `id` | `str` | 工具调用的唯一 ID（自动生成） |
| `name` | `str` | 工具名称 |
| `input` | `dict[str, Any]` | 工具输入参数 |

> 证据来源：`src/openharness/engine/messages.py` -> `ToolUseBlock`（行 40-46）

### ToolResultBlock

工具执行结果内容块（发回给模型）。

```python
class ToolResultBlock(BaseModel):
    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str
    content: str
    is_error: bool = False
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | `Literal["tool_result"]` | 固定为 `"tool_result"` |
| `tool_use_id` | `str` | 对应 `ToolUseBlock.id` |
| `content` | `str` | 工具执行结果的文本表示 |
| `is_error` | `bool` | 是否为错误结果（默认 `False`） |

> 证据来源：`src/openharness/engine/messages.py` -> `ToolResultBlock`（行 49-55）

---

### ToolExecutionContext

工具调用的共享执行上下文。

```python
@dataclass
class ToolExecutionContext:
    cwd: Path
    metadata: dict[str, Any] = field(default_factory=dict)
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `cwd` | `Path` | 当前工作目录 |
| `metadata` | `dict[str, Any]` | 传递给工具的元数据 |

> 证据来源：`src/openharness/tools/base.py` -> `ToolExecutionContext`（行 13-18）

### ToolResult

规范化的工具执行结果。

```python
@dataclass(frozen=True)
class ToolResult:
    output: str
    is_error: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `output` | `str` | 工具执行的输出文本 |
| `is_error` | `bool` | 是否为错误（默认 `False`） |
| `metadata` | `dict[str, Any]` | 额外元数据（如执行时间、资源使用等） |

> 证据来源：`src/openharness/tools/base.py` -> `ToolResult`（行 21-27）

---

### StreamEvent

查询引擎产生的流事件联合类型。

```python
StreamEvent = (
    AssistantTextDelta
    | AssistantTurnComplete
    | ToolExecutionStarted
    | ToolExecutionCompleted
    | ErrorEvent
    | StatusEvent
    | CompactProgressEvent
)
```

#### AssistantTextDelta

助手文本增量事件（流式输出）。

```python
@dataclass(frozen=True)
class AssistantTextDelta:
    text: str
```

#### AssistantTurnComplete

助手回合完成事件。

```python
@dataclass(frozen=True)
class AssistantTurnComplete:
    message: ConversationMessage
    usage: UsageSnapshot
```

#### ToolExecutionStarted

工具开始执行事件。

```python
@dataclass(frozen=True)
class ToolExecutionStarted:
    tool_name: str
    tool_input: dict[str, Any]
```

#### ToolExecutionCompleted

工具执行完成事件。

```python
@dataclass(frozen=True)
class ToolExecutionCompleted:
    tool_name: str
    output: str
    is_error: bool = False
```

#### ErrorEvent

错误事件。

```python
@dataclass(frozen=True)
class ErrorEvent:
    message: str
    recoverable: bool = True
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `recoverable` | `bool` | 是否可恢复（默认 `True`），不可恢复的错误会导致会话终止 |

#### StatusEvent

瞬态系统状态消息事件。

```python
@dataclass(frozen=True)
class StatusEvent:
    message: str
```

#### CompactProgressEvent

对话压缩进度事件。

```python
@dataclass(frozen=True)
class CompactProgressEvent:
    phase: Literal[
        "hooks_start",
        "context_collapse_start",
        "context_collapse_end",
        "session_memory_start",
        "session_memory_end",
        "compact_start",
        "compact_retry",
        "compact_end",
        "compact_failed",
    ]
    trigger: Literal["auto", "manual", "reactive"]
    message: str | None = None
    attempt: int | None = None
    checkpoint: str | None = None
    metadata: dict[str, Any] | None = None
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `phase` | `Literal` | 压缩阶段 |
| `trigger` | `Literal["auto", "manual", "reactive"]` | 触发方式 |
| `message` | `str \| None` | 可读状态消息 |
| `attempt` | `int \| None` | 当前重试次数 |
| `checkpoint` | `str \| None` | 检查点标识 |
| `metadata` | `dict \| None` | 额外元数据 |

> 证据来源：`src/openharness/engine/stream_events.py` -> 全部 StreamEvent 子类型（行 12-88）

---

### CostTracker

会话期间的用量累积器。

```python
class CostTracker:
    def __init__(self) -> None:
        self._usage: UsageSnapshot

    def add(self, usage: UsageSnapshot) -> None:
        """累加一个用量快照"""

    @property
    def total(self) -> UsageSnapshot:
        """返回聚合后的总用量"""
```

> 证据来源：`src/openharness/engine/cost_tracker.py` -> `CostTracker`（行 8-24）

---

## Config 层

Config 层包含所有配置相关的数据模型。`Settings`、`ProviderProfile`、`PermissionSettings`、`SandboxSettings`、`MemorySettings` 已在 [配置参考](./config.md) 中详细说明，此处不再重复。以下补充 Config 层中其他模型。

### ResolvedAuth

规范化后的认证材料，用于构造 API 客户端。

```python
@dataclass(frozen=True)
class ResolvedAuth:
    provider: str
    auth_kind: str
    value: str
    source: str
    state: str = "configured"
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `provider` | `str` | Provider ID |
| `auth_kind` | `str` | 认证类型（如 `"api_key"`、`"oauth_device"`） |
| `value` | `str` | 认证值（API 密钥或令牌） |
| `source` | `str` | 来源（如 `"env:ANTHROPIC_API_KEY"`、`"file:anthropic"`） |
| `state` | `str` | 状态，默认 `"configured"` |

> 证据来源：`src/openharness/config/settings.py` -> `ResolvedAuth`（行 132-140）

---

## MCP 层

### McpServerConfig

MCP 服务器配置的联合类型（三种传输方式），已在 [配置参考](./config.md) 中详细说明。

### McpStdioServerConfig

stdio 传输配置。

```python
class McpStdioServerConfig(BaseModel):
    type: Literal["stdio"] = "stdio"
    command: str
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] | None = None
    cwd: str | None = None
```

> 证据来源：`src/openharness/mcp/types.py` -> `McpStdioServerConfig`（行 11-18）

### McpHttpServerConfig

HTTP 传输配置。

```python
class McpHttpServerConfig(BaseModel):
    type: Literal["http"] = "http"
    url: str
    headers: dict[str, str] = Field(default_factory=dict)
```

> 证据来源：`src/openharness/mcp/types.py` -> `McpHttpServerConfig`（行 21-26）

### McpWebSocketServerConfig

WebSocket 传输配置。

```python
class McpWebSocketServerConfig(BaseModel):
    type: Literal["ws"] = "ws"
    url: str
    headers: dict[str, str] = Field(default_factory=dict)
```

> 证据来源：`src/openharness/mcp/types.py` -> `McpWebSocketServerConfig`（行 29-34）

### McpToolInfo

MCP 服务器暴露的工具元数据。

```python
@dataclass(frozen=True)
class McpToolInfo:
    server_name: str
    name: str
    description: str
    input_schema: dict[str, object]
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `server_name` | `str` | 所属服务器名称 |
| `name` | `str` | 工具名称 |
| `description` | `str` | 工具描述 |
| `input_schema` | `dict[str, object]` | JSON Schema 格式的输入参数规范 |

> 证据来源：`src/openharness/mcp/types.py` -> `McpToolInfo`（行 46-53）

### McpResourceInfo

MCP 服务器暴露的资源元数据。

```python
@dataclass(frozen=True)
class McpResourceInfo:
    server_name: str
    name: str
    uri: str
    description: str = ""
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `server_name` | `str` | 所属服务器名称 |
| `name` | `str` | 资源名称 |
| `uri` | `str` | 资源 URI |
| `description` | `str` | 资源描述（默认空） |

> 证据来源：`src/openharness/mcp/types.py` -> `McpResourceInfo`（行 56-63）

### McpConnectionStatus

MCP 服务器运行时状态。

```python
@dataclass
class McpConnectionStatus:
    name: str
    state: Literal["connected", "failed", "pending", "disabled"]
    detail: str = ""
    transport: str = "unknown"
    auth_configured: bool = False
    tools: list[McpToolInfo] = field(default_factory=list)
    resources: list[McpResourceInfo] = field(default_factory=list)
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `state` | `Literal` | 连接状态 |
| `detail` | `str` | 状态详情或错误信息 |
| `transport` | `str` | 传输类型（`stdio`、`http`、`ws`） |
| `auth_configured` | `bool` | 是否已配置认证 |
| `tools` | `list[McpToolInfo]` | 该服务器暴露的工具列表 |
| `resources` | `list[McpResourceInfo]` | 该服务器暴露的资源列表 |

> 证据来源：`src/openharness/mcp/types.py` -> `McpConnectionStatus`（行 66-76）

### McpJsonConfig

MCP 配置文件的标准格式（插件和项目文件使用）。

```python
class McpJsonConfig(BaseModel):
    mcpServers: dict[str, McpServerConfig] = Field(default_factory=dict)
```

> 证据来源：`src/openharness/mcp/types.py` -> `McpJsonConfig`（行 40-43）

---

## Swarm 层

Swarm 层处理多 Agent 团队协作和终端 Pane 管理。

### BackendType

后端类型字面量联合。

```python
BackendType = Literal["subprocess", "in_process", "tmux", "iterm2"]
```

| 值 | 说明 |
|------|------|
| `subprocess` | 子进程模式 |
| `in_process` | 进程内模式 |
| `tmux` | tmux Pane 管理 |
| `iterm2` | iTerm2 Pane 管理 |

### PaneBackendType

仅支持 Pane 的后端类型。

```python
PaneBackendType = Literal["tmux", "iterm2"]
```

### PaneId

Pane 的不透明标识符字符串：
- tmux：格式为 `"%1"` 等
- iTerm2：会话 ID（由 `it2` 返回）

### CreatePaneResult

创建新 Teammate Pane 的结果。

```python
@dataclass
class CreatePaneResult:
    pane_id: PaneId
    is_first_teammate: bool
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `is_first_teammate` | `bool` | 是否为第一个 Teammate Pane（影响布局策略） |

### BackendDetectionResult

后端自动检测结果。

```python
@dataclass
class BackendDetectionResult:
    backend: str
    is_native: bool
    needs_setup: bool = False
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `backend` | `str` | 应使用的后端类型字符串 |
| `is_native` | `bool` | 是否运行在后端自身的环境中 |
| `needs_setup` | `bool` | 是否需要额外设置（如安装 `it2`） |

> 证据来源：`src/openharness/swarm/types.py` -> `BackendDetectionResult`（行 212-229）

### TeammateIdentity

Teammate Agent 的身份字段。

```python
@dataclass
class TeammateIdentity:
    agent_id: str
    name: str
    team: str
    color: str | None = None
    parent_session_id: str | None = None
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `agent_id` | `str` | 唯一 Agent 标识符（格式：`agentName@teamName`） |
| `name` | `str` | Agent 名称（如 `"researcher"`） |
| `team` | `str` | 所属团队名称 |
| `color` | `str \| None` | UI 区分用的颜色 |
| `parent_session_id` | `str \| None` | 父会话 ID（用于上下文关联） |

> 证据来源：`src/openharness/swarm/types.py` -> `TeammateIdentity`（行 237-254）

### TeammateSpawnConfig

Teammate 启动配置。

```python
@dataclass
class TeammateSpawnConfig:
    name: str
    team: str
    prompt: str
    cwd: str
    parent_session_id: str
    model: str | None = None
    system_prompt: str | None = None
    system_prompt_mode: Literal["default", "replace", "append"] | None = None
    color: str | None = None
    color_override: str | None = None
    permissions: list[str] = field(default_factory=list)
    plan_mode_required: bool = False
    allow_permission_prompts: bool = False
    worktree_path: str | None = None
    session_id: str | None = None
    subscriptions: list[str] = field(default_factory=list)
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | `str` | Teammate 显示名称 |
| `team` | `str` | 团队名称 |
| `prompt` | `str` | 初始提示词/任务 |
| `cwd` | `str` | 工作目录 |
| `parent_session_id` | `str` | 父会话 ID（用于转录关联） |
| `model` | `str \| None` | 模型覆盖 |
| `system_prompt_mode` | `Literal` | 系统提示词应用方式 |
| `color` | `str \| None` | UI 颜色（可选） |
| `permissions` | `list[str]` | 授予该 Teammate 的工具权限 |
| `plan_mode_required` | `bool` | 该 Teammate 是否必须在实现前进入规划模式 |
| `allow_permission_prompts` | `bool` | 是否允许权限提示（`False` 时未列出的工具自动拒绝） |
| `worktree_path` | `str \| None` | 隔离文件系统访问的 git worktree 路径 |
| `subscriptions` | `list[str]` | 该 Teammate 订阅的事件主题 |

> 证据来源：`src/openharness/swarm/types.py` -> `TeammateSpawnConfig`（行 257-307）

### SpawnResult

Teammate 启动结果。

```python
@dataclass
class SpawnResult:
    task_id: str
    agent_id: str
    backend_type: BackendType
    success: bool = True
    error: str | None = None
    pane_id: PaneId | None = None
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `pane_id` | `PaneId \| None` | Pane ID（仅 Pane 后端有效） |

> 证据来源：`src/openharness/swarm/types.py` -> `SpawnResult`（行 315-332）

### TeammateMessage

发送给 Teammate 的消息。

```python
@dataclass
class TeammateMessage:
    text: str
    from_agent: str
    color: str | None = None
    timestamp: str | None = None
    summary: str | None = None
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `from_agent` | `str` | 发送方 Agent ID |
| `summary` | `str \| None` | 消息摘要（用于通知显示） |

> 证据来源：`src/openharness/swarm/types.py` -> `TeammateMessage`（行 335-343）

### TeammateExecutor

Teammate 执行后端的协议接口（Protocol），支持 `spawn`/`send_message`/`shutdown` 操作。

```python
@runtime_checkable
class TeammateExecutor(Protocol):
    type: BackendType

    def is_available(self) -> bool: ...
    async def spawn(self, config: TeammateSpawnConfig) -> SpawnResult: ...
    async def send_message(self, agent_id: str, message: TeammateMessage) -> None: ...
    async def shutdown(self, agent_id: str, *, force: bool = False) -> bool: ...
```

> 证据来源：`src/openharness/swarm/types.py` -> `TeammateExecutor` 协议（行 351-382）

### PaneBackend

Pane 管理后端的协议接口（tmux / iTerm2）。

```python
@runtime_checkable
class PaneBackend(Protocol):
    @property
    def type(self) -> BackendType: ...
    @property
    def display_name(self) -> str: ...
    @property
    def supports_hide_show(self) -> bool: ...
    async def is_available(self) -> bool: ...
    async def is_running_inside(self) -> bool: ...
    async def create_teammate_pane_in_swarm_view(self, name: str, color: str | None = None) -> CreatePaneResult: ...
    async def send_command_to_pane(self, pane_id: PaneId, command: str, *, use_external_session: bool = False) -> None: ...
    async def set_pane_border_color(self, pane_id: PaneId, color: str, *, use_external_session: bool = False) -> None: ...
    async def set_pane_title(self, pane_id: PaneId, name: str, color: str | None = None, *, use_external_session: bool = False) -> None: ...
    async def enable_pane_border_status(self, window_target: str | None = None, *, use_external_session: bool = False) -> None: ...
    async def rebalance_panes(self, window_target: str, has_leader: bool) -> None: ...
    async def kill_pane(self, pane_id: PaneId, *, use_external_session: bool = False) -> bool: ...
    async def hide_pane(self, pane_id: PaneId, *, use_external_session: bool = False) -> bool: ...
    async def show_pane(self, pane_id: PaneId, target_window_or_pane: str, *, use_external_session: bool = False) -> bool: ...
    def list_panes(self) -> list[PaneId]: ...
```

> 证据来源：`src/openharness/swarm/types.py` -> `PaneBackend` 协议（行 46-204）

---

## Coordinator 层

### AgentDefinition

完整的 Agent 定义，包含所有配置字段。

```python
class AgentDefinition(BaseModel):
    # --- 必需字段 ---
    name: str
    description: str

    # --- 提示词和工具 ---
    system_prompt: str | None = None
    tools: list[str] | None = None      # None = 所有工具允许
    disallowed_tools: list[str] | None = None

    # --- 模型和努力级别 ---
    model: str | None = None             # None = 继承默认
    effort: str | int | None = None      # "low" | "medium" | "high" 或正整数

    # --- 权限 ---
    permission_mode: str | None = None   # PERMISSION_MODES 之一

    # --- Agent 循环控制 ---
    max_turns: int | None = None        # 正整数轮次限制

    # --- 技能和 MCP ---
    skills: list[str] = Field(default_factory=list)
    mcp_servers: list[Any] | None = None
    required_mcp_servers: list[str] | None = None

    # --- Hooks ---
    hooks: dict[str, Any] | None = None

    # --- UI ---
    color: str | None = None             # AGENT_COLORS 之一

    # --- 生命周期 ---
    background: bool = False              # 始终作为后台任务运行
    initial_prompt: str | None = None    # 追加到首次用户轮次
    memory: str | None = None            # MEMORY_SCOPES 之一
    isolation: str | None = None          # ISOLATION_MODES 之一

    # --- 元数据 ---
    filename: str | None = None
    base_dir: str | None = None
    critical_system_reminder: str | None = None
    omit_claude_md: bool = False

    # --- Python 专用 ---
    permissions: list[str] = Field(default_factory=list)
    subagent_type: str = "general-purpose"
    source: Literal["builtin", "user", "plugin"] = "builtin"
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | `str` | Agent 类型标识符 |
| `description` | `str` | 使用时机描述（显示给 Spawn 发起方） |
| `tools` | `list[str] \| None` | `None` 表示允许所有工具（等效于 `["*"]`） |
| `effort` | `str \| int \| None` | 整数表示精确轮次上限 |
| `required_mcp_servers` | `list[str] \| None` | 必须存在的 MCP 服务器名模式列表 |
| `background` | `bool` | `True` 时始终作为后台任务运行 |
| `memory` | `str \| None` | 记忆作用域：`user`、`project`、`local` |
| `isolation` | `str \| None` | 隔离模式：`worktree`、`remote` |
| `critical_system_reminder` | `str \| None` | 每个用户轮次重新注入的短消息 |
| `omit_claude_md` | `bool` | 跳过 CLAUDE.md 注入 |

**内置 Agent 列表：** `general-purpose`、`statusline-setup`、`claude-code-guide`、`Explore`、`Plan`、`worker`、`verification`

**Agent 颜色常量：** `red`、`green`、`blue`、`yellow`、`purple`、`orange`、`cyan`、`magenta`、`white`、`gray`

> 证据来源：`src/openharness/coordinator/agent_definitions.py` -> `AgentDefinition` 类（行 60-134）和常量定义（行 21-52）

### WorkerConfig

Worker 配置（TODO：在代码中进一步确认具体字段）。

---

### TaskNotification

任务通知（TODO：在代码中进一步确认具体字段）。

---

## Plugin 层

### PluginCommandDefinition

插件贡献的斜杠命令定义。

```python
@dataclass(frozen=True)
class PluginCommandDefinition:
    name: str
    description: str
    content: str
    path: str | None = None
    source: str = "plugin"
    base_dir: str | None = None
    argument_hint: str | None = None
    when_to_use: str | None = None
    version: str | None = None
    model: str | None = None
    effort: str | int | None = None
    disable_model_invocation: bool = False
    user_invocable: bool = True
    is_skill: bool = False
    display_name: str | None = None
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `disable_model_invocation` | `bool` | 是否禁用模型调用（纯命令模式） |
| `user_invocable` | `bool` | 用户是否可以直接调用 |
| `is_skill` | `bool` | 是否作为 Skill 注册 |
| `model` | `str \| None` | 使用的模型（如不指定则继承） |

> 证据来源：`src/openharness/plugins/types.py` -> `PluginCommandDefinition`（行 15-32）

### LoadedPlugin

已加载插件及其贡献的所有制品。

```python
@dataclass(frozen=True)
class LoadedPlugin:
    manifest: PluginManifest
    path: Path
    enabled: bool
    skills: list[SkillDefinition] = field(default_factory=list)
    commands: list[PluginCommandDefinition] = field(default_factory=list)
    agents: list[AgentDefinition] = field(default_factory=list)
    hooks: dict[str, list] = field(default_factory=dict)
    mcp_servers: dict[str, McpServerConfig] = field(default_factory=dict)
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `manifest` | `PluginManifest` | 插件清单元数据 |
| `path` | `Path` | 插件文件路径 |
| `skills` | `list[SkillDefinition]` | 该插件贡献的技能列表 |
| `commands` | `list[PluginCommandDefinition]` | 该插件贡献的斜杠命令列表 |
| `agents` | `list[AgentDefinition]` | 该插件贡献的 Agent 定义列表 |
| `hooks` | `dict[str, list]` | 该插件注册的 Hook |
| `mcp_servers` | `dict[str, McpServerConfig]` | 该插件贡献的 MCP 服务器配置 |

**属性：**
- `name: str`：返回 `manifest.name`
- `description: str`：返回 `manifest.description`

> 证据来源：`src/openharness/plugins/types.py` -> `LoadedPlugin`（行 35-54）

---

## Channel 层

### InboundMessage

从聊天通道接收的消息。

```python
@dataclass
class InboundMessage:
    channel: str
    sender_id: str
    chat_id: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    media: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    session_key_override: str | None = None
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `channel` | `str` | 通道类型：`telegram`、`discord`、`slack`、`whatsapp` |
| `sender_id` | `str` | 用户标识符 |
| `chat_id` | `str` | 聊天/频道标识符 |
| `media` | `list[str]` | 媒体 URL 列表 |
| `session_key_override` | `str \| None` | 可选的线程作用域会话覆盖键 |

**属性：**
- `session_key: str`：会话唯一键（`channel:chat_id` 或覆盖值）

> 证据来源：`src/openharness/channels/bus/events.py` -> `InboundMessage`（行 8-24）

### OutboundMessage

发送到聊天通道的消息。

```python
@dataclass
class OutboundMessage:
    channel: str
    chat_id: str
    content: str
    reply_to: str | None = None
    media: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `reply_to` | `str \| None` | 回复目标消息 ID（用于 threading） |
| `media` | `list[str]` | 发送的媒体 URL 列表 |

> 证据来源：`src/openharness/channels/bus/events.py` -> `OutboundMessage`（行 27-36）

### ChannelBridge

通道桥接器：将 `MessageBus` 的入站消息连接到 `QueryEngine` 实例，并将回复发布回总线。

```python
class ChannelBridge:
    def __init__(self, *, engine: "QueryEngine", bus: MessageBus) -> None:
        self._engine: "QueryEngine"
        self._bus: MessageBus
        self._running: bool
        self._task: asyncio.Task | None

    async def start(self) -> None:
        """作为后台任务启动桥接循环"""

    async def stop(self) -> None:
        """优雅地停止桥接循环"""

    async def run(self) -> None:
        """内联运行（阻塞直到停止）"""

    async def _handle(self, msg: InboundMessage) -> None:
        """处理单条入站消息并发布回复"""
        # 消费消息 -> 提交给 QueryEngine -> 收集流事件 -> 发布 OutboundMessage
```

**内部处理流程：**
1. 从总线消费 `InboundMessage`
2. 调用 `QueryEngine.submit_message(msg.content)` 获得流事件
3. 聚合 `AssistantTextDelta` 文本增量
4. 将聚合文本作为 `OutboundMessage` 发布回总线

> 证据来源：`src/openharness/channels/adapter.py` -> `ChannelBridge`（行 29-131）

---

## Sandbox 层补充

### SandboxAvailability

沙箱运行时可用性计算结果。

```python
@dataclass(frozen=True)
class SandboxAvailability:
    enabled: bool
    available: bool
    reason: str | None = None
    command: str | None = None

    @property
    def active(self) -> bool:
        """沙箱是否应该应用到子进程"""
        return self.enabled and self.available
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `reason` | `str \| None` | 不可用原因（当 `available=False` 时） |
| `command` | `str \| None` | 可执行命令路径（当 `available=True` 时） |

> 证据来源：`src/openharness/sandbox/adapter.py` -> `SandboxAvailability`（行 21-33）

---

## Hook 定义补充

`HookDefinition` 联合类型已在 [配置参考](./config.md) 中说明。

| 类型 | 说明 |
|------|------|
| `CommandHookDefinition` | 执行 shell 命令 |
| `PromptHookDefinition` | 请求模型验证条件 |
| `HttpHookDefinition` | POST 事件负载到 HTTP 端点 |
| `AgentHookDefinition` | 执行 Agent 深度验证 |

---

## 证据索引

1. `src/openharness/engine/messages.py` -> `ConversationMessage`、`TextBlock`、`ImageBlock`、`ToolUseBlock`、`ToolResultBlock`（行 14-148）
2. `src/openharness/engine/stream_events.py` -> `AssistantTextDelta`、`AssistantTurnComplete`、`ToolExecutionStarted`、`ToolExecutionCompleted`、`ErrorEvent`、`StatusEvent`、`CompactProgressEvent`、`StreamEvent`（行 12-89）
3. `src/openharness/engine/cost_tracker.py` -> `CostTracker`（行 8-24）
4. `src/openharness/tools/base.py` -> `ToolExecutionContext`、`ToolResult`、`BaseTool`、`ToolRegistry`（行 13-75）
5. `src/openharness/config/settings.py` -> `Settings`、`ProviderProfile`、`PermissionSettings`、`SandboxSettings`、`MemorySettings`、`ResolvedAuth`（行 41-737）
6. `src/openharness/mcp/types.py` -> `McpServerConfig` 联合类型、`McpStdioServerConfig`、`McpHttpServerConfig`、`McpWebSocketServerConfig`、`McpToolInfo`、`McpResourceInfo`、`McpConnectionStatus`（行 11-76）
7. `src/openharness/swarm/types.py` -> `BackendType`、`PaneBackendType`、`CreatePaneResult`、`BackendDetectionResult`、`TeammateIdentity`、`TeammateSpawnConfig`、`SpawnResult`、`TeammateMessage`、`TeammateExecutor`、`PaneBackend`（行 16-393）
8. `src/openharness/coordinator/agent_definitions.py` -> `AgentDefinition`、`AGENT_COLORS`、`EFFORT_LEVELS`、`PERMISSION_MODES`、`MEMORY_SCOPES`、`ISOLATION_MODES`（行 21-975）
9. `src/openharness/plugins/types.py` -> `PluginCommandDefinition`、`LoadedPlugin`（行 15-54）
10. `src/openharness/channels/bus/events.py` -> `InboundMessage`、`OutboundMessage`（行 8-36）
11. `src/openharness/channels/adapter.py` -> `ChannelBridge`（行 29-131）
12. `src/openharness/sandbox/adapter.py` -> `SandboxAvailability`（行 21-33）
13. `src/openharness/hooks/schemas.py` -> `HookDefinition` 联合类型及四个子类型（行 10-58）
