"""Tests for context offloader."""

from __future__ import annotations

import pytest

from mozi.context.models import BuiltContext, ContextConfig
from mozi.context.offloader import OffloadEntry, Offloader


@pytest.mark.unit
class TestOffloader:
    """Tests for Offloader class."""

    def test_init_default(self) -> None:
        """Test initialization with defaults."""
        offloader = Offloader()
        assert offloader.storage_size == 0
        assert offloader.config is not None

    def test_init_custom_max_entries(self) -> None:
        """Test initialization with custom max entries."""
        offloader = Offloader(max_memory_entries=50)
        assert offloader.storage_size == 0

    def test_should_offload_storage_full(self) -> None:
        """Test offload when storage is full."""
        offloader = Offloader(max_memory_entries=1)
        offloader._storage["entry1"] = OffloadEntry(
            entry_id="entry1",
            session_id="session1",
            context={},
        )
        context = BuiltContext(system_prompt="Test", total_tokens=100)
        assert offloader.should_offload(context) is True

    def test_should_offload_token_limit(self) -> None:
        """Test offload when token limit exceeded."""
        config = ContextConfig(max_tokens=1000)
        offloader = Offloader(config=config)
        context = BuiltContext(system_prompt="Test", total_tokens=950)
        assert offloader.should_offload(context) is True

    def test_should_offload_false(self) -> None:
        """Test should_offload returns False when not needed."""
        offloader = Offloader()
        context = BuiltContext(system_prompt="Test", total_tokens=100)
        assert offloader.should_offload(context) is False

    @pytest.mark.asyncio
    async def test_offload(self) -> None:
        """Test offloading a context."""
        offloader = Offloader()
        context = BuiltContext(system_prompt="Test", total_tokens=100)
        entry = await offloader.offload("session1", context)
        assert isinstance(entry, OffloadEntry)
        assert entry.session_id == "session1"
        assert offloader.storage_size == 1

    @pytest.mark.asyncio
    async def test_reload(self) -> None:
        """Test reloading an offloaded context."""
        offloader = Offloader()
        context = BuiltContext(
            system_prompt="Test",
            messages=["Message 1"],
            total_tokens=100,
        )
        entry = await offloader.offload("session1", context)
        reloaded = await offloader.reload(entry.entry_id)
        assert reloaded is not None
        assert reloaded.system_prompt == "Test"
        assert reloaded.messages == ["Message 1"]

    @pytest.mark.asyncio
    async def test_reload_not_found(self) -> None:
        """Test reloading non-existent entry."""
        offloader = Offloader()
        reloaded = await offloader.reload("nonexistent")
        assert reloaded is None

    @pytest.mark.asyncio
    async def test_reload_updates_access_count(self) -> None:
        """Test that reload updates access statistics."""
        offloader = Offloader()
        context = BuiltContext(system_prompt="Test", total_tokens=100)
        entry = await offloader.offload("session1", context)
        assert entry.access_count == 0
        await offloader.reload(entry.entry_id)
        assert entry.access_count == 1

    @pytest.mark.asyncio
    async def test_reload_by_session(self) -> None:
        """Test reloading all contexts for a session."""
        offloader = Offloader()
        context1 = BuiltContext(system_prompt="Test 1", total_tokens=100)
        context2 = BuiltContext(system_prompt="Test 2", total_tokens=100)
        await offloader.offload("session1", context1)
        await offloader.offload("session2", context2)
        await offloader.offload("session1", context2)
        results = await offloader.reload_by_session("session1")
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_delete(self) -> None:
        """Test deleting an offload entry."""
        offloader = Offloader()
        context = BuiltContext(system_prompt="Test", total_tokens=100)
        entry = await offloader.offload("session1", context)
        result = await offloader.delete(entry.entry_id)
        assert result is True
        assert offloader.storage_size == 0

    @pytest.mark.asyncio
    async def test_delete_not_found(self) -> None:
        """Test deleting non-existent entry."""
        offloader = Offloader()
        result = await offloader.delete("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_clear_session(self) -> None:
        """Test clearing all entries for a session."""
        offloader = Offloader()
        context = BuiltContext(system_prompt="Test", total_tokens=100)
        await offloader.offload("session1", context)
        await offloader.offload("session1", context)
        await offloader.offload("session2", context)
        cleared = await offloader.clear_session("session1")
        assert cleared == 2
        assert offloader.storage_size == 1

    def test_get_stats_empty(self) -> None:
        """Test getting stats when empty."""
        offloader = Offloader()
        stats = offloader.get_stats()
        assert stats["storage_size"] == 0
        assert stats["max_entries"] == offloader._max_entries
        assert stats["total_access_count"] == 0
