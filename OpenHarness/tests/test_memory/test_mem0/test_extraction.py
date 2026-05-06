"""Tests for memory extraction timing (dual-trigger + compact safety net)."""

from __future__ import annotations

from openharness.memory.base import MemoryBackend


class _StubBackend(MemoryBackend):
    """Minimal backend with real should_extract for timing tests."""

    async def add(self, content, *, title="", memory_type="", metadata=None):
        return NotImplemented

    async def search(self, query, *, max_results=5):
        return NotImplemented

    async def delete(self, id):
        return NotImplemented

    async def list_all(self, *, memory_type=""):
        return NotImplemented

    def load_prompt_section(self, *, max_lines=200):
        return NotImplemented

    async def extract_and_store(self, messages):
        return []


def test_trigger_on_message_count():
    backend = _StubBackend()
    assert backend.should_extract(
        message_count=5, elapsed_seconds=0,
        extract_every_n_messages=5, extract_every_seconds=300,
    )


def test_trigger_on_elapsed_time():
    backend = _StubBackend()
    assert backend.should_extract(
        message_count=0, elapsed_seconds=300,
        extract_every_n_messages=5, extract_every_seconds=300,
    )


def test_no_trigger_below_thresholds():
    backend = _StubBackend()
    assert not backend.should_extract(
        message_count=4, elapsed_seconds=299,
        extract_every_n_messages=5, extract_every_seconds=300,
    )


def test_trigger_on_either_threshold():
    backend = _StubBackend()
    # Count met but time not
    assert backend.should_extract(
        message_count=5, elapsed_seconds=10,
        extract_every_n_messages=5, extract_every_seconds=300,
    )
    # Time met but count not
    assert backend.should_extract(
        message_count=1, elapsed_seconds=300,
        extract_every_n_messages=5, extract_every_seconds=300,
    )


def test_custom_thresholds():
    backend = _StubBackend()
    # More aggressive thresholds
    assert backend.should_extract(
        message_count=2, elapsed_seconds=0,
        extract_every_n_messages=2, extract_every_seconds=60,
    )
    # Not yet with lenient thresholds
    assert not backend.should_extract(
        message_count=2, elapsed_seconds=0,
        extract_every_n_messages=10, extract_every_seconds=600,
    )
