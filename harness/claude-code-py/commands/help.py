"""Help command for Claude Code.

Displays help information about available commands and their usage.

TypeScript equivalent: src/commands/help/help.tsx, src/commands/help/index.ts
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .base import BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


# Common info arguments (like --version, -v)
COMMON_INFO_ARGS: frozenset[str] = frozenset({"--version", "-v", "--info", "?"})

# Common help arguments
COMMON_HELP_ARGS: frozenset[str] = frozenset({"--help", "-h", "-?"})


@dataclass
class HelpCommand(BaseCommand):
    """Show help and available commands.

    Displays help information for all available commands or a specific command.

    TypeScript equivalent: src/commands/help/help.tsx, src/commands/help/index.ts
    """

    name: str = "help"
    description: str = "Show help and available commands"
    argument_hint: str | None = "[command]"
    command_type: CommandType = CommandType.LOCAL_JSX
    source: str = "builtin"
    _get_all_commands: Any = None  # Set via __init__

    def __init__(
        self,
        get_all_commands: Any = None,
    ) -> None:
        """Initialize the help command.

        Args:
            get_all_commands: Optional callable that returns all available commands.
        """
        super().__init__(name=self.name, description=self.description)
        object.__setattr__(self, "_get_all_commands", get_all_commands)

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the help command."""
        trimmed_args = args.strip()

        if trimmed_args in COMMON_INFO_ARGS:
            return CommandResult(
                type="jsx",
                value=None,
                node={
                    "type": "help",
                    "mode": "info",
                    "context": context,
                },
            )

        if trimmed_args in COMMON_HELP_ARGS:
            return CommandResult(
                type="text",
                value="Run /help to see available commands, or /help <command> for details on a specific command.",
            )

        if trimmed_args:
            return self._help_for_command(trimmed_args)

        return self._help_general(context)

    def _help_for_command(self, cmd_name: str) -> CommandResult:
        """Get help for a specific command.

        Args:
            cmd_name: Name of the command to get help for.

        Returns:
            CommandResult with help text.
        """
        if self._get_all_commands:
            commands = self._get_all_commands()
            for cmd in commands:
                if cmd_name in cmd._all_names:
                    hint = cmd.argument_hint if cmd.argument_hint else ""
                    msg = f"/{cmd.name}"
                    if hint:
                        msg += f" {hint}"
                    msg += f"\n\n{cmd.description}"
                    if cmd.aliases:
                        msg += f"\nAliases: {', '.join('/' + a for a in cmd.aliases)}"
                    return CommandResult(type="text", value=msg)

        return CommandResult(
            type="text",
            value=f"Unknown command: /{cmd_name}",
        )

    def _help_general(self, context: dict[str, Any]) -> CommandResult:
        """Get general help listing all commands.

        Args:
            context: Execution context.

        Returns:
            CommandResult with general help text.
        """
        return CommandResult(
            type="jsx",
            value=None,
            node={
                "type": "help",
                "mode": "list",
                "context": context,
            },
        )
