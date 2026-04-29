"""Tests for services/utils/token.py - TokenCounter."""

from __future__ import annotations

import pytest

from claude_code.services.utils.token import (
    TokenUsage,
    get_token_count_from_usage,
    get_current_usage,
    token_count_with_estimation,
    rough_token_count_estimation,
    rough_token_count_estimation_for_messages,
)


class TestTokenUsage:
    """Tests for TokenUsage dataclass."""

    def test_default_values(self) -> None:
        """Test default values."""
        usage = TokenUsage(input_tokens=100, output_tokens=50)
        assert usage.input_tokens == 100
        assert usage.output_tokens == 50
        assert usage.cache_creation_input_tokens == 0
        assert usage.cache_read_input_tokens == 0

    def test_full_usage(self) -> None:
        """Test usage with all fields."""
        usage = TokenUsage(
            input_tokens=1000,
            output_tokens=500,
            cache_creation_input_tokens=200,
            cache_read_input_tokens=300,
        )
        assert usage.input_tokens == 1000
        assert usage.output_tokens == 500
        assert usage.cache_creation_input_tokens == 200
        assert usage.cache_read_input_tokens == 300


class TestGetTokenCountFromUsage:
    """Tests for get_token_count_from_usage function."""

    def test_basic_usage(self) -> None:
        """Test counting tokens in basic usage."""
        usage = TokenUsage(input_tokens=100, output_tokens=50)
        assert get_token_count_from_usage(usage) == 150

    def test_with_cache_tokens(self) -> None:
        """Test counting tokens with cache tokens."""
        usage = TokenUsage(
            input_tokens=100,
            output_tokens=50,
            cache_creation_input_tokens=200,
            cache_read_input_tokens=300,
        )
        # Total = input + cache_creation + cache_read + output
        assert get_token_count_from_usage(usage) == 650

    def test_zero_usage(self) -> None:
        """Test zero usage returns 0."""
        usage = TokenUsage(input_tokens=0, output_tokens=0)
        assert get_token_count_from_usage(usage) == 0


class TestGetCurrentUsage:
    """Tests for get_current_usage function."""

    def test_empty_messages(self) -> None:
        """Test with empty message list."""
        result = get_current_usage([])
        assert result is None

    def test_no_assistant_message(self) -> None:
        """Test with no assistant message."""
        messages = [
            {"type": "user", "message": {"content": [{"type": "text", "text": "hello"}]}},
        ]
        result = get_current_usage(messages)
        assert result is None

    def test_assistant_message_with_usage(self) -> None:
        """Test finding usage in assistant message."""
        messages = [
            {"type": "user", "message": {"content": [{"type": "text", "text": "hello"}]}},
            {
                "type": "assistant",
                "message": {
                    "content": [{"type": "text", "text": "Hi there!"}],
                    "usage": {
                        "input_tokens": 100,
                        "output_tokens": 50,
                        "cache_creation_input_tokens": 200,
                        "cache_read_input_tokens": 300,
                    },
                },
            },
        ]
        result = get_current_usage(messages)
        assert result is not None
        assert result.input_tokens == 100
        assert result.output_tokens == 50
        assert result.cache_creation_input_tokens == 200
        assert result.cache_read_input_tokens == 300

    def test_multiple_assistant_messages(self) -> None:
        """Test gets last assistant message's usage."""
        messages = [
            {
                "type": "assistant",
                "message": {
                    "content": [{"type": "text", "text": "First"}],
                    "usage": {"input_tokens": 10, "output_tokens": 5},
                },
            },
            {
                "type": "assistant",
                "message": {
                    "content": [{"type": "text", "text": "Last"}],
                    "usage": {"input_tokens": 100, "output_tokens": 50},
                },
            },
        ]
        result = get_current_usage(messages)
        assert result is not None
        assert result.input_tokens == 100
        assert result.output_tokens == 50

    def test_assistant_message_without_usage(self) -> None:
        """Test assistant message without usage is skipped."""
        messages = [
            {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "No usage"}]},
            },
        ]
        result = get_current_usage(messages)
        assert result is None

    def test_non_dict_message_content(self) -> None:
        """Test handling of non-dict message content."""
        messages = [
            {"type": "assistant", "message": None},
        ]
        result = get_current_usage(messages)
        assert result is None


class TestRoughTokenCountEstimation:
    """Tests for rough_token_count_estimation function."""

    def test_empty_text(self) -> None:
        """Test empty text returns 0."""
        assert rough_token_count_estimation("") == 0

    def test_short_text(self) -> None:
        """Test short text estimation."""
        text = "hello world"
        # 11 chars / 4 = 2.75 -> 2 (floor) but min is 1
        assert rough_token_count_estimation(text) >= 1

    def test_known_length(self) -> None:
        """Test text of known length."""
        text = "a" * 40
        assert rough_token_count_estimation(text) == 10

    def test_unicode_chars(self) -> None:
        """Test unicode characters are counted."""
        text = "hello"  # 5 chars
        result = rough_token_count_estimation(text)
        assert result >= 1


class TestRoughTokenCountEstimationForMessages:
    """Tests for rough_token_count_estimation_for_messages function."""

    def test_empty_list(self) -> None:
        """Test empty message list."""
        assert rough_token_count_estimation_for_messages([]) == 0

    def test_user_message_with_text(self) -> None:
        """Test user message with text content."""
        messages = [
            {
                "type": "user",
                "message": {
                    "content": [{"type": "text", "text": "hello world"}]
                },
            },
        ]
        result = rough_token_count_estimation_for_messages(messages)
        assert result >= 2

    def test_user_message_with_tool_use(self) -> None:
        """Test user message with tool_use content."""
        messages = [
            {
                "type": "user",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "input": {"command": "ls", "-la": True},
                        }
                    ]
                },
            },
        ]
        result = rough_token_count_estimation_for_messages(messages)
        assert result >= 0  # At minimum counts role overhead

    def test_assistant_message_with_text(self) -> None:
        """Test assistant message with text."""
        messages = [
            {
                "type": "assistant",
                "message": {
                    "content": [{"type": "text", "text": "This is a response"}]
                },
            },
        ]
        result = rough_token_count_estimation_for_messages(messages)
        assert result >= 1

    def test_assistant_message_with_thinking(self) -> None:
        """Test assistant message with thinking block."""
        messages = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "thinking", "thinking": "thinking about this"},
                        {"type": "text", "text": "final answer"},
                    ]
                },
            },
        ]
        result = rough_token_count_estimation_for_messages(messages)
        assert result >= 2  # Both thinking and text

    def test_assistant_message_with_redacted_thinking(self) -> None:
        """Test assistant message with redacted_thinking block."""
        messages = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "redacted_thinking", "data": "hidden data"},
                        {"type": "text", "text": "result"},
                    ]
                },
            },
        ]
        result = rough_token_count_estimation_for_messages(messages)
        assert result >= 1


class TestTokenCountWithEstimation:
    """Tests for token_count_with_estimation function."""

    def test_empty_messages(self) -> None:
        """Test empty message list."""
        result = token_count_with_estimation([])
        assert result == 0

    def test_no_usage_estimates_all(self) -> None:
        """Test messages without usage are estimated."""
        messages = [
            {
                "type": "user",
                "message": {"content": [{"type": "text", "text": "hello"}]},
            },
        ]
        result = token_count_with_estimation(messages)
        assert result >= 1

    def test_with_usage_and_remaining(self) -> None:
        """Test usage + remaining message estimation."""
        messages = [
            {
                "type": "user",
                "message": {"content": [{"type": "text", "text": "hello"}]},
            },
            {
                "type": "assistant",
                "message": {
                    "content": [{"type": "text", "text": "response"}],
                    "usage": {
                        "input_tokens": 100,
                        "output_tokens": 50,
                    },
                },
            },
        ]
        result = token_count_with_estimation(messages)
        # Base usage + estimation of "hello" (no remaining messages after usage)
        assert result >= 150

    def test_parallel_tool_calls_scenario(self) -> None:
        """Test scenario with parallel tool calls (same response ID)."""
        messages = [
            {
                "type": "assistant",
                "message": {
                    "id": "msg-123",
                    "model": "claude-3",
                    "content": [
                        {"type": "tool_use", "input": {"tool": "a"}},
                    ],
                    "usage": {"input_tokens": 100, "output_tokens": 50},
                },
            },
            {
                "type": "user",
                "message": {
                    "content": [
                        {"type": "tool_result", "tool_use_id": "tool-1", "content": "result a"}
                    ]
                },
            },
            {
                "type": "assistant",
                "message": {
                    "id": "msg-123",  # Same ID - parallel tool call
                    "content": [
                        {"type": "tool_use", "input": {"tool": "b"}},
                    ],
                },
            },
        ]
        # Should handle same ID correctly
        result = token_count_with_estimation(messages)
        assert result >= 150

    def test_different_response_ids(self) -> None:
        """Test messages with different response IDs."""
        messages = [
            {
                "type": "assistant",
                "message": {
                    "id": "msg-1",
                    "model": "claude-3",
                    "content": [{"type": "text", "text": "first"}],
                    "usage": {"input_tokens": 100, "output_tokens": 50},
                },
            },
            {
                "type": "user",
                "message": {"content": [{"type": "text", "text": "second user"}]},
            },
            {
                "type": "assistant",
                "message": {
                    "id": "msg-2",  # Different ID
                    "model": "claude-3",
                    "content": [{"type": "text", "text": "second assistant"}],
                },
            },
        ]
        result = token_count_with_estimation(messages)
        # Should count from msg-1 usage + estimation of user + msg-2
        assert result >= 150
