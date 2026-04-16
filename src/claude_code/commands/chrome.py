"""Chrome command for Claude Code.

Claude in Chrome (Beta) settings.

TypeScript equivalent: src/commands/chrome/index.ts, src/commands/chrome/chrome.tsx
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .base import BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


@dataclass
class ChromeCommand(BaseCommand):
    """Claude in Chrome (Beta) settings.

    TypeScript equivalent: src/commands/chrome/index.ts, src/commands/chrome/chrome.tsx
    """

    name: str = "chrome"
    aliases: list[str] = field(default_factory=list)
    description: str = "Claude in Chrome (Beta) settings"
    command_type = CommandType.LOCAL
    source: str = "builtin"

    def __post_init__(self) -> None:
        self._all_names: set[str] = {self.name, *self.aliases}

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the chrome command.

        Shows Claude in Chrome settings and configuration.
        """
        message = (
            "Claude in Chrome (Beta)\n\n"
            "Claude in Chrome works with the Chrome extension to let you "
            "control your browser directly from Claude Code.\n\n"
            "Features:\n"
            "- Navigate websites\n"
            "- Fill forms\n"
            "- Capture screenshots\n"
            "- Record GIFs\n"
            "- Debug with console logs and network requests\n\n"
            "Setup:\n"
            "1. Install the Chrome extension from https://claude.ai/chrome\n"
            "2. Connect your Claude.ai account\n"
            "3. Use: claude --chrome or claude --no-chrome\n\n"
            "Learn more: https://code.claude.com/docs/en/chrome"
        )
        return CommandResult(type="text", value=message)
