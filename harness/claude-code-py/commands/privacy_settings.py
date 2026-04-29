"""Privacy settings command for Claude Code.

Opens the privacy settings panel.

TypeScript equivalent: src/commands/privacy-settings/index.ts, src/commands/privacy-settings/privacy-settings.tsx
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .base import BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


@dataclass
class PrivacySettingsCommand(BaseCommand):
    """View and update your privacy settings.

    TypeScript equivalent: src/commands/privacy-settings/index.ts
    """

    name: str = "privacy-settings"
    aliases: list[str] = field(default_factory=list)
    description: str = "View and update your privacy settings"
    command_type = CommandType.LOCAL
    source: str = "builtin"

    def __post_init__(self) -> None:
        self._all_names: set[str] = {self.name, *self.aliases}

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the privacy settings command.

        Opens the privacy settings panel.
        In a TUI context, this would render a privacy settings dialog.
        """
        return CommandResult(
            type="jsx",
            value=None,
            node={
                "type": "privacy-settings",
                "context": context,
            },
        )
