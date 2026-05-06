"""Tests for the memory backend registry."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from openharness.memory.base import MemoryBackend, MemoryEntry
from openharness.memory.registry import _backends, get_backend, register_backend


class _DummyBackend(MemoryBackend):
    def __init__(self, *, settings, cwd):
        self.cwd = cwd

    async def add(self, content, *, title="", memory_type="", metadata=None):
        return MemoryEntry(id="x", title=title, content=content)

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


class _SettingsStub:
    class _Memory:
        backend = "dummy"

    memory = _Memory()


def test_register_and_get_backend():
    register_backend("dummy", _DummyBackend)
    backend = get_backend(_SettingsStub(), cwd="/tmp/test")
    assert isinstance(backend, _DummyBackend)
    assert backend.cwd == Path("/tmp/test")


def test_get_unknown_backend_raises():
    with pytest.raises(ValueError, match="Unknown memory backend: nonexistent"):
        get_backend(
            type("_S", (), {"memory": type("_M", (), {"backend": "nonexistent"})()}),
            cwd="/tmp",
        )


def test_register_overwrites():
    register_backend("overwrite_test", _DummyBackend)
    register_backend("overwrite_test", _DummyBackend)
    backend = get_backend(_SettingsStub(), cwd="/tmp")
    assert isinstance(backend, _DummyBackend)
