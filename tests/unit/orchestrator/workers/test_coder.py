"""Tests for the coder worker."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from mozi.orchestrator.state import TodoItem, TodoStatus
from mozi.orchestrator.workers.coder import CoderWorker


@pytest.fixture
def coder() -> CoderWorker:
    """Create a CoderWorker instance."""
    return CoderWorker()


@pytest.fixture
def sample_todo() -> TodoItem:
    """Create a sample todo item."""
    return TodoItem(
        id="test-1",
        description="Code test",
        status=TodoStatus.PENDING,
    )


@pytest.fixture
def temp_file() -> Path:
    """Create a temporary file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("# Original content\nprint('hello')\n")
        return Path(f.name)


class TestCoderWorker:
    """Tests for CoderWorker."""

    @pytest.mark.asyncio
    async def test_execute_unknown_action(self, coder: CoderWorker, sample_todo: TodoItem) -> None:
        """Test execute with unknown action."""
        result = await coder.execute(sample_todo, {"action": "unknown"})
        assert result["status"] == "unknown_action"

    @pytest.mark.asyncio
    async def test_apply_diff_nonexistent_file(self, coder: CoderWorker) -> None:
        """Test apply_diff with nonexistent file."""
        result = await coder.apply_diff("/nonexistent/file.py", "some diff")
        assert result["status"] == "error"
        assert result["applied"] is False

    @pytest.mark.asyncio
    async def test_apply_diff_dry_run(self, coder: CoderWorker, temp_file: Path) -> None:
        """Test apply_diff in dry run mode."""
        diff = f"""--- {temp_file}
+++ {temp_file}
@@ -1,2 +1,2 @@
 # Original content
-print('hello')
+print('world')
"""
        result = await coder.apply_diff(str(temp_file), diff, dry_run=True)
        assert result["status"] == "dry_run"
        assert result["applied"] is False

        with open(temp_file) as f:
            content = f.read()
        assert "hello" in content

    @pytest.mark.asyncio
    async def test_validate_change_nonexistent(self, coder: CoderWorker) -> None:
        """Test validate_change with nonexistent file."""
        result = await coder.validate_change("/nonexistent/file.py", "some code")
        assert result["status"] == "error"
        assert result["valid"] is False

    @pytest.mark.asyncio
    async def test_validate_change_python_syntax_error(
        self, coder: CoderWorker, temp_file: Path
    ) -> None:
        """Test validate_change with syntax error."""
        result = await coder.validate_change(str(temp_file), "def func(:\n    pass")
        assert result["valid"] is False
        assert any("Syntax error" in issue for issue in result["issues"])

    @pytest.mark.asyncio
    async def test_validate_change_dangerous_patterns(
        self, coder: CoderWorker, temp_file: Path
    ) -> None:
        """Test validate_change with dangerous patterns."""
        result = await coder.validate_change(str(temp_file), "eval('print(1)')")
        assert result["valid"] is False
        assert any("eval" in issue for issue in result["issues"])

    @pytest.mark.asyncio
    async def test_create_file_success(self, coder: CoderWorker) -> None:
        """Test creating a file."""
        new_file = Path(tempfile.gettempdir()) / "new_test_file.py"
        try:
            result = await coder.create_file(str(new_file), "# New file\nprint('test')")
            assert result["status"] == "success"
            assert result["created"] is True
            assert new_file.exists()
        finally:
            if new_file.exists():
                new_file.unlink()

    @pytest.mark.asyncio
    async def test_create_file_already_exists(self, coder: CoderWorker, temp_file: Path) -> None:
        """Test creating a file that already exists."""
        result = await coder.create_file(str(temp_file), "# Content")
        assert result["status"] == "error"
        assert result["created"] is False

    def test_get_applied_diffs(self, coder: CoderWorker) -> None:
        """Test getting applied diffs."""
        diffs = coder.get_applied_diffs()
        assert diffs == []
