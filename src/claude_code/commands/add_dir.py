"""
Add directory command for Claude Code.

Adds a directory to the workspace.

TypeScript equivalent: src/commands/add-dir/add-dir.tsx
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .base import Availability, BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


@dataclass
class AddDirCommand(BaseCommand):
    """Add a directory to the workspace.

    Adds a directory as a working directory for Claude Code,
    allowing the agent to read and modify files in that directory.
    """

    name: str = "add-dir"
    description: str = "Add a directory to the workspace"
    argument_hint: str | None = "<path>"
    availability: list[str] = field(
        default_factory=lambda: [Availability.ALL.value]
    )
    command_type: CommandType = CommandType.LOCAL_JSX
    supports_non_interactive: bool = False

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the add-dir command."""
        directory_path = args.strip()

        if not directory_path:
            # Show the directory input form
            return CommandResult(
                type="jsx",
                value=None,
                node={
                    "type": "AddWorkspaceDirectory",
                    "props": {
                        "onAddDirectory": None,  # Set by TUI layer
                        "onCancel": None,  # Set by TUI layer
                    },
                },
            )

        # Validate the directory path
        abs_path = os.path.abspath(directory_path)

        if not os.path.exists(abs_path):
            return CommandResult(
                type="text",
                value=f'Directory not found: {directory_path}\n'
                + "Use /add-dir <path> to add a directory to the workspace.",
            )

        if not os.path.isdir(abs_path):
            return CommandResult(
                type="text",
                value=f'Not a directory: {directory_path}',
            )

        # Show confirmation with the validated path
        return CommandResult(
            type="jsx",
            value=None,
            node={
                "type": "AddWorkspaceDirectory",
                "props": {
                    "directoryPath": abs_path,
                    "onAddDirectory": None,  # Set by TUI layer
                    "onCancel": None,  # Set by TUI layer
                },
            },
        )
