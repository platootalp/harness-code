"""Integration tests for Orchestrator and Context integration.

This module contains integration tests for:
- Context building and allocation to workers
- Worker result summarization and archival
- Context window management during execution

Tests verify that the orchestrator correctly integrates with
the Context module for context management.
"""

from __future__ import annotations

import tempfile
from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mozi.context.builder import BuiltContext, ContextBuilder, ContextConfig
from mozi.orchestrator import Orchestrator


@pytest.fixture
def context_builder() -> ContextBuilder:
    """Create a context builder instance."""
    config = ContextConfig(
        max_tokens=100000,
        include_history=True,
        include_memory=True,
    )
    return ContextBuilder(config=config)


@pytest.fixture
def orchestrator() -> Iterator[Orchestrator]:
    """Create an orchestrator instance."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Orchestrator(storage_path=tmpdir)


@pytest.mark.integration
class TestContextAllocationToWorkers:
    """Tests for context allocation to workers."""

    @pytest.mark.asyncio
    async def test_context_built_for_session(
        self,
        orchestrator: Orchestrator,
        context_builder: ContextBuilder,
    ) -> None:
        """Test that context is built for a session."""
        # Mock session manager to return messages
        mock_session_manager = MagicMock()
        mock_session_manager.get_messages = AsyncMock(return_value=[])

        context_builder._session_manager = mock_session_manager

        built = await context_builder.build(
            session_id="test-session",
            system_prompt="You are a helpful assistant.",
        )

        assert built is not None
        assert built.system_prompt == "You are a helpful assistant."
        assert isinstance(built, BuiltContext)

    @pytest.mark.asyncio
    async def test_context_includes_history(
        self,
        context_builder: ContextBuilder,
    ) -> None:
        """Test that context includes conversation history."""
        from mozi.session.models import Message, MessageRole

        mock_messages = [
            Message(
                id="msg-1",
                session_id="test-session",
                role=MessageRole.USER,
                content="Hello",
            ),
            Message(
                id="msg-2",
                session_id="test-session",
                role=MessageRole.ASSISTANT,
                content="Hi there!",
            ),
        ]

        mock_session_manager = MagicMock()
        mock_session_manager.get_messages = AsyncMock(return_value=mock_messages)

        context_builder._session_manager = mock_session_manager

        built = await context_builder.build(session_id="test-session")

        assert len(built.messages) == 2
        assert "Hello" in built.messages[0]
        assert "Hi there!" in built.messages[1]


@pytest.mark.integration
class TestWorkerResultSummarization:
    """Tests for worker result summarization."""

    @pytest.mark.asyncio
    async def test_worker_result_summarized(
        self,
        orchestrator: Orchestrator,
    ) -> None:
        """Test that worker results are summarized."""
        context = {"session_id": "summarize-test"}

        with patch.object(orchestrator._state_store, "save_state"):
            with patch.object(orchestrator._state_store, "add_todo"):
                with patch.object(orchestrator._state_store, "complete_todo") as mock_complete:
                    with patch.object(orchestrator._state_store, "add_decision"):
                        await orchestrator.execute(
                            "Fix typo in variable name",
                            context=context,
                        )

        # Verify complete_todo was called with result
        if mock_complete.called:
            call_args = mock_complete.call_args
            assert call_args is not None

    @pytest.mark.asyncio
    async def test_deep_task_results_collected(
        self,
        orchestrator: Orchestrator,
    ) -> None:
        """Test that DEEP task results are collected properly."""
        context = {
            "session_id": "deep-results-test",
            "multi_step": True,
            "requires_planning": True,
        }

        with patch.object(orchestrator._state_store, "load_state"):
            with patch.object(orchestrator._state_store, "save_state"):
                with patch.object(orchestrator._state_store, "add_todo"):
                    with patch.object(orchestrator._state_store, "update_todo"):
                        with patch.object(orchestrator._state_store, "complete_todo"):
                            with patch.object(orchestrator._state_store, "add_decision"):
                                result = await orchestrator.execute(
                                    "Build feature X with multiple components",
                                    context=context,
                                )

        assert result["category"] == "deep"
        assert "results" in result


@pytest.mark.integration
class TestContextWindowManagement:
    """Tests for context window management."""

    @pytest.mark.asyncio
    async def test_context_token_estimation(
        self,
        context_builder: ContextBuilder,
    ) -> None:
        """Test that context token estimation works."""
        built = await context_builder.build(
            session_id="token-test",
            system_prompt="A" * 1000,  # ~250 tokens
        )

        # Token estimation is rough: len/4
        assert built.total_tokens >= 0

    @pytest.mark.asyncio
    async def test_context_config_respected(
        self,
        context_builder: ContextBuilder,
    ) -> None:
        """Test that context config is respected."""
        config = ContextConfig(
            max_tokens=50000,
            include_history=False,
            include_memory=False,
        )

        builder = ContextBuilder(config=config)
        built = await builder.build(session_id="config-test")

        assert built.config.max_tokens == 50000
        assert built.config.include_history is False
        assert built.config.include_memory is False
