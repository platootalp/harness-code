"""
Passes command for Claude Code.

Show guest passes.

TypeScript equivalent: src/commands/passes/passes.tsx
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .base import Availability, BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


@dataclass
class PassesCommand(BaseCommand):
    """Show guest passes.

    Displays information about available guest passes for
    trying Claude Code without a subscription.
    """

    name: str = "passes"
    description: str = "Show guest passes"
    availability: list[str] = field(
        default_factory=lambda: [Availability.ALL.value]
    )
    command_type: CommandType = CommandType.LOCAL_JSX
    supports_non_interactive: bool = False

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the passes command.

        Returns a node dict for TUI rendering of the passes component.
        """
        return CommandResult(
            type="jsx",
            value=None,
            node={
                "type": "Passes",
                "props": {
                    "onDone": None,  # Set by TUI layer
                },
            },
        )
