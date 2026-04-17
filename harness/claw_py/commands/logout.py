"""
Logout command for Claude Code.

Log out from Claude Code.

TypeScript equivalent: src/commands/logout/logout.tsx
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .base import Availability, BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


@dataclass
class LogoutCommand(BaseCommand):
    """Log out from Claude Code.

    Clears authentication credentials, secure storage, and caches,
    then gracefully shuts down the session.
    """

    name: str = "logout"
    description: str = "Log out from Claude Code"
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
        """Execute the logout command."""
        # In a full implementation, this would:
        # 1. Flush telemetry
        # 2. Remove API key
        # 3. Clear secure storage
        # 4. Clear auth-related caches
        # 5. Update global config
        # 6. Trigger graceful shutdown

        return CommandResult(
            type="jsx",
            value=None,
            node={
                "type": "Logout",
                "props": {
                    "onDone": None,  # Set by TUI layer
                    "performLogout": True,  # Signal to perform logout action
                },
            },
        )
