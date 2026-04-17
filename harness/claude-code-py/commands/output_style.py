"""Output style command for Claude Code.

Deprecated: This command has been deprecated in favor of /config.

TypeScript equivalent: src/commands/output-style/index.ts, src/commands/output-style/output-style.tsx
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .base import BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


@dataclass
class OutputStyleCommand(BaseCommand):
    """Deprecated: Use /config to change output style.

    TypeScript equivalent: src/commands/output-style/index.ts
    """

    name: str = "output-style"
    aliases: list[str] = field(default_factory=list)
    description: str = "Deprecated: use /config to change output style"
    command_type = CommandType.LOCAL
    is_hidden: bool = True
    source: str = "builtin"

    def __post_init__(self) -> None:
        self._all_names: set[str] = {self.name, *self.aliases}

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the output-style command.

        Shows deprecation notice directing users to /config.
        """
        message = (
            "/output-style has been deprecated. "
            "Use /config to change your output style, or set it in your settings file. "
            "Changes take effect on the next session."
        )
        return CommandResult(type="text", value=message)
