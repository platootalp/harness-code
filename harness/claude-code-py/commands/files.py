"""Files command for Claude Code.

Lists files in the current context.

TypeScript equivalent: src/commands/files/files.ts
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .base import BaseCommand, CommandResult

if TYPE_CHECKING:
    pass


def _is_ant_user() -> bool:
    """Check if current user is an ANT (developer).

    Returns:
        True if USER_TYPE environment variable is 'ant'.
    """
    return os.environ.get("USER_TYPE") == "ant"


@dataclass
class FilesCommand(BaseCommand):
    """Show files in the current context.

    TypeScript equivalent: src/commands/files/files.ts
    """

    name: str = "files"
    description: str = "Show files in the current context"
    availability: list[str] | None = None  # Only available for USER_TYPE === 'ant'
    supports_non_interactive: bool = True

    def __post_init__(self) -> None:
        # Build lookup set for aliases
        self._all_names: set[str] = {self.name}
        # Hide from non-ANT users
        self.is_hidden = not _is_ant_user()

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the files command."""
        read_file_state = context.get("readFileState")
        files: list[str] = []

        if read_file_state and hasattr(read_file_state, "__iter__"):
            files = list(read_file_state)

        if not files:
            return CommandResult(
                type="text",
                value="No files in context.",
            )

        # Get relative paths from cwd
        cwd = context.get("cwd", ".")
        try:
            from pathlib import Path
            rel_files = []
            for f in files:
                try:
                    rel = str(Path(f).relative_to(Path(cwd)))
                    rel_files.append(rel)
                except ValueError:
                    rel_files.append(f)
        except Exception:
            rel_files = files

        return CommandResult(
            type="text",
            value="Files in context:\n" + "\n".join(sorted(rel_files)),
        )
