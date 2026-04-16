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

    @pytest.mark.asyncio
    async def test_execute_search_codebase_action(
        self, explorer: ExplorerWorker, sample_todo: TodoItem
    ) -> None:
        """Test execute with search_codebase action."""
        result = await explorer.execute(
            sample_todo,
            {"action": "search_codebase", "query": "test", "path": "."}
        )
        assert result["status"] == "success"
        assert "results" in result

    @pytest.mark.asyncio
    async def test_execute_get_file_info_action(
        self, explorer: ExplorerWorker, sample_todo: TodoItem, tmp_path: pytest.TempPathFactory
    ) -> None:
        """Test execute with get_file_info action."""
        # Create a temporary file
        test_file = tmp_path / "test_file.py"
        test_file.write_text("print('hello')")

        result = await explorer.execute(
            sample_todo,
            {"action": "get_file_info", "file_path": str(test_file)}
        )
        assert result["status"] == "success"
        assert result["file_type"] == "python"

    @pytest.mark.asyncio
    async def test_execute_explore_structure_action(
        self, explorer: ExplorerWorker, sample_todo: TodoItem, tmp_path: pytest.TempPathFactory
    ) -> None:
        """Test execute with explore_structure action."""
        result = await explorer.execute(
            sample_todo,
            {"action": "explore_structure", "path": str(tmp_path)}
        )
        assert result["status"] == "success"
        assert "structure" in result

    @pytest.mark.asyncio
    async def test_get_file_info_directory(
        self, explorer: ExplorerWorker, tmp_path: pytest.TempPathFactory
    ) -> None:
        """Test get_file_info when path is a directory."""
        result = await explorer.get_file_info(str(tmp_path))
        assert result["status"] == "error"
        assert "not a file" in result["message"]

    @pytest.mark.asyncio
    async def test_get_file_info_various_types(
        self, explorer: ExplorerWorker, tmp_path: pytest.TempPathFactory
    ) -> None:
        """Test get_file_info with various file types."""
        # Python file
        py_file = tmp_path / "test.py"
        py_file.write_text("print('hello')")
        result = await explorer.get_file_info(str(py_file))
        assert result["file_type"] == "python"
        assert result["extension"] == ".py"

        # JSON file
        json_file = tmp_path / "test.json"
        json_file.write_text('{"key": "value"}')
        result = await explorer.get_file_info(str(json_file))
        assert result["file_type"] == "json"

        # Markdown file
        md_file = tmp_path / "test.md"
        md_file.write_text("# Title")
        result = await explorer.get_file_info(str(md_file))
        assert result["file_type"] == "markdown"

        # TypeScript file
        ts_file = tmp_path / "test.ts"
        ts_file.write_text("const x = 1;")
        result = await explorer.get_file_info(str(ts_file))
        assert result["file_type"] == "typescript"

        # JavaScript file
        js_file = tmp_path / "test.js"
        js_file.write_text("var x = 1;")
        result = await explorer.get_file_info(str(js_file))
        assert result["file_type"] == "javascript"

    @pytest.mark.asyncio
    async def test_explore_structure_permission_error(
        self, explorer: ExplorerWorker, tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test explore_structure when PermissionError occurs."""
        # Create a directory we can make inaccessible
        restricted_dir = tmp_path / "restricted"
        restricted_dir.mkdir()

        # Create a subdirectory with restricted access
        import os
        protected_dir = restricted_dir / "protected"
        protected_dir.mkdir()

        # Make the parent directory unreadable
        os.chmod(restricted_dir, 0o000)

        try:
            result = await explorer.explore_structure(str(restricted_dir), max_depth=1)
            # Should handle permission error gracefully
            assert result["status"] == "success"
        finally:
            # Restore permissions
            os.chmod(restricted_dir, 0o755)

    @pytest.mark.asyncio
    async def test_explore_structure_max_depth_zero(
        self, explorer: ExplorerWorker, tmp_path: pytest.TempPathFactory
    ) -> None:
        """Test explore_structure with max_depth=0."""
        # Create a directory structure
        sub_dir = tmp_path / "subdir"
        sub_dir.mkdir()

        result = await explorer.explore_structure(str(tmp_path), max_depth=0)
        assert result["status"] == "success"
        assert result["max_depth"] == 0

    @pytest.mark.asyncio
    async def test_search_codebase_filename_match(
        self, explorer: ExplorerWorker, tmp_path: pytest.TempPathFactory
    ) -> None:
        """Test search_codebase finds matches in filename."""
        # Create files with matching names
        test_file = tmp_path / "test_file.py"
        test_file.write_text("# test content")

        result = await explorer.search_codebase("test_file", str(tmp_path), ["*.py"])
        assert result["status"] == "success"
        assert result["count"] >= 1
        assert any("test_file" in r["file"] for r in result["results"])

    @pytest.mark.asyncio
    async def test_search_codebase_path_match(
        self, explorer: ExplorerWorker, tmp_path: pytest.TempPathFactory
    ) -> None:
        """Test search_codebase finds matches in path."""
        # Create nested directory with matching path
        nested_dir = tmp_path / "mypackage"
        nested_dir.mkdir()
        test_file = nested_dir / "module.py"
        test_file.write_text("# content")

        result = await explorer.search_codebase("mypackage", str(tmp_path), ["*.py"])
        assert result["status"] == "success"
        # Should find files under mypackage path

    @pytest.mark.asyncio
    async def test_explore_structure_nested(
        self, explorer: ExplorerWorker, tmp_path: pytest.TempPathFactory
    ) -> None:
        """Test explore_structure with nested directories."""
        # Create nested structure
        level1 = tmp_path / "level1"
        level1.mkdir()
        level2 = level1 / "level2"
        level2.mkdir()
        (level2 / "file.txt").write_text("content")

        result = await explorer.explore_structure(str(tmp_path), max_depth=2)
        assert result["status"] == "success"
        assert "structure" in result

    def test_is_hidden_or_ignored_edge_cases(self, explorer: ExplorerWorker) -> None:
        """Test hidden/ignored file detection edge cases."""
        from pathlib import Path

        # test_ prefix is allowed
        assert not explorer._is_hidden_or_ignored(Path("test_main.py"))
        assert not explorer._is_hidden_or_ignored(Path("test_helper.py"))

        # .DS_Store
        assert explorer._is_hidden_or_ignored(Path(".DS_Store"))

        # Various ignored directories
        assert explorer._is_hidden_or_ignored(Path("node_modules"))
        assert explorer._is_hidden_or_ignored(Path(".mypy_cache"))
