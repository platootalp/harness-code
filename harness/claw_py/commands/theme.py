"""
Theme command for Claude Code.

Changes the terminal theme.

TypeScript equivalent: src/commands/theme/theme.tsx
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .base import Availability, BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


@dataclass
class ThemeCommand(BaseCommand):
    """Change the terminal theme.

    Opens an interactive theme picker to select a terminal color theme.
    """

    name: str = "theme"
    description: str = "Change the theme"
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
        """Execute the theme command.

        Returns a node dict for TUI rendering of the theme picker.
        In a full implementation, this would render the ThemePicker component.
        """
        # Return a JSX node for TUI rendering
        # The TUI layer would handle rendering the theme picker UI
        return CommandResult(
            type="jsx",
            value=None,
            node={
                "type": "ThemePicker",
                "props": {
                    "onThemeSelect": None,  # Set by TUI layer
                    "onCancel": None,  # Set by TUI layer
                    "skipExitHandling": True,
                },
            },
        )
