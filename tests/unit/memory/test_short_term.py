"""Unit tests for the short_term module."""

import pytest

from mozi.memory.short_term import ShortTermMemory, ShortTermMemoryEntry


class TestShortTermMemoryEntry:
    """Tests for ShortTermMemoryEntry class."""

    def test_entry_creation(self) -> None:
        """Test creating a memory entry."""
        entry = ShortTermMemoryEntry(
            id="test_1",
            content="Test content",
        )
        assert entry.id == "test_1"
        assert entry.content == "Test content"
        assert entry.metadata == {}

    def test_entry_with_metadata(self) -> None:
        """Test creating a memory entry with metadata."""
        metadata = {"key": "value"}
        entry = ShortTermMemoryEntry(
            id="test_2",
            content="Test content",
            metadata=metadata,
        )
        assert entry.metadata == {"key": "value"}


class TestShortTermMemory:
    """Tests for ShortTermMemory class."""

    def test_initialization(self) -> None:
        """Test initializing short-term memory."""
        memory = ShortTermMemory(max_entries=50)
        assert memory.max_entries == 50
        assert len(memory) == 0

    def test_initialization_default(self) -> None:
        """Test initializing short-term memory with defaults."""
        memory = ShortTermMemory()
        assert memory.max_entries == 100
        assert len(memory) == 0

    def test_add_single_entry(self) -> None:
        """Test adding a single entry to memory."""
        memory = ShortTermMemory()
        entry = memory.add("First entry")

        assert len(memory) == 1
        assert entry.content == "First entry"
        assert entry.id.startswith("stm_")

    def test_add_multiple_entries(self) -> None:
        """Test adding multiple entries to memory."""
        memory = ShortTermMemory()
        memory.add("First entry")
        memory.add("Second entry")
        memory.add("Third entry")

        assert len(memory) == 3

    def test_add_with_metadata(self) -> None:
        """Test adding an entry with metadata."""
        memory = ShortTermMemory()
        metadata = {"source": "user", "type": "question"}
        entry = memory.add("What is this?", metadata=metadata)

        assert entry.metadata == {"source": "user", "type": "question"}

    def test_get_recent_default_limit(self) -> None:
        """Test getting recent entries with default limit."""
        memory = ShortTermMemory()
        memory.add("First entry")
        memory.add("Second entry")
        memory.add("Third entry")
        memory.add("Fourth entry")
        memory.add("Fifth entry")

        recent = memory.get_recent()
        assert len(recent) == 5
        assert recent[0].content == "Fifth entry"
        assert recent[-1].content == "First entry"

    def test_get_recent_custom_limit(self) -> None:
        """Test getting recent entries with custom limit."""
        memory = ShortTermMemory()
        memory.add("First entry")
        memory.add("Second entry")
        memory.add("Third entry")

        recent = memory.get_recent(limit=2)
        assert len(recent) == 2
        assert recent[0].content == "Third entry"

    def test_get_recent_zero_limit(self) -> None:
        """Test getting recent entries with zero limit."""
        memory = ShortTermMemory()
        memory.add("First entry")

        recent = memory.get_recent(limit=0)
        assert len(recent) == 0

    def test_get_recent_exceeds_entries(self) -> None:
        """Test getting recent entries when limit exceeds available entries."""
        memory = ShortTermMemory()
        memory.add("Only entry")

        recent = memory.get_recent(limit=10)
        assert len(recent) == 1

    def test_trim(self) -> None:
        """Test trimming memory to max entries."""
        memory = ShortTermMemory(max_entries=200)
        for i in range(150):
            memory.add(f"Entry {i}")

        assert len(memory) == 150

        memory.trim(50)
        assert len(memory) == 50
        assert memory.entries[0].content == "Entry 100"

    def test_trim_auto(self) -> None:
        """Test automatic trimming when exceeding max entries."""
        memory = ShortTermMemory(max_entries=3)
        memory.add("First")
        memory.add("Second")
        memory.add("Third")
        assert len(memory) == 3

        memory.add("Fourth")
        assert len(memory) == 3
        assert memory.entries[0].content == "Second"
        assert memory.entries[-1].content == "Fourth"

    def test_clear(self) -> None:
        """Test clearing all entries from memory."""
        memory = ShortTermMemory()
        memory.add("First entry")
        memory.add("Second entry")

        memory.clear()
        assert len(memory) == 0

    def test_len(self) -> None:
        """Test length of memory."""
        memory = ShortTermMemory()
        assert len(memory) == 0

        memory.add("First entry")
        assert len(memory) == 1

        memory.add("Second entry")
        assert len(memory) == 2

    def test_repr(self) -> None:
        """Test string representation of memory."""
        memory = ShortTermMemory(max_entries=50)
        memory.add("Test entry")

        repr_str = repr(memory)
        assert "ShortTermMemory" in repr_str
        assert "entries=1" in repr_str
        assert "max_entries=50" in repr_str
