"""
Color command for Claude Code.

Sets the prompt bar color for the current session.

TypeScript equivalent: src/commands/color/color.ts
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..tools.agent_color_manager import (
    AGENT_COLORS,
    is_reset_alias,
    is_valid_color,
)
from .base import Availability, BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


@dataclass
class ColorCommand(BaseCommand):
    """Set the prompt bar color for this session.

    Allows changing the color of the agent's prompt bar. Available colors
    are listed in AGENT_COLORS. Use 'default' to reset to the default color.
    """

    name: str = "color"
    description: str = "Set the prompt bar color for this session"
    argument_hint: str | None = "<color|default>"
    availability: list[str] = field(
        default_factory=lambda: [Availability.ALL.value]
    )
    command_type: CommandType = CommandType.LOCAL
    immediate: bool = True
    supports_non_interactive: bool = True

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the color command."""
        color_arg = args.strip().lower()

        if not color_arg:
            color_list = ", ".join(AGENT_COLORS)
            return CommandResult(
                type="text",
                value=f"Please provide a color. Available colors: {color_list}, default",
            )

        # Handle reset aliases
        if is_reset_alias(color_arg):
            return CommandResult(
                type="text",
                value="Session color reset to default",
            )

        # Validate color
        if not is_valid_color(color_arg):
            color_list = ", ".join(AGENT_COLORS)
            return CommandResult(
                type="text",
                value=f'Invalid color "{color_arg}". Available colors: {color_list}, default',
            )

        # Apply the color
        # In a full implementation, this would persist to session storage
        # and update the AppState. For now, return confirmation.
        return CommandResult(
            type="text",
            value=f"Session color set to: {color_arg}",
        )
