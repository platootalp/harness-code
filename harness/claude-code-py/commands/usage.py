"""Usage command for Claude Code.

Shows plan usage limits.

TypeScript equivalent: src/commands/usage/usage.tsx
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .base import Availability, BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


def _is_claude_ai_subscriber() -> bool:
    """Check if the user has a claude.ai subscription.

    Returns:
        True if subscribed.
    """
    return bool(os.environ.get("CLAUDE_AI_SUBSCRIBER"))


@dataclass
class UsageCommand(BaseCommand):
    """Show plan usage limits.

    TypeScript equivalent: src/commands/usage/usage.tsx
    """

    name: str = "usage"
    description: str = "Show plan usage limits"
    command_type: CommandType = CommandType.LOCAL_JSX
    source: str = "builtin"
    availability: list[str] = field(
        default_factory=lambda: [Availability.CLAUDE_AI.value]
    )

    def __post_init__(self) -> None:
        # Build lookup set for aliases
        self._all_names: set[str] = {self.name}
        # Hide if not a subscriber
        self.is_hidden = not _is_claude_ai_subscriber()

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the usage command."""
        return CommandResult(
            type="jsx",
            value=None,
            node={
                "type": "settings",
                "default_tab": "Usage",
                "context": context,
            },
        )
