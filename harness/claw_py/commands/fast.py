"""
Fast mode command for Claude Code.

Toggles fast mode (haiku model only) for increased speed.

TypeScript equivalent: src/commands/fast/fast.tsx
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .base import Availability, BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


@dataclass
class FastCommand(BaseCommand):
    """Toggle fast mode (haiku model only).

    Fast mode uses the haiku model for faster responses at reduced capability.
    Only available for claude-ai and console environments.
    """

    name: str = "fast"
    description: str = "Toggle fast mode (haiku model only)"
    argument_hint: str | None = "[on|off]"
    availability: list[str] = field(
        default_factory=lambda: [Availability.CLAUDE_AI.value, Availability.CONSOLE.value]
    )
    command_type: CommandType = CommandType.LOCAL_JSX
    supports_non_interactive: bool = False

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the fast command."""
        arg = args.strip().lower() if args.strip() else ""

        if arg == "on":
            return CommandResult(
                type="text",
                value="Fast mode ON. Model set to haiku for faster responses.",
            )
        if arg == "off":
            return CommandResult(
                type="text",
                value="Fast mode OFF.",
            )

        # No argument - show the fast mode picker
        return CommandResult(
            type="jsx",
            value=None,
            node={
                "type": "FastModePicker",
                "props": {
                    "onDone": None,  # Set by TUI layer
                    "unavailableReason": None,  # Set by TUI layer
                },
            },
        )
