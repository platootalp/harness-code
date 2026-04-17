"""
Stream event types for Claude Code streaming API.

This module defines all stream event types including:
- StreamEvent: Base event structure with enum type
- ThinkingEvent: Internal thinking/thoughts from extended thinking
- ToolUseEvent: Tool call start event
- ToolResultEvent: Tool execution result event
- MessageStartEvent: Message stream start
- ContentBlockStartEvent: Content block start
- ContentBlockDeltaEvent: Content block delta (text chunks)
- MessageDeltaEvent: Message delta (usage, stop reason)
- MessageStopEvent: Message stream stop
- TombstoneEvent: Placeholder/deleted content marker

Based on Anthropic streaming API event types and internal streaming patterns.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any

# =============================================================================
# Stream Event Type Enum
# =============================================================================


class StreamEventType(StrEnum):
    """All stream event types used by Claude Code.

    These cover the full lifecycle of a streaming response including:
    - Claude internal events (thinking, reflection)
    - Tool events (call start, result, call end)
    - Step events (start, complete)
    - Message events (message_start, content_block_start/delta, message_delta, message_stop)
    - Termination events (final_result, termination_reason)
    - Utility events (heartbeat, error)
    - Tombstone events for deleted content
    """

    THOUGHT = "thought"
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_END = "tool_call_end"
    TOOL_RESULT = "tool_result"
    STEP_COMPLETE = "step_complete"
    STEP_START = "step_start"
    FINAL_RESULT = "final_result"
    ERROR = "error"
    REFLECTION = "reflection"
    REFLECTION_COMPLETE = "reflection_complete"
    TOKEN_USAGE = "token_usage"
    TERMINATION_REASON = "termination_reason"
    HEARTBEAT = "heartbeat"

    # Anthropic streaming API event types
    THINKING = "thinking"
    MESSAGE_START = "message_start"
    CONTENT_BLOCK_START = "content_block_start"
    CONTENT_BLOCK_DELTA = "content_block_delta"
    MESSAGE_DELTA = "message_delta"
    MESSAGE_STOP = "message_stop"
    TOMBSTONE = "tombstone"


# =============================================================================
# Base Stream Event
# =============================================================================


@dataclass
class StreamEvent:
    """Base stream event structure.

    All streaming events share these common fields and carry
    type-specific data in the `data` field.

    Attributes:
        event_type: The type of this event (from StreamEventType enum).
        agent_id: Identifier of the agent that emitted this event.
        step: Current step number (0-indexed) within this stream.
        data: Type-specific payload (structure varies by event_type).
        timestamp: Unix timestamp when this event was created.
        trace_id: Optional trace identifier for distributed tracing.
        span_id: Optional span identifier for distributed tracing.
    """

    event_type: StreamEventType
    agent_id: str
    step: int
    data: dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    trace_id: str | None = None
    span_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert this event to a dictionary.

        Serializes the event to a JSON-compatible dictionary. Enum values
        are converted to their string values for JSON compatibility.

        Returns:
            Dictionary representation of this event.
        """
        result = asdict(self)
        result["event_type"] = self.event_type.value
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StreamEvent:
        """Reconstruct a StreamEvent from a dictionary.

        Args:
            data: Dictionary previously produced by to_dict().

        Returns:
            A new StreamEvent instance.

        Raises:
            KeyError: If required fields are missing from data.
            ValueError: If event_type string is not a valid StreamEventType.
        """
        event_type_str = data.get("event_type")
        if not isinstance(event_type_str, str):
            raise ValueError("event_type is required in StreamEvent data")
        event_type = StreamEventType(event_type_str)

        return cls(
            event_type=event_type,
            agent_id=data["agent_id"],
            step=data["step"],
            data=data["data"],
            timestamp=data.get("timestamp", time.time()),
            trace_id=data.get("trace_id"),
            span_id=data.get("span_id"),
        )


# =============================================================================
# Anthropic Streaming API Event Types
# =============================================================================


@dataclass
class ThinkingEvent:
    """Extended thinking event from Anthropic's extended thinking API.

    This event carries the thinking/thought content that Claude generates
    during extended thinking mode. The thinking content is typically hidden
    from the user and used for internal reasoning.

    Attributes:
        thinking: The thinking/reasoning text content.
        is_visible: Whether this thinking is visible to the user.
        signature: Cryptographic signature for verification (if enabled).
    """

    thinking: str
    is_visible: bool = False
    signature: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "thinking": self.thinking,
            "is_visible": self.is_visible,
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ThinkingEvent:
        """Deserialize from dictionary."""
        return cls(
            thinking=data["thinking"],
            is_visible=data.get("is_visible", False),
            signature=data.get("signature"),
        )


@dataclass
class ToolUseEvent:
    """Tool use event indicating the start of a tool call.

    Attributes:
        tool_use_id: Unique identifier for this tool call.
        tool_name: Name of the tool being called.
        tool_args: Arguments being passed to the tool.
        tool_input: Alias for tool_args (Anthropic API compatibility).
    """

    tool_use_id: str
    tool_name: str
    tool_args: dict[str, Any] = field(default_factory=dict)
    tool_input: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "tool_use_id": self.tool_use_id,
            "tool_name": self.tool_name,
            "tool_args": self.tool_args,
            "tool_input": self.tool_input,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolUseEvent:
        """Deserialize from dictionary."""
        return cls(
            tool_use_id=data["tool_use_id"],
            tool_name=data["tool_name"],
            tool_args=data.get("tool_args", {}),
            tool_input=data.get("tool_input"),
        )


@dataclass
class ToolResultEvent:
    """Tool execution result event.

    Carries the result of a tool execution. Can represent either
    a successful result or an error.

    Attributes:
        tool_use_id: ID of the tool call this result corresponds to.
        tool_name: Name of the tool that was executed.
        result: The result content (string) or None on error.
        is_error: Whether this result represents an error condition.
        content: Alias for result (Anthropic API compatibility).
        error: Error message string if is_error is True.
    """

    tool_use_id: str
    tool_name: str
    result: str | None = None
    is_error: bool = False
    content: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "tool_use_id": self.tool_use_id,
            "tool_name": self.tool_name,
            "result": self.result,
            "is_error": self.is_error,
            "content": self.content,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolResultEvent:
        """Deserialize from dictionary."""
        return cls(
            tool_use_id=data["tool_use_id"],
            tool_name=data["tool_name"],
            result=data.get("result"),
            is_error=data.get("is_error", False),
            content=data.get("content"),
            error=data.get("error"),
        )


@dataclass
class MessageStartEvent:
    """Message stream start event.

    Indicates the beginning of a new message stream. Contains the
    initial message structure.

    Attributes:
        message: Initial message data (role, content blocks, etc.).
        index: Index of this message in the conversation.
        type: Always "message_start" for this event type.
    """

    message: dict[str, Any] = field(default_factory=dict)
    index: int = 0
    type: str = "message_start"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "type": self.type,
            "message": self.message,
            "index": self.index,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MessageStartEvent:
        """Deserialize from dictionary."""
        return cls(
            message=data.get("message", {}),
            index=data.get("index", 0),
            type=data.get("type", "message_start"),
        )


@dataclass
class ContentBlockStartEvent:
    """Content block start event.

    Indicates the beginning of a new content block within a message.

    Attributes:
        index: Index of this content block in the message.
        content_block: The content block data (type, text, etc.).
        type: Always "content_block_start" for this event type.
    """

    index: int
    content_block: dict[str, Any] = field(default_factory=dict)
    type: str = "content_block_start"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "type": self.type,
            "index": self.index,
            "content_block": self.content_block,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ContentBlockStartEvent:
        """Deserialize from dictionary."""
        return cls(
            index=data["index"],
            content_block=data.get("content_block", {}),
            type=data.get("type", "content_block_start"),
        )


@dataclass
class ContentBlockDeltaEvent:
    """Content block delta/event event.

    Carries incremental content for a content block. For text content,
    this is typically a text delta/chunk.

    Attributes:
        index: Index of the content block this delta belongs to.
        delta: The delta data (e.g., {"type": "text_delta", "text": "..."}).
        type: Always "content_block_delta" for this event type.
    """

    index: int
    delta: dict[str, Any] = field(default_factory=dict)
    type: str = "content_block_delta"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "type": self.type,
            "index": self.index,
            "delta": self.delta,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ContentBlockDeltaEvent:
        """Deserialize from dictionary."""
        return cls(
            index=data["index"],
            delta=data.get("delta", {}),
            type=data.get("type", "content_block_delta"),
        )


@dataclass
class MessageDeltaEvent:
    """Message delta event.

    Carries the final delta information for a message including
    usage statistics and stop reason.

    Attributes:
        usage: Token usage statistics for this message.
        stop_reason: Reason the message generation stopped.
        type: Always "message_delta" for this event type.
    """

    usage: dict[str, Any] = field(default_factory=dict)
    delta: dict[str, Any] = field(default_factory=dict)
    stop_reason: str | None = None
    type: str = "message_delta"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "type": self.type,
            "usage": self.usage,
            "delta": self.delta,
            "stop_reason": self.stop_reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MessageDeltaEvent:
        """Deserialize from dictionary."""
        return cls(
            usage=data.get("usage", {}),
            stop_reason=data.get("stop_reason"),
            type=data.get("type", "message_delta"),
        )


@dataclass
class MessageStopEvent:
    """Message stream stop event.

    Indicates the end of a message stream.

    Attributes:
        type: Always "message_stop" for this event type.
    """

    type: str = "message_stop"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {"type": self.type}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MessageStopEvent:
        """Deserialize from dictionary."""
        return cls(type=data.get("type", "message_stop"))


@dataclass
class TombstoneEvent:
    """Tombstone event for deleted/redacted content.

    Tombstones mark content that has been deleted or redacted from
    the conversation history. They preserve the structural position
    of deleted content while indicating it is no longer present.

    Attributes:
        index: Index of the content block that was deleted.
        type: Always "tombstone" for this event type.
    """

    index: int = 0
    type: str = "tombstone"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "type": self.type,
            "index": self.index,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TombstoneEvent:
        """Deserialize from dictionary."""
        return cls(
            index=data.get("index", 0),
            type=data.get("type", "tombstone"),
        )


# =============================================================================
# Factory and Utility Functions
# =============================================================================


def create_stream_event(
    event_type: StreamEventType,
    agent_id: str,
    step: int,
    data: dict[str, Any],
    trace_id: str | None = None,
    span_id: str | None = None,
) -> StreamEvent:
    """Factory function to create a StreamEvent with auto-generated timestamp.

    Args:
        event_type: Type of the stream event.
        agent_id: Identifier of the agent.
        step: Current step number.
        data: Event-specific payload data.
        trace_id: Optional trace identifier.
        span_id: Optional span identifier.

    Returns:
        A new StreamEvent instance.
    """
    return StreamEvent(
        event_type=event_type,
        agent_id=agent_id,
        step=step,
        data=data,
        timestamp=time.time(),
        trace_id=trace_id,
        span_id=span_id,
    )


def generate_trace_id() -> str:
    """Generate a new trace identifier.

    Returns:
        A new trace ID with 'trace_' prefix.
    """
    return f"trace_{uuid.uuid4().hex[:12]}"


def generate_span_id() -> str:
    """Generate a new span identifier.

    Returns:
        A new span ID with 'span_' prefix.
    """
    return f"span_{uuid.uuid4().hex[:8]}"
