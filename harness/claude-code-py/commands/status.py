"""Status command for Claude Code.

Shows Claude Code status including version, model, account, and connectivity.

TypeScript equivalent: src/commands/status/status.tsx
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .base import BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


@dataclass
class StatusCommand(BaseCommand):
    """Show Claude Code status.

    TypeScript equivalent: src/commands/status/status.tsx
    """

    name: str = "status"
    description: str = "Show Claude Code status including version, model, account, API connectivity, and tool statuses"
    command_type: CommandType = CommandType.LOCAL_JSX
    source: str = "builtin"
    immediate: bool = True

    def __post_init__(self) -> None:
        # Build lookup set for aliases
        self._all_names: set[str] = {self.name}

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the status command."""
        return CommandResult(
            type="jsx",
            value=None,
            node={
                "type": "settings",
                "default_tab": "Status",
                "context": context,
            },
        )
