"""Think-back command for Claude Code.

Shows the user's 2025 Claude Code Year in Review.

TypeScript equivalent: src/commands/thinkback/index.ts, src/commands/thinkback/thinkback.tsx
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .base import BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


@dataclass
class ThinkbackCommand(BaseCommand):
    """Your 2025 Claude Code Year in Review.

    TypeScript equivalent: src/commands/thinkback/index.ts, src/commands/thinkback/thinkback.tsx
    """

    name: str = "think-back"
    aliases: list[str] = field(default_factory=list)
    description: str = "Your 2025 Claude Code Year in Review"
    command_type = CommandType.LOCAL
    source: str = "builtin"

    def __post_init__(self) -> None:
        self._all_names: set[str] = {self.name, *self.aliases}

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the think-back command.

        Shows year in review stats for 2025.
        """
        # Check feature gate - in Python, we just show the feature
        # The actual feature gate is checked by the caller
        message = (
            "Your 2025 Claude Code Year in Review\n\n"
            "This feature shows your coding statistics and highlights "
            "from using Claude Code throughout 2025.\n\n"
            "Check back in 2025 to see your year in review!"
        )
        return CommandResult(type="text", value=message)
