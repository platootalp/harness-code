"""Tests for utils/messages.py."""

from __future__ import annotations

import pytest

from claude_code.utils.messages import (
    CANCEL_MESSAGE,
    DENIAL_WORKAROUND_GUIDANCE,
    INTERRUPT_MESSAGE,
    INTERRUPT_MESSAGE_FOR_TOOL_USE,
    REJECT_MESSAGE,
    AssistantMessage,
    ProgressMessage,
    UserMessage,
    build_yolo_rejection_message,
    create_assistant_message,
    create_progress_message,
    create_user_message,
    derive_short_message_id,
    derive_uuid,
    extract_tag,
    extract_text_content,
    get_last_assistant_message,
    get_user_message_text,
    is_classifier_denial,
    is_synthetic_message,
    is_thinking_message,
    is_tool_use_request_message,
    is_tool_use_result_message,
    normalize_messages,
    reorder_messages_in_ui,
)


class TestConstants:
    """Tests for message constants."""

    def test_interrupt_message(self) -> None:
        assert INTERRUPT_MESSAGE == "[Request interrupted by user]"

    def test_interrupt_message_for_tool_use(self) -> None:
        assert INTERRUPT_MESSAGE_FOR_TOOL_USE == "[Request interrupted by user for tool use]"

    def test_cancel_message(self) -> None:
        assert CANCEL_MESSAGE == "The user doesn't want to take this action right now..."

    def test_reject_message(self) -> None:
        assert REJECT_MESSAGE == "The user doesn't want to proceed with this tool use..."

    def test_denial_workaround_guidance(self) -> None:
        assert "IMPORTANT" in DENIAL_WORKAROUND_GUIDANCE
        assert "different approach" in DENIAL_WORKAROUND_GUIDANCE


class TestCreateUserMessage:
    """Tests for create_user_message."""

    def test_basic(self) -> None:
        msg = create_user_message("Hello")
        assert isinstance(msg, UserMessage)
        assert msg.type == "user"
        assert msg.content == "Hello"
        assert msg.is_meta is False
        assert msg.is_virtual is False
        assert msg.uuid != ""

    def test_with_blocks(self) -> None:
        blocks = [{"type": "text", "text": "Hello"}]
        msg = create_user_message(blocks)
        assert msg.content == blocks

    def test_with_options(self) -> None:
        msg = create_user_message(
            "test",
            is_meta=True,
            is_visible_in_transcript_only=True,
            is_virtual=True,
            uuid_val="custom-uuid",
            timestamp="2024-01-01T00:00:00Z",
        )
        assert msg.is_meta is True
        assert msg.is_visible_in_transcript_only is True
        assert msg.is_virtual is True
        assert msg.uuid == "custom-uuid"
        assert msg.timestamp == "2024-01-01T00:00:00Z"


class TestCreateAssistantMessage:
    """Tests for create_assistant_message."""

    def test_string_content(self) -> None:
        msg = create_assistant_message("Hello")
        assert isinstance(msg, AssistantMessage)
        assert msg.type == "assistant"
        assert msg.uuid != ""
        assert msg.is_virtual is False
        assert msg.message["content"] == [{"type": "text", "text": "Hello"}]

    def test_with_blocks(self) -> None:
        blocks = [{"type": "text", "text": "Hi"}]
        msg = create_assistant_message(blocks)
        assert msg.message["content"] == blocks

    def test_with_usage(self) -> None:
        msg = create_assistant_message("Hello", usage={"input_tokens": 100})
        assert msg.message["usage"] == {"input_tokens": 100}

    def test_is_virtual(self) -> None:
        msg = create_assistant_message("Hello", is_virtual=True)
        assert msg.is_virtual is True


class TestCreateProgressMessage:
    """Tests for create_progress_message."""

    def test_basic(self) -> None:
        msg = create_progress_message(
            tool_use_id="tu_123",
            parent_tool_use_id="tu_parent",
            data={"progress": 50},
        )
        assert isinstance(msg, ProgressMessage)
        assert msg.type == "progress"
        assert msg.tool_use_id == "tu_123"
        assert msg.parent_tool_use_id == "tu_parent"
        assert msg.data == {"progress": 50}


class TestExtractTextContent:
    """Tests for extract_text_content."""

    def test_string_content(self) -> None:
        result = extract_text_content("Hello world")
        assert result == "Hello world"

    def test_blocks_with_text(self) -> None:
        blocks = [
            {"type": "text", "text": "Hello"},
            {"type": "text", "text": "World"},
        ]
        result = extract_text_content(blocks)
        assert result == "Hello World"

    def test_blocks_with_non_text(self) -> None:
        blocks = [
            {"type": "tool_use", "text": "ignored"},
            {"type": "text", "text": "visible"},
        ]
        result = extract_text_content(blocks)
        assert result == "visible"


class TestGetUserMessageText:
    """Tests for get_user_message_text."""

    def test_string_content(self) -> None:
        msg = UserMessage(content="Hello")
        assert get_user_message_text(msg) == "Hello"

    def test_blocks(self) -> None:
        msg = UserMessage(content=[{"type": "text", "text": "Hi there"}])
        assert get_user_message_text(msg) == "Hi there"


class TestIsToolUseRequestMessage:
    """Tests for is_tool_use_request_message."""

    def test_tool_use_request(self) -> None:
        msg = {
            "role": "assistant",
            "content": [{"type": "tool_use", "name": "Bash", "input": {}}],
        }
        assert is_tool_use_request_message(msg) is True

    def test_text_only(self) -> None:
        msg = {"role": "assistant", "content": [{"type": "text", "text": "hi"}]}
        assert is_tool_use_request_message(msg) is False

    def test_user_role(self) -> None:
        msg = {"role": "user", "content": [{"type": "tool_use"}]}
        assert is_tool_use_request_message(msg) is False


class TestIsToolUseResultMessage:
    """Tests for is_tool_use_result_message."""

    def test_tool_result(self) -> None:
        msg = {
            "role": "user",
            "content": [{"type": "tool_result", "content": "done"}],
        }
        assert is_tool_use_result_message(msg) is True

    def test_non_tool_result(self) -> None:
        msg = {"role": "user", "content": [{"type": "text", "text": "hi"}]}
        assert is_tool_use_result_message(msg) is False

    def test_wrong_role(self) -> None:
        msg = {
            "role": "assistant",
            "content": [{"type": "tool_result", "content": "done"}],
        }
        assert is_tool_use_result_message(msg) is False


class TestIsThinkingMessage:
    """Tests for is_thinking_message."""

    def test_thinking(self) -> None:
        msg = {"role": "assistant", "content": [{"type": "thinking", "thinking": "..."}]}
        assert is_thinking_message(msg) is True

    def test_no_thinking(self) -> None:
        msg = {"role": "assistant", "content": [{"type": "text", "text": "hi"}]}
        assert is_thinking_message(msg) is False


class TestIsSyntheticMessage:
    """Tests for is_synthetic_message."""

    def test_user_message_virtual(self) -> None:
        msg = UserMessage(is_virtual=True)
        assert is_synthetic_message(msg) is True

    def test_assistant_message_virtual(self) -> None:
        msg = AssistantMessage(is_virtual=True)
        assert is_synthetic_message(msg) is True

    def test_dict_virtual(self) -> None:
        msg = {"is_virtual": True}
        assert is_synthetic_message(msg) is True

    def test_not_virtual(self) -> None:
        msg = UserMessage(is_virtual=False)
        assert is_synthetic_message(msg) is False


class TestIsClassifierDenial:
    """Tests for is_classifier_denial."""

    def test_im_not_able(self) -> None:
        assert is_classifier_denial("I'm not able to help with that.") is True

    def test_i_cannot(self) -> None:
        assert is_classifier_denial("I cannot provide that information.") is True

    def test_normal_content(self) -> None:
        assert is_classifier_denial("Here is the file content: def foo(): pass") is False


class TestExtractTag:
    """Tests for extract_tag."""

    def test_simple_tag(self) -> None:
        html = "<message>Hello World</message>"
        assert extract_tag(html, "message") == "Hello World"

    def test_nested_tag(self) -> None:
        html = "<outer><inner>content</inner></outer>"
        assert extract_tag(html, "inner") == "content"

    def test_not_found(self) -> None:
        html = "<other>text</other>"
        assert extract_tag(html, "message") is None


class TestNormalizeMessages:
    """Tests for normalize_messages."""

    def test_single_block(self) -> None:
        msgs = [{"role": "user", "content": [{"type": "text", "text": "hi"}]}]
        result = normalize_messages(msgs)
        assert len(result) == 1

    def test_multi_block_split(self) -> None:
        msgs = [
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "hello"},
                    {"type": "text", "text": "world"},
                ],
            }
        ]
        result = normalize_messages(msgs)
        assert len(result) == 2


class TestGetLastAssistantMessage:
    """Tests for get_last_assistant_message."""

    def test_finds_assistant(self) -> None:
        msgs = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hi there"},
        ]
        result = get_last_assistant_message(msgs)
        assert result["role"] == "assistant"

    def test_empty_list(self) -> None:
        assert get_last_assistant_message([]) is None


class TestReorderMessagesInUi:
    """Tests for reorder_messages_in_ui."""

    def test_empty_synthetic(self) -> None:
        msgs = [{"role": "user", "content": "hi"}]
        result = reorder_messages_in_ui(msgs, [])
        assert result == msgs

    def test_no_matching_tool_id(self) -> None:
        msgs = [{"role": "user", "content": "hi", "tool_call_id": "tu_999"}]
        synthetic = [{"tool_use_id": "tu_123", "role": "assistant"}]
        result = reorder_messages_in_ui(msgs, synthetic)
        assert len(result) == 1


class TestDeriveUuid:
    """Tests for derive_uuid."""

    def test_deterministic(self) -> None:
        parent = "550e8400-e29b-41d4-a716-446655440000"
        uuid1 = derive_uuid(parent, 0)
        uuid2 = derive_uuid(parent, 0)
        assert uuid1 == uuid2

    def test_different_index(self) -> None:
        parent = "550e8400-e29b-41d4-a716-446655440000"
        uuid1 = derive_uuid(parent, 0)
        uuid2 = derive_uuid(parent, 1)
        assert uuid1 != uuid2

    def test_different_parent(self) -> None:
        uuid1 = derive_uuid("550e8400-e29b-41d4-a716-446655440000", 0)
        uuid2 = derive_uuid("550e8400-e29b-41d4-a716-446655440001", 0)
        assert uuid1 != uuid2


class TestDeriveShortMessageId:
    """Tests for derive_short_message_id."""

    def test_length(self) -> None:
        uid = "550e8400-e29b-41d4-a716-446655440000"
        short = derive_short_message_id(uid)
        assert len(short) == 6

    def test_deterministic(self) -> None:
        uid = "550e8400-e29b-41d4-a716-446655440000"
        assert derive_short_message_id(uid) == derive_short_message_id(uid)

    def test_valid_hex(self) -> None:
        uid = "550e8400-e29b-41d4-a716-446655440000"
        short = derive_short_message_id(uid)
        assert all(c in "0123456789abcdef" for c in short)


class TestBuildYoloRejectionMessage:
    """Tests for build_yolo_rejection_message."""

    def test_contains_reason(self) -> None:
        result = build_yolo_rejection_message("no permission")
        assert "no permission" in result

    def test_contains_guidance(self) -> None:
        result = build_yolo_rejection_message("test")
        assert DENIAL_WORKAROUND_GUIDANCE in result
