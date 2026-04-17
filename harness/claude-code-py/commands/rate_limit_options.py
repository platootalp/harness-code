"""Rate limit options command for Claude Code.

Shows options when a rate limit is reached.

TypeScript equivalent: src/commands/rate-limit-options/index.ts, src/commands/rate-limit-options/rate-limit-options.tsx
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .base import BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


@dataclass
class RateLimitOptionsCommand(BaseCommand):
    """Show options when rate limit is reached.

    TypeScript equivalent: src/commands/rate-limit-options/index.ts
    """

    name: str = "rate-limit-options"
    aliases: list[str] = field(default_factory=list)
    description: str = "Show options when rate limit is reached"
    command_type = CommandType.LOCAL
    is_hidden: bool = True  # Hidden from help - only used internally
    source: str = "builtin"

    def __post_init__(self) -> None:
        self._all_names: set[str] = {self.name, *self.aliases}

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the rate limit options command.

        Shows options when a rate limit is reached.
        """
        return CommandResult(
            type="jsx",
            value=None,
            node={
                "type": "rate-limit-options",
                "context": context,
            },
        )
