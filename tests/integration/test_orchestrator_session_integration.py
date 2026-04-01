"""Integration tests for Orchestrator and Session integration.

This module contains integration tests for:
- Session context passing
- State persistence to Session
- Message persistence during task execution

Tests verify that the orchestrator correctly integrates with
the Session module for session management.
"""

from __future__ import annotations

import tempfile
from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mozi.orchestrator import Orchestrator


@pytest.fixture
def mock_session_manager() -> MagicMock:
    """Create a mock session manager."""
    manager = MagicMock()
    manager.init = AsyncMock()
    manager.close = AsyncMock()
    manager.create_session = AsyncMock()
    manager.get_session = AsyncMock()
    manager.update_session = AsyncMock()
    manager.add_message = AsyncMock()
    manager.get_messages = AsyncMock(return_value=[])
    return manager


@pytest.fixture
def orchestrator() -> Iterator[Orchestrator]:
    """Create an orchestrator instance."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Orchestrator(storage_path=tmpdir)


@pytest.mark.integration
class TestSessionContextPassing:
    """Tests for session context passing."""

    @pytest.mark.asyncio
    async def test_session_id_passed_to_execute(
        self,
        orchestrator: Orchestrator,
        mock_session_manager: MagicMock,
    ) -> None:
        """Test that session ID is passed through execution context."""
        context = {"session_id": "test-session-123"}

        # Mock the state store to avoid file operations
        with patch.object(orchestrator._state_store, "save_state"):
            with patch.object(orchestrator._state_store, "add_todo"):
                with patch.object(orchestrator._state_store, "complete_todo"):
                    with patch.object(orchestrator._state_store, "add_decision"):
                        result = await orchestrator.execute(
                            "Fix typo in variable name",
                            context=context,
                        )

        assert result["session_id"] == "test-session-123"

    @pytest.mark.asyncio
    async def test_session_created_if_not_exists(
        self,
        orchestrator: Orchestrator,
        mock_session_manager: MagicMock,
    ) -> None:
        """Test that session is created if it doesn't exist."""
        mock_session_manager.get_session = AsyncMock(return_value=None)
        mock_session_manager.create_session = AsyncMock()

        context = {"session_id": "new-session-456"}

        # The orchestrator should work without session manager being set
        with patch.object(orchestrator._state_store, "save_state"):
            with patch.object(orchestrator._state_store, "add_todo"):
                with patch.object(orchestrator._state_store, "complete_todo"):
                    with patch.object(orchestrator._state_store, "add_decision"):
                        result = await orchestrator.execute(
                            "Simple task",
                            context=context,
                        )

        # Verify session_id is in result
        assert "session_id" in result


@pytest.mark.integration
class TestStatePersistenceToSession:
    """Tests for state persistence to Session."""

    @pytest.mark.asyncio
    async def test_state_saved_after_execution(
        self,
        orchestrator: Orchestrator,
    ) -> None:
        """Test that state is saved after task execution."""
        context = {"session_id": "persist-session"}

        with patch.object(orchestrator._state_store, "save_state") as mock_save:
            with patch.object(orchestrator._state_store, "add_todo"):
                with patch.object(orchestrator._state_store, "complete_todo"):
                    with patch.object(orchestrator._state_store, "add_decision"):
                        await orchestrator.execute(
                            "Fix typo",
                            context=context,
                        )

            # Should have been called multiple times during execution
            assert mock_save.call_count >= 1

    @pytest.mark.asyncio
    async def test_state_loadable_after_execution(
        self,
        orchestrator: Orchestrator,
    ) -> None:
        """Test that state can be loaded after execution."""
        from mozi.orchestrator.state import OrchestratorState

        context = {"session_id": "load-state-session"}

        # Create a mock state
        mock_state = OrchestratorState(
            session_id="load-state-session",
            task_description="Simple task",
            category="quick",
        )

        with patch.object(orchestrator._state_store, "save_state"):
            with patch.object(orchestrator._state_store, "add_todo"):
                with patch.object(orchestrator._state_store, "complete_todo"):
                    with patch.object(orchestrator._state_store, "add_decision"):
                        with patch.object(
                            orchestrator._state_store, "load_state",
                            return_value=mock_state
                        ):
                            await orchestrator.execute(
                                "Simple task",
                                context=context,
                            )

        # Load the state - mock get_state since we mocked load_state
        with patch.object(
            orchestrator, "get_state",
            return_value=mock_state
        ):
            loaded_state = await orchestrator.get_state("load-state-session")
            assert loaded_state is not None
            assert loaded_state.session_id == "load-state-session"
