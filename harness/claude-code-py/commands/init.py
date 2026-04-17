"""
Init command for Claude Code.

Initializes Claude Code for a project.

This is a stub implementation as the TypeScript source was empty.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .base import Availability, BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


@dataclass
class InitCommand(BaseCommand):
    """Initialize Claude Code for a project.

    Sets up the initial configuration and files needed for Claude Code
    to work properly in a project directory.
    """

    name: str = "init"
    description: str = "Initialize Claude Code for a project"
    availability: list[str] = field(
        default_factory=lambda: [Availability.ALL.value]
    )
    command_type: CommandType = CommandType.LOCAL_JSX
    supports_non_interactive: bool = True

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the init command."""
        return CommandResult(
            type="jsx",
            value=None,
            node={
                "type": "InitWizard",
                "props": {
                    "onDone": None,  # Set by TUI layer
                },
            },
        )
