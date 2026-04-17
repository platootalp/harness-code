"""
IDE command for Claude Code.

Manages IDE integrations and shows status.

TypeScript equivalent: src/commands/ide/ide.tsx
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .base import Availability, BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


@dataclass
class IDECommand(BaseCommand):
    """Manage IDE integrations and show status.

    View configured IDE integrations (VS Code, Cursor, JetBrains, etc.)
    and open projects in your preferred editor.
    """

    name: str = "ide"
    description: str = "Manage IDE integrations and show status"
    argument_hint: str | None = "[open]"
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
        """Execute the ide command."""
        arg = args.strip().lower() if args.strip() else ""

        if arg == "open":
            # Return node for IDE selection/picker
            return CommandResult(
                type="jsx",
                value=None,
                node={
                    "type": "IDEOpenSelection",
                    "props": {
                        "availableIDEs": [],  # Would be populated by TUI layer
                        "onSelectIDE": None,  # Set by TUI layer
                    },
                },
            )

        # Default - show IDE status
        return CommandResult(
            type="jsx",
            value=None,
            node={
                "type": "IDEPanel",
                "props": {
                    "onDone": None,  # Set by TUI layer
                },
            },
        )
