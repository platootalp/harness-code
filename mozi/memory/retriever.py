"""Memory retriever implementation for the Mozi AI Coding Agent.

The retriever provides unified access to both short-term and long-term
memory with hybrid search capabilities.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from mozi.infrastructure.vector_db import MemoryBlock, MemoryType
from mozi.memory.long_term import LongTermMemory
from mozi.memory.short_term import ShortTermMemory, ShortTermMemoryEntry


@dataclass
class RetrievedMemory:
    """A retrieved memory entry with relevance score.

    Attributes:
        block: The memory block retrieved.
        score: Relevance score from 0.0 to 1.0.
        source: Source of the memory ('short_term', 'long_term', or 'hybrid').
    """

    block: MemoryBlock | ShortTermMemoryEntry
    score: float
    source: str


class MemoryRetriever:
    """Unified memory retrieval across short-term and long-term stores.

    This class provides a single interface for retrieving memories
    using various strategies including recall, hybrid search, and reranking.

    Attributes:
        short_term: The short-term memory store.
        long_term: The long-term memory store.
    """

    def __init__(
        self,
        short_term: ShortTermMemory,
        long_term: LongTermMemory,
    ) -> None:
        """Initialize the memory retriever.

        Args:
            short_term: The short-term memory store.
            long_term: The long-term memory store.
        """
        self.short_term = short_term
        self.long_term = long_term

    async def recall(
        self,
        query_embedding: list[float],
        memory_type: MemoryType | None = None,
        top_k: int = 5,
        threshold: float = 0.7,
    ) -> list[RetrievedMemory]:
        """Recall memories using vector similarity search.

        This method searches long-term memory for semantically similar
        memories based on the provided query embedding.

        Args:
            query_embedding: The query vector to search with.
            memory_type: Optional filter by memory type.
            top_k: Maximum number of results to return. Defaults to 5.
            threshold: Minimum similarity score threshold. Defaults to 0.7.

        Returns:
            List of retrieved memories with relevance scores.
        """
        results = await self.long_term.search(
            query_embedding=query_embedding,
            memory_type=memory_type,
            top_k=top_k,
            threshold=threshold,
        )

        return [
            RetrievedMemory(block=block, score=score, source="long_term")
            for block, score in results
        ]

    async def hybrid_search(
        self,
        query_embedding: list[float],
        query_text: str | None = None,
        memory_type: MemoryType | None = None,
        top_k: int = 5,
        threshold: float = 0.7,
    ) -> list[RetrievedMemory]:
        """Perform hybrid search combining vector and text similarity.

        This method searches long-term memory using both vector embeddings
        and optional text matching for improved recall.

        Args:
            query_embedding: The query vector for similarity search.
            query_text: Optional text query for keyword matching.
            memory_type: Optional filter by memory type.
            top_k: Maximum number of results to return. Defaults to 5.
            threshold: Minimum similarity score threshold. Defaults to 0.7.

        Returns:
            List of retrieved memories with combined relevance scores.
        """
        results = await self.long_term.store.hybrid_search(
            query_embedding=query_embedding,
            query_text=query_text,
            session_id=self.long_term.session_id,
            memory_type=memory_type,
            top_k=top_k,
            threshold=threshold,
        )

        return [
            RetrievedMemory(block=block, score=score, source="hybrid")
            for block, score in results
        ]

    def rerank(
        self,
        memories: list[RetrievedMemory],
        importance_weight: float = 0.3,
        recency_weight: float = 0.2,
    ) -> list[RetrievedMemory]:
        """Rerank retrieved memories using importance and recency factors.

        This method adjusts the scores of retrieved memories based on
        importance scores and access recency.

        Args:
            memories: List of retrieved memories to rerank.
            importance_weight: Weight for importance score (0.0 to 1.0).
                              Defaults to 0.3.
            recency_weight: Weight for recency score (0.0 to 1.0).
                          Defaults to 0.2.

        Returns:
            Reranked list of memories, highest score first.
        """
        now = datetime.now()

        def get_recency_score(mem: RetrievedMemory) -> float:
            """Calculate recency score based on accessed_at timestamp."""
            if isinstance(mem.block, MemoryBlock):
                accessed = mem.block.accessed_at
                age = (now - accessed).total_seconds()
                return max(0.0, 1.0 - (age / (7 * 24 * 3600)))
            return 0.5

        def get_importance_score(mem: RetrievedMemory) -> float:
            """Get importance score from the memory block."""
            if isinstance(mem.block, MemoryBlock):
                return mem.block.importance
            return 0.5

        reranked: list[RetrievedMemory] = []
        for mem in memories:
            base_score = mem.score
            importance = get_importance_score(mem)
            recency = get_recency_score(mem)

            adjusted_score = (
                base_score * (1.0 - importance_weight - recency_weight)
                + importance * importance_weight
                + recency * recency_weight
            )

            reranked.append(
                RetrievedMemory(
                    block=mem.block,
                    score=adjusted_score,
                    source=mem.source,
                )
            )

        reranked.sort(key=lambda x: x.score, reverse=True)
        return reranked

    def get_short_term_context(self, limit: int = 10) -> list[ShortTermMemoryEntry]:
        """Get recent entries from short-term memory.

        Args:
            limit: Maximum number of entries to return. Defaults to 10.

        Returns:
            List of recent short-term memory entries.
        """
        return self.short_term.get_recent(limit=limit)
