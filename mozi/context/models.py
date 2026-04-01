"""Context data models for Mozi.

Defines the core data structures for context management:
- BuiltContext: Final context after building and compression
- ContextConfig: Configuration for context building
- CompressionResult: Result of context compression
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class CompressionStrategy(Enum):
    """Strategy for context compression."""

    NONE = "none"
    TRUNCATE = "truncate"
    SUMMARIZE = "summarize"
    MIXED = "mixed"


@dataclass
class ContextConfig:
    """Configuration for context building.

    Attributes:
        max_tokens: Maximum tokens allowed in context.
        compression_strategy: Strategy to use when context exceeds limit.
        system_prompt: System prompt template.
        include_history: Whether to include conversation history.
        include_memory: Whether to include memory retrieval results.
    """

    max_tokens: int = 100000
    compression_strategy: CompressionStrategy = CompressionStrategy.MIXED
    system_prompt: str | None = None
    include_history: bool = True
    include_memory: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "max_tokens": self.max_tokens,
            "compression_strategy": self.compression_strategy.value,
            "system_prompt": self.system_prompt,
            "include_history": self.include_history,
            "include_memory": self.include_memory,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ContextConfig:
        """Create config from dictionary."""
        strategy_str = data.get("compression_strategy", "mixed")
        try:
            if isinstance(strategy_str, str):
                strategy = CompressionStrategy(strategy_str)
            else:
                strategy = CompressionStrategy.MIXED
        except ValueError:
            strategy = CompressionStrategy.MIXED
        return cls(
            max_tokens=data.get("max_tokens", 100000),
            compression_strategy=strategy,
            system_prompt=data.get("system_prompt"),
            include_history=data.get("include_history", True),
            include_memory=data.get("include_memory", True),
        )


@dataclass
class CompressionResult:
    """Result of a context compression operation.

    Attributes:
        original_tokens: Number of tokens before compression.
        compressed_tokens: Number of tokens after compression.
        strategy_used: The compression strategy that was applied.
        timestamp: When the compression was performed.
        metadata: Additional metadata about the compression.
    """

    original_tokens: int
    compressed_tokens: int
    strategy_used: CompressionStrategy
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def compression_ratio(self) -> float:
        """Calculate the compression ratio."""
        if self.original_tokens == 0:
            return 1.0
        return 1.0 - (self.compressed_tokens / self.original_tokens)

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "original_tokens": self.original_tokens,
            "compressed_tokens": self.compressed_tokens,
            "strategy_used": self.strategy_used.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "compression_ratio": self.compression_ratio,
        }


@dataclass
class BuiltContext:
    """Final built context ready for model input.

    Attributes:
        system_prompt: The system prompt content.
        messages: List of message contents (user/assistant).
        memory_results: Retrieved memory content.
        config: The config used to build this context.
        total_tokens: Total token count.
        created_at: When the context was built.
        metadata: Additional context metadata.
    """

    system_prompt: str
    messages: list[str] = field(default_factory=list)
    memory_results: list[str] = field(default_factory=list)
    config: ContextConfig = field(default_factory=ContextConfig)
    total_tokens: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert context to dictionary."""
        return {
            "system_prompt": self.system_prompt,
            "messages": self.messages,
            "memory_results": self.memory_results,
            "config": self.config.to_dict(),
            "total_tokens": self.total_tokens,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    def get_full_prompt(self) -> str:
        """Get the full prompt string for model input."""
        parts: list[str] = []
        if self.system_prompt:
            parts.append(f"System: {self.system_prompt}")
        if self.memory_results:
            parts.append(f"Memory: {' '.join(self.memory_results)}")
        for msg in self.messages:
            parts.append(msg)
        return "\n\n".join(parts)

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text (rough approximation)."""
        return len(text) // 4
