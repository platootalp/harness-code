"""
Core builtin commands for Claude Code.

Implements the core slash commands:
- ClearCommand: Clear the conversation
- CompactCommand: Trigger context compaction
- HelpCommand: Show help information
- ModelCommand: Show or set the current model
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .base import Availability, BaseCommand, CommandResult

if TYPE_CHECKING:
    from ..cli.state import REPLState


# =============================================================================
# Clear Command
# =============================================================================


@dataclass
class ClearCommand(BaseCommand):
    """Clear the conversation history.

    Clears all messages from the current conversation while preserving
    session settings. Optionally clears command history too.
    """

    name: str = "clear"
    description: str = "Clear the conversation"
    argument_hint: str | None = "(--history)"
    availability: list[str] = field(
        default_factory=lambda: [Availability.ALL.value]
    )
    supports_non_interactive: bool = True

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the clear command."""
        clear_history = "--history" in args

        repl_state: REPLState | None = context.get("_repl_state")
        if repl_state is not None:
            repl_state.messages.clear()
            if clear_history:
                repl_state.command_history.clear()
                repl_state.history_index = -1

        output = "Conversation cleared."
        if clear_history:
            output += " Command history also cleared."
        return CommandResult(type="text", value=output)


# =============================================================================
# Compact Command
# =============================================================================


@dataclass
class CompactCommand(BaseCommand):
    """Trigger context window compaction.

    Initiates a context compaction operation to reduce the number of
    tokens in the conversation context while preserving important content.
    """

    name: str = "compact"
    description: str = "Compress the conversation context"
    availability: list[str] = field(
        default_factory=lambda: [Availability.ALL.value]
    )
    supports_non_interactive: bool = True

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the compact command."""
        repl_state: REPLState | None = context.get("_repl_state")
        if repl_state is not None:
            repl_state.is_compressing = True

        return CommandResult(
            type="text",
            value="Starting context compaction...",
        )


# =============================================================================
# Help Command
# =============================================================================


@dataclass
class HelpCommand(BaseCommand):
    """Show help information.

    Displays help for all available commands or a specific command.
    """

    name: str = "help"
    description: str = "Show this help message"
    argument_hint: str | None = "[command]"
    availability: list[str] = field(
        default_factory=lambda: [Availability.ALL.value]
    )
    supports_non_interactive: bool = True

    def __init__(
        self,
        get_all_commands: Any = None,
    ) -> None:
        super().__init__(
            name="help",
            description="Show this help message",
            argument_hint="[command]",
            availability=[Availability.ALL.value],
            supports_non_interactive=True,
        )
        self._get_all_commands = get_all_commands

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the help command."""
        if args.strip():
            return self._help_for_command(args.strip())
        return self._help_general()

    def _help_for_command(self, cmd_name: str) -> CommandResult:
        """Get help for a specific command."""
        if self._get_all_commands:
            commands = self._get_all_commands()
            for cmd in commands:
                if cmd_name in cmd._all_names:
                    return CommandResult(
                        type="text",
                        value=f"/{cmd.name}: {cmd.description}\n"
                        + (f"Usage: /{cmd.name} {cmd.argument_hint}" if cmd.argument_hint else ""),
                    )
        return CommandResult(
            type="text",
            value=f"Unknown command: /{cmd_name}",
        )

    def _help_general(self) -> CommandResult:
        """Get general help listing all commands."""
        lines = [
            "Available commands:",
            "",
        ]
        if self._get_all_commands:
            commands = self._get_all_commands()
            for cmd in sorted(commands, key=lambda c: c.name):
                if cmd.is_hidden:
                    continue
                line = f"  /{cmd.name}"
                if cmd.argument_hint:
                    line += f" {cmd.argument_hint}"
                line += f" - {cmd.description}"
                lines.append(line)
        else:
            # Fallback when registry not available
            lines.extend([
                "  /clear - Clear the conversation",
                "  /compact - Compress the conversation context",
                "  /help - Show this help message",
                "  /model - Show or set the current model",
            ])
        lines.extend([
            "",
            "Type /help <command> for details on a specific command.",
        ])
        return CommandResult(type="text", value="\n".join(lines))


# =============================================================================
# Model Command
# =============================================================================


@dataclass
class ModelCommand(BaseCommand):
    """Show or set the current model.

    When called without arguments, shows the current model.
    When called with a model name, switches to that model.
    """

    name: str = "model"
    description: str = "Show or change the current model"
    argument_hint: str | None = "[model-name]"
    availability: list[str] = field(
        default_factory=lambda: [Availability.ALL.value]
    )
    supports_non_interactive: bool = True

    # Available models for reference
    AVAILABLE_MODELS = [
        "claude-opus-4-5",
        "claude-sonnet-4-7",
        "claude-haiku-4-3",
    ]

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the model command."""
        model_arg = args.strip()

        repl_state: REPLState | None = context.get("_repl_state")
        current_model = repl_state.session.model if repl_state else "unknown"

        if not model_arg:
            return CommandResult(
                type="text",
                value=f"Current model: {current_model}",
            )

        # Validate model name (basic check)
        if model_arg not in self.AVAILABLE_MODELS:
            return CommandResult(
                type="text",
                value=f"Unknown model: {model_arg}\n"
                + f"Available models: {', '.join(self.AVAILABLE_MODELS)}",
            )

        if repl_state:
            old_model = repl_state.session.model
            repl_state.session.model = model_arg

        return CommandResult(
            type="text",
            value=f"Model changed from {old_model} to {model_arg}",
        )


# =============================================================================
# Registry
# =============================================================================

def get_all_commands() -> list[BaseCommand]:
    """Get all built-in commands.

    Returns:
        List of all core command instances.
    """
    return [
        ClearCommand(),
        CompactCommand(),
        HelpCommand(get_all_commands=get_all_commands),
        ModelCommand(),
    ]


def register_builtin_commands(registry: Any) -> None:
    """Register all built-in commands with a command registry.

    Args:
        registry: Command registry with a register() method.
    """
    for cmd in get_all_commands():
        registry.register(cmd)
