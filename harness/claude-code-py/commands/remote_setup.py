"""Remote setup command for Claude Code.

Setup Claude Code on the web (requires connecting your GitHub account).

TypeScript equivalent: src/commands/remote-setup/index.ts, src/commands/remote-setup/remote-setup.tsx
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .base import BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


@dataclass
class RemoteSetupCommand(BaseCommand):
    """Setup Claude Code on the web.

    TypeScript equivalent: src/commands/remote-setup/index.ts
    """

    name: str = "remote-setup"
    aliases: list[str] = field(default_factory=list)
    description: str = "Setup Claude Code on the web (requires connecting your GitHub account)"
    argument_hint: str | None = None
    command_type = CommandType.LOCAL
    source: str = "builtin"

    def __post_init__(self) -> None:
        self._all_names: set[str] = {self.name, *self.aliases}

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the remote-setup command.

        Opens the web setup configuration panel.
        """
        return CommandResult(
            type="jsx",
            value=None,
            node={
                "type": "remote-setup",
                "context": context,
            },
        )
