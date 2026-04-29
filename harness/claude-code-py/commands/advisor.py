"""
Advisor command for Claude Code.

Ask the advisor for suggestions.

This is a stub implementation as the TypeScript source was empty.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .base import Availability, BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


@dataclass
class AdvisorCommand(BaseCommand):
    """Ask the advisor for suggestions.

    The advisor analyzes your current project and provides recommendations
    for improvements, best practices, and next steps.
    """

    name: str = "advisor"
    description: str = "Ask the advisor for suggestions"
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
        """Execute the advisor command."""
        return CommandResult(
            type="jsx",
            value=None,
            node={
                "type": "AdvisorPanel",
                "props": {
                    "onDone": None,  # Set by TUI layer
                },
            },
        )
