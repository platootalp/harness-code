"""Context compactor for Mozi.

Provides context compression functionality to reduce token count
while preserving important information.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from mozi.context.models import (
    BuiltContext,
    CompressionResult,
    CompressionStrategy,
    ContextConfig,
)


class Compactor:
    """Compresses context to reduce token count.

    Provides various compression strategies to reduce context size
    while preserving essential information.

    Attributes:
        config: Configuration for compression.
    """

    def __init__(self, config: ContextConfig | None = None) -> None:
        """Initialize the compactor.

        Args:
            config: Configuration for context building/compression.
        """
        self.config = config or ContextConfig()

    async def compress(
        self,
        context: BuiltContext,
        strategy: CompressionStrategy | None = None,
    ) -> tuple[BuiltContext, CompressionResult]:
        """Compress the given context.

        Args:
            context: The context to compress.
            strategy: Override compression strategy. Uses config default if None.

        Returns:
            Tuple of (compressed context, compression result).
        """
        if strategy is None:
            strategy = self.config.compression_strategy

        original_tokens = context.total_tokens

        if strategy == CompressionStrategy.NONE:
            return context, CompressionResult(
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
                strategy_used=strategy,
            )

        compressed_context = await self._apply_compression(context, strategy)
        compressed_tokens = self._estimate_tokens(compressed_context)

        result = CompressionResult(
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            strategy_used=strategy,
            metadata={"method": strategy.value},
        )

        return compressed_context, result

    async def _apply_compression(
        self,
        context: BuiltContext,
        strategy: CompressionStrategy,
    ) -> BuiltContext:
        """Apply the compression strategy to the context.

        Args:
            context: The context to compress.
            strategy: The compression strategy to apply.

        Returns:
            Compressed context.
        """
        if strategy == CompressionStrategy.TRUNCATE:
            return self._truncate_context(context)
        elif strategy == CompressionStrategy.SUMMARIZE:
            return await self._summarize_context(context)
        elif strategy == CompressionStrategy.MIXED:
            return await self._mixed_compression(context)
        return context

    def _truncate_context(self, context: BuiltContext) -> BuiltContext:
        """Truncate context to fit within token limit.

        Args:
            context: The context to truncate.

        Returns:
            Truncated context.
        """
        target_tokens = int(self.config.max_tokens * 0.8)
        current_tokens = context.total_tokens

        if current_tokens <= target_tokens:
            return context

        ratio = target_tokens / current_tokens
        truncated_messages = context.messages[:int(len(context.messages) * ratio)]
        truncated_memory = context.memory_results[:int(len(context.memory_results) * ratio)]

        compressed = BuiltContext(
            system_prompt=context.system_prompt,
            messages=truncated_messages,
            memory_results=truncated_memory,
            config=context.config,
            metadata={**context.metadata, "compression": "truncate"},
        )
        compressed.total_tokens = self._estimate_tokens(compressed)
        return compressed

    async def _summarize_context(self, context: BuiltContext) -> BuiltContext:
        """Summarize context using a mock summarization.

        In production, this would call an LLM to summarize.

        Args:
            context: The context to summarize.

        Returns:
            Summarized context.
        """
        summarized_messages = context.messages
        if len(context.messages) > 5:
            summarized_messages = [
                f"[Summary of {len(context.messages) - 5} messages]: "
                f"Previous conversation discussed {' and '.join(context.messages[-1].split()[:5])}"
            ] + context.messages[-4:]

        summarized_memory = context.memory_results
        if len(context.memory_results) > 3:
            summarized_memory = [
                f"[Summary of {len(context.memory_results) - 3} memory entries]"
            ] + context.memory_results[-2:]

        compressed = BuiltContext(
            system_prompt=context.system_prompt,
            messages=summarized_messages,
            memory_results=summarized_memory,
            config=context.config,
            metadata={**context.metadata, "compression": "summarize"},
        )
        compressed.total_tokens = self._estimate_tokens(compressed)
        return compressed

    async def _mixed_compression(self, context: BuiltContext) -> BuiltContext:
        """Apply mixed compression strategy.

        Combines truncation and summarization based on context size.

        Args:
            context: The context to compress.

        Returns:
            Compressed context.
        """
        if len(context.messages) > 10:
            return await self._summarize_context(context)
        return self._truncate_context(context)

    async def create_snapshot(
        self,
        context: BuiltContext,
        name: str | None = None,
    ) -> dict[str, Any]:
        """Create a serializable snapshot of the context.

        Args:
            context: The context to snapshot.
            name: Optional name for the snapshot.

        Returns:
            Dictionary representation of the snapshot.
        """
        return {
            "name": name,
            "created_at": datetime.now(UTC).isoformat(),
            "context": context.to_dict(),
            "tokens": context.total_tokens,
        }

    async def merge_snapshots(
        self,
        snapshots: list[dict[str, Any]],
    ) -> BuiltContext | None:
        """Merge multiple context snapshots into one.

        Args:
            snapshots: List of snapshot dictionaries.

        Returns:
            Merged context, or None if snapshots list is empty.
        """
        if not snapshots:
            return None

        all_messages: list[str] = []
        all_memory: list[str] = []

        for snapshot in snapshots:
            ctx_data = snapshot.get("context", {})
            all_messages.extend(ctx_data.get("messages", []))
            all_memory.extend(ctx_data.get("memory_results", []))

        snapshot_names = [s.get("name") for s in snapshots]
        merged = BuiltContext(
            system_prompt=snapshots[0].get("context", {}).get("system_prompt", ""),
            messages=all_messages,
            memory_results=all_memory,
            metadata={"merged_from": len(snapshots), "snapshot_names": snapshot_names},
        )
        merged.total_tokens = self._estimate_tokens(merged)
        return merged

    def _estimate_tokens(self, context: BuiltContext) -> int:
        """Estimate token count for a context.

        Args:
            context: The context to estimate.

        Returns:
            Estimated token count.
        """
        total = context.estimate_tokens(context.system_prompt)
        for msg in context.messages:
            total += context.estimate_tokens(msg)
        for mem in context.memory_results:
            total += context.estimate_tokens(mem)
        return total
