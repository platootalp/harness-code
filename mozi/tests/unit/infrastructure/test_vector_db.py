"""Unit tests for the vector_db module."""

import json
import os
import tempfile

import pytest

from mozi.exceptions import MemoryNotFoundError, VectorStoreError
from mozi.infrastructure.vector_db import (
    FileVectorStore,
    MemoryBlock,
    MemoryType,
)


class TestMemoryType:
    """Tests for MemoryType enum."""

    def test_memory_type_values(self) -> None:
        """Test MemoryType enum values."""
        assert MemoryType.SHORT_TERM.value == "short_term"
        assert MemoryType.SEMANTIC.value == "semantic"
        assert MemoryType.EPISODIC.value == "episodic"
        assert MemoryType.PROCEDURAL.value == "procedural"


class TestMemoryBlock:
    """Tests for MemoryBlock dataclass."""

    def test_creation(self) -> None:
        """Test creating a MemoryBlock."""
        block = MemoryBlock(
            id="test_1",
            session_id="session_1",
            content="Test content",
            memory_type=MemoryType.SEMANTIC,
        )
        assert block.id == "test_1"
        assert block.session_id == "session_1"
        assert block.content == "Test content"
        assert block.memory_type == MemoryType.SEMANTIC
        assert block.importance == 0.5
        assert block.status == "active"

    def test_to_dict(self) -> None:
        """Test converting MemoryBlock to dictionary."""
        block = MemoryBlock(
            id="test_1",
            session_id="session_1",
            content="Test content",
            memory_type=MemoryType.SEMANTIC,
            importance=0.8,
        )
        data = block.to_dict()
        assert data["id"] == "test_1"
        assert data["content"] == "Test content"
        assert data["memory_type"] == "semantic"
        assert data["importance"] == 0.8

    def test_from_dict(self) -> None:
        """Test creating MemoryBlock from dictionary."""
        data = {
            "id": "test_1",
            "session_id": "session_1",
            "content": "Test content",
            "memory_type": "semantic",
            "importance": 0.8,
            "status": "active",
            "created_at": "2026-01-01T00:00:00",
            "accessed_at": "2026-01-01T00:00:00",
            "metadata": {},
        }
        block = MemoryBlock.from_dict(data)
        assert block.id == "test_1"
        assert block.memory_type == MemoryType.SEMANTIC

    def test_roundtrip(self) -> None:
        """Test to_dict and from_dict roundtrip."""
        block = MemoryBlock(
            id="test_1",
            session_id="session_1",
            content="Test content",
            memory_type=MemoryType.EPISODIC,
            embedding=[0.1, 0.2, 0.3],
            importance=0.9,
            metadata={"key": "value"},
        )
        data = block.to_dict()
        restored = MemoryBlock.from_dict(data)

        assert restored.id == block.id
        assert restored.session_id == block.session_id
        assert restored.content == block.content
        assert restored.memory_type == block.memory_type
        assert restored.embedding == block.embedding
        assert restored.importance == block.importance


class TestFileVectorStore:
    """Tests for FileVectorStore class."""

    @pytest.fixture
    def temp_storage(self) -> str:
        """Create a temporary storage file."""
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.unlink(path)
        yield path
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def store(self, temp_storage: str) -> FileVectorStore:
        """Create a FileVectorStore with temporary storage."""
        return FileVectorStore(storage_path=temp_storage)

    def test_initialization(self, temp_storage: str) -> None:
        """Test initializing FileVectorStore."""
        store = FileVectorStore(storage_path=temp_storage)
        assert store.storage_path == temp_storage

    def test_initialization_default_path(self) -> None:
        """Test initializing with default storage path."""
        store = FileVectorStore()
        assert "vector_store.json" in store.storage_path

    @pytest.mark.asyncio
    async def test_upsert_single_block(self, store: FileVectorStore) -> None:
        """Test inserting a single memory block."""
        block = MemoryBlock(
            id="block_1",
            session_id="session_1",
            content="First block",
            memory_type=MemoryType.SEMANTIC,
        )
        await store.upsert("session_1", [block])

        assert len(store._blocks) == 1
        assert store._blocks["block_1"].content == "First block"

    @pytest.mark.asyncio
    async def test_upsert_multiple_blocks(self, store: FileVectorStore) -> None:
        """Test inserting multiple memory blocks."""
        blocks = [
            MemoryBlock(
                id=f"block_{i}",
                session_id="session_1",
                content=f"Block {i}",
                memory_type=MemoryType.SEMANTIC,
            )
            for i in range(3)
        ]
        await store.upsert("session_1", blocks)

        assert len(store._blocks) == 3

    @pytest.mark.asyncio
    async def test_upsert_updates_existing(self, store: FileVectorStore) -> None:
        """Test that upsert updates existing blocks."""
        block1 = MemoryBlock(
            id="block_1",
            session_id="session_1",
            content="Original content",
            memory_type=MemoryType.SEMANTIC,
        )
        await store.upsert("session_1", [block1])

        block1.content = "Updated content"
        await store.upsert("session_1", [block1])

        assert len(store._blocks) == 1
        assert store._blocks["block_1"].content == "Updated content"

    @pytest.mark.asyncio
    async def test_search_basic(self, store: FileVectorStore) -> None:
        """Test basic vector search."""
        embedding = [0.1, 0.2, 0.3]
        block = MemoryBlock(
            id="block_1",
            session_id="session_1",
            content="Test block",
            memory_type=MemoryType.SEMANTIC,
            embedding=embedding,
        )
        await store.upsert("session_1", [block])

        results = await store.search(query_embedding=embedding, threshold=0.0)

        assert len(results) == 1
        assert results[0][0].id == "block_1"
        assert results[0][1] == 1.0

    @pytest.mark.asyncio
    async def test_search_with_session_filter(self, store: FileVectorStore) -> None:
        """Test search with session ID filter."""
        block1 = MemoryBlock(
            id="block_1",
            session_id="session_1",
            content="Block 1",
            memory_type=MemoryType.SEMANTIC,
            embedding=[0.1, 0.1, 0.1],
        )
        block2 = MemoryBlock(
            id="block_2",
            session_id="session_2",
            content="Block 2",
            memory_type=MemoryType.SEMANTIC,
            embedding=[0.1, 0.1, 0.1],
        )
        await store.upsert("session_1", [block1])
        await store.upsert("session_2", [block2])

        results = await store.search(
            query_embedding=[0.1, 0.1, 0.1],
            session_id="session_1",
            threshold=0.0,
        )

        assert len(results) == 1
        assert results[0][0].session_id == "session_1"

    @pytest.mark.asyncio
    async def test_search_with_memory_type_filter(self, store: FileVectorStore) -> None:
        """Test search with memory type filter."""
        block1 = MemoryBlock(
            id="block_1",
            session_id="session_1",
            content="Semantic block",
            memory_type=MemoryType.SEMANTIC,
            embedding=[0.1, 0.1, 0.1],
        )
        block2 = MemoryBlock(
            id="block_2",
            session_id="session_1",
            content="Episodic block",
            memory_type=MemoryType.EPISODIC,
            embedding=[0.1, 0.1, 0.1],
        )
        await store.upsert("session_1", [block1, block2])

        results = await store.search(
            query_embedding=[0.1, 0.1, 0.1],
            memory_type=MemoryType.SEMANTIC,
            threshold=0.0,
        )

        assert len(results) == 1
        assert results[0][0].memory_type == MemoryType.SEMANTIC

    @pytest.mark.asyncio
    async def test_search_top_k(self, store: FileVectorStore) -> None:
        """Test search with top_k limit."""
        for i in range(5):
            block = MemoryBlock(
                id=f"block_{i}",
                session_id="session_1",
                content=f"Block {i}",
                memory_type=MemoryType.SEMANTIC,
                embedding=[0.1] * 3,
            )
            await store.upsert("session_1", [block])

        results = await store.search(
            query_embedding=[0.1, 0.1, 0.1],
            threshold=0.0,
            top_k=3,
        )

        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_search_threshold_filters_results(self, store: FileVectorStore) -> None:
        """Test that threshold filters out low similarity results."""
        block = MemoryBlock(
            id="block_1",
            session_id="session_1",
            content="Test block",
            memory_type=MemoryType.SEMANTIC,
            embedding=[1.0, 0.0, 0.0],
        )
        await store.upsert("session_1", [block])

        results = await store.search(
            query_embedding=[0.0, 1.0, 0.0],
            threshold=0.5,
        )

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_delete_existing_block(self, store: FileVectorStore) -> None:
        """Test deleting an existing block."""
        block = MemoryBlock(
            id="block_to_delete",
            session_id="session_1",
            content="Block to delete",
            memory_type=MemoryType.SEMANTIC,
        )
        await store.upsert("session_1", [block])

        result = await store.delete("block_to_delete")

        assert result is True
        assert "block_to_delete" not in store._blocks

    @pytest.mark.asyncio
    async def test_delete_nonexistent_block(self, store: FileVectorStore) -> None:
        """Test deleting a nonexistent block raises error."""
        with pytest.raises(MemoryNotFoundError):
            await store.delete("nonexistent_block")

    def test_cosine_similarity_identical(self) -> None:
        """Test cosine similarity of identical vectors."""
        vec = [0.1, 0.2, 0.3]
        similarity = FileVectorStore._cosine_similarity(vec, vec)
        assert similarity == 1.0

    def test_cosine_similarity_orthogonal(self) -> None:
        """Test cosine similarity of orthogonal vectors."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        similarity = FileVectorStore._cosine_similarity(vec1, vec2)
        assert similarity == 0.0

    def test_cosine_similarity_opposite(self) -> None:
        """Test cosine similarity of opposite vectors."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [-1.0, 0.0, 0.0]
        similarity = FileVectorStore._cosine_similarity(vec1, vec2)
        assert similarity == -1.0

    def test_cosine_similarity_different_lengths(self) -> None:
        """Test cosine similarity with different length vectors."""
        vec1 = [0.1, 0.2]
        vec2 = [0.1, 0.2, 0.3]
        similarity = FileVectorStore._cosine_similarity(vec1, vec2)
        assert similarity == 0.0

    def test_cosine_similarity_zero_vector(self) -> None:
        """Test cosine similarity with zero vector."""
        vec1 = [0.0, 0.0, 0.0]
        vec2 = [0.1, 0.2, 0.3]
        similarity = FileVectorStore._cosine_similarity(vec1, vec2)
        assert similarity == 0.0

    @pytest.mark.asyncio
    async def test_hybrid_search(self, store: FileVectorStore) -> None:
        """Test hybrid search combining vector and text."""
        block = MemoryBlock(
            id="block_1",
            session_id="session_1",
            content="Python programming language",
            memory_type=MemoryType.SEMANTIC,
            embedding=[0.1, 0.1, 0.1],
        )
        await store.upsert("session_1", [block])

        results = await store.hybrid_search(
            query_embedding=[0.1, 0.1, 0.1],
            query_text="Python",
            threshold=0.0,
        )

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_hybrid_search_text_only(self, store: FileVectorStore) -> None:
        """Test hybrid search with text only (no embedding match)."""
        block = MemoryBlock(
            id="block_1",
            session_id="session_1",
            content="Python programming",
            memory_type=MemoryType.SEMANTIC,
            embedding=None,
        )
        await store.upsert("session_1", [block])

        results = await store.hybrid_search(
            query_embedding=[0.0, 0.0, 0.0],
            query_text="Python",
            threshold=0.0,
        )

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_persistence(self, temp_storage: str) -> None:
        """Test that data persists after recreation."""
        block = MemoryBlock(
            id="block_persist",
            session_id="session_1",
            content="Persistent block",
            memory_type=MemoryType.SEMANTIC,
        )

        store1 = FileVectorStore(storage_path=temp_storage)
        await store1.upsert("session_1", [block])

        store2 = FileVectorStore(storage_path=temp_storage)

        assert "block_persist" in store2._blocks
        assert store2._blocks["block_persist"].content == "Persistent block"

    def test_load_corrupted_file(self, temp_storage: str) -> None:
        """Test loading from corrupted JSON file."""
        with open(temp_storage, "w") as f:
            f.write("invalid json content")

        with pytest.raises(VectorStoreError):
            FileVectorStore(storage_path=temp_storage)

    @pytest.mark.asyncio
    async def test_search_updates_accessed_at(self, store: FileVectorStore) -> None:
        """Test that search updates the accessed_at timestamp."""
        import time

        block = MemoryBlock(
            id="block_accessed",
            session_id="session_1",
            content="Test block",
            memory_type=MemoryType.SEMANTIC,
            embedding=[0.1, 0.1, 0.1],
        )
        await store.upsert("session_1", [block])
        original_time = store._blocks["block_accessed"].accessed_at

        time.sleep(0.01)
        await store.search(query_embedding=[0.1, 0.1, 0.1], threshold=0.0)

        assert store._blocks["block_accessed"].accessed_at > original_time
