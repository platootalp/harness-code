"""
Upgrade command for Claude Code.

Upgrade to Max plan.

TypeScript equivalent: src/commands/upgrade/upgrade.tsx
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .base import Availability, BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


@dataclass
class UpgradeCommand(BaseCommand):
    """Upgrade to Max plan.

    Opens the browser to upgrade to Claude Max subscription,
    then initiates the login flow after upgrade.
    """

    name: str = "upgrade"
    description: str = "Upgrade to Max plan"
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
        """Execute the upgrade command.

        Returns a node dict for TUI rendering. In a full implementation,
        this would open a browser to the upgrade page and then
        run the login flow.
        """
        return CommandResult(
            type="jsx",
            value=None,
            node={
                "type": "Upgrade",
                "props": {
                    "onDone": None,  # Set by TUI layer
                    "url": "https://claude.ai/upgrade/max",
                },
            },
        )
