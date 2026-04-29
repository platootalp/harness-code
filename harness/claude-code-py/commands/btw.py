"""Btw command for Claude Code.

Ask a side question without losing context.

TypeScript equivalent: src/commands/btw/
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .base import Availability, BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


# =============================================================================
# Btw Command
# =============================================================================


@dataclass
class BtwCommand(BaseCommand):
    """Ask a quick side question without interrupting the main conversation.

    The /btw command allows asking questions that are related to but separate
    from the current task. The question is answered while preserving the
    main conversation context.

    TypeScript equivalent: src/commands/btw/btw.tsx
    """

    name: str = "btw"
    aliases: list[str] = field(default_factory=list)
    description: str = "Ask a side question without losing context"
    argument_hint: str | None = "<question>"
    command_type: CommandType = CommandType.LOCAL_JSX
    availability: list[str] = field(default_factory=lambda: [Availability.ALL.value])
    immediate: bool = True  # Execute without waiting for stop point
    source: str = "builtin"

    def __post_init__(self) -> None:
        self._all_names: set[str] = {self.name, *self.aliases}

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the btw command."""
        question = args.strip() if args else ""

        if not question:
            return CommandResult(
                type="text",
                value="Usage: /btw <your question>\n\n"
                      "Asks a side question without interrupting the main conversation.",
            )

        # In a full TUI implementation, this would:
        # 1. Spawn a side question fork with the current context
        # 2. Display a loading spinner while waiting for response
        # 3. Show the response with scrollable markdown
        # 4. Allow dismissal with Escape/Enter

        # For text/TUI mode, indicate the question is being processed
        lines = [
            f"/btw {question}",
            "",
            "Side question is being processed...",
            "",
            "In full TUI mode, this would display a spinner and show the response.",
            "",
            "Note: Side questions use a fork of the current context to provide",
            "answers without interrupting your main conversation.",
        ]

        return CommandResult(type="text", value="\n".join(lines))


# =============================================================================
# Registry
# =============================================================================


def get_all_commands() -> list[BaseCommand]:
    """Get all btw-related commands.

    Returns:
        List of btw command instances.
    """
    return [BtwCommand()]


def register_builtin_commands(registry: Any) -> None:
    """Register btw commands with a command registry.

    Args:
        registry: Command registry with a register() method.
    """
    for cmd in get_all_commands():
        registry.register(cmd)
