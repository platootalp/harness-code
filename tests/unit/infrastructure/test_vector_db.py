"""Unit tests for vector_db module."""

from __future__ import annotations

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from mozi.exceptions import MemoryNotFoundError
from mozi.infrastructure.vector_db import (
    FileVectorStore,
    MemoryBlock,
    MemoryType,
)


@pytest.fixture
def temp_storage_path() -> Generator[str, None, None]:
    """Create a temporary storage path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield str(Path(tmpdir) / "test_vector_store.json")


@pytest.fixture
def sample_block() -> MemoryBlock:
    """Create a sample memory block."""
    return MemoryBlock(
        id="test-block-1",
        session_id="test-session",
        content="This is a test memory block",
        memory_type=MemoryType.SEMANTIC,
        embedding=[0.1, 0.2, 0.3, 0.4],
        importance=0.8,
    )


@pytest.fixture
def sample_blocks() -> list[MemoryBlock]:
    """Create multiple sample memory blocks."""
    return [
        MemoryBlock(
            id="block-1",
            session_id="session-1",
            content="Python programming",
            memory_type=MemoryType.SEMANTIC,
            embedding=[0.9, 0.1, 0.1, 0.1],
        ),
        MemoryBlock(
            id="block-2",
            session_id="session-1",
            content="JavaScript frameworks",
            memory_type=MemoryType.SEMANTIC,
            embedding=[0.1, 0.9, 0.1, 0.1],
        ),
        MemoryBlock(
            id="block-3",
            session_id="session-2",
            content="Database design",
            memory_type=MemoryType.EPISODIC,
            embedding=[0.1, 0.1, 0.9, 0.1],
        ),
    ]


@pytest.mark.unit
class TestMemoryBlock:
    """Unit tests for MemoryBlock."""

    def test_to_dict(self, sample_block: MemoryBlock) -> None:
        """Test converting MemoryBlock to dictionary."""
        data = sample_block.to_dict()

        assert data["id"] == sample_block.id
        assert data["session_id"] == sample_block.session_id
        assert data["content"] == sample_block.content
        assert data["memory_type"] == sample_block.memory_type.value
        assert data["embedding"] == sample_block.embedding
        assert data["importance"] == sample_block.importance

    def test_from_dict(self) -> None:
        """Test creating MemoryBlock from dictionary."""
        data = {
            "id": "dict-block",
            "session_id": "dict-session",
            "content": "Test content",
            "memory_type": "semantic",
            "embedding": [0.5, 0.5],
            "importance": 0.7,
            "status": "active",
            "created_at": "2024-01-01T00:00:00",
            "accessed_at": "2024-01-01T00:00:00",
            "metadata": {"key": "value"},
        }

        block = MemoryBlock.from_dict(data)

        assert block.id == "dict-block"
        assert block.session_id == "dict-session"
        assert block.content == "Test content"
        assert block.memory_type == MemoryType.SEMANTIC
        assert block.embedding == [0.5, 0.5]
        assert block.importance == 0.7


@pytest.mark.unit
class TestFileVectorStore:
    """Unit tests for FileVectorStore."""

    async def test_upsert_single_block(
        self, temp_storage_path: str, sample_block: MemoryBlock
    ) -> None:
        """Test upserting a single memory block."""
        store = FileVectorStore(storage_path=temp_storage_path)
        await store.upsert("test-session", [sample_block])

        results = await store.search(
            query_embedding=[0.1, 0.2, 0.3, 0.4],
            top_k=10,
        )

        assert len(results) == 1
        assert results[0][0].id == sample_block.id

    async def test_search_with_threshold(
        self, temp_storage_path: str, sample_block: MemoryBlock
    ) -> None:
        """Test search with similarity threshold."""
        store = FileVectorStore(storage_path=temp_storage_path)
        await store.upsert("test-session", [sample_block])

        very_different_embedding = [0.5, 0.5, 0.5, 0.5]
        results = await store.search(
            query_embedding=very_different_embedding,
            threshold=0.99,
        )

        assert len(results) == 0

    async def test_search_with_session_filter(
        self, temp_storage_path: str, sample_blocks: list[MemoryBlock]
    ) -> None:
        """Test search filtering by session_id."""
        store = FileVectorStore(storage_path=temp_storage_path)
        await store.upsert("session-1", sample_blocks[:2])
        await store.upsert("session-2", [sample_blocks[2]])

        results = await store.search(
            query_embedding=[0.9, 0.1, 0.1, 0.1],
            session_id="session-1",
            top_k=10,
        )

        assert all(r[0].session_id == "session-1" for r in results)

    async def test_search_with_memory_type_filter(
        self, temp_storage_path: str, sample_blocks: list[MemoryBlock]
    ) -> None:
        """Test search filtering by memory_type."""
        store = FileVectorStore(storage_path=temp_storage_path)
        await store.upsert("session-1", sample_blocks)

        results = await store.search(
            query_embedding=[0.1, 0.1, 0.9, 0.1],
            memory_type=MemoryType.EPISODIC,
            top_k=10,
        )

        assert all(r[0].memory_type == MemoryType.EPISODIC for r in results)

    async def test_delete_block(
        self, temp_storage_path: str, sample_block: MemoryBlock
    ) -> None:
        """Test deleting a memory block."""
        store = FileVectorStore(storage_path=temp_storage_path)
        await store.upsert("test-session", [sample_block])

        result = await store.delete("test-block-1")
        assert result is True

        results = await store.search(
            query_embedding=[0.1, 0.2, 0.3, 0.4],
            top_k=10,
        )
        assert len(results) == 0

    async def test_delete_nonexistent_block(self, temp_storage_path: str) -> None:
        """Test deleting a block that does not exist."""
        store = FileVectorStore(storage_path=temp_storage_path)

        with pytest.raises(MemoryNotFoundError):
            await store.delete("nonexistent-block")

    async def test_hybrid_search(
        self, temp_storage_path: str, sample_blocks: list[MemoryBlock]
    ) -> None:
        """Test hybrid search combining vector and text similarity."""
        store = FileVectorStore(storage_path=temp_storage_path)
        await store.upsert("session-1", sample_blocks)

        results = await store.hybrid_search(
            query_embedding=[0.1, 0.9, 0.1, 0.1],
            query_text="JavaScript",
            top_k=5,
        )

        assert len(results) > 0
        assert results[0][0].content == "JavaScript frameworks"

    async def test_cosine_similarity(self, temp_storage_path: str) -> None:
        """Test cosine similarity calculation."""
        store = FileVectorStore(storage_path=temp_storage_path)

        similar_embedding = [0.1, 0.2, 0.3, 0.4]
        result = await store.search(
            query_embedding=similar_embedding,
            top_k=1,
        )

        assert len(result) == 0

        block = MemoryBlock(
            id="similar-block",
            session_id="test-session",
            content="Similar content",
            memory_type=MemoryType.SEMANTIC,
            embedding=similar_embedding,
        )
        await store.upsert("test-session", [block])

        result = await store.search(
            query_embedding=similar_embedding,
            top_k=1,
        )

        assert len(result) == 1
        assert result[0][1] == pytest.approx(1.0, rel=0.01)

    async def test_upsert_updates_existing_block(
        self, temp_storage_path: str, sample_block: MemoryBlock
    ) -> None:
        """Test that upsert updates an existing block with same id."""
        store = FileVectorStore(storage_path=temp_storage_path)
        await store.upsert("test-session", [sample_block])

        updated_block = MemoryBlock(
            id="test-block-1",
            session_id="test-session",
            content="Updated content",
            memory_type=MemoryType.EPISODIC,
            embedding=[0.5, 0.5, 0.5, 0.5],
        )
        await store.upsert("test-session", [updated_block])

        results = await store.search(
            query_embedding=[0.5, 0.5, 0.5, 0.5],
            top_k=10,
        )

        assert len(results) == 1
        assert results[0][0].content == "Updated content"
        assert results[0][0].memory_type == MemoryType.EPISODIC

    async def test_search_top_k(
        self, temp_storage_path: str, sample_blocks: list[MemoryBlock]
    ) -> None:
        """Test that search respects top_k parameter."""
        store = FileVectorStore(storage_path=temp_storage_path)
        await store.upsert("session-1", sample_blocks)

        results = await store.search(
            query_embedding=[0.9, 0.1, 0.1, 0.1],
            threshold=0.1,
            top_k=1,
        )

        assert len(results) == 1

    async def test_persistence(
        self, temp_storage_path: str, sample_block: MemoryBlock
    ) -> None:
        """Test that data persists across store instances."""
        store1 = FileVectorStore(storage_path=temp_storage_path)
        await store1.upsert("test-session", [sample_block])

        store2 = FileVectorStore(storage_path=temp_storage_path)
        results = await store2.search(
            query_embedding=[0.1, 0.2, 0.3, 0.4],
            top_k=10,
        )

        assert len(results) == 1
        assert results[0][0].id == sample_block.id
