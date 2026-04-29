"""Mobile command for Claude Code.

Show QR code to download the Claude mobile app.

TypeScript equivalent: src/commands/mobile/index.ts, src/commands/mobile/mobile.tsx
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .base import BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


# App store URLs
IOS_URL = "https://apps.apple.com/app/claude-by-anthropic/id6473753684"
ANDROID_URL = "https://play.google.com/store/apps/details?id=com.anthropic.claude"


@dataclass
class MobileCommand(BaseCommand):
    """Show QR code to download the Claude mobile app.

    TypeScript equivalent: src/commands/mobile/index.ts, src/commands/mobile/mobile.tsx
    """

    name: str = "mobile"
    aliases: list[str] = field(default_factory=lambda: ["ios", "android"])
    description: str = "Show QR code to download the Claude mobile app"
    command_type = CommandType.LOCAL
    source: str = "builtin"

    def __post_init__(self) -> None:
        self._all_names: set[str] = {self.name, *self.aliases}

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the mobile command.

        Shows download information for the Claude mobile app.
        """
        message = (
            "Claude Mobile App\n\n"
            "Download Claude on your mobile device to continue conversations on the go.\n\n"
            "iOS (Apple devices):\n"
            f"  {IOS_URL}\n\n"
            "Android (Google Play):\n"
            f"  {ANDROID_URL}\n\n"
            "Scan with your phone's camera app to quickly access the download links.\n"
        )
        return CommandResult(type="text", value=message)
