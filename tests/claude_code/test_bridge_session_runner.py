"""
Tests for bridge/session_runner.py - Child CLI session spawning.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest


class TestSafeFilenameId:
    """Tests for safe_filename_id()."""

    def test_alphanumeric_passthrough(self) -> None:
        """Alphanumeric characters are preserved."""
        from claude_code.bridge.session_runner import safe_filename_id

        assert safe_filename_id("sess-123abc") == "sess-123abc"

    def test_underscore_dash_preserved(self) -> None:
        """Underscores and dashes are preserved."""
        from claude_code.bridge.session_runner import safe_filename_id

        assert safe_filename_id("sess_abc-123") == "sess_abc-123"

    def test_slashes_replaced(self) -> None:
        """Path separators are replaced with underscores."""
        from claude_code.bridge.session_runner import safe_filename_id

        assert safe_filename_id("sess/abc/123") == "sess_abc_123"
        assert safe_filename_id("sess\\abc\\123") == "sess_abc_123"

    def test_dotdot_replaced(self) -> None:
        """Path traversal patterns are replaced."""
        from claude_code.bridge.session_runner import safe_filename_id

        # Each '.' is replaced individually: '../etc/passwd' -> '___etc_passwd'
        assert safe_filename_id("../etc/passwd") == "___etc_passwd"
        # '..' -> '__' then '/'
        assert safe_filename_id("sess..test") == "sess__test"

    def test_spaces_replaced(self) -> None:
        """Spaces are replaced with underscores."""
        from claude_code.bridge.session_runner import safe_filename_id

        assert safe_filename_id("session with spaces") == "session_with_spaces"

    def test_special_chars_replaced(self) -> None:
        """Non-alphanumeric chars (except underscore and dash) are replaced."""
        from claude_code.bridge.session_runner import safe_filename_id

        assert safe_filename_id("sess@#$%123") == "sess____123"
        # Each special char: 'test<>|' -> 't','e','s','t','<','>','|' -> 'test___' (only 3)
        assert safe_filename_id("test<>|") == "test___"

    def test_empty_string(self) -> None:
        """Empty string returns empty string."""
        from claude_code.bridge.session_runner import safe_filename_id

        assert safe_filename_id("") == ""


class TestPermissionRequestType:
    """Tests for PermissionRequest type."""

    def test_permission_request_fields(self) -> None:
        """PermissionRequest should have required fields."""
        from claude_code.bridge.session_runner import PermissionRequest

        req = PermissionRequest(
            type="control_request",
            request_id="req-123",
            request={
                "subtype": "can_use_tool",
                "tool_name": "Bash",
                "input": {"command": "ls"},
                "tool_use_id": "tool-456",
            },
        )
        assert req.type == "control_request"
        assert req.request_id == "req-123"
        assert req.request["tool_name"] == "Bash"
        assert req.request["subtype"] == "can_use_tool"


class TestToolVerbs:
    """Tests for tool verb mapping."""

    def test_common_tools_have_verbs(self) -> None:
        """Common tools should have human-readable verb mappings."""
        from claude_code.bridge.session_runner import TOOL_VERBS

        assert TOOL_VERBS.get("Read") == "Reading"
        assert TOOL_VERBS.get("Bash") == "Running"
        assert TOOL_VERBS.get("Write") == "Writing"
        assert TOOL_VERBS.get("Glob") == "Searching"
        assert TOOL_VERBS.get("WebSearch") == "Searching"


class TestExtractActivities:
    """Tests for extract_activities()."""

    def test_assistant_message_with_tool_use(self) -> None:
        """extract_activities parses assistant message with tool_use."""
        from claude_code.bridge.session_runner import extract_activities

        line = '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Bash","input":{"command":"ls -la"}}]}}'
        activities = extract_activities(line, "sess-1", lambda m: None)
        assert len(activities) == 1
        assert activities[0].type == "tool_start"
        # Summary is "Running ls -la" (verb + target)
        assert "Running" in activities[0].summary
        assert "ls" in activities[0].summary
        assert activities[0].timestamp > 0

    def test_assistant_message_with_text(self) -> None:
        """extract_activities parses assistant message with text content."""
        from claude_code.bridge.session_runner import extract_activities

        line = '{"type":"assistant","message":{"content":[{"type":"text","text":"Hello world"}]}}'
        activities = extract_activities(line, "sess-1", lambda m: None)
        assert len(activities) == 1
        assert activities[0].type == "text"
        assert "Hello world" in activities[0].summary

    def test_result_success(self) -> None:
        """extract_activities parses success result."""
        from claude_code.bridge.session_runner import extract_activities

        line = '{"type":"result","subtype":"success"}'
        activities = extract_activities(line, "sess-1", lambda m: None)
        assert len(activities) == 1
        assert activities[0].type == "result"
        assert "completed" in activities[0].summary.lower()

    def test_result_error(self) -> None:
        """extract_activities parses error result."""
        from claude_code.bridge.session_runner import extract_activities

        line = '{"type":"result","subtype":"error","errors":["Command failed"]}'
        activities = extract_activities(line, "sess-1", lambda m: None)
        assert len(activities) == 1
        assert activities[0].type == "error"
        assert "Command failed" in activities[0].summary

    def test_invalid_json_returns_empty(self) -> None:
        """extract_activities returns empty list for invalid JSON."""
        from claude_code.bridge.session_runner import extract_activities

        activities = extract_activities("not json{", "sess-1", lambda m: None)
        assert activities == []

    def test_non_object_json_returns_empty(self) -> None:
        """extract_activities returns empty list for non-object JSON."""
        from claude_code.bridge.session_runner import extract_activities

        activities = extract_activities('"just a string"', "sess-1", lambda m: None)
        assert activities == []

    def test_unknown_type_returns_empty(self) -> None:
        """extract_activities returns empty list for unknown message type."""
        from claude_code.bridge.session_runner import extract_activities

        line = '{"type":"ping"}'
        activities = extract_activities(line, "sess-1", lambda m: None)
        assert activities == []

    def test_tool_use_without_name(self) -> None:
        """extract_activities handles tool_use without name."""
        from claude_code.bridge.session_runner import extract_activities

        line = '{"type":"assistant","message":{"content":[{"type":"tool_use","input":{}}]}}'
        activities = extract_activities(line, "sess-1", lambda m: None)
        assert len(activities) == 1
        assert activities[0].type == "tool_start"
        assert "Tool" in activities[0].summary  # defaults to "Tool"


class TestExtractUserMessageText:
    """Tests for extract_user_message_text()."""

    def test_real_user_message(self) -> None:
        """extract_user_message_text returns text from real user message."""
        from claude_code.bridge.session_runner import extract_user_message_text

        msg = {
            "type": "user",
            "message": {"content": "Hello, how are you?"},
        }
        text = extract_user_message_text(msg)
        assert text == "Hello, how are you?"

    def test_synthetic_message_returns_none(self) -> None:
        """isSynthetic messages return None."""
        from claude_code.bridge.session_runner import extract_user_message_text

        msg = {
            "type": "user",
            "isSynthetic": True,
            "message": {"content": "Synthetic message"},
        }
        text = extract_user_message_text(msg)
        assert text is None

    def test_replay_message_returns_none(self) -> None:
        """isReplay messages return None."""
        from claude_code.bridge.session_runner import extract_user_message_text

        msg = {
            "type": "user",
            "isReplay": True,
            "message": {"content": "Replay message"},
        }
        text = extract_user_message_text(msg)
        assert text is None

    def test_parent_tool_id_returns_none(self) -> None:
        """Messages with parent_tool_use_id return None."""
        from claude_code.bridge.session_runner import extract_user_message_text

        msg = {
            "type": "user",
            "parent_tool_use_id": "tool-123",
            "message": {"content": "Tool result"},
        }
        text = extract_user_message_text(msg)
        assert text is None

    def test_string_content(self) -> None:
        """extract_user_message_text handles string content."""
        from claude_code.bridge.session_runner import extract_user_message_text

        msg = {"type": "user", "message": {"content": "Direct string"}}
        text = extract_user_message_text(msg)
        assert text == "Direct string"

    def test_empty_content_returns_none(self) -> None:
        """Empty content returns None."""
        from claude_code.bridge.session_runner import extract_user_message_text

        msg = {"type": "user", "message": {"content": ""}}
        text = extract_user_message_text(msg)
        assert text is None


class TestActivityType:
    """Tests for SessionActivity types."""

    def test_tool_start_activity(self) -> None:
        """ToolStartActivity has required fields."""
        from claude_code.bridge.session_runner import ToolStartActivity

        act = ToolStartActivity(
            type="tool_start",
            summary="Running ls",
            timestamp=1000,
        )
        assert act.type == "tool_start"
        assert act.summary == "Running ls"
        assert act.timestamp == 1000

    def test_text_activity(self) -> None:
        """TextActivity has required fields."""
        from claude_code.bridge.session_runner import TextActivity

        act = TextActivity(type="text", summary="Hello", timestamp=2000)
        assert act.type == "text"
        assert act.timestamp == 2000

    def test_result_activity(self) -> None:
        """ResultActivity has required fields."""
        from claude_code.bridge.session_runner import ResultActivity

        act = ResultActivity(
            type="result",
            summary="Session completed",
            timestamp=3000,
        )
        assert act.type == "result"

    def test_error_activity(self) -> None:
        """ErrorActivity has required fields."""
        from claude_code.bridge.session_runner import ErrorActivity

        act = ErrorActivity(
            type="error",
            summary="Command failed",
            timestamp=4000,
        )
        assert act.type == "error"
        assert act.summary == "Command failed"
