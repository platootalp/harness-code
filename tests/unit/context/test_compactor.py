"""Tests for context compactor."""

from __future__ import annotations

import pytest

from mozi.context.compactor import Compactor
from mozi.context.models import (
    BuiltContext,
    CompressionStrategy,
    ContextConfig,
)


@pytest.mark.unit
class TestCompactor:
    """Tests for Compactor class."""

    def test_init_default(self) -> None:
        """Test initialization with defaults."""
        compactor = Compactor()
        assert compactor.config is not None
        assert isinstance(compactor.config, ContextConfig)

    def test_init_custom_config(self) -> None:
        """Test initialization with custom config."""
        config = ContextConfig(max_tokens=50000)
        compactor = Compactor(config=config)
        assert compactor.config.max_tokens == 50000

    @pytest.mark.asyncio
    async def test_compress_none_strategy(self) -> None:
        """Test compression with NONE strategy."""
        compactor = Compactor()
        context = BuiltContext(system_prompt="Test", total_tokens=100)
        compressed, result = await compactor.compress(
            context, CompressionStrategy.NONE
        )
        assert compressed is context
        assert result.original_tokens == 100
        assert result.compressed_tokens == 100

    @pytest.mark.asyncio
    async def test_compress_truncate(self) -> None:
        """Test truncation compression."""
        config = ContextConfig(max_tokens=1000)
        compactor = Compactor(config=config)
        context = BuiltContext(
            system_prompt="System",
            messages=["Message" * 100] * 20,
            total_tokens=2000,
        )
        compressed, result = await compactor.compress(
            context, CompressionStrategy.TRUNCATE
        )
        assert result.strategy_used == CompressionStrategy.TRUNCATE
        assert result.compressed_tokens < result.original_tokens

    @pytest.mark.asyncio
    async def test_compress_summarize(self) -> None:
        """Test summarization compression."""
        compactor = Compactor()
        context = BuiltContext(
            system_prompt="System",
            messages=["Message" * 100] * 10,
            total_tokens=1000,
        )
        compressed, result = await compactor.compress(
            context, CompressionStrategy.SUMMARIZE
        )
        assert result.strategy_used == CompressionStrategy.SUMMARIZE
        assert len(compressed.messages) <= len(context.messages)

    @pytest.mark.asyncio
    async def test_compress_mixed(self) -> None:
        """Test mixed compression strategy."""
        compactor = Compactor()
        context = BuiltContext(
            system_prompt="System",
            messages=["Message" * 100] * 15,
            total_tokens=1500,
        )
        compressed, result = await compactor.compress(
            context, CompressionStrategy.MIXED
        )
        assert result.strategy_used == CompressionStrategy.MIXED

    @pytest.mark.asyncio
    async def test_compress_uses_config_strategy(self) -> None:
        """Test that compression uses config strategy when not specified."""
        config = ContextConfig(compression_strategy=CompressionStrategy.TRUNCATE)
        compactor = Compactor(config=config)
        context = BuiltContext(system_prompt="Test", total_tokens=100)
        _, result = await compactor.compress(context)
        assert result.strategy_used == CompressionStrategy.TRUNCATE

    @pytest.mark.asyncio
    async def test_create_snapshot(self) -> None:
        """Test creating a context snapshot."""
        compactor = Compactor()
        context = BuiltContext(system_prompt="Test", total_tokens=100)
        snapshot = await compactor.create_snapshot(context, "test-snapshot")
        assert snapshot["name"] == "test-snapshot"
        assert "created_at" in snapshot
        assert snapshot["context"]["system_prompt"] == "Test"
        assert snapshot["tokens"] == 100

    @pytest.mark.asyncio
    async def test_merge_snapshots(self) -> None:
        """Test merging multiple snapshots."""
        compactor = Compactor()
        snapshot1 = {
            "name": "snapshot1",
            "context": {
                "system_prompt": "System 1",
                "messages": ["Message 1"],
                "memory_results": [],
            },
        }
        snapshot2 = {
            "name": "snapshot2",
            "context": {
                "system_prompt": "System 2",
                "messages": ["Message 2"],
                "memory_results": ["Memory 1"],
            },
        }
        merged = await compactor.merge_snapshots([snapshot1, snapshot2])
        assert merged is not None
        assert len(merged.messages) == 2
        assert len(merged.memory_results) == 1

    @pytest.mark.asyncio
    async def test_merge_snapshots_empty(self) -> None:
        """Test merging empty snapshots list."""
        compactor = Compactor()
        merged = await compactor.merge_snapshots([])
        assert merged is None
