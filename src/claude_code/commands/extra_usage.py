"""Extra usage command for Claude Code.

Configure extra usage to keep working when limits are hit.

TypeScript equivalent: src/commands/extra-usage/index.ts, src/commands/extra-usage/extra-usage.tsx
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .base import BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


@dataclass
class ExtraUsageCommand(BaseCommand):
    """Configure extra usage to keep working when limits are hit.

    TypeScript equivalent: src/commands/extra-usage/index.ts
    """

    name: str = "extra-usage"
    aliases: list[str] = field(default_factory=list)
    description: str = "Configure extra usage to keep working when limits are hit"
    command_type = CommandType.LOCAL
    source: str = "builtin"

    def __post_init__(self) -> None:
        self._all_names: set[str] = {self.name, *self.aliases}

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the extra-usage command.

        Shows information about extra usage configuration.
        """
        message = (
            "Extra Usage Configuration\n\n"
            "To manage extra usage and billing:\n"
            "- Consumer accounts: Visit https://claude.ai/settings/usage\n"
            "- Team/Enterprise accounts: Visit https://claude.ai/admin-settings/usage\n\n"
            "If you have billing access, you can:\n"
            "- Enable extra usage to continue working when limits are hit\n"
            "- Set monthly spending limits\n"
            "- Manage team usage and budgets\n\n"
            "Contact your admin if you need help with team/enterprise accounts."
        )
        return CommandResult(type="text", value=message)
