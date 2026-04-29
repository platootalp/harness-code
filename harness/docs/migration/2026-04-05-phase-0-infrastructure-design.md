# Phase 0: 基础设施设计

> 日期：2026-04-05
> 状态：设计阶段
> 对应 TypeScript：`src/` 全模块

---

## 1. 项目概述

### 1.1 技术栈

| 类别 | 技术 | 理由 |
|------|------|------|
| 运行时 | Python 3.11+ | async/await 原生支持，协程优化 |
| 类型检查 | mypy + Pydantic | 运行时类型验证，Zod 替代 |
| CLI UI | Textual | React-like 组件模型，现代 TUI |
| HTTP 客户端 | httpx | async 支持，类型安全 |
| WebSocket | websockets | async 原生 |
| Schema 验证 | Pydantic v2 | Python 原生，Zod 对应 |
| Shell 解析 | bashlex | Bash AST 解析 |
| 测试 | pytest + pytest-asyncio | async 测试支持 |
| 代码质量 | ruff + mypy | lint + type check |

### 1.2 项目结构

```
src_py/
├── pyproject.toml              # 项目配置
├── src/
│   └── claude_code/            # 主包
│       ├── __init__.py
│       ├── main.py             # CLI 入口
│       │
│       ├── models/             # 核心数据模型
│       │   ├── __init__.py
│       │   ├── message.py      # Message, Role, Content
│       │   ├── tool.py         # Tool, ToolResult, ToolUse
│       │   ├── task.py         # Task, TaskStatus
│       │   ├── session.py       # Session, SessionState
│       │   └── events.py       # StreamEvent types
│       │
│       ├── engine/             # 查询引擎
│       │   ├── __init__.py
│       │   ├── engine.py       # QueryEngine
│       │   ├── pipeline.py      # Query pipeline (AsyncGenerator)
│       │   ├── context.py      # Context management/compression
│       │   └── tools/
│       │       ├── __init__.py
│       │       ├── registry.py # ToolRegistry
│       │       └── orchestration.py  # ToolOrchestrator
│       │
│       ├── tools/              # 工具实现
│       │   ├── __init__.py
│       │   ├── base.py         # BaseTool
│       │   ├── bash.py         # BashTool
│       │   ├── file_read.py    # FileReadTool
│       │   ├── file_edit.py    # FileEditTool
│       │   └── ...             # 45+ tools
│       │
│       ├── commands/           # 命令实现
│       │   ├── __init__.py
│       │   ├── registry.py     # CommandRegistry
│       │   ├── base.py         # BaseCommand
│       │   └── ...             # 75+ commands
│       │
│       ├── cli/                # CLI UI
│       │   ├── __init__.py
│       │   ├── app.py         # ClaudeCodeApp (Textual)
│       │   ├── repl.py         # REPL screen
│       │   ├── output.py       # OutputHandler
│       │   └── style.py       # Styling
│       │
│       ├── bridge/             # IDE 桥接
│       │   ├── __init__.py
│       │   ├── protocol.py     # BridgeProtocol
│       │   ├── vscode.py       # VS Code 扩展
│       │   └── jetbrains.py    # JetBrains 插件
│       │
│       ├── services/           # 服务层
│       │   ├── __init__.py
│       │   ├── api/
│       │   │   ├── __init__.py
│       │   │   ├── client.py   # HTTPClient
│       │   │   ├── claude.py   # ClaudeAIClient (multi-provider)
│       │   │   └── errors.py   # Error types
│       │   ├── mcp/
│       │   │   ├── __init__.py
│       │   │   ├── client.py   # MCPClient
│       │   │   ├── protocol.py # MCPProtocol
│       │   │   └── auth.py    # OAuth provider
│       │   └── storage/
│       │       ├── __init__.py
│       │       └── session.py  # SessionStorage
│       │
│       ├── state/              # 状态管理
│       │   ├── __init__.py
│       │   ├── store.py        # Observable Store
│       │   └── hooks.py        # State hooks
│       │
│       ├── security/           # 安全层
│       │   ├── __init__.py
│       │   ├── rules.py        # SecurityRule engine
│       │   ├── permissions.py  # Permission checks
│       │   └── budgets.py      # Budget tracking
│       │
│       └── utils/              # 工具函数
│           ├── __init__.py
│           ├── shell.py        # Shell parsing
│           ├── attachments.py  # Attachment handling
│           └── token.py        # Token counting
│
└── tests/
    ├── conftest.py
    ├── test_models.py
    ├── test_engine.py
    ├── test_tools.py
    └── test_commands.py
```

---

## 2. 核心模型设计

### 2.1 Message 模型

对应 TypeScript：`src/models.ts` (implicit), `src/query.ts`

```python
"""Message data models."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Literal, Union


class Role(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


@dataclass
class ContentBlock:
    """Content block - supports text, tool_use, tool_result."""
    type: Literal["text", "tool_use", "tool_result"]
    text: str = ""
    id: str = ""          # tool_use id
    name: str = ""        # tool_use name
    input: dict[str, Any] = field(default_factory=dict)
    tool_use_id: str = ""  # tool_result reference
    content: str = ""      # tool_result content
    is_error: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "text": self.text,
            "id": self.id,
            "name": self.name,
            "input": self.input,
            "tool_use_id": self.tool_use_id,
            "content": self.content,
            "is_error": self.is_error,
        }


@dataclass
class Message:
    """Chat message."""
    role: Role
    content: Union[str, list[ContentBlock]]
    name: str | None = None
    tool_use_id: str | None = None
    tool_name: str | None = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        content = self.content
        if isinstance(content, list):
            content = [c.to_dict() if isinstance(c, ContentBlock) else c for c in content]
        return {
            "role": self.role.value,
            "content": content,
            "name": self.name,
            "tool_use_id": self.tool_use_id,
            "tool_name": self.tool_name,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Message:
        role = Role(data["role"])
        content = data["content"]
        if isinstance(content, list):
            content = [ContentBlock(**c) if isinstance(c, dict) else c for c in content]
        return cls(
            role=role,
            content=content,
            name=data.get("name"),
            tool_use_id=data.get("tool_use_id"),
            tool_name=data.get("tool_name"),
        )
```

### 2.2 Tool 模型

对应 TypeScript：`src/Tool.ts`

```python
"""Tool data models."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable


@dataclass
class ToolDefinition:
    """Tool definition for API."""
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass
class ToolResult:
    """Result from tool execution."""
    id: str
    tool_name: str
    input: dict[str, Any]
    output: str | None = None
    error: str | None = None
    is_error: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "tool_result",
            "id": self.id,
            "tool_name": self.tool_name,
            "input": self.input,
            "output": self.output,
            "error": self.error,
            "is_error": self.is_error,
        }


class ToolExecuteContext:
    """Context passed to tool during execution."""
    def __init__(
        self,
        working_directory: str = "",
        can_use_tool: Callable[[str], Awaitable[bool]] | None = None,
        parent_message_id: str | None = None,
        abort_signal: Any = None,
    ):
        self.working_directory = working_directory
        self.can_use_tool = can_use_tool
        self.parent_message_id = parent_message_id
        self.abort_signal = abort_signal


class BaseTool(ABC):
    """Base class for all tools.

    Corresponds to TypeScript Tool interface in src/Tool.ts
    """

    def __init__(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        max_result_size_chars: int = 100_000,
    ):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.max_result_size_chars = max_result_size_chars

    @abstractmethod
    async def execute(
        self,
        input_args: dict[str, Any],
        context: ToolExecuteContext | None = None,
    ) -> str:
        """Execute the tool with given input."""
        ...

    def isConcurrencySafe(self, input_args: dict[str, Any]) -> bool:
        """Whether this tool can run in parallel with others."""
        return False

    def isReadOnly(self, input_args: dict[str, Any]) -> bool:
        """Whether this tool modifies system state."""
        return False

    def isDestructive(self, input_args: dict[str, Any]) -> bool:
        """Whether this tool performs irreversible operations."""
        return False

    def isEnabled(self) -> bool:
        """Whether this tool is available in current context."""
        return True

    def get_metadata(self) -> dict[str, Any]:
        """Get tool metadata for API."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }
```

### 2.3 Task 模型

对应 TypeScript：`src/Task.ts`

```python
"""Task data models."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    KILLED = "killed"


class TaskType(str, Enum):
    LOCAL_BASH = "local_bash"
    LOCAL_AGENT = "local_agent"
    REMOTE_AGENT = "remote_agent"
    IN_PROCESS_TEAMMATE = "in_process_teammate"
    LOCAL_WORKFLOW = "local_workflow"
    MONITOR_MCP = "monitor_mcp"
    DREAM = "dream"


@dataclass
class Task:
    """Task representation."""
    id: str
    type: TaskType
    description: str
    dependencies: list[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    agent_id: str | None = None
    tool_use_id: str | None = None
    result: Any = None
    error: str | None = None
    output_file: str = ""
    output_offset: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime | None = None
    notified: bool = False

    def is_terminal(self) -> bool:
        return self.status in (
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.KILLED,
        )
```

### 2.4 Session 模型

对应 TypeScript：`src/state/AppStateStore.ts`

```python
"""Session data models."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from .message import Message


@dataclass
class Session:
    """Session state."""
    id: str
    messages: list[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    model: str = "claude-opus-4-6"
    system_prompt: str | None = None
    context_overflow: bool = False
    total_tokens: int = 0
    total_cost: float = 0.0

    def add_message(self, message: Message) -> None:
        self.messages.append(message)
        self.updated_at = datetime.now()


@dataclass
class AppState:
    """Global application state."""
    session_id: str | None = None
    current_agent_id: str | None = None
    is_streaming: bool = False
    is_compressing: bool = False
    tool_registry_version: int = 0
    permission_mode: str = "auto"
    model: str = "claude-opus-4-6"
    mcp_servers: dict[str, Any] = field(default_factory=dict)
```

### 2.5 Event 模型

对应 TypeScript：`src/query.ts` StreamEvent types

```python
"""Event types for streaming."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal


@dataclass
class StreamEvent:
    """Base stream event."""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ThinkingEvent(StreamEvent):
    """Thinking/throttling event."""
    type: Literal["thinking"] = "thinking"
    thinking: str = ""


@dataclass
class ToolUseEvent(StreamEvent):
    """Tool use event."""
    type: Literal["tool_use"] = "tool_use"
    id: str = ""
    name: str = ""
    input: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResultEvent(StreamEvent):
    """Tool result event."""
    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str = ""
    content: str = ""
    is_error: bool = False


@dataclass
class MessageStartEvent(StreamEvent):
    """Message start event."""
    type: Literal["message_start"] = "message_start"
    message: dict[str, Any] = field(default_factory=dict)


@dataclass
class ContentBlockStartEvent(StreamEvent):
    """Content block start event."""
    type: Literal["content_block_start"] = "content_block_start"
    index: int = 0
    block: dict[str, Any] = field(default_factory=dict)


@dataclass
class ContentBlockDeltaEvent(StreamEvent):
    """Content block delta event."""
    type: Literal["content_block_delta"] = "content_block_delta"
    index: int = 0
    delta: dict[str, Any] = field(default_factory=dict)


@dataclass
class MessageDeltaEvent(StreamEvent):
    """Message delta event."""
    type: Literal["message_delta"] = "message_delta"
    delta: dict[str, Any] = field(default_factory=dict)
    usage: dict[str, Any] = field(default_factory=dict)


@dataclass
class MessageStopEvent(StreamEvent):
    """Message stop event."""
    type: Literal["message_stop"] = "message_stop"


@dataclass
class TombstoneEvent(StreamEvent):
    """Message deletion signal."""
    type: Literal["tombstone"] = "tombstone"
    message_id: str = ""
```

---

## 3. 状态存储设计

对应 TypeScript：`src/state/store.ts`

```python
"""Observable state store."""
from __future__ import annotations
from typing import Any, Callable, Generic, TypeVar
from dataclasses import dataclass, field
import asyncio


T = TypeVar("T")


@dataclass
class Store(Generic[T]):
    """Observable store for state management.

    TypeScript equivalent: src/state/store.ts
    """
    _state: T
    _listeners: list[Callable[[T, T], None]] = field(default_factory=list)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def get_state(self) -> T:
        return self._state

    def set_state(self, updater: Callable[[T], T]) -> None:
        prev = self._state
        self._state = updater(prev)
        for listener in self._listeners:
            listener(prev, self._state)

    def subscribe(self, listener: Callable[[T, T], None]) -> Callable[[], None]:
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    async def set_state_async(self, updater: Callable[[T], T]) -> None:
        async with self._lock:
            prev = self._state
            self._state = updater(prev)
            for listener in self._listeners:
                listener(prev, self._state)


# Global state instance
_app_state = AppState()
app_store: Store[AppState] = Store(_app_state)
_messages_store: Store[list[Message]] = Store([])


def get_app_state() -> AppState:
    return app_store.get_state()


def update_app_state(updater: Callable[[AppState], AppState]) -> None:
    app_store.set_state(updater)


def get_messages() -> list[Message]:
    return _messages_store.get_state()


def update_messages(updater: Callable[[list[Message]], list[Message]]) -> None:
    _messages_store.set_state(updater)
```

---

## 4. API 客户端设计

对应 TypeScript：`src/services/api/claude.ts`

### 4.1 HTTP 客户端

```python
"""HTTP client for API calls."""
from __future__ import annotations
import httpx
from typing import Any, AsyncGenerator
import asyncio


class HTTPClient:
    """Async HTTP client with retry and timeout."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 60.0,
        max_retries: int = 3,
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> HTTPClient:
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout),
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()

    async def post(
        self,
        url: str,
        json: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        assert self._client is not None
        return await self._client.post(url, json=json, headers=headers)

    async def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        assert self._client is not None
        return await self._client.get(url, params=params, headers=headers)

    async def stream_post(
        self,
        url: str,
        json: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> AsyncGenerator[bytes, None]:
        """Streaming POST request."""
        assert self._client is not None
        async with self._client.stream("POST", url, json=json, headers=headers) as response:
            async for chunk in response.aiter_bytes():
                yield chunk
```

### 4.2 Claude API 客户端 (Multi-Provider)

```python
"""Anthropic Claude API client with multi-provider support."""
from __future__ import annotations
import os
from typing import Any, AsyncGenerator, Literal
from .client import HTTPClient
from ..models.message import Message, Role


class ClaudeProvider(str, Enum):
    DIRECT = "direct"      # Direct API
    AWS_BEDROCK = "bedrock"
    AZURE_FOUNDRY = "foundry"
    GOOGLE_VERTEX = "vertex"


class ClaudeAIClient:
    """Client for Anthropic Claude API.

    Supports multiple providers:
    - Direct API (ANTHROPIC_API_KEY)
    - AWS Bedrock
    - Azure Foundry
    - Google Vertex
    """

    def __init__(
        self,
        api_key: str | None = None,
        provider: ClaudeProvider = ClaudeProvider.DIRECT,
        model: str = "claude-opus-4-6",
    ):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.provider = provider
        self.model = model
        self.base_url = self._get_base_url()
        self.http = HTTPClient(base_url=self.base_url)

    def _get_base_url(self) -> str:
        match self.provider:
            case ClaudeProvider.DIRECT:
                return "https://api.anthropic.com/v1"
            case ClaudeProvider.AWS_BEDROCK:
                return f"https://bedrock.{os.environ.get('AWS_REGION', 'us-east-1')}.amazonaws.com"
            case ClaudeProvider.AZURE_FOUNDRY:
                return os.environ.get("ANTHROPIC_FOUNDRY_ENDPOINT", "")
            case ClaudeProvider.GOOGLE_VERTEX:
                return f"https://{os.environ.get('ANTHROPIC_VERTEX_PROJECT_ID')}-aiplatform.googleapis.com"
            case _:
                return "https://api.anthropic.com/v1"

    def _get_headers(self) -> dict[str, str]:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
            "x-app": "cli",
        }
        # Add session ID header
        # Add client request ID
        return headers

    async def chat_complete(
        self,
        messages: list[Message],
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        thinking: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Non-streaming chat completion."""
        payload = {
            "model": self.model,
            "messages": [self._message_to_dict(m) for m in messages],
            "max_tokens": max_tokens,
        }
        if system:
            payload["system"] = system
        if tools:
            payload["tools"] = tools
        if thinking:
            payload["thinking"] = thinking

        async with self.http:
            response = await self.http.post("/messages", json=payload, headers=self._get_headers())
            response.raise_for_status()
            return response.json()

    async def stream_complete(
        self,
        messages: list[Message],
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Streaming chat completion (NDJSON)."""
        payload = {
            "model": self.model,
            "messages": [self._message_to_dict(m) for m in messages],
            "max_tokens": max_tokens,
            "stream": True,
        }
        if system:
            payload["system"] = system
        if tools:
            payload["tools"] = tools

        async with self.http:
            async for chunk in self.http.stream_post("/messages", json=payload, headers=self._get_headers()):
                line = chunk.decode().strip()
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    yield data

    def _message_to_dict(self, message: Message) -> dict[str, Any]:
        return message.to_dict()
```

### 4.3 错误类型

对应 TypeScript：`src/services/api/errors.ts`

```python
"""API error types."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class APIErrorType(str, Enum):
    RATE_LIMIT = "rate_limit"
    PROMPT_TOO_LONG = "prompt_too_long"
    AUTH_ERROR = "auth_error"
    TOKEN_REVOKED = "token_revoked"
    OVERAGE_DISABLED = "overage_disabled"
    CAPACITY_OFF_SWITCH = "capacity_off_switch"
    SERVER_OVERLOAD = "server_overload"
    CONNECTION_ERROR = "connection_error"
    SSL_CERT_ERROR = "ssl_cert_error"


@dataclass
class APIError(Exception):
    """Base API error."""
    type: APIErrorType
    message: str
    status_code: int | None = None
    retry_after: float | None = None  # seconds

    def __str__(self) -> str:
        return f"{self.type.value}: {self.message}"


class RateLimitError(APIError):
    """Rate limit exceeded."""
    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(APIErrorType.RATE_LIMIT, message)
        self.retry_after = retry_after


class AuthError(APIError):
    """Authentication error."""
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(APIErrorType.AUTH_ERROR, message, status_code)


class PromptTooLongError(APIError):
    """Context window exceeded."""
    def __init__(self, message: str, input_tokens: int | None = None, max_tokens: int | None = None):
        super().__init__(APIErrorType.PROMPT_TOO_LONG, message)
        self.input_tokens = input_tokens
        self.max_tokens = max_tokens
```

---

## 5. 安全层设计

对应 TypeScript：各工具中的 `checkPermissions` 和 `security-rules`

```python
"""Security rules engine."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class SecurityRule:
    """A security rule that can allow or deny an action."""
    name: str
    description: str
    check: Callable[[dict[str, Any]], bool]


class PermissionResult:
    """Result of a permission check."""
    def __init__(
        self,
        behavior: Literal["allow", "deny", "ask"],
        updated_input: dict[str, Any] | None = None,
        reason: str | None = None,
    ):
        self.behavior = behavior
        self.updated_input = updated_input
        self.reason = reason


class SecurityEngine:
    """Engine for evaluating security rules.

    Checks commands and actions against defined security rules.
    TypeScript equivalent: security layer in tools
    """

    def __init__(self):
        self._rules: list[SecurityRule] = []
        self._bypass_mode = False
        self._permission_mode = "auto"  # auto, bypassPermissions, deny

    def add_rule(self, rule: SecurityRule) -> None:
        """Add a security rule."""
        self._rules.append(rule)

    def set_permission_mode(self, mode: str) -> None:
        """Set permission mode: auto, bypassPermissions, deny."""
        self._permission_mode = mode

    def enable_bypass(self) -> None:
        """Enable bypass mode (for trusted sessions)."""
        self._bypass_mode = True

    def disable_bypass(self) -> None:
        """Disable bypass mode."""
        self._bypass_mode = False

    async def check_tool_permission(
        self,
        tool_name: str,
        input_args: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> PermissionResult:
        """Check if a tool execution is allowed."""
        if self._bypass_mode or self._permission_mode == "bypassPermissions":
            return PermissionResult("allow")

        if self._permission_mode == "deny":
            return PermissionResult("deny", reason="Permission mode is deny")

        # Run security rules
        ctx = {"tool_name": tool_name, "input": input_args, **(context or {})}
        for rule in self._rules:
            if not rule.check(ctx):
                return PermissionResult("deny", reason=f"Rule '{rule.name}' denied")

        # Default: ask for permission
        return PermissionResult("ask")

    def check_path(self, path: str, operation: str) -> bool:
        """Check if a path operation is allowed."""
        # Prevent path traversal
        normalized = os.path.normpath(path)
        if ".." in path or normalized.startswith("/"):
            return False
        return True

    def check_command(self, command: str, context: dict[str, Any] | None = None) -> tuple[bool, str]:
        """Check if a shell command is allowed.

        Returns (allowed, reason).
        """
        if self._bypass_mode:
            return True, "bypass_enabled"

        ctx = {"command": command, **(context or {})}
        for rule in self._rules:
            if not rule.check(ctx):
                return False, f"Rule '{rule.name}' denied: {rule.description}"

        return True, ""
```

---

## 6. 实施任务清单

### Phase 0.1: 项目脚手架
- [ ] 创建 `pyproject.toml`
- [ ] 创建目录结构
- [ ] 创建 `__init__.py` 文件
- [ ] 配置 mypy、ruff、pytest

### Phase 0.2: 核心模型
- [ ] 实现 `models/message.py`
- [ ] 实现 `models/tool.py`
- [ ] 实现 `models/task.py`
- [ ] 实现 `models/session.py`
- [ ] 实现 `models/events.py`

### Phase 0.3: 状态存储
- [ ] 实现 `state/store.py`
- [ ] 实现 `state/hooks.py`

### Phase 0.4: API 客户端
- [ ] 实现 `services/api/client.py`
- [ ] 实现 `services/api/claude.py`
- [ ] 实现 `services/api/errors.py`

### Phase 0.5: 安全层
- [ ] 实现 `security/rules.py`
- [ ] 实现 `security/permissions.py`
- [ ] 实现 `security/budgets.py`
