"""Sandbox toggle command for Claude Code.

Configure sandboxing for bash commands.

TypeScript equivalent: src/commands/sandbox-toggle/index.ts, src/commands/sandbox-toggle/sandbox-toggle.tsx
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .base import BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass

# Terminals that natively support CSI u / Kitty keyboard protocol
NATIVE_CSIU_TERMINALS = {
    "ghostty": "Ghostty",
    "kitty": "Kitty",
    "iTerm.app": "iTerm2",
    "WezTerm": "WezTerm",
}


@dataclass
class SandboxToggleCommand(BaseCommand):
    """Configure sandboxing for bash commands.

    TypeScript equivalent: src/commands/sandbox-toggle/index.ts, src/commands/sandbox-toggle/sandbox-toggle.tsx
    """

    name: str = "sandbox"
    aliases: list[str] = field(default_factory=list)
    description: str = "sandbox disabled (\u23ce to configure)"
    argument_hint: str | None = 'exclude "command pattern"'
    command_type = CommandType.LOCAL
    immediate: bool = True
    source: str = "builtin"

    def __post_init__(self) -> None:
        self._all_names: set[str] = {self.name, *self.aliases}
        self._update_description()

    def _update_description(self) -> None:
        """Update the description based on sandbox status."""
        enabled = self._is_sandboxing_enabled()
        auto_allow = self._is_auto_allow_enabled()
        has_deps = self._check_dependencies()

        if not has_deps:
            icon = "(!)"
        elif enabled:
            icon = "[+]"
        else:
            icon = "[ ]"

        status = "sandbox disabled"
        if enabled:
            status = "sandbox enabled"
            if auto_allow:
                status = "sandbox enabled (auto-allow)"

        self.description = f"{icon} {status} (\u23ce to configure)"

    def _is_sandboxing_enabled(self) -> bool:
        """Check if sandboxing is currently enabled."""
        return False  # Default to disabled unless configured

    def _is_auto_allow_enabled(self) -> bool:
        """Check if auto-allow is enabled."""
        return False

    def _check_dependencies(self) -> bool:
        """Check if sandbox dependencies are available."""
        # Check if we have the required tools
        return shutil.which("sandbox-exec") is not None if os.uname().sysname == "Darwin" else True

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the sandbox command.

        Shows sandbox configuration or handles subcommands.
        """
        trimmed_args = args.strip()

        if not trimmed_args:
            # Show status
            return await self._show_status()

        # Handle subcommands
        parts = trimmed_args.split(" ", 1)
        subcommand = parts[0]

        if subcommand == "exclude":
            return await self._handle_exclude(parts[1] if len(parts) > 1 else "")
        else:
            return CommandResult(
                type="text",
                value=f"Error: Unknown subcommand \"{subcommand}\". Available subcommand: exclude",
            )

    async def _show_status(self) -> CommandResult:
        """Show sandbox configuration status."""
        self._update_description()

        # Check dependencies
        has_deps = self._check_dependencies()
        if not has_deps:
            return CommandResult(
                type="text",
                value="Sandbox: Dependencies not found. sandbox-exec may not be available.",
            )

        return CommandResult(
            type="text",
            value=self.description,
        )

    async def _handle_exclude(self, pattern: str) -> CommandResult:
        """Handle the 'exclude' subcommand."""
        if not pattern:
            return CommandResult(
                type="text",
                value='Error: Please provide a command pattern to exclude (e.g., /sandbox exclude "npm run test:*")',
            )

        # Remove quotes if present
        clean_pattern = pattern.strip().strip("'\"")

        if not clean_pattern:
            return CommandResult(
                type="text",
                value='Error: Please provide a valid command pattern to exclude.',
            )

        # Add to excluded commands
        success = self._add_excluded_command(clean_pattern)

        if success:
            return CommandResult(
                type="text",
                value=f"Added \"{clean_pattern}\" to excluded commands.",
            )
        else:
            return CommandResult(
                type="text",
                value="Could not save excluded commands setting.",
            )

    def _add_excluded_command(self, pattern: str) -> bool:
        """Add a command pattern to the excluded list."""
        try:
            # Try to find the local settings file
            settings_path = self._find_local_settings_path()
            if settings_path is None:
                return False

            import json

            # Read existing settings
            settings: dict[str, Any] = {}
            if settings_path.exists():
                try:
                    with open(settings_path, encoding="utf-8") as f:
                        settings = json.load(f)
                except (OSError, json.JSONDecodeError):
                    settings = {}

            # Add to excludedCommands
            excluded = settings.get("excludedCommands", [])
            if pattern not in excluded:
                excluded.append(pattern)
                settings["excludedCommands"] = excluded

                # Ensure parent directory exists
                settings_path.parent.mkdir(parents=True, exist_ok=True)

                with open(settings_path, "w", encoding="utf-8") as f:
                    json.dump(settings, f, indent=2)

            return True
        except OSError:
            return False

    def _find_local_settings_path(self) -> Path | None:
        """Find the local settings file path."""
        cwd = Path.cwd()
        candidates = [
            cwd / ".claude" / "settings.local.json",
            cwd / ".claude" / "settings.json",
            Path.home() / ".claude" / "settings.local.json",
        ]

        for path in candidates:
            if path.exists():
                return path

        # Return the first candidate as default
        return candidates[0]
