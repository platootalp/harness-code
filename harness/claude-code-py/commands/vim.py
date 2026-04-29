"""Vim command for Claude Code.

Toggles between Vim and Normal editing modes.

TypeScript equivalent: src/commands/vim/vim.ts
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .base import BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass
class VimCommand(BaseCommand):
    """Toggle between Vim and Normal editing modes.

    TypeScript equivalent: src/commands/vim/vim.ts
    """

    name: str = "vim"
    description: str = "Toggle between Vim and Normal editing modes"
    command_type: CommandType = CommandType.LOCAL
    source: str = "builtin"
    supports_non_interactive: bool = False

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the vim command."""
        # Get current editor mode from config
        config: dict[str, Any] = context.get("_config", {})
        current_mode = config.get("editorMode", "normal")

        # emacs falls back to normal
        if current_mode == "emacs":
            current_mode = "normal"

        # Toggle mode
        new_mode = "vim" if current_mode == "normal" else "normal"

        # Save to config
        if "_set_config" in context and callable(context["_set_config"]):
            try:
                context["_set_config"]({"editorMode": new_mode})
            except Exception as e:
                logger.warning("Failed to save editor mode: %s", e)

        if new_mode == "vim":
            msg = (
                "Editor mode set to vim. "
                "Use Escape key to toggle between INSERT and NORMAL modes."
            )
        else:
            msg = "Editor mode set to normal. Using standard (readline) keyboard bindings."

        return CommandResult(type="text", value=msg)
