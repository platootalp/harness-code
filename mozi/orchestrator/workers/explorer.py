"""Explorer worker for Mozi orchestrator.

Responsible for exploring the codebase, searching for files,
and gathering information about the project structure.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mozi.orchestrator.state import TodoItem


class ExplorerWorker:
    """Worker that explores the codebase and provides information.

    Responsible for:
    - Searching the codebase for relevant files
    - Getting file information (size, type, etc.)
    - Building a map of the project structure
    """

    def __init__(self) -> None:
        """Initialize the explorer worker."""
        self._search_results: list[dict[str, Any]] = []

    async def execute(
        self,
        todo: TodoItem,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute the explorer task.

        Args:
            todo: The todo item to process.
            context: Optional context information.

        Returns:
            Execution result with search results and file info.
        """
        context = context or {}
        action = context.get("action", "search_codebase")
        result: dict[str, Any]

        if action == "search_codebase":
            result = await self.search_codebase(
                context.get("query", ""),
                context.get("path", "."),
                context.get("file_patterns", []),
            )
        elif action == "get_file_info":
            result = await self.get_file_info(context.get("file_path", ""))
        elif action == "explore_structure":
            result = await self.explore_structure(context.get("path", "."))
        else:
            result = {"status": "unknown_action", "action": action}

        return result

    async def search_codebase(
        self,
        query: str,
        path: str = ".",
        file_patterns: list[str] | None = None,
    ) -> dict[str, Any]:
        """Search the codebase for matching files or content.

        Args:
            query: Search query string.
            path: Root path to search from.
            file_patterns: Optional list of file patterns to match.

        Returns:
            Search results with matching files and line numbers.
        """
        self._search_results = []
        results: list[dict[str, Any]] = []
        search_path = Path(path).resolve()

        if not search_path.exists():
            return {
                "status": "error",
                "message": f"Path does not exist: {path}",
                "results": [],
            }

        patterns = file_patterns or ["*.py", "*.ts", "*.js", "*.json"]

        for pattern in patterns:
            for file_path in search_path.rglob(pattern):
                if self._is_hidden_or_ignored(file_path):
                    continue
                if query in file_path.name:
                    results.append(
                        {
                            "file": str(file_path),
                            "type": "filename_match",
                            "match": query,
                        }
                    )
                elif query in str(file_path):
                    results.append(
                        {
                            "file": str(file_path),
                            "type": "path_match",
                            "match": query,
                        }
                    )

        self._search_results = results
        return {
            "status": "success",
            "query": query,
            "path": str(search_path),
            "results": results,
            "count": len(results),
        }

    async def get_file_info(self, file_path: str) -> dict[str, Any]:
        """Get information about a specific file.

        Args:
            file_path: Path to the file.

        Returns:
            File information including size, type, and metadata.
        """
        path = Path(file_path).resolve()

        if not path.exists():
            return {
                "status": "error",
                "message": f"File not found: {file_path}",
            }

        if not path.is_file():
            return {
                "status": "error",
                "message": f"Path is not a file: {file_path}",
            }

        stat = path.stat()
        suffix = path.suffix.lower()

        file_type = "unknown"
        if suffix in {".py"}:
            file_type = "python"
        elif suffix in {".ts", ".tsx"}:
            file_type = "typescript"
        elif suffix in {".js", ".jsx"}:
            file_type = "javascript"
        elif suffix in {".json"}:
            file_type = "json"
        elif suffix in {".md"}:
            file_type = "markdown"
        elif suffix in {".txt", ".log"}:
            file_type = "text"

        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()
            line_count = len(content.splitlines())
            char_count = len(content)
        except Exception:
            content = ""
            line_count = 0
            char_count = 0

        return {
            "status": "success",
            "file_path": str(path),
            "name": path.name,
            "size": stat.st_size,
            "file_type": file_type,
            "extension": suffix,
            "line_count": line_count,
            "char_count": char_count,
            "modified": stat.st_mtime,
            "is_readable": bool(content),
        }

    async def explore_structure(
        self,
        path: str = ".",
        max_depth: int = 3,
    ) -> dict[str, Any]:
        """Explore the directory structure.

        Args:
            path: Root path to explore.
            max_depth: Maximum directory depth to traverse.

        Returns:
            Directory structure information.
        """
        root_path = Path(path).resolve()

        if not root_path.exists():
            return {
                "status": "error",
                "message": f"Path does not exist: {path}",
            }

        structure: dict[str, Any] = {
            "name": root_path.name,
            "path": str(root_path),
            "type": "directory",
        }

        if max_depth > 0:
            children: list[dict[str, Any]] = []
            try:
                for item in sorted(root_path.iterdir()):
                    if self._is_hidden_or_ignored(item):
                        continue
                    if item.is_dir():
                        children.append(
                            {
                                "name": item.name,
                                "path": str(item),
                                "type": "directory",
                            }
                        )
                    else:
                        children.append(
                            {
                                "name": item.name,
                                "path": str(item),
                                "type": "file",
                                "size": item.stat().st_size,
                            }
                        )
            except PermissionError:
                children = [{"error": "Permission denied"}]

            structure["children"] = children

            if max_depth > 1:
                for child in children:
                    if child["type"] == "directory":
                        child["children"] = (
                            await self.explore_structure(child["path"], max_depth - 1)
                        ).get("children", [])

        return {
            "status": "success",
            "structure": structure,
            "max_depth": max_depth,
        }

    def _is_hidden_or_ignored(self, path: Path) -> bool:
        """Check if a path should be ignored.

        Args:
            path: Path to check.

        Returns:
            True if path should be ignored.
        """
        ignored_names = {
            "__pycache__",
            ".git",
            ".venv",
            "node_modules",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            ".claude",
            ".env",
            ".DS_Store",
        }
        ignored_prefixes = (".", "test_", "_")

        if path.name in ignored_names:
            return True
        if path.name.startswith(ignored_prefixes) and path.suffix in {".py", ".ts", ".js"}:
            if not path.name.startswith("test_"):
                return True
        return False

    def get_last_search_results(self) -> list[dict[str, Any]]:
        """Get the results from the last search operation."""
        return self._search_results
