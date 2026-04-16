# Phase 4: CLI/REPL 设计

> 日期：2026-04-05
> 状态：设计阶段
> 对应 TypeScript：`src/main.tsx`, `src/screens/REPL.tsx`, `src/cli/print.ts`, `src/ink.ts`

---

## 1. CLI/REPL 架构

### 1.1 技术选择

| 组件 | TypeScript | Python | 理由 |
|------|------------|--------|------|
| CLI 解析 | Commander.js | Click/Typer | 标准 CLI 框架 |
| TUI 框架 | Ink (React-like) | Textual | 类似 React 组件模型 |
| 输出格式化 | chalk + 自定义 | Rich | 终端彩色输出 |
| 输入处理 | raw stdin | textual 输入 | 内置支持 |

### 1.2 核心组件

```
CLI/REPL System
├── main.py (入口)
│   ├── CLI 参数解析 (Click)
│   └── 模式分发 (interactive/print/sdk)
├── cli/
│   ├── app.py (Textual App)
│   ├── repl.py (REPL Screen)
│   ├── output.py (OutputHandler)
│   └── style.py (Styling)
└── models/
    └── repl_state.py
```

---

## 2. CLI 入口设计

### 2.1 main.py

对应 TypeScript：`src/main.tsx`

```python
"""Claude Code CLI - Main entry point."""
from __future__ import annotations
import sys
import asyncio
from typing import Optional

import click

__version__ = "0.1.0"


@click.group(invoke_without_command=True)
@click.version_option(version=__version__)
@click.argument("prompt", required=False)
@click.option("-p", "--print", "headless", is_flag=True, help="Print response and exit (headless mode)")
@click.option("-d", "--debug", "debug_filter", is_flag=False, help="Enable debug mode")
@click.option("--output-format", type=click.Choice(["text", "json", "stream-json"]), default="text")
@click.option("--model", help="Model for the session")
@click.option("--permission-mode", type=click.Choice(["auto", "bypassPermissions", "deny"]))
@click.option("-c", "--continue", "continue_session", is_flag=True, help="Continue most recent conversation")
@click.option("-r", "--resume", "resume_id", help="Resume by session ID or open picker")
@click.option("--system-prompt", help="System prompt for session")
@click.option("--mcp-config", multiple=True, help="Load MCP servers from JSON files")
@click.option("--session-id", help="Specify session ID")
@click.option("--input-format", type=click.Choice(["text", "stream-json"]), default="text")
@click.pass_context
def cli(
    ctx: click.Context,
    prompt: Optional[str],
    headless: bool,
    debug_filter: str | bool,
    output_format: str,
    model: Optional[str],
    permission_mode: Optional[str],
    continue_session: bool,
    resume_id: Optional[str],
    system_prompt: Optional[str],
    mcp_config: tuple[str, ...],
    session_id: Optional[str],
    input_format: str,
) -> None:
    """Claude Code - AI-powered coding assistant."""
    # Store options in context for subcommands
    ctx.ensure_object(dict)
    ctx.obj["headless"] = headless
    ctx.obj["output_format"] = output_format
    ctx.obj["debug"] = debug_filter
    ctx.obj["model"] = model
    ctx.obj["permission_mode"] = permission_mode
    ctx.obj["continue_session"] = continue_session
    ctx.obj["resume_id"] = resume_id
    ctx.obj["system_prompt"] = system_prompt
    ctx.obj["mcp_config"] = list(mcp_config)
    ctx.obj["session_id"] = session_id
    ctx.obj["input_format"] = input_format
    ctx.obj["prompt"] = prompt


@cli.command()
@click.argument("prompt")
@click.pass_context
def ask(ctx: click.Context, prompt: str) -> None:
    """Send a prompt to Claude and print the response."""
    # Headless execution
    asyncio.run(headless_ask(ctx.obj, prompt))


async def headless_ask(opts: dict, prompt: str) -> None:
    """Run a single prompt in headless mode."""
    from .cli.output import OutputHandler
    from .engine.engine import QueryEngine
    from .services.api.claude import ClaudeAIClient
    from .engine.tools.registry import ToolRegistry
    from .engine.context import ContextManager

    # Initialize components
    api_client = ClaudeAIClient(model=opts.get("model"))
    tool_registry = ToolRegistry()
    context_manager = ContextManager()

    # TODO: Register tools, load MCP configs

    engine = QueryEngine(
        api_client=api_client,
        tool_registry=tool_registry,
        context_manager=context_manager,
    )

    output_handler = OutputHandler()

    # Stream response
    async for event in engine.submit_message(prompt, []):
        output_handler.handle_event(event)


@cli.command()
@click.pass_context
def remote_control(ctx: click.Context) -> None:
    """Start remote control server mode."""
    # TODO: Implement remote control daemon
    click.echo("Remote control mode not yet implemented")


def main() -> None:
    """Main entry point."""
    cli(obj={})


if __name__ == "__main__":
    main()
```

---

## 3. Textual TUI 应用

### 3.1 ClaudeCodeApp

对应 TypeScript：`src/screens/REPL.tsx`

```python
"""Claude Code Textual TUI application."""
from __future__ import annotations
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Log, Input, Static
from textual.binding import Binding
from textual.containers import Container, VerticalScroll
from textual.events import Mount
from typing import Any

from .repl import REPLScreen
from .output import OutputHandler


class ClaudeCodeApp(App):
    """Main Claude Code TUI application.

    TypeScript equivalent: src/screens/REPL.tsx

    Features:
    - Full-screen REPL interface
    - Message history with virtualization
    - Multi-line input support
    - Command mode (slash commands)
    - Vim keybindings
    - Streaming output
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

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self._history: list[str] = []
        self._history_index: int = -1
        self._output_handler = OutputHandler()
        self._is_streaming: bool = False

        # State from options
        self._model = kwargs.get("model", "claude-opus-4-6")
        self._permission_mode = kwargs.get("permission_mode", "auto")

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()

        with VerticalScroll(id="output"):
            yield Log(id="message-log", auto_scroll=True)

        with Container(id="input-area"):
            yield Input(
                id="input",
                placeholder="Enter message to Claude...",
                multiline=True,
            )

        yield Static(id="status", renderable="Ready")

        yield Footer()

    def on_mount(self) -> None:
        """Called when app is mounted."""
        input_widget = self.query_one("#input", Input)
        input_widget.focus()

        # Show welcome message
        log = self.query_one("#message-log", Log)
        log.write_line("Claude Code v0.1.0")
        log.write_line("Type /help for available commands")
        log.write_line("")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        prompt = event.value
        if not prompt.strip():
            return

        # Add to history
        self._history.append(prompt)
        self._history_index = len(self._history)

        # Clear input
        input_widget = self.query_one("#input", Input)
        input_widget.value = ""

        # Echo user message
        log = self.query_one("#message-log", Log)
        log.write_line(f"\n[user] {prompt}\n")

        # Update status
        self._set_status("Thinking...")

        # Process the prompt
        if prompt.startswith("/"):
            await self._handle_command(prompt)
        else:
            await self._handle_message(prompt)

    async def _handle_command(self, command: str) -> None:
        """Handle a slash command."""
        from ..commands.registry import CommandRegistry

        # Parse command
        parts = command[1:].split(maxsplit=1)
        cmd_name = parts[0]
        args = parts[1] if len(parts) > 1 else ""

        # Get registry and execute
        registry = CommandRegistry()  # TODO: Get from app state
        result = await registry.execute(cmd_name, args, {})

        # Output result
        log = self.query_one("#message-log", Log)
        if result.type == "text" and result.value:
            log.write_line(f"\n{result.value}\n")
        elif result.type == "jsx":
            # TODO: Render JSX component
            pass

        self._set_status("Ready")

    async def _handle_message(self, message: str) -> None:
        """Handle a user message through the query engine."""
        from ..engine.engine import QueryEngine
        from ..services.api.claude import ClaudeAIClient
        from ..engine.tools.registry import ToolRegistry
        from ..engine.context import ContextManager

        # TODO: Get these from app state
        api_client = ClaudeAIClient(model=self._model)
        tool_registry = ToolRegistry()
        context_manager = ContextManager()

        engine = QueryEngine(
            api_client=api_client,
            tool_registry=tool_registry,
            context_manager=context_manager,
        )

        self._is_streaming = True

        try:
            # Stream response
            async for event in engine.submit_message(message, []):
                self._handle_stream_event(event)

        except Exception as e:
            log = self.query_one("#message-log", Log)
            log.write_line(f"\n[error] {str(e)}\n")

        finally:
            self._is_streaming = False
            self._set_status("Ready")

    def _handle_stream_event(self, event: Any) -> None:
        """Handle a stream event from the query engine."""
        from ..models.events import (
            ThinkingEvent,
            ToolUseEvent,
            ToolResultEvent,
            MessageStartEvent,
            ContentBlockDeltaEvent,
            MessageStopEvent,
        )

        log = self.query_one("#message-log", Log)

        if isinstance(event, ThinkingEvent):
            # Show thinking indicator
            self._set_status("Thinking...")

        elif isinstance(event, ToolUseEvent):
            # Show tool use
            log.write_line(f"\n[tool] Using {event.name}...")

        elif isinstance(event, ToolResultEvent):
            # Show tool result
            log.write_line(f"[result] {event.content[:200]}...")
            if event.is_error:
                log.write_line("[error] Tool execution failed")

        elif isinstance(event, ContentBlockDeltaEvent):
            # Streaming text output
            if event.delta.get("type") == "text_delta":
                text = event.delta.get("text", "")
                log.write_line(text, shrink=True)

        elif isinstance(event, MessageStopEvent):
            log.write_line("\n")

    def _set_status(self, status: str) -> None:
        """Update status bar."""
        status_widget = self.query_one("#status", Static)
        status_widget.update(status)

    # Key bindings

    def action_toggle_transcript(self) -> None:
        """Toggle transcript mode (read-only history)."""
        # TODO: Implement transcript mode
        pass

    def action_interrupt(self) -> None:
        """Interrupt current operation."""
        if self._is_streaming:
            # TODO: Send interrupt signal to engine
            self._is_streaming = False
            self._set_status("Interrupted")

    def action_suspend(self) -> None:
        """Suspend the application."""
        self.suspend()

    def action_enter_normal_mode(self) -> None:
        """Enter normal mode (vim)."""
        input_widget = self.query_one("#input", Input)
        input_widget.remove_class("cursor-blink")

    def action_enter_insert_mode(self) -> None:
        """Enter insert mode (vim)."""
        input_widget = self.query_one("#input", Input)
        input_widget.add_class("cursor-blink")

    def action_history_prev(self) -> None:
        """Navigate to previous history item."""
        if not self._history:
            return
        if self._history_index > 0:
            self._history_index -= 1
        input_widget = self.query_one("#input", Input)
        input_widget.value = self._history[self._history_index]

    def action_history_next(self) -> None:
        """Navigate to next history item."""
        if not self._history:
            return
        if self._history_index < len(self._history) - 1:
            self._history_index += 1
        input_widget = self.query_one("#input", Input)
        input_widget.value = self._history[self._history_index]
        input_widget.focus()

    def action_clear_output(self) -> None:
        """Clear output log."""
        log = self.query_one("#message-log", Log)
        log.clear()

    def action_toggle_help(self) -> None:
        """Toggle help panel."""
        # TODO: Show/hide help
        pass
```

---

## 4. 输出处理

### 4.1 OutputHandler

对应 TypeScript：`src/cli/print.ts`

```python
"""Output handling and formatting."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Literal
from rich.console import Console
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.panel import Panel
from rich.table import Table

from ..models.events import (
    StreamEvent,
    ThinkingEvent,
    ToolUseEvent,
    ToolResultEvent,
    MessageStartEvent,
    ContentBlockStartEvent,
    ContentBlockDeltaEvent,
    MessageDeltaEvent,
    MessageStopEvent,
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
    """

    def __init__(self, console: Console | None = None):
        self.console = console or Console()
        self._streaming_text: str = ""

    def handle_event(self, event: StreamEvent) -> None:
        """Handle a stream event and render it."""
        if isinstance(event, ThinkingEvent):
            self._render_thinking(event.thinking)

        elif isinstance(event, ToolUseEvent):
            self._render_tool_use(event.name, event.input)

        elif isinstance(event, ToolResultEvent):
            self._render_tool_result(event.content, event.is_error)

        elif isinstance(event, ContentBlockDeltaEvent):
            self._render_content_delta(event.delta)

        elif isinstance(event, MessageDeltaEvent):
            self._render_message_delta(event.delta)

        elif isinstance(event, MessageStopEvent):
            self._finalize_streaming()

    def _render_thinking(self, thinking: str) -> None:
        """Render thinking/throttling content."""
        if thinking:
            self.console.print("[dim]Thinking...[/dim]")

    def _render_tool_use(self, tool_name: str, input_args: dict[str, Any]) -> None:
        """Render tool use block."""
        self.console.print(f"\n[cyan]Using tool:[/cyan] [bold]{tool_name}[/bold]")
        if input_args:
            args_str = ", ".join(f"{k}={v}" for k, v in list(input_args.items())[:3])
            self.console.print(f"[dim]{args_str}[/dim]")

    def _render_tool_result(self, result: str, is_error: bool = False) -> None:
        """Render tool result."""
        style = "red" if is_error else "green"
        prefix = "Error" if is_error else "Result"
        self.console.print(f"\n[{style}]{prefix}:[/{style}]")
        self.console.print(result[:1000] + "..." if len(result) > 1000 else result)

    def _render_content_delta(self, delta: dict[str, Any]) -> None:
        """Render content block delta (streaming text)."""
        if delta.get("type") == "text_delta":
            text = delta.get("text", "")
            self._streaming_text += text
            self.console.print(text, end="")

    def _render_message_delta(self, delta: dict[str, Any]) -> None:
        """Render message delta."""
        if delta.get("type") == "text_delta":
            text = delta.get("text", "")
            self._streaming_text += text
            self.console.print(text, end="")

    def _finalize_streaming(self) -> None:
        """Finalize streaming output."""
        if self._streaming_text:
            self.console.print()  # Newline
        self._streaming_text = ""

    def print_text(self, text: str, **kwargs: Any) -> None:
        """Print plain text."""
        self.console.print(text, **kwargs)

    def print_markdown(self, text: str) -> None:
        """Print markdown text with rendering."""
        md = Markdown(text)
        self.console.print(md)

    def print_code(self, code: str, language: str = "bash") -> None:
        """Print syntax-highlighted code."""
        syntax = Syntax(code, language, theme="monokai")
        self.console.print(syntax)

    def print_panel(self, content: str, title: str | None = None) -> None:
        """Print content in a panel."""
        panel = Panel(content, title=title)
        self.console.print(panel)

    def print_table(self, data: list[dict[str, Any]], columns: list[str]) -> None:
        """Print data as a table."""
        table = Table(*columns)
        for row in data:
            table.add_row(*[str(row.get(col, "")) for col in columns])
        self.console.print(table)

    def print_error(self, message: str) -> None:
        """Print error message."""
        self.console.print(f"[red]Error:[/red] {message}")

    def print_warning(self, message: str) -> None:
        """Print warning message."""
        self.console.print(f"[yellow]Warning:[/yellow] {message}")

    def print_success(self, message: str) -> None:
        """Print success message."""
        self.console.print(f"[green]Success:[/green] {message}")
```

---

## 5. 会话状态管理

### 5.1 REPLState

对应 TypeScript：`src/state/AppStateStore.ts`

```python
"""REPL state management."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from enum import Enum

from ..models.message import Message


class PromptInputMode(str, Enum):
    """Input mode for the prompt."""
    PROMPT = "prompt"      # Normal input
    EDIT = "edit"          # Editing mode
    VIM_NORMAL = "vim_normal"
    VIM_INSERT = "vim_insert"


@dataclass
class REPLState:
    """State for the REPL application.

    TypeScript equivalent: AppState in src/state/AppStateStore.ts
    """
    # Session
    session_id: str | None = None

    # Messages
    messages: list[Message] = field(default_factory=list)

    # Input state
    input_mode: PromptInputMode = PromptInputMode.PROMPT
    cursor_offset: int = 0

    # Streaming state
    is_streaming: bool = False
    is_compressing: bool = False

    # Model
    model: str = "claude-opus-4-6"
    permission_mode: str = "auto"

    # MCP
    mcp_servers: dict[str, Any] = field(default_factory=dict)

    # Tasks
    tasks: dict[str, Any] = field(default_factory=dict)

    # Bridge
    bridge_connected: bool = False
    bridge_reconnecting: bool = False

    # Team
    team_context: dict[str, Any] | None = None


# Global state
_repl_state = REPLState()


def get_repl_state() -> REPLState:
    return _repl_state


def update_repl_state(updater: callable) -> None:
    """Update REPL state."""
    updater(_repl_state)
```

---

## 6. 实施任务清单

### Phase 4.1: CLI 入口
- [ ] 实现 `main.py` - Click CLI
- [ ] 实现 `--print` 头内模式
- [ ] 实现 `--resume` 会话恢复
- [ ] 实现 `--model` 模型选择
- [ ] 实现 `--mcp-config` MCP 配置

### Phase 4.2: Textual TUI
- [ ] 实现 `cli/app.py` - ClaudeCodeApp
- [ ] 实现消息显示
- [ ] 实现输入处理
- [ ] 实现命令处理
- [ ] 实现流式输出
- [ ] 实现键盘绑定

### Phase 4.3: 输出处理
- [ ] 实现 `cli/output.py` - OutputHandler
- [ ] 实现 markdown 渲染
- [ ] 实现代码高亮
- [ ] 实现表格/面板
- [ ] 实现流式文本

### Phase 4.4: 状态管理
- [ ] 实现 `cli/state.py` - REPLState
- [ ] 实现消息历史
- [ ] 实现输入模式
- [ ] 实现任务跟踪

### Phase 4.5: 交互功能
- [ ] 实现历史导航
- [ ] 实现 Vim 模式
- [ ] 实现中断处理
- [ ] 实现挂起/恢复
