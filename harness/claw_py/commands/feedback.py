"""
Feedback command for Claude Code.

Submit feedback or report a bug.

TypeScript equivalent: src/commands/feedback/feedback.tsx
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .base import Availability, BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


@dataclass
class FeedbackCommand(BaseCommand):
    """Submit feedback or report a bug.

    Opens an interactive form to submit feedback, bug reports,
    or feature requests to the Claude Code team.
    """

    name: str = "feedback"
    aliases: list[str] = field(default_factory=lambda: ["bug"])
    description: str = "Submit feedback or report a bug"
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
        """Execute the feedback command.

        Returns a node dict for TUI rendering of the feedback form.
        """
        initial_description = args.strip() if args.strip() else ""

        return CommandResult(
            type="jsx",
            value=None,
            node={
                "type": "Feedback",
                "props": {
                    "initialDescription": initial_description,
                    "messages": [],  # Would be populated from context
                    "onDone": None,  # Set by TUI layer
                    "abortSignal": None,  # Would be from context
                },
            },
        )
