"""
Doctor command for Claude Code.

Diagnoses and verifies the Claude Code installation and settings.

TypeScript equivalent: src/commands/doctor/doctor.tsx
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .base import Availability, BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


@dataclass
class DoctorCommand(BaseCommand):
    """Diagnose and verify your Claude Code installation and settings.

    Checks for common issues with configuration, permissions, API keys,
    and other setup problems. Provides recommendations for fixes.
    """

    name: str = "doctor"
    description: str = "Diagnose and verify your Claude Code installation and settings"
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
        """Execute the doctor command.

        Returns a node dict for TUI rendering of the doctor component.
        """
        return CommandResult(
            type="jsx",
            value=None,
            node={
                "type": "Doctor",
                "props": {
                    "onDone": None,  # Set by TUI layer
                },
            },
        )
