# Claude Code Python 迁移实施路线图

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用 Python 完全重写 TypeScript `src/` 模块，最终替代原版

**Architecture:** 采用模块化单体架构，核心模块包括：查询引擎(engine)、工具系统(tools)、命令系统(commands)、CLI UI(cli)、IDE桥接(bridge)、服务层(services)。各模块通过清晰接口通信，支持 async/await 流式处理。

**Tech Stack:** Python 3.11+, Textual, Pydantic, httpx, websockets, bashlex, pytest

---

## 实施概览

| Phase | 名称 | 周期 | 目标 |
|-------|------|------|------|
| 0 | 基础设施搭建 | 3-5 天 | 项目脚手架、数据模型、状态存储、API客户端 |
| 1 | 查询引擎 | 5-7 天 | QueryEngine、上下文压缩、工具注册表、基础工具 |
| 2 | CLI + REPL | 5-7 天 | Textual TUI、REPL界面、命令解析器 |
| 3 | 命令系统 | 5-7 天 | 命令注册表、核心命令实现 |
| 4 | 桥接系统 | 5-7 天 | IDE桥接协议、VS Code扩展 |
| 5 | 服务集成 | 5-7 天 | MCP客户端/服务器、安全规则 |
| 6 | 完善测试 | 持续 | 剩余工具/命令、测试覆盖 |

---

## Phase 0: 基础设施搭建

### Phase 0.1: 项目脚手架

**Files:**
- Create: `src_py/pyproject.toml`
- Create: `src_py/src/__init__.py`
- Create: `src_py/src/main.py`
- Create: `src_py/.gitignore`
- Create: `src_py/README.md`

- [ ] **Step 1: 创建 pyproject.toml**

```toml
[project]
name = "claude-code"
version = "0.1.0"
description = "Claude Code CLI - AI-powered coding assistant"
requires-python = ">=3.11"
dependencies = [
    "textual>=0.50.0",
    "pydantic>=2.0",
    "httpx>=0.25.0",
    "websockets>=12.0",
    "bashlex>=0.18",
    "rich>=13.0",
    "click>=8.0",
    "typer>=0.9.0",
    "anthropic>=0.20.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.0",
    "mypy>=1.8.0",
    "ruff>=0.2.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.mypy]
python_version = "3.11"
strict = true

[tool.ruff]
line-length = 100
target-version = "py311"
```

- [ ] **Step 2: 创建目录结构**

```bash
mkdir -p src_py/src/{models,engine/tools,tools,commands,cli,bridge,services/{api,mcp,storage},state,security,utils}
mkdir -p src_py/tests/{models,engine,tools,commands,cli}
touch src_py/src/__init__.py
touch src_py/src/models/__init__.py
# ... 其余 __init__.py 文件
```

- [ ] **Step 3: 创建 main.py 入口**

```python
"""Claude Code CLI - Main entry point."""
import sys
import click
from typing import Optional

__version__ = "0.1.0"


@click.group()
@click.version_option(version=__version__)
def cli() -> None:
    """Claude Code - AI-powered coding assistant."""
    pass


@cli.command()
@click.argument("prompt", required=False)
@click.option("--model", "-m", help="Model to use")
@click.option("--no-stream", is_flag=True, help="Disable streaming")
def ask(prompt: Optional[str], model: Optional[str], no_stream: bool) -> None:
    """Send a prompt to Claude."""
    from src.engine.engine import QueryEngine
    # Implementation...


if __name__ == "__main__":
    cli()
```

### Phase 0.2: 数据模型

**Files:**
- Create: `src_py/src/models/message.py`
- Create: `src_py/src/models/tool.py`
- Create: `src_py/src/models/task.py`
- Create: `src_py/src/models/session.py`
- Create: `src_py/src/models/events.py`
- Modify: `src_py/src/models/__init__.py`

- [ ] **Step 1: 创建 Message 模型**

```python
"""Message data models."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Literal


class Role(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


@dataclass
class Content:
    """Message content - supports text and tool use blocks."""
    type: Literal["text", "tool_use", "tool_result"]
    text: str = ""
    id: str = ""  # tool_use id
    name: str = ""  # tool_use name
    input: dict[str, Any] = field(default_factory=dict)
    tool_use_id: str = ""  # tool_result
    content: str = ""  # tool_result

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "text": self.text,
            "id": self.id,
            "name": self.name,
            "input": self.input,
            "tool_use_id": self.tool_use_id,
            "content": self.content,
        }


@dataclass
class Message:
    """Chat message."""
    role: Role
    content: str | list[Content]
    name: str | None = None
    tool_use_id: str | None = None
    tool_name: str | None = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role.value,
            "content": self.content if isinstance(self.content, str) else [c.to_dict() for c in self.content],
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
            content = [Content(**c) for c in content]
        return cls(
            role=role,
            content=content,
            name=data.get("name"),
            tool_use_id=data.get("tool_use_id"),
            tool_name=data.get("tool_name"),
        )
```

- [ ] **Step 2: 创建 Tool 相关模型**

```python
"""Tool data models."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable


@dataclass
class ToolDefinition:
    """Tool definition for API."""
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass
class ToolResult:
    """Result from a tool execution."""
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
```

- [ ] **Step 3: 创建 Task 模型**

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
    CANCELLED = "cancelled"


@dataclass
class Task:
    """Task representation."""
    id: str
    description: str
    dependencies: list[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    agent_id: str | None = None
    result: Any = None
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def is_terminal(self) -> bool:
        return self.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
```

- [ ] **Step 4: 创建 Session 模型**

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

    def add_message(self, message: Message) -> None:
        self.messages.append(message)
        self.updated_at = datetime.now()
```

- [ ] **Step 5: 创建 Event 模型**

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
    type: str = ""


@dataclass
class ThinkingEvent(StreamEvent):
    """Thinking/throttling event."""
    type: Literal["thinking"] = "thinking"
    content: str = ""


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
class MessageEvent(StreamEvent):
    """Final message event."""
    type: Literal["message"] = "message"
    content: str = ""
```

### Phase 0.3: 状态存储

**Files:**
- Create: `src_py/src/state/store.py`
- Create: `src_py/src/state/hooks.py`
- Modify: `src_py/src/state/__init__.py`

- [ ] **Step 1: 创建 Observable Store**

```python
"""Observable state store - implements the store pattern."""
from __future__ import annotations
from typing import Any, Callable, Generic, TypeVar
from dataclasses import dataclass
import asyncio


T = TypeVar("T")


@dataclass
class Store(Generic[T]):
    """Observable store for state management.

    TypeScript equivalent: state/store.ts
    """
    _state: T
    _listeners: list[Callable[[T, T], None]] = field(default_factory=list)

    def get_state(self) -> T:
        return self._state

    def set_state(self, updater: Callable[[T], T]) -> None:
        prev = self._state
        self._state = updater(prev)
        self._notify(prev, self._state)

    def subscribe(self, listener: Callable[[T, T], None]) -> Callable[[], None]:
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    def _notify(self, prev: T, next_: T) -> None:
        for listener in self._listeners:
            listener(prev, next_)


@dataclass
class AppState:
    """Global application state."""
    session_id: str | None = None
    current_agent_id: str | None = None
    is_streaming: bool = False
    is_compressing: bool = False
    tool_registry_version: int = 0


# Global state instance
_app_state = AppState()
app_store = Store[AppState](_app_state)


def get_app_state() -> AppState:
    return app_store.get_state()


def update_app_state(updater: Callable[[AppState], AppState]) -> None:
    app_store.set_state(updater)
```

### Phase 0.4: API 客户端

**Files:**
- Create: `src_py/src/services/api/client.py`
- Create: `src_py/src/services/api/claude.py`
- Modify: `src_py/src/services/api/__init__.py`

- [ ] **Step 1: 创建 HTTP 客户端基础**

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
        return await self._client.post(url, json=json, headers=headers)  # type: ignore

    async def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        return await self._client.get(url, params=params, headers=headers)  # type: ignore
```

- [ ] **Step 2: 创建 Anthropic API 客户端**

```python
"""Anthropic Claude API client."""
from __future__ import annotations
import os
from typing import Any, AsyncGenerator
from .client import HTTPClient
from ...models.message import Message, Role


class ClaudeAIClient:
    """Client for Anthropic Claude API."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.base_url = "https://api.anthropic.com/v1"
        self.model = "claude-opus-4-6"
        self.http = HTTPClient(base_url=self.base_url)

    def _get_headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

    async def chat_complete(
        self,
        messages: list[Message],
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
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
        """Streaming chat completion."""
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
            async with self.http._client.stream("POST", "/messages", json=payload, headers=self._get_headers()) as response:  # type: ignore
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        yield data

    def _message_to_dict(self, message: Message) -> dict[str, Any]:
        return message.to_dict()
```

---

## Phase 1: 查询引擎

### Phase 1.1: QueryEngine 核心

**Files:**
- Create: `src_py/src/engine/engine.py`
- Create: `src_py/src/engine/pipeline.py`
- Create: `src_py/src/engine/context.py`
- Modify: `src_py/src/engine/__init__.py`

- [ ] **Step 1: 创建 QueryEngine**

```python
"""QueryEngine - core query processing engine."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator
import asyncio

from ..models.message import Message
from ..models.events import StreamEvent, ThinkingEvent, ToolUseEvent, ToolResultEvent, MessageEvent
from ..services.api.claude import ClaudeAIClient
from .tools.registry import ToolRegistry
from .context import ContextManager


@dataclass
class QueryEngine:
    """Core query processing engine.

    TypeScript equivalent: QueryEngine.ts
    """
    api_client: ClaudeAIClient
    tool_registry: ToolRegistry
    context_manager: ContextManager
    max_concurrent_tools: int = 10

    _session_id: str | None = field(default=None)
    _is_running: bool = field(default=False)

    async def submit_message(
        self,
        prompt: str,
        messages: list[Message],
        system: str | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """Submit a message and process the response stream.

        Yields stream events (thinking, tool_use, tool_result, message).
        """
        self._is_running = True

        try:
            # Compress context if needed
            if await self.context_manager.should_compress(messages):
                messages = await self.context_manager.compress(messages)

            # Add user message
            messages.append(Message(role=Role.USER, content=prompt))

            # Get tools
            tools = self.tool_registry.list_tools()

            # Stream response
            async for event in self._stream_response(messages, system, tools):
                yield event

        finally:
            self._is_running = False

    async def _stream_response(
        self,
        messages: list[Message],
        system: str | None,
        tools: list[dict[str, Any]],
    ) -> AsyncGenerator[StreamEvent, None]:
        """Stream response from API."""
        # This would call the API and yield events
        # Implementation details...
        pass
```

- [ ] **Step 2: 创建上下文管理器**

```python
"""Context management and compression."""
from __future__ import annotations
from typing import Any
from ..models.message import Message, Role


class ContextManager:
    """Manages context window and compression.

    TypeScript equivalent: context.ts
    """

    MAX_TOKENS = 200000
    COMPRESSION_THRESHOLD = 0.8

    def __init__(self, max_tokens: int = MAX_TOKENS):
        self.max_tokens = max_tokens
        self.compression_ratio = self.COMPRESSION_THRESHOLD

    async def should_compress(self, messages: list[Message]) -> bool:
        """Check if context should be compressed."""
        total_tokens = self._estimate_tokens(messages)
        return total_tokens > (self.max_tokens * self.compression_ratio)

    async def compress(self, messages: list[Message]) -> list[Message]:
        """Compress messages using summarization."""
        # Simple compression: keep recent messages and summarize older ones
        # In production, this would call an LLM to summarize
        if len(messages) <= 4:
            return messages

        recent = messages[-4:]
        summary = Message(
            role=Role.SYSTEM,
            content=f"[Previous {len(messages) - 4} messages summarized]",
        )
        return [summary] + recent

    def _estimate_tokens(self, messages: list[Message]) -> int:
        """Rough token estimation (1 token ≈ 4 chars)."""
        total = 0
        for msg in messages:
            if isinstance(msg.content, str):
                total += len(msg.content) // 4
        return total
```

### Phase 1.2: 工具注册表

**Files:**
- Create: `src_py/src/engine/tools/registry.py`
- Create: `src_py/src/engine/tools/orchestration.py`
- Modify: `src_py/src/engine/tools/__init__.py`

- [ ] **Step 1: 创建工具注册表**

```python
"""Tool registry - manages available tools."""
from __future__ import annotations
from typing import Any
from ...models.tool import ToolDefinition


class ToolRegistry:
    """Registry for available tools.

    TypeScript equivalent: tools.ts
    """

    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[dict[str, Any]]:
        """List all tools as API-compatible format."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in self._tools.values()
        ]

    def unregister(self, name: str) -> None:
        """Unregister a tool."""
        self._tools.pop(name, None)
```

- [ ] **Step 2: 创建工具编排器**

```python
"""Tool orchestration - coordinates tool execution."""
from __future__ import annotations
from typing import Any
import asyncio

from ...models.tool import ToolResult
from .registry import ToolRegistry


class ToolOrchestrator:
    """Orchestrates tool execution with concurrency control.

    TypeScript equivalent: toolOrchestration.ts
    """

    def __init__(self, registry: ToolRegistry, max_concurrent: int = 10):
        self.registry = registry
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._running_tools: dict[str, asyncio.Task] = {}

    async def execute_tool(
        self,
        tool_name: str,
        tool_id: str,
        input_args: dict[str, Any],
    ) -> ToolResult:
        """Execute a tool with concurrency control."""
        async with self._semaphore:
            tool = self.registry.get(tool_name)
            if not tool:
                return ToolResult(
                    id=tool_id,
                    tool_name=tool_name,
                    input=input_args,
                    error=f"Tool not found: {tool_name}",
                    is_error=True,
                )

            try:
                # Call tool implementation
                result = await tool.execute(input_args)
                return ToolResult(
                    id=tool_id,
                    tool_name=tool_name,
                    input=input_args,
                    output=result,
                )
            except Exception as e:
                return ToolResult(
                    id=tool_id,
                    tool_name=tool_name,
                    input=input_args,
                    error=str(e),
                    is_error=True,
                )

    async def execute_tools_parallel(
        self,
        tool_calls: list[dict[str, Any]],
    ) -> list[ToolResult]:
        """Execute multiple tools in parallel."""
        tasks = [
            self.execute_tool(call["name"], call["id"], call["input"])
            for call in tool_calls
        ]
        return await asyncio.gather(*tasks)
```

### Phase 1.3: 基础工具实现

**Files:**
- Create: `src_py/src/tools/base.py`
- Create: `src_py/src/tools/bash.py`
- Create: `src_py/src/tools/file_read.py`
- Create: `src_py/src/tools/file_edit.py`
- Create: `src_py/src/tools/glob.py`
- Create: `src_py/src/tools/grep.py`
- Create: `src_py/src/tools/web_fetch.py`
- Modify: `src_py/src/tools/__init__.py`

- [ ] **Step 1: 创建 BaseTool 抽象类**

```python
"""Base tool class - all tools inherit from this."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Callable, Awaitable
from dataclasses import dataclass


@dataclass
class ToolExecuteContext:
    """Context passed to tool during execution."""
    working_directory: str = ""
    can_use_tool: Callable[[str], Awaitable[bool]] | None = None
    parent_message_id: str | None = None


class BaseTool(ABC):
    """Base class for all tools.

    TypeScript equivalent: Tool.ts
    """

    def __init__(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
    ):
        self.name = name
        self.description = description
        self.input_schema = input_schema

    @abstractmethod
    async def execute(
        self,
        input_args: dict[str, Any],
        context: ToolExecuteContext | None = None,
    ) -> str:
        """Execute the tool with given input."""
        ...

    def get_metadata(self) -> dict[str, Any]:
        """Get tool metadata for API."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }
```

- [ ] **Step 2: 创建 BashTool**

```python
"""Bash tool - executes shell commands."""
from __future__ import annotations
import asyncio
import shlex
from typing import Any
from .base import BaseTool, ToolExecuteContext


class BashTool(BaseTool):
    """Execute bash commands.

    TypeScript equivalent: tools/BashTool/*
    """

    def __init__(self):
        super().__init__(
            name="Bash",
            description="Execute a bash command. Use for git, npm, shell commands, etc.",
            input_schema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The bash command to execute",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds",
                        "default": 30,
                    },
                    "workingDirectory": {
                        "type": "string",
                        "description": "Working directory for the command",
                    },
                },
                "required": ["command"],
            },
        )

    async def execute(
        self,
        input_args: dict[str, Any],
        context: ToolExecuteContext | None = None,
    ) -> str:
        command = input_args["command"]
        timeout = input_args.get("timeout", 30)
        cwd = input_args.get("workingDirectory") or (context.working_directory if context else None)

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            result = stdout.decode() if stdout else ""
            if stderr:
                result += "\n[stderr]\n" + stderr.decode()
            return result
        except asyncio.TimeoutError:
            proc.kill()
            return f"Command timed out after {timeout} seconds"
        except Exception as e:
            return f"Error executing command: {str(e)}"
```

- [ ] **Step 3: 创建 FileReadTool**

```python
"""File read tool - reads files from the filesystem."""
from __future__ import annotations
import os
from pathlib import Path
from typing import Any
from .base import BaseTool, ToolExecuteContext


class FileReadTool(BaseTool):
    """Read file contents.

    TypeScript equivalent: tools/FileReadTool/*
    """

    def __init__(self):
        super().__init__(
            name="FileRead",
            description="Read the contents of a file",
            input_schema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to read",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of lines to read",
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Line number to start reading from (0-indexed)",
                    },
                },
                "required": ["file_path"],
            },
        )

    async def execute(
        self,
        input_args: dict[str, Any],
        context: ToolExecuteContext | None = None,
    ) -> str:
        file_path = input_args["file_path"]
        limit = input_args.get("limit")
        offset = input_args.get("offset", 0)

        # Security: prevent path traversal
        file_path = os.path.normpath(file_path)

        try:
            with open(file_path, "r") as f:
                if offset:
                    f.seek(offset)
                if limit:
                    lines = [f.readline() for _ in range(limit)]
                    return "".join(lines)
                return f.read()
        except FileNotFoundError:
            return f"File not found: {file_path}"
        except Exception as e:
            return f"Error reading file: {str(e)}"
```

---

## Phase 2: CLI + REPL

### Phase 2.1: Textual TUI 应用

**Files:**
- Create: `src_py/src/cli/app.py`
- Create: `src_py/src/cli/repl.py`
- Create: `src_py/src/cli/output.py`
- Create: `src_py/src/cli/style.py`
- Modify: `src_py/src/cli/__init__.py`

- [ ] **Step 1: 创建 Textual App**

```python
"""Claude Code Textual TUI application."""
from __future__ import annotations
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Log, Input, Button
from textual.binding import Binding
from textual.containers import Container, VerticalScroll
from typing import Any


class ClaudeCodeApp(App):
    """Main Claude Code TUI application.

    TypeScript equivalent: main.tsx + screens/REPL.tsx
    """

    CSS = """
    Screen {
        background: $surface;
    }
    #output {
        height: 1fr;
        border: solid $primary;
    }
    #input {
        dock: bottom;
        height: 3;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+z", "suspend", "Suspend"),
        Binding("up", "history_prev", "History Prev", show=False),
        Binding("down", "history_next", "History Next", show=False),
    ]

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self._history: list[str] = []
        self._history_index: int = -1

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(Log(id="output", auto_scroll=True))
        yield Input(id="input", placeholder="Enter message to Claude...")
        yield Footer()

    async def on_mount(self) -> None:
        """Called when app is mounted."""
        input_widget = self.query_one("#input", Input)
        input_widget.focus()

    def action_suspend(self) -> None:
        """Suspend the application."""
        self.suspend()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        prompt = event.value
        if not prompt.strip():
            return

        self._history.append(prompt)
        self._history_index = len(self._history)

        log = self.query_one("#output", Log)
        await log.write_line(f"> {prompt}")

        # Process the prompt through QueryEngine
        # Implementation...

        input_widget = self.query_one("#input", Input)
        input_widget.value = ""

    def action_history_prev(self) -> None:
        """Navigate to previous history item."""
        if not self._history:
            return
        if self._history_index > 0:
            self._history_index -= 1
        input_widget = self.query_one("#input", Input)
        input_widget.value = self._history[self._history_index]

    def action_history_next(self) -> None:
        """Navigate to next history item."""
        if not self._history:
            return
        if self._history_index < len(self._history) - 1:
            self._history_index += 1
        input_widget = self.query_one("#input", Input)
        input_widget.value = self._history[self._history_index]
```

### Phase 2.2: 输出处理

**Files:**
- Create: `src_py/src/cli/output.py`

- [ ] **Step 1: 创建输出处理器**

```python
"""Output handling and formatting."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from rich.console import Console
from rich.markdown import Markdown
from rich.syntax import Syntax


console = Console()


@dataclass
class OutputBlock:
    """Output block with type and content."""
    type: str  # "text", "code", "tool_use", "tool_result", "error"
    content: str
    language: str | None = None
    tool_name: str | None = None
    is_error: bool = False


class OutputHandler:
    """Handles output rendering.

    TypeScript equivalent: cli/print.ts
    """

    def __init__(self, console: Console = console):
        self.console = console

    def print_text(self, text: str, **kwargs: Any) -> None:
        """Print plain text."""
        self.console.print(text, **kwargs)

    def print_markdown(self, text: str) -> None:
        """Print markdown text."""
        md = Markdown(text)
        self.console.print(md)

    def print_code(self, code: str, language: str = "bash") -> None:
        """Print syntax-highlighted code."""
        syntax = Syntax(code, language, theme="monokai")
        self.console.print(syntax)

    def print_tool_use(self, tool_name: str, input_args: dict[str, Any]) -> None:
        """Print tool use information."""
        self.console.print(f"[bold cyan]Using tool:[/bold cyan] {tool_name}")
        self.console.print(f"Input: {input_args}")

    def print_tool_result(self, result: str, is_error: bool = False) -> None:
        """Print tool result."""
        style = "red" if is_error else "green"
        prefix = "Error" if is_error else "Result"
        self.console.print(f"[bold {style}]{prefix}:[/bold {style}]")
        self.console.print(result)

    def print_streaming(self, text: str) -> None:
        """Print streaming text (no newline)."""
        self.console.print(text, end="")
```

---

## Phase 3: 命令系统

### Phase 3.1: 命令注册表

**Files:**
- Create: `src_py/src/commands/registry.py`
- Create: `src_py/src/commands/base.py`
- Modify: `src_py/src/commands/__init__.py`

- [ ] **Step 1: 创建命令基类**

```python
"""Base command class."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class CommandResult:
    """Result from command execution."""
    success: bool
    output: str = ""
    error: str | None = None


class BaseCommand(ABC):
    """Base class for all commands.

    TypeScript equivalent: commands.ts
    """

    def __init__(
        self,
        name: str,
        description: str,
        aliases: list[str] | None = None,
    ):
        self.name = name
        self.description = description
        self.aliases = aliases or []

    @abstractmethod
    async def execute(self, args: list[str], context: dict[str, Any]) -> CommandResult:
        """Execute the command with given arguments."""
        ...

    def get_help(self) -> str:
        """Get help text for this command."""
        return f"{self.name}: {self.description}"
```

- [ ] **Step 2: 创建命令注册表**

```python
"""Command registry - manages available commands."""
from __future__ import annotations
from typing import Any
from .base import BaseCommand, CommandResult


class CommandRegistry:
    """Registry for slash commands.

    TypeScript equivalent: commands.ts (command registration)
    """

    def __init__(self):
        self._commands: dict[str, BaseCommand] = {}

    def register(self, command: BaseCommand) -> None:
        """Register a command."""
        self._commands[command.name] = command
        for alias in command.aliases:
            self._commands[alias] = command

    def get(self, name: str) -> BaseCommand | None:
        """Get a command by name or alias."""
        return self._commands.get(name)

    def list_commands(self) -> list[BaseCommand]:
        """List all registered commands."""
        seen: set[str] = set()
        result: list[BaseCommand] = []
        for cmd in self._commands.values():
            if cmd.name not in seen:
                seen.add(cmd.name)
                result.append(cmd)
        return result

    async def execute(
        self,
        name: str,
        args: list[str],
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute a command by name."""
        command = self.get(name)
        if not command:
            return CommandResult(
                success=False,
                error=f"Command not found: {name}",
            )
        return await command.execute(args, context)
```

### Phase 3.2: 核心命令实现

**Files:**
- Create: `src_py/src/commands/commit.py`
- Create: `src_py/src/commands/branch.py`
- Create: `src_py/src/commands/config.py`
- Create: `src_py/src/commands/add.py`
- Create: `src_py/src/commands/help.py`

- [ ] **Step 1: 创建 CommitCommand**

```python
"""Git commit command."""
from __future__ import annotations
import subprocess
from typing import Any
from .base import BaseCommand, CommandResult


class CommitCommand(BaseCommand):
    """Git commit command.

    TypeScript equivalent: commands/commit.ts
    """

    def __init__(self):
        super().__init__(
            name="commit",
            description="Create a git commit",
            aliases=["ci"],
        )

    async def execute(self, args: list[str], context: dict[str, Any]) -> CommandResult:
        try:
            result = subprocess.run(
                ["git", "commit"] + args,
                capture_output=True,
                text=True,
            )
            return CommandResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr if result.returncode != 0 else None,
            )
        except Exception as e:
            return CommandResult(success=False, error=str(e))
```

- [ ] **Step 2: 创建 BranchCommand**

```python
"""Git branch command."""
from __future__ import annotations
import subprocess
from typing import Any
from .base import BaseCommand, CommandResult


class BranchCommand(BaseCommand):
    """Git branch management command.

    TypeScript equivalent: commands/branch/*
    """

    def __init__(self):
        super().__init__(
            name="branch",
            description="List, create, or delete branches",
        )

    async def execute(self, args: list[str], context: dict[str, Any]) -> CommandResult:
        try:
            result = subprocess.run(
                ["git", "branch"] + args,
                capture_output=True,
                text=True,
            )
            return CommandResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr if result.returncode != 0 else None,
            )
        except Exception as e:
            return CommandResult(success=False, error=str(e))
```

---

## Phase 4: 桥接系统

### Phase 4.1: IDE 桥接协议

**Files:**
- Create: `src_py/src/bridge/protocol.py`
- Create: `src_py/src/bridge/vscode.py`
- Create: `src_py/src/bridge/jetbrains.py`
- Modify: `src_py/src/bridge/__init__.py`

- [ ] **Step 1: 创建桥接协议**

```python
"""IDE Bridge protocol.

TypeScript equivalent: bridge/types.ts + bridge/bridgeMain.ts
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator
import asyncio
import json


@dataclass
class BridgeMessage:
    """Message in the bridge protocol."""
    type: str
    payload: dict[str, Any]
    id: str | None = None


class BridgeProtocol:
    """Protocol for IDE bridge communication.

    Handles message serialization, routing, and protocol versioning.
    """

    PROTOCOL_VERSION = "1.0"

    def __init__(self):
        self._handlers: dict[str, callable] = {}

    def register_handler(self, message_type: str, handler: callable) -> None:
        """Register a message handler."""
        self._handlers[message_type] = handler

    async def send_message(self, writer: asyncio.StreamWriter, message: BridgeMessage) -> None:
        """Send a message through the bridge."""
        data = json.dumps({
            "type": message.type,
            "payload": message.payload,
            "id": message.id,
            "version": self.PROTOCOL_VERSION,
        })
        writer.write(data.encode())
        await writer.drain()

    async def receive_message(self, reader: asyncio.StreamReader) -> BridgeMessage | None:
        """Receive a message from the bridge."""
        line = await reader.readline()
        if not line:
            return None
        data = json.loads(line.decode())
        return BridgeMessage(
            type=data["type"],
            payload=data["payload"],
            id=data.get("id"),
        )
```

---

## Phase 5: 服务集成

### Phase 5.1: MCP 客户端/服务器

**Files:**
- Create: `src_py/src/services/mcp/client.py`
- Create: `src_py/src/services/mcp/server.py`
- Create: `src_py/src/services/mcp/protocol.py`
- Modify: `src_py/src/services/mcp/__init__.py`

- [ ] **Step 1: 创建 MCP 客户端**

```python
"""MCP client implementation.

TypeScript equivalent: services/mcp/client.ts
"""
from __future__ import annotations
import json
import asyncio
from typing import Any, AsyncGenerator
from .protocol import MCPProtocol, MCPMessage


class MCPClient:
    """Client for Model Context Protocol.

    Connects to MCP servers and manages tool calls.
    """

    def __init__(self, server_url: str):
        self.server_url = server_url
        self.protocol = MCPProtocol()
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

    async def connect(self) -> None:
        """Connect to the MCP server."""
        self._reader, self._writer = await asyncio.open_connection(
            *self.server_url.split(":")
        )

    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()

    async def list_tools(self) -> list[dict[str, Any]]:
        """List available tools from the server."""
        message = MCPMessage(
            type="tools/list",
            payload={},
        )
        await self.protocol.send_message(self._writer, message)  # type: ignore
        response = await self.protocol.receive_message(self._reader)  # type: ignore
        return response.payload.get("tools", []) if response else []

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Call a tool on the MCP server."""
        message = MCPMessage(
            type="tools/call",
            payload={"name": tool_name, "arguments": arguments},
        )
        await self.protocol.send_message(self._writer, message)  # type: ignore
        response = await self.protocol.receive_message(self._reader)  # type: ignore
        return response.payload if response else {}
```

### Phase 5.2: 安全规则

**Files:**
- Create: `src_py/src/security/rules.py`
- Create: `src_py/src/security/permissions.py`
- Create: `src_py/src/security/budgets.py`
- Modify: `src_py/src/security/__init__.py`

- [ ] **Step 1: 创建安全规则引擎**

```python
"""Security rules engine.

TypeScript equivalent: security layer in various tools
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class SecurityRule:
    """A security rule that can allow or deny an action."""
    name: str
    description: str
    check: Callable[[dict[str, Any]], bool]


class SecurityEngine:
    """Engine for evaluating security rules.

    Checks commands and actions against defined security rules.
    """

    def __init__(self):
        self._rules: list[SecurityRule] = []
        self._bypass_mode = False

    def add_rule(self, rule: SecurityRule) -> None:
        """Add a security rule."""
        self._rules.append(rule)

    def enable_bypass(self) -> None:
        """Enable bypass mode (for trusted sessions)."""
        self._bypass_mode = True

    def disable_bypass(self) -> None:
        """Disable bypass mode."""
        self._bypass_mode = False

    async def check_command(self, command: str, context: dict[str, Any]) -> tuple[bool, str]:
        """Check if a command is allowed.

        Returns (allowed, reason).
        """
        if self._bypass_mode:
            return True, "bypass_enabled"

        for rule in self._rules:
            if not rule.check({"command": command, **context}):
                return False, f"Rule '{rule.name}' denied: {rule.description}"

        return True, ""

    def check_path(self, path: str, operation: str) -> bool:
        """Check if a path operation is allowed."""
        # Prevent path traversal
        if ".." in path or path.startswith("/"):
            return False
        return True
```

---

## Phase 6: 完善与测试

### Phase 6.1: 测试基础设施

**Files:**
- Create: `src_py/tests/conftest.py`
- Create: `src_py/tests/test_engine.py`
- Create: `src_py/tests/test_tools.py`
- Create: `src_py/tests/test_commands.py`
- Create: `src_py/tests/test_models.py`

- [ ] **Step 1: 创建 pytest 配置**

```python
"""Pytest configuration and fixtures."""
import pytest
import asyncio
from typing import AsyncGenerator


@pytest.fixture
def event_loop() -> AsyncGenerator:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_api_client():
    """Mock API client for testing."""
    from src.services.api.claude import ClaudeAIClient

    class MockClaudeAIClient(ClaudeAIClient):
        async def chat_complete(self, *args, **kwargs):
            return {"content": "mock response"}

        async def stream_complete(self, *args, **kwargs):
            yield '{"type": "content_block", "text": "mock streaming response"}'
            yield "[DONE]"

    return MockClaudeAIClient(api_key="test-key")


@pytest.fixture
def tool_registry():
    """Create a tool registry with basic tools."""
    from src.engine.tools.registry import ToolRegistry
    from src.tools.bash import BashTool
    from src.tools.file_read import FileReadTool

    registry = ToolRegistry()
    registry.register(BashTool())
    registry.register(FileReadTool())
    return registry
```

- [ ] **Step 2: 创建模型测试**

```python
"""Tests for data models."""
import pytest
from src.models.message import Message, Role, Content


def test_message_creation():
    """Test creating a message."""
    msg = Message(role=Role.USER, content="Hello")
    assert msg.role == Role.USER
    assert msg.content == "Hello"


def test_message_to_dict():
    """Test message serialization."""
    msg = Message(role=Role.USER, content="Hello")
    data = msg.to_dict()
    assert data["role"] == "user"
    assert data["content"] == "Hello"


def test_message_from_dict():
    """Test message deserialization."""
    data = {"role": "user", "content": "Hello"}
    msg = Message.from_dict(data)
    assert msg.role == Role.USER
    assert msg.content == "Hello"


def test_content_blocks():
    """Test content blocks for tool use."""
    content = Content(
        type="tool_use",
        id="tool_1",
        name="Bash",
        input={"command": "ls"},
    )
    assert content.type == "tool_use"
    assert content.name == "Bash"
```

- [ ] **Step 3: 创建工具测试**

```python
"""Tests for tools."""
import pytest
from src.tools.bash import BashTool
from src.tools.base import ToolExecuteContext


@pytest.mark.asyncio
async def test_bash_tool_simple_command():
    """Test executing a simple bash command."""
    tool = BashTool()
    result = await tool.execute({"command": "echo 'hello'"})
    assert "hello" in result


@pytest.mark.asyncio
async def test_bash_tool_with_timeout():
    """Test bash command with timeout."""
    tool = BashTool()
    result = await tool.execute({
        "command": "sleep 10",
        "timeout": 1,
    })
    assert "timed out" in result.lower()
```

---

## 实施检查点

### 检查点 0: 基础设施完成
- [ ] 项目脚手架可运行
- [ ] 数据模型通过测试
- [ ] 状态存储工作正常
- [ ] API 客户端可调用

### 检查点 1: 查询引擎完成
- [ ] QueryEngine 流式响应正常
- [ ] 上下文压缩工作
- [ ] 工具注册表正常
- [ ] 基础工具 (Bash, FileRead) 可用

### 检查点 2: CLI 完成
- [ ] Textual TUI 正常启动
- [ ] REPL 可输入消息
- [ ] 输出正确显示

### 检查点 3: 命令系统完成
- [ ] 命令注册成功
- [ ] 核心命令 (commit, branch) 可执行

### 检查点 4: 桥接系统完成
- [ ] IDE 桥接协议实现
- [ ] VS Code 扩展可通信

### 检查点 5: 服务集成完成
- [ ] MCP 客户端连接正常
- [ ] 安全规则生效

### 检查点 6: 完成
- [ ] 所有工具实现
- [ ] 所有命令实现
- [ ] 测试覆盖 > 80%
