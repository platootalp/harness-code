"""
Output handling and formatting for CLI.

TypeScript equivalent: src/cli/print.ts

Provides output formatting using Rich with support for:
- Markdown rendering
- Syntax-highlighted code
- Tables and panels
- Streaming text output
- Multiple output formats (text, json, stream-json)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from rich.console import Console

from ..models.events import (
    ContentBlockDeltaEvent,
    ContentBlockStartEvent,
    MessageDeltaEvent,
    MessageStartEvent,
    MessageStopEvent,
    ThinkingEvent,
    TombstoneEvent,
    ToolResultEvent,
    ToolUseEvent,
)


@dataclass
class OutputBlock:
    """Output block with type and content."""

    type: Literal["text", "code", "tool_use", "tool_result", "error"]
    content: str
    language: str | None = None
    tool_name: str | None = None


class OutputHandler:
    """Handles output rendering for different modes.

    TypeScript equivalent: src/cli/print.ts StructuredIO

    Supports multiple output formats:
    - text: Plain text with ANSI colors (default)
    - json: Structured JSON output
    - stream-json: Newline-delimited JSON (NDJSON)
    """

    def __init__(
        self,
        console: Console | None = None,
        format_type: str = "text",
    ) -> None:
        """Initialize output handler.

        Args:
            console: Rich Console instance. Created if not provided.
            format_type: Output format (text, json, stream-json).
        """
        self._console = console
        self._format_type = format_type
        self._streaming_text = ""
        self._message_id: str | None = None
        self._tool_results: list[dict[str, Any]] = []

    @property
    def console(self) -> Console:
        """Get or create Rich Console instance."""
        if self._console is None:
            try:
                from rich.console import Console

                self._console = Console(
                    color_system="auto",
                    stderr=self._format_type != "stream-json",
                )
            except ImportError:
                raise RuntimeError(
                    "Rich library required for CLI output. "
                    "Install with: pip install rich"
                ) from None
        return self._console

    def handle_event(self, event: Any) -> None:
        """Handle a stream event and render it.

        Args:
            event: Event from the query engine (ThinkingEvent, ToolUseEvent, etc.).
        """
        if self._format_type in ("json", "stream-json"):
            self._handle_structured_event(event)
            return

        # Text format
        if isinstance(event, ThinkingEvent):
            self._render_thinking(event.thinking)

        elif isinstance(event, ToolUseEvent):
            self._render_tool_use(event.tool_name, event.tool_args)

        elif isinstance(event, ToolResultEvent):
            content = event.content or event.result or ""
            self._render_tool_result(content, event.is_error)

        elif isinstance(event, ContentBlockDeltaEvent):
            self._render_content_delta(event.delta)

        elif isinstance(event, MessageDeltaEvent):
            self._render_message_delta(event.usage)

        elif isinstance(event, MessageStopEvent):
            self._finalize_streaming()

        elif isinstance(event, MessageStartEvent):
            self._message_id = getattr(event, "message_id", None)

        elif isinstance(event, ContentBlockStartEvent):
            pass  # Handled via delta events

        elif isinstance(event, TombstoneEvent):
            pass  # Skip tombstones in text mode

    def _handle_structured_event(self, event: Any) -> None:
        """Handle event for structured output formats.

        Args:
            event: Event from the query engine.
        """
        # Extract event data using type attribute or class name
        event_type = getattr(event, "type", None) or type(event).__name__
        event_data: dict[str, Any] = {"type": event_type}

        if isinstance(event, ThinkingEvent):
            event_data["thinking"] = event.thinking

        elif isinstance(event, ToolUseEvent):
            event_data["tool_use_id"] = event.tool_use_id
            event_data["tool_name"] = event.tool_name
            event_data["tool_args"] = event.tool_args

        elif isinstance(event, ToolResultEvent):
            event_data["tool_use_id"] = event.tool_use_id
            event_data["tool_name"] = event.tool_name
            event_data["result"] = event.result
            event_data["content"] = event.content
            event_data["is_error"] = event.is_error

        elif isinstance(event, ContentBlockDeltaEvent):
            event_data["index"] = event.index
            event_data["delta"] = event.delta

        elif isinstance(event, MessageDeltaEvent):
            event_data["delta"] = event.delta
            event_data["usage"] = getattr(event, "usage", None)

        elif isinstance(event, MessageStopEvent):
            event_data["stop_reason"] = getattr(event, "stop_reason", None)

        elif isinstance(event, MessageStartEvent):
            event_data["message"] = getattr(event, "message", {})

        elif isinstance(event, ContentBlockStartEvent):
            event_data["index"] = event.index
            event_data["block"] = getattr(event, "block", {})

        # Output as NDJSON
        self.console.print(json.dumps(event_data))

    def _render_thinking(self, thinking: str) -> None:
        """Render thinking/throttling content.

        Args:
            thinking: Thinking content to display.
        """
        if thinking:
            self.console.print("[dim]Thinking...[/dim]")

    def _render_tool_use(self, tool_name: str, input_args: dict[str, Any]) -> None:
        """Render tool use block.

        Args:
            tool_name: Name of the tool being used.
            input_args: Tool input arguments.
        """
        self.console.print(f"\n[cyan]Using tool:[/cyan] [bold]{tool_name}[/bold]")
        if input_args:
            # Show first few args truncated
            args_preview = ", ".join(
                f"{k}={self._truncate(str(v), 50)}"
                for k, v in list(input_args.items())[:3]
            )
            self.console.print(f"[dim]{args_preview}[/dim]")

    def _render_tool_result(
        self,
        result: str,
        is_error: bool = False,
    ) -> None:
        """Render tool result.

        Args:
            result: Tool result content.
            is_error: Whether the result is an error.
        """
        style = "red" if is_error else "green"
        prefix = "Error" if is_error else "Result"

        # Truncate long results
        truncated = self._truncate(result, 2000)

        self.console.print(f"\n[{style}]{prefix}:[/{style}]")
        if result != truncated:
            truncated += "\n[dim](truncated)[/dim]"
        self.console.print(truncated)

    def _render_content_delta(self, delta: dict[str, Any]) -> None:
        """Render content block delta (streaming text).

        Args:
            delta: Delta data containing text or other content.
        """
        if delta.get("type") == "text_delta":
            text = delta.get("text", "")
            self._streaming_text += text
            self.console.print(text, end="")

    def _render_message_delta(self, delta: dict[str, Any]) -> None:
        """Render message delta.

        Args:
            delta: Delta data containing text or usage info.
        """
        if delta.get("type") == "text_delta":
            text = delta.get("text", "")
            self._streaming_text += text
            self.console.print(text, end="")

    def _finalize_streaming(self) -> None:
        """Finalize streaming output."""
        if self._streaming_text:
            self.console.print()  # Newline
        self._streaming_text = ""
        self._message_id = None
        self._tool_results.clear()

    def _truncate(self, text: str, max_length: int) -> str:
        """Truncate text to maximum length.

        Args:
            text: Text to truncate.
            max_length: Maximum length.

        Returns:
            Truncated text.
        """
        if len(text) <= max_length:
            return text
        return text[:max_length] + "..."

    # =========================================================================
    # Direct output methods
    # =========================================================================

    def print_text(self, text: str, **kwargs: Any) -> None:
        """Print plain text.

        Args:
            text: Text to print.
            **kwargs: Additional arguments passed to Rich console.
        """
        self.console.print(text, **kwargs)

    def print_markdown(self, text: str) -> None:
        """Print markdown text with rendering.

        Args:
            text: Markdown text to render.
        """
        try:
            from rich.markdown import Markdown

            md = Markdown(text)
            self.console.print(md)
        except ImportError:
            # Fallback to plain text
            self.console.print(text)

    def print_code(
        self,
        code: str,
        language: str = "bash",
        theme: str = "monokai",
    ) -> None:
        """Print syntax-highlighted code.

        Args:
            code: Code to highlight.
            language: Programming language for highlighting.
            theme: Color theme name.
        """
        try:
            from rich.syntax import Syntax

            syntax = Syntax(code, language, theme=theme)
            self.console.print(syntax)
        except ImportError:
            # Fallback to plain text
            self.console.print(code)

    def print_panel(
        self,
        content: str,
        title: str | None = None,
        border_style: str = "cyan",
    ) -> None:
        """Print content in a panel.

        Args:
            content: Content to display in panel.
            title: Optional panel title.
            border_style: Border color style.
        """
        try:
            from rich.panel import Panel

            panel = Panel(
                content,
                title=title,
                border_style=border_style,
            )
            self.console.print(panel)
        except ImportError:
            # Fallback
            if title:
                self.console.print(f"[bold]{title}[/bold]")
            self.console.print(content)

    def print_table(
        self,
        data: list[dict[str, Any]],
        columns: list[str],
        title: str | None = None,
    ) -> None:
        """Print data as a table.

        Args:
            data: List of row dictionaries.
            columns: Column names to display.
            title: Optional table title.
        """
        try:
            from rich.table import Table

            table = Table(title=title)
            for col in columns:
                table.add_column(col)

            for row in data:
                table.add_row(*[str(row.get(col, "")) for col in columns])

            self.console.print(table)
        except ImportError:
            # Fallback: print as text
            for row in data:
                self.console.print(" | ".join(str(row.get(col, "")) for col in columns))

    def print_error(self, message: str) -> None:
        """Print error message.

        Args:
            message: Error message text.
        """
        self.console.print(f"[red]Error:[/red] {message}")

    def print_warning(self, message: str) -> None:
        """Print warning message.

        Args:
            message: Warning message text.
        """
        self.console.print(f"[yellow]Warning:[/yellow] {message}")

    def print_success(self, message: str) -> None:
        """Print success message.

        Args:
            message: Success message text.
        """
        self.console.print(f"[green]Success:[/green] {message}")

    def print_info(self, message: str) -> None:
        """Print info message.

        Args:
            message: Info message text.
        """
        self.console.print(f"[cyan]Info:[/cyan] {message}")

    def print_separator(self, char: str = "-", width: int | None = None) -> None:
        """Print a horizontal separator.

        Args:
            char: Character to use for separator.
            width: Width of separator (defaults to terminal width).
        """
        if width is None:
            try:
                width = self.console.width
            except Exception:
                width = 80
        self.console.print(char * width)
