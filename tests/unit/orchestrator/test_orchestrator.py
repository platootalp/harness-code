"""Tests for the main orchestrator."""

from __future__ import annotations

import tempfile

import pytest

from mozi.orchestrator import Orchestrator, OrchestratorError


@pytest.fixture
def orchestrator() -> Orchestrator:
    """Create an Orchestrator instance."""
    with tempfile.TemporaryDirectory() as tmpdir:
        return Orchestrator(storage_path=tmpdir)


class TestOrchestratorError:
    """Tests for OrchestratorError exception."""

    def test_raise_error(self) -> None:
        """Test raising OrchestratorError."""
        with pytest.raises(OrchestratorError):
            raise OrchestratorError("Test error")


class TestOrchestrator:
    """Tests for Orchestrator class."""

    def test_init_default(self) -> None:
        """Test initialization with defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = Orchestrator(storage_path=tmpdir)
            assert orch._quality_threshold == 80.0
            assert orch._current_state is None

    def test_init_custom_threshold(self) -> None:
        """Test initialization with custom threshold."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = Orchestrator(storage_path=tmpdir, quality_threshold=90.0)
            assert orch._quality_threshold == 90.0

    def test_get_current_state_none(self) -> None:
        """Test getting current state when none exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = Orchestrator(storage_path=tmpdir)
            state = orch.get_current_state()
            assert state is None

    @pytest.mark.asyncio
    async def test_execute_quick_task(self, orchestrator: Orchestrator) -> None:
        """Test executing a quick task."""
        result = await orchestrator.execute("Fix typo in variable name")
        assert result["status"] == "completed"
        assert result["category"] == "quick"
        assert "session_id" in result

    @pytest.mark.asyncio
    async def test_execute_deep_task(self, orchestrator: Orchestrator) -> None:
        """Test executing a deep task."""
        result = await orchestrator.execute(
            "Build feature X with multiple components and dependencies",
            context={
                "multi_step": True,
                "requires_planning": True,
                "file_operations": True,
            },
        )
        assert result["category"] == "deep"
        assert "results" in result

    @pytest.mark.asyncio
    async def test_execute_strategic_task(self, orchestrator: Orchestrator) -> None:
        """Test executing a strategic task."""
        result = await orchestrator.execute(
            "Design system architecture for large scale application with multiple services",
            context={
                "requires_planning": True,
                "multi_step": True,
                "file_operations": True,
                "code_review": True,
                "testing": True,
            },
        )
        assert result["category"] == "strategic"

    @pytest.mark.asyncio
    async def test_review(self, orchestrator: Orchestrator) -> None:
        """Test reviewing a diff."""
        result = await orchestrator.review(
            "test-session",
            "+++ a/test.py\n+print('hello')\n",
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_state(self, orchestrator: Orchestrator) -> None:
        """Test getting state after execution."""
        await orchestrator.execute("Simple task")
        session_id = orchestrator.get_current_state().session_id  # type: ignore
        state = await orchestrator.get_state(session_id)
        assert state is not None
        assert state.session_id == session_id
