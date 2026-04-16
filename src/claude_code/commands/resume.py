"""Resume command for Claude Code.

Resumes a previous conversation.

TypeScript equivalent: src/commands/resume/resume.tsx, index.ts
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .base import Availability, BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


@dataclass
class ResumeCommand(BaseCommand):
    """Resume a previous conversation.

    Allows resuming past conversations by:
    - Session ID (UUID format)
    - Search term matching session titles
    - Listing available sessions (when no args provided)

    TypeScript equivalent: src/commands/resume/resume.tsx
    """

    name: str = "resume"
    aliases: list[str] = field(default_factory=lambda: ["continue"])
    description: str = "Resume a previous conversation"
    argument_hint: str | None = "[conversation id or search term]"
    command_type: CommandType = CommandType.LOCAL_JSX
    availability: list[str] = field(default_factory=lambda: [Availability.ALL.value])
    source: str = "builtin"

    def __post_init__(self) -> None:
        self._all_names: set[str] = {self.name, *self.aliases}

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the resume command."""
        import uuid as uuid_mod

        trimmed = args.strip() if args else ""
        current_session_id: str | None = context.get("session_id")
        session_logs: list[dict[str, Any]] = context.get("session_logs", [])

        # Filter out current session
        resumable = [
            s for s in session_logs
            if s.get("session_id") != current_session_id
        ]

        if not trimmed:
            # No argument - show available sessions
            if not resumable:
                return CommandResult(
                    type="text",
                    value=(
                        "No previous conversations found to resume.\n"
                        "Start a new conversation and it will be saved for future resume."
                    ),
                )

            lines = ["Available conversations to resume:", ""]
            sorted_sessions = sorted(
                resumable,
                key=lambda s: s.get("modified", ""),
                reverse=True,
            )[:10]

            for i, log in enumerate(sorted_sessions, 1):
                title = log.get("title") or log.get("first_prompt", "Untitled")
                if len(title) > 60:
                    title = title[:57] + "..."
                lines.append(f"  {i}. {title}")
                lines.append(f"     ID: {log.get('session_id')}")

            lines.extend([
                "",
                f"Showing {len(sorted_sessions)} of {len(resumable)} sessions.",
                "",
                "Usage:",
                "  /resume <session-id>  - Resume by session ID",
                "  /resume <search-term> - Search by title",
            ])
            return CommandResult(type="text", value="\n".join(lines))

        # Try to match as UUID first
        try:
            target_uuid = uuid_mod.UUID(trimmed)
            for log in resumable:
                if str(log.get("session_id")) == str(target_uuid):
                    return CommandResult(
                        type="text",
                        value=f"Found session: {log.get('title', 'Untitled')}\n"
                              f"Session ID: {log.get('session_id')}\n"
                              f"Last modified: {log.get('modified', 'unknown')}\n\n"
                              f"Use 'claude --resume {target_uuid}' to resume this session.",
                    )

            return CommandResult(
                type="text",
                value=f"Session '{trimmed}' was not found.",
            )
        except ValueError:
            pass

        # Search by title
        search_term = trimmed.lower()
        matches = [
            s for s in resumable
            if search_term in (s.get("title", "") or "").lower()
            or search_term in (s.get("first_prompt", "") or "").lower()
        ]

        if len(matches) == 1:
            log = matches[0]
            return CommandResult(
                type="text",
                value=f"Found session: {log.get('title', 'Untitled')}\n"
                      f"Session ID: {log.get('session_id')}\n"
                      f"Last modified: {log.get('modified', 'unknown')}\n\n"
                      f"Use 'claude --resume {log.get('session_id')}' to resume.",
            )

        if len(matches) > 1:
            lines = [f"Found {len(matches)} sessions matching '{trimmed}':", ""]
            for i, log in enumerate(matches, 1):
                title = log.get("title") or log.get("first_prompt", "Untitled")
                if len(title) > 50:
                    title = title[:47] + "..."
                lines.append(f"  {i}. {title}")
                lines.append(f"     ID: {log.get('session_id')}")
            lines.extend([
                "",
                "Use 'claude --resume <session-id>' to resume a specific session.",
            ])
            return CommandResult(type="text", value="\n".join(lines))

        return CommandResult(
            type="text",
            value=f"No sessions found matching '{trimmed}'.",
        )


# =============================================================================
# Registry
# =============================================================================


def get_all_commands() -> list[BaseCommand]:
    """Get all resume-related commands.

    Returns:
        List of resume command instances.
    """
    return [ResumeCommand()]


def register_builtin_commands(registry: Any) -> None:
    """Register resume commands with a command registry.

    Args:
        registry: Command registry with a register() method.
    """
    for cmd in get_all_commands():
        registry.register(cmd)
