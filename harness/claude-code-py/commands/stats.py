"""Stats command for Claude Code.

Shows Claude Code usage statistics and activity.

TypeScript equivalent: src/commands/stats/stats.tsx
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .base import BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


@dataclass
class StatsCommand(BaseCommand):
    """Show Claude Code usage statistics and activity.

    TypeScript equivalent: src/commands/stats/stats.tsx
    """

    name: str = "stats"
    description: str = "Show your Claude Code usage statistics and activity"
    command_type: CommandType = CommandType.LOCAL_JSX
    source: str = "builtin"

    def __post_init__(self) -> None:
        # Build lookup set for aliases
        self._all_names: set[str] = {self.name}

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the stats command."""
        return CommandResult(
            type="jsx",
            value=None,
            node={
                "type": "stats",
                "context": context,
            },
        )
