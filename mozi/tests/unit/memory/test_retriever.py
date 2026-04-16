"""Unit tests for the retriever module."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from mozi.infrastructure.vector_db import MemoryBlock, MemoryType
from mozi.memory.long_term import LongTermMemory
from mozi.memory.retriever import MemoryRetriever, RetrievedMemory
from mozi.memory.short_term import ShortTermMemory, ShortTermMemoryEntry


class TestRetrievedMemory:
    """Tests for RetrievedMemory dataclass."""

    def test_creation(self) -> None:
        """Test creating a RetrievedMemory instance."""
        block = MemoryBlock(
            id="test_block",
            session_id="test_session",
            content="Test content",
            memory_type=MemoryType.SEMANTIC,
        )
        retrieved = RetrievedMemory(block=block, score=0.95, source="long_term")

        assert retrieved.block is block
        assert retrieved.score == 0.95
        assert retrieved.source == "long_term"


class TestMemoryRetriever:
    """Tests for MemoryRetriever class."""

    @pytest.fixture
    def short_term_memory(self) -> ShortTermMemory:
        """Create a short-term memory instance."""
        memory = ShortTermMemory()
        memory.add("First entry")
        memory.add("Second entry")
        return memory

    @pytest.fixture
    def mock_long_term(self) -> MagicMock:
        """Create a mock long-term memory."""
        mock = MagicMock(spec=LongTermMemory)
        mock.session_id = "test_session"
        mock.store = MagicMock()
        mock.store.hybrid_search = AsyncMock(return_value=[])
        return mock

    @pytest.fixture
    def retriever(
        self, short_term_memory: ShortTermMemory, mock_long_term: MagicMock
    ) -> MemoryRetriever:
        """Create a MemoryRetriever instance."""
        return MemoryRetriever(
            short_term=short_term_memory,
            long_term=mock_long_term,
        )

    def test_initialization(
        self, retriever: MemoryRetriever, short_term_memory: ShortTermMemory
    ) -> None:
        """Test initializing the retriever."""
        assert retriever.short_term is short_term_memory
        assert retriever.long_term is not None

    @pytest.mark.asyncio
    async def test_recall_delegates_to_long_term(
        self, retriever: MemoryRetriever, mock_long_term: MagicMock
    ) -> None:
        """Test that recall delegates to long-term memory search."""
        query_embedding = [0.1] * 128
        mock_long_term.search = AsyncMock(return_value=[])

        results = await retriever.recall(query_embedding)

        mock_long_term.search.assert_called_once()
        assert results == []

    @pytest.mark.asyncio
    async def test_recall_returns_retrieved_memories(
        self, retriever: MemoryRetriever, mock_long_term: MagicMock
    ) -> None:
        """Test that recall returns properly formatted results."""
        query_embedding = [0.1] * 128
        block = MemoryBlock(
            id="test_block",
            session_id="test_session",
            content="Recalled content",
            memory_type=MemoryType.SEMANTIC,
        )
        mock_long_term.search = AsyncMock(return_value=[(block, 0.92)])

        results = await retriever.recall(query_embedding)

        assert len(results) == 1
        assert isinstance(results[0], RetrievedMemory)
        assert results[0].block.content == "Recalled content"
        assert results[0].score == 0.92
        assert results[0].source == "long_term"

    @pytest.mark.asyncio
    async def test_recall_with_filters(
        self, retriever: MemoryRetriever, mock_long_term: MagicMock
    ) -> None:
        """Test recall with memory type filter."""
        query_embedding = [0.1] * 128
        mock_long_term.search = AsyncMock(return_value=[])

        await retriever.recall(
            query_embedding,
            memory_type=MemoryType.EPISODIC,
            top_k=10,
            threshold=0.8,
        )

        mock_long_term.search.assert_called_once_with(
            query_embedding=query_embedding,
            memory_type=MemoryType.EPISODIC,
            top_k=10,
            threshold=0.8,
        )

    @pytest.mark.asyncio
    async def test_hybrid_search_delegates_to_store(
        self, retriever: MemoryRetriever, mock_long_term: MagicMock
    ) -> None:
        """Test that hybrid_search delegates to the store."""
        query_embedding = [0.1] * 128
        query_text = "test query"

        results = await retriever.hybrid_search(
            query_embedding=query_embedding,
            query_text=query_text,
        )

        mock_long_term.store.hybrid_search.assert_called_once()
        assert results == []

    @pytest.mark.asyncio
    async def test_hybrid_search_returns_results(
        self, retriever: MemoryRetriever, mock_long_term: MagicMock
    ) -> None:
        """Test that hybrid_search returns properly formatted results."""
        query_embedding = [0.1] * 128
        block = MemoryBlock(
            id="hybrid_block",
            session_id="test_session",
            content="Hybrid content",
            memory_type=MemoryType.SEMANTIC,
        )
        mock_long_term.store.hybrid_search.return_value = [(block, 0.88)]

        results = await retriever.hybrid_search(query_embedding, query_text="test")

        assert len(results) == 1
        assert results[0].source == "hybrid"
        assert results[0].score == 0.88

    def test_rerank_orders_by_adjusted_score(self, retriever: MemoryRetriever) -> None:
        """Test that rerank orders memories by adjusted score."""
        block1 = MemoryBlock(
            id="block1",
            session_id="test",
            content="Content 1",
            memory_type=MemoryType.SEMANTIC,
            importance=0.3,
            accessed_at=datetime.now() - timedelta(days=6),
        )
        block2 = MemoryBlock(
            id="block2",
            session_id="test",
            content="Content 2",
            memory_type=MemoryType.SEMANTIC,
            importance=0.9,
            accessed_at=datetime.now(),
        )

        memories = [
            RetrievedMemory(block=block1, score=0.7, source="long_term"),
            RetrievedMemory(block=block2, score=0.7, source="long_term"),
        ]

        reranked = retriever.rerank(memories)

        assert reranked[0].block.id == "block2"
        assert reranked[1].block.id == "block1"

    def test_rerank_with_custom_weights(self, retriever: MemoryRetriever) -> None:
        """Test reranking with custom weights."""
        block = MemoryBlock(
            id="block1",
            session_id="test",
            content="Content",
            memory_type=MemoryType.SEMANTIC,
            importance=0.5,
        )

        memories = [RetrievedMemory(block=block, score=0.5, source="long_term")]

        reranked = retriever.rerank(
            memories,
            importance_weight=0.5,
            recency_weight=0.0,
        )

        assert len(reranked) == 1

    def test_get_short_term_context(
        self, retriever: MemoryRetriever, short_term_memory: ShortTermMemory
    ) -> None:
        """Test getting short-term context."""
        context = retriever.get_short_term_context(limit=5)

        assert len(context) == 2
        assert context[0].content == "Second entry"
        assert context[1].content == "First entry"

    def test_get_short_term_context_default_limit(
        self, retriever: MemoryRetriever
    ) -> None:
        """Test getting short-term context with default limit."""
        context = retriever.get_short_term_context()

        assert len(context) == 2
