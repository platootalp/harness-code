"""Command history navigation for Claude Code.

Provides history navigation functions that wrap the REPL state helpers.
Used by the CLI to navigate through previously entered commands.

TypeScript equivalent: src/cli/history.ts
"""

from __future__ import annotations

from .state import (
    REPLState,
    add_to_history,
    get_repl_state,
    history_next,
    history_previous,
)


class CommandHistory:
    """Command history navigator.

    Provides a class-based interface for navigating command history,
    with support for incremental search and history persistence.

    TypeScript equivalent: src/cli/history.ts CommandHistory class
    """

    def __init__(self, state: REPLState | None = None) -> None:
        """Initialize the history navigator.

        Args:
            state: Optional REPL state. Uses global state if not provided.
        """
        self._state = state or get_repl_state()
        self._search_prefix: str = ""
        self._search_results: list[str] = []

    @property
    def history(self) -> list[str]:
        """Get the command history.

        Returns:
            List of historical command strings.
        """
        return list(self._state.command_history)

    @property
    def current_index(self) -> int:
        """Get the current history index.

        Returns:
            Current index in history (-1 means at the end/current input).
        """
        return self._state.history_index

    def add(self, command: str) -> None:
        """Add a command to history.

        Args:
            command: Command string to add.
        """
        if command.strip():
            add_to_history(command)

    def previous(self) -> str | None:
        """Navigate to previous command in history.

        Returns:
            Previous command string, or None if at the beginning.
        """
        return history_previous()

    def next(self) -> str | None:
        """Navigate to next command in history.

        Returns:
            Next command string, or empty string if at the end.
        """
        return history_next()

    def start_search(self, prefix: str) -> list[str]:
        """Start an incremental search through history.

        Args:
            prefix: The prefix to search for.

        Returns:
            List of matching commands.
        """
        self._search_prefix = prefix
        self._search_results = [
            cmd
            for cmd in reversed(self._state.command_history)
            if cmd.startswith(prefix)
        ]
        return self._search_results

    def search_next(self) -> str | None:
        """Get the next search result.

        Returns:
            Next matching command, or None.
        """
        if not self._search_results:
            return None
        # Cycling through results
        return self._search_results[0] if self._search_results else None

    def search_previous(self) -> str | None:
        """Get the previous search result.

        Returns:
            Previous matching command, or None.
        """
        if not self._search_results:
            return None
        return self._search_results[-1] if self._search_results else None

    def reset_search(self) -> None:
        """Reset the incremental search state."""
        self._search_prefix = ""
        self._search_results = []

    def clear(self) -> None:
        """Clear all history."""
        self._state.command_history.clear()
        self._state.history_index = -1
        self.reset_search()

    def get_recent(self, count: int = 10) -> list[str]:
        """Get the most recent N commands.

        Args:
            count: Number of recent commands to return.

        Returns:
            List of recent command strings.
        """
        return list(self._state.command_history[-count:])

    def duplicate_last(self) -> str | None:
        """Get the last executed command for redo.

        Returns:
            The most recent command, or None.
        """
        if not self._state.command_history:
            return None
        return self._state.command_history[-1]
