"""
Hooks command for Claude Code.

View and configure hook configurations for tool events.

TypeScript equivalent: src/commands/hooks/hooks.tsx
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .base import Availability, BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


@dataclass
class HooksCommand(BaseCommand):
    """View hook configurations for tool events.

    Hooks allow running custom scripts before or after tool execution.
    Configure hooks for events like pre-tool-use, post-tool-use, etc.
    """

    name: str = "hooks"
    description: str = "View hook configurations for tool events"
    availability: list[str] = field(
        default_factory=lambda: [Availability.ALL.value]
    )
    command_type: CommandType = CommandType.LOCAL_JSX
    immediate: bool = True
    supports_non_interactive: bool = False

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the hooks command.

        Returns a node dict for TUI rendering of the hooks config menu.
        """
        # Return a JSX node for TUI rendering
        return CommandResult(
            type="jsx",
            value=None,
            node={
                "type": "HooksConfigMenu",
                "props": {
                    "toolNames": [],  # Would be populated from context
                    "onExit": None,  # Set by TUI layer
                },
            },
        )
