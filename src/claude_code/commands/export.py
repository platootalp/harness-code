"""Export command for Claude Code.

Export conversation to a file.

TypeScript equivalent: src/commands/export/
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from .base import Availability, BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


# =============================================================================
# Export Command
# =============================================================================


@dataclass
class ExportCommand(BaseCommand):
    """Export the current conversation to a file.

    Exports the conversation as plain text. If a filename is provided,
    writes directly to that file. Otherwise, generates a filename from
    the first prompt or current timestamp.

    TypeScript equivalent: src/commands/export/export.tsx
    """

    name: str = "export"
    aliases: list[str] = field(default_factory=list)
    description: str = "Export the conversation to a file"
    argument_hint: str | None = "[filename]"
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
        """Execute the export command."""
        cwd: str = context.get("cwd", os.getcwd())
        messages: list[Any] = context.get("messages", [])

        # Render conversation to text
        content = self._render_conversation(messages)

        if not content.strip():
            return CommandResult(
                type="text",
                value="No conversation content to export.",
            )

        filename_arg = args.strip() if args.strip() else ""

        if filename_arg:
            # User specified a filename
            final_filename = filename_arg
            if not final_filename.endswith(".txt"):
                final_filename = final_filename.rsplit(".", 1)[0] + ".txt"

            filepath = os.path.join(cwd, final_filename)

            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                return CommandResult(
                    type="text",
                    value=f"Conversation exported to: {filepath}",
                )
            except OSError as e:
                return CommandResult(
                    type="text",
                    value=f"Failed to export conversation: {e}",
                )

        # Generate default filename
        default_filename = self._generate_default_filename(messages)
        filepath = os.path.join(cwd, default_filename)

        # Try to write the file
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            return CommandResult(
                type="text",
                value=f"Conversation exported to: {filepath}",
            )
        except OSError as e:
            # Fallback: show content preview
            lines = [
                f"Could not write to {filepath}: {e}",
                "",
                "Conversation content preview:",
                "-" * 40,
                content[:2000],
            ]
            if len(content) > 2000:
                lines.append(f"\n... ({len(content) - 2000} more characters)")
            return CommandResult(type="text", value="\n".join(lines))

    def _render_conversation(self, messages: list[Any]) -> str:
        """Render conversation messages to plain text."""
        if not messages:
            return ""

        lines: list[str] = []

        for msg in messages:
            role = getattr(msg, "role", None) or ""
            role_name = role.value if hasattr(role, "value") else str(role)

            content = ""
            if hasattr(msg, "content_blocks") and msg.content_blocks:
                for block in msg.content_blocks:
                    if hasattr(block, "text") and block.text:
                        content += block.text
            elif hasattr(msg, "get"):
                # Dict-like access for backwards compatibility
                content = msg.get("content", "")
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            content = block.get("text", "")
                            break

            if role_name == "user":
                lines.append(f"## You\n\n{content}\n")
            elif role_name == "assistant":
                lines.append(f"## Claude\n\n{content}\n")
            elif role_name == "tool":
                tool_name = getattr(msg, "name", "tool")
                lines.append(f"## Tool: {tool_name}\n\n{content}\n")

        return "\n".join(lines)

    def _generate_default_filename(self, messages: list[Any]) -> str:
        """Generate a default export filename."""
        first_prompt = ""
        for msg in messages:
            role = getattr(msg, "role", None) or ""
            role_name = role.value if hasattr(role, "value") else str(role)
            if role_name == "user":
                if hasattr(msg, "content_blocks") and msg.content_blocks:
                    for block in msg.content_blocks:
                        if hasattr(block, "text") and block.text:
                            first_prompt = block.text.strip()
                            break
                elif hasattr(msg, "get"):
                    c = msg.get("content", "")
                    if isinstance(c, str):
                        first_prompt = c.strip()
                break

        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d-%H%M%S")

        if first_prompt:
            first_line = first_prompt.split("\n")[0].strip()
            if len(first_line) > 50:
                first_line = first_line[:47] + "..."
            sanitized = "".join(
                c if c.isalnum() or c in " -_" else "" for c in first_line
            ).strip().replace(" ", "-")
            if sanitized:
                return f"{timestamp}-{sanitized[:50]}.txt"

        return f"conversation-{timestamp}.txt"


# =============================================================================
# Registry
# =============================================================================


def get_all_commands() -> list[BaseCommand]:
    """Get all export-related commands.

    Returns:
        List of export command instances.
    """
    return [ExportCommand()]


def register_builtin_commands(registry: Any) -> None:
    """Register export commands with a command registry.

    Args:
        registry: Command registry with a register() method.
    """
    for cmd in get_all_commands():
        registry.register(cmd)
