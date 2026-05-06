"""Tests for MarkdownMemoryBackend via the MemoryBackend protocol."""

from __future__ import annotations

import asyncio
from pathlib import Path

from openharness.memory.base import MemoryBackend, MemoryEntry
from openharness.memory.markdown.backend import MarkdownMemoryBackend


class _SettingsStub:
    class _Memory:
        max_entrypoint_lines = 200
        max_files = 5

    memory = _Memory()


def _run(coro):
    return asyncio.run(coro)


def test_add_returns_memory_entry(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENHARNESS_DATA_DIR", str(tmp_path / "data"))
    backend = MarkdownMemoryBackend(settings=_SettingsStub(), cwd=tmp_path / "project")
    entry = _run(backend.add("test content", title="my-note"))
    assert isinstance(entry, MemoryEntry)
    assert entry.title == "my-note"
    assert entry.content == "test content"


def test_search_finds_entry(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENHARNESS_DATA_DIR", str(tmp_path / "data"))
    backend = MarkdownMemoryBackend(settings=_SettingsStub(), cwd=tmp_path / "project")
    _run(backend.add("Redis cache invalidation strategy", title="redis-cache"))
    results = _run(backend.search("redis caching"))
    assert len(results) >= 1
    assert results[0].title == "redis-cache"


def test_delete_removes_entry(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENHARNESS_DATA_DIR", str(tmp_path / "data"))
    backend = MarkdownMemoryBackend(settings=_SettingsStub(), cwd=tmp_path / "project")
    entry = _run(backend.add("to be deleted", title="deleteme"))
    assert _run(backend.delete(Path(entry.id).stem))
    results = _run(backend.search("deleteme"))
    assert len(results) == 0


def test_list_all_returns_entries(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENHARNESS_DATA_DIR", str(tmp_path / "data"))
    backend = MarkdownMemoryBackend(settings=_SettingsStub(), cwd=tmp_path / "project")
    _run(backend.add("first entry", title="first"))
    _run(backend.add("second entry", title="second"))
    all_entries = _run(backend.list_all())
    assert len(all_entries) >= 2


def test_load_prompt_section(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENHARNESS_DATA_DIR", str(tmp_path / "data"))
    backend = MarkdownMemoryBackend(settings=_SettingsStub(), cwd=tmp_path / "project")
    section = backend.load_prompt_section()
    assert section is not None
    assert "Memory" in section


def test_extract_and_store_is_noop(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENHARNESS_DATA_DIR", str(tmp_path / "data"))
    backend = MarkdownMemoryBackend(settings=_SettingsStub(), cwd=tmp_path / "project")
    result = _run(backend.extract_and_store([{"role": "user", "content": "hello"}]))
    assert result == []


def test_satisfies_protocol():
    """MarkdownMemoryBackend is a proper MemoryBackend subclass."""
    assert issubclass(MarkdownMemoryBackend, MemoryBackend)
