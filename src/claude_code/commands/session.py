"""Session command for Claude Code.

Shows remote session URL and QR code for mobile access.

TypeScript equivalent: src/commands/session/session.tsx, index.ts
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .base import BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


@dataclass
class SessionCommand(BaseCommand):
    """Show remote session URL and QR code.

    TypeScript equivalent: src/commands/session/session.tsx
    """

    name: str = "session"
    aliases: list[str] = field(default_factory=lambda: ["remote"])
    description: str = "Show remote session URL and QR code"
    argument_hint: str | None = None
    command_type: CommandType = CommandType.LOCAL_JSX
    source: str = "builtin"
    immediate: bool = True
    is_hidden: bool = True  # Hidden when not in remote mode

    def __post_init__(self) -> None:
        self._all_names: set[str] = {self.name, *self.aliases}

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the session command."""
        remote_url: str | None = context.get("_remote_session_url")

        if not remote_url:
            return CommandResult(
                type="text",
                value=(
                    "Not in remote mode. Start with `claude --remote` to use this command.\n"
                    "(Use /help for available commands)"
                ),
            )

        # Return text with remote session info
        # QR code generation requires a full TUI implementation
        lines = [
            "Remote Session",
            "",
            f"Open in browser: {remote_url}",
            "",
            "(QR code generation requires a full TUI - not available in text mode)",
        ]
        return CommandResult(type="text", value="\n".join(lines))


# =============================================================================
# Registry
# =============================================================================


def get_all_commands() -> list[BaseCommand]:
    """Get all session-related commands.

    Returns:
        List of session command instances.
    """
    return [SessionCommand()]


def register_builtin_commands(registry: Any) -> None:
    """Register session commands with a command registry.

    Args:
        registry: Command registry with a register() method.
    """
    for cmd in get_all_commands():
        registry.register(cmd)
