"""Context window manager for Mozi.

Manages the context window by tracking usage and determining
when compression or offloading is needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from mozi.context.models import BuiltContext, CompressionStrategy, ContextConfig


@dataclass
class WindowSnapshot:
    """A snapshot of the context window at a point in time.

    Attributes:
        context: The built context at snapshot time.
        taken_at: When the snapshot was taken.
        reason: Why the snapshot was taken.
    """

    context: BuiltContext
    taken_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    reason: str = "manual"


class WindowManager:
    """Manages the context window and determines when to compress/offload.

    Tracks context token usage and provides methods to check if
    compression or offloading is needed.

    Attributes:
        config: Configuration for the window manager.
        _snapshots: List of context snapshots.
    """

    DEFAULT_THRESHOLD_RATIO = 0.8

    def __init__(
        self,
        config: ContextConfig | None = None,
        threshold_ratio: float | None = None,
    ) -> None:
        """Initialize the window manager.

        Args:
            config: Configuration for context building.
            threshold_ratio: Token threshold as ratio of max_tokens.
        """
        self.config = config or ContextConfig()
        self._threshold_ratio = threshold_ratio or self.DEFAULT_THRESHOLD_RATIO
        self._snapshots: list[WindowSnapshot] = []

    @property
    def max_tokens(self) -> int:
        """Get the maximum allowed tokens."""
        return self.config.max_tokens

    @property
    def threshold_tokens(self) -> int:
        """Get the threshold for triggering actions."""
        return int(self.max_tokens * self._threshold_ratio)

    def check_threshold(self, current_tokens: int) -> bool:
        """Check if current tokens exceed the threshold.

        Args:
            current_tokens: Current token count.

        Returns:
            True if threshold is exceeded.
        """
        return current_tokens >= self.threshold_tokens

    def should_compress(self, context: BuiltContext) -> bool:
        """Determine if the context should be compressed.

        Args:
            context: The context to check.

        Returns:
            True if compression is recommended.
        """
        if self.config.compression_strategy == CompressionStrategy.NONE:
            return False

        if context.total_tokens >= self.threshold_tokens:
            return True

        return False

    def get_snapshot(self, context: BuiltContext, reason: str = "manual") -> WindowSnapshot:
        """Take a snapshot of the current context.

        Args:
            context: The context to snapshot.
            reason: Reason for taking the snapshot.

        Returns:
            The created snapshot.
        """
        snapshot = WindowSnapshot(context=context, reason=reason)
        self._snapshots.append(snapshot)
        return snapshot

    def get_recent_snapshots(self, limit: int = 10) -> list[WindowSnapshot]:
        """Get the most recent snapshots.

        Args:
            limit: Maximum number of snapshots to return.

        Returns:
            List of recent snapshots, newest first.
        """
        if limit <= 0:
            return []
        return list(reversed(self._snapshots[-limit:]))

    def clear_old_snapshots(self, max_age: timedelta | None = None) -> int:
        """Clear snapshots older than the specified age.

        Args:
            max_age: Maximum age of snapshots to keep. Defaults to 1 hour.

        Returns:
            Number of snapshots removed.
        """
        if max_age is None:
            max_age = timedelta(hours=1)

        cutoff = datetime.now(UTC) - max_age
        original_count = len(self._snapshots)
        self._snapshots = [s for s in self._snapshots if s.taken_at >= cutoff]
        return original_count - len(self._snapshots)

    def get_snapshot_stats(self) -> dict[str, Any]:
        """Get statistics about snapshots.

        Returns:
            Dictionary of snapshot statistics.
        """
        if not self._snapshots:
            return {"count": 0, "total_tokens": 0}

        return {
            "count": len(self._snapshots),
            "total_tokens": sum(s.context.total_tokens for s in self._snapshots),
            "oldest": self._snapshots[0].taken_at.isoformat() if self._snapshots else None,
            "newest": self._snapshots[-1].taken_at.isoformat() if self._snapshots else None,
        }
