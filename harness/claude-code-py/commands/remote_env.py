"""Remote environment command for Claude Code.

Configure the default remote environment for teleport sessions.

TypeScript equivalent: src/commands/remote-env/index.ts, src/commands/remote-env/remote-env.tsx
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .base import BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


@dataclass
class RemoteEnvCommand(BaseCommand):
    """Configure the default remote environment for teleport sessions.

    TypeScript equivalent: src/commands/remote-env/index.ts
    """

    name: str = "remote-env"
    aliases: list[str] = field(default_factory=list)
    description: str = "Configure the default remote environment for teleport sessions"
    command_type = CommandType.LOCAL
    source: str = "builtin"

    def __post_init__(self) -> None:
        self._all_names: set[str] = {self.name, *self.aliases}

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the remote-env command.

        Opens the remote environment configuration panel.
        """
        return CommandResult(
            type="jsx",
            value=None,
            node={
                "type": "remote-env",
                "context": context,
            },
        )
