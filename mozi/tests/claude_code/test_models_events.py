"""
Tests for stream event models.
"""

from __future__ import annotations

import json
import time

import pytest
from claude_code.models.events import (
    ContentBlockDeltaEvent,
    ContentBlockStartEvent,
    MessageDeltaEvent,
    MessageStartEvent,
    MessageStopEvent,
    StreamEvent,
    StreamEventType,
    ThinkingEvent,
    TombstoneEvent,
    ToolResultEvent,
    ToolUseEvent,
    create_stream_event,
    generate_span_id,
    generate_trace_id,
)


class TestStreamEventType:
    """Tests for StreamEventType enum."""

    def test_all_event_types_exist(self) -> None:
        """All expected event types should be defined."""
        expected = {
            "THOUGHT",
            "TOOL_CALL_START",
            "TOOL_CALL_END",
            "TOOL_RESULT",
            "STEP_COMPLETE",
            "STEP_START",
            "FINAL_RESULT",
            "ERROR",
            "REFLECTION",
            "REFLECTION_COMPLETE",
            "TOKEN_USAGE",
            "TERMINATION_REASON",
            "HEARTBEAT",
            "THINKING",
            "MESSAGE_START",
            "CONTENT_BLOCK_START",
            "CONTENT_BLOCK_DELTA",
            "MESSAGE_DELTA",
            "MESSAGE_STOP",
            "TOMBSTONE",
        }
        actual = {e.name for e in StreamEventType}
        assert actual == expected

    def test_event_type_values_lowercase(self) -> None:
        """Each event type value should be lowercase string of its name."""
        for et in StreamEventType:
            assert et.value == et.name.lower()

    def test_event_type_from_string(self) -> None:
        """Event types should be constructible from their string values."""
        assert StreamEventType("thought") == StreamEventType.THOUGHT
        assert StreamEventType("tool_call_start") == StreamEventType.TOOL_CALL_START
        assert StreamEventType("message_start") == StreamEventType.MESSAGE_START
        assert StreamEventType("error") == StreamEventType.ERROR

    def test_invalid_event_type_raises(self) -> None:
        """Invalid event type strings should raise ValueError."""
        with pytest.raises(ValueError):
            StreamEventType("invalid_type")


class TestStreamEvent:
    """Tests for StreamEvent dataclass."""

    def test_create_basic_event(self) -> None:
        """StreamEvent should be constructible with required fields."""
        event = StreamEvent(
            event_type=StreamEventType.THOUGHT,
            agent_id="test-agent",
            step=0,
            data={"content": "Thinking..."},
        )
        assert event.event_type == StreamEventType.THOUGHT
        assert event.agent_id == "test-agent"
        assert event.step == 0
        assert event.data == {"content": "Thinking..."}
        assert event.timestamp > 0
        assert event.trace_id is None
        assert event.span_id is None

    def test_create_event_with_optional_fields(self) -> None:
        """StreamEvent should accept optional trace/span fields."""
        ts = time.time()
        event = StreamEvent(
            event_type=StreamEventType.TOOL_RESULT,
            agent_id="agent-1",
            step=3,
            data={"tool_id": "call_abc"},
            timestamp=ts,
            trace_id="trace_xyz",
            span_id="span_123",
        )
        assert event.timestamp == ts
        assert event.trace_id == "trace_xyz"
        assert event.span_id == "span_123"

    def test_to_dict_basic(self) -> None:
        """to_dict should return a JSON-compatible dictionary."""
        event = StreamEvent(
            event_type=StreamEventType.ERROR,
            agent_id="my-agent",
            step=2,
            data={"message": "Something went wrong"},
            trace_id="trace_abc",
        )
        d = event.to_dict()
        assert d["event_type"] == "error"
        assert d["agent_id"] == "my-agent"
        assert d["step"] == 2
        assert d["data"] == {"message": "Something went wrong"}
        assert d["trace_id"] == "trace_abc"

    def test_to_dict_enum_serialized_as_string(self) -> None:
        """Event type in to_dict output should be a string, not an enum."""
        event = StreamEvent(
            event_type=StreamEventType.MESSAGE_STOP,
            agent_id="a",
            step=0,
            data={},
        )
        d = event.to_dict()
        assert isinstance(d["event_type"], str)
        assert d["event_type"] == "message_stop"

    def test_from_dict_roundtrip(self) -> None:
        """from_dict should reconstruct an equivalent event."""
        original = StreamEvent(
            event_type=StreamEventType.TOOL_CALL_START,
            agent_id="roundtrip-agent",
            step=5,
            data={
                "tool_name": "read_file",
                "tool_args": {"path": "/tmp/test.txt"},
                "tool_id": "call_001",
            },
            timestamp=1700000000.0,
            trace_id="trace_test",
            span_id="span_test",
        )

        d = original.to_dict()
        restored = StreamEvent.from_dict(d)

        assert restored.event_type == original.event_type
        assert restored.agent_id == original.agent_id
        assert restored.step == original.step
        assert restored.data == original.data
        assert restored.timestamp == original.timestamp
        assert restored.trace_id == original.trace_id
        assert restored.span_id == original.span_id

    def test_from_dict_json_roundtrip(self) -> None:
        """Events should survive JSON serialization roundtrip."""
        original = StreamEvent(
            event_type=StreamEventType.FINAL_RESULT,
            agent_id="json-agent",
            step=1,
            data={"content": "The answer is 42"},
            trace_id="trace_json",
        )

        serialized = json.dumps(original.to_dict())
        parsed = json.loads(serialized)
        restored = StreamEvent.from_dict(parsed)

        assert restored.event_type == original.event_type
        assert restored.agent_id == original.agent_id
        assert restored.data == original.data

    def test_from_dict_missing_optional_fields(self) -> None:
        """from_dict should handle missing optional fields gracefully."""
        data = {
            "event_type": "heartbeat",
            "agent_id": "minimal-agent",
            "step": 0,
            "data": {"alive": True},
        }
        event = StreamEvent.from_dict(data)
        assert event.trace_id is None
        assert event.span_id is None
        assert event.timestamp > 0

    def test_from_dict_invalid_event_type(self) -> None:
        """from_dict should raise ValueError for invalid event type."""
        data = {
            "event_type": "not_a_valid_type",
            "agent_id": "x",
            "step": 0,
            "data": {},
        }
        with pytest.raises(ValueError):
            StreamEvent.from_dict(data)

    def test_all_event_types_instantiable(self) -> None:
        """Every event type should be constructible as a StreamEvent."""
        agent_id = "test-agent"
        step = 1
        ts = time.time()

        for event_type in StreamEventType:
            event = StreamEvent(
                event_type=event_type,
                agent_id=agent_id,
                step=step,
                data={"test": "payload"},
                timestamp=ts,
            )
            assert event.event_type == event_type
            assert event.agent_id == agent_id
            assert event.step == step
            assert event.data == {"test": "payload"}
            assert event.timestamp == ts

    def test_event_data_varies_by_type(self) -> None:
        """Each event type should carry appropriate data structure."""
        cases = [
            (StreamEventType.THOUGHT, {"content": "Let me think about this..."}),
            (StreamEventType.TOOL_CALL_START, {"tool_name": "bash", "tool_args": {"cmd": "ls"}, "tool_id": "c1"}),
            (StreamEventType.TOOL_CALL_END, {"tool_name": "bash", "tool_id": "c1", "success": True}),
            (StreamEventType.TOOL_RESULT, {"tool_name": "bash", "tool_id": "c1", "result": "file1.txt"}),
            (StreamEventType.STEP_COMPLETE, {"content": "Thought text", "tool_count": 2}),
            (StreamEventType.STEP_START, {"input": {"task": "Analyze this"}}),
            (StreamEventType.FINAL_RESULT, {"content": "The answer is 42"}),
            (StreamEventType.ERROR, {"message": "File not found"}),
            (StreamEventType.REFLECTION, {"thought": "Why did this fail?"}),
            (StreamEventType.REFLECTION_COMPLETE, {"adjustments": ["try different path"]}),
            (StreamEventType.TOKEN_USAGE, {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}),
            (StreamEventType.TERMINATION_REASON, {"reason": "max_steps_reached"}),
            (StreamEventType.HEARTBEAT, {"alive": True, "latency_ms": 5}),
            (StreamEventType.THINKING, {"thinking": "Let me reason through this step by step."}),
            (StreamEventType.MESSAGE_START, {"message": {"role": "assistant"}}),
            (StreamEventType.CONTENT_BLOCK_START, {"index": 0, "content_block": {"type": "text"}}),
            (StreamEventType.CONTENT_BLOCK_DELTA, {"index": 0, "delta": {"type": "text_delta", "text": "Hi"}}),
            (StreamEventType.MESSAGE_DELTA, {"usage": {"output_tokens": 10}, "stop_reason": "end_turn"}),
            (StreamEventType.MESSAGE_STOP, {}),
            (StreamEventType.TOMBSTONE, {"index": 1}),
        ]

        for event_type, data in cases:
            event = StreamEvent(
                event_type=event_type,
                agent_id="data-test",
                step=0,
                data=data,
                timestamp=time.time(),
            )
            assert event.data == data, f"Data mismatch for {event_type.name}"


class TestThinkingEvent:
    """Tests for ThinkingEvent."""

    def test_create_basic_thinking_event(self) -> None:
        """ThinkingEvent should be constructible with thinking text."""
        event = ThinkingEvent(thinking="Stepping through the logic...")
        assert event.thinking == "Stepping through the logic..."
        assert event.is_visible is False
        assert event.signature is None

    def test_create_with_signature(self) -> None:
        """ThinkingEvent should accept signature for verification."""
        event = ThinkingEvent(
            thinking="Deep reasoning here.",
            is_visible=True,
            signature="sig_abc123",
        )
        assert event.thinking == "Deep reasoning here."
        assert event.is_visible is True
        assert event.signature == "sig_abc123"

    def test_thinking_to_dict(self) -> None:
        """to_dict should serialize thinking event correctly."""
        event = ThinkingEvent(
            thinking="Test thinking",
            is_visible=True,
            signature="sig_xyz",
        )
        d = event.to_dict()
        assert d["thinking"] == "Test thinking"
        assert d["is_visible"] is True
        assert d["signature"] == "sig_xyz"

    def test_thinking_from_dict(self) -> None:
        """from_dict should reconstruct thinking event."""
        original = ThinkingEvent(thinking="Reconstruct me", is_visible=True, signature="sig")
        restored = ThinkingEvent.from_dict(original.to_dict())
        assert restored.thinking == original.thinking
        assert restored.is_visible == original.is_visible
        assert restored.signature == original.signature

    def test_thinking_json_roundtrip(self) -> None:
        """ThinkingEvent should survive JSON serialization."""
        event = ThinkingEvent(thinking="JSON test", is_visible=False)
        serialized = json.dumps(event.to_dict())
        restored = ThinkingEvent.from_dict(json.loads(serialized))
        assert restored.thinking == event.thinking


class TestToolUseEvent:
    """Tests for ToolUseEvent."""

    def test_create_tool_use_event(self) -> None:
        """ToolUseEvent should carry tool call details."""
        event = ToolUseEvent(
            tool_use_id="call_001",
            tool_name="bash",
            tool_args={"command": "ls -la"},
        )
        assert event.tool_use_id == "call_001"
        assert event.tool_name == "bash"
        assert event.tool_args == {"command": "ls -la"}
        assert event.tool_input is None

    def test_tool_use_with_tool_input(self) -> None:
        """ToolUseEvent should support tool_input alias."""
        event = ToolUseEvent(
            tool_use_id="call_002",
            tool_name="read_file",
            tool_input={"path": "/etc/hosts"},
        )
        assert event.tool_input == {"path": "/etc/hosts"}
        assert event.tool_args == {}

    def test_tool_use_to_dict(self) -> None:
        """to_dict should serialize tool use event."""
        event = ToolUseEvent(
            tool_use_id="call_003",
            tool_name="search",
            tool_args={"query": "python"},
        )
        d = event.to_dict()
        assert d["tool_use_id"] == "call_003"
        assert d["tool_name"] == "search"
        assert d["tool_args"] == {"query": "python"}

    def test_tool_use_from_dict(self) -> None:
        """from_dict should reconstruct tool use event."""
        original = ToolUseEvent(
            tool_use_id="call_004",
            tool_name="web_fetch",
            tool_args={"url": "https://example.com"},
        )
        restored = ToolUseEvent.from_dict(original.to_dict())
        assert restored.tool_use_id == original.tool_use_id
        assert restored.tool_name == original.tool_name
        assert restored.tool_args == original.tool_args

    def test_tool_use_json_roundtrip(self) -> None:
        """ToolUseEvent should survive JSON serialization."""
        event = ToolUseEvent(tool_use_id="c1", tool_name="t", tool_args={"a": 1})
        restored = ToolUseEvent.from_dict(json.loads(json.dumps(event.to_dict())))
        assert restored.tool_use_id == event.tool_use_id
        assert restored.tool_name == event.tool_name


class TestToolResultEvent:
    """Tests for ToolResultEvent."""

    def test_create_successful_result(self) -> None:
        """ToolResultEvent should carry successful result data."""
        event = ToolResultEvent(
            tool_use_id="call_001",
            tool_name="bash",
            result="file1.txt\nfile2.txt",
        )
        assert event.tool_use_id == "call_001"
        assert event.tool_name == "bash"
        assert event.result == "file1.txt\nfile2.txt"
        assert event.is_error is False
        assert event.error is None

    def test_create_error_result(self) -> None:
        """ToolResultEvent should carry error information."""
        event = ToolResultEvent(
            tool_use_id="call_err",
            tool_name="read_file",
            result=None,
            is_error=True,
            error="FileNotFoundError: /nonexistent",
        )
        assert event.is_error is True
        assert "FileNotFoundError" in event.error

    def test_tool_result_with_content_alias(self) -> None:
        """ToolResultEvent should support content alias."""
        event = ToolResultEvent(
            tool_use_id="c1",
            tool_name="t",
            content="result content",
        )
        assert event.content == "result content"

    def test_tool_result_to_dict(self) -> None:
        """to_dict should serialize all result fields."""
        event = ToolResultEvent(
            tool_use_id="c2",
            tool_name="bash",
            result="success",
            is_error=False,
            content="success",
            error=None,
        )
        d = event.to_dict()
        assert d["tool_use_id"] == "c2"
        assert d["is_error"] is False

    def test_tool_result_from_dict(self) -> None:
        """from_dict should reconstruct tool result event."""
        original = ToolResultEvent(
            tool_use_id="c3",
            tool_name="t",
            result="data",
            is_error=True,
            error="failed",
        )
        restored = ToolResultEvent.from_dict(original.to_dict())
        assert restored.tool_use_id == original.tool_use_id
        assert restored.is_error == original.is_error
        assert restored.error == original.error


class TestMessageStartEvent:
    """Tests for MessageStartEvent."""

    def test_create_message_start(self) -> None:
        """MessageStartEvent should carry initial message data."""
        event = MessageStartEvent(
            message={"role": "assistant", "content": []},
            index=0,
        )
        assert event.message == {"role": "assistant", "content": []}
        assert event.index == 0
        assert event.type == "message_start"

    def test_message_start_defaults(self) -> None:
        """MessageStartEvent should have sensible defaults."""
        event = MessageStartEvent()
        assert event.message == {}
        assert event.index == 0
        assert event.type == "message_start"

    def test_message_start_to_dict(self) -> None:
        """to_dict should serialize message start event."""
        event = MessageStartEvent(
            message={"role": "assistant"},
            index=1,
        )
        d = event.to_dict()
        assert d["type"] == "message_start"
        assert d["message"] == {"role": "assistant"}
        assert d["index"] == 1

    def test_message_start_from_dict(self) -> None:
        """from_dict should reconstruct message start event."""
        original = MessageStartEvent(
            message={"role": "assistant", "content": [{"type": "text", "text": "Hi"}]},
            index=2,
        )
        restored = MessageStartEvent.from_dict(original.to_dict())
        assert restored.message == original.message
        assert restored.index == original.index

    def test_message_start_json_roundtrip(self) -> None:
        """MessageStartEvent should survive JSON serialization."""
        event = MessageStartEvent(message={"role": "assistant"}, index=0)
        restored = MessageStartEvent.from_dict(json.loads(json.dumps(event.to_dict())))
        assert restored.message == event.message


class TestContentBlockStartEvent:
    """Tests for ContentBlockStartEvent."""

    def test_create_content_block_start(self) -> None:
        """ContentBlockStartEvent should carry block data."""
        event = ContentBlockStartEvent(
            index=0,
            content_block={"type": "text", "text": ""},
        )
        assert event.index == 0
        assert event.content_block == {"type": "text", "text": ""}
        assert event.type == "content_block_start"

    def test_content_block_start_to_dict(self) -> None:
        """to_dict should serialize content block start event."""
        event = ContentBlockStartEvent(
            index=1,
            content_block={"type": "tool_use", "name": "bash", "id": "call_1"},
        )
        d = event.to_dict()
        assert d["type"] == "content_block_start"
        assert d["index"] == 1
        assert d["content_block"]["name"] == "bash"

    def test_content_block_start_from_dict(self) -> None:
        """from_dict should reconstruct content block start event."""
        original = ContentBlockStartEvent(
            index=3,
            content_block={"type": "thinking"},
        )
        restored = ContentBlockStartEvent.from_dict(original.to_dict())
        assert restored.index == original.index
        assert restored.content_block == original.content_block

    def test_content_block_start_json_roundtrip(self) -> None:
        """ContentBlockStartEvent should survive JSON serialization."""
        event = ContentBlockStartEvent(index=0, content_block={"type": "text"})
        restored = ContentBlockStartEvent.from_dict(json.loads(json.dumps(event.to_dict())))
        assert restored.index == event.index


class TestContentBlockDeltaEvent:
    """Tests for ContentBlockDeltaEvent."""

    def test_create_text_delta(self) -> None:
        """ContentBlockDeltaEvent should carry text delta."""
        event = ContentBlockDeltaEvent(
            index=0,
            delta={"type": "text_delta", "text": "Hello, "},
        )
        assert event.index == 0
        assert event.delta == {"type": "text_delta", "text": "Hello, "}
        assert event.type == "content_block_delta"

    def test_create_thinking_delta(self) -> None:
        """ContentBlockDeltaEvent should support thinking deltas."""
        event = ContentBlockDeltaEvent(
            index=0,
            delta={"type": "thinking_delta", "thinking": "Thinking..."},
        )
        assert event.delta["thinking"] == "Thinking..."

    def test_content_block_delta_to_dict(self) -> None:
        """to_dict should serialize delta correctly."""
        event = ContentBlockDeltaEvent(
            index=2,
            delta={"type": "text_delta", "text": "world!"},
        )
        d = event.to_dict()
        assert d["type"] == "content_block_delta"
        assert d["index"] == 2
        assert d["delta"]["text"] == "world!"

    def test_content_block_delta_from_dict(self) -> None:
        """from_dict should reconstruct content block delta event."""
        original = ContentBlockDeltaEvent(
            index=1,
            delta={"type": "text_delta", "text": "test"},
        )
        restored = ContentBlockDeltaEvent.from_dict(original.to_dict())
        assert restored.index == original.index
        assert restored.delta == original.delta

    def test_content_block_delta_json_roundtrip(self) -> None:
        """ContentBlockDeltaEvent should survive JSON serialization."""
        event = ContentBlockDeltaEvent(index=0, delta={"type": "text_delta", "text": "x"})
        restored = ContentBlockDeltaEvent.from_dict(json.loads(json.dumps(event.to_dict())))
        assert restored.delta == event.delta


class TestMessageDeltaEvent:
    """Tests for MessageDeltaEvent."""

    def test_create_message_delta(self) -> None:
        """MessageDeltaEvent should carry usage and stop reason."""
        event = MessageDeltaEvent(
            usage={"output_tokens": 42, "total_tokens": 200},
            stop_reason="end_turn",
        )
        assert event.usage["output_tokens"] == 42
        assert event.stop_reason == "end_turn"
        assert event.type == "message_delta"

    def test_message_delta_defaults(self) -> None:
        """MessageDeltaEvent should have sensible defaults."""
        event = MessageDeltaEvent()
        assert event.usage == {}
        assert event.stop_reason is None
        assert event.type == "message_delta"

    def test_message_delta_to_dict(self) -> None:
        """to_dict should serialize message delta event."""
        event = MessageDeltaEvent(
            usage={"prompt_tokens": 100, "completion_tokens": 50},
            stop_reason="max_tokens",
        )
        d = event.to_dict()
        assert d["type"] == "message_delta"
        assert d["usage"]["completion_tokens"] == 50
        assert d["stop_reason"] == "max_tokens"

    def test_message_delta_from_dict(self) -> None:
        """from_dict should reconstruct message delta event."""
        original = MessageDeltaEvent(
            usage={"total_tokens": 500},
            stop_reason="stop_sequence",
        )
        restored = MessageDeltaEvent.from_dict(original.to_dict())
        assert restored.usage == original.usage
        assert restored.stop_reason == original.stop_reason

    def test_message_delta_json_roundtrip(self) -> None:
        """MessageDeltaEvent should survive JSON serialization."""
        event = MessageDeltaEvent(usage={"total_tokens": 100}, stop_reason="done")
        restored = MessageDeltaEvent.from_dict(json.loads(json.dumps(event.to_dict())))
        assert restored.stop_reason == event.stop_reason


class TestMessageStopEvent:
    """Tests for MessageStopEvent."""

    def test_create_message_stop(self) -> None:
        """MessageStopEvent should have type field."""
        event = MessageStopEvent()
        assert event.type == "message_stop"

    def test_message_stop_to_dict(self) -> None:
        """to_dict should serialize message stop event."""
        event = MessageStopEvent()
        d = event.to_dict()
        assert d == {"type": "message_stop"}

    def test_message_stop_from_dict(self) -> None:
        """from_dict should reconstruct message stop event."""
        original = MessageStopEvent()
        restored = MessageStopEvent.from_dict(original.to_dict())
        assert restored.type == original.type

    def test_message_stop_json_roundtrip(self) -> None:
        """MessageStopEvent should survive JSON serialization."""
        event = MessageStopEvent()
        restored = MessageStopEvent.from_dict(json.loads(json.dumps(event.to_dict())))
        assert restored.type == event.type


class TestTombstoneEvent:
    """Tests for TombstoneEvent."""

    def test_create_tombstone(self) -> None:
        """TombstoneEvent should carry index of deleted content."""
        event = TombstoneEvent(index=5)
        assert event.index == 5
        assert event.type == "tombstone"

    def test_tombstone_defaults(self) -> None:
        """TombstoneEvent should default to index 0."""
        event = TombstoneEvent()
        assert event.index == 0
        assert event.type == "tombstone"

    def test_tombstone_to_dict(self) -> None:
        """to_dict should serialize tombstone event."""
        event = TombstoneEvent(index=3)
        d = event.to_dict()
        assert d == {"type": "tombstone", "index": 3}

    def test_tombstone_from_dict(self) -> None:
        """from_dict should reconstruct tombstone event."""
        original = TombstoneEvent(index=7)
        restored = TombstoneEvent.from_dict(original.to_dict())
        assert restored.index == original.index
        assert restored.type == original.type

    def test_tombstone_json_roundtrip(self) -> None:
        """TombstoneEvent should survive JSON serialization."""
        event = TombstoneEvent(index=2)
        restored = TombstoneEvent.from_dict(json.loads(json.dumps(event.to_dict())))
        assert restored.index == event.index


class TestUtilityFunctions:
    """Tests for factory and utility functions."""

    def test_create_stream_event_generates_timestamp(self) -> None:
        """create_stream_event should generate a timestamp."""
        before = time.time()
        event = create_stream_event(
            event_type=StreamEventType.HEARTBEAT,
            agent_id="factory-agent",
            step=0,
            data={"alive": True},
        )
        after = time.time()
        assert before <= event.timestamp <= after

    def test_create_stream_event_preserves_fields(self) -> None:
        """create_stream_event should preserve all fields."""
        event = create_stream_event(
            event_type=StreamEventType.FINAL_RESULT,
            agent_id="my-agent",
            step=3,
            data={"answer": 42},
            trace_id="trace_f",
            span_id="span_f",
        )
        assert event.event_type == StreamEventType.FINAL_RESULT
        assert event.agent_id == "my-agent"
        assert event.step == 3
        assert event.data == {"answer": 42}
        assert event.trace_id == "trace_f"
        assert event.span_id == "span_f"

    def test_generate_trace_id_format(self) -> None:
        """generate_trace_id should create properly formatted IDs."""
        trace_id = generate_trace_id()
        assert trace_id.startswith("trace_")
        assert len(trace_id) == 6 + 12  # prefix + 12 hex chars

    def test_generate_trace_id_unique(self) -> None:
        """generate_trace_id should generate unique IDs."""
        ids = {generate_trace_id() for _ in range(100)}
        assert len(ids) == 100

    def test_generate_span_id_format(self) -> None:
        """generate_span_id should create properly formatted IDs."""
        span_id = generate_span_id()
        assert span_id.startswith("span_")
        assert len(span_id) == 5 + 8  # prefix + 8 hex chars

    def test_generate_span_id_unique(self) -> None:
        """generate_span_id should generate unique IDs."""
        ids = {generate_span_id() for _ in range(100)}
        assert len(ids) == 100
