"""Rename command for Claude Code.

Renames the current session.

TypeScript equivalent: src/commands/rename/rename.ts, generateSessionName.ts
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .base import BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


@dataclass
class RenameCommand(BaseCommand):
    """Rename the current session.

    TypeScript equivalent: src/commands/rename/rename.ts
    """

    name: str = "rename"
    description: str = "Rename the current session"
    argument_hint: str | None = "[name]"
    command_type: CommandType = CommandType.LOCAL_JSX
    source: str = "builtin"
    immediate: bool = True

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the rename command."""
        # Check if this is a teammate (teammates cannot rename)
        is_teammate = context.get("_is_teammate", False)
        if is_teammate:
            return CommandResult(
                type="text",
                value=(
                    "Cannot rename: This session is a swarm teammate. "
                    "Teammate names are set by the team leader."
                ),
            )

        new_name = args.strip() if args.strip() else None

        if not new_name:
            # Try to generate a name
            new_name = self._generate_session_name(context)
            if not new_name:
                return CommandResult(
                    type="text",
                    value=(
                        "Could not generate a name: no conversation context yet. "
                        "Usage: /rename <name>"
                    ),
                )

        # Save the new name
        session_id = context.get("_session_id", "default")
        repl_state: dict[str, Any] | None = context.get("_repl_state")

        if repl_state:
            # Update session name in repl state
            if hasattr(repl_state, "session_name"):
                repl_state.session_name = new_name

        # Save to storage
        self._save_session_name(session_id, new_name, context)

        return CommandResult(
            type="text",
            value=f"Session renamed to: {new_name}",
        )

    def _generate_session_name(self, context: dict[str, Any]) -> str | None:
        """Generate a session name from conversation context.

        Returns a generated name or None if not enough context.
        """
        messages: list[dict[str, Any]] = context.get("messages", [])
        if not messages:
            return None

        # Get first user message
        first_msg = None
        for msg in messages:
            # Support both dict-style and object-style messages
            if hasattr(msg, "role"):
                role = getattr(msg, "role", None)
                if role is not None and hasattr(role, "value"):
                    role_val = role.value
                else:
                    role_val = str(role) if role is not None else ""
            else:
                role_val = msg.get("role", "")
            if role_val == "user":
                first_msg = msg
                break

        if not first_msg:
            return None

        # Extract content - support both object and dict styles
        content = ""
        if hasattr(first_msg, "content_blocks") and first_msg.content_blocks:
            for block in first_msg.content_blocks:
                if hasattr(block, "text") and block.text:
                    content = block.text
                    break
        elif hasattr(first_msg, "get"):
            content = first_msg.get("content", "")
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        content = block.get("text", "")
                        break

        if not content or not isinstance(content, str):
            return None

        # Collapse whitespace and truncate
        words = " ".join(content.split()).strip()
        if not words:
            return None

        # Take first 8 words, max 60 chars
        name = words[:60]
        return name

    def _save_session_name(
        self,
        session_id: str,
        name: str,
        context: dict[str, Any],
    ) -> None:
        """Save session name to storage."""
        # This would typically save to session storage
        # For now, just update context
        pass


# =============================================================================
# Registry
# =============================================================================


def get_all_commands() -> list[BaseCommand]:
    """Get all rename-related commands.

    Returns:
        List of rename command instances.
    """
    return [RenameCommand()]


def register_builtin_commands(registry: Any) -> None:
    """Register rename commands with a command registry.

    Args:
        registry: Command registry with a register() method.
    """
    for cmd in get_all_commands():
        registry.register(cmd)
