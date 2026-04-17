"""Config command for Claude Code.

Opens the configuration panel where users can view and modify settings.

TypeScript equivalent: src/commands/config/config.tsx, src/commands/config/index.ts
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .base import BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


@dataclass
class ConfigCommand(BaseCommand):
    """Open config panel.

    Displays a configuration interface where users can modify settings
    including model preferences, permissions, and other options.

    TypeScript equivalent: src/commands/config/config.tsx, src/commands/config/index.ts
    """

    name: str = "config"
    aliases: list[str] = field(default_factory=lambda: ["settings"])
    description: str = "Open config panel"
    command_type: CommandType = CommandType.LOCAL_JSX
    source: str = "builtin"

    def __post_init__(self) -> None:
        # Build lookup set for aliases
        self._all_names: set[str] = {self.name, *self.aliases}

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the config command.

        Opens the settings panel with the Config tab selected.
        In Python/Textual context, this renders a settings panel.
        """
        # For the TUI implementation, this would open a Settings panel.
        # Return a JSX node indicator - the actual rendering happens
        # in the Textual app's command handler.

        # In the CLI context, fall back to text-based config display
        return CommandResult(
            type="jsx",
            value=None,
            node={
                "type": "config",
                "tab": "Config",
                "context": context,
            },
        )

    def get_help(self) -> str:
        """Get help text for this command."""
        return "/config: Open config panel"
