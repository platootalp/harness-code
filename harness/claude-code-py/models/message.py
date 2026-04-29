"""
Message type definitions for Claude Code.

This module defines the core message models including:
- Role: Enum for message roles (user, assistant, system, tool)
- ContentBlock: Content block with text or image_url
- Message: Conversation message with role and content
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# =============================================================================
# Role Enum
# =============================================================================

class Role(Enum):
    """Enumeration of message roles in a conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


# =============================================================================
# Content Block
# =============================================================================

@dataclass
class ContentBlock:
    """A content block within a message.

    Attributes:
        text: Text content of the block.
        image_url: URL for image content.
    """

    text: str | None = None
    image_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert the content block to a dictionary.

        Returns:
            Dictionary representation of the content block.
        """
        result: dict[str, Any] = {}
        if self.text is not None:
            result["text"] = self.text
        if self.image_url is not None:
            result["image_url"] = self.image_url
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ContentBlock:
        """Create a ContentBlock from a dictionary.

        Args:
            data: Dictionary containing 'text' and/or 'image_url' keys.

        Returns:
            A new ContentBlock instance.
        """
        return cls(
            text=data.get("text"),
            image_url=data.get("image_url"),
        )


# =============================================================================
# Tool Call
# =============================================================================

@dataclass
class ToolCall:
    """Represents a tool call within an assistant message.

    Attributes:
        id: Unique identifier for the tool call.
        name: Name of the tool being called.
        arguments: Arguments passed to the tool (as a JSON string).
    """

    id: str
    name: str
    arguments: str = "{}"

    def to_dict(self) -> dict[str, Any]:
        """Convert the tool call to a dictionary.

        Returns:
            Dictionary representation of the tool call.
        """
        return {
            "id": self.id,
            "name": self.name,
            "arguments": self.arguments,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolCall:
        """Create a ToolCall from a dictionary.

        Args:
            data: Dictionary containing 'id', 'name', and 'arguments'.

        Returns:
            A new ToolCall instance.
        """
        return cls(
            id=data["id"],
            name=data["name"],
            arguments=data.get("arguments", "{}"),
        )


# =============================================================================
# Message
# =============================================================================

@dataclass
class Message:
    """A conversation message.

    Attributes:
        id: Unique identifier for the message.
        role: The role of the message sender.
        content_blocks: List of content blocks in the message.
        name: Optional name associated with the message.
        tool_calls: Optional list of tool calls made by the assistant.
        tool_call_id: Optional ID linking this message to a tool result.
    """

    id: str
    role: Role
    content_blocks: list[ContentBlock] = field(default_factory=list)
    name: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert the message to a dictionary.

        Returns:
            Dictionary representation of the message.
        """
        result: dict[str, Any] = {
            "id": self.id,
            "role": self.role.value,
            "content_blocks": [cb.to_dict() for cb in self.content_blocks],
        }
        if self.name is not None:
            result["name"] = self.name
        if self.tool_calls is not None:
            result["tool_calls"] = [tc.to_dict() for tc in self.tool_calls]
        if self.tool_call_id is not None:
            result["tool_call_id"] = self.tool_call_id
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Message:
        """Create a Message from a dictionary.

        Args:
            data: Dictionary containing message data.

        Returns:
            A new Message instance.
        """
        role_value = data["role"]
        role = role_value if isinstance(role_value, Role) else Role(role_value)

        content_blocks = [
            ContentBlock.from_dict(cb) for cb in data.get("content_blocks", [])
        ]

        tool_calls: list[ToolCall] | None = None
        if "tool_calls" in data:
            tool_calls = [ToolCall.from_dict(tc) for tc in data["tool_calls"]]

        return cls(
            id=data["id"],
            role=role,
            content_blocks=content_blocks,
            name=data.get("name"),
            tool_calls=tool_calls,
            tool_call_id=data.get("tool_call_id"),
        )
