"""Vector store abstraction with multiple backends.

This module provides a unified interface for vector storage operations
across different backends (Milvus, PGVector, File-based).
"""

from __future__ import annotations

import json
import math
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from mozi.exceptions import MemoryNotFoundError, VectorStoreError


class MemoryType(Enum):
    """Enumeration of memory types in the system."""

    SHORT_TERM = "short_term"
    SEMANTIC = "semantic"
    EPISODIC = "episodic"
    PROCEDURAL = "procedural"


@dataclass
class MemoryBlock:
    """A block of memory stored in the vector database.

    Attributes:
        id: Unique identifier for the memory block.
        session_id: ID of the session this memory belongs to.
        content: The textual content of the memory.
        memory_type: The type of memory (short_term, semantic, episodic, procedural).
        embedding: Optional vector embedding of the content.
        importance: Importance score from 0.0 to 1.0.
        status: Current status of the memory (active, archived, etc.).
        created_at: Timestamp when the memory was created.
        accessed_at: Timestamp when the memory was last accessed.
        metadata: Additional metadata associated with the memory.
    """

    id: str
    session_id: str
    content: str
    memory_type: MemoryType
    embedding: list[float] | None = None
    importance: float = 0.5
    status: str = "active"
    created_at: datetime = field(default_factory=datetime.now)
    accessed_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert the memory block to a dictionary.

        Returns:
            A dictionary representation of the memory block.
        """
        return {
            "id": self.id,
            "session_id": self.session_id,
            "content": self.content,
            "memory_type": self.memory_type.value,
            "embedding": self.embedding,
            "importance": self.importance,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "accessed_at": self.accessed_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryBlock:
        """Create a memory block from a dictionary.

        Args:
            data: Dictionary containing memory block data.

        Returns:
            A MemoryBlock instance.
        """
        return cls(
            id=data["id"],
            session_id=data["session_id"],
            content=data["content"],
            memory_type=MemoryType(data["memory_type"]),
            embedding=data.get("embedding"),
            importance=data.get("importance", 0.5),
            status=data.get("status", "active"),
            created_at=datetime.fromisoformat(data["created_at"]),
            accessed_at=datetime.fromisoformat(data["accessed_at"]),
            metadata=data.get("metadata", {}),
        )


class VectorStore(ABC):
    """Abstract base class for vector store implementations.

    This class defines the interface that all vector store backends
    must implement.
    """

    @abstractmethod
    async def upsert(self, session_id: str, blocks: list[MemoryBlock]) -> None:
        """Insert or update memory blocks.

        Args:
            session_id: The session ID these blocks belong to.
            blocks: List of memory blocks to insert or update.
        """

    @abstractmethod
    async def search(
        self,
        query_embedding: list[float],
        session_id: str | None = None,
        memory_type: MemoryType | None = None,
        top_k: int = 5,
        threshold: float = 0.7,
    ) -> list[tuple[MemoryBlock, float]]:
        """Search for similar memories using vector similarity.

        Args:
            query_embedding: The query vector to search with.
            session_id: Optional filter by session ID.
            memory_type: Optional filter by memory type.
            top_k: Maximum number of results to return.
            threshold: Minimum similarity score threshold (0.0 to 1.0).

        Returns:
            List of tuples containing (MemoryBlock, similarity_score).
        """

    @abstractmethod
    async def delete(self, block_id: str) -> bool:
        """Delete a memory block.

        Args:
            block_id: The ID of the memory block to delete.

        Returns:
            True if the block was deleted, False if it was not found.
        """

    @abstractmethod
    async def hybrid_search(
        self,
        query_embedding: list[float],
        query_text: str | None = None,
        session_id: str | None = None,
        memory_type: MemoryType | None = None,
        top_k: int = 5,
        threshold: float = 0.7,
    ) -> list[tuple[MemoryBlock, float]]:
        """Hybrid search combining vector and text similarity.

        Args:
            query_embedding: The query vector for similarity search.
            query_text: Optional text query for keyword matching.
            session_id: Optional filter by session ID.
            memory_type: Optional filter by memory type.
            top_k: Maximum number of results to return.
            threshold: Minimum similarity score threshold (0.0 to 1.0).

        Returns:
            List of tuples containing (MemoryBlock, combined_score).
        """


class MilvusVectorStore(VectorStore):
    """Milvus backend implementation for vector storage.

    This implementation uses the Milvus vector database for
    storage and similarity search operations.
    """

    def __init__(self, host: str = "localhost", port: int = 19530, **kwargs: Any) -> None:
        """Initialize the Milvus vector store.

        Args:
            host: Milvus server host.
            port: Milvus server port.
            **kwargs: Additional connection parameters.
        """
        self.host = host
        self.port = port
        self.kwargs = kwargs
        self._client = None

    async def upsert(self, session_id: str, blocks: list[MemoryBlock]) -> None:
        """Insert or update memory blocks in Milvus.

        Args:
            session_id: The session ID these blocks belong to.
            blocks: List of memory blocks to insert or update.

        Raises:
            NotImplementedError: Milvus integration coming soon.
        """
        raise NotImplementedError("Milvus integration coming soon")

    async def search(
        self,
        query_embedding: list[float],
        session_id: str | None = None,
        memory_type: MemoryType | None = None,
        top_k: int = 5,
        threshold: float = 0.7,
    ) -> list[tuple[MemoryBlock, float]]:
        """Search for similar memories in Milvus.

        Args:
            query_embedding: The query vector to search with.
            session_id: Optional filter by session ID.
            memory_type: Optional filter by memory type.
            top_k: Maximum number of results to return.
            threshold: Minimum similarity score threshold.

        Returns:
            List of tuples containing (MemoryBlock, similarity_score).

        Raises:
            NotImplementedError: Milvus integration coming soon.
        """
        raise NotImplementedError("Milvus integration coming soon")

    async def delete(self, block_id: str) -> bool:
        """Delete a memory block from Milvus.

        Args:
            block_id: The ID of the memory block to delete.

        Returns:
            True if the block was deleted.

        Raises:
            NotImplementedError: Milvus integration coming soon.
        """
        raise NotImplementedError("Milvus integration coming soon")

    async def hybrid_search(
        self,
        query_embedding: list[float],
        query_text: str | None = None,
        session_id: str | None = None,
        memory_type: MemoryType | None = None,
        top_k: int = 5,
        threshold: float = 0.7,
    ) -> list[tuple[MemoryBlock, float]]:
        """Hybrid search in Milvus combining vector and text similarity.

        Args:
            query_embedding: The query vector for similarity search.
            query_text: Optional text query for keyword matching.
            session_id: Optional filter by session ID.
            memory_type: Optional filter by memory type.
            top_k: Maximum number of results to return.
            threshold: Minimum similarity score threshold.

        Returns:
            List of tuples containing (MemoryBlock, combined_score).

        Raises:
            NotImplementedError: Milvus integration coming soon.
        """
        raise NotImplementedError("Milvus integration coming soon")


class PGVectorStore(VectorStore):
    """PostgreSQL/PGVector backend implementation for vector storage.

    This implementation uses PostgreSQL with the pgvector extension
    for storage and similarity search operations.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "src",
        user: str = "postgres",
        password: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the PGVector store.

        Args:
            host: PostgreSQL server host.
            port: PostgreSQL server port.
            database: Database name.
            user: Database user.
            password: Database password.
            **kwargs: Additional connection parameters.
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.kwargs = kwargs
        self._pool = None

    async def upsert(self, session_id: str, blocks: list[MemoryBlock]) -> None:
        """Insert or update memory blocks in PostgreSQL.

        Args:
            session_id: The session ID these blocks belong to.
            blocks: List of memory blocks to insert or update.

        Raises:
            NotImplementedError: PGVector integration coming soon.
        """
        raise NotImplementedError("PGVector integration coming soon")

    async def search(
        self,
        query_embedding: list[float],
        session_id: str | None = None,
        memory_type: MemoryType | None = None,
        top_k: int = 5,
        threshold: float = 0.7,
    ) -> list[tuple[MemoryBlock, float]]:
        """Search for similar memories in PostgreSQL.

        Args:
            query_embedding: The query vector to search with.
            session_id: Optional filter by session ID.
            memory_type: Optional filter by memory type.
            top_k: Maximum number of results to return.
            threshold: Minimum similarity score threshold.

        Returns:
            List of tuples containing (MemoryBlock, similarity_score).

        Raises:
            NotImplementedError: PGVector integration coming soon.
        """
        raise NotImplementedError("PGVector integration coming soon")

    async def delete(self, block_id: str) -> bool:
        """Delete a memory block from PostgreSQL.

        Args:
            block_id: The ID of the memory block to delete.

        Returns:
            True if the block was deleted.

        Raises:
            NotImplementedError: PGVector integration coming soon.
        """
        raise NotImplementedError("PGVector integration coming soon")

    async def hybrid_search(
        self,
        query_embedding: list[float],
        query_text: str | None = None,
        session_id: str | None = None,
        memory_type: MemoryType | None = None,
        top_k: int = 5,
        threshold: float = 0.7,
    ) -> list[tuple[MemoryBlock, float]]:
        """Hybrid search in PostgreSQL combining vector and text similarity.

        Args:
            query_embedding: The query vector for similarity search.
            query_text: Optional text query for keyword matching.
            session_id: Optional filter by session ID.
            memory_type: Optional filter by memory type.
            top_k: Maximum number of results to return.
            threshold: Minimum similarity score threshold.

        Returns:
            List of tuples containing (MemoryBlock, combined_score).

        Raises:
            NotImplementedError: PGVector integration coming soon.
        """
        raise NotImplementedError("PGVector integration coming soon")


class FileVectorStore(VectorStore):
    """File-based vector store implementation for testing and lightweight usage.

    This implementation uses an in-memory dictionary with JSON file
    persistence for storage and computes cosine similarity for search.
    """

    def __init__(self, storage_path: str | None = None) -> None:
        """Initialize the file-based vector store.

        Args:
            storage_path: Optional path to the JSON file for persistence.
                          If not provided, uses 'vector_store.json' in the
                          current working directory.
        """
        if storage_path is None:
            storage_path = os.path.join(os.getcwd(), "vector_store.json")
        self.storage_path = storage_path
        self._blocks: dict[str, MemoryBlock] = {}
        self._load()

    def _load(self) -> None:
        """Load memory blocks from the JSON file."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path) as f:
                    content = f.read()
                    if not content:
                        return
                    data = json.loads(content)
                    for block_data in data.values():
                        block = MemoryBlock.from_dict(block_data)
                        self._blocks[block.id] = block
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                raise VectorStoreError(f"Failed to load vector store: {e}") from e

    def _persist(self) -> None:
        """Persist memory blocks to the JSON file."""
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                data = {block_id: block.to_dict() for block_id, block in self._blocks.items()}
                json.dump(data, f, indent=4, ensure_ascii=False)
        except OSError as e:
            raise VectorStoreError(f"Failed to persist vector store: {e}") from e

    @staticmethod
    def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
        """Compute cosine similarity between two vectors.

        Args:
            vec1: First vector.
            vec2: Second vector.

        Returns:
            Cosine similarity score between 0.0 and 1.0.
        """
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=True))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0.0 or magnitude2 == 0.0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    async def upsert(self, session_id: str, blocks: list[MemoryBlock]) -> None:
        """Insert or update memory blocks.

        Args:
            session_id: The session ID these blocks belong to.
            blocks: List of memory blocks to insert or update.
        """
        for block in blocks:
            block.session_id = session_id
            self._blocks[block.id] = block
        self._persist()

    async def search(
        self,
        query_embedding: list[float],
        session_id: str | None = None,
        memory_type: MemoryType | None = None,
        top_k: int = 5,
        threshold: float = 0.7,
    ) -> list[tuple[MemoryBlock, float]]:
        """Search for similar memories using cosine similarity.

        Args:
            query_embedding: The query vector to search with.
            session_id: Optional filter by session ID.
            memory_type: Optional filter by memory type.
            top_k: Maximum number of results to return.
            threshold: Minimum similarity score threshold (0.0 to 1.0).

        Returns:
            List of tuples containing (MemoryBlock, similarity_score).
        """
        results: list[tuple[MemoryBlock, float]] = []

        for block in self._blocks.values():
            if block.embedding is None:
                continue

            if session_id is not None and block.session_id != session_id:
                continue

            if memory_type is not None and block.memory_type != memory_type:
                continue

            similarity = self._cosine_similarity(query_embedding, block.embedding)
            if similarity >= threshold:
                block.accessed_at = datetime.now()
                results.append((block, similarity))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    async def delete(self, block_id: str) -> bool:
        """Delete a memory block.

        Args:
            block_id: The ID of the memory block to delete.

        Returns:
            True if the block was deleted, False if it was not found.
        """
        if block_id not in self._blocks:
            raise MemoryNotFoundError(f"Memory block not found: {block_id}")

        del self._blocks[block_id]
        self._persist()
        return True

    async def hybrid_search(
        self,
        query_embedding: list[float],
        query_text: str | None = None,
        session_id: str | None = None,
        memory_type: MemoryType | None = None,
        top_k: int = 5,
        threshold: float = 0.7,
    ) -> list[tuple[MemoryBlock, float]]:
        """Hybrid search combining vector and text similarity.

        For text-based similarity, this implementation uses simple
        keyword matching (count of query terms in content).

        Args:
            query_embedding: The query vector for similarity search.
            query_text: Optional text query for keyword matching.
            session_id: Optional filter by session ID.
            memory_type: Optional filter by memory type.
            top_k: Maximum number of results to return.
            threshold: Minimum similarity score threshold (0.0 to 1.0).

        Returns:
            List of tuples containing (MemoryBlock, combined_score).
        """
        results: list[tuple[MemoryBlock, float]] = []

        query_terms: list[str] = []
        if query_text:
            query_terms = query_text.lower().split()

        for block in self._blocks.values():
            vector_score = 0.0
            text_score = 0.0

            if block.embedding is not None:
                vector_score = self._cosine_similarity(query_embedding, block.embedding)

            if query_terms and block.content:
                content_lower = block.content.lower()
                matches = sum(1 for term in query_terms if term in content_lower)
                text_score = matches / len(query_terms)

            combined_score = (vector_score + text_score) / 2

            if session_id is not None and block.session_id != session_id:
                continue

            if memory_type is not None and block.memory_type != memory_type:
                continue

            if combined_score >= threshold:
                block.accessed_at = datetime.now()
                results.append((block, combined_score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
