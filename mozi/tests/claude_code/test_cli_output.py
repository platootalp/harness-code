"""
Tests for OutputHandler.
"""

from __future__ import annotations

from io import StringIO
from typing import Any
from unittest.mock import MagicMock

import pytest
from claude_code.cli.output import OutputBlock, OutputHandler


class TestOutputBlock:
    """Tests for OutputBlock dataclass."""

    def test_creation(self) -> None:
        """OutputBlock can be created with required fields."""
        block = OutputBlock(type="text", content="Hello")
        assert block.type == "text"
        assert block.content == "Hello"
        assert block.language is None
        assert block.tool_name is None

    def test_with_language(self) -> None:
        """OutputBlock can include language for code blocks."""
        block = OutputBlock(type="code", content="print('hi')", language="python")
        assert block.type == "code"
        assert block.content == "print('hi')"
        assert block.language == "python"

    def test_with_tool_name(self) -> None:
        """OutputBlock can include tool name."""
        block = OutputBlock(
            type="tool_use", content="", tool_name="Bash"
        )
        assert block.type == "tool_use"
        assert block.tool_name == "Bash"


class MockConsole:
    """Mock Rich Console for testing without terminal dependencies."""

    def __init__(self) -> None:
        self.output: list[str] = []
        self._width: int = 80
        self._color_system: str | None = None
        self._stderr: bool = False

    @property
    def width(self) -> int:
        return self._width

    def print(self, *args: Any, **kwargs: Any) -> None:
        """Capture print output."""
        parts = []
        for arg in args:
            if hasattr(arg, "__str__"):
                parts.append(str(arg))
            else:
                parts.append(str(arg))
        self.output.append("".join(parts))

    def clear_output(self) -> None:
        """Clear captured output."""
        self.output.clear()


class TestOutputHandlerInit:
    """Tests for OutputHandler initialization."""

    def test_default_init(self) -> None:
        """Handler initializes with defaults."""
        handler = OutputHandler()
        assert handler._format_type == "text"
        assert handler._console is None
        assert handler._streaming_text == ""
        assert handler._message_id is None

    def test_with_format_type(self) -> None:
        """Handler accepts format type."""
        handler = OutputHandler(format_type="json")
        assert handler._format_type == "json"

    def test_with_mock_console(self) -> None:
        """Handler accepts a console instance."""
        mock_console = MockConsole()
        handler = OutputHandler(console=mock_console)
        assert handler._console is mock_console

    def test_console_lazy_creation(self) -> None:
        """Console is created on first access."""
        # Mock Rich to avoid import errors when rich is not installed
        mock_console = MockConsole()
        handler = OutputHandler(console=mock_console)
        console = handler.console
        assert console is mock_console
        assert handler._console is mock_console


class TestOutputHandlerTruncate:
    """Tests for text truncation."""

    def test_truncate_short_text(self) -> None:
        """Short text is not truncated."""
        handler = OutputHandler()
        result = handler._truncate("hello", 10)
        assert result == "hello"

    def test_truncate_long_text(self) -> None:
        """Long text is truncated with ellipsis."""
        handler = OutputHandler()
        result = handler._truncate("hello world", 5)
        assert result == "hello..."

    def test_truncate_exact_length(self) -> None:
        """Text at max length is not truncated."""
        handler = OutputHandler()
        result = handler._truncate("hello", 5)
        assert result == "hello"


class TestOutputHandlerDirectPrint:
    """Tests for direct print methods."""

    @pytest.fixture
    def handler(self) -> OutputHandler:
        """Create handler with mock console."""
        mock = MockConsole()
        return OutputHandler(console=mock)

    def test_print_text(self, handler: OutputHandler) -> None:
        """print_text outputs text."""
        handler.print_text("Hello, world!")
        assert "Hello, world!" in handler.console.output

    def test_print_error(self, handler: OutputHandler) -> None:
        """print_error outputs in red."""
        handler.print_error("Something went wrong")
        output = "".join(handler.console.output)
        assert "Error:" in output
        assert "Something went wrong" in output

    def test_print_warning(self, handler: OutputHandler) -> None:
        """print_warning outputs in yellow."""
        handler.print_warning("Be careful")
        output = "".join(handler.console.output)
        assert "Warning:" in output
        assert "Be careful" in output

    def test_print_success(self, handler: OutputHandler) -> None:
        """print_success outputs in green."""
        handler.print_success("Done!")
        output = "".join(handler.console.output)
        assert "Success:" in output
        assert "Done!" in output

    def test_print_info(self, handler: OutputHandler) -> None:
        """print_info outputs in cyan."""
        handler.print_info("FYI")
        output = "".join(handler.console.output)
        assert "Info:" in output
        assert "FYI" in output

    def test_print_separator(self, handler: OutputHandler) -> None:
        """print_separator outputs dashes."""
        handler.print_separator(width=10)
        output = "".join(handler.console.output)
        assert output == "-" * 10

    def test_print_separator_custom_char(self, handler: OutputHandler) -> None:
        """print_separator accepts custom character."""
        handler.print_separator(char="=", width=5)
        output = "".join(handler.console.output)
        assert output == "=" * 5

    def test_print_markdown_fallback(self, handler: OutputHandler) -> None:
        """print_markdown falls back to plain text."""
        handler.print_markdown("# Hello\nThis is **bold**.")
        # Falls back since Rich Markdown may not be available
        assert len(handler.console.output) > 0

    def test_print_code_fallback(self, handler: OutputHandler) -> None:
        """print_code falls back to plain text."""
        handler.print_code("def hello(): pass", language="python")
        # Falls back since Rich Syntax may not be available
        assert len(handler.console.output) > 0

    def test_print_panel_fallback(self, handler: OutputHandler) -> None:
        """print_panel falls back to plain text."""
        handler.print_panel("Content here", title="My Panel")
        assert len(handler.console.output) > 0

    def test_print_table_fallback(self, handler: OutputHandler) -> None:
        """print_table falls back to text rows."""
        data = [
            {"name": "Alice", "age": "30"},
            {"name": "Bob", "age": "25"},
        ]
        handler.print_table(data, columns=["name", "age"])
        assert len(handler.console.output) > 0


class TestOutputHandlerEventHandling:
    """Tests for event handling."""

    @pytest.fixture
    def handler(self) -> OutputHandler:
        """Create handler with mock console."""
        mock = MockConsole()
        return OutputHandler(console=mock)

    def test_handle_thinking_event(self, handler: OutputHandler) -> None:
        """ThinkingEvent renders thinking content."""
        from claude_code.models.events import ThinkingEvent

        event = ThinkingEvent(
            thinking="Let me think about this...",
        )
        handler.handle_event(event)
        # Should render the thinking indicator
        assert len(handler.console.output) > 0

    def test_handle_tool_use_event(self, handler: OutputHandler) -> None:
        """ToolUseEvent renders tool usage."""
        from claude_code.models.events import ToolUseEvent

        event = ToolUseEvent(
            tool_use_id="test_1",
            tool_name="Bash",
            tool_args={"command": "ls -la"},
        )
        handler.handle_event(event)
        output = "".join(handler.console.output)
        assert "Bash" in output

    def test_handle_tool_result_event(self, handler: OutputHandler) -> None:
        """ToolResultEvent renders tool result."""
        from claude_code.models.events import ToolResultEvent

        event = ToolResultEvent(
            tool_use_id="test-123",
            tool_name="Bash",
            content="file1.txt\nfile2.txt",
        )
        handler.handle_event(event)
        output = "".join(handler.console.output)
        assert "file1.txt" in output

    def test_handle_tool_result_error(self, handler: OutputHandler) -> None:
        """ToolResultEvent with is_error renders in red."""
        from claude_code.models.events import ToolResultEvent

        event = ToolResultEvent(
            tool_use_id="test-123",
            tool_name="Bash",
            content="Error: permission denied",
            is_error=True,
        )
        handler.handle_event(event)
        output = "".join(handler.console.output)
        assert "Error" in output

    def test_handle_content_block_delta_text(self, handler: OutputHandler) -> None:
        """ContentBlockDeltaEvent streams text."""
        from claude_code.models.events import ContentBlockDeltaEvent

        event = ContentBlockDeltaEvent(
            index=0,
            delta={"type": "text_delta", "text": "Hello"},
        )
        handler.handle_event(event)
        assert "Hello" in "".join(handler.console.output)

    def test_handle_message_delta_event(self, handler: OutputHandler) -> None:
        """MessageDeltaEvent is handled without error."""
        from claude_code.models.events import MessageDeltaEvent

        event = MessageDeltaEvent(
            usage={"output_tokens": 10},
            stop_reason="end_turn",
        )
        handler.handle_event(event)

    def test_handle_message_stop_finalizes_streaming(
        self, handler: OutputHandler
    ) -> None:
        """MessageStopEvent finalizes streaming."""
        from claude_code.models.events import MessageStopEvent

        event = MessageStopEvent()
        handler.handle_event(event)
        # Should clear streaming state
        assert handler._streaming_text == ""


class TestOutputHandlerStructuredOutput:
    """Tests for structured output formats."""

    @pytest.fixture
    def handler(self) -> OutputHandler:
        """Create handler with json format."""
        mock = MockConsole()
        return OutputHandler(console=mock, format_type="stream-json")

    def test_json_format_outputs_type(
        self, handler: OutputHandler
    ) -> None:
        """JSON format includes event type."""
        from claude_code.models.events import ThinkingEvent

        event = ThinkingEvent(thinking="Thinking...")
        handler.handle_event(event)
        output = "".join(handler.console.output)
        assert "thinking" in output.lower()

    def test_tool_use_event_json_format(
        self, handler: OutputHandler
    ) -> None:
        """ToolUseEvent in JSON format includes tool name and input."""
        from claude_code.models.events import ToolUseEvent

        event = ToolUseEvent(
            tool_use_id="test_1",
            tool_name="Bash",
            tool_args={"command": "ls"},
        )
        handler.handle_event(event)
        output = "".join(handler.console.output)
        assert "Bash" in output


class TestOutputHandlerStreamingState:
    """Tests for streaming state management."""

    def test_streaming_accumulates_across_events(self) -> None:
        """Streaming text accumulates across multiple events."""
        mock = MockConsole()
        handler = OutputHandler(console=mock)

        from claude_code.models.events import ContentBlockDeltaEvent

        handler.handle_event(
            ContentBlockDeltaEvent(index=0, delta={"type": "text_delta", "text": "Hello "})
        )
        handler.handle_event(
            ContentBlockDeltaEvent(index=0, delta={"type": "text_delta", "text": "World"})
        )

        assert handler._streaming_text == "Hello World"

    def test_finalize_clears_streaming(self) -> None:
        """Finalize clears streaming text."""
        mock = MockConsole()
        handler = OutputHandler(console=mock)

        from claude_code.models.events import (
            ContentBlockDeltaEvent,
            MessageStopEvent,
        )

        handler.handle_event(
            ContentBlockDeltaEvent(index=0, delta={"type": "text_delta", "text": "Hi"})
        )
        assert handler._streaming_text == "Hi"

        handler.handle_event(MessageStopEvent())
        assert handler._streaming_text == ""

    def test_finalize_clears_tool_results(self) -> None:
        """Finalize clears tool results."""
        mock = MockConsole()
        handler = OutputHandler(console=mock)

        from claude_code.models.events import MessageStopEvent

        handler._tool_results.append({"id": "test"})
        handler.handle_event(MessageStopEvent())
        assert handler._tool_results == []
