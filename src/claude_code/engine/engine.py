"""QueryEngine - core query processing engine.

TypeScript equivalent: src/QueryEngine.ts
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from claude_code.models.events import (
    ContentBlockDeltaEvent,
    ContentBlockStartEvent,
    MessageDeltaEvent,
    MessageStartEvent,
    MessageStopEvent,
    StreamEvent,
    ThinkingEvent,
    TombstoneEvent,
    ToolUseEvent,
)

if TYPE_CHECKING:
    from claude_code.engine.pipeline import QueryState
    from claude_code.models.message import ContentBlock, Message, ToolCall
    from claude_code.services.api.claude import ClaudeAIClient

logger = logging.getLogger(__name__)

# Default max turns to prevent infinite loops
DEFAULT_MAX_TURNS = 100
# Default model
DEFAULT_MODEL = "claude-sonnet-4-20250514"


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

    Attributes:
        api_client: The Claude AI API client for making requests.
        model: Model identifier to use (default: claude-sonnet-4-20250514).
        max_concurrent_tools: Maximum tools to run in parallel (default: 10).
        max_turns: Maximum query loop iterations (default: 100).
        max_output_tokens: Maximum tokens per response (default: 8192).
    """

    api_client: ClaudeAIClient
    model: str = DEFAULT_MODEL
    max_concurrent_tools: int = 10
    max_turns: int = DEFAULT_MAX_TURNS
    max_output_tokens: int = 8192

    # Internal state
    _session_id: str | None = field(default=None, repr=False)
    _is_running: bool = field(default=False, repr=False)
    _turn_count: int = field(default=0, repr=False)

    async def submit_message(
        self,
        prompt: str | list[ContentBlock],
        messages: list[Message],
        system: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """Submit a message and process the response stream.

        This is the main entry point for query execution. It builds the system
        prompt, adds the user message to history, and runs the query loop
        which handles API calls, tool execution, and context management.

        Args:
            prompt: User input as a string or list of content blocks.
            messages: Conversation history. The user message will be appended.
            system: Optional system prompt override.
            options: Additional options including:
                - uuid: Custom message ID
                - is_meta: Whether this is a meta/pseudo-message
                - temperature: Sampling temperature
                - thinking: Thinking budget config

        Yields:
            StreamEvent types including: thinking, tool_use, tool_result,
            message_start, content_block_start, content_block_delta,
            message_delta, message_stop, tombstone.

        Raises:
            RuntimeError: If the engine is already running.
        """
        if self._is_running:
            raise RuntimeError("QueryEngine is already processing a message")

        self._is_running = True
        options = options or {}
        self._turn_count = 0

        try:
            # Build system prompt
            system_prompt = system or await self._build_system_prompt(options)

            # Create user message
            from claude_code.models.message import ContentBlock as CB
            from claude_code.models.message import Message as Msg
            from claude_code.models.message import Role

            msg_id = options.get("uuid", str(uuid.uuid4()))
            content = [CB(text=prompt)] if isinstance(prompt, str) else prompt

            user_message = Msg(
                id=msg_id,
                role=Role.USER,
                content_blocks=content,
            )
            messages.append(user_message)

            # Run query pipeline
            async for event in self._query_loop(messages, system_prompt, options):
                yield event

        finally:
            self._is_running = False

    async def _build_system_prompt(self, options: dict[str, Any]) -> str:
        """Build system prompt from parts.

        Fetches:
        - Git status
        - CLAUDE.md content
        - Custom prompts
        - Append prompts

        Args:
            options: Additional options for prompt building.

        Returns:
            Complete system prompt string.
        """
        parts: list[str] = []

        # TODO: Fetch git status
        # git_status = await self._fetch_git_status()

        # TODO: Load CLAUDE.md files
        # claude_md = self._load_claude_md()

        # TODO: Load custom prompts
        # custom_prompts = self._load_custom_prompts()

        return "\n\n".join(parts)

    async def _query_loop(
        self,
        messages: list[Message],
        system: str,
        options: dict[str, Any],
    ) -> AsyncGenerator[StreamEvent, None]:
        """Main query loop - handles iteration, tool execution, and context management.

        TypeScript equivalent: query.ts::query() -> queryLoop()

        This loop continues until:
        - The model stops without requesting tool calls
        - Max turns is reached
        - An error occurs

        Args:
            messages: Conversation history.
            system: System prompt.
            options: Additional query options.

        Yields:
            Stream events from the model and tool execution.
        """
        from claude_code.engine.pipeline import QueryState

        state = QueryState(messages=messages, turn_count=self._turn_count)

        while True:
            # Check max turns
            if state.turn_count >= self.max_turns:
                yield self._create_event(
                    "tombstone",
                    {"message": "max_turns_reached", "type": "tombstone"},
                )
                break

            # Pre-query context preparation
            await self._prepare_context(state)

            # Get tools for this turn
            tools: list[dict[str, Any]] = []
            try:
                from claude_code.engine.tools.registry import ToolRegistry

                registry = ToolRegistry()
                tools = registry.list_tools()
            except (ImportError, Exception):
                pass

            # Call API with streaming
            needs_follow_up = False
            accumulated_tool_inputs: dict[int, dict[str, Any]] = {}

            temperature = options.get("temperature")
            thinking_config = options.get("thinking")

            try:
                stream = self.api_client.chat_complete(
                    messages=[m.to_dict() for m in state.messages],
                    stream=True,
                    model=self.model,
                    system=system,
                    max_tokens=self.max_output_tokens,
                    temperature=temperature,
                    tools=tools if tools else None,
                    thinking=thinking_config,
                )

                for event_data in stream:
                    parsed = self._parse_sse_data(event_data)
                    if parsed is None:
                        continue

                    event = self._convert_to_event(parsed)
                    if event is None:
                        continue

                    # Handle different event types
                    if isinstance(event, (ThinkingEvent, MessageStartEvent)):
                        yield event

                    elif isinstance(event, ContentBlockStartEvent):
                        if event.content_block.get("type") == "tool_use":
                            tool_id = event.content_block.get("id", "")
                            tool_name = event.content_block.get("name", "")
                            accumulated_tool_inputs[event.index] = {
                                "id": tool_id,
                                "name": tool_name,
                                "input": "",
                            }
                        yield event

                    elif isinstance(event, ContentBlockDeltaEvent):
                        delta = event.delta
                        if delta.get("type") == "input_json_delta":
                            input_delta = delta.get("text", "")
                            if event.index in accumulated_tool_inputs:
                                accumulated_tool_inputs[event.index]["input"] += input_delta
                        yield event

                    elif isinstance(event, ToolUseEvent):
                        needs_follow_up = True
                        yield event

                    elif isinstance(event, MessageDeltaEvent):
                        yield event

                    elif isinstance(event, MessageStopEvent):
                        yield event
                        # Execute accumulated tools
                        if accumulated_tool_inputs:
                            tool_calls = self._build_tool_calls(accumulated_tool_inputs)
                            async for tool_event in self._execute_tools(state, tool_calls):
                                yield tool_event

                    elif isinstance(event, TombstoneEvent):
                        yield event

            except Exception as e:
                logger.error("Error during API call: %s", e)
                yield self._create_event(
                    "error",
                    {"error": str(e), "type": "error"},
                )
                break

            # Check continuation conditions
            if not needs_follow_up and not accumulated_tool_inputs:
                break

            # Update state for next iteration
            state = state.copy_with(turn_count=state.turn_count + 1)
            self._turn_count = state.turn_count

    async def _prepare_context(self, state: QueryState) -> None:
        """Prepare context before API call.

        Operations:
        - HISTORY_SNIP: Remove protected-tail messages
        - Microcompact: Cache repeated tool results
        - ContextCollapse: Project collapsed context
        - AutoCompact: Summarize if near context limit

        Args:
            state: Current query state with messages.
        """
        try:
            from claude_code.engine.context import ContextManager

            ctx_manager = ContextManager()
            if await ctx_manager.should_compress(state.messages):
                state.messages = await ctx_manager.compress(state.messages)
                state.has_attempted_reactive_compact = True
        except (ImportError, Exception) as e:
            logger.debug("Context preparation skipped: %s", e)

    def _build_tool_calls(
        self, accumulated: dict[int, dict[str, Any]]
    ) -> list[ToolCall]:
        """Build ToolCall objects from accumulated streaming data.

        Args:
            accumulated: Dict mapping index to tool call data.

        Returns:
            List of ToolCall objects for execution.
        """
        from claude_code.models.message import ToolCall

        calls: list[ToolCall] = []
        for index in sorted(accumulated.keys()):
            data = accumulated[index]
            tool_call = ToolCall(
                id=data["id"],
                name=data["name"],
                arguments=data.get("input", "{}"),
            )
            calls.append(tool_call)

        return calls

    async def _execute_tools(
        self,
        state: QueryState,
        tool_calls: list[ToolCall],
    ) -> AsyncGenerator[StreamEvent, None]:
        """Execute tools with concurrency control.

        TypeScript equivalent: toolOrchestration.ts + StreamingToolExecutor.ts

        Args:
            state: Current query state.
            tool_calls: List of ToolCall objects to execute.

        Yields:
            ToolResultEvent for each tool execution.
        """
        if not tool_calls:
            return

        try:
            from claude_code.engine.tools.orchestration import (
                ToolCall as OrchestratorToolCall,
            )
            from claude_code.engine.tools.orchestration import (
                ToolOrchestrator,
            )
            from claude_code.engine.tools.registry import ToolRegistry
            from claude_code.models.tool import ToolUseContext

            registry = ToolRegistry()
            orchestrator = ToolOrchestrator(
                max_parallel=self.max_concurrent_tools,
            )

            # Build execution context
            context = ToolUseContext(
                abort_controller=asyncio.get_running_loop(),
                messages=[m.to_dict() for m in state.messages],
            )

            # Convert Message.ToolCall to orchestrator ToolCall
            def noop_permission(
                args: Any, ctx: Any, msg: Any = None
            ) -> Any:
                from claude_code.models.tool import PermissionAllowResult

                return PermissionAllowResult()

            orchestrator_calls: list[OrchestratorToolCall] = []
            for tc in tool_calls:
                tool = registry.get(tc.name)
                if tool is None:
                    yield self._create_event(
                        "tool_result",
                        {
                            "tool_use_id": tc.id,
                            "tool_name": tc.name,
                            "result": f"Tool not found: {tc.name}",
                            "is_error": True,
                            "content": f"Tool not found: {tc.name}",
                        },
                    )
                    continue

                try:
                    args = json.loads(tc.arguments) if tc.arguments else {}
                except json.JSONDecodeError:
                    args = {}

                orchestrator_calls.append(
                    OrchestratorToolCall(
                        tool=tool,
                        args=args,
                        tool_use_id=tc.id,
                        context=context,
                        can_use_tool=noop_permission,
                    )
                )

            # Partition and execute
            plan = orchestrator.partition_tool_calls(orchestrator_calls)

            for partition in plan.partitions:
                if partition.execution_mode == "parallel":
                    results = await orchestrator.execute_parallel(partition.calls)
                else:
                    results = await orchestrator.execute_serial(partition.calls)

                for result in results:
                    is_error = result.error is not None
                    content = result.error or ""
                    if result.result is not None:
                        content = str(result.result.data)

                    yield self._create_event(
                        "tool_result",
                        {
                            "tool_use_id": result.tool_use_id,
                            "tool_name": getattr(
                                result.result, "tool_name", ""
                            ) if result.result else "",
                            "result": content,
                            "is_error": is_error,
                            "content": content,
                        },
                    )

        except (ImportError, Exception) as e:
            logger.error("Tool execution failed: %s", e)
            # Yield error results for all tools
            for tc in tool_calls:
                yield self._create_event(
                    "tool_result",
                    {
                        "tool_use_id": tc.id,
                        "tool_name": tc.name,
                        "result": f"Tool execution unavailable: {e}",
                        "is_error": True,
                        "content": f"Tool execution unavailable: {e}",
                    },
                )

    def _parse_sse_data(
        self, event_data: Any
    ) -> dict[str, Any] | None:
        """Parse SSE data line or event object.

        Handles:
        - Dict format (raw dict from stream)
        - String format (raw SSE lines)
        - API StreamEvent objects (from services/api/claude.py)
        - Other objects with 'type' attribute

        Args:
            event_data: Raw event data from the stream.

        Returns:
            Parsed event dict or None if invalid.
        """
        # Handle API StreamEvent from services/api/claude.py
        if hasattr(event_data, "type"):
            result: dict[str, Any] = {"type": event_data.type}
            # Handle MessageDelta (from api StreamEvent)
            if hasattr(event_data, "delta") and event_data.delta is not None:
                delta = event_data.delta
                result["delta"] = {
                    "type": getattr(delta, "type", "content_block_delta"),
                    "text": getattr(delta, "text", ""),
                    "index": getattr(delta, "index", 0),
                }
            # Handle content_block
            if hasattr(event_data, "content_block") and event_data.content_block is not None:
                result["content_block"] = event_data.content_block
            # Handle usage
            if hasattr(event_data, "usage") and event_data.usage is not None:
                result["usage"] = event_data.usage
            return result

        if isinstance(event_data, dict):
            return event_data

        if isinstance(event_data, str):
            try:
                return json.loads(event_data)
            except json.JSONDecodeError:
                return None

        return None

    def _convert_to_event(self, data: dict[str, Any]) -> StreamEvent | None:
        """Convert API response data to a typed stream event.

        Args:
            data: Parsed SSE event data with 'type' field.

        Returns:
            Typed stream event or None for unknown types.
        """
        from claude_code.models.events import (
            ContentBlockDeltaEvent,
            ContentBlockStartEvent,
            MessageDeltaEvent,
            MessageStartEvent,
            MessageStopEvent,
            ThinkingEvent,
            ToolResultEvent,
            ToolUseEvent,
        )

        event_type = data.get("type", "")

        match event_type:
            case "message_start":
                return MessageStartEvent(
                    message=data.get("message", {}),
                    index=data.get("index", 0),
                )

            case "content_block_start":
                return ContentBlockStartEvent(
                    index=data.get("index", 0),
                    content_block=data.get("content_block", {}),
                )

            case "content_block_delta":
                delta = data.get("delta", {})
                return ContentBlockDeltaEvent(
                    index=data.get("index", 0),
                    delta=delta,
                )

            case "message_delta":
                return MessageDeltaEvent(
                    usage=data.get("usage", {}),
                    stop_reason=data.get("stop_reason"),
                )

            case "message_stop":
                return MessageStopEvent()

            case "thinking":
                return ThinkingEvent(
                    thinking=data.get("thinking", ""),
                    is_visible=data.get("is_visible", False),
                    signature=data.get("signature"),
                )

            case "tool_use":
                return ToolUseEvent(
                    tool_use_id=data.get("id", str(uuid.uuid4())),
                    tool_name=data.get("name", ""),
                    tool_args=data.get("input", {}),
                )

            case "tool_result":
                return ToolResultEvent(
                    tool_use_id=data.get("tool_use_id", ""),
                    tool_name=data.get("tool_name", ""),
                    result=data.get("result"),
                    is_error=data.get("is_error", False),
                    content=data.get("content"),
                )

            case _:
                logger.debug("Unknown event type: %s", event_type)
                return None

    def _create_event(
        self,
        event_type: str,
        data: dict[str, Any],
    ) -> StreamEvent:
        """Create a StreamEvent with standard fields.

        Args:
            event_type: Type of the event.
            data: Event-specific payload.

        Returns:
            A new StreamEvent instance.
        """
        from claude_code.models.events import StreamEvent, StreamEventType

        return StreamEvent(
            event_type=StreamEventType(event_type),
            agent_id=self._session_id or "engine",
            step=self._turn_count,
            data=data,
        )

    def set_session_id(self, session_id: str) -> None:
        """Set the session ID for request correlation.

        Args:
            session_id: Unique session identifier.
        """
        self._session_id = session_id

    @property
    def is_running(self) -> bool:
        """Check if the engine is currently processing a message.

        Returns:
            True if a query is in progress.
        """
        return self._is_running

    @property
    def turn_count(self) -> int:
        """Get the current turn count.

        Returns:
            Number of turns completed in the current query.
        """
        return self._turn_count
