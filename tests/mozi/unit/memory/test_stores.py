"""Unit tests for the memory stores."""

import pytest

from mozi.memory.stores.milvus import MilvusMemoryStore
from mozi.memory.stores.pgvector import PGVectorMemoryStore


class TestMilvusMemoryStore:
    """Tests for MilvusMemoryStore class."""

    def test_initialization(self) -> None:
        """Test initializing the Milvus store."""
        store = MilvusMemoryStore(
            host="localhost",
            port=19530,
            collection="test_collection",
            dimension=768,
        )

        assert store.host == "localhost"
        assert store.port == 19530
        assert store.collection == "test_collection"
        assert store.dimension == 768

    def test_initialization_defaults(self) -> None:
        """Test initializing with default values."""
        store = MilvusMemoryStore()

        assert store.host == "localhost"
        assert store.port == 19530
        assert store.collection == "mozi_memory"
        assert store.dimension == 1536

    @pytest.mark.asyncio
    async def test_upsert_not_implemented(self) -> None:
        """Test that upsert raises NotImplementedError."""
        store = MilvusMemoryStore()

        with pytest.raises(NotImplementedError, match="Milvus integration coming soon"):
            await store.upsert("session", [])

    @pytest.mark.asyncio
    async def test_search_not_implemented(self) -> None:
        """Test that search raises NotImplementedError."""
        store = MilvusMemoryStore()

        with pytest.raises(NotImplementedError, match="Milvus integration coming soon"):
            await store.search([0.1] * 128)

    @pytest.mark.asyncio
    async def test_delete_not_implemented(self) -> None:
        """Test that delete raises NotImplementedError."""
        store = MilvusMemoryStore()

        with pytest.raises(NotImplementedError, match="Milvus integration coming soon"):
            await store.delete("block_id")

    @pytest.mark.asyncio
    async def test_hybrid_search_not_implemented(self) -> None:
        """Test that hybrid_search raises NotImplementedError."""
        store = MilvusMemoryStore()

        with pytest.raises(NotImplementedError, match="Milvus integration coming soon"):
            await store.hybrid_search([0.1] * 128, query_text="test")


class TestPGVectorMemoryStore:
    """Tests for PGVectorMemoryStore class."""

    def test_initialization(self) -> None:
        """Test initializing the PGVector store."""
        store = PGVectorMemoryStore(
            host="localhost",
            port=5432,
            database="test_db",
            user="test_user",
            table="test_table",
        )

        assert store.host == "localhost"
        assert store.port == 5432
        assert store.database == "test_db"
        assert store.user == "test_user"
        assert store.table == "test_table"

    def test_initialization_defaults(self) -> None:
        """Test initializing with default values."""
        store = PGVectorMemoryStore()

        assert store.host == "localhost"
        assert store.port == 5432
        assert store.database == "mozi"
        assert store.user == "postgres"
        assert store.table == "mozi_memory"

    def test_initialization_with_password(self) -> None:
        """Test initializing with password."""
        store = PGVectorMemoryStore(password="secret")

        assert store.password == "secret"

    @pytest.mark.asyncio
    async def test_upsert_not_implemented(self) -> None:
        """Test that upsert raises NotImplementedError."""
        store = PGVectorMemoryStore()

        with pytest.raises(NotImplementedError, match="PGVector integration coming soon"):
            await store.upsert("session", [])

    @pytest.mark.asyncio
    async def test_search_not_implemented(self) -> None:
        """Test that search raises NotImplementedError."""
        store = PGVectorMemoryStore()

        with pytest.raises(NotImplementedError, match="PGVector integration coming soon"):
            await store.search([0.1] * 128)

    @pytest.mark.asyncio
    async def test_delete_not_implemented(self) -> None:
        """Test that delete raises NotImplementedError."""
        store = PGVectorMemoryStore()

        with pytest.raises(NotImplementedError, match="PGVector integration coming soon"):
            await store.delete("block_id")

    @pytest.mark.asyncio
    async def test_hybrid_search_not_implemented(self) -> None:
        """Test that hybrid_search raises NotImplementedError."""
        store = PGVectorMemoryStore()

        with pytest.raises(NotImplementedError, match="PGVector integration coming soon"):
            await store.hybrid_search([0.1] * 128, query_text="test")
