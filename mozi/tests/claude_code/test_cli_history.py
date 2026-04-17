"""
Tests for cli/history.py - command history navigation.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from claude_code.cli.history import CommandHistory


class MockREPLState:
    """Mock REPLState for testing."""

    def __init__(self) -> None:
        self.command_history: list[str] = []
        self.history_index: int = -1


class TestCommandHistoryInit:
    """Tests for CommandHistory initialization."""

    def test_default_init(self) -> None:
        """CommandHistory initializes with empty history."""
        state = MockREPLState()
        ch = CommandHistory(state=state)
        assert ch.history == []
        assert ch.current_index == -1

    def test_init_with_history(self) -> None:
        """CommandHistory initializes with existing history."""
        state = MockREPLState()
        state.command_history = ["cmd1", "cmd2"]
        state.history_index = 0
        ch = CommandHistory(state=state)
        assert ch.history == ["cmd1", "cmd2"]
        assert ch.current_index == 0


class TestCommandHistoryAdd:
    """Tests for add() method."""

    def test_add_command(self) -> None:
        """add() calls add_to_history with the command."""
        with patch("claude-code-py.cli.history.add_to_history") as mock_add:
            ch = CommandHistory(state=MockREPLState())
            ch.add("hello world")
            mock_add.assert_called_once_with("hello world")

    def test_add_empty_command_not_called(self) -> None:
        """add() does not call add_to_history for empty commands."""
        with patch("claude-code-py.cli.history.add_to_history") as mock_add:
            ch = CommandHistory(state=MockREPLState())
            ch.add("")
            ch.add("   ")
            ch.add("  \t  ")
            mock_add.assert_not_called()


class TestCommandHistorySearch:
    """Tests for history search functionality."""

    def test_start_search_finds_matches(self) -> None:
        """start_search() returns commands matching the prefix."""
        state = MockREPLState()
        state.command_history = ["git commit", "git push", "npm install", "git status"]
        ch = CommandHistory(state=state)
        results = ch.start_search("git ")
        assert results == ["git status", "git push", "git commit"]

    def test_start_search_empty_prefix(self) -> None:
        """start_search() with empty prefix returns all commands."""
        state = MockREPLState()
        state.command_history = ["a", "b", "c"]
        ch = CommandHistory(state=state)
        results = ch.start_search("")
        assert results == ["c", "b", "a"]

    def test_start_search_no_matches(self) -> None:
        """start_search() returns empty list when no matches."""
        state = MockREPLState()
        state.command_history = ["git commit", "npm install"]
        ch = CommandHistory(state=state)
        results = ch.start_search("xyz")
        assert results == []

    def test_search_next_returns_first_result(self) -> None:
        """search_next() returns the first search result."""
        state = MockREPLState()
        state.command_history = ["git commit", "git push", "git status"]
        ch = CommandHistory(state=state)
        ch.start_search("git ")
        result = ch.search_next()
        assert result == "git status"

    def test_search_next_empty_when_no_search(self) -> None:
        """search_next() returns None when no search has been started."""
        state = MockREPLState()
        ch = CommandHistory(state=state)
        assert ch.search_next() is None

    def test_search_previous_returns_last_result(self) -> None:
        """search_previous() returns the last search result."""
        state = MockREPLState()
        state.command_history = ["git commit", "git push", "git status"]
        ch = CommandHistory(state=state)
        ch.start_search("git ")
        result = ch.search_previous()
        assert result == "git commit"

    def test_search_previous_empty_when_no_search(self) -> None:
        """search_previous() returns None when no search has been started."""
        state = MockREPLState()
        ch = CommandHistory(state=state)
        assert ch.search_previous() is None

    def test_reset_search_clears_state(self) -> None:
        """reset_search() clears the search prefix and results."""
        state = MockREPLState()
        state.command_history = ["git commit", "git push"]
        ch = CommandHistory(state=state)
        ch.start_search("git ")
        assert len(ch._search_results) == 2
        ch.reset_search()
        assert ch._search_prefix == ""
        assert ch._search_results == []


class TestCommandHistoryClear:
    """Tests for clear() method."""

    def test_clear_removes_all_commands(self) -> None:
        """clear() removes all commands from history."""
        state = MockREPLState()
        state.command_history = ["cmd1", "cmd2", "cmd3"]
        state.history_index = 1
        ch = CommandHistory(state=state)
        ch.clear()
        assert state.command_history == []
        assert state.history_index == -1

    def test_clear_resets_search(self) -> None:
        """clear() also resets search state."""
        state = MockREPLState()
        state.command_history = ["git commit"]
        ch = CommandHistory(state=state)
        ch.start_search("git ")
        ch.clear()
        assert ch._search_prefix == ""
        assert ch._search_results == []


class TestCommandHistoryGetRecent:
    """Tests for get_recent() method."""

    def test_get_recent_default_count(self) -> None:
        """get_recent() returns last 10 commands by default."""
        state = MockREPLState()
        state.command_history = [f"cmd{i}" for i in range(15)]
        ch = CommandHistory(state=state)
        recent = ch.get_recent()
        assert len(recent) == 10
        assert recent[0] == "cmd5"
        assert recent[-1] == "cmd14"

    def test_get_recent_custom_count(self) -> None:
        """get_recent() returns the specified number of commands."""
        state = MockREPLState()
        state.command_history = ["a", "b", "c", "d", "e"]
        ch = CommandHistory(state=state)
        recent = ch.get_recent(3)
        assert recent == ["c", "d", "e"]

    def test_get_recent_fewer_than_count(self) -> None:
        """get_recent() returns all commands when fewer than count exist."""
        state = MockREPLState()
        state.command_history = ["a", "b"]
        ch = CommandHistory(state=state)
        recent = ch.get_recent(10)
        assert recent == ["a", "b"]

    def test_get_recent_empty_history(self) -> None:
        """get_recent() returns empty list when history is empty."""
        state = MockREPLState()
        ch = CommandHistory(state=state)
        recent = ch.get_recent()
        assert recent == []


class TestCommandHistoryDuplicateLast:
    """Tests for duplicate_last() method."""

    def test_duplicate_last_returns_last_command(self) -> None:
        """duplicate_last() returns the most recent command."""
        state = MockREPLState()
        state.command_history = ["cmd1", "cmd2", "cmd3"]
        ch = CommandHistory(state=state)
        assert ch.duplicate_last() == "cmd3"

    def test_duplicate_last_empty_history(self) -> None:
        """duplicate_last() returns None when history is empty."""
        state = MockREPLState()
        ch = CommandHistory(state=state)
        assert ch.duplicate_last() is None
