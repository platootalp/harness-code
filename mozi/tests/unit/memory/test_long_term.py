"""Unit tests for the long_term module."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from mozi.infrastructure.vector_db import MemoryBlock, MemoryType
from mozi.memory.long_term import LongTermMemory


class TestLongTermMemory:
    """Tests for LongTermMemory class."""

    @pytest.fixture
    def mock_store(self) -> MagicMock:
        """Create a mock vector store."""
        store = MagicMock()
        store.upsert = AsyncMock()
        store.search = AsyncMock(return_value=[])
        store.delete = AsyncMock(return_value=True)
        return store

    @pytest.fixture
    def memory(self, mock_store: MagicMock) -> LongTermMemory:
        """Create a LongTermMemory instance with mock store."""
        return LongTermMemory(store=mock_store, session_id="test_session")

    def test_initialization(self, memory: LongTermMemory, mock_store: MagicMock) -> None:
        """Test initializing long-term memory."""
        assert memory.store is mock_store
        assert memory.session_id == "test_session"

    @pytest.mark.asyncio
    async def test_add_creates_memory_block(self, memory: LongTermMemory, mock_store: MagicMock) -> None:
        """Test that add creates a proper memory block."""
        block = await memory.add("Test content")

        assert isinstance(block, MemoryBlock)
        assert block.content == "Test content"
        assert block.session_id == "test_session"
        assert block.memory_type == MemoryType.SEMANTIC
        assert block.importance == 0.5

    @pytest.mark.asyncio
    async def test_add_with_custom_type(self, memory: LongTermMemory, mock_store: MagicMock) -> None:
        """Test adding memory with custom memory type."""
        block = await memory.add("Episode content", memory_type=MemoryType.EPISODIC)

        assert block.memory_type == MemoryType.EPISODIC

    @pytest.mark.asyncio
    async def test_add_with_embedding(self, memory: LongTermMemory, mock_store: MagicMock) -> None:
        """Test adding memory with embedding vector."""
        embedding = [0.1] * 128
        block = await memory.add("Content with embedding", embedding=embedding)

        assert block.embedding == embedding

    @pytest.mark.asyncio
    async def test_add_with_importance(self, memory: LongTermMemory, mock_store: MagicMock) -> None:
        """Test adding memory with custom importance."""
        block = await memory.add("Important content", importance=0.9)

        assert block.importance == 0.9

    @pytest.mark.asyncio
    async def test_add_with_metadata(self, memory: LongTermMemory, mock_store: MagicMock) -> None:
        """Test adding memory with metadata."""
        metadata = {"source": "user", "priority": "high"}
        block = await memory.add("Content with metadata", metadata=metadata)

        assert block.metadata == {"source": "user", "priority": "high"}

    @pytest.mark.asyncio
    async def test_add_calls_store_upsert(self, memory: LongTermMemory, mock_store: MagicMock) -> None:
        """Test that add calls the store's upsert method."""
        block = await memory.add("Test content")

        mock_store.upsert.assert_called_once()
        call_args = mock_store.upsert.call_args
        assert call_args[0][0] == "test_session"
        assert call_args[0][1] == [block]

    @pytest.mark.asyncio
    async def test_search_delegates_to_store(
        self, memory: LongTermMemory, mock_store: MagicMock
    ) -> None:
        """Test that search delegates to the store."""
        query_embedding = [0.1] * 128
        mock_store.search.return_value = []

        results = await memory.search(query_embedding)

        mock_store.search.assert_called_once_with(
            query_embedding=query_embedding,
            session_id="test_session",
            memory_type=None,
            top_k=5,
            threshold=0.7,
        )
        assert results == []

    @pytest.mark.asyncio
    async def test_search_with_filters(
        self, memory: LongTermMemory, mock_store: MagicMock
    ) -> None:
        """Test search with memory type and limit filters."""
        query_embedding = [0.1] * 128

        results = await memory.search(
            query_embedding=query_embedding,
            memory_type=MemoryType.EPISODIC,
            top_k=10,
            threshold=0.8,
        )

        mock_store.search.assert_called_once_with(
            query_embedding=query_embedding,
            session_id="test_session",
            memory_type=MemoryType.EPISODIC,
            top_k=10,
            threshold=0.8,
        )

    @pytest.mark.asyncio
    async def test_search_returns_results(
        self, memory: LongTermMemory, mock_store: MagicMock
    ) -> None:
        """Test that search properly returns results."""
        query_embedding = [0.1] * 128
        block = MemoryBlock(
            id="test_block",
            session_id="test_session",
            content="Found content",
            memory_type=MemoryType.SEMANTIC,
            embedding=[0.1] * 128,
        )
        mock_store.search.return_value = [(block, 0.95)]

        results = await memory.search(query_embedding)

        assert len(results) == 1
        assert results[0][0].content == "Found content"
        assert results[0][1] == 0.95

    @pytest.mark.asyncio
    async def test_delete_calls_store(
        self, memory: LongTermMemory, mock_store: MagicMock
    ) -> None:
        """Test that delete calls the store's delete method."""
        result = await memory.delete("test_block_id")

        mock_store.delete.assert_called_once_with("test_block_id")
        assert result is True

    @pytest.mark.asyncio
    async def test_update_importance(
        self, memory: LongTermMemory, mock_store: MagicMock
    ) -> None:
        """Test updating importance score of a memory block."""
        block = MemoryBlock(
            id="test_block",
            session_id="test_session",
            content="Content to update",
            memory_type=MemoryType.SEMANTIC,
            embedding=[0.1] * 128,
            importance=0.5,
        )
        mock_store.search.return_value = [(block, 1.0)]

        updated = await memory.update_importance("test_block", 0.9)

        assert updated is not None
        assert updated.importance == 0.9

    @pytest.mark.asyncio
    async def test_update_importance_block_not_found(
        self, memory: LongTermMemory, mock_store: MagicMock
    ) -> None:
        """Test updating importance when block is not found."""
        mock_store.search.return_value = []

        updated = await memory.update_importance("nonexistent", 0.9)

        assert updated is None

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self, memory: LongTermMemory, mock_store: MagicMock
    ) -> None:
        """Test getting a memory block by ID when it exists."""
        block = MemoryBlock(
            id="found_block",
            session_id="test_session",
            content="Found content",
            memory_type=MemoryType.SEMANTIC,
        )
        mock_store.search.return_value = [(block, 1.0)]

        result = await memory.get_by_id("found_block")

        assert result is not None
        assert result.id == "found_block"
        assert result.content == "Found content"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self, memory: LongTermMemory, mock_store: MagicMock
    ) -> None:
        """Test getting a memory block by ID when it doesn't exist."""
        mock_store.search.return_value = []

        result = await memory.get_by_id("nonexistent")

        assert result is None
