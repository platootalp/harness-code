"""Long-term memory implementation for the Mozi AI Coding Agent.

Long-term memory stores important information that persists across
sessions and can be searched using vector similarity.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from mozi.exceptions import MemoryNotFoundError
from mozi.infrastructure.vector_db import (
    MemoryBlock,
    MemoryType,
    VectorStore,
)


class LongTermMemory:
    """Long-term memory store with vector-based search.

    This class manages persistent memory blocks that can be searched
    using vector embeddings or hybrid text+vector queries.

    Attributes:
        store: The underlying vector store backend.
        session_id: The session ID this memory belongs to.
    """

    def __init__(
        self,
        store: VectorStore,
        session_id: str,
    ) -> None:
        """Initialize long-term memory.

        Args:
            store: The vector store backend to use.
            session_id: The session ID this memory belongs to.
        """
        self.store = store
        self.session_id = session_id

    async def add(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.SEMANTIC,
        embedding: list[float] | None = None,
        importance: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryBlock:
        """Add a new memory block to long-term storage.

        Args:
            content: The content to store.
            memory_type: The type of memory. Defaults to SEMANTIC.
            embedding: Optional vector embedding for the content.
            importance: Importance score from 0.0 to 1.0. Defaults to 0.5.
            metadata: Optional metadata to associate with this block.

        Returns:
            The created memory block.
        """
        block_id = f"ltm_{self.session_id}_{datetime.now().timestamp()}"
        block = MemoryBlock(
            id=block_id,
            session_id=self.session_id,
            content=content,
            memory_type=memory_type,
            embedding=embedding,
            importance=importance,
            metadata=metadata or {},
        )
        await self.store.upsert(self.session_id, [block])
        return block

    async def search(
        self,
        query_embedding: list[float],
        memory_type: MemoryType | None = None,
        top_k: int = 5,
        threshold: float = 0.7,
    ) -> list[tuple[MemoryBlock, float]]:
        """Search for similar memories using vector similarity.

        Args:
            query_embedding: The query vector to search with.
            memory_type: Optional filter by memory type.
            top_k: Maximum number of results to return. Defaults to 5.
            threshold: Minimum similarity score threshold. Defaults to 0.7.

        Returns:
            List of tuples containing (MemoryBlock, similarity_score).
        """
        return await self.store.search(
            query_embedding=query_embedding,
            session_id=self.session_id,
            memory_type=memory_type,
            top_k=top_k,
            threshold=threshold,
        )

    async def delete(self, block_id: str) -> bool:
        """Delete a memory block from long-term storage.

        Args:
            block_id: The ID of the memory block to delete.

        Returns:
            True if the block was deleted.

        Raises:
            MemoryNotFoundError: If the block does not exist.
        """
        try:
            return await self.store.delete(block_id)
        except MemoryNotFoundError:
            raise

    async def update_importance(self, block_id: str, importance: float) -> MemoryBlock | None:
        """Update the importance score of a memory block.

        Args:
            block_id: The ID of the memory block to update.
            importance: New importance score from 0.0 to 1.0.

        Returns:
            The updated memory block, or None if not found.
        """
        results = await self.store.search(
            query_embedding=[0.0] * 128,
            session_id=self.session_id,
            top_k=1000,
            threshold=0.0,
        )

        for block, _ in results:
            if block.id == block_id:
                block.importance = max(0.0, min(1.0, importance))
                await self.store.upsert(self.session_id, [block])
                return block

        return None

    async def get_by_id(self, block_id: str) -> MemoryBlock | None:
        """Get a specific memory block by its ID.

        Args:
            block_id: The ID of the memory block to retrieve.

        Returns:
            The memory block if found, None otherwise.
        """
        results = await self.store.search(
            query_embedding=[0.0] * 128,
            session_id=self.session_id,
            top_k=1000,
            threshold=0.0,
        )

        for block, _ in results:
            if block.id == block_id:
                return block

        return None
