"""Memory command for Claude Code.

Edit Claude memory files.

TypeScript equivalent: src/commands/memory/
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .base import Availability, BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


# =============================================================================
# Memory Command
# =============================================================================


@dataclass
class MemoryCommand(BaseCommand):
    """Edit Claude memory files.

    Provides access to Claude's memory files for viewing and editing.
    Memory files store persistent context across sessions.

    TypeScript equivalent: src/commands/memory/memory.tsx
    """

    name: str = "memory"
    aliases: list[str] = field(default_factory=list)
    description: str = "Edit Claude memory files"
    argument_hint: str | None = None
    command_type: CommandType = CommandType.LOCAL_JSX
    availability: list[str] = field(default_factory=lambda: [Availability.ALL.value])
    source: str = "builtin"

    def __post_init__(self) -> None:
        # Build lookup set for aliases
        self._all_names: set[str] = {self.name, *self.aliases}

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the memory command.

        Args:
            args: Optional argument (e.g., memory file path).
            context: Execution context.

        Returns:
            CommandResult with memory file information.
        """
        # Get memory file paths from context
        memory_paths: list[str] = context.get("memory_paths", [])

        # Determine which memory file to show
        target_file = args.strip() if args.strip() else None

        if not memory_paths:
            # Try to find default memory locations
            memory_paths = self._find_default_memory_paths()

        if not memory_paths:
            return CommandResult(
                type="text",
                value=(
                    "No memory files found.\n\n"
                    "Claude memory files are typically stored at:\n"
                    "  ~/.claude/memory/  (user memory)\n"
                    "  .claude/memory/    (project memory)\n\n"
                    "Use /memory <path> to edit a specific memory file."
                ),
            )

        # Filter by target if specified
        if target_file:
            matching = [p for p in memory_paths if target_file in p]
            if not matching:
                return CommandResult(
                    type="text",
                    value=f"Memory file not found: {target_file}\n"
                          f"Available memory files: {', '.join(memory_paths)}",
                )
            memory_paths = matching

        # Display memory file information
        lines = ["Claude Memory Files", ""]

        for path in memory_paths:
            if os.path.exists(path):
                try:
                    with open(path, encoding="utf-8") as f:
                        content = f.read()
                    size = len(content)
                    lines.append(f"## {path}")
                    lines.append(f"Size: {size} bytes")
                    lines.append("")
                    # Show content preview
                    preview = content[:500]
                    if len(content) > 500:
                        preview += "\n... (truncated)"
                    lines.append(preview)
                    lines.append("")
                    lines.append(f"Full path: {os.path.abspath(path)}")
                    lines.append("")
                except OSError as e:
                    lines.append(f"## {path}")
                    lines.append(f"Error reading: {e}")
                    lines.append("")
            else:
                lines.append(f"## {path}")
                lines.append("(file not found)")
                lines.append("")

        lines.extend([
            "-" * 40,
            "",
            "To edit a memory file, open it in your editor.",
        ])

        return CommandResult(type="text", value="\n".join(lines))

    def _find_default_memory_paths(self) -> list[str]:
        """Find default memory file locations.

        Returns:
            List of default memory file paths.
        """
        paths: list[str] = []

        # User memory directory
        home = os.path.expanduser("~")
        user_memory_dir = os.path.join(home, ".claude", "memory")
        if os.path.isdir(user_memory_dir):
            try:
                for entry in os.listdir(user_memory_dir):
                    if entry.endswith(".md"):
                        paths.append(os.path.join(user_memory_dir, entry))
            except OSError:
                pass

        # Project memory directory
        cwd = os.getcwd()
        project_memory_dir = os.path.join(cwd, ".claude", "memory")
        if os.path.isdir(project_memory_dir):
            try:
                for entry in os.listdir(project_memory_dir):
                    if entry.endswith(".md"):
                        paths.append(os.path.join(project_memory_dir, entry))
            except OSError:
                pass

        return paths


# =============================================================================
# Registry
# =============================================================================


def get_all_commands() -> list[BaseCommand]:
    """Get all memory-related commands.

    Returns:
        List of memory command instances.
    """
    return [MemoryCommand()]


def register_builtin_commands(registry: Any) -> None:
    """Register memory commands with a command registry.

    Args:
        registry: Command registry with a register() method.
    """
    for cmd in get_all_commands():
        registry.register(cmd)
