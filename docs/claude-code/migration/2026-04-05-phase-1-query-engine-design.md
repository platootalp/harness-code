# Phase 1: 查询引擎设计

> 日期：2026-04-05
> 状态：设计阶段
> 对应 TypeScript：`src/QueryEngine.ts`, `src/query.ts`, `src/context.ts`

---

## 1. 架构概述

### 1.1 核心组件

```
QueryEngine
├── QueryPipeline (query.ts)
│   ├── ContextManager (context.ts)
│   │   ├── AutoCompact
│   │   ├── Snip (HISTORY_SNIP)
│   │   └── ContextCollapse
│   ├── ToolOrchestrator
│   │   ├── StreamingToolExecutor
│   │   └── ToolRegistry
│   └── StopHooks
├── APIClient (services/api/claude.py)
└── StateStore (state/store.py)
```

### 1.2 数据流

```
用户输入
    │
    ▼
QueryEngine.submit_message()
    │
    ▼
SystemPrompt 构建 (fetchSystemPromptParts)
    │
    ▼
QueryPipeline.query_loop()
    │
    ├─► AutoCompact 检查
    │       │
    │       ▼
    │   上下文压缩
    │
    ▼
API Stream (callModel)
    │
    ▼
StreamingToolExecutor (工具并行执行)
    │
    ▼
ToolOrchestrator (串行/并行批次)
    │
    ▼
循环或结束
```

---

## 2. QueryEngine 核心

对应 TypeScript：`src/QueryEngine.ts`

```python
"""QueryEngine - core query processing engine."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Literal
import asyncio

from ..models.message import Message, Role, ContentBlock
from ..models.events import (
    StreamEvent,
    ThinkingEvent,
    ToolUseEvent,
    ToolResultEvent,
    MessageStartEvent,
    ContentBlockStartEvent,
    ContentBlockDeltaEvent,
    MessageDeltaEvent,
    MessageStopEvent,
    TombstoneEvent,
)
from ..services.api.claude import ClaudeAIClient
from .tools.registry import ToolRegistry
from .context import ContextManager
from .pipeline import QueryState, QueryParams, QueryResult


@dataclass
class QueryEngine:
    """Core query processing engine.

    TypeScript equivalent: src/QueryEngine.ts

    Responsibilities:
        - System prompt assembly
        - Message submission and streaming
        - Tool orchestration coordination
        - Context management
        - Error recovery
    """

    api_client: ClaudeAIClient
    tool_registry: ToolRegistry
    context_manager: ContextManager

    # Configuration
    max_concurrent_tools: int = 10
    max_turns: int = 100
    model: str = "claude-opus-4-6"

    # Internal state
    _session_id: str | None = field(default=None)
    _is_running: bool = field(default=False)
    _turn_count: int = field(default=0)

    async def submit_message(
        self,
        prompt: str | list[ContentBlock],
        messages: list[Message],
        system: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """Submit a message and process the response stream.

        Args:
            prompt: User input (string or content blocks)
            messages: Conversation history
            system: System prompt override
            options: Additional options (uuid, isMeta, etc.)

        Yields:
            StreamEvent types (thinking, tool_use, tool_result, message, etc.)
        """
        self._is_running = True
        options = options or {}

        try:
            # Build system prompt
            system_prompt = system or await self._build_system_prompt()

            # Add user message
            user_message = Message(
                role=Role.USER,
                content=prompt if isinstance(prompt, str) else prompt,
            )
            messages.append(user_message)

            # Run query pipeline
            async for event in self._query_loop(messages, system_prompt, options):
                yield event
                self._turn_count += 1

        finally:
            self._is_running = False

    async def _build_system_prompt(self) -> str:
        """Build system prompt from parts.

        Fetches:
        - Git status
        - CLAUDE.md content
        - Custom prompts
        - Append prompts
        """
        parts = []

        # TODO: Fetch git status
        # TODO: Load CLAUDE.md files
        # TODO: Load custom prompts

        return "\n\n".join(parts)

    async def _query_loop(
        self,
        messages: list[Message],
        system: str,
        options: dict[str, Any],
    ) -> AsyncGenerator[StreamEvent, None]:
        """Main query loop - handles iteration, tool execution, and context management.

        TypeScript equivalent: query.ts::query() -> queryLoop()
        """
        state = QueryState(
            messages=messages,
            tool_registry=self.tool_registry,
            context_manager=self.context_manager,
            turn_count=self._turn_count,
        )

        while True:
            # Check max turns
            if state.turn_count >= self.max_turns:
                yield TombstoneEvent(message_id="max_turns_reached")
                break

            # Pre-query context preparation
            await self._prepare_context(state)

            # Get tools for this turn
            tools = self.tool_registry.list_tools()

            # Call API with streaming
            needs_follow_up = False
            tool_use_blocks: list[ContentBlock] = []

            async for event in self._call_model(state, system, tools):
                if isinstance(event, ThinkingEvent):
                    yield event

                elif isinstance(event, ContentBlockStartEvent):
                    if event.block.get("type") == "tool_use":
                        tool_use_blocks.append(ContentBlock(
                            type="tool_use",
                            id=event.block.get("id", ""),
                            name=event.block.get("name", ""),
                            input=event.block.get("input", {}),
                        ))
                    yield event

                elif isinstance(event, ContentBlockDeltaEvent):
                    # Accumulate delta into tool use block
                    if tool_use_blocks and event.index < len(tool_use_blocks):
                        block = tool_use_blocks[event.index]
                        if event.delta.get("type") == "input_json_delta":
                            # Accumulate input
                            pass
                    yield event

                elif isinstance(event, ToolUseEvent):
                    needs_follow_up = True
                    yield event

                elif isinstance(event, MessageStopEvent):
                    # Execute tools
                    if tool_use_blocks:
                        async for tool_event in self._execute_tools(state, tool_use_blocks):
                            yield tool_event

                elif isinstance(event, MessageStartEvent):
                    yield event

            # Check continuation conditions
            if not needs_follow_up and not tool_use_blocks:
                break

            # Update state for next iteration
            state = state.copy_with(turn_count=state.turn_count + 1)

    async def _call_model(
        self,
        state: QueryState,
        system: str,
        tools: list[dict[str, Any]],
    ) -> AsyncGenerator[StreamEvent, None]:
        """Call the API with streaming.

        TypeScript equivalent: query.ts::callModel()
        """
        async for chunk in self.api_client.stream_complete(
            messages=state.messages,
            system=system,
            tools=tools if tools else None,
        ):
            # Parse SSE data
            data = self._parse_sse_data(chunk)
            if data is None:
                continue

            # Convert to stream event
            event = self._convert_to_event(data)
            if event:
                yield event

    async def _prepare_context(self, state: QueryState) -> None:
        """Prepare context before API call.

        Operations:
        - HISTORY_SNIP: Remove protected-tail messages
        - Microcompact: Cache repeated tool results
        - ContextCollapse: Project collapsed context
        - AutoCompact: Summarize if near context limit
        """
        # Check if compression needed
        if await self.context_manager.should_compress(state.messages):
            # Run compaction
            state.messages = await self.context_manager.compress(state.messages)
            state.has_attempted_reactive_compact = True

    async def _execute_tools(
        self,
        state: QueryState,
        tool_blocks: list[ContentBlock],
    ) -> AsyncGenerator[StreamEvent, None]:
        """Execute tools with concurrency control.

        TypeScript equivalent: toolOrchestration.ts + StreamingToolExecutor.ts
        """
        from .tools.orchestration import ToolOrchestrator

        orchestrator = ToolOrchestrator(
            registry=self.tool_registry,
            max_concurrent=self.max_concurrent_tools,
        )

        # Partition tools: read-only (parallel) vs write (serial)
        batches = orchestrator.partition_tool_calls(tool_blocks)

        for batch in batches:
            if batch.is_concurrency_safe:
                # Execute batch in parallel
                results = await orchestrator.execute_parallel(batch.blocks)
            else:
                # Execute serially
                results = await orchestrator.execute_serial(batch.blocks)

            for result in results:
                yield ToolResultEvent(
                    tool_use_id=result.id,
                    content=result.output or result.error or "",
                    is_error=result.is_error,
                )

    def _parse_sse_data(self, chunk: str) -> dict[str, Any] | None:
        """Parse SSE data line."""
        # Handle NDJSON format
        import json
        try:
            return json.loads(chunk)
        except json.JSONDecodeError:
            return None

    def _convert_to_event(self, data: dict[str, Any]) -> StreamEvent | None:
        """Convert API response to StreamEvent."""
        event_type = data.get("type", "")

        match event_type:
            case "message_start":
                return MessageStartEvent(message=data.get("message", {}))
            case "content_block_start":
                return ContentBlockStartEvent(
                    index=data.get("index", 0),
                    block=data.get("block", {}),
                )
            case "content_block_delta":
                return ContentBlockDeltaEvent(
                    index=data.get("index", 0),
                    delta=data.get("delta", {}),
                )
            case "message_delta":
                return MessageDeltaEvent(
                    delta=data.get("delta", {}),
                    usage=data.get("usage", {}),
                )
            case "message_stop":
                return MessageStopEvent()
            case "thinking":
                return ThinkingEvent(thinking=data.get("thinking", ""))
            case _:
                return None
```

---

## 3. QueryPipeline 与状态

对应 TypeScript：`src/query.ts` State type

```python
"""Query pipeline state and parameters."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from ..models.message import Message


@dataclass
class QueryParams:
    """Parameters for query execution."""
    messages: list[Message]
    system_prompt: str | None = None
    tools: list[dict[str, Any]] = field(default_factory=list)
    max_output_tokens: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class QueryState:
    """State carried across query loop iterations.

    TypeScript equivalent: src/query.ts::State
    """
    messages: list[Message]
    tool_registry: Any  # ToolRegistry
    context_manager: Any  # ContextManager

    # Iteration tracking
    turn_count: int = 0

    # Context management
    auto_compact_tracking: dict[str, Any] | None = None
    has_attempted_reactive_compact: bool = False

    # Error recovery
    max_output_tokens_recovery_count: int = 0
    max_output_tokens_override: int | None = None

    # Tool execution
    pending_tool_use_summary: Any = None

    # Stop hooks
    stop_hook_active: bool = False

    # Continuation
    transition: str | None = None  # Continue type

    def copy_with(self, **kwargs: Any) -> QueryState:
        """Create a copy with updated fields."""
        import copy
        new_state = copy.copy(self)
        for key, value in kwargs.items():
            setattr(new_state, key, value)
        return new_state


@dataclass
class QueryResult:
    """Result from query execution."""
    reason: str  # "completed", "max_turns", "budget_exceeded", "abort"
    messages: list[Message] = field(default_factory=list)
    total_tokens: int = 0
    total_cost: float = 0.0
```

---

## 4. 上下文管理

对应 TypeScript：`src/context.ts` + `src/query/autoCompact.ts`

```python
"""Context management and compression."""
from __future__ import annotations
from typing import Any
from ..models.message import Message, Role


class ContextManager:
    """Manages context window and compression.

    TypeScript equivalent: src/context.ts, src/query/autoCompact.ts

    Features:
    - AutoCompact: Automatic summarization when near context limit
    - HISTORY_SNIP: Remove intermediate messages while protecting tail
    - Microcompact: Cache repeated tool results
    - ContextCollapse: Project collapsed context view
    """

    # Thresholds (from TypeScript)
    AUTOCOMPACT_BUFFER_TOKENS = 13_000
    WARNING_THRESHOLD_BUFFER_TOKENS = 20_000
    ERROR_THRESHOLD_BUFFER_TOKENS = 20_000
    MANUAL_COMPACT_BUFFER_TOKENS = 3_000

    # Snip protection
    PROTECTED_TAIL_MESSAGES = 10

    def __init__(
        self,
        max_tokens: int = 200_000,
        effective_context_window: int | None = None,
    ):
        self.max_tokens = max_tokens
        self.effective_context_window = effective_context_window or (max_tokens - self.AUTOCOMPACT_BUFFER_TOKENS)
        self.compression_ratio = 0.8

        # Tracking
        self._last_summarized_message_id: str | None = None
        self._consecutive_compact_failures = 0
        self.MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES = 3

    async def should_compress(self, messages: list[Message]) -> bool:
        """Check if context should be compressed.

        Triggers when:
        - Context exceeds ~93% of effective window
        - MANUAL_COMPACT requested
        """
        total_tokens = self._estimate_tokens(messages)
        threshold = self.effective_context_window * 0.93
        return total_tokens > threshold

    async def compress(
        self,
        messages: list[Message],
        custom_instructions: str | None = None,
    ) -> list[Message]:
        """Compress messages using summarization.

        Creates summary messages replacing multiple conversation turns.
        """
        if not messages:
            return messages

        # Check circuit breaker
        if self._consecutive_compact_failures >= self.MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES:
            # Too many failures, don't retry
            return messages

        try:
            # Identify message groups to summarize
            groups = self._group_messages(messages)

            if len(groups) <= 1:
                return messages  # Nothing to compress

            # Create summary for older groups
            summary_parts = []
            preserved_messages = []

            for i, group in enumerate(groups):
                if i >= len(groups) - 2:
                    # Keep last 2 groups
                    preserved_messages.extend(group)
                else:
                    # Summarize this group
                    summary = await self._summarize_group(group, custom_instructions)
                    summary_parts.append(summary)

            # Build compressed message list
            result: list[Message] = []

            if summary_parts:
                result.append(Message(
                    role=Role.SYSTEM,
                    content=f"[Summary of {len(groups) - 2} earlier turns]\n" + "\n\n".join(summary_parts),
                ))

            result.extend(preserved_messages)

            self._consecutive_compact_failures = 0
            return result

        except Exception:
            self._consecutive_compact_failures += 1
            raise

    async def _summarize_group(
        self,
        group: list[Message],
        instructions: str | None,
    ) -> str:
        """Summarize a group of messages using an LLM.

        In production, this would call a separate summarization model.
        """
        # Simple implementation: concatenate content
        content_parts = []
        for msg in group:
            if isinstance(msg.content, str):
                content_parts.append(f"{msg.role.value}: {msg.content}")
            elif isinstance(msg.content, list):
                for block in msg.content:
                    if block.type == "text" and block.text:
                        content_parts.append(f"{msg.role.value}: {block.text}")

        return f"Previous conversation ({len(group)} messages): " + " | ".join(content_parts[:5])

    def _group_messages(self, messages: list[Message]) -> list[list[Message]]:
        """Group messages by turn.

        A turn consists of a user message followed by assistant responses.
        """
        groups: list[list[Message]] = []
        current_group: list[Message] = []

        for msg in messages:
            current_group.append(msg)
            if msg.role == Role.ASSISTANT:
                groups.append(current_group)
                current_group = []

        if current_group:
            groups.append(current_group)

        return groups

    def snip(
        self,
        messages: list[Message],
        protected_tail: int | None = None,
    ) -> list[Message]:
        """Remove intermediate messages while preserving a protected tail.

        TypeScript equivalent: HISTORY_SNIP feature

        Args:
            messages: Message list to snip
            protected_tail: Number of recent messages to protect (default: PROTECTED_TAIL_MESSAGES)
        """
        protected_tail = protected_tail or self.PROTECTED_TAIL_MESSAGES

        if len(messages) <= protected_tail:
            return messages  # Nothing to snip

        # Keep protected tail + summary indicator
        tail = messages[-protected_tail:]
        removed_count = len(messages) - protected_tail

        return [
            Message(
                role=Role.SYSTEM,
                content=f"[{removed_count} earlier messages removed]",
            ),
            *tail,
        ]

    def _estimate_tokens(self, messages: list[Message]) -> int:
        """Rough token estimation.

        TypeScript uses tokenCountWithEstimation() for consistency.
        """
        total = 0
        for msg in messages:
            if isinstance(msg.content, str):
                # Rough estimate: 1 token ≈ 4 characters
                total += len(msg.content) // 4
            elif isinstance(msg.content, list):
                for block in msg.content:
                    if block.type == "text" and block.text:
                        total += len(block.text) // 4
                    elif block.type == "tool_use":
                        # Tool calls have overhead
                        total += 100 + len(str(block.input)) // 4

            # Role overhead
            total += 5

        return total

    def get_auto_compact_threshold(self) -> int:
        """Get the token count threshold for auto-compact."""
        return self.effective_context_window - self.AUTOCOMPACT_BUFFER_TOKENS

    def get_warning_threshold(self) -> int:
        """Get the token count for warning (93%+ of context)."""
        return self.effective_context_window - self.WARNING_THRESHOLD_BUFFER_TOKENS
```

---

## 5. 工具编排

对应 TypeScript：`src/services/tools/toolOrchestration.ts` + `StreamingToolExecutor.ts`

```python
"""Tool orchestration - coordinates tool execution."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator
import asyncio

from ..models.tool import ToolResult
from ..models.message import ContentBlock
from .registry import ToolRegistry


@dataclass
class ToolBatch:
    """A batch of tool calls for execution."""
    is_concurrency_safe: bool
    blocks: list[ContentBlock]


class ToolOrchestrator:
    """Orchestrates tool execution with concurrency control.

    TypeScript equivalent: src/services/tools/toolOrchestration.ts

    Features:
    - Partitions tools into batches (read-only vs write)
    - Read-only tools run in parallel (up to max_concurrent)
    - Write tools run serially
    - Streaming execution as tool_use blocks arrive
    """

    def __init__(self, registry: ToolRegistry, max_concurrent: int = 10):
        self.registry = registry
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)

    def partition_tool_calls(
        self,
        tool_blocks: list[ContentBlock],
    ) -> list[ToolBatch]:
        """Partition tool calls into batches.

        Rules:
        - Consecutive read-only tools batched together
        - Non-read-only tools become single-item batches
        """
        batches: list[ToolBatch] = []
        current_batch: list[ContentBlock] = []
        current_safe = True

        for block in tool_blocks:
            tool = self.registry.get(block.name)
            is_safe = tool.isConcurrencySafe(block.input) if tool else False

            if is_safe == current_safe:
                # Same safety level, add to batch
                current_batch.append(block)
            else:
                # Safety level changed, flush and start new batch
                if current_batch:
                    batches.append(ToolBatch(
                        is_concurrency_safe=current_safe,
                        blocks=current_batch,
                    ))
                current_batch = [block]
                current_safe = is_safe

        # Flush remaining
        if current_batch:
            batches.append(ToolBatch(
                is_concurrency_safe=current_safe,
                blocks=current_batch,
            ))

        return batches

    async def execute_parallel(
        self,
        blocks: list[ContentBlock],
    ) -> list[ToolResult]:
        """Execute multiple tools in parallel."""
        tasks = [
            self._execute_single(block.id, block.name, block.input)
            for block in blocks
        ]
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def execute_serial(
        self,
        blocks: list[ContentBlock],
    ) -> list[ToolResult]:
        """Execute tools one at a time."""
        results = []
        for block in blocks:
            result = await self._execute_single(block.id, block.name, block.input)
            results.append(result)
        return results

    async def _execute_single(
        self,
        tool_id: str,
        tool_name: str,
        input_args: dict[str, Any],
    ) -> ToolResult:
        """Execute a single tool with semaphore control."""
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
                result = await tool.execute(input_args)
                return ToolResult(
                    id=tool_id,
                    tool_name=tool_name,
                    input=input_args,
                    output=str(result),
                )
            except Exception as e:
                return ToolResult(
                    id=tool_id,
                    tool_name=tool_name,
                    input=input_args,
                    error=str(e),
                    is_error=True,
                )
```

---

## 6. 工具注册表

对应 TypeScript：`src/tools.ts`

```python
"""Tool registry - manages available tools."""
from __future__ import annotations
from typing import Any

from ..models.tool import ToolDefinition
from .base import BaseTool


class ToolRegistry:
    """Registry for available tools.

    TypeScript equivalent: src/tools.ts
    """

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
        self._tool_definitions: dict[str, ToolDefinition] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool
        self._tool_definitions[tool.name] = ToolDefinition(
            name=tool.name,
            description=tool.description,
            input_schema=tool.input_schema,
        )

    def get(self, name: str) -> BaseTool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[dict[str, Any]]:
        """List all tools as API-compatible format."""
        return [
            tool.get_metadata()
            for tool in self._tools.values()
            if tool.isEnabled()
        ]

    def unregister(self, name: str) -> None:
        """Unregister a tool."""
        self._tools.pop(name, None)
        self._tool_definitions.pop(name, None)

    def get_by_alias(self, alias: str) -> BaseTool | None:
        """Get a tool by alias."""
        for tool in self._tools.values():
            if hasattr(tool, 'aliases') and alias in tool.aliases:
                return tool
        return None

    def filter_tools(
        self,
        permission_context: dict[str, Any] | None = None,
        simple_mode: bool = False,
    ) -> list[BaseTool]:
        """Filter tools based on permission context.

        TypeScript equivalent: getTools() in tools.ts
        """
        filtered = []
        for tool in self._tools.values():
            if not tool.isEnabled():
                continue

            # TODO: Apply permission filters
            # TODO: Apply simple_mode filters (Bash, Read, Edit only)

            filtered.append(tool)

        return filtered

    def assemble_tool_pool(
        self,
        mcp_tools: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Combine built-in tools with MCP tools.

        TypeScript equivalent: assembleToolPool() in tools.ts
        """
        pool = self.list_tools()

        # Add MCP tools (deduplicated)
        if mcp_tools:
            builtin_names = {t["name"] for t in pool}
            for mcp_tool in mcp_tools:
                if mcp_tool["name"] not in builtin_names:
                    pool.append(mcp_tool)

        # Sort alphabetically for prompt-cache stability
        pool.sort(key=lambda t: t["name"])

        return pool
```

---

## 7. 错误处理

对应 TypeScript：`src/services/api/errors.ts` + `src/query.ts` error handling

```python
"""Error handling and recovery."""
from __future__ import annotations
from typing import Any
from enum import Enum


class ErrorAction(Enum):
    """Error recovery actions."""
    RETRY = "retry"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    FALLBACK_MODEL = "fallback_model"
    RECOVER_OUTPUT = "recover_output"
    MARK_FAILED = "mark_failed"
    ASK_USER = "ask_user"


class ErrorRecoveryConfig:
    """Configuration for error recovery."""
    def __init__(
        self,
        max_retries: int = 10,
        base_backoff_seconds: float = 0.5,
        max_backoff_seconds: float = 60.0,
        max_consecutive_529_errors: int = 3,
        max_output_tokens_recovery_limit: int = 3,
    ):
        self.max_retries = max_retries
        self.base_backoff_seconds = base_backoff_seconds
        self.max_backoff_seconds = max_backoff_seconds
        self.max_consecutive_529_errors = max_consecutive_529_errors
        self.max_output_tokens_recovery_limit = max_output_tokens_recovery_limit


class QueryErrorHandler:
    """Handles errors during query execution.

    TypeScript equivalent: Error handling in query.ts
    """

    def __init__(self, config: ErrorRecoveryConfig | None = None):
        self.config = config or ErrorRecoveryConfig()
        self._retry_counters: dict[str, int] = {}
        self._partial_outputs: dict[str, str] = {}

    async def handle_error(
        self,
        error: Exception,
        context: dict[str, Any],
    ) -> ErrorAction:
        """Determine recovery action for an error.

        Flow:
        1. Check if error is retryable
        2. Check retry budget
        3. Check if API error (429, 500, etc.) → fallback model
        4. Check for partial output → recover
        5. Retry with backoff
        6. Mark failed
        """
        task_id = context.get("task_id", "")
        is_api_error = self._is_api_error(error)

        # 1. Is retryable?
        if not self._is_retryable(error):
            return ErrorAction.ASK_USER

        # 2. Check retry budget
        retry_count = self._retry_counters.get(task_id, 0)
        if retry_count >= self.config.max_retries:
            return ErrorAction.ASK_USER

        # 3. API error → fallback model
        if is_api_error:
            if self._is_rate_limit_error(error):
                return ErrorAction.RETRY_WITH_BACKOFF
            if self._is_server_overload(error):
                return ErrorAction.FALLBACK_MODEL

        # 4. Partial output recovery
        partial = self._partial_outputs.get(task_id)
        if partial and self._has_meaningful_output(partial):
            return ErrorAction.RECOVER_OUTPUT

        # 5. Retry with backoff
        self._retry_counters[task_id] = retry_count + 1
        return ErrorAction.RETRY_WITH_BACKOFF

    def _is_retryable(self, error: Exception) -> bool:
        """Determine if an error is retryable."""
        retryable_types = (
            TimeoutError,
            ConnectionError,
            asyncio.TimeoutError,
        )

        error_msg = str(error).lower()
        retryable_keywords = (
            "timeout", "connection", "network",
            "rate limit", "429", "500", "503", "529",
        )

        return isinstance(error, retryable_types) or any(
            kw in error_msg for kw in retryable_keywords
        )

    def _is_api_error(self, error: Exception) -> bool:
        """Check if error is an API error."""
        error_msg = str(error).lower()
        api_keywords = (
            "auth", "api", "401", "403", "429",
            "500", "502", "503", "rate limit",
        )
        return any(kw in error_msg for kw in api_keywords)

    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Check if error is a rate limit error."""
        return "429" in str(error) or "rate limit" in str(error).lower()

    def _is_server_overload(self, error: Exception) -> bool:
        """Check if error is a server overload error."""
        return "529" in str(error) or "overload" in str(error).lower()

    def _has_meaningful_output(self, output: str) -> bool:
        """Check if partial output is meaningful enough to recover."""
        return len(output.strip()) > 50

    def save_partial_output(self, task_id: str, output: str) -> None:
        """Save partial output for recovery."""
        self._partial_outputs[task_id] = output

    def clear_partial_output(self, task_id: str) -> None:
        """Clear partial output after successful recovery."""
        self._partial_outputs.pop(task_id, None)
```

---

## 8. 实施任务清单

### Phase 1.1: QueryEngine 核心
- [ ] 实现 `engine/engine.py` - QueryEngine 类
- [ ] 实现 `engine/pipeline.py` - QueryState, QueryParams
- [ ] 实现 `_query_loop()` 主循环
- [ ] 实现 `_call_model()` API 调用

### Phase 1.2: 上下文管理
- [ ] 实现 `engine/context.py` - ContextManager
- [ ] 实现 `compress()` 自动压缩
- [ ] 实现 `snip()` 历史裁剪
- [ ] 实现 token 估算

### Phase 1.3: 工具编排
- [ ] 实现 `engine/tools/orchestration.py` - ToolOrchestrator
- [ ] 实现 `partition_tool_calls()` 批次划分
- [ ] 实现并行/串行执行
- [ ] 实现 `engine/tools/registry.py` - ToolRegistry

### Phase 1.4: 错误处理
- [ ] 实现错误恢复配置
- [ ] 实现 QueryErrorHandler
- [ ] 实现重试逻辑
- [ ] 实现回退模型逻辑
