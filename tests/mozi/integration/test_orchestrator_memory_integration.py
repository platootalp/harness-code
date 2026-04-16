"""Integration tests for Orchestrator and Memory integration.

This module contains integration tests for:
- Memory retrieval triggering during task execution
- New memory storage after task completion
- Memory context inclusion in task processing

Tests verify that the orchestrator correctly integrates with
the Memory module for memory management.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from mozi.infrastructure.vector_db import MemoryBlock, MemoryType
from mozi.memory.long_term import LongTermMemory
from mozi.memory.retriever import MemoryRetriever
from mozi.memory.short_term import ShortTermMemory
from mozi.orchestrator.integration import OrchestratorIntegration


@pytest.fixture
def mock_short_term_memory() -> MagicMock:
    """Create a mock short-term memory."""
    memory = MagicMock(spec=ShortTermMemory)
    memory.add = AsyncMock()
    memory.get_recent = MagicMock(return_value=[])
    memory.search = AsyncMock(return_value=[])
    memory.clear = MagicMock()
    return memory


@pytest.fixture
def mock_long_term_memory() -> MagicMock:
    """Create a mock long-term memory."""
    memory = MagicMock(spec=LongTermMemory)
    memory.add = AsyncMock()
    memory.search = AsyncMock(return_value=[])
    memory.delete = AsyncMock()
    # Add the store mock that hybrid_search expects
    memory.store = MagicMock()
    memory.store.hybrid_search = AsyncMock(return_value=[])
    # session_id is accessed in hybrid_search
    memory.session_id = "test-session"
    return memory


@pytest.fixture
def memory_retriever(
    mock_short_term_memory: MagicMock,
    mock_long_term_memory: MagicMock,
) -> MemoryRetriever:
    """Create a memory retriever with mocks."""
    return MemoryRetriever(
        short_term=mock_short_term_memory,
        long_term=mock_long_term_memory,
    )


@pytest.fixture
def orchestrator_integration(
    memory_retriever: MemoryRetriever,
) -> OrchestratorIntegration:
    """Create an orchestrator integration with memory retriever."""
    return OrchestratorIntegration(
        memory_retriever=memory_retriever,
    )


@pytest.mark.integration
class TestMemoryRetrievalTriggering:
    """Tests for memory retrieval triggering."""

    @pytest.mark.asyncio
    async def test_memory_retrieved_for_session(
        self,
        orchestrator_integration: OrchestratorIntegration,
        mock_long_term_memory: MagicMock,
    ) -> None:
        """Test that memory is retrieved for a session."""
        # Setup mock to return some memories
        mock_block = MemoryBlock(
            id="mem-1",
            session_id="test-session",
            content="Previous work on similar feature",
            memory_type=MemoryType.EPISODIC,
            importance=0.8,
        )
        # Mock at the store level since hybrid_search calls long_term.store.hybrid_search
        mock_long_term_memory.store.hybrid_search = AsyncMock(
            return_value=[(mock_block, 0.9)]
        )

        result = await orchestrator_integration.retrieve_memories(
            session_id="test-session",
            query="feature implementation",
            limit=5,
        )

        assert result["status"] == "success"
        assert result["count"] == 1
        mock_long_term_memory.store.hybrid_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_memory_retrieval_with_no_results(
        self,
        orchestrator_integration: OrchestratorIntegration,
        mock_long_term_memory: MagicMock,
    ) -> None:
        """Test memory retrieval when no memories exist."""
        mock_long_term_memory.store.hybrid_search = AsyncMock(return_value=[])

        result = await orchestrator_integration.retrieve_memories(
            session_id="new-session",
            query="new task",
            limit=5,
        )

        assert result["status"] == "success"
        assert result["count"] == 0


@pytest.mark.integration
class TestNewMemoryStorage:
    """Tests for new memory storage."""

    @pytest.mark.asyncio
    async def test_memory_stored_after_task(
        self,
        orchestrator_integration: OrchestratorIntegration,
        mock_long_term_memory: MagicMock,
    ) -> None:
        """Test that memory is stored after task completion."""
        mock_long_term_memory.add = AsyncMock()

        result = await orchestrator_integration.store_memory(
            session_id="test-session",
            content="Completed task: Fixed bug in authentication module",
            memory_type="session",
            importance=0.7,
        )

        assert result["status"] == "success"
        mock_long_term_memory.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_memory_importance_captured(
        self,
        orchestrator_integration: OrchestratorIntegration,
        mock_long_term_memory: MagicMock,
    ) -> None:
        """Test that memory importance is captured."""
        mock_long_term_memory.add = AsyncMock()

        await orchestrator_integration.store_memory(
            session_id="test-session",
            content="Critical fix applied",
            memory_type="session",
            importance=0.95,
        )

        # Verify the memory was added
        mock_long_term_memory.add.assert_called_once()
        call_args = mock_long_term_memory.add.call_args
        assert call_args is not None


@pytest.mark.integration
class TestMemoryContextInclusion:
    """Tests for memory context inclusion."""

    @pytest.mark.asyncio
    async def test_retrieved_memories_formatted(
        self,
        orchestrator_integration: OrchestratorIntegration,
        mock_long_term_memory: MagicMock,
    ) -> None:
        """Test that retrieved memories are properly formatted."""
        mock_block = MemoryBlock(
            id="mem-1",
            session_id="test-session",
            content="Previous implementation details",
            memory_type=MemoryType.EPISODIC,
            importance=0.8,
        )
        mock_long_term_memory.store.hybrid_search = AsyncMock(
            return_value=[(mock_block, 0.85)]
        )

        result = await orchestrator_integration.retrieve_memories(
            session_id="test-session",
            query="implementation",
            limit=5,
        )

        assert "memories" in result
        assert len(result["memories"]) == 1
        assert result["memories"][0]["content"] == "Previous implementation details"
        assert result["memories"][0]["score"] == 0.85

    @pytest.mark.asyncio
    async def test_no_memory_retriever_returns_empty(
        self,
    ) -> None:
        """Test that missing memory retriever returns empty results."""
        integration = OrchestratorIntegration(memory_retriever=None)

        result = await integration.retrieve_memories(
            session_id="test-session",
            query="test",
        )

        assert result["status"] == "no_memory_retriever"
        assert result["memories"] == []


@pytest.mark.integration
class TestShortTermMemoryIntegration:
    """Tests for short-term memory integration."""

    @pytest.mark.asyncio
    async def test_short_term_context_retrieved(
        self,
        memory_retriever: MemoryRetriever,
        mock_short_term_memory: MagicMock,
    ) -> None:
        """Test that short-term context is retrieved."""
        from datetime import datetime

        from mozi.memory.short_term import ShortTermMemoryEntry

        mock_entry = ShortTermMemoryEntry(
            id="stm-1",
            content="Recent interaction",
            timestamp=datetime.fromtimestamp(1234567890.0),
        )
        mock_short_term_memory.get_recent = MagicMock(return_value=[mock_entry])

        context = memory_retriever.get_short_term_context(limit=5)

        assert len(context) == 1
        assert context[0].content == "Recent interaction"
