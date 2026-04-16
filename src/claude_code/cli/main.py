"""
Claude Code CLI - Main entry point.

TypeScript equivalent: src/main.tsx

This module provides the Click-based CLI interface supporting:
- Interactive TUI mode (default)
- Headless print mode (--print)
- SDK mode for programmatic access
"""

from __future__ import annotations

import asyncio
import sys
from typing import TYPE_CHECKING, Any

import click

__version__ = "1.0.0"

if TYPE_CHECKING:
    pass


@click.group(invoke_without_command=True)
@click.version_option(version=__version__)
@click.argument("prompt", required=False)
@click.option(
    "-p",
    "--print",
    "headless",
    is_flag=True,
    help="Print response and exit (headless mode)",
)
@click.option("-d", "--debug", "debug_filter", is_flag=True, help="Enable debug mode")
@click.option(
    "--output-format",
    type=click.Choice(["text", "json", "stream-json"]),
    default="text",
    help="Output format for headless mode",
)
@click.option("--model", help="Model for the session")
@click.option(
    "--permission-mode",
    type=click.Choice(["auto", "bypassPermissions", "deny"]),
    default="auto",
    help="Permission mode for tool execution",
)
@click.option(
    "-c",
    "--continue",
    "continue_session",
    is_flag=True,
    help="Continue most recent conversation",
)
@click.option("-r", "--resume", "resume_id", help="Resume by session ID or open picker")
@click.option("--system-prompt", help="System prompt for session")
@click.option(
    "--mcp-config",
    multiple=True,
    help="Load MCP servers from JSON files",
)
@click.option("--session-id", help="Specify session ID")
@click.option(
    "--input-format",
    type=click.Choice(["text", "stream-json"]),
    default="text",
    help="Input format",
)
@click.pass_context
def cli(
    ctx: click.Context,
    prompt: str | None,
    headless: bool,
    debug_filter: bool,
    output_format: str,
    model: str | None,
    permission_mode: str | None,
    continue_session: bool,
    resume_id: str | None,
    system_prompt: str | None,
    mcp_config: tuple[str, ...],
    session_id: str | None,
    input_format: str,
) -> None:
    """Claude Code - AI-powered coding assistant.

    Run without arguments to start the interactive TUI.
    Provide a prompt as an argument for single-query headless mode.
    """
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

    if headless:
        # Headless mode - run single prompt and exit
        if not prompt:
            click.echo("Error: --print mode requires a prompt argument.", err=True)
            ctx.exit(1)
        asyncio.run(headless_ask(ctx.obj, prompt))
    elif prompt:
        # Interactive mode with initial prompt
        asyncio.run(interactive_with_prompt(ctx.obj, prompt))
    else:
        # Full interactive TUI mode
        # app.run() is sync and creates its own event loop - don't wrap in asyncio.run()
        run_tui_sync(ctx.obj)


@cli.command("ask")
@click.argument("prompt")
@click.pass_context
def ask(ctx: click.Context, prompt: str) -> None:
    """Send a prompt to Claude and print the response.

    Shorthand for running Claude Code with a single prompt in headless mode.
    """
    opts: dict[str, Any] = dict(ctx.parent.obj) if ctx.parent and ctx.parent.obj else {}
    opts["prompt"] = prompt
    _run_async(headless_ask(opts, prompt))


async def headless_ask(opts: dict[str, Any], prompt: str) -> None:
    """Run a single prompt in headless mode.

    Args:
        opts: CLI options from context.
        prompt: User prompt to send.
    """
    from ..engine.engine import QueryEngine
    from ..services.api.claude import create_client

    # Create API client
    try:
        api_client = create_client()
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    # Load MCP servers if configured
    mcp_configs = opts.get("mcp_config", [])
    if mcp_configs:
        await _load_mcp_servers(mcp_configs)

    engine = QueryEngine(
        api_client=api_client,
        model=opts.get("model") or "claude-sonnet-4-20250514",
    )

    # Build messages
    messages = _build_messages(prompt, opts.get("system_prompt"))

    # Stream response
    output_handler = _create_output_handler(opts.get("output_format", "text"))

    try:
        async for event in engine.submit_message(
            prompt=prompt,
            messages=messages,
            system=opts.get("system_prompt"),
        ):
            output_handler.handle_event(event)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


async def interactive_with_prompt(opts: dict[str, Any], prompt: str) -> None:
    """Start TUI with an initial prompt.

    Args:
        opts: CLI options from context.
        prompt: Initial prompt to send.
    """
    # For now, fall back to headless mode
    # Full implementation would pre-populate messages
    await headless_ask(opts, prompt)


async def run_tui(opts: dict[str, Any]) -> None:
    """Start the full Textual TUI application.

    Args:
        opts: CLI options from context.
    """
    try:
        from .app import ClaudeCodeApp
    except ImportError as e:
        click.echo(f"Error: Could not load TUI: {e}", err=True)
        click.echo("Falling back to headless mode...")
        return

    app = ClaudeCodeApp(
        model=opts.get("model"),
        permission_mode=opts.get("permission_mode", "auto"),
        debug=opts.get("debug", False),
    )

    try:
        # Use async_run for async context, run for sync context
        if hasattr(app, 'async_run'):
            await app.async_run()
        else:
            app.run()
    except Exception as e:
        click.echo(f"TUI Error: {e}", err=True)
        sys.exit(1)


async def _load_mcp_servers(configs: list[str]) -> None:
    """Load MCP servers from config files.

    Args:
        configs: List of MCP config file paths.
    """
    # MCP client loading would be implemented here
    pass


def _build_messages(
    prompt: str,
    system_prompt: str | None = None,
) -> list[Any]:
    """Build message list for API call.

    Args:
        prompt: User prompt.
        system_prompt: Optional system prompt.

    Returns:
        List of Message objects.
    """
    import uuid

    from ..models.message import ContentBlock, Message, Role

    messages: list[Any] = []
    if system_prompt:
        messages.append(Message(
            id=str(uuid.uuid4()),
            role=Role.SYSTEM,
            content_blocks=[ContentBlock(text=system_prompt)],
        ))
    messages.append(Message(
        id=str(uuid.uuid4()),
        role=Role.USER,
        content_blocks=[ContentBlock(text=prompt)],
    ))
    return messages


def _create_output_handler(format_type: str) -> Any:
    """Create output handler for the given format type.

    Args:
        format_type: Output format (text, json, stream-json).

    Returns:
        OutputHandler instance.
    """
    from .output import OutputHandler

    return OutputHandler(format_type=format_type)


def main() -> None:
    """Main entry point."""
    cli(obj={})


def _run_async(coro: Any) -> None:
    """Run an async coroutine, handling existing event loops.

    Args:
        coro: The coroutine to run.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop, safe to use asyncio.run()
        asyncio.run(coro)
    else:
        # Already in an event loop - use run_until_complete
        loop.run_until_complete(coro)


def run_tui_sync(opts: dict[str, Any]) -> None:
    """Start the Textual TUI in a synchronous context.

    App.run() creates its own event loop, so we call it directly
    without wrapping in asyncio.run().

    Args:
        opts: CLI options from context.
    """
    try:
        from .app import ClaudeCodeApp
    except ImportError as e:
        click.echo(f"Error: Could not load TUI: {e}", err=True)
        click.echo("Falling back to headless mode...")
        return

    app = ClaudeCodeApp(
        model=opts.get("model"),
        permission_mode=opts.get("permission_mode", "auto"),
        debug=opts.get("debug", False),
    )

    try:
        app.run()
    except Exception as e:
        click.echo(f"TUI Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
