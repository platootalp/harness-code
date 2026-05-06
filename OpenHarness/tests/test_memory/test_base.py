"""Tests for the MemoryBackend protocol and MemoryEntry dataclass."""

from __future__ import annotations

import asyncio
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from openharness.memory.base import MemoryBackend, MemoryEntry


class _StubBackend(MemoryBackend):
    """Minimal concrete backend for protocol tests."""

    async def add(self, content, *, title="", memory_type="", metadata=None):
        return MemoryEntry(id="1", title=title, content=content, memory_type=memory_type)

    async def search(self, query, *, max_results=5):
        return []

    async def delete(self, id):
        return True

    async def list_all(self, *, memory_type=""):
        return []

    def load_prompt_section(self, *, max_lines=200):
        return None

    async def extract_and_store(self, messages):
        return []


def test_memory_entry_is_frozen():
    entry = MemoryEntry(id="1", title="test", content="hello")
    with pytest.raises(FrozenInstanceError):
        entry.id = "2"


def test_memory_entry_defaults():
    entry = MemoryEntry(id="1", title="test", content="hello")
    assert entry.memory_type == ""
    assert entry.metadata is None
    assert entry.score is None


def test_memory_entry_with_all_fields():
    entry = MemoryEntry(
        id="abc", title="pref", content="likes dark mode",
        memory_type="preference", metadata={"source": "chat"}, score=0.95,
    )
    assert entry.memory_type == "preference"
    assert entry.metadata == {"source": "chat"}
    assert entry.score == 0.95


def test_stub_backend_satisfies_protocol():
    backend = _StubBackend()
    result = asyncio.run(backend.add("test content", title="test"))
    assert result.content == "test content"
    assert result.title == "test"


def test_should_extract_count_trigger():
    backend = _StubBackend()
    assert backend.should_extract(
        message_count=5, elapsed_seconds=0,
        extract_every_n_messages=5, extract_every_seconds=300,
    )


def test_should_extract_time_trigger():
    backend = _StubBackend()
    assert backend.should_extract(
        message_count=0, elapsed_seconds=300,
        extract_every_n_messages=5, extract_every_seconds=300,
    )


def test_should_extract_no_trigger():
    backend = _StubBackend()
    assert not backend.should_extract(
        message_count=3, elapsed_seconds=100,
        extract_every_n_messages=5, extract_every_seconds=300,
    )


def test_cannot_instantiate_abc_directly():
    with pytest.raises(TypeError):
        MemoryBackend()
