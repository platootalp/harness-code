"""
Tests for message models.
"""

from __future__ import annotations

import pytest
from claude_code.models.message import (
    ContentBlock,
    Message,
    Role,
    ToolCall,
)


class TestRole:
    """Tests for Role enum."""

    def test_role_values(self) -> None:
        """Test that Role enum has expected values."""
        assert Role.USER.value == "user"
        assert Role.ASSISTANT.value == "assistant"
        assert Role.SYSTEM.value == "system"
        assert Role.TOOL.value == "tool"

    def test_role_from_string(self) -> None:
        """Test creating Role from string value."""
        assert Role("user") == Role.USER
        assert Role("assistant") == Role.ASSISTANT
        assert Role("system") == Role.SYSTEM
        assert Role("tool") == Role.TOOL


class TestContentBlock:
    """Tests for ContentBlock class."""

    def test_create_text_block(self) -> None:
        """Test creating a text content block."""
        block = ContentBlock(text="Hello, world!")
        assert block.text == "Hello, world!"
        assert block.image_url is None

    def test_create_image_block(self) -> None:
        """Test creating an image content block."""
        block = ContentBlock(image_url="https://example.com/image.png")
        assert block.text is None
        assert block.image_url == "https://example.com/image.png"

    def test_create_empty_block(self) -> None:
        """Test creating an empty content block."""
        block = ContentBlock()
        assert block.text is None
        assert block.image_url is None

    def test_to_dict_text(self) -> None:
        """Test converting text block to dict."""
        block = ContentBlock(text="Hello")
        result = block.to_dict()
        assert result == {"text": "Hello"}

    def test_to_dict_image(self) -> None:
        """Test converting image block to dict."""
        block = ContentBlock(image_url="https://example.com/img.png")
        result = block.to_dict()
        assert result == {"image_url": "https://example.com/img.png"}

    def test_to_dict_both(self) -> None:
        """Test converting block with both fields to dict."""
        block = ContentBlock(text="Hello", image_url="https://example.com/img.png")
        result = block.to_dict()
        assert result == {
            "text": "Hello",
            "image_url": "https://example.com/img.png",
        }

    def test_to_dict_empty(self) -> None:
        """Test converting empty block to dict."""
        block = ContentBlock()
        result = block.to_dict()
        assert result == {}

    def test_from_dict_text(self) -> None:
        """Test creating block from dict with text."""
        data = {"text": "Hello"}
        block = ContentBlock.from_dict(data)
        assert block.text == "Hello"
        assert block.image_url is None

    def test_from_dict_image(self) -> None:
        """Test creating block from dict with image."""
        data = {"image_url": "https://example.com/img.png"}
        block = ContentBlock.from_dict(data)
        assert block.text is None
        assert block.image_url == "https://example.com/img.png"

    def test_roundtrip_text(self) -> None:
        """Test roundtrip serialization for text block."""
        original = ContentBlock(text="Hello, world!")
        restored = ContentBlock.from_dict(original.to_dict())
        assert restored.text == original.text
        assert restored.image_url == original.image_url


class TestToolCall:
    """Tests for ToolCall class."""

    def test_create(self) -> None:
        """Test creating a tool call."""
        tc = ToolCall(id="tc_1", name="bash", arguments='{"command": "ls"}')
        assert tc.id == "tc_1"
        assert tc.name == "bash"
        assert tc.arguments == '{"command": "ls"}'

    def test_to_dict(self) -> None:
        """Test converting tool call to dict."""
        tc = ToolCall(id="tc_1", name="bash", arguments='{"command": "ls"}')
        result = tc.to_dict()
        assert result == {
            "id": "tc_1",
            "name": "bash",
            "arguments": '{"command": "ls"}',
        }

    def test_to_dict_default_arguments(self) -> None:
        """Test converting tool call with default arguments to dict."""
        tc = ToolCall(id="tc_1", name="bash")
        result = tc.to_dict()
        assert result == {"id": "tc_1", "name": "bash", "arguments": "{}"}

    def test_from_dict(self) -> None:
        """Test creating tool call from dict."""
        data = {"id": "tc_1", "name": "bash", "arguments": '{"command": "ls"}'}
        tc = ToolCall.from_dict(data)
        assert tc.id == "tc_1"
        assert tc.name == "bash"
        assert tc.arguments == '{"command": "ls"}'

    def test_from_dict_minimal(self) -> None:
        """Test creating tool call from dict with minimal data."""
        data = {"id": "tc_1", "name": "bash"}
        tc = ToolCall.from_dict(data)
        assert tc.id == "tc_1"
        assert tc.name == "bash"
        assert tc.arguments == "{}"

    def test_roundtrip(self) -> None:
        """Test roundtrip serialization for tool call."""
        original = ToolCall(id="tc_1", name="read", arguments='{"path": "/tmp"}')
        restored = ToolCall.from_dict(original.to_dict())
        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.arguments == original.arguments


class TestMessage:
    """Tests for Message class."""

    def test_create_user_message(self) -> None:
        """Test creating a user message."""
        msg = Message(
            id="msg_1",
            role=Role.USER,
            content_blocks=[ContentBlock(text="Hello")],
        )
        assert msg.id == "msg_1"
        assert msg.role == Role.USER
        assert len(msg.content_blocks) == 1
        assert msg.name is None
        assert msg.tool_calls is None
        assert msg.tool_call_id is None

    def test_create_assistant_message(self) -> None:
        """Test creating an assistant message."""
        msg = Message(
            id="msg_2",
            role=Role.ASSISTANT,
            content_blocks=[ContentBlock(text="Hi there!")],
        )
        assert msg.id == "msg_2"
        assert msg.role == Role.ASSISTANT

    def test_create_system_message(self) -> None:
        """Test creating a system message."""
        msg = Message(
            id="msg_3",
            role=Role.SYSTEM,
            content_blocks=[ContentBlock(text="You are helpful.")],
        )
        assert msg.id == "msg_3"
        assert msg.role == Role.SYSTEM

    def test_create_tool_message(self) -> None:
        """Test creating a tool message."""
        msg = Message(
            id="msg_4",
            role=Role.TOOL,
            content_blocks=[ContentBlock(text="Tool result")],
            tool_call_id="tc_1",
        )
        assert msg.id == "msg_4"
        assert msg.role == Role.TOOL
        assert msg.tool_call_id == "tc_1"

    def test_create_message_with_tool_calls(self) -> None:
        """Test creating an assistant message with tool calls."""
        msg = Message(
            id="msg_5",
            role=Role.ASSISTANT,
            content_blocks=[],
            tool_calls=[ToolCall(id="tc_1", name="bash")],
        )
        assert msg.id == "msg_5"
        assert msg.tool_calls is not None
        assert len(msg.tool_calls) == 1
        assert msg.tool_calls[0].name == "bash"

    def test_create_message_with_name(self) -> None:
        """Test creating a message with a name field."""
        msg = Message(
            id="msg_6",
            role=Role.USER,
            content_blocks=[ContentBlock(text="Hello")],
            name="user-1",
        )
        assert msg.name == "user-1"

    def test_to_dict_basic(self) -> None:
        """Test converting basic message to dict."""
        msg = Message(
            id="msg_1",
            role=Role.USER,
            content_blocks=[ContentBlock(text="Hello")],
        )
        result = msg.to_dict()
        assert result == {
            "id": "msg_1",
            "role": "user",
            "content_blocks": [{"text": "Hello"}],
        }

    def test_to_dict_with_name(self) -> None:
        """Test converting message with name to dict."""
        msg = Message(
            id="msg_1",
            role=Role.USER,
            content_blocks=[ContentBlock(text="Hello")],
            name="user-1",
        )
        result = msg.to_dict()
        assert result["name"] == "user-1"

    def test_to_dict_with_tool_calls(self) -> None:
        """Test converting message with tool calls to dict."""
        msg = Message(
            id="msg_1",
            role=Role.ASSISTANT,
            content_blocks=[],
            tool_calls=[ToolCall(id="tc_1", name="bash")],
        )
        result = msg.to_dict()
        assert result["tool_calls"] == [
            {"id": "tc_1", "name": "bash", "arguments": "{}"},
        ]

    def test_to_dict_with_tool_call_id(self) -> None:
        """Test converting message with tool_call_id to dict."""
        msg = Message(
            id="msg_1",
            role=Role.TOOL,
            content_blocks=[ContentBlock(text="Result")],
            tool_call_id="tc_1",
        )
        result = msg.to_dict()
        assert result["tool_call_id"] == "tc_1"

    def test_to_dict_empty_content_blocks(self) -> None:
        """Test converting message with empty content blocks."""
        msg = Message(
            id="msg_1",
            role=Role.ASSISTANT,
            content_blocks=[],
        )
        result = msg.to_dict()
        assert result["content_blocks"] == []

    def test_from_dict_basic(self) -> None:
        """Test creating message from basic dict."""
        data = {
            "id": "msg_1",
            "role": "user",
            "content_blocks": [{"text": "Hello"}],
        }
        msg = Message.from_dict(data)
        assert msg.id == "msg_1"
        assert msg.role == Role.USER
        assert len(msg.content_blocks) == 1
        assert msg.content_blocks[0].text == "Hello"

    def test_from_dict_with_name(self) -> None:
        """Test creating message from dict with name."""
        data = {
            "id": "msg_1",
            "role": "user",
            "content_blocks": [{"text": "Hello"}],
            "name": "user-1",
        }
        msg = Message.from_dict(data)
        assert msg.name == "user-1"

    def test_from_dict_with_tool_calls(self) -> None:
        """Test creating message from dict with tool calls."""
        data = {
            "id": "msg_1",
            "role": "assistant",
            "content_blocks": [],
            "tool_calls": [{"id": "tc_1", "name": "bash"}],
        }
        msg = Message.from_dict(data)
        assert msg.tool_calls is not None
        assert len(msg.tool_calls) == 1
        assert msg.tool_calls[0].id == "tc_1"
        assert msg.tool_calls[0].name == "bash"

    def test_from_dict_with_tool_call_id(self) -> None:
        """Test creating message from dict with tool_call_id."""
        data = {
            "id": "msg_1",
            "role": "tool",
            "content_blocks": [{"text": "Result"}],
            "tool_call_id": "tc_1",
        }
        msg = Message.from_dict(data)
        assert msg.tool_call_id == "tc_1"

    def test_from_dict_role_as_enum(self) -> None:
        """Test creating message from dict with role already as Role enum."""
        data = {
            "id": "msg_1",
            "role": Role.ASSISTANT,
            "content_blocks": [],
        }
        msg = Message.from_dict(data)
        assert msg.role == Role.ASSISTANT

    def test_from_dict_all_roles(self) -> None:
        """Test creating messages from dict with all role types."""
        for role_str in ["user", "assistant", "system", "tool"]:
            data = {
                "id": "msg_1",
                "role": role_str,
                "content_blocks": [],
            }
            msg = Message.from_dict(data)
            assert msg.role.value == role_str

    def test_roundtrip_user_message(self) -> None:
        """Test roundtrip serialization for user message."""
        original = Message(
            id="msg_1",
            role=Role.USER,
            content_blocks=[ContentBlock(text="Hello, world!")],
            name="alice",
        )
        restored = Message.from_dict(original.to_dict())
        assert restored.id == original.id
        assert restored.role == original.role
        assert len(restored.content_blocks) == len(original.content_blocks)
        assert restored.name == original.name

    def test_roundtrip_assistant_with_tools(self) -> None:
        """Test roundtrip serialization for assistant message with tools."""
        original = Message(
            id="msg_2",
            role=Role.ASSISTANT,
            content_blocks=[ContentBlock(text="I'll run that command.")],
            tool_calls=[
                ToolCall(id="tc_1", name="bash", arguments='{"command": "ls"}'),
            ],
        )
        restored = Message.from_dict(original.to_dict())
        assert restored.id == original.id
        assert restored.role == original.role
        assert restored.tool_calls is not None
        assert len(restored.tool_calls) == 1
        assert restored.tool_calls[0].id == "tc_1"
        assert restored.tool_calls[0].name == "bash"

    def test_roundtrip_tool_message(self) -> None:
        """Test roundtrip serialization for tool message."""
        original = Message(
            id="msg_3",
            role=Role.TOOL,
            content_blocks=[ContentBlock(text="/bin/ls output")],
            tool_call_id="tc_1",
        )
        restored = Message.from_dict(original.to_dict())
        assert restored.id == original.id
        assert restored.role == original.role
        assert restored.tool_call_id == "tc_1"
