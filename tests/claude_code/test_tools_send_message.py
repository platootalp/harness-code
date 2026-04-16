"""
Tests for SendMessageTool.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from claude_code.tools.send_message import SendMessageTool


@pytest.fixture
def send_message_tool() -> SendMessageTool:
    return SendMessageTool()


@pytest.fixture
def mock_context() -> MagicMock:
    ctx = MagicMock()
    ctx.get_app_state = MagicMock(return_value=MagicMock())
    return ctx


class TestSendMessageTool:
    """Tests for SendMessageTool."""

    def test_name(self, send_message_tool: SendMessageTool) -> None:
        assert send_message_tool.name == "SendMessage"

    def test_aliases(self, send_message_tool: SendMessageTool) -> None:
        assert send_message_tool.aliases is None

    def test_search_hint(self, send_message_tool: SendMessageTool) -> None:
        assert "send" in send_message_tool.search_hint.lower()
        assert "message" in send_message_tool.search_hint.lower()

    def test_should_defer(self, send_message_tool: SendMessageTool) -> None:
        assert send_message_tool.should_defer is True

    def test_always_load(self, send_message_tool: SendMessageTool) -> None:
        assert send_message_tool.always_load is False

    def test_max_result_size_chars(self, send_message_tool: SendMessageTool) -> None:
        assert send_message_tool.max_result_size_chars == 100_000

    def test_strict(self, send_message_tool: SendMessageTool) -> None:
        assert send_message_tool.strict is False

    def test_description_text(self, send_message_tool: SendMessageTool) -> None:
        assert "message" in send_message_tool.description_text.lower()

    def test_prompt_text(self, send_message_tool: SendMessageTool) -> None:
        assert "message" in send_message_tool.prompt_text.lower()

    def test_input_schema(self, send_message_tool: SendMessageTool) -> None:
        schema = send_message_tool.input_schema
        assert schema["type"] == "object"
        assert "to" in schema["required"]
        assert "message" in schema["required"]
        props = schema["properties"]
        assert "to" in props
        assert "summary" in props
        assert "message" in props

    def test_output_schema(self, send_message_tool: SendMessageTool) -> None:
        schema = send_message_tool.output_schema
        assert schema["type"] == "object"
        props = schema["properties"]
        assert "success" in props
        assert "message" in props

    def test_user_facing_name(self, send_message_tool: SendMessageTool) -> None:
        assert send_message_tool.user_facing_name({}) == "SendMessage"

    def test_is_enabled(self, send_message_tool: SendMessageTool) -> None:
        assert send_message_tool.is_enabled() is True

    def test_is_read_only_text_message(self, send_message_tool: SendMessageTool) -> None:
        assert send_message_tool.is_read_only({"message": "Hello"}) is True

    def test_is_read_only_structured_message(self, send_message_tool: SendMessageTool) -> None:
        assert (
            send_message_tool.is_read_only(
                {"message": {"type": "shutdown_request"}}
            )
            is False
        )

    def test_validate_input_missing_to(self, send_message_tool: SendMessageTool) -> None:
        result = send_message_tool.validate_input({"message": "Hello"}, MagicMock())
        assert result is not True
        assert isinstance(result, tuple)
        assert "to must not be empty" in result[1]
        assert result[2] == 9

    def test_validate_input_text_message_missing_summary(
        self, send_message_tool: SendMessageTool
    ) -> None:
        result = send_message_tool.validate_input(
            {"to": "dev-1", "message": "Hello"}, MagicMock()
        )
        assert result is not True
        assert isinstance(result, tuple)
        assert "summary" in result[1]

    def test_validate_input_text_message_with_summary(
        self, send_message_tool: SendMessageTool
    ) -> None:
        result = send_message_tool.validate_input(
            {"to": "dev-1", "message": "Hello", "summary": "Greeting"},
            MagicMock(),
        )
        assert result is True

    def test_validate_input_structured_broadcast_disallowed(
        self, send_message_tool: SendMessageTool
    ) -> None:
        result = send_message_tool.validate_input(
            {"to": "*", "message": {"type": "shutdown_request"}}, MagicMock()
        )
        assert result is not True
        assert isinstance(result, tuple)
        assert "broadcast" in result[1]

    def test_validate_input_structured_ok(self, send_message_tool: SendMessageTool) -> None:
        result = send_message_tool.validate_input(
            {"to": "dev-1", "message": {"type": "shutdown_request"}}, MagicMock()
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_call_no_app_state(self, send_message_tool: SendMessageTool) -> None:
        ctx = MagicMock()
        ctx.get_app_state = None
        result = await send_message_tool.call(
            {"to": "dev-1", "message": "Hello"}, ctx, AsyncMock(), None
        )
        assert result["data"]["success"] is False
        assert "Cannot access app state" in result["data"]["message"]

    @pytest.mark.asyncio
    async def test_call_broadcast_text(
        self, send_message_tool: SendMessageTool, mock_context: MagicMock
    ) -> None:
        result = await send_message_tool.call(
            {"to": "*", "summary": "Broadcast", "message": "Hello team"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["success"] is True
        assert "broadcast" in result["data"]["message"].lower()

    @pytest.mark.asyncio
    async def test_call_send_to_teammate(
        self, send_message_tool: SendMessageTool, mock_context: MagicMock
    ) -> None:
        result = await send_message_tool.call(
            {"to": "dev-1", "summary": "Greeting", "message": "Hello"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["success"] is True
        assert "dev-1" in result["data"]["message"]

    @pytest.mark.asyncio
    async def test_call_shutdown_request(
        self, send_message_tool: SendMessageTool, mock_context: MagicMock
    ) -> None:
        result = await send_message_tool.call(
            {
                "to": "dev-1",
                "message": {"type": "shutdown_request", "reason": "Done"},
            },
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["success"] is True
        assert "Shutdown request" in result["data"]["message"]
        assert "request_id" in result["data"]

    @pytest.mark.asyncio
    async def test_call_shutdown_approve(
        self, send_message_tool: SendMessageTool, mock_context: MagicMock
    ) -> None:
        result = await send_message_tool.call(
            {
                "to": "team-lead",
                "message": {
                    "type": "shutdown_response",
                    "approve": True,
                    "request_id": "req-123",
                },
            },
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["success"] is True
        assert "approved" in result["data"]["message"].lower()

    @pytest.mark.asyncio
    async def test_call_shutdown_reject(
        self, send_message_tool: SendMessageTool, mock_context: MagicMock
    ) -> None:
        result = await send_message_tool.call(
            {
                "to": "team-lead",
                "message": {
                    "type": "shutdown_response",
                    "approve": False,
                    "request_id": "req-123",
                },
            },
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["success"] is True
        assert "rejected" in result["data"]["message"].lower()

    @pytest.mark.asyncio
    async def test_call_plan_approve(
        self, send_message_tool: SendMessageTool, mock_context: MagicMock
    ) -> None:
        result = await send_message_tool.call(
            {
                "to": "planner",
                "message": {
                    "type": "plan_approval_response",
                    "approve": True,
                    "request_id": "plan-456",
                },
            },
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["success"] is True
        assert "approved" in result["data"]["message"].lower()

    @pytest.mark.asyncio
    async def test_call_plan_reject(
        self, send_message_tool: SendMessageTool, mock_context: MagicMock
    ) -> None:
        result = await send_message_tool.call(
            {
                "to": "planner",
                "message": {
                    "type": "plan_approval_response",
                    "approve": False,
                    "request_id": "plan-456",
                },
            },
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["success"] is True
        assert "rejected" in result["data"]["message"].lower()

    @pytest.mark.asyncio
    async def test_call_unknown_type(
        self, send_message_tool: SendMessageTool, mock_context: MagicMock
    ) -> None:
        result = await send_message_tool.call(
            {"to": "dev-1", "message": {"type": "unknown_type"}},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["success"] is False
        assert "Unknown message type" in result["data"]["message"]

    def test_map_tool_result_to_tool_result_block_param(
        self, send_message_tool: SendMessageTool
    ) -> None:
        result = send_message_tool.map_tool_result_to_tool_result_block_param(
            {"success": True, "message": "Sent"}, "tool-123"
        )
        assert result["tool_use_id"] == "tool-123"
        assert result["type"] == "tool_result"
