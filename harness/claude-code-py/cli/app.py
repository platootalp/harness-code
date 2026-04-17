"""
Claude Code Textual TUI application.

TypeScript equivalent: src/screens/REPL.tsx

A full-screen REPL interface with:
- Message history with virtualization
- Multi-line input support
- Command mode (slash commands)
- Vim keybindings
- Streaming output
- Status bar
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from ..engine.engine import QueryEngine

from textual.app import App
from textual.binding import Binding
from textual.containers import Container, VerticalScroll
from textual.widgets import Footer, Header, Input, Log, Static

from .output import OutputHandler
from .state import (
    PermissionMode,
    PromptInputMode,
    add_message,
    add_to_history,
    get_repl_state,
    history_next,
    history_previous,
    set_input_mode,
    set_streaming,
)


class ClaudeCodeApp(App):
    """Main Claude Code TUI application.

    Features:
    - Full-screen REPL interface
    - Message history with scrolling
    - Multi-line input support
    - Command mode (slash commands)
    - Vim keybindings
    - Streaming output
    - Status bar

    TypeScript equivalent: src/screens/REPL.tsx
    """

    CSS = """
    Screen {
        background: $surface;
    }

    #output {
        height: 1fr;
        padding: 0 1;
    }

    #input-area {
        height: auto;
        min-height: 3;
        max-height: 10;
        border: solid $primary;
        padding: 0 1;
    }

    #input {
        height: 100%;
        border: none;
    }

    #status {
        height: 1;
        background: $accent;
        color: $text;
        padding: 0 1;
    }

    .message {
        padding: 0 0;
    }

    .message-user {
        color: $accent;
        text-style: bold;
    }

    .message-assistant {
        color: $text;
    }

    .message-tool {
        color: $secondary;
    }

    .tool-use {
        background: $surface-darken-1;
        border: solid $primary;
        padding: 0 1;
    }

    Thinking {
        color: $text-muted;
        text-style: italic;
    }
    """

    BINDINGS = [
        # Navigation
        Binding("ctrl+o", "toggle_transcript", "Transcript", show=True),
        Binding("ctrl+c", "interrupt", "Interrupt", show=True),
        Binding("ctrl+z", "suspend", "Suspend", show=True),

        # Input modes
        Binding("escape", "enter_normal_mode", "Normal", show=False),
        Binding("i", "enter_insert_mode", "Insert", show=False),

        # History navigation
        Binding("up", "history_prev", "History", show=False),
        Binding("down", "history_next", "History", show=False),

        # Custom
        Binding("ctrl+l", "clear_output", "Clear", show=False),
        Binding("ctrl+x", "toggle_help", "Help", show=False),
    ]

    def __init__(
        self,
        model: str | None = None,
        permission_mode: str = "auto",
        debug: bool = False,
        **kwargs: Any,
    ) -> None:
        """Initialize the application.

        Args:
            model: AI model to use.
            permission_mode: Permission mode (auto, bypassPermissions, deny).
            debug: Enable debug mode.
            **kwargs: Additional arguments for Textual App.
        """
        super().__init__(**kwargs)
        self._model = model or "claude-sonnet-4-20250514"
        self._permission_mode = permission_mode
        self._debug = debug
        self._output_handler = OutputHandler()
        self._is_streaming = False
        self._state = get_repl_state()
        self._state.debug_enabled = debug
        self._state.permission_mode = PermissionMode(permission_mode)

        # History
        self._history_index = -1

        # Engine reference (set when initialized)
        self._engine: QueryEngine | None = None

    def compose(self) -> ComposeResult:
        """Create child widgets.

        Yields:
            Widgets to compose the UI.
        """
        yield Header()

        with VerticalScroll(id="output"):
            yield Log(id="message-log", auto_scroll=True)

        with Container(id="input-area"):
            yield Input(
                id="input",
                placeholder="Enter message to Claude...",
            )

        yield Static("Ready", id="status")

        yield Footer()

    def on_mount(self) -> None:
        """Called when app is mounted."""
        input_widget = self.query_one("#input", Input)
        input_widget.focus()

        # Show welcome message
        log = self.query_one("#message-log", Log)
        log.write_line("Claude Code v1.0.0")
        log.write_line("Type /help for available commands")
        log.write_line("")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission.

        Args:
            event: Input submitted event.
        """
        prompt = event.value
        if not prompt.strip():
            return

        # Add to history
        add_to_history(prompt)
        self._history_index = len(self._state.command_history)

        # Clear input
        input_widget = self.query_one("#input", Input)
        input_widget.value = ""

        # Echo user message
        log = self.query_one("#message-log", Log)
        log.write_line("")
        log.write_line(f"[bold cyan]> {prompt}[/bold cyan]")
        log.write_line("")

        # Update status
        self._set_status("Thinking...")

        # Process the prompt
        if prompt.startswith("/"):
            await self._handle_command(prompt)
        else:
            await self._handle_message(prompt)

    async def _handle_command(self, command: str) -> None:
        """Handle a slash command.

        Args:
            command: Command string starting with /.
        """
        from ..commands.base import BaseCommand
        from ..commands.registry import get_builtin_registry

        # Parse command
        parts = command[1:].split(maxsplit=1)
        cmd_name = parts[0]
        args = parts[1] if len(parts) > 1 else ""

        # Get builtin registry
        registry = get_builtin_registry()
        cmd: BaseCommand | None = registry.get(cmd_name)

        # Output result
        log = self.query_one("#message-log", Log)

        if cmd is None:
            log.write_line(f"[red]Unknown command: /{cmd_name}[/red]")
            self._set_status("Ready")
            return

        # Execute command
        context: dict[str, Any] = {
            "model": self._model,
            "permission_mode": self._permission_mode,
        }
        result = await cmd.execute(args, context)

        if result.type == "text" and result.value:
            log.write_line("")
            log.write_line(result.value)
            log.write_line("")
        elif result.type == "jsx":
            # JSX commands would render a component
            log.write_line("[dim](JSX command not fully implemented)[/dim]")
        elif result.type == "content":
            # Prompt commands add content to the conversation
            await self._handle_message(args or command)

        self._set_status("Ready")

    async def _handle_message(self, message: str) -> None:
        """Handle a user message through the query engine.

        Args:
            message: User message to process.
        """
        import uuid

        from ..engine.engine import QueryEngine
        from ..models.message import ContentBlock, Message, Role
        from ..services.api.claude import create_client

        # Create engine lazily (to avoid circular imports)
        if self._engine is None:
            api_client = create_client()  # Reads API key from env var
            self._engine = QueryEngine(
                api_client=api_client,
                model=self._model,
            )

        # Add user message
        user_message = Message(
            id=str(uuid.uuid4()),
            role=Role.USER,
            content_blocks=[ContentBlock(text=message)],
        )
        add_message(user_message)

        # Get existing messages
        messages: list[Message] = list(self._state.messages)

        self._is_streaming = True
        set_streaming(True)

        log = self.query_one("#message-log", Log)

        engine = self._engine
        try:
            # Stream response
            async for event in engine.submit_message(
                prompt=message,
                messages=messages,
            ):
                await self._handle_stream_event(event)

        except Exception as e:
            log.write_line("")
            log.write_line(f"[red]Error:[/red] {e}")

        finally:
            self._is_streaming = False
            set_streaming(False)
            self._set_status("Ready")

    async def _handle_stream_event(self, event: Any) -> None:
        """Handle a stream event from the query engine.

        Args:
            event: Stream event to handle.
        """
        from ..models.events import (
            ContentBlockDeltaEvent,
            MessageDeltaEvent,
            MessageStopEvent,
            ThinkingEvent,
            ToolResultEvent,
            ToolUseEvent,
        )

        log = self.query_one("#message-log", Log)

        if isinstance(event, ThinkingEvent):
            self._set_status("Thinking...")

        elif isinstance(event, ToolUseEvent):
            log.write_line("")
            log.write_line(
                f"[cyan]Using tool:[/cyan] [bold]{event.tool_name}[/bold]"
            )

        elif isinstance(event, ToolResultEvent):
            content = event.content or ""
            if len(content) > 2000:
                content = content[:2000] + "\n[dim](truncated)[/dim]"
            style = "red" if event.is_error else "green"
            prefix = "Error" if event.is_error else "Result"
            log.write_line(f"\n[{style}]{prefix}:[/{style}]")
            log.write_line(content)

        elif isinstance(event, (ContentBlockDeltaEvent, MessageDeltaEvent)):
            delta = event.delta
            if isinstance(delta, dict) and delta.get("type") == "text_delta":
                log.write(delta.get("text", ""))

        elif isinstance(event, MessageStopEvent):
            log.write_line("")

        # Delegate to output handler for structured events
        self._output_handler.handle_event(event)

    def _set_status(self, status: str) -> None:
        """Update status bar.

        Args:
            status: Status text to display.
        """
        status_widget = self.query_one("#status", Static)
        status_widget.update(status)

    # =========================================================================
    # Key bindings
    # =========================================================================

    def action_toggle_transcript(self) -> None:
        """Toggle transcript mode (read-only history)."""
        # TODO: Implement transcript mode
        pass

    def action_interrupt(self) -> None:
        """Interrupt current operation."""
        if self._is_streaming:
            self._is_streaming = False
            set_streaming(False)
            self._set_status("Interrupted")
            log = self.query_one("#message-log", Log)
            log.write_line("")
            log.write_line("[yellow]Interrupted[/yellow]")

    def action_suspend(self) -> None:
        """Suspend the application."""
        self.suspend()

    def action_enter_normal_mode(self) -> None:
        """Enter normal mode (vim)."""
        set_input_mode(PromptInputMode.VIM_NORMAL)
        input_widget = self.query_one("#input", Input)
        input_widget.remove_class("cursor-blink")

    def action_enter_insert_mode(self) -> None:
        """Enter insert mode (vim)."""
        set_input_mode(PromptInputMode.VIM_INSERT)
        input_widget = self.query_one("#input", Input)
        input_widget.add_class("cursor-blink")
        input_widget.focus()

    def action_history_prev(self) -> None:
        """Navigate to previous history item."""
        prev = history_previous()
        if prev is not None:
            input_widget = self.query_one("#input", Input)
            input_widget.value = prev

    def action_history_next(self) -> None:
        """Navigate to next history item."""
        next_cmd = history_next()
        if next_cmd is not None:
            input_widget = self.query_one("#input", Input)
            input_widget.value = next_cmd

    def action_clear_output(self) -> None:
        """Clear output log."""
        log = self.query_one("#message-log", Log)
        log.clear()

    def action_toggle_help(self) -> None:
        """Toggle help panel."""
        # TODO: Show/hide help
        log = self.query_one("#message-log", Log)
        log.write_line("")
        log.write_line("[bold]Claude Code Help[/bold]")
        log.write_line("")
        log.write_line("Ctrl+C: Interrupt current operation")
        log.write_line("Ctrl+L: Clear output")
        log.write_line("Ctrl+O: Toggle transcript")
        log.write_line("Ctrl+Z: Suspend (background)")
        log.write_line("Up/Down: Navigate command history")
        log.write_line("")
