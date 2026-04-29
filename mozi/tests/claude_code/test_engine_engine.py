"""Tests for engine/engine.py - QueryEngine.

These tests cover the QueryEngine class including message submission,
query loop, event conversion, and SSE parsing.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from claude_code.engine.engine import DEFAULT_MAX_TURNS, DEFAULT_MODEL, QueryEngine
from claude_code.engine.pipeline import QueryParams, QueryResult, QueryState
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
from claude_code.models.message import ContentBlock, Message, Role


class TestQueryEngineInit:
    """Tests for QueryEngine initialization."""

    def test_default_initialization(self) -> None:
        """Test creating QueryEngine with default values."""
        mock_client = MagicMock()
        engine = QueryEngine(api_client=mock_client)

        assert engine.api_client is mock_client
        assert engine.model == DEFAULT_MODEL
        assert engine.max_concurrent_tools == 10
        assert engine.max_turns == DEFAULT_MAX_TURNS
        assert engine.max_output_tokens == 8192
        assert engine._is_running is False
        assert engine._turn_count == 0
        assert engine._session_id is None

    def test_custom_initialization(self) -> None:
        """Test creating QueryEngine with custom values."""
        mock_client = MagicMock()
        engine = QueryEngine(
            api_client=mock_client,
            model="claude-opus-4-6",
            max_concurrent_tools=5,
            max_turns=50,
            max_output_tokens=4096,
        )

        assert engine.model == "claude-opus-4-6"
        assert engine.max_concurrent_tools == 5
        assert engine.max_turns == 50
        assert engine.max_output_tokens == 4096

    def test_is_running_property(self) -> None:
        """Test the is_running property."""
        mock_client = MagicMock()
        engine = QueryEngine(api_client=mock_client)

        assert engine.is_running is False
        engine._is_running = True
        assert engine.is_running is True

    def test_turn_count_property(self) -> None:
        """Test the turn_count property."""
        mock_client = MagicMock()
        engine = QueryEngine(api_client=mock_client)

        assert engine.turn_count == 0
        engine._turn_count = 5
        assert engine.turn_count == 5

    def test_set_session_id(self) -> None:
        """Test setting the session ID."""
        mock_client = MagicMock()
        engine = QueryEngine(api_client=mock_client)

        engine.set_session_id("session-123")
        assert engine._session_id == "session-123"


class TestQueryEngineSubmitMessage:
    """Tests for submit_message method."""

    @pytest.mark.asyncio
    async def test_submit_message_requires_context(self) -> None:
        """Test that submit_message fails if engine is already running."""
        mock_client = MagicMock()
        engine = QueryEngine(api_client=mock_client)
        engine._is_running = True

        messages = [Message(id="m1", role=Role.USER, content_blocks=[ContentBlock(text="hi")])]

        with pytest.raises(RuntimeError, match="already processing"):
            async for _ in engine.submit_message("hello", messages):
                pass

    @pytest.mark.asyncio
    async def test_submit_message_string_prompt(self) -> None:
        """Test submit_message with a string prompt."""
        mock_client = MagicMock()

        # Mock chat_complete to return empty sync generator
        def empty_stream():
            return
            yield  # make it a generator

        mock_client.chat_complete = MagicMock(return_value=empty_stream())

        engine = QueryEngine(api_client=mock_client)
        messages: list[Message] = []

        events = []
        async for event in engine.submit_message("hello world", messages):
            events.append(event)

        # Verify message was added
        assert len(messages) == 1
        assert messages[0].role == Role.USER
        assert len(messages[0].content_blocks) == 1
        assert messages[0].content_blocks[0].text == "hello world"
        assert engine.is_running is False  # Should be reset after completion

    @pytest.mark.asyncio
    async def test_submit_message_content_blocks(self) -> None:
        """Test submit_message with content blocks."""
        mock_client = MagicMock()

        def empty_stream():
            return
            yield

        mock_client.chat_complete = MagicMock(return_value=empty_stream())

        engine = QueryEngine(api_client=mock_client)
        messages: list[Message] = []
        content_blocks = [ContentBlock(text="hello"), ContentBlock(text="world")]

        async for _ in engine.submit_message(content_blocks, messages):
            pass

        assert len(messages) == 1
        assert len(messages[0].content_blocks) == 2

    @pytest.mark.asyncio
    async def test_submit_message_with_system_override(self) -> None:
        """Test submit_message with a system prompt override."""
        mock_client = MagicMock()

        def empty_stream():
            return
            yield

        mock_client.chat_complete = MagicMock(return_value=empty_stream())

        engine = QueryEngine(api_client=mock_client)
        messages: list[Message] = []
        system = "You are a helpful assistant."

        with patch.object(engine, "_build_system_prompt", new_callable=AsyncMock) as mock_build:
            mock_build.return_value = system
            async for _ in engine.submit_message("hello", messages, system=system):
                pass

            mock_build.assert_not_called()  # Should use provided system directly

    @pytest.mark.asyncio
    async def test_submit_message_tracks_turn_count(self) -> None:
        """Test that submit_message initializes turn count."""
        mock_client = MagicMock()

        def empty_stream():
            return
            yield

        mock_client.chat_complete = MagicMock(return_value=empty_stream())

        engine = QueryEngine(api_client=mock_client)
        engine._turn_count = 10  # Pre-existing count
        messages: list[Message] = []

        async for _ in engine.submit_message("hello", messages):
            pass

        assert engine._turn_count == 0  # Should be reset


class TestQueryEngineBuildSystemPrompt:
    """Tests for _build_system_prompt method."""

    @pytest.mark.asyncio
    async def test_build_system_prompt_empty(self) -> None:
        """Test building system prompt with no parts."""
        mock_client = MagicMock()
        engine = QueryEngine(api_client=mock_client)

        result = await engine._build_system_prompt({})
        assert result == ""


class TestQueryEngineParseSseData:
    """Tests for _parse_sse_data method."""

    def test_parse_dict(self) -> None:
        """Test parsing a dict directly."""
        mock_client = MagicMock()
        engine = QueryEngine(api_client=mock_client)

        data = {"type": "message_start", "message": {"id": "msg-1"}}
        result = engine._parse_sse_data(data)
        assert result == data

    def test_parse_json_string(self) -> None:
        """Test parsing a JSON string."""
        mock_client = MagicMock()
        engine = QueryEngine(api_client=mock_client)

        data = {"type": "message_start", "message": {"id": "msg-1"}}
        json_str = json.dumps(data)
        result = engine._parse_sse_data(json_str)
        assert result == data

    def test_parse_invalid_string(self) -> None:
        """Test parsing an invalid JSON string."""
        mock_client = MagicMock()
        engine = QueryEngine(api_client=mock_client)

        result = engine._parse_sse_data("not valid json")
        assert result is None

    def test_parse_other_type(self) -> None:
        """Test parsing a non-dict, non-string type."""
        mock_client = MagicMock()
        engine = QueryEngine(api_client=mock_client)

        result = engine._parse_sse_data(123)
        assert result is None

        result = engine._parse_sse_data(None)
        assert result is None


class TestQueryEngineConvertToEvent:
    """Tests for _convert_to_event method."""

    def test_convert_message_start(self) -> None:
        """Test converting message_start event."""
        mock_client = MagicMock()
        engine = QueryEngine(api_client=mock_client)

        data = {
            "type": "message_start",
            "message": {"id": "msg-1", "role": "assistant"},
            "index": 0,
        }
        event = engine._convert_to_event(data)

        assert isinstance(event, MessageStartEvent)
        assert event.message == {"id": "msg-1", "role": "assistant"}
        assert event.index == 0

    def test_convert_content_block_start(self) -> None:
        """Test converting content_block_start event."""
        mock_client = MagicMock()
        engine = QueryEngine(api_client=mock_client)

        data = {
            "type": "content_block_start",
            "index": 0,
            "content_block": {"type": "text", "text": ""},
        }
        event = engine._convert_to_event(data)

        assert isinstance(event, ContentBlockStartEvent)
        assert event.index == 0
        assert event.content_block == {"type": "text", "text": ""}

    def test_convert_content_block_delta_text(self) -> None:
        """Test converting content_block_delta for text."""
        mock_client = MagicMock()
        engine = QueryEngine(api_client=mock_client)

        data = {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": "Hello"},
        }
        event = engine._convert_to_event(data)

        assert isinstance(event, ContentBlockDeltaEvent)
        assert event.index == 0
        assert event.delta == {"type": "text_delta", "text": "Hello"}

    def test_convert_message_delta(self) -> None:
        """Test converting message_delta event."""
        mock_client = MagicMock()
        engine = QueryEngine(api_client=mock_client)

        data = {
            "type": "message_delta",
            "usage": {"input_tokens": 100, "output_tokens": 50},
            "stop_reason": "end_turn",
        }
        event = engine._convert_to_event(data)

        assert isinstance(event, MessageDeltaEvent)
        assert event.usage == {"input_tokens": 100, "output_tokens": 50}
        assert event.stop_reason == "end_turn"

    def test_convert_message_stop(self) -> None:
        """Test converting message_stop event."""
        mock_client = MagicMock()
        engine = QueryEngine(api_client=mock_client)

        data = {"type": "message_stop"}
        event = engine._convert_to_event(data)

        assert isinstance(event, MessageStopEvent)

    def test_convert_thinking(self) -> None:
        """Test converting thinking event."""
        mock_client = MagicMock()
        engine = QueryEngine(api_client=mock_client)

        data = {
            "type": "thinking",
            "thinking": "Let me think about this...",
            "is_visible": False,
            "signature": "sig-123",
        }
        event = engine._convert_to_event(data)

        assert isinstance(event, ThinkingEvent)
        assert event.thinking == "Let me think about this..."
        assert event.is_visible is False
        assert event.signature == "sig-123"

    def test_convert_tool_use(self) -> None:
        """Test converting tool_use event."""
        mock_client = MagicMock()
        engine = QueryEngine(api_client=mock_client)

        data = {
            "type": "tool_use",
            "id": "tool-1",
            "name": "bash",
            "input": {"command": "ls"},
        }
        event = engine._convert_to_event(data)

        assert isinstance(event, ToolUseEvent)
        assert event.tool_use_id == "tool-1"
        assert event.tool_name == "bash"
        assert event.tool_args == {"command": "ls"}

    def test_convert_tool_result(self) -> None:
        """Test converting tool_result event."""
        mock_client = MagicMock()
        engine = QueryEngine(api_client=mock_client)

        data = {
            "type": "tool_result",
            "tool_use_id": "tool-1",
            "tool_name": "bash",
            "result": "files listed",
            "is_error": False,
            "content": "files listed",
        }
        event = engine._convert_to_event(data)

        assert isinstance(event, ToolResultEvent)
        assert event.tool_use_id == "tool-1"
        assert event.tool_name == "bash"
        assert event.result == "files listed"
        assert event.is_error is False

    def test_convert_unknown_type(self) -> None:
        """Test converting unknown event type."""
        mock_client = MagicMock()
        engine = QueryEngine(api_client=mock_client)

        data = {"type": "unknown_type", "foo": "bar"}
        event = engine._convert_to_event(data)

        assert event is None


class TestQueryEngineCreateEvent:
    """Tests for _create_event method."""

    def test_create_basic_event(self) -> None:
        """Test creating a basic stream event."""
        mock_client = MagicMock()
        engine = QueryEngine(api_client=mock_client)
        engine._session_id = "session-1"
        engine._turn_count = 3

        event = engine._create_event("error", {"error": "something went wrong"})

        assert event.event_type.value == "error"
        assert event.agent_id == "session-1"
        assert event.step == 3
        assert event.data == {"error": "something went wrong"}

    def test_create_event_without_session(self) -> None:
        """Test creating event without a session ID."""
        mock_client = MagicMock()
        engine = QueryEngine(api_client=mock_client)

        event = engine._create_event("final_result", {"result": "done"})

        assert event.agent_id == "engine"


class TestQueryEngineBuildToolBlocks:
    """Tests for _build_tool_calls method."""

    def test_build_empty_calls(self) -> None:
        """Test building tool calls from empty input."""
        mock_client = MagicMock()
        engine = QueryEngine(api_client=mock_client)

        result = engine._build_tool_calls({})
        assert result == []

    def test_build_single_call(self) -> None:
        """Test building a single tool call."""
        mock_client = MagicMock()
        engine = QueryEngine(api_client=mock_client)

        accumulated = {
            0: {
                "id": "tool-1",
                "name": "bash",
                "input": '{"command": "ls"}',
            }
        }
        calls = engine._build_tool_calls(accumulated)

        assert len(calls) == 1
        assert calls[0].id == "tool-1"
        assert calls[0].name == "bash"
        assert calls[0].arguments == '{"command": "ls"}'

    def test_build_multiple_calls_sorted(self) -> None:
        """Test that tool calls are sorted by index."""
        mock_client = MagicMock()
        engine = QueryEngine(api_client=mock_client)

        accumulated = {
            2: {"id": "tool-3", "name": "read", "input": "{}"},
            0: {"id": "tool-1", "name": "bash", "input": "{}"},
            1: {"id": "tool-2", "name": "grep", "input": "{}"},
        }
        calls = engine._build_tool_calls(accumulated)

        assert len(calls) == 3
        assert calls[0].name == "bash"
        assert calls[1].name == "grep"
        assert calls[2].name == "read"

    def test_build_tool_call_with_empty_input(self) -> None:
        """Test building tool call with empty input."""
        mock_client = MagicMock()
        engine = QueryEngine(api_client=mock_client)

        accumulated = {0: {"id": "tool-1", "name": "read", "input": ""}}
        calls = engine._build_tool_calls(accumulated)

        assert len(calls) == 1
        assert calls[0].arguments == ""


class TestQueryState:
    """Tests for QueryState dataclass."""

    def test_default_state(self) -> None:
        """Test QueryState with default values."""
        messages = [Message(id="m1", role=Role.USER, content_blocks=[])]
        state = QueryState(messages=messages)

        assert state.messages is messages
        assert state.turn_count == 0
        assert state.auto_compact_tracking is None
        assert state.has_attempted_reactive_compact is False
        assert state.max_output_tokens_recovery_count == 0
        assert state.max_output_tokens_override is None
        assert state.pending_tool_use_summary is None
        assert state.stop_hook_active is False
        assert state.transition is None

    def test_copy_with(self) -> None:
        """Test QueryState.copy_with creates new instance."""
        messages = [Message(id="m1", role=Role.USER, content_blocks=[])]
        state = QueryState(messages=messages, turn_count=0)

        new_state = state.copy_with(turn_count=5, stop_hook_active=True)

        assert new_state.turn_count == 5
        assert new_state.stop_hook_active is True
        assert new_state.messages is messages  # Original unchanged
        assert state.turn_count == 0  # Original unchanged

    def test_copy_with_preserves_all_fields(self) -> None:
        """Test that copy_with preserves unmodified fields."""
        messages = [Message(id="m1", role=Role.USER, content_blocks=[])]
        state = QueryState(
            messages=messages,
            turn_count=5,
            auto_compact_tracking={"key": "value"},
            has_attempted_reactive_compact=True,
            max_output_tokens_recovery_count=2,
            stop_hook_active=True,
        )

        new_state = state.copy_with(turn_count=10)

        assert new_state.turn_count == 10
        assert new_state.auto_compact_tracking == {"key": "value"}
        assert new_state.has_attempted_reactive_compact is True
        assert new_state.stop_hook_active is True


class TestQueryParams:
    """Tests for QueryParams dataclass."""

    def test_default_params(self) -> None:
        """Test QueryParams with default values."""
        messages = [Message(id="m1", role=Role.USER, content_blocks=[])]
        params = QueryParams(messages=messages)

        assert params.messages is messages
        assert params.system_prompt is None
        assert params.tools == []
        assert params.max_output_tokens is None
        assert params.metadata == {}

    def test_custom_params(self) -> None:
        """Test QueryParams with custom values."""
        messages = [Message(id="m1", role=Role.USER, content_blocks=[])]
        params = QueryParams(
            messages=messages,
            system_prompt="You are helpful.",
            tools=[{"name": "bash", "description": "Run bash"}],
            max_output_tokens=4096,
            metadata={"source": "test"},
        )

        assert params.system_prompt == "You are helpful."
        assert len(params.tools) == 1
        assert params.tools[0]["name"] == "bash"
        assert params.max_output_tokens == 4096
        assert params.metadata["source"] == "test"


class TestQueryResult:
    """Tests for QueryResult dataclass."""

    def test_default_result(self) -> None:
        """Test QueryResult with default values."""
        result = QueryResult(reason="completed")

        assert result.reason == "completed"
        assert result.messages == []
        assert result.total_tokens == 0
        assert result.total_cost == 0.0

    def test_full_result(self) -> None:
        """Test QueryResult with all fields."""
        messages = [Message(id="m1", role=Role.USER, content_blocks=[])]
        result = QueryResult(
            reason="max_turns",
            messages=messages,
            total_tokens=5000,
            total_cost=0.25,
        )

        assert result.reason == "max_turns"
        assert result.messages is messages
        assert result.total_tokens == 5000
        assert result.total_cost == 0.25


class TestQueryEnginePrepareContext:
    """Tests for _prepare_context method."""

    @pytest.mark.asyncio
    async def test_prepare_context_no_compression_needed(self) -> None:
        """Test context preparation when no compression is needed."""
        mock_client = MagicMock()
        engine = QueryEngine(api_client=mock_client)
        state = QueryState(messages=[])

        await engine._prepare_context(state)

        # No changes to state if no compression
        assert state.messages == []

    @pytest.mark.asyncio
    async def test_prepare_context_with_context_manager(self) -> None:
        """Test context preparation with a real ContextManager."""
        mock_client = MagicMock()
        engine = QueryEngine(api_client=mock_client)
        messages = [Message(id="m1", role=Role.USER, content_blocks=[ContentBlock(text="hello")])]
        state = QueryState(messages=messages)

        # Try to import and use real ContextManager
        try:
            from claude_code.engine.context import ContextManager

            await engine._prepare_context(state)
            # Should not raise, just pass
        except ImportError:
            pytest.skip("ContextManager not yet implemented")


class TestQueryEngineIntegration:
    """Integration-style tests for QueryEngine."""

    @pytest.mark.asyncio
    async def test_simple_query_flow(self) -> None:
        """Test a complete simple query without tools."""
        mock_client = MagicMock()

        # Simulate a streaming response with message_start, content blocks, and message_stop
        def mock_stream():
            yield {"type": "message_start", "message": {"id": "msg-1"}, "index": 0}
            yield {
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "text", "text": ""},
            }
            yield {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Hello"}}
            yield {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": "!"},
            }
            yield {
                "type": "message_delta",
                "usage": {"input_tokens": 10, "output_tokens": 5},
                "stop_reason": "end_turn",
            }
            yield {"type": "message_stop"}

        mock_client.chat_complete = MagicMock(return_value=mock_stream())

        engine = QueryEngine(api_client=mock_client)
        messages: list[Message] = []

        events = []
        async for event in engine.submit_message("Say hello", messages):
            events.append(event)

        # Verify events were generated
        assert len(events) > 0

        # Should have message_start, content_block_start, deltas, delta, message_stop
        event_types = [type(e).__name__ for e in events]
        assert "MessageStartEvent" in event_types
        assert "MessageStopEvent" in event_types

    @pytest.mark.asyncio
    async def test_query_resets_state_on_completion(self) -> None:
        """Test that engine state is properly reset after query completes."""
        mock_client = MagicMock()

        def empty_stream():
            return
            yield

        mock_client.chat_complete = MagicMock(return_value=empty_stream())

        engine = QueryEngine(api_client=mock_client)
        messages: list[Message] = []

        assert engine.is_running is False

        async for _ in engine.submit_message("hello", messages):
            pass

        assert engine.is_running is False
        assert engine._turn_count == 0

    @pytest.mark.asyncio
    async def test_query_with_custom_options(self) -> None:
        """Test query with custom options like temperature and thinking."""
        mock_client = MagicMock()

        def empty_stream():
            return
            yield

        mock_client.chat_complete = MagicMock(return_value=empty_stream())

        engine = QueryEngine(api_client=mock_client)
        messages: list[Message] = []
        options = {
            "uuid": "custom-uuid-123",
            "temperature": 0.7,
            "thinking": {"type": "enabled", "budget_tokens": 1000},
        }

        async for _ in engine.submit_message("hello", messages, options=options):
            pass

        # Verify custom message ID was used
        assert len(messages) == 1
        assert messages[0].id == "custom-uuid-123"

        # Verify API was called with options
        mock_client.chat_complete.assert_called_once()
        call_kwargs = mock_client.chat_complete.call_args.kwargs
        assert call_kwargs["temperature"] == 0.7
        assert call_kwargs["thinking"] == {"type": "enabled", "budget_tokens": 1000}
