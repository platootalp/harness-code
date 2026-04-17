"""
Login command for Claude Code.

Log in to Claude Code via OAuth.

TypeScript equivalent: src/commands/login/login.tsx
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .base import Availability, BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


@dataclass
class LoginCommand(BaseCommand):
    """Log in to Claude Code.

    Initiates the OAuth login flow to authenticate with your
    Anthropic account or Claude.ai subscription.
    """

    name: str = "login"
    description: str = "Log in to Claude Code"
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
        """Execute the login command.

        Returns a node dict for TUI rendering of the OAuth flow.
        """
        return CommandResult(
            type="jsx",
            value=None,
            node={
                "type": "Login",
                "props": {
                    "onDone": None,  # Set by TUI layer
                    "startingMessage": None,
                },
            },
        )
