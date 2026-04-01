"""Tests for the explorer worker."""

from __future__ import annotations

import pytest

from mozi.orchestrator.state import TodoItem, TodoStatus
from mozi.orchestrator.workers.explorer import ExplorerWorker


@pytest.fixture
def explorer() -> ExplorerWorker:
    """Create an ExplorerWorker instance."""
    return ExplorerWorker()


@pytest.fixture
def sample_todo() -> TodoItem:
    """Create a sample todo item."""
    return TodoItem(
        id="test-1",
        description="Explore test",
        status=TodoStatus.PENDING,
    )


class TestExplorerWorker:
    """Tests for ExplorerWorker."""

    @pytest.mark.asyncio
    async def test_execute_unknown_action(
        self, explorer: ExplorerWorker, sample_todo: TodoItem
    ) -> None:
        """Test execute with unknown action."""
        result = await explorer.execute(sample_todo, {"action": "unknown"})
        assert result["status"] == "unknown_action"

    @pytest.mark.asyncio
    async def test_search_codebase_empty_query(self, explorer: ExplorerWorker) -> None:
        """Test search with empty query."""
        result = await explorer.search_codebase("", ".")
        assert result["status"] == "success"
        assert "results" in result

    @pytest.mark.asyncio
    async def test_search_codebase_nonexistent_path(self, explorer: ExplorerWorker) -> None:
        """Test search with nonexistent path."""
        result = await explorer.search_codebase("test", "/nonexistent/path")
        assert result["status"] == "error"
        assert "does not exist" in result["message"]

    @pytest.mark.asyncio
    async def test_search_codebase_with_patterns(self, explorer: ExplorerWorker) -> None:
        """Test search with file patterns."""
        result = await explorer.search_codebase("test", ".", ["*.py"])
        assert result["status"] == "success"
        assert result["query"] == "test"
        assert "results" in result
        assert "count" in result

    @pytest.mark.asyncio
    async def test_get_file_info_nonexistent(self, explorer: ExplorerWorker) -> None:
        """Test get_file_info with nonexistent file."""
        result = await explorer.get_file_info("/nonexistent/file.txt")
        assert result["status"] == "error"
        assert "not found" in result["message"]

    @pytest.mark.asyncio
    async def test_explore_structure_success(self, explorer: ExplorerWorker) -> None:
        """Test explore_structure with current directory."""
        result = await explorer.explore_structure(".")
        assert result["status"] == "success"
        assert "structure" in result

    @pytest.mark.asyncio
    async def test_explore_structure_with_depth(self, explorer: ExplorerWorker) -> None:
        """Test explore_structure with depth limit."""
        result = await explorer.explore_structure(".", max_depth=1)
        assert result["status"] == "success"
        assert result["max_depth"] == 1

    @pytest.mark.asyncio
    async def test_explore_structure_nonexistent_path(self, explorer: ExplorerWorker) -> None:
        """Test explore_structure with nonexistent path."""
        result = await explorer.explore_structure("/nonexistent/path")
        assert result["status"] == "error"

    def test_is_hidden_or_ignored(self, explorer: ExplorerWorker) -> None:
        """Test hidden/ignored file detection."""
        from pathlib import Path

        assert explorer._is_hidden_or_ignored(Path("__pycache__"))
        assert explorer._is_hidden_or_ignored(Path(".git"))
        assert explorer._is_hidden_or_ignored(Path(".env"))
        assert not explorer._is_hidden_or_ignored(Path("test_file.py"))
        assert not explorer._is_hidden_or_ignored(Path("main.py"))
        assert explorer._is_hidden_or_ignored(Path("_private.py"))

    def test_get_last_search_results_empty(self, explorer: ExplorerWorker) -> None:
        """Test getting search results before any search."""
        results = explorer.get_last_search_results()
        assert results == []
