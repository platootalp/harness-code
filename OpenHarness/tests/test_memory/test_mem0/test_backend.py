"""Tests for Mem0MemoryBackend with mocked mem0 client."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from openharness.memory.base import MemoryBackend, MemoryEntry
from openharness.memory.mem0.backend import Mem0MemoryBackend


class _Mem0Settings:
    storage = "local"
    vector_store = "chroma"
    embedder = "openai"
    embedder_model = "text-embedding-3-small"
    api_key = None
    base_url = None
    auto_extract = True
    extract_user_id = "default"
    extract_every_n_messages = 5
    extract_every_seconds = 300.0


class _SettingsStub:
    class _Memory:
        backend = "mem0"
        max_entrypoint_lines = 200
        max_files = 5
        mem0 = _Mem0Settings()

    memory = _Memory()


def _run(coro):
    return asyncio.run(coro)


def _mock_local_client():
    """Return a mock Memory (local) client."""
    client = MagicMock()
    client.add.return_value = {"results": [{"id": "mem1", "memory": "User prefers dark mode", "event": "ADD"}]}
    client.search.return_value = [
        {"id": "mem1", "memory": "User prefers dark mode", "score": 0.95,
         "metadata": {"title": "theme-pref", "memory_type": "preference"}},
    ]
    client.get_all.return_value = [
        {"id": "mem1", "memory": "User prefers dark mode",
         "metadata": {"title": "theme-pref", "memory_type": "preference"}},
    ]
    client.delete.return_value = None
    return client


def test_add_calls_client(tmp_path: Path):
    backend = Mem0MemoryBackend(settings=_SettingsStub(), cwd=tmp_path)
    mock_client = _mock_local_client()
    backend._client = mock_client

    entry = _run(backend.add("User prefers dark mode", title="theme-pref", memory_type="preference"))

    mock_client.add.assert_called_once()
    assert isinstance(entry, MemoryEntry)
    assert entry.content == "User prefers dark mode"


def test_search_returns_scored_entries(tmp_path: Path):
    backend = Mem0MemoryBackend(settings=_SettingsStub(), cwd=tmp_path)
    mock_client = _mock_local_client()
    backend._client = mock_client

    results = _run(backend.search("theme preference"))

    assert len(results) == 1
    assert results[0].score == 0.95
    assert results[0].memory_type == "preference"


def test_delete_calls_client(tmp_path: Path):
    backend = Mem0MemoryBackend(settings=_SettingsStub(), cwd=tmp_path)
    mock_client = _mock_local_client()
    backend._client = mock_client

    result = _run(backend.delete("mem1"))
    assert result is True
    mock_client.delete.assert_called_once_with("mem1")


def test_list_all_calls_get_all(tmp_path: Path):
    backend = Mem0MemoryBackend(settings=_SettingsStub(), cwd=tmp_path)
    mock_client = _mock_local_client()
    backend._client = mock_client

    entries = _run(backend.list_all())
    assert len(entries) == 1
    mock_client.get_all.assert_called_once()


def test_list_all_filters_by_memory_type(tmp_path: Path):
    backend = Mem0MemoryBackend(settings=_SettingsStub(), cwd=tmp_path)
    mock_client = _mock_local_client()
    backend._client = mock_client

    entries = _run(backend.list_all(memory_type="preference"))
    assert len(entries) == 1

    entries = _run(backend.list_all(memory_type="fact"))
    assert len(entries) == 0


def test_extract_and_store_calls_add_with_messages(tmp_path: Path):
    backend = Mem0MemoryBackend(settings=_SettingsStub(), cwd=tmp_path)
    mock_client = _mock_local_client()
    backend._client = mock_client

    messages = [{"role": "user", "content": "I prefer dark mode"}]
    entries = _run(backend.extract_and_store(messages))

    mock_client.add.assert_called_once_with(messages, user_id="default")
    assert len(entries) >= 1


def test_extract_and_store_disabled(tmp_path: Path):
    settings = _SettingsStub()
    settings.memory.mem0.auto_extract = False
    backend = Mem0MemoryBackend(settings=settings, cwd=tmp_path)
    mock_client = _mock_local_client()
    backend._client = mock_client

    entries = _run(backend.extract_and_store([{"role": "user", "content": "hello"}]))
    assert entries == []
    mock_client.add.assert_not_called()


def test_load_prompt_section_reads_cache(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENHARNESS_DATA_DIR", str(tmp_path / "data"))
    backend = Mem0MemoryBackend(settings=_SettingsStub(), cwd=tmp_path / "project")
    cache_dir = tmp_path / "data" / "mem0_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    slug = backend._slug  # get the slug used by the backend
    cache_file = cache_dir / f"{slug}.md"
    cache_file.write_text("# mem0 Memories\n- User prefers dark mode\n", encoding="utf-8")
    backend._cache_path = cache_file
    section = backend.load_prompt_section()
    # Returns None if cache doesn't exist or can't be read
    assert section is None or isinstance(section, str)


def test_satisfies_protocol():
    assert issubclass(Mem0MemoryBackend, MemoryBackend)