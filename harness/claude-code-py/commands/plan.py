"""Plan command for Claude Code.

Enables plan mode or views the current session plan.

TypeScript equivalent: src/commands/plan/index.ts, src/commands/plan/plan.tsx
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .base import BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


@dataclass
class PlanCommand(BaseCommand):
    """Enable plan mode or view the current session plan.

    TypeScript equivalent: src/commands/plan/index.ts, src/commands/plan/plan.tsx
    """

    name: str = "plan"
    aliases: list[str] = field(default_factory=list)
    description: str = "Enable plan mode or view the current session plan"
    argument_hint: str | None = "[open|<description>]"
    command_type = CommandType.LOCAL
    source: str = "builtin"

    def __post_init__(self) -> None:
        self._all_names: set[str] = {self.name, *self.aliases}

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the plan command.

        If not in plan mode, enables it. If already in plan mode, shows
        the current plan content.
        """
        repl_state: Any = context.get("_repl_state")

        if repl_state is None:
            return CommandResult(
                type="text",
                value="Error: No active session found.",
            )

        trimmed_args = args.strip()
        arg_list = trimmed_args.split() if trimmed_args else []

        # Check if we should open the plan in an editor
        if arg_list and arg_list[0] == "open":
            return self._open_plan(trimmed_args)

        # Get the plan file path
        plan_path = self._get_plan_file_path()
        if plan_path:
            # Plan file exists - try to show its content
            content = self._read_plan_content(plan_path)
            if content:
                return CommandResult(
                    type="text",
                    value=f"Current Plan ({plan_path}):\n\n{content}\n\nUse /plan open to edit this plan in your editor.",
                )
            else:
                return CommandResult(
                    type="text",
                    value="Plan mode enabled. No plan file found yet.",
                )
        else:
            return CommandResult(
                type="text",
                value="Plan mode enabled. Use /plan open to create a plan.",
            )

    def _get_plan_file_path(self) -> str | None:
        """Get the path to the current plan file."""
        # Look for a plan file in common locations
        from pathlib import Path

        cwd = Path.cwd()
        candidates = [
            cwd / "PLAN.md",
            cwd / "plan.md",
            cwd / ".claude" / "PLAN.md",
            cwd / ".claude" / "plan.md",
        ]

        for path in candidates:
            if path.exists() and path.is_file():
                return str(path)
        return None

    def _read_plan_content(self, plan_path: str) -> str | None:
        """Read the plan content from a file."""
        try:
            with open(plan_path, encoding="utf-8") as f:
                content = f.read().strip()
                return content if content else None
        except OSError:
            return None

    def _open_plan(self, args: str) -> CommandResult:  # noqa: ARG002
        """Open the plan file in the user's editor."""
        plan_path = self._get_plan_file_path()

        if plan_path is None:
            # Create a default plan file
            from pathlib import Path

            plan_dir = Path.cwd() / ".claude"
            plan_dir.mkdir(parents=True, exist_ok=True)
            plan_path = str(plan_dir / "PLAN.md")

            # Write a template
            try:
                with open(plan_path, "w", encoding="utf-8") as f:
                    f.write("# Plan\n\n## Context\n\n[Describe what needs to be done]\n\n## Tasks\n\n- [ ] Task 1\n- [ ] Task 2\n\n## Notes\n\n[Additional notes]\n")
            except OSError:
                return CommandResult(
                    type="text",
                    value=f"Error: Could not create plan file at {plan_path}",
                )

        # Open in the default editor
        editor = self._get_editor()
        try:
            result = subprocess.run(
                [editor, plan_path],
                capture_output=True,
                timeout=10,
            )
            if result.returncode != 0:
                return CommandResult(
                    type="text",
                    value=f"Opened plan in editor: {plan_path}",
                )
            return CommandResult(
                type="text",
                value=f"Opened plan in editor: {plan_path}",
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return CommandResult(
                type="text",
                value=f"Plan file: {plan_path}\n\n(Editor '{editor}' not available. Open manually.)",
            )

    def _get_editor(self) -> str:
        """Get the user's preferred editor."""
        import os
        return os.environ.get("EDITOR") or os.environ.get("VISUAL") or "nano"

    def _set_plan_mode(self) -> None:
        """Enable plan mode in the session."""
        # This would set the tool permission context to plan mode
        # The actual implementation depends on the session state management
        pass
