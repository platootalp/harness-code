"""Message creation and manipulation utilities."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


# =============================================================================
# Constants
# =============================================================================

INTERRUPT_MESSAGE = "[Request interrupted by user]"
INTERRUPT_MESSAGE_FOR_TOOL_USE = "[Request interrupted by user for tool use]"
CANCEL_MESSAGE = "The user doesn't want to take this action right now..."
REJECT_MESSAGE = "The user doesn't want to proceed with this tool use..."
DENIAL_WORKAROUND_GUIDANCE = (
    "IMPORTANT: You *may* attempt to accomplish the goal with a different "
    "approach, but you *must* respect the user's decision and not ask about it "
    "again in this session."
)


# =============================================================================
# Message Creation
# =============================================================================


@dataclass
class UserMessage:
    """A user message for API calls."""

    type: str = "user"
    uuid: str = ""
    timestamp: str = ""
    content: str | list[dict[str, Any]] = ""
    message: dict[str, Any] = field(default_factory=dict)
    is_meta: bool = False
    is_visible_in_transcript_only: bool = False
    is_virtual: bool = False
    is_compact_summary: bool = False


@dataclass
class AssistantMessage:
    """A synthetic assistant message."""

    type: str = "assistant"
    uuid: str = ""
    timestamp: str = ""
    message: dict[str, Any] = field(default_factory=dict)
    is_api_error_message: bool = False
    is_virtual: bool = False


@dataclass
class ProgressMessage:
    """A progress message for tool execution."""

    type: str = "progress"
    tool_use_id: str = ""
    parent_tool_use_id: str = ""
    data: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Message Factory Functions
# =============================================================================


def create_user_message(
    content: str | list[dict[str, Any]],
    is_meta: bool = False,
    is_visible_in_transcript_only: bool = False,
    is_virtual: bool = False,
    uuid_val: str | None = None,
    timestamp: str | None = None,
    origin: str | None = None,
) -> UserMessage:
    """Create a user message.

    Args:
        content: The message content (text string or content blocks).
        is_meta: Whether this is a meta message.
        is_visible_in_transcript_only: Whether to show only in transcript.
        is_virtual: Whether this is a synthetic/virtual message.
        uuid_val: Optional UUID override.
        timestamp: Optional timestamp override.
        origin: Optional origin field.

    Returns:
        A new UserMessage instance.
    """
    msg = UserMessage(
        type="user",
        content=content,
        is_meta=is_meta,
        is_visible_in_transcript_only=is_visible_in_transcript_only,
        is_virtual=is_virtual,
    )
    if uuid_val:
        msg.uuid = uuid_val
    else:
        msg.uuid = str(uuid.uuid4())
    if timestamp:
        msg.timestamp = timestamp
    if origin:
        msg.message = {"origin": origin}
    return msg


def create_assistant_message(
    content: str | list[dict[str, Any]],
    usage: dict[str, int] | None = None,
    is_virtual: bool = False,
) -> AssistantMessage:
    """Create a synthetic assistant message.

    Args:
        content: The message content.
        usage: Optional token usage information.
        is_virtual: Whether this is a synthetic message.

    Returns:
        A new AssistantMessage instance.
    """
    msg: AssistantMessage = AssistantMessage(
        type="assistant",
        uuid=str(uuid.uuid4()),
        is_virtual=is_virtual,
    )
    if isinstance(content, str):
        msg.message = {"content": [{"type": "text", "text": content}]}
    else:
        msg.message = {"content": content}
    if usage:
        msg.message["usage"] = usage
    return msg


def create_progress_message(
    tool_use_id: str,
    parent_tool_use_id: str,
    data: dict[str, Any],
) -> ProgressMessage:
    """Create a progress message for tool execution.

    Args:
        tool_use_id: The tool use ID.
        parent_tool_use_id: The parent tool use ID.
        data: Progress data.

    Returns:
        A new ProgressMessage instance.
    """
    return ProgressMessage(
        type="progress",
        tool_use_id=tool_use_id,
        parent_tool_use_id=parent_tool_use_id,
        data=data,
    )


# =============================================================================
# Content Extraction
# =============================================================================


def extract_text_content(content: str | list[dict[str, Any]]) -> str:
    """Extract text from message content blocks.

    Args:
        content: Content string or list of content blocks.

    Returns:
        Extracted text content.
    """
    if isinstance(content, str):
        return content

    parts: list[str] = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            text = block.get("text", "")
            if text:
                parts.append(text)
    return " ".join(parts)


def get_user_message_text(message: UserMessage) -> str:
    """Extract text content from a user message.

    Args:
        message: The user message.

    Returns:
        Text content of the message.
    """
    return extract_text_content(message.content)


# =============================================================================
# Type Guards
# =============================================================================


def is_tool_use_request_message(message: Any) -> bool:
    """Type guard for tool use request messages.

    Args:
        message: The message to check.

    Returns:
        True if this is a tool use request (assistant role with tool_use blocks).
    """
    if not isinstance(message, dict):
        return False
    role = message.get("role", "")
    if role != "assistant":
        return False
    content = message.get("content", [])
    if not isinstance(content, list):
        return False
    return any(
        isinstance(block, dict) and block.get("type") == "tool_use"
        for block in content
    )


def is_tool_use_result_message(message: Any) -> bool:
    """Type guard for tool use result messages.

    Args:
        message: The message to check.

    Returns:
        True if this is a tool use result.
    """
    if not isinstance(message, dict):
        return False
    role = message.get("role", "")
    if role != "user":
        return False
    content = message.get("content", [])
    if not isinstance(content, list):
        return False
    return any(
        isinstance(block, dict) and block.get("type") == "tool_result"
        for block in content
    )


def is_thinking_message(message: Any) -> bool:
    """Check if message contains a thinking block.

    Args:
        message: The message to check.

    Returns:
        True if message has thinking content.
    """
    if not isinstance(message, dict):
        return False
    content = message.get("content", [])
    if not isinstance(content, list):
        return False
    return any(
        isinstance(block, dict) and block.get("type") == "thinking"
        for block in content
    )


def is_synthetic_message(message: Any) -> bool:
    """Check if message is synthetic (interrupt/cancel/reject).

    Args:
        message: The message to check.

    Returns:
        True if message is synthetic.
    """
    if isinstance(message, AssistantMessage):
        return message.is_virtual
    if isinstance(message, UserMessage):
        return message.is_virtual
    if isinstance(message, dict):
        return message.get("is_virtual", False) is True
    return False


def is_classifier_denial(content: str) -> bool:
    """Check if tool result is a classifier denial.

    Args:
        content: The tool result content.

    Returns:
        True if this is a classifier denial.
    """
    denial_phrases = [
        "i'm not able",
        "i cannot",
        "i'm not able to help",
        "i can't help",
        "not able to provide",
        "cannot provide",
        "don't have the ability",
    ]
    lower_content = content.lower()
    return any(phrase in lower_content for phrase in denial_phrases)


# =============================================================================
# Message Utilities
# =============================================================================


def extract_tag(html: str, tag_name: str) -> str | None:
    """Extract content from XML-style tags.

    Args:
        html: HTML-like string with tags.
        tag_name: Name of the tag to extract.

    Returns:
        Content between tags, or None if not found.
    """
    pattern = rf"<{tag_name}>(.*?)</{tag_name}>"
    match = re.search(pattern, html, re.DOTALL)
    if match:
        return match.group(1)
    return None


def normalize_messages(
    messages: list[Any],
) -> list[Any]:
    """Split multi-block messages into single-block messages.

    Args:
        messages: List of messages to normalize.

    Returns:
        Messages with multi-block content split into individual messages.
    """
    result: list[Any] = []
    for msg in messages:
        if isinstance(msg, dict) and "content" in msg:
            content = msg["content"]
            if isinstance(content, list) and len(content) > 1:
                for block in content:
                    new_msg = {**msg, "content": [block]}
                    result.append(new_msg)
            else:
                result.append(msg)
        else:
            result.append(msg)
    return result


def get_last_assistant_message(
    messages: list[Any],
) -> dict[str, Any] | None:
    """Find the last assistant message in the list.

    Args:
        messages: List of messages.

    Returns:
        Last assistant message, or None.
    """
    for msg in reversed(messages):
        if isinstance(msg, dict):
            role = msg.get("role", "")
            if role == "assistant":
                return msg
            if isinstance(msg, AssistantMessage):
                return msg
    return None


def reorder_messages_in_ui(
    messages: list[Any],
    synthetic_streaming_tool_use_messages: list[Any],
) -> list[Any]:
    """Reorder messages to group tool uses with their results.

    Args:
        messages: Original message list.
        synthetic_streaming_tool_use_messages: Tool use messages to group.

    Returns:
        Reordered message list.
    """
    if not synthetic_streaming_tool_use_messages:
        return list(messages)

    result: list[Any] = list(messages)
    for tool_msg in synthetic_streaming_tool_use_messages:
        tool_use_id = tool_msg.get("tool_use_id") if isinstance(tool_msg, dict) else None
        if not tool_use_id:
            continue
        for i, msg in enumerate(result):
            if isinstance(msg, dict) and msg.get("tool_call_id") == tool_use_id:
                result.insert(i, tool_msg)
                break
    return result


# =============================================================================
# UUID Derivation
# =============================================================================


def derive_uuid(parent_uuid: str, index: int) -> str:
    """Derive a deterministic UUID from parent UUID and index.

    Uses a namespace UUID combined with parent UUID and index
    to generate deterministic child UUIDs.

    Args:
        parent_uuid: The parent message UUID.
        index: The child index.

    Returns:
        A derived UUID string.
    """
    namespace = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
    combined = f"{parent_uuid}:{index}"
    return str(uuid.uuid5(namespace, combined))


def derive_short_message_id(uuid_str: str) -> str:
    """Generate a 6-character base36 short ID from a UUID.

    Args:
        uuid_str: A UUID string.

    Returns:
        6-char base36 lowercase string.
    """
    try:
        uid = uuid.UUID(uuid_str)
    except ValueError:
        uid = uuid.uuid5(uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8"), uuid_str)
    return uid.hex[:6]


# =============================================================================
# Rejection Messages
# =============================================================================


def build_yolo_rejection_message(reason: str) -> str:
    """Build rejection message for auto mode denials.

    Args:
        reason: The denial reason.

    Returns:
        Formatted rejection message.
    """
    return f"[Permission denied in auto mode: {reason}] {DENIAL_WORKAROUND_GUIDANCE}"
