"""Tests for context window manager."""

from __future__ import annotations

from datetime import timedelta

import pytest

from mozi.context.models import BuiltContext, CompressionStrategy, ContextConfig
from mozi.context.window import WindowManager, WindowSnapshot


@pytest.mark.unit
class TestWindowManager:
    """Tests for WindowManager class."""

    def test_init_default(self) -> None:
        """Test initialization with defaults."""
        manager = WindowManager()
        assert manager.max_tokens == 100000
        assert manager.threshold_tokens == 80000
        assert len(manager._snapshots) == 0

    def test_init_custom_config(self) -> None:
        """Test initialization with custom config."""
        config = ContextConfig(max_tokens=50000)
        manager = WindowManager(config=config)
        assert manager.max_tokens == 50000
        assert manager.threshold_tokens == 40000

    def test_init_custom_threshold_ratio(self) -> None:
        """Test initialization with custom threshold ratio."""
        manager = WindowManager(threshold_ratio=0.5)
        assert manager.threshold_tokens == 50000

    def test_check_threshold_below(self) -> None:
        """Test threshold check when below."""
        manager = WindowManager()
        result = manager.check_threshold(50000)
        assert result is False

    def test_check_threshold_at(self) -> None:
        """Test threshold check when at threshold."""
        manager = WindowManager()
        result = manager.check_threshold(80000)
        assert result is True

    def test_check_threshold_above(self) -> None:
        """Test threshold check when above."""
        manager = WindowManager()
        result = manager.check_threshold(90000)
        assert result is True

    def test_should_compress_below_threshold(self) -> None:
        """Test should_compress returns False when below threshold."""
        context = BuiltContext(system_prompt="Test", total_tokens=50000)
        manager = WindowManager()
        assert manager.should_compress(context) is False

    def test_should_compress_above_threshold(self) -> None:
        """Test should_compress returns True when above threshold."""
        context = BuiltContext(system_prompt="Test", total_tokens=90000)
        manager = WindowManager()
        assert manager.should_compress(context) is True

    def test_should_compress_no_compression_strategy(self) -> None:
        """Test should_compress with NONE strategy."""
        context = BuiltContext(system_prompt="Test", total_tokens=90000)
        config = ContextConfig(compression_strategy=CompressionStrategy.NONE)
        manager = WindowManager(config=config)
        assert manager.should_compress(context) is False

    def test_get_snapshot(self) -> None:
        """Test taking a context snapshot."""
        context = BuiltContext(system_prompt="Test", total_tokens=100)
        manager = WindowManager()
        snapshot = manager.get_snapshot(context, "test")
        assert isinstance(snapshot, WindowSnapshot)
        assert snapshot.context is context
        assert snapshot.reason == "test"
        assert len(manager._snapshots) == 1

    def test_get_recent_snapshots(self) -> None:
        """Test getting recent snapshots."""
        context = BuiltContext(system_prompt="Test", total_tokens=100)
        manager = WindowManager()
        for i in range(5):
            manager.get_snapshot(context, f"reason_{i}")

        recent = manager.get_recent_snapshots(3)
        assert len(recent) == 3
        assert recent[0].reason == "reason_4"

    def test_get_recent_snapshots_empty(self) -> None:
        """Test getting recent snapshots when none exist."""
        manager = WindowManager()
        recent = manager.get_recent_snapshots(3)
        assert recent == []

    def test_get_recent_snapshots_zero_limit(self) -> None:
        """Test getting recent snapshots with zero limit."""
        manager = WindowManager()
        recent = manager.get_recent_snapshots(0)
        assert recent == []

    def test_clear_old_snapshots(self) -> None:
        """Test clearing old snapshots."""
        context = BuiltContext(system_prompt="Test", total_tokens=100)
        manager = WindowManager()
        manager.get_snapshot(context, "old")
        manager.clear_old_snapshots(timedelta(hours=0))
        assert len(manager._snapshots) == 0

    def test_clear_old_snapshots_with_zero_age(self) -> None:
        """Test clearing snapshots with zero age clears all."""
        context = BuiltContext(system_prompt="Test", total_tokens=100)
        manager = WindowManager()
        manager.get_snapshot(context, "test")
        removed = manager.clear_old_snapshots(timedelta(hours=0))
        assert removed == 1

    def test_get_snapshot_stats_empty(self) -> None:
        """Test snapshot stats when empty."""
        manager = WindowManager()
        stats = manager.get_snapshot_stats()
        assert stats["count"] == 0
        assert stats["total_tokens"] == 0

    def test_get_snapshot_stats_with_data(self) -> None:
        """Test snapshot stats with data."""
        context = BuiltContext(system_prompt="Test", total_tokens=100)
        manager = WindowManager()
        manager.get_snapshot(context, "test")
        manager.get_snapshot(context, "test2")

        stats = manager.get_snapshot_stats()
        assert stats["count"] == 2
        assert stats["total_tokens"] == 200
        assert stats["oldest"] is not None
        assert stats["newest"] is not None
