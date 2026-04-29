"""Desktop command for Claude Code.

Continue the current session in Claude Desktop.

TypeScript equivalent: src/commands/desktop/index.ts, src/commands/desktop/desktop.tsx
"""

from __future__ import annotations

import platform
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .base import BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


@dataclass
class DesktopCommand(BaseCommand):
    """Continue the current session in Claude Desktop.

    TypeScript equivalent: src/commands/desktop/index.ts, src/commands/desktop/desktop.tsx
    """

    name: str = "desktop"
    aliases: list[str] = field(default_factory=lambda: ["app"])
    description: str = "Continue the current session in Claude Desktop"
    command_type = CommandType.LOCAL
    source: str = "builtin"

    def __post_init__(self) -> None:
        self._all_names: set[str] = {self.name, *self.aliases}

    def _is_supported_platform(self) -> bool:
        """Check if running on a supported platform."""
        system = platform.system()
        arch = platform.machine()
        return system == "Darwin" or (system == "Windows" and arch == "x86_64")

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the desktop command.

        Shows information about continuing in Claude Desktop.
        """
        if not self._is_supported_platform():
            return CommandResult(
                type="text",
                value="Claude Desktop is available on macOS and Windows (x86_64).\n"
                "Visit https://claude.ai/download to download the app.",
            )

        message = (
            "Claude Desktop\n\n"
            "Continue your session in Claude Desktop for a native app experience.\n\n"
            "Download Claude Desktop:\n"
            "  https://claude.ai/download\n\n"
            "After installing:\n"
            "1. Open Claude Desktop\n"
            "2. Sign in with the same account\n"
            "3. Your session will be available in the desktop app\n"
        )
        return CommandResult(type="text", value=message)
