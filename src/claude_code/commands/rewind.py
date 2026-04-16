"""Rewind command for Claude Code.

Rewinds to a previous checkpoint in the conversation.

TypeScript equivalent: src/commands/rewind/rewind.ts
"""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .base import BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


@dataclass
class RewindCommand(BaseCommand):
    """Rewind to a previous checkpoint.

    TypeScript equivalent: src/commands/rewind/rewind.ts
    """

    name: str = "rewind"
    aliases: list[str] = field(default_factory=lambda: ["checkpoint"])
    description: str = "Rewind to a previous checkpoint in the conversation"
    argument_hint: str | None = "[checkpoint-id]"
    command_type: CommandType = CommandType.LOCAL
    source: str = "builtin"
    supports_non_interactive: bool = False

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the rewind command."""
        open_selector = context.get("openMessageSelector")

        if open_selector and callable(open_selector):
            with suppress(Exception):
                open_selector()

        # Return skip type to move past the stop point without appending text
        return CommandResult(type="skip", value=None)
