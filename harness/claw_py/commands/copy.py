"""Copy command for Claude Code.

Copies Claude's last response to clipboard.

TypeScript equivalent: src/commands/copy/copy.tsx
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .base import BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


@dataclass
class CopyCommand(BaseCommand):
    """Copy Claude's last response to clipboard.

    TypeScript equivalent: src/commands/copy/copy.tsx
    """

    name: str = "copy"
    description: str = "Copy Claude's last response to clipboard (supports /copy N)"
    argument_hint: str | None = "[N]"
    command_type: CommandType = CommandType.LOCAL_JSX
    source: str = "builtin"

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the copy command."""
        # Get the N argument (which response to copy)
        n_arg = args.strip() if args.strip() else "1"
        try:
            response_index = int(n_arg) - 1  # Convert to 0-based
        except ValueError:
            response_index = 0

        messages: list[dict[str, Any]] = context.get("messages", [])

        # Collect assistant responses (newest first)
        assistant_texts: list[tuple[int, str]] = []
        for i, msg in enumerate(reversed(messages)):
            if msg.get("role") == "assistant":
                content = msg.get("content") or ""
                if isinstance(content, str) and content.strip():
                    assistant_texts.append((len(messages) - 1 - i, content))
                elif isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text = (block.get("text") or "").strip()
                            if text:
                                assistant_texts.append((len(messages) - 1 - i, text))
                                break

        if not assistant_texts:
            return CommandResult(
                type="text",
                value="No assistant response to copy.",
            )

        if response_index < 0 or response_index >= len(assistant_texts):
            return CommandResult(
                type="text",
                value=f"Invalid response number. There are {len(assistant_texts)} responses.",
            )

        _, text_to_copy = assistant_texts[response_index]

        # Copy to clipboard via context
        clipboard = context.get("_clipboard")
        if clipboard and callable(clipboard):
            try:
                clipboard(text_to_copy)
                return CommandResult(
                    type="text",
                    value="Copied to clipboard!",
                )
            except Exception:
                pass

        return CommandResult(
            type="text",
            value=f"Response:\n{text_to_copy}",
        )


# =============================================================================
# Registry
# =============================================================================


def get_all_commands() -> list[BaseCommand]:
    """Get all copy-related commands.

    Returns:
        List of copy command instances.
    """
    return [CopyCommand()]


def register_builtin_commands(registry: Any) -> None:
    """Register copy commands with a command registry.

    Args:
        registry: Command registry with a register() method.
    """
    for cmd in get_all_commands():
        registry.register(cmd)
