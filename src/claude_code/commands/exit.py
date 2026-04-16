"""Exit command for Claude Code.

Exits the Claude Code session.

TypeScript equivalent: src/commands/exit/exit.tsx
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .base import BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


@dataclass
class ExitCommand(BaseCommand):
    """Exit Claude Code.

    TypeScript equivalent: src/commands/exit/exit.tsx
    """

    name: str = "exit"
    aliases: list[str] = field(default_factory=lambda: ["quit", "q"])
    description: str = "Exit Claude Code"
    argument_hint: str | None = None
    command_type: CommandType = CommandType.LOCAL
    source: str = "builtin"
    immediate: bool = True
    supports_non_interactive: bool = True

    def __post_init__(self) -> None:
        self._all_names: set[str] = {self.name, *self.aliases}

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the exit command."""
        repl_state: dict[str, Any] | None = context.get("_repl_state")

        # Check for worktree session
        if repl_state and hasattr(repl_state, "_worktree_session"):
            # Detach from tmux worktree
            try:
                import subprocess
                subprocess.run(
                    ["tmux", "detach-client"],
                    capture_output=True,
                    timeout=5,
                )
            except Exception:
                pass

        # Exit with code 0
        return CommandResult(
            type="text",
            value="Goodbye! Exiting Claude Code.",
        )
