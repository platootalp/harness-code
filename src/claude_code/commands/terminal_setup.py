"""Terminal setup command for Claude Code.

Configure terminal key bindings for newlines.

TypeScript equivalent: src/commands/terminalSetup/index.ts, src/commands/terminalSetup/terminalSetup.tsx
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
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
class TerminalSetupCommand(BaseCommand):
    """Enable Option+Enter key binding for newlines and visual bell.

    TypeScript equivalent: src/commands/terminalSetup/index.ts
    """

    name: str = "terminal-setup"
    aliases: list[str] = field(default_factory=list)
    description: str = "Enable Option+Enter key binding for newlines and visual bell"
    command_type = CommandType.LOCAL
    source: str = "builtin"

    def __post_init__(self) -> None:
        self._all_names: set[str] = {self.name, *self.aliases}
        self._update_description()

    def _update_description(self) -> None:
        """Update description based on current terminal."""
        term = os.environ.get("TERM", "")
        term_program = os.environ.get("TERM_PROGRAM", "")

        if term_program in NATIVE_CSIU_TERMINALS or term in NATIVE_CSIU_TERMINALS:
            self.is_hidden = True
        else:
            self.is_hidden = False
            # Update description based on terminal type
            if term_program == "Apple_Terminal" or term == "xterm-256color":
                self.description = "Enable Option+Enter key binding for newlines and visual bell"
            else:
                self.description = "Install Shift+Enter key binding for newlines"

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the terminal-setup command.

        Shows instructions for configuring terminal key bindings.
        """
        term_program = os.environ.get("TERM_PROGRAM", "")
        term = os.environ.get("TERM", "")

        if term_program in NATIVE_CSIU_TERMINALS:
            terminal_name = NATIVE_CSIU_TERMINALS[term_program]
            return CommandResult(
                type="text",
                value=f"{terminal_name} natively supports CSI u mode. "
                f"Shift+Enter should already work for newlines.",
            )

        if term in NATIVE_CSIU_TERMINALS:
            terminal_name = NATIVE_CSIU_TERMINALS[term]
            return CommandResult(
                type="text",
                value=f"{terminal_name} natively supports CSI u mode. "
                f"Shift+Enter should already work for newlines.",
            )

        if term_program == "Apple_Terminal":
            return CommandResult(
                type="text",
                value=(
                    "Terminal Setup for Apple Terminal:\n\n"
                    "To enable Option+Enter for newlines:\n"
                    "1. Open Terminal > Settings > Keyboard\n"
                    "2. Enable 'Use Option as Meta key' (or similar)\n"
                    "3. For Option+Enter, you may need to create a custom key binding:\n"
                    "   - Go to Keyboard > Shortcuts > App Shortcuts\n"
                    "   - Add: Menu title: 'New Line' (or Enter character)\n"
                    "   - Key: Option+Return\n\n"
                    "Note: Visual bell may require terminal preferences."
                ),
            )

        # Generic instructions
        return CommandResult(
            type="text",
            value=(
                "Terminal Setup:\n\n"
                "To enable Shift+Enter or Option+Enter for newlines:\n"
                "- iTerm2: Preferences > Profiles > Keys > Key Mappings\n"
                "  Add: Shift+Return or Option+Return -> Send Escape Sequence: \\n\n"
                "- Kitty: Should work natively with CSI u protocol\n"
                "- WezTerm: Should work natively with CSI u protocol\n"
                "- Other terminals: Check your terminal's key binding settings\n"
            ),
        )
